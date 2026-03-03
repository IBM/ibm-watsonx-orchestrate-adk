import logging
import json
import ast
import time
import asyncio
import os
import requests

from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown

from ibm_watsonx_orchestrate.client.chat.run_client import RunClient
from ibm_watsonx_orchestrate.client.threads.threads_client import ThreadsClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.cli.commands.agents.agents_helper import get_agent_id_by_name
from ibm_watsonx_orchestrate.cli.commands.chat.types import AgentInteractionResult

logger = logging.getLogger(__name__)
console = Console()

# Emojis matching evaluation framework
USER_EMOJI = "👤"
BOT_EMOJI = "🤖"

# Log level colors for captured logs display
LOG_LEVEL_COLORS = {
    "DEBUG": "blue",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold red"
}

def create_run_client() -> RunClient:
    """Create and return an RunClient instance using active environment."""
    return instantiate_client(RunClient)


def create_threads_client() -> ThreadsClient:
    """Create and return a ThreadsClient instance using active environment."""
    return instantiate_client(ThreadsClient)


def display_message(
    role: str,
    content: str,
    agent_name: str,
    include_reasoning: bool = False,
    reasoning_trace: Optional[dict] = None,
    thread_id: Optional[str] = None,
    return_agent_interaction_result: bool = False,
    thinking_messages: Optional[List[str]] = None
) -> Optional[AgentInteractionResult]:
    """
    Display a message with appropriate emoji and formatting.
    
    Args:
        role: The role of the message sender ("user" or "assistant")
        content: The message content to display
        agent_name: The name of the agent
        include_reasoning: Whether to include reasoning trace
        reasoning_trace: The reasoning trace data
        thread_id: The conversation thread ID
        return_agent_interaction_result: If True, return AgentInteractionResult instead of None
        thinking_messages: List of thinking messages collected during interaction
        
    Returns:
        AgentInteractionResult if return_agent_interaction_result=True, otherwise None
    """
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
    
    # Return structured result if requested (for MCP/API usage)
    if return_agent_interaction_result and role == "assistant":
        # Use provided thinking messages or empty list
        thinking_trace = thinking_messages if thinking_messages is not None else []
        
        result = AgentInteractionResult(
            status="success",
            final_message=content,
            thinking_trace=thinking_trace,
            reasoning_trace=reasoning_trace if include_reasoning else None,
            thread_id=thread_id,
            error=None
        )
        return result
    
    return None


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


def _display_captured_logs_via_api(threads_client: ThreadsClient, run_status: dict, final_message: dict = None) -> bool:
    """
    Retrieve and display captured logs using the API endpoint.
    
    Args:
        threads_client: The threads client instance
        run_status: The run status response
        final_message: Optional final message dict
        
    Returns:
        bool: True if logs were successfully retrieved and displayed, False otherwise
    """
    try:
        # Extract log_id from various locations
        log_id = None
        
        # Check in run_status
        if run_status:
            result = run_status.get('result', {})
            if isinstance(result, dict):
                data = result.get('data', {})
                if isinstance(data, dict):
                    message = data.get('message', {})
                    if isinstance(message, dict):
                        log_id = message.get('log_id')
                        if not log_id:
                            # Also check in additional_properties
                            add_props = message.get('additional_properties', {})
                            if isinstance(add_props, dict):
                                log_id = add_props.get('log_id')
        
        # Check in final_message if not found
        if not log_id and final_message:
            log_id = final_message.get('log_id')
            if not log_id:
                metadata = final_message.get('additional_properties', {})
                if isinstance(metadata, dict):
                    log_id = metadata.get('log_id')
        
        # Validate log_id
        if not log_id or (isinstance(log_id, str) and log_id.strip() == ""):
            return False
        
        # Call the API endpoint GET /threads/logs/{log_id}
        logs_response = threads_client.get_logs_by_log_id(log_id)
        captured_logs = logs_response.get("captured_logs", {})
        
        if captured_logs: # call the function that prints the captured logs
            _display_captured_logs_from_captured_logs(captured_logs)
            return True
        else:
            logger.warning("API returned empty captured_logs")
            return False
            
    except Exception as e:
        logger.error(f"Error retrieving logs via API: {e}")
        return False


def _display_captured_logs_from_captured_logs(captured_logs: dict):
    """
    Display all captured logs for custom agents (LangGraph)
    
    Args:
        captured_logs: The captured_logs dict from run_status['result']['data']['message']['additional_properties']['captured_logs']
    """
    try:
        log_id = captured_logs.get("log_id", "N/A")
        log_count = captured_logs.get("log_count", 0)
        entries = captured_logs.get("logs", [])

        console.print(f"\n[bold cyan]📝 Captured Logs (Log ID: {log_id}):[/bold cyan]")
        console.print("─" * 60)

        if not entries:
            logger.warning("No log entries found")
        else:
            for entry in entries:
                timestamp = entry.get("timestamp", "")
                level = entry.get("level", "INFO")
                log_message = entry.get("message", "")

                # Extract just the timestamp part (before the first " - ")
                if timestamp and " - " in timestamp:
                    formatted_time = timestamp.split(" - ")[0]
                else:
                    formatted_time = timestamp or "Unknown"

                # Color code by level
                level_color = LOG_LEVEL_COLORS.get(level.upper(), "white")

                console.print(f"[dim]{formatted_time}[/dim] [{level_color}]{level}[/{level_color}]: {log_message}")

        console.print("─" * 60)
        console.print(f"[cyan]Total log entries: {log_count}[/cyan]\n")

    except Exception as e:
        logger.error(f"Failed to display logs: {e}")


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
    
    if not isinstance(content, list): # After parsing, content should be a list. If not, something went wrong
        return False, str(content) if content is not None else "No response"

    for item in content:
        if isinstance(item, dict):
            response_type = item.get("response_type", "")

            # Check for widget/form response types that cannot be rendered in CLI
            if response_type in ["user_input", "form", "forms","disconnected_apps"]:
                has_widgets = True
    
    extracted_text = "\n".join(text_parts) if text_parts else str(content)
    return has_widgets, extracted_text

def _print_thinking_message(content_text: str, agent_name: str, thinking_messages: List[str]):
    """
    Display thinking intermediate message and collect it for programmatic access.

    Args:
        content_text: The text to be displayed
        agent_name: The agent name
        thinking_messages: List to append the thinking message to
    """
    thinking_messages.append(content_text)
    
    async_panel = Panel(
        content_text,
        title=f"💭 {agent_name} (Thinking...)",
        title_align="left",
        border_style="yellow",
        padding=(1, 2)
    )
    console.print(async_panel)

def _display_completed_response(
    threads_client: ThreadsClient,
    thread_id: str,
    include_reasoning: bool,
    agent_name: str,
    messages: Optional[list] = None,
    capture_logs: bool = False,
    run_status = None,
    return_agent_interaction_result: bool = False,
    thinking_messages: Optional[List[str]] = None
) -> Optional[AgentInteractionResult]:
    """
    Display the completed response from a non-async agent.
    
    Args:
        threads_client: The threads client instance
        thread_id: The thread ID to get messages from
        include_reasoning: Whether to include reasoning trace
        agent_name: Name of the agent for display
        messages: Optional pre-fetched messages list to avoid duplicate API calls
        capture_logs: Whether to display captured logs
        run_status: Optional run status containing log_id
        return_agent_interaction_result: If True, return AgentInteractionResult
        thinking_messages: List of thinking messages collected during interaction
    """
    # Get the final messages if not provided
    if messages is None:
        thread_messages_response = threads_client.get_thread_messages(thread_id)
        if isinstance(thread_messages_response, list):
            messages = thread_messages_response
        elif isinstance(thread_messages_response, dict) and "data" in thread_messages_response:
            messages = thread_messages_response["data"]
        else:
            messages = []
    
    final_message = None
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            final_message = msg
            break

    if final_message:
        content = final_message.get("content", "No response")
        
        # Extract text from structured content
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
            steps = final_message.get("step_history", [])
            if steps:
                reasoning_trace = {"steps": steps}
        
        # Display the message
        interaction_result = display_message("assistant", content, agent_name, include_reasoning, reasoning_trace, thread_id, return_agent_interaction_result, thinking_messages)
        
        # Display captured logs if capture_logs is enabled
        if capture_logs and run_status:
            try:
                embedded_logs = run_status.get('result', {}).get('data', {}).get('message', {}).get('additional_properties', {}).get('captured_logs')
                if embedded_logs:# Try to get logs from embedded run_status response (most efficient)
                    _display_captured_logs_from_captured_logs(embedded_logs)
                else: # Fallback to API call if embedded logs not found
                    api_success = _display_captured_logs_via_api(threads_client, run_status, final_message)
                    if not api_success:
                        logger.warning("Captured logs are only available for custom agents")
            except Exception as e:
                # Fallback to API call if extraction fails
                logger.warning(f"Error extracting embedded logs: {e}, falling back to API call")
                try:
                    api_success = _display_captured_logs_via_api(threads_client, run_status, final_message)
                    if not api_success:
                        logger.error("Both methods failed to retrieve logs")
                except Exception as api_error:
                    logger.error(f"Failed to retrieve logs via API: {api_error}")
        if return_agent_interaction_result:
            return interaction_result
    else:
        console.print("[yellow]No response received from agent[/yellow]")


def detect_file_upload_request(content) -> Optional[dict]:
    """
    Detect if the agent is requesting a file upload.
    
    Args:
        content: Message content (can be list or string)
        
    Returns:
        Dictionary with file upload details if detected, None otherwise
        Example: {
            "text": "Please upload the file you want to use : document_ref",
            "supported_formats": "CSV,DOC,DOCX,JPEG,PDF,PNG,WAV,XLS,XLSX,XLSM,PPT,PPTX",
            "size_limit": "10MB"
        }
    """
    if not isinstance(content, list):
        return None
    
    for item in content:
        if isinstance(item, dict) and item.get("response_type") == "file_upload":
            return {
                "text": item.get("text", "Please upload a file"),
                "supported_formats": item.get("supported_formats", ""),
                "size_limit": item.get("size_limit", "")
            }
    
    return None


def _detect_file_upload_request(content) -> Optional[dict]:
    """
    Wrapper for backward compatibility.
    Detect if the agent is requesting a file upload.
    
    Args:
        content: Message content (can be list or string)
        
    Returns:
        Dictionary with file upload details if detected, None otherwise
    """
    return detect_file_upload_request(content)


def _validate_file_format(file_path: str, supported_formats: str) -> tuple[bool, str]:
    """
    Validate if a file matches the supported formats.
    
    Args:
        file_path: Path to the file
        supported_formats: Comma-separated list of supported extensions (e.g., "PDF,DOCX,CSV")
        
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    
    if not os.path.isfile(file_path):
        return False, f"Path is not a file: {file_path}"
    
    # Get file extension
    _, ext = os.path.splitext(file_path)
    ext = ext.lstrip('.').upper()
    
    if supported_formats:
        formats_list = [f.strip().upper() for f in supported_formats.split(',')]
        if ext not in formats_list:
            return False, f"Unsupported file format: .{ext.lower()}. Supported formats: {supported_formats}"
    
    return True, "File format is valid"


def _prompt_for_file_upload(upload_request: dict) -> Optional[tuple[str, str]]:
    """
    Prompt user to provide a file path and optional message.
    
    Args:
        upload_request: Dictionary with file upload details in format as _detect_file_upload_request
        
    Returns:
        Tuple of (file_path, message) if user provides valid file, None if user cancels
    """
    console.print()
    console.print(Panel(
        f"[yellow]{upload_request['text']}[/yellow]\n\n"
        f"[cyan]Supported formats:[/cyan] {upload_request['supported_formats']}\n"
        f"[cyan]Size limit:[/cyan] {upload_request['size_limit']}",
        title="File Upload Required",
        title_align="left",
        border_style="yellow",
        padding=(1, 2)
    ))
    
    while True:
        file_path = Prompt.ask(
            "\n[bold cyan]Enter file path[/bold cyan] (or 'cancel' to skip)",
            default=""
        ).strip()
        
        if file_path.lower() == 'cancel' or not file_path:
            console.print("[yellow]File upload cancelled[/yellow]")
            return None
        
        # Remove quotes if present
        file_path = file_path.strip('"').strip("'")
        
        # Validate file format
        is_valid, message = _validate_file_format(file_path, upload_request['supported_formats'])
        
        if is_valid:
            # Ask for optional message - allow empty for file-only uploads
            user_message = Prompt.ask(
                "\n[bold cyan]Enter your message (optional)[/bold cyan] (e.g., 'summarize this', or press Enter to skip)",
                default=""
            ).strip()
            
            console.print(f"[green]✓[/green] File accepted: {file_path}")
            if user_message:
                console.print(f"[green]✓[/green] Message: {user_message}")
            else:
                console.print("[cyan]ℹ[/cyan] No message provided - sending file only")
            return file_path, user_message
        else:
            console.print(f"[red]✗ {message}[/red]")
            console.print("[yellow]Please try again or type 'cancel' to skip[/yellow]")


def _get_unique_filename(file_path: str) -> str:
    """
    Generate a unique filename by appending -1, -2, etc. if file already exists.
    
    Args:
        file_path: Original file path
        
    Returns:
        Unique file path that doesn't exist yet
        
    Example:
        output.docx -> output-1.docx -> output-2.docx
    """
    if not os.path.exists(file_path):
        return file_path
    
    # Split filename and extension
    directory = os.path.dirname(file_path)
    basename = os.path.basename(file_path)
    name, ext = os.path.splitext(basename)
    
    # Try appending -1, -2, -3, etc.
    counter = 1
    while True:
        new_name = f"{name}-{counter}{ext}"
        new_path = os.path.join(directory, new_name) if directory else new_name
        if not os.path.exists(new_path):
            return new_path
        counter += 1


def extract_downloadable_files(thread_messages_response) -> list:
    """
    Extract downloadable files from thread messages response.
    
    Args:
        thread_messages_response: Response from threads_client.get_thread_messages()
        
    Returns:
        List of file dictionaries with 'url', 'fileName', etc.
    """
    files_to_download = []
    seen_urls = set()  # Track URLs to avoid duplicates
    
    content_list = thread_messages_response
    if isinstance(content_list, list):
        for item in content_list:
            step_history = item.get("step_history", [])
            if step_history:
                for step in step_history:
                    step_details = step.get("step_details", [])
                    for detail in step_details:
                        if "content" in detail:
                            downloadable_content_str = detail["content"]
                            if not downloadable_content_str:
                                continue
                            try:
                                # Parse the JSON string to dictionary
                                downloadable_content = json.loads(downloadable_content_str) if isinstance(downloadable_content_str, str) else downloadable_content_str
                                
                                if isinstance(downloadable_content, dict) and downloadable_content.get("type") == "downloadable_file":
                                    file_url = downloadable_content.get("path", "")
                                    # Skip if we've already seen this URL (avoid duplicates)
                                    if file_url and file_url not in seen_urls:
                                        seen_urls.add(file_url)
                                        file_info = {
                                            "fileName": downloadable_content.get("filename", "downloaded_file"),
                                            "url": file_url,
                                            "id": "from_step_history",
                                            "statusCode": 200,
                                            "uploadStatus": "complete"
                                        }
                                        files_to_download.append(file_info)
                                        logger.info(f"Detected downloadable file: {file_info['fileName']}")
                            except (json.JSONDecodeError, TypeError, AttributeError) as e:
                                logger.debug(f"Could not parse content as JSON: {e}")
    
    return files_to_download


def _prompt_and_download_files(files: list) -> None:
    """
    Prompt user to download files (can be more than one) returned by the agent.
    
    Args:
        files: List of file dictionaries with 'url', 'fileName', etc.
        
    Example file structure:
        {
            'id': 'dummy_id',
            'url': 'http://localhost:9000/wxo-server-storage-bucket/.../output.docx',
            'fileName': 'output.docx',
            'statusCode': 200,
            'uploadStatus': 'complete',
            'urlExpiryTime': '4926569109'
        }
    """
    if not files:
        return
    
    console.print()
    console.print(Panel(
        f"[green]The agent has generated {len(files)} file(s) for download[/green]",
        title="📥 Files Available",
        title_align="left",
        border_style="green",
        padding=(1, 2)
    ))
    
    for idx, file_info in enumerate(files, 1):
        file_name = file_info.get('fileName', f'file_{idx}')
        file_url = file_info.get('url', '')
        
        if not file_url:
            console.print(f"[yellow]⚠ File {idx}: {file_name} - No download URL available[/yellow]")
            continue
        
        console.print(f"\n[cyan]File {idx}:[/cyan] {file_name}")
        
        # Ask user where to save the file
        download_choice = Prompt.ask(
            f"[bold cyan]Download this file?[/bold cyan]",
            choices=["yes", "no", "cancel"],
            default="yes"
        )
        
        if download_choice == "cancel":
            console.print("[yellow]Download cancelled[/yellow]")
            break
        elif download_choice == "no":
            console.print(f"[yellow]Skipped {file_name}[/yellow]")
            continue
        
        # Ask for save location
        save_path = Prompt.ask(
            f"[bold cyan]Enter save path[/bold cyan] (or press Enter for current directory)",
            default=file_name
        ).strip()
        
        # Remove quotes if present
        save_path = save_path.strip('"').strip("'")
        
        if os.path.isdir(save_path): # If user gives directory then append the default filename
            save_path = os.path.join(save_path, file_name)
            console.print(f"[cyan]Saving to directory as: {save_path}[/cyan]")
        
        # Check if file exists and generate unique filename if needed
        if os.path.exists(save_path):
            save_path = _get_unique_filename(save_path)
            console.print(f"[yellow]File exists, saving as: {os.path.basename(save_path)}[/yellow]")
        
        # Download the file
        try:
            console.print(f"[cyan]Downloading {file_name}...[/cyan]")
            response = requests.get(file_url, timeout=30)
            response.raise_for_status()
            
            # Write to file
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            console.print(f"[green]✓ Downloaded successfully to: {save_path}[/green]")
            
        except requests.exceptions.RequestException as e:
            console.print(f"[red]✗ Failed to download {file_name}: {e}[/red]")
            logger.error(f"File download error: {e}", exc_info=True)
        except IOError as e:
            console.print(f"[red]✗ Failed to save {file_name}: {e}[/red]")
            logger.error(f"File save error: {e}", exc_info=True)
    
    console.print()


def _show_widget_warning():
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


def _poll_and_display_async_messages(
    threads_client: ThreadsClient,
    thread_id: str,
    initial_message_count: int,
    agent_name: str,
    poll_interval: int = 1,
    thinking_messages: Optional[List[str]] = None,
    return_agent_interaction_result: bool = False
) -> Optional[dict]:
    """
    Poll for flow completion and display async messages as they arrive.
    
    Args:
        threads_client: The threads client instance
        thread_id: The thread ID to poll
        initial_message_count: Number of messages before the flow started
        agent_name: Name of the agent for display
        poll_interval: Seconds between polling attempts
        thinking_messages: List to collect thinking messages
        
    Returns:
        The final message dict (with is_async=false), or None if not found
    """
    if thinking_messages is None:
        thinking_messages = []
    
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
                                if return_agent_interaction_result:
                                    # For MCP/API: Return None to signal widget detected
                                    # The caller will handle creating the error result
                                    return None
                                else:
                                    # For CLI: Show warning and exit
                                    _show_widget_warning()
                                    os._exit(0)
                            
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
                                _print_thinking_message(content_text, agent_name, thinking_messages)
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
    

async def _execute_agent_interaction_websocket(
    run_client: RunClient,
    threads_client: ThreadsClient,
    message: str,
    agent_id: str,
    include_reasoning: bool,
    agent_name: str,
    thread_id: Optional[str] = None,
    capture_logs: bool = False,
    return_agent_interaction_result: bool = False
) -> Optional[str] | Optional[AgentInteractionResult]:
    """
    Execute agent interaction using WebSocket approach.
    
    Flow:
    1. Create run and start WebSocket immediately
    2. Wait for run completion to get first message with is_async flag
    3. If is_async=true: Wait for WebSocket flow events
    4. If is_async=false: Display HTTP response and close WebSocket
    
    Args:
        return_agent_interaction_result: If True, returns AgentInteractionResult for API/MCP usage (non-interactive mode).
                      If False, returns thread_id for CLI usage (interactive mode with prompts).
    
    Returns thread_id on success, None if widget detected or error occurred.
    """
    # Initialize thinking messages list for this interaction
    thinking_messages: List[str] = []
    try:
        # Step 1: Send the message via HTTP
        run_response = run_client.create_run(
            message=message,
            agent_id=agent_id,
            thread_id=thread_id,
            capture_logs=capture_logs
        )
        
        thread_id = run_response["thread_id"]
        run_id = run_response["run_id"]
        
        # Step 2: Wait for run completion to get the first message with is_async flag
        with console.status("[bold green]Waiting for response...", spinner="dots"):
            run_status = run_client.wait_for_run_completion(run_id)
        
        # Check for errors
        if run_status.get("status") == "failed":
            error_msg = run_status.get("error", "Unknown error")
            console.print(f"[red]Error: {error_msg}[/red]")
            logger.error(f"Run failed with status: {run_status}")
            return None
        
        # Step 3: Get the first message and check is_async flag
        thread_messages_response = threads_client.get_thread_messages(thread_id)
        if isinstance(thread_messages_response, list):
            messages = thread_messages_response
        elif isinstance(thread_messages_response, dict) and "data" in thread_messages_response:
            messages = thread_messages_response["data"]
        else:
            messages = []

        first_message = None
        is_async_agent = False
        
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                first_message = msg
                
                # Check the is_async flag
                additional_props = msg.get("additional_properties", {})
                display_props = additional_props.get("display_properties") if additional_props else None
                is_async_agent = display_props.get("is_async", False) if display_props else False
                
                logger.info(f"First message is_async flag: {is_async_agent}")
                break
        
        # Step 4: Check if agent is requesting file upload and widget detection
        if first_message:
            content = first_message.get("content", [])
            file_upload_request = _detect_file_upload_request(content)
            
            if file_upload_request:
                # Agent needs a file
                logger.info("File upload requested by agent")
                
                # In non-interactive mode (MCP/API), don't prompt - just return the result
                if return_agent_interaction_result:
                    # For MCP/API: Return result with file upload request info
                    # The caller will handle getting the file from the user
                    logger.info("Non-interactive mode: returning result with file upload request")
                    _, extracted_text = _check_for_widgets_and_extract_text(content)
                    return AgentInteractionResult(
                        thread_id=thread_id,
                        final_message=extracted_text,
                        reasoning_trace=None,
                        thinking_trace=thinking_messages,
                        status="success",
                        error=None
                    )
                
                # In interactive mode (CLI), prompt user for file
                file_info = _prompt_for_file_upload(file_upload_request)
                
                if file_info is None:
                    # User cancelled
                    console.print("[yellow]Conversation ended - file upload required but cancelled[/yellow]")
                    return thread_id
                
                file_path, user_message = file_info
                
                # Upload file to S3
                console.print("[cyan]Uploading file...[/cyan]")
                try:
                    file_urls = run_client.upload_file_to_s3(file_path, user_message)
                    console.print(f"[green]✓ File uploaded successfully[/green]")
                    
                    # Send message with file attachment
                    console.print(f"[cyan]Sending message with file attachment...[/cyan]")
                    run_response = run_client.create_run_with_files(
                        message=user_message,
                        file_urls=file_urls,
                        agent_id=agent_id,
                        thread_id=thread_id
                    )
                    
                    # Update thread_id and run_id for the new run
                    thread_id = run_response["thread_id"]
                    run_id = run_response["run_id"]
                    
                    # Wait for this new run to complete
                    with console.status("[bold green]Processing file...", spinner="dots"):
                        run_status = run_client.wait_for_run_completion(run_id)
                    
                    if run_status.get("status") == "failed":
                        error_msg = run_status.get("error", "Unknown error")
                        console.print(f"[red]Error: {error_msg}[/red]")
                        return thread_id
                    
                    # Get the response after file processing
                    thread_messages_response = threads_client.get_thread_messages(thread_id)
                    
                    if isinstance(thread_messages_response, list):
                        messages = thread_messages_response
                    elif isinstance(thread_messages_response, dict) and "data" in thread_messages_response:
                        messages = thread_messages_response["data"]
                    else:
                        messages = []
                    
                    # Check for file downloads in the response
                    files_to_download = extract_downloadable_files(thread_messages_response)
                    # Prompt user to download files if any were found
                    if files_to_download:
                        logger.info(f"Total {len(files_to_download)} downloadable file(s) detected")
                        _prompt_and_download_files(files_to_download)
                        # File download complete, return thread_id
                        return thread_id

                    # Check if this triggered an async flow
                    for msg in reversed(messages):
                        if isinstance(msg, dict) and msg.get("role") == "assistant":
                            additional_props = msg.get("additional_properties", {})
                            display_props = additional_props.get("display_properties") if additional_props else None
                            is_async_agent = display_props.get("is_async", False) if display_props else False
                            break
                    
                    # If not async after file upload, display result and return
                    if not is_async_agent:
                        interaction_result = _display_completed_response(threads_client, thread_id, include_reasoning, agent_name, messages, return_agent_interaction_result=return_agent_interaction_result, thinking_messages=thinking_messages)
                        if return_agent_interaction_result:
                            return interaction_result
                        return thread_id
                    
                    # Otherwise continue to WebSocket handling below
                    
                except Exception as e:
                    console.print(f"[red]Error uploading file: {e}[/red]")
                    logger.error(f"File upload error: {e}", exc_info=True)
                    if return_agent_interaction_result:
                        interaction_result = AgentInteractionResult(
                            status="error",
                            final_message=None,
                            thinking_trace=thinking_messages.copy(),
                            reasoning_trace=None,
                            thread_id=thread_id,
                            error=str(e)
                        )
                        return interaction_result

                    return thread_id
            # widget detection
            has_widgets, _= _check_for_widgets_and_extract_text(content)
            if has_widgets:
                if return_agent_interaction_result:
                    return AgentInteractionResult(
                        status="error",
                        final_message=None,
                        thinking_trace=thinking_messages.copy() if thinking_messages else [],
                        reasoning_trace=None,
                        thread_id=thread_id,
                        error="Widget detected: This agent requires interactive UI elements that cannot be rendered in this context. Please use the full UI experience."
                    )
                else:
                    _show_widget_warning()
                    os._exit(0)

        # Step 5: Route based on is_async flag
        if not is_async_agent:
            # Non-async agent: Display the response we already have
            logger.info("Non-async agent - displaying HTTP response")
            interaction_result = _display_completed_response(threads_client, thread_id, include_reasoning, agent_name, messages, capture_logs, run_status, return_agent_interaction_result=return_agent_interaction_result, thinking_messages=thinking_messages)
            if return_agent_interaction_result:
                return interaction_result
            return thread_id
        
        # Step 6: Async/flow agent - use WebSocket for real-time updates
        logger.info("Async/flow agent (is_async=true) - waiting for WebSocket events")
        
        # Initialize reasoning_trace
        reasoning_trace = None
        if first_message and include_reasoning:
            steps = first_message.get("step_history", [])
            if steps:
                reasoning_trace = {"steps": steps}

        # Track intermediate messages and capture final message from WebSocket
        final_ws_message = None  # Will store the final message.created event
        form_detected = False  # Flag to track if form was detected
        
        def handle_intermediate(event_data, agent_name):
            """
            Handle intermediate thinking/progress messages and slot.input events.
            
            Event types:
            1. run.step.intermediate: {"data": {"message": {"text": "...", "key": "..."}}}
            2. slot.input: {"data": {"message": {"content": [{"text": "int_out: 123"}]}}}
            """
            # Extract event type and data
            event_type = event_data.get("event", "")
            data = event_data.get("data", {})
            
            # Handle slot.input events (flow output messages)
            if event_type == "slot.input":
                # Path: data.message.content[].text
                message_obj = data.get("message", {})
                content_list = message_obj.get("content", [])
                
                # Check for forms in the content using _check_for_widgets_and_extract_text
                has_widgets, extracted_text = _check_for_widgets_and_extract_text(content_list)
                if has_widgets:
                    nonlocal form_detected
                    form_detected = True
                    if not return_agent_interaction_result:
                        _show_widget_warning()
                        os._exit(0)
                    return  # Exit the handler, will be caught by the outer function

                # Extract all text from content items and display as intermediate messages
                for content_item in content_list:
                    if isinstance(content_item, dict):
                        text = content_item.get("text", "")
                        if text:
                            _print_thinking_message(text, agent_name, thinking_messages)

                return
            return
        
        def handle_message(msg_data):
            """
            Handle message.created events from WebSocket.
            Capture the final message (with is_async=false) for display.
            Keep updating to get the LAST non-async message with substantial content.
            """
            nonlocal final_ws_message
            
            event_type = msg_data.get("event", "")
            if event_type == "message.created":
                data = msg_data.get("data", {})
                message = data.get("message", {})
                
                # Check if this is the final message (is_async=false)
                additional_props = message.get("additional_properties", {})
                display_props = additional_props.get("display_properties") if additional_props else None
                is_async = display_props.get("is_async", False) if display_props else False
                
                # Keep updating to capture the LAST non-async message
                # This ensures we get the final result, not intermediate status messages
                if not is_async:
                    final_ws_message = message
                    logger.info(f"Captured final message from WebSocket (message.created with is_async=false)")
            return

        def handle_complete(status):
            """Handle run completion."""
            return
        
        def handle_error(error_msg):
            """Handle run error."""
            console.print(f"[red]Error: {error_msg}[/red]")
        
        # Stream via WebSocket
        with console.status("[bold green]Waiting for response...", spinner="dots") as status:
            try:
                # Create a task for WebSocket streaming
                stream_task = asyncio.create_task(
                    run_client.stream_run_with_websocket(
                        agent_id=agent_id,
                        thread_id=thread_id,
                        run_id=run_id,
                        on_message=handle_message,
                        on_intermediate=lambda event_data: handle_intermediate(event_data, agent_name),
                        on_complete=handle_complete,
                        on_error=handle_error
                    )
                )
                
                # Wait for either completion or form detection
                while not stream_task.done():
                    if form_detected:
                        # Form detected - cancel the stream task and exit
                        stream_task.cancel()
                        try:
                            await stream_task
                        except asyncio.CancelledError:
                            pass
                        logger.info("Form detected - stopping WebSocket stream")
                        
                        if return_agent_interaction_result:
                            # For MCP/API: Return error result
                            return AgentInteractionResult(
                                status="error",
                                final_message=None,
                                thinking_trace=thinking_messages.copy() if thinking_messages else [],
                                reasoning_trace=None,
                                thread_id=thread_id,
                                error="Widget detected: This agent requires interactive UI elements that cannot be rendered in this context. Please use the full UI experience."
                            )
                        return  # Exit the function early for CLI
                    await asyncio.sleep(0.1)
                
                # Get the result if task completed normally
                final_status = await stream_task
                
            except Exception as ws_error:
                logger.warning(f"WebSocket streaming failed: {ws_error}, falling back to HTTP polling")
                raise  # Re-raise to trigger fallback
        
        # Use the final message captured from WebSocket if available
        # Otherwise fall back to HTTP API
        final_message = None
        
        if final_ws_message:
            logger.info("Using final message captured from WebSocket")
            final_message = final_ws_message
        else: # Fall back to HTTP API
            logger.info("No final message from WebSocket, fetching via HTTP API")
            thread_messages_response = threads_client.get_thread_messages(thread_id)
            if isinstance(thread_messages_response, list):
                messages = thread_messages_response
            elif isinstance(thread_messages_response, dict) and "data" in thread_messages_response:
                messages = thread_messages_response["data"]
            else:
                messages = []
            
            # Find the most recent assistant message with is_async=false (the final response)
            # If no such message exists, fall back to the most recent assistant message
            final_non_async_message = None
            final_any_message = None
            
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    # Keep track of the most recent assistant message as fallback
                    if final_any_message is None:
                        final_any_message = msg
                    
                    # Check if this is a non-async (final) message
                    additional_props = msg.get("additional_properties", {})
                    display_props = additional_props.get("display_properties") if additional_props else None
                    is_async = display_props.get("is_async", False) if display_props else False
                    
                    # If we find a non-async message, that's our final message
                    if not is_async:
                        final_non_async_message = msg
                        break
            
            # Prefer the non-async message if found, otherwise use any assistant message
            final_message = final_non_async_message if final_non_async_message else final_any_message
        
        if final_message:
            content = final_message.get("content", "No response")

            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("response_type") == "text":
                            text_parts.append(item.get("text", ""))
                        elif "text" in item:
                            text_parts.append(item["text"])
                content = "\n".join(text_parts) if text_parts else str(content)
            
            if include_reasoning and not reasoning_trace: # Try to get step_history from final_message if not already set
                steps = final_message.get("step_history", [])
                if steps:
                    reasoning_trace = {"steps": steps}
                
                if not reasoning_trace: # If still no reasoning trace, fetch via run_id
                    try:
                        run_status = run_client.get_run_status(run_id)
                        if run_status and run_status.get("log_id"):
                            log_id = run_status["log_id"]
                            try:
                                reasoning_trace = threads_client.get_logs_by_log_id(log_id)
                            except Exception as e:
                                logger.error(f"Could not retrieve reasoning trace via log_id: {e}")
                        elif run_status and "result" in run_status:
                            try:
                                step_history = run_status.get("result", {}).get("data", {}).get("message", {}).get("step_history")
                                if step_history:
                                    reasoning_trace = {"steps": step_history}
                            except (KeyError, TypeError, AttributeError):
                                pass
                    except Exception as e:
                        logger.warning(f"Could not fetch run status for reasoning trace: {e}")
            
            # Check for widgets in final content
            has_widgets, content = _check_for_widgets_and_extract_text(content)
            if has_widgets:
                if return_agent_interaction_result:
                    # For MCP/API: Return error result instead of exiting
                    return AgentInteractionResult(
                        status="error",
                        final_message=content,
                        thinking_trace=thinking_messages.copy() if thinking_messages else [],
                        reasoning_trace=reasoning_trace,
                        thread_id=thread_id,
                        error="Widget detected: This agent requires interactive UI elements that cannot be rendered in this context. Please use the full UI experience."
                    )
                else:
                    # For CLI: Show warning and exit
                    _show_widget_warning()
                    os._exit(0)
            
            interaction_result = display_message("assistant", content, agent_name, include_reasoning, reasoning_trace, thread_id, return_agent_interaction_result, thinking_messages)
            
            # Display captured logs if capture_logs is enabled
            if capture_logs and run_status:
                try:
                    embedded_logs = run_status.get('result', {}).get('data', {}).get('message', {}).get('additional_properties', {}).get('captured_logs')
                    if embedded_logs:  # Try to get logs from embedded run_status response (most efficient)
                        _display_captured_logs_from_captured_logs(embedded_logs)
                    else:  # Fallback to API call if embedded logs not found
                        api_success = _display_captured_logs_via_api(threads_client, run_status, final_message)
                        if not api_success:
                            logger.warning("Note: Captured logs are only available for custom agents")
                except Exception as e:
                    # Fallback to API call if extraction fails
                    logger.warning(f"Error extracting embedded logs: {e}, falling back to API call")
                    try:
                        api_success = _display_captured_logs_via_api(threads_client, run_status, final_message)
                        if not api_success:
                            logger.error("Both methods failed to retrieve logs")
                    except Exception as api_error:
                        logger.error(f"Failed to retrieve logs via API: {api_error}")
            if return_agent_interaction_result:
                return interaction_result
        else:
            console.print("[yellow]No response from assistant[/yellow]")
            if return_agent_interaction_result:
                # Return error result if no response
                interaction_result = AgentInteractionResult(
                    status="error",
                    final_message=None,
                    thinking_trace=thinking_messages.copy(),
                    reasoning_trace=None,
                    thread_id=thread_id,
                    error="No response from assistant"
                )
                return interaction_result
        
        return thread_id
        
    except Exception as e:
        logger.error(f"Error in WebSocket interaction: {e}", exc_info=True)
        raise  # Re-raise to trigger HTTP fallback


def _execute_agent_interaction(run_client: RunClient, threads_client: ThreadsClient, message: str, agent_id: str, include_reasoning: bool, agent_name: str, thread_id: Optional[str] = None,
                                capture_logs: bool = False, return_agent_interaction_result: bool = False) -> Optional[str] | Optional[AgentInteractionResult]:
    """
    Execute agent interaction: send message, wait for response, display answer, and return thread_id to keep the conversation context in interactive mode.
    
    Args:
        return_agent_interaction_result: If True, returns tuple of (thread_id, AgentInteractionResult)
    
    Returns:
        thread_id on success (if return_agent_interaction_result=False), None if widget detected or error occurred.
        OR AgentInteractionResult if return_agent_interaction_result=True
    """
    # Initialize thinking messages list for this interaction
    thinking_messages: List[str] = []
    
    try:
        run_response = run_client.create_run(
            message=message,
            agent_id=agent_id,
            thread_id=thread_id,
            capture_logs=capture_logs
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
                        if return_agent_interaction_result:
                            # For MCP/API: Return error result
                            return AgentInteractionResult(
                                status="error",
                                final_message=None,
                                thinking_trace=thinking_messages.copy() if thinking_messages else [],
                                reasoning_trace=None,
                                thread_id=thread_id,
                                error="Widget detected: This agent requires interactive UI elements that cannot be rendered in this context. Please use the full UI experience."
                            )
                        else:
                            # For CLI: Show warning and exit
                            _show_widget_warning()
                            os._exit(0)
                
                # Now wait for flow completion and display async messages as they arrive
                flow_completion_message = _poll_and_display_async_messages(
                    threads_client, thread_id, initial_message_count, agent_name, thinking_messages=thinking_messages, return_agent_interaction_result=return_agent_interaction_result
                )
                
                # If None was returned, it means a widget was detected
                if flow_completion_message is None:
                    if return_agent_interaction_result:
                        # For MCP/API: Return error result
                        return AgentInteractionResult(
                            status="error",
                            final_message=None,
                            thinking_trace=thinking_messages.copy() if thinking_messages else [],
                            reasoning_trace=None,
                            thread_id=thread_id,
                            error="Widget detected: This agent requires interactive UI elements that cannot be rendered in this context. Please use the full UI experience."
                        )
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
                if return_agent_interaction_result:
                    # For MCP/API: Return error result
                    return AgentInteractionResult(
                        status="error",
                        final_message=content,
                        thinking_trace=thinking_messages.copy() if thinking_messages else [],
                        reasoning_trace=reasoning_trace,
                        thread_id=thread_id,
                        error="Widget detected: This agent requires interactive UI elements that cannot be rendered in this context. Please use the full UI experience."
                    )
                else:
                    # For CLI: Show warning and exit
                    _show_widget_warning()
                    os._exit(0)
                
            interaction_result = display_message("assistant", content, agent_name, include_reasoning, reasoning_trace, thread_id, return_agent_interaction_result, thinking_messages)
            
            if capture_logs and run_status:
                try:
                    embedded_logs = run_status.get('result', {}).get('data', {}).get('message', {}).get('additional_properties', {}).get('captured_logs')
                    if embedded_logs:# Try to get logs from embedded run_status response (most efficient)
                        _display_captured_logs_from_captured_logs(embedded_logs)
                    else: # Fallback to API call if embedded logs not found
                        api_success = _display_captured_logs_via_api(threads_client, run_status, final_message)
                        if not api_success:
                            logger.warning("Captured logs are only available for custom agents")
                except Exception as e:
                    # Fallback to API call if extraction fails
                    logger.warning(f"Error extracting embedded logs: {e}, falling back to API call")
                    try:
                        api_success = _display_captured_logs_via_api(threads_client, run_status, final_message)
                        if not api_success:
                            logger.error("Both methods failed to retrieve logs")
                    except Exception as api_error:
                        logger.error(f"Failed to retrieve logs via API: {api_error}")
            if return_agent_interaction_result:
                return interaction_result
        else:
            console.print("[yellow]No response from assistant[/yellow]")
        return thread_id

    except Exception as e:
        logger.error(f"Error in _execute_agent_interaction: {e}", exc_info=True)
        raise e


async def execute_agent_interaction_with_fallback_async(
    run_client: RunClient,
    threads_client: ThreadsClient,
    message: str,
    agent_id: str,
    include_reasoning: bool,
    agent_name: str,
    thread_id: Optional[str] = None,
    capture_logs: bool = False,
    return_agent_interaction_result: bool = False
) -> Optional[str] | Optional[AgentInteractionResult]:
    """
    Async version: Execute agent interaction with automatic WebSocket/HTTP fallback.
    
    Use this version when calling from an async context (e.g., MCP server).
    
    Args:
        return_agent_interaction_result: If True, returns AgentInteractionResult
    
    Returns:
        thread_id on success (if return_agent_interaction_result=False), None if widget detected or error occurred.
        OR AgentInteractionResult if return_agent_interaction_result=True
    """
    
    
    # Use WebSocket approach - await directly since we're already async
    try:
        result = await _execute_agent_interaction_websocket(
            run_client, threads_client, message, agent_id,
            include_reasoning, agent_name, thread_id, capture_logs, return_agent_interaction_result
        )
        return result
            
    except Exception as e:
        logger.error(f"Error in WebSocket execution ({type(e).__name__}), falling back to HTTP polling")
    
    # Fallback to HTTP polling
    return _execute_agent_interaction(
        run_client, threads_client, message, agent_id,
        include_reasoning, agent_name, thread_id, capture_logs, return_agent_interaction_result
    )


def execute_agent_interaction_with_fallback(
    run_client: RunClient,
    threads_client: ThreadsClient,
    message: str,
    agent_id: str,
    include_reasoning: bool,
    agent_name: str,
    thread_id: Optional[str] = None,
    capture_logs: bool = False,
    return_agent_interaction_result: bool = False
) -> Optional[str] | Optional[AgentInteractionResult]:
    """
    Sync version: Execute agent interaction with automatic WebSocket/HTTP fallback.
    
    Use this version when calling from a sync context.
    
    Args:
        return_agent_interaction_result: If True, returns AgentInteractionResult
    
    Returns:
        thread_id on success (if return_agent_interaction_result=False), None if widget detected or error occurred.
        OR AgentInteractionResult if return_agent_interaction_result=True
    """
    
    # Use WebSocket approach (like UI does) - always start WebSocket, then check is_async flag
    try:
        result = asyncio.run(_execute_agent_interaction_websocket(
            run_client, threads_client, message, agent_id,
            include_reasoning, agent_name, thread_id, capture_logs, return_agent_interaction_result
        ))
        return result
    except RuntimeError as e:
        # RuntimeError typically means we're already in an async context
        logger.error(f"Cannot use asyncio.run() in async context. Use execute_agent_interaction_with_fallback_async instead.")
        raise
    except Exception as e:
        logger.error(f"Error in WebSocket execution ({type(e).__name__}), falling back to HTTP polling")
    
    # Fallback to HTTP polling
    return _execute_agent_interaction(
        run_client, threads_client, message, agent_id,
        include_reasoning, agent_name, thread_id, capture_logs, return_agent_interaction_result
    )


def chat_ask_interactive(
    agent_name: str,
    include_reasoning: bool,
    initial_message: Optional[str] = None,
    capture_logs: bool = False,
    thread_id: Optional[str] = None
):
    """Interactive chat mode. If initial_message is provided, it's sent automatically first and then opens the chat."""
    # convert the agent name to agent id which runclient understands
    agent_id = get_agent_id_by_name(agent_name)

    run_client = create_run_client()
    threads_client = create_threads_client()
    
    # Only show thread_id info if explicitly provided via command line
    if thread_id:
        logger.info(f"Continuing conversation with thread ID: {thread_id}")
        
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
        thread_id = execute_agent_interaction_with_fallback(
            run_client, threads_client, initial_message, agent_id, include_reasoning, agent_name, thread_id, capture_logs
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
                if thread_id:
                    if isinstance(thread_id,AgentInteractionResult):
                        thread_id=thread_id.thread_id
                    console.print(Panel(
                        f"[bold green]Thread ID:[/bold green] {thread_id}\n\n"
                        "Save this ID to continue this conversation later using:\n"
                        f"[cyan]orchestrate chat ask --agent-name {agent_name} --thread-id {thread_id}[/cyan]",
                        title="💾 Save Your Conversation",
                        border_style="green"
                    ))
                break

            if not user_input.strip():
                continue
            
            # Display user message
            display_message("user", user_input, agent_name=agent_name)

            # execute the whole agent interaction with WebSocket/HTTP fallback
            thread_id = execute_agent_interaction_with_fallback(
                run_client, threads_client, user_input, agent_id,
                include_reasoning, agent_name, thread_id, capture_logs
            )
            if thread_id is None: # Widget was detected or error occurred, exit chat
                break
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]Exiting chat...[/yellow]")
            if thread_id:
                if isinstance(thread_id,AgentInteractionResult):
                    thread_id=thread_id.thread_id
                console.print(Panel(
                    f"[bold green]Thread ID:[/bold green] {thread_id}\n\n"
                    "Save this ID to continue this conversation later using:\n"
                    f"[cyan]orchestrate chat ask --agent-name {agent_name} --thread-id {thread_id}[/cyan]",
                    title="💾 Save Your Conversation",
                    border_style="green"
                ))
            break
        except Exception as e:
            logger.error(f"Error during chat: {e}")
            console.print(f"[red]Error: {e}[/red]")
            continue
