import logging
import json
import ast
import time

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

    if "steps" in trace and trace["steps"] is not None:
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


def _check_for_widgets_and_extract_text(content) -> tuple[bool, str]:
    """
    Check if content contains widgets and extract text parts.
    Also detects error messages that indicate a widget was needed (e.g., file upload errors).
    
    Returns:
        tuple: (has_widgets: bool, extracted_text: str)
    """
    # Handle None or non-list content
    if content is None:
        return False, "No response"

    if not isinstance(content, list):
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, ValueError):
                try: # If JSON fails, try Python literal eval (handles single quotes)
                    content = ast.literal_eval(content)
                except (ValueError, SyntaxError):
                    
                    return False, content
        else: # If it's a dict or other non-string, non-list type
            return False, str(content)
    
    text_parts = []
    has_widgets = False
    
    # Keywords that indicate a file upload or form widget was needed (needed in document_processing)
    widget_error_keywords = [
        "file type",
        "document content is not supported",
        "the supported file types",
        "upload",
        "please provide a file",
        "missing file",
        "no file provided"
    ]
    
    if not isinstance(content, list): # After parsing, content should be a list. If not, something went wrong
        return False, str(content) if content is not None else "No response"
    
    for item in content:
        if isinstance(item, dict):
            response_type = item.get("response_type", "")

            # Check for widget/form response types that cannot be rendered in CLI
            if response_type in ["user_input", "form", "forms", "file_upload"]:
                has_widgets = True
            elif response_type == "text": # Check if the text contains error messages indicating a widget was needed
                text_content = item.get("text", "")
                text_parts.append(text_content)
                text_lower = text_content.lower()
                if "error in flow execution" in text_lower:
                    for keyword in widget_error_keywords:
                        if keyword in text_lower:
                            has_widgets = True
                            break
            elif "text" in item:
                text_parts.append(item["text"])
    
    extracted_text = "\n".join(text_parts) if text_parts else str(content)
    return has_widgets, extracted_text


def _poll_and_display_async_messages(
    threads_client: ThreadsClient,
    thread_id: str,
    initial_message_count: int,
    agent_name: str,
    poll_interval: int = 1
) -> Optional[dict]:
    """
    Poll for flow completion and display async messages as they arrive.
    
    Args:
        threads_client: The threads client instance
        thread_id: The thread ID to poll
        initial_message_count: Number of messages before the flow started
        agent_name: Name of the agent for display
        poll_interval: Seconds between polling attempts
        
    Returns:
        The final message dict (with is_async=false), or None if not found
    """
    
    displayed_message_ids = set()
    attempt = 0
    warning_shown = False
    start_time = time.time()

    with console.status("[bold green]Waiting for flow to complete...", spinner="dots"):
        while True:
            try:
                # Check if 30 seconds have passed and show warning
                elapsed_time = time.time() - start_time
                if elapsed_time >= 30 and not warning_shown:
                    console.print()
                    warning_panel = Panel(
                        "This is taking longer than expected, CTRL+C to cancel the run.\nUse 'orchestrate chat start' for the full chat experience.",
                        title="⚠️  Warning",
                        title_align="left",
                        border_style="yellow",
                        padding=(1, 2)
                    )
                    console.print(warning_panel)
                    console.print()
                    warning_shown = True
                
                thread_messages_response = threads_client.get_thread_messages(thread_id)
                if isinstance(thread_messages_response, list):
                    messages = thread_messages_response
                elif isinstance(thread_messages_response, dict) and "data" in thread_messages_response:
                    messages = thread_messages_response["data"]
                else:
                    messages = []
                
                if len(messages) > initial_message_count:
                    # Check all new messages
                    for msg in messages[initial_message_count:]:
                        if isinstance(msg, dict) and msg.get("role") == "assistant":
                            msg_id = msg.get("id")
                                                        
                            # Skip if already displayed
                            if msg_id in displayed_message_ids:
                                continue
                            
                            content = msg.get("content", "")
                            is_flow_started_msg = False
                            
                            if isinstance(content, str):
                                if "flow has started" in content.lower() or "flow instance ID" in content:
                                    is_flow_started_msg = True
                            elif isinstance(content, list):
                                text_parts = []
                                for item in content:
                                    if isinstance(item, dict):
                                        if item.get("response_type") == "text":
                                            text_parts.append(item.get("text", ""))
                                        elif "text" in item:
                                            text_parts.append(item["text"])
                                full_text = "\n".join(text_parts)
                                if "flow has started" in full_text.lower() or "flow instance ID" in full_text:
                                    is_flow_started_msg = True
                            
                            # Skip flow started messages
                            if is_flow_started_msg:
                                displayed_message_ids.add(msg_id)
                                continue
                            
                            # Check if this is an async message or the final message
                            additional_props = msg.get("additional_properties", {})
                            display_props = additional_props.get("display_properties") if additional_props else None
                            is_async = display_props.get("is_async", False) if display_props else False
                            
                            # Check for widgets/forms that need user input (check BEFORE displaying)
                            has_widgets, _ = _check_for_widgets_and_extract_text(content)
                            if has_widgets:
                                logger.info(f"Found widget/form in async message (id: {msg_id}) - flow needs user input")
                                console.print()
                                widget_panel = Panel(
                                    "Sorry the chat ask command cannot render widgets.\nPlease use orchestrate chat start to access the full ui experience",
                                    title="Widget Detected",
                                    title_align="left",
                                    border_style="yellow",
                                    padding=(1, 2)
                                )
                                console.print(widget_panel)
                                console.print()
                                return None
                            
                            if isinstance(content, list):
                                text_parts = []
                                for item in content:
                                    if isinstance(item, dict):
                                        if item.get("response_type") == "text":
                                            text_parts.append(item.get("text", ""))
                                        elif "text" in item:
                                            text_parts.append(item["text"])
                                content_text = "\n".join(text_parts) if text_parts else str(content)
                            else:
                                content_text = str(content)
                            
                            console.print()  # Add spacing
                            if is_async:
                                # Display thinking async message
                                async_panel = Panel(
                                    content_text,
                                    title=f"💭 {agent_name} (Thinking...)",
                                    title_align="left",
                                    border_style="yellow",
                                    padding=(1, 2)
                                )
                                console.print(async_panel)
                            else: # This is the final message
                                return msg
                            
                            displayed_message_ids.add(msg_id)
                
                time.sleep(poll_interval)
                attempt += 1
                
            except KeyboardInterrupt:
                logger.info(f"Flow polling interrupted by user (Ctrl+C) after {attempt} attempts")
                raise
            except Exception as e:
                logger.warning(f"Error polling for flow completion (attempt {attempt + 1}): {e}")
                time.sleep(poll_interval)
    

def _execute_agent_interaction(run_client:RunClient, threads_client:ThreadsClient, message:str, agent_id:str, include_reasoning:bool, agent_name:str, thread_id: Optional[str] = None) -> Optional[str]:
    """Execute agent interaction: send message, wait for response, display answer, and return thread_id to keep the conversation context in interactive mode."""
    try:
        run_response = run_client.create_run(
            message=message,
            agent_id=agent_id,
            thread_id=thread_id,
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
        
        initial_message_count = len(messages)
        
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
            
            # Get reasoning trace as it's needed for flow detection
            reasoning_trace = None

            if assistant_message and "step_history" in assistant_message:
                reasoning_trace = {"steps": assistant_message["step_history"]}

            if include_reasoning and not reasoning_trace:
                # If we don't have step_history, fallback to log_id approach (old format)
                if not reasoning_trace and run_status.get("log_id"):
                    log_id = run_status["log_id"]
                    try:
                        reasoning_trace = threads_client.get_logs_by_log_id(log_id)
                    except Exception as e:
                        logger.error(f"Could not retrieve reasoning trace: {e}")
                        raise e
                
            # Check if we got content indicating flow (in content or reasoning trace)
            is_flow_started = False
            flow_message = None
            
            # Check in main content
            if isinstance(content, str):
                if ("flow has started" in content.lower() or
                    "flow instance id" in content.lower() or
                    "thread will remain blocked" in content.lower()):
                    is_flow_started = True
                    flow_message = content
            
            # Also check in reasoning trace (tool responses) - even without -r flag
            if not is_flow_started and reasoning_trace and reasoning_trace.get("steps"):
                for step in reasoning_trace["steps"]:
                    if "step_details" in step:
                        for step_detail in step["step_details"]:
                            if step_detail.get("type") == "tool_response":
                                tool_content = str(step_detail.get("content", ""))
                                if ("flow instance id" in tool_content.lower() or
                                    "thread will remain blocked" in tool_content.lower() or
                                    "flow has started" in content.lower()  
                                    ):
                                    is_flow_started = True
                                    flow_message = tool_content
                                    break
                    if is_flow_started:
                        break
            # Also check if the message has is_async=true (indicates more messages coming)
            if not is_flow_started and assistant_message:
                additional_props = assistant_message.get("additional_properties", {})
                display_props = additional_props.get("display_properties") if additional_props else None
                is_async = display_props.get("is_async", False) if display_props else False
                
                if is_async:
                    is_flow_started = True
            
            if is_flow_started: # Display the flow started message (if we have one)
                if flow_message:
                    console.print()
                    flow_panel = Panel(
                        flow_message,
                        title="🔄 Flow Started",
                        title_align="left",
                        border_style="blue",
                        padding=(1, 2)
                    )
                    console.print(flow_panel)
                    console.print()
                    
                # Also check if the current message already contains a widget in content
                if assistant_message:
                    current_content = assistant_message.get("content", "")
                    has_widgets, _ = _check_for_widgets_and_extract_text(current_content)
                    if has_widgets:
                        logger.info("Flow started message contains widget - needs user input")
                        console.print()
                        widget_panel = Panel(
                            "Sorry the chat ask command cannot render widgets.\nPlease use orchestrate chat start to access the full ui experience",
                            title="Widget Detected",
                            title_align="left",
                            border_style="yellow",
                            padding=(1, 2)
                        )
                        console.print(widget_panel)
                        console.print()
                        return None
                
                # Now wait for flow completion and display async messages as they arrive
                flow_completion_message = _poll_and_display_async_messages(
                    threads_client, thread_id, initial_message_count, agent_name
                )
                
                # If None was returned, it means a widget was detected or an error occurred
                if flow_completion_message is None:
                    return None
                
                if flow_completion_message:
                    # Update with the flow completion message
                    assistant_message = flow_completion_message
                    content = assistant_message.get("content", "No response")
                    if include_reasoning and (not reasoning_trace or not reasoning_trace["steps"]): # Update reasoning trace if not provided in the beginning
                        if "step_history" in assistant_message and assistant_message["step_history"]:
                            reasoning_trace = {"steps": assistant_message["step_history"]}
                        elif run_status and "result" in run_status:
                            try:
                                step_history = run_status.get("result", {}).get("data", {}).get("message", {}).get("step_history")
                                if step_history:
                                    reasoning_trace = {"steps": step_history}
                            except (KeyError, TypeError, AttributeError):
                                pass
                        if not reasoning_trace and run_response.get("run_id"): # If still not found, try re-fetching
                            try:
                                updated_run_status = run_client.get_run_status(run_response["run_id"])
                                if updated_run_status and "result" in updated_run_status:
                                    step_history = updated_run_status.get("result", {}).get("data", {}).get("message", {}).get("step_history")
                                    if step_history:
                                        reasoning_trace = {"steps": step_history}
                            except Exception as e:
                                logger.warning(f"Could not retrieve reasoning trace after flow completion: {e}")
                else:
                    console.print("[yellow]Flow did not complete[/yellow]")
                    return thread_id
            
            # Check for widgets in the final content
            has_widgets, content = _check_for_widgets_and_extract_text(content)
            
            if has_widgets:
                console.print()
                widget_panel = Panel(
                    "Sorry the chat ask command cannot render widgets.\nPlease use orchestrate chat start to access the full ui experience",
                    title="Widget Detected",
                    title_align="left",
                    border_style="yellow",
                    padding=(1, 2)
                    )
                console.print(widget_panel)
                console.print()
                return None

            display_message("assistant", content, agent_name, include_reasoning, reasoning_trace)
        else:
            console.print("[yellow]No response from assistant[/yellow]")
        return thread_id

    except Exception as e:
        logger.error(f"Error in _execute_agent_interaction: {e}", exc_info=True)
        console.print(f"[red]Error: {e}[/red]")
        raise e


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
        if thread_id is None: # Widget was detected or error occurred, exit chat
            return
    
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
            if thread_id is None: # Widget was detected or error occurred, exit chat
                break
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]Exiting chat...[/yellow]")
            break
        except Exception as e:
            logger.error(f"Error during chat: {e}")
            console.print(f"[red]Error: {e}[/red]")
            continue
