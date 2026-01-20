import logging
import json

from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown

from ibm_watsonx_orchestrate.client.chat.run_client import RunClient
from ibm_watsonx_orchestrate.client.threads.threads_client import ThreadsClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.cli.commands.agents.agents_helper import get_agent_id_by_name

logger = logging.getLogger(__name__)
console = Console()

# Emojis matching evaluation framework
USER_EMOJI = "👤"
BOT_EMOJI = "🤖"


def create_run_client() -> RunClient:
    """Create and return an RunClient instance using active environment."""
    return instantiate_client(RunClient)


def create_threads_client() -> ThreadsClient:
    """Create and return a ThreadsClient instance using active environment."""
    return instantiate_client(ThreadsClient)


def display_message(role: str, content: str, agent_name:str, include_reasoning: bool = False, reasoning_trace: Optional[dict] = None):
    """Display a message with appropriate emoji and formatting."""
    emoji = USER_EMOJI if role == "user" else BOT_EMOJI
    if role == "user":
        title = f"{emoji} {role.capitalize()}"
    else:
        title: str = f"{emoji} {agent_name}"

    # For assistant agent messages, try to render as markdown for better table formatting
    if role == "assistant" and "|" in content:
        try:
            rendered_content = Markdown(content)
        except:
            rendered_content = content
    else:
        rendered_content = content
    # Include reasoning if requested
    if include_reasoning and reasoning_trace:
        reasoning_content = format_reasoning_trace(reasoning_trace)
        reasoning_panel = Panel(
            reasoning_content,
            title="🧠 Reasoning Trace",
            title_align="left",
            border_style="yellow",
            padding=(1, 2)
        )
        console.print(reasoning_panel) 
    # Agent answer
    panel = Panel(
    rendered_content,
    title=title,
    title_align="left",
    border_style="blue" if role == "user" else "green",
    padding=(1, 2)
    )
    console.print(panel)


def format_reasoning_trace(trace: dict) -> str:
    """Format reasoning trace for display."""
    if not trace:
        return "No reasoning trace available"
    
    formatted = []

    if "steps" in trace:
        step_num = 1
        for step in trace["steps"]:
            if "step_details" in step:
                step_details = step['step_details'][0]
                
                if step_details['type'] == 'tool_calls': # tool calls
                    for tool_call in step_details['tool_calls']: 
                        formatted.append(f"Step {step_num}: Called tool '{tool_call['name']}'")
                        if tool_call.get('args') and tool_call['args'].get(''):
                            formatted.append(f"  Arguments: {tool_call['args']}")
                        agent_name = step_details.get('agent_display_name', 'agent')
                        formatted.append(f"  Agent: {agent_name}")
                        step_num += 1                       
                elif step_details['type'] == 'tool_response': #  tool response
                    formatted.append(f"Step {step_num}: Tool '{step_details.get('name', 'unknown')}' responded")
                    content = step_details.get('content', '')
                    formatted.append(f"  Response: {content}")
                    step_num += 1
    else:
        formatted.append(json.dumps(trace, indent=2))
    
    return "\n".join(formatted) if formatted else "No steps found"


def _execute_agent_interaction(run_client:RunClient, threads_client:ThreadsClient, message:str, agent_id:str, include_reasoning:bool, agent_name:str, thread_id: Optional[str] = None) -> Optional[str]:
    """Execute agent interaction: send message, wait for response, display answer, and return thread_id to keep the conversation context in interactive mode."""

    with console.status("[bold green]Processing...", spinner="dots"):
        run_response = run_client.create_run(
            message=message,
            agent_id=agent_id,
            thread_id=thread_id,  # Use the parameter, not None!
        )
    
    # Always get the thread_id from the response for conversation continuity
    thread_id = run_response["thread_id"]
    
    with console.status("[bold green]Waiting for response...", spinner="dots"):
        run_status = run_client.wait_for_run_completion(run_response["run_id"])
    
    # Check for errors
    if run_status.get("status") == "failed":
        error_msg = run_status.get("error", "Unknown error")
        console.print(f"[red]Error: {error_msg}[/red]")
        logger.error(f"Run failed with status: {run_status}")
        return
    
    thread_messages_response = threads_client.get_thread_messages(thread_id)
    
    # Handle both list and dict responses
    if isinstance(thread_messages_response, list):
        messages = thread_messages_response
    elif isinstance(thread_messages_response, dict) and "data" in thread_messages_response:
        messages = thread_messages_response["data"]
    else:
        messages = []
    
    # Find and display the assistant's response
    assistant_message = None
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            assistant_message = msg
            break
    
    if assistant_message:
        content = assistant_message.get("content", "No response")
        
        # Handle structured content (list of response objects)
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("response_type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif "text" in item:
                        text_parts.append(item["text"])
            content = "\n".join(text_parts) if text_parts else str(content)
        
        # Get reasoning trace if requested
        reasoning_trace = None
        if include_reasoning:
            if assistant_message and "step_history" in assistant_message:
                reasoning_trace = {"steps": assistant_message["step_history"]}
            # Fallback to log_id approach (old format)
            elif run_status.get("log_id"):
                log_id = run_status["log_id"]
                try:
                    logger.info(f"Fetching reasoning trace for log_id: {log_id}")
                    reasoning_trace = threads_client.get_logs_by_log_id(log_id)
                except Exception as e:
                    logger.error(f"Could not retrieve reasoning trace: {e}")
                    console.print(f"[yellow]Note: Could not retrieve reasoning trace: {e}[/yellow]")
            else:
                logger.info("No step_history or log_id available")

        display_message("assistant", content, agent_name, include_reasoning, reasoning_trace)
    else:
        console.print("[yellow]No response from assistant[/yellow]")
    return thread_id


def chat_ask_interactive(
    agent_name: str,
    include_reasoning: bool,
    initial_message: Optional[str] = None
):
    """Interactive chat mode. If initial_message is provided, it's sent automatically first and then opens the chat."""
    # convert the agent name to agent id which runclient understands
    agent_id = get_agent_id_by_name(agent_name)

    run_client = create_run_client()
    threads_client = create_threads_client()
    thread_id = None
    
    console.print(Panel(
        "[bold cyan]Chat Mode[/bold cyan]\n\n"
        "Type your messages and press Enter to send.\n"
        "Commands: 'exit', 'quit', or 'q' to exit",
        title="💬 Chat",
        border_style="cyan"
    ))
    
    # Send initial message if provided
    if initial_message:
        display_message("user", initial_message, agent_name=agent_name)
        thread_id = _execute_agent_interaction(
            run_client, threads_client, initial_message, agent_id, include_reasoning, agent_name, thread_id
        )
    
    exit_command: list[str]=["exit", "quit", "q"]
    
    while True:
        try:
            user_input = Prompt.ask(f"\n{USER_EMOJI} You")
            
            # Check for exit commands
            if user_input.lower() in exit_command:
                console.print("[yellow]Exiting chat...[/yellow]")
                break

            if not user_input.strip():
                continue
            
            # Display user message
            display_message("user", user_input, agent_name=agent_name)

            # execute the whole agent interaction of sending, reveiving and displaying the message
            thread_id=_execute_agent_interaction(run_client, threads_client,user_input, agent_id, include_reasoning, agent_name, thread_id)
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]Exiting chat...[/yellow]")
            break
        except Exception as e:
            logger.error(f"Error during chat: {e}")
            console.print(f"[red]Error: {e}[/red]")
            continue
