#!/usr/bin/env python3
"""
Flow Callback Handler Tester - Interactive CLI

This script provides an interactive CLI to test the flow callback handler by:
1. Sending example flow events to the handler
2. Retrieving stored events from the AstraDB table

Usage:
    python flow_callback_tester.py
"""

import json
import os
import sys
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

# Suppress AstraDB Data API warnings about sorting and filtering
warnings.filterwarnings("ignore", category=UserWarning, module="astrapy")

# Add the tools directory to the path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "tools"))

from astrapy import DataAPIClient


# ANSI color codes for better UX
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print a colored header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.ENDC}\n")


def print_success(text: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print an error message."""
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.ENDC}")


def load_env():
    """Load environment variables from .env file."""
    env_file = SCRIPT_DIR / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, _, value = line.partition('=')
                    os.environ[key.strip()] = value.strip()


def get_astra_credentials() -> tuple[str, str, str]:
    """Get AstraDB credentials from environment variables."""
    api_token = os.getenv("ASTRA_TOKEN")
    api_endpoint = os.getenv("ASTRA_URL")
    keyspace = os.getenv("ASTRA_KEYSPACE", "default_keyspace")
    
    if not api_token:
        raise ValueError("ASTRA_TOKEN not set. Please configure your .env file.")
    if not api_endpoint:
        raise ValueError("ASTRA_URL not set. Please configure your .env file.")
    
    return api_token, api_endpoint, keyspace


def generate_instance_id() -> str:
    """Generate a random UUID-based instance ID."""
    return f"flow-inst-{uuid.uuid4().hex[:12]}"


def get_input(prompt: str, default: Optional[str] = None) -> str:
    """Get user input with optional default value."""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    value = input(prompt).strip()
    return value if value else (default or "")


def get_choice(prompt: str, options: List[str], allow_quit: bool = False) -> str:
    """Get user choice from a list of options."""
    print(f"\n{prompt}")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    
    if allow_quit:
        prompt_text = f"\nEnter choice (1-{len(options)}, or 'q' to quit): "
    else:
        prompt_text = f"\nEnter choice (1-{len(options)}): "
    
    while True:
        try:
            choice = input(prompt_text).strip().lower()
            
            # Check for quit
            if allow_quit and choice == 'q':
                return ""
            
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
            print_error(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            if allow_quit:
                print_error("Please enter a valid number or 'q' to quit")
            else:
                print_error("Please enter a valid number")
        except KeyboardInterrupt:
            print("\n")
            return ""


def send_test_event_interactive():
    """Interactive flow to send a test event."""
    print_header("Send Test Event")
    
    # Select event type
    event_types = [
        "flow:on_flow_start",
        "flow:on_flow_end",
        "flow:on_flow_error",
        "task:on_task_wait",
        "task:on_task_error",
        "task:on_task_message"
    ]
    
    event_type = get_choice("Select event type:", event_types)
    if not event_type:
        return
    
    print()
    
    # Get instance ID
    default_instance_id = generate_instance_id()
    instance_id = get_input("Instance ID", default_instance_id)
    
    # Get flow details
    flow_name = get_input("Flow name", "Test Flow")
    flow_id = get_input("Flow ID", f"flow-{uuid.uuid4().hex[:8]}")
    
    # Get task details if it's a task event
    task_id = None
    task_name = None
    task_display_name = None
    assignee = None
    
    if event_type.startswith("task:"):
        print(f"\n{Colors.BOLD}Task Details:{Colors.ENDC}")
        task_id = get_input("Task ID", f"task-{uuid.uuid4().hex[:8]}")
        task_name = get_input("Task name", "test_task")
        task_display_name = get_input("Task display name", "Test Task")
        assignee = get_input("Assignee", "test@example.com")
    
    # Get error details if it's an error event
    error = None
    if "error" in event_type:
        print(f"\n{Colors.BOLD}Error Details:{Colors.ENDC}")
        error_message = get_input("Error message", "Test error occurred")
        error_code = get_input("Error code", "TEST_ERROR")
        if error_message:
            error = {"message": error_message, "code": error_code}
    
    # Get optional metadata
    print(f"\n{Colors.BOLD}Optional Metadata:{Colors.ENDC}")
    add_metadata_input = input("Add custom metadata? (y/N): ").strip().lower()
    add_metadata = "Yes" if add_metadata_input in ['y', 'yes'] else "No"
    
    metadata = None
    context_data = None
    
    if add_metadata == "Yes":
        metadata_key = get_input("Metadata key", "test_key")
        metadata_value = get_input("Metadata value", "test_value")
        if metadata_key:
            metadata = {metadata_key: metadata_value}
        
        context_key = get_input("Context data key", "test_context")
        context_value = get_input("Context data value", "test_data")
        if context_key:
            context_data = {context_key: context_value}
    
    # Send the event
    print(f"\n{Colors.BOLD}Sending event...{Colors.ENDC}")
    
    try:
        result = send_test_event(
            event_type=event_type,
            instance_id=instance_id,
            task_id=task_id,
            flow_id=flow_id,
            flow_name=flow_name,
            task_name=task_name,
            task_display_name=task_display_name,
            assignee=assignee,
            context_data=context_data,
            metadata=metadata,
            error=error
        )
        
        print_success("Event sent successfully!")
        print(f"   Event ID: {result['event_id']}")
        print(f"   Instance ID: {result['instance_id']}")
        
        # Ask if user wants to retrieve the event
        retrieve = get_choice("\nRetrieve this event to verify?", ["No", "Yes"])
        if retrieve == "Yes":
            print()
            retrieve_events_interactive(default_instance_id=instance_id)
            
    except Exception as e:
        print_error(f"Failed to send event: {e}")


def send_batch_events_interactive():
    """Interactive flow to build and send a batch of events."""
    print_header("Send Batch of Events")
    
    events_batch = []
    instance_id = generate_instance_id()  # Use same instance for all events in batch
    
    print_info(f"Building batch with instance ID: {instance_id}")
    print_info("You can add multiple events to the batch before sending them all together.")
    print()
    
    while True:
        print(f"\n{Colors.BOLD}Current batch: {len(events_batch)} event(s){Colors.ENDC}")
        
        if events_batch:
            print(f"{Colors.CYAN}Events in batch:{Colors.ENDC}")
            for i, evt in enumerate(events_batch, 1):
                print(f"  {i}. {evt['event_kind']} - {evt.get('task_name', 'N/A')}")
        
        print()
        batch_options = [
            "Add event to batch",
            "Send batch",
            "Clear batch",
            "Cancel"
        ]
        
        choice = get_choice("What would you like to do?", batch_options)
        
        if choice == "Cancel":
            return
        elif choice == "Clear batch":
            events_batch = []
            print_success("Batch cleared")
            continue
        elif choice == "Send batch":
            if not events_batch:
                print_warning("Batch is empty. Add at least one event first.")
                continue
            break
        elif choice == "Add event to batch":
            # Select event type
            event_types = [
                "flow:on_flow_start",
                "flow:on_flow_end",
                "flow:on_flow_error",
                "task:on_task_wait",
                "task:on_task_error",
                "task:on_task_message"
            ]
            
            event_type = get_choice("Select event type:", event_types)
            if not event_type:
                continue
            
            # Get task details if it's a task event
            task_id = None
            task_name = None
            task_display_name = None
            
            if event_type.startswith("task:"):
                print(f"\n{Colors.BOLD}Task Details:{Colors.ENDC}")
                task_id = get_input("Task ID", f"task-{uuid.uuid4().hex[:8]}")
                task_name = get_input("Task name", f"task_{len(events_batch) + 1}")
                task_display_name = get_input("Task display name", f"Task {len(events_batch) + 1}")
            
            # Get error details if it's an error event
            error = None
            if "error" in event_type:
                print(f"\n{Colors.BOLD}Error Details:{Colors.ENDC}")
                error_message = get_input("Error message", "Test error occurred")
                error_code = get_input("Error code", "TEST_ERROR")
                if error_message:
                    error = {"message": error_message, "code": error_code}
            
            # Create event data
            event_data = {
                "event_kind": event_type,
                "instance_id": instance_id,
                "task_id": task_id,
                "task_name": task_name,
                "task_display_name": task_display_name,
                "error": error
            }
            
            events_batch.append(event_data)
            print_success(f"Added {event_type} to batch (total: {len(events_batch)} events)")
    
    # Send the batch
    print(f"\n{Colors.BOLD}Sending batch of {len(events_batch)} event(s)...{Colors.ENDC}")
    
    try:
        result = send_batch_events(
            events_batch=events_batch,
            flow_name="Batch Test Flow"
        )
        
        print_success(f"Batch sent successfully!")
        print(f"   Total events: {result['total_events']}")
        print(f"   Successful: {result['successful']}")
        print(f"   Failed: {result['failed']}")
        
        if result.get('results'):
            print(f"\n{Colors.CYAN}Individual Results:{Colors.ENDC}")
            for i, evt_result in enumerate(result['results'], 1):
                status = "✅" if evt_result.get('success') else "❌"
                print(f"  {i}. {status} {evt_result.get('event_kind')} - {evt_result.get('event_id')}")
        
        # Ask if user wants to retrieve the events
        retrieve = get_choice("\nRetrieve these events to verify?", ["No", "Yes"])
        if retrieve == "Yes":
            print()
            retrieve_events_interactive(default_instance_id=instance_id)
            
    except Exception as e:
        print_error(f"Failed to send batch: {e}")


def send_batch_events(
    events_batch: List[Dict[str, Any]],
    flow_name: str = "Test Flow"
) -> Dict[str, Any]:
    """Send a batch of events to the flow callback handler."""
    from flow_callback_handler import flow_callback_handler
    from flow_callback_types import (
        FlowCallbackEventPayload,
        EventMetadata,
        FlowCallbackEventKind,
        FlowState,
        ErrorDetails
    )
    
    # Build array of FlowCallbackEventPayload objects
    events_array = []
    
    for event_data in events_batch:
        event_type = event_data['event_kind']
        instance_id = event_data['instance_id']
        
        # Generate timestamp and event ID
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        event_id = f"{instance_id}_{timestamp}_{uuid.uuid4().hex[:8]}"
        
        # Determine flow state based on event type
        if "error" in event_type:
            flow_state = FlowState.FAILED
        elif event_type == "flow:on_flow_end":
            flow_state = FlowState.COMPLETED
        elif event_type == "task:on_task_wait":
            flow_state = FlowState.INPUT_REQUIRED
        else:
            flow_state = FlowState.WORKING
        
        # Create error details if provided
        error_details = None
        if event_data.get('error'):
            error_details = ErrorDetails(
                message=event_data['error'].get("message", ""),
                code=event_data['error'].get("code")
            )
        
        # Create the event payload
        event = FlowCallbackEventPayload(
            event=EventMetadata(
                id=event_id,
                kind=FlowCallbackEventKind(event_type),
                created_at=timestamp,
                instance_id=instance_id,
                flow_name=flow_name,
                environment_id="draft",
                state=flow_state,
                parent_instance_id=None,
                parent_flow_name=None,
                task_id=event_data.get('task_id'),
                task_name=event_data.get('task_name'),
                task_display_name=event_data.get('task_display_name'),
                error=error_details
            ),
            output=None,
            elicitation=None
        )
        
        events_array.append(event)
    
    # Call the handler with the array
    tool_response = flow_callback_handler(events_array)
    
    # Extract the actual result from the ToolResponse
    if hasattr(tool_response, 'content'):
        result = tool_response.content
    elif hasattr(tool_response, 'result'):
        result = tool_response.result
    else:
        result = tool_response
    
    return {
        "total_events": result.total_events if hasattr(result, 'total_events') else len(events_array),
        "successful": result.successful if hasattr(result, 'successful') else 0,
        "failed": result.failed if hasattr(result, 'failed') else 0,
        "results": [
            {
                "event_id": r.event_id if hasattr(r, 'event_id') else 'unknown',
                "success": r.success if hasattr(r, 'success') else False,
                "event_kind": r.event_kind if hasattr(r, 'event_kind') else 'unknown'
            }
            for r in (result.results if hasattr(result, 'results') else [])
        ]
    }


def send_test_event(
    event_type: str,
    instance_id: Optional[str] = None,
    task_id: Optional[str] = None,
    flow_id: Optional[str] = None,
    flow_name: Optional[str] = None,
    task_name: Optional[str] = None,
    task_display_name: Optional[str] = None,
    assignee: Optional[str] = None,
    context_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    error: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Send a test event to the flow callback handler."""
    # Import the handler function and types
    from flow_callback_handler import flow_callback_handler
    from flow_callback_types import (
        FlowCallbackEventPayload,
        EventMetadata,
        FlowCallbackEventKind,
        FlowState,
        ErrorDetails
    )
    
    # Generate instance ID if not provided
    if not instance_id:
        instance_id = generate_instance_id()
    
    # Generate timestamp and event ID (use timezone-aware datetime)
    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    event_id = f"{instance_id}_{timestamp}"
    
    # Determine flow state based on event type
    if "error" in event_type:
        flow_state = FlowState.FAILED
    elif event_type == "flow:on_flow_end":
        flow_state = FlowState.COMPLETED
    elif event_type == "task:on_task_wait":
        flow_state = FlowState.INPUT_REQUIRED
    else:
        flow_state = FlowState.WORKING
    
    # Create error details if provided
    error_details = None
    if error:
        error_details = ErrorDetails(
            message=error.get("message", ""),
            code=error.get("code")
        )
    
    # Create the event payload
    event = FlowCallbackEventPayload(
        event=EventMetadata(
            id=event_id,
            kind=FlowCallbackEventKind(event_type),
            created_at=timestamp,
            instance_id=instance_id,
            flow_name=flow_name or "Test Flow",
            environment_id="draft",  # Default to 'draft' environment
            state=flow_state,
            parent_instance_id=None,
            parent_flow_name=None,
            task_id=task_id,
            task_name=task_name,
            task_display_name=task_display_name,
            error=error_details
        ),
        output=context_data if flow_state == FlowState.COMPLETED else None,
        elicitation=None  # TODO: Add elicitation support if needed
    )
    
    # Wrap the event in an array (handler expects List[FlowCallbackEventPayload])
    events_array = [event]
    
    # Call the handler (it's decorated with @tool, so it returns a ToolResponse)
    tool_response = flow_callback_handler(events_array)
    
    # Extract the actual result from the ToolResponse
    # The tool decorator wraps the return value in a ToolResponse object
    # The actual FlowEventsResult is in tool_response.content or tool_response.result
    if hasattr(tool_response, 'content'):
        result = tool_response.content
    elif hasattr(tool_response, 'result'):
        result = tool_response.result
    else:
        # If it's already the FlowEventsResult, use it directly
        result = tool_response
    
    # Extract the first event result from the batch result
    first_result = result.results[0] if hasattr(result, 'results') and result.results else None
    
    return {
        "event_id": first_result.event_id if first_result and hasattr(first_result, 'event_id') else event_id,
        "instance_id": instance_id,
        "event_kind": event_type,
        "success": first_result.success if first_result and hasattr(first_result, 'success') else True,
        "total_events": result.total_events if hasattr(result, 'total_events') else 1,
        "successful": result.successful if hasattr(result, 'successful') else 1,
        "failed": result.failed if hasattr(result, 'failed') else 0
    }


def retrieve_events_interactive(default_instance_id: Optional[str] = None):
    """Interactive flow to retrieve events."""
    print_header("Retrieve Events")
    
    # Choose filter type
    filter_options = [
        "All events (latest 10)",
        "Filter by instance ID",
        "Filter by event type",
        "Custom filter"
    ]
    
    filter_choice = get_choice("How would you like to filter events?", filter_options)
    if not filter_choice:
        return
    
    instance_id = None
    event_type = None
    limit = 10
    
    if filter_choice == "Filter by instance ID":
        instance_id = get_input("Instance ID", default_instance_id)
        if not instance_id:
            print_error("Instance ID is required")
            return
    
    elif filter_choice == "Filter by event type":
        event_types = [
            "flow:on_flow_start",
            "flow:on_flow_end", 
            "flow:on_flow_error",
            "task:on_task_wait",
            "task:on_task_error",
            "task:on_task_message"
        ]
        event_type = get_choice("Select event type:", event_types)
        if not event_type:
            return
    
    elif filter_choice == "Custom filter":
        instance_id = get_input("Instance ID (optional)", default_instance_id)
        event_type = get_input("Event type (optional)")
        limit_str = get_input("Limit", "10")
        try:
            limit = int(limit_str) if limit_str else 10
        except ValueError:
            limit = 10
    
    # Retrieve events
    try:
        events = retrieve_events(
            instance_id=instance_id if instance_id else None,
            event_type=event_type if event_type else None,
            limit=limit
        )
        
        if not events:
            print_warning("No events found matching the criteria")
            return
        
        print_success(f"Found {len(events)} event(s)")
        
        # Display options
        display_options = ["Summary view", "Detailed view", "JSON output"]
        display_choice = get_choice("How would you like to view the events?", display_options)
        
        if display_choice == "Summary view":
            print_events_summary(events)
        elif display_choice == "Detailed view":
            print_events_detailed(events)
        elif display_choice == "JSON output":
            print(json.dumps(events, indent=2, default=str))
            
    except Exception as e:
        print_error(f"Failed to retrieve events: {e}")


def retrieve_events(
    instance_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Retrieve events from the AstraDB table."""
    api_token, api_endpoint, keyspace = get_astra_credentials()
    
    # Initialize AstraDB client
    client = DataAPIClient(api_token)
    database = client.get_database(api_endpoint, keyspace=keyspace)
    table = database.get_table("flow_events")
    
    # Build filter
    filter_dict = {}
    if instance_id:
        filter_dict["instance_id"] = instance_id
    if event_type:
        filter_dict["event_kind"] = event_type
    
    # Query the table
    if filter_dict:
        cursor = table.find(filter=filter_dict, limit=limit, sort={"created_at": -1})
    else:
        cursor = table.find(limit=limit, sort={"created_at": -1})
    
    return list(cursor)


def print_events_summary(events: List[Dict[str, Any]]):
    """Print events in summary format."""
    print(f"\n{Colors.BOLD}Event Summary:{Colors.ENDC}")
    print(f"{'#':<3} {'Event Type':<20} {'Instance ID':<20} {'Timestamp':<20}")
    print("-" * 70)
    
    for i, event in enumerate(events, 1):
        event_kind = event.get('event_kind', 'N/A')[:19]
        instance_id = event.get('instance_id', 'N/A')[:19]
        created_at = event.get('created_at', 'N/A')[:19]
        print(f"{i:<3} {event_kind:<20} {instance_id:<20} {created_at:<20}")


def print_events_detailed(events: List[Dict[str, Any]]):
    """Print events in detailed format."""
    for i, event in enumerate(events, 1):
        print(f"\n{Colors.BOLD}{'='*80}{Colors.ENDC}")
        print(f"{Colors.BOLD}Event #{i}{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*80}{Colors.ENDC}")
        
        print(f"{Colors.CYAN}Event ID:{Colors.ENDC}       {event.get('event_id', 'N/A')}")
        print(f"{Colors.CYAN}Event Kind:{Colors.ENDC}     {event.get('event_kind', 'N/A')}")
        print(f"{Colors.CYAN}Created At:{Colors.ENDC}     {event.get('created_at', 'N/A')}")
        print(f"{Colors.CYAN}Instance ID:{Colors.ENDC}    {event.get('instance_id', 'N/A')}")
        print(f"{Colors.CYAN}Flow Name:{Colors.ENDC}      {event.get('flow_name', 'N/A')}")
        
        if event.get('task_id'):
            print(f"{Colors.CYAN}Task ID:{Colors.ENDC}        {event.get('task_id')}")
        if event.get('task_name'):
            print(f"{Colors.CYAN}Task Name:{Colors.ENDC}      {event.get('task_name')}")
        if event.get('task_display_name'):
            print(f"{Colors.CYAN}Task Display:{Colors.ENDC}   {event.get('task_display_name')}")
        if event.get('assignee'):
            print(f"{Colors.CYAN}Assignee:{Colors.ENDC}       {event.get('assignee')}")
        
        # Parse and display context data
        if event.get('context_data'):
            try:
                context = json.loads(event['context_data'])
                if context:
                    print(f"{Colors.CYAN}Context Data:{Colors.ENDC}")
                    print(json.dumps(context, indent=2))
            except:
                pass
        
        # Parse and display metadata
        if event.get('metadata'):
            try:
                metadata = json.loads(event['metadata'])
                if metadata:
                    print(f"{Colors.CYAN}Metadata:{Colors.ENDC}")
                    print(json.dumps(metadata, indent=2))
            except:
                pass
        
        # Display error if present
        if event.get('error'):
            try:
                error = json.loads(event['error'])
                print(f"{Colors.RED}Error:{Colors.ENDC}")
                print(json.dumps(error, indent=2))
            except:
                print(f"{Colors.RED}Error:{Colors.ENDC}          {event.get('error')}")


def test_connection():
    """Test the AstraDB connection."""
    print_header("Test Connection")
    
    try:
        api_token, api_endpoint, keyspace = get_astra_credentials()
        print_info(f"Testing connection to {api_endpoint}")
        print_info(f"Keyspace: {keyspace}")
        
        # Initialize client
        client = DataAPIClient(api_token)
        database = client.get_database(api_endpoint, keyspace=keyspace)
        
        # Try to get the table
        table = database.get_table("flow_events")
        
        # Try a simple query
        cursor = table.find(limit=1)
        list(cursor)  # Execute the query
        
        print_success("Connection successful!")
        print_info("The flow_events table is accessible")
        
    except Exception as e:
        print_error(f"Connection failed: {e}")
        print_info("Make sure you have:")
        print_info("1. Configured your .env file with valid credentials")
        print_info("2. Run ./setup_astra_table.sh to create the table")


def show_menu():
    """Show the main menu."""
    print_header("Flow Callback Handler Tester")
    
    print(f"{Colors.BOLD}What would you like to do?{Colors.ENDC}")
    print()
    
    options = [
        "Send a single test event",
        "Send a batch of events",
        "Retrieve stored events",
        "Test AstraDB connection"
    ]
    
    return get_choice("Select an option (or 'q' to quit):", options, allow_quit=True)


def main():
    """Main interactive loop."""
    # Load environment variables
    load_env()
    
    print(f"{Colors.BOLD}{Colors.BLUE}Welcome to the Flow Callback Handler Tester!{Colors.ENDC}")
    print_info("This tool helps you test the flow callback handler interactively.")
    
    while True:
        try:
            choice = show_menu()
            
            # Check if user wants to quit (empty choice from 'q' or Ctrl+C)
            if not choice:
                print(f"\n{Colors.BOLD}Thanks for using the Flow Callback Handler Tester!{Colors.ENDC}")
                break
            
            if choice == "Send a single test event":
                send_test_event_interactive()
            elif choice == "Send a batch of events":
                send_batch_events_interactive()
            elif choice == "Retrieve stored events":
                retrieve_events_interactive()
            elif choice == "Test AstraDB connection":
                test_connection()
            
            # Wait for user to continue
            input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                
        except KeyboardInterrupt:
            print(f"\n\n{Colors.BOLD}Goodbye!{Colors.ENDC}")
            break
        except Exception as e:
            print_error(f"An error occurred: {e}")
            input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")


if __name__ == "__main__":
    main()

# Made with Bob