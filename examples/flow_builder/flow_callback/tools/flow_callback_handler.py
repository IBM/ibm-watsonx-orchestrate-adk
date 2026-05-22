"""
Flow Callback Handler Tool

This tool handles flow events by storing them in the AstraDB flow_events table.
It accepts FlowCallbackEventPayload as defined in flow_callback_types.py.
"""

import logging
import os
import json
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field
from astrapy import DataAPIClient

# Suppress AstraDB warnings about in-memory sorting and missing indexes
logging.getLogger("astrapy").setLevel(logging.ERROR)

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType, ExpectedCredentials
from ibm_watsonx_orchestrate.run import connections

# Import the type definitions
try:
    from .flow_callback_types import FlowCallbackEventPayload
except ImportError:
    # When imported from tester, use absolute import
    from flow_callback_types import FlowCallbackEventPayload


# Connection ID for Flow Callback App (contains token, url, and keyspace)
CONNECTION_FLOW_CALLBACK = 'flow_callback_app'


class FlowEventResult(BaseModel):
    """
    Represents the result of a flow event storage operation.
    """
    event_id: str = Field(..., description='The unique event identifier')
    success: bool = Field(..., description='Whether the storage was successful')
    message: str = Field(..., description='Status message')
    event_kind: str = Field(..., description='Kind of event stored')


class FlowEventsResult(BaseModel):
    """
    Represents the result of multiple flow events storage operation.
    """
    total_events: int = Field(..., description='Total number of events processed')
    successful: int = Field(..., description='Number of successfully stored events')
    failed: int = Field(..., description='Number of failed events')
    results: list[FlowEventResult] = Field(..., description='Individual event results')


def get_astra_credentials() -> tuple[str, str, str]:
    """
    Get AstraDB credentials from connections or environment variables.
    
    Since BadRequest exception calls sys.exit(1), we need to check for environment
    variables first to avoid triggering BadRequest when connections are not configured.
    
    The connection should be a key-value type with keys matching environment variable names:
    - ASTRA_TOKEN: AstraDB API token
    - ASTRA_URL: AstraDB API endpoint URL
    - ASTRA_NAMESPACE: AstraDB namespace name (optional, defaults to "default_keyspace")
    
    Returns:
        Tuple of (api_token, api_endpoint, keyspace)
        
    Raises:
        ValueError: If credentials are not found
    """
    # Check environment variables first to avoid BadRequest sys.exit()
    api_token = os.getenv("ASTRA_TOKEN")
    api_endpoint = os.getenv("ASTRA_URL")
    keyspace = os.getenv("ASTRA_NAMESPACE", "default_keyspace")  # Default to "default_keyspace"
    
    # If env vars are not set, try to get from connection (key-value type)
    # Connection keys match environment variable names for consistency
    if not api_token or not api_endpoint:
        try:
            conn_creds = connections.key_value(CONNECTION_FLOW_CALLBACK)
            if not api_token:
                api_token = conn_creds.get("ASTRA_TOKEN")
            if not api_endpoint:
                api_endpoint = conn_creds.get("ASTRA_URL")
            if not keyspace or keyspace == "default_keyspace":
                # Allow connection to override default keyspace
                conn_keyspace = conn_creds.get("ASTRA_NAMESPACE")
                if conn_keyspace:
                    keyspace = conn_keyspace
        except Exception as e:
            # Connection failed, but env vars might be set
            logging.debug(f"Failed to get credentials from connection: {type(e).__name__}: {e}")
    
    # Final validation
    if not api_token or not isinstance(api_token, str):
        raise ValueError(
            f"Missing API token. Either configure connection '{CONNECTION_FLOW_CALLBACK}' "
            "with 'ASTRA_TOKEN' key or set ASTRA_TOKEN environment variable."
        )
    
    if not api_endpoint or not isinstance(api_endpoint, str):
        raise ValueError(
            f"Missing API endpoint. Either configure connection '{CONNECTION_FLOW_CALLBACK}' "
            "with 'ASTRA_URL' key or set ASTRA_URL environment variable."
        )
    
    if not isinstance(keyspace, str):
        raise ValueError(
            f"Invalid keyspace value. Must be a string."
        )
    
    return api_token, api_endpoint, keyspace


def store_flow_event_in_db(
    api_token: str,
    api_endpoint: str,
    keyspace: str,
    event: FlowCallbackEventPayload
) -> FlowEventResult:
    """
    Store a flow callback event in the AstraDB flow_events table.
    
    Args:
        api_token: AstraDB API token
        api_endpoint: AstraDB API endpoint URL
        keyspace: AstraDB keyspace name
        event: FlowCallbackEventPayload object to store
        
    Returns:
        FlowEventResult object with storage status
        
    Raises:
        Exception: If database insert fails
    """
    try:
        # Initialize AstraDB client
        client = DataAPIClient(api_token)
        database = client.get_database(api_endpoint, keyspace=keyspace)
        
        # Get the flow_events table
        table = database.get_table("flow_events")
        
        # Use the event ID from the event payload
        event_id = event.event.id
        
        # Prepare event data for storage
        event_data = {
            "event_id": event_id,
            "event_kind": event.event.kind.value,
            "created_at": event.event.created_at,
            "instance_id": event.event.instance_id,
            "flow_name": event.event.flow_name,
            "environment_id": event.event.environment_id,
            "flow_state": event.event.state.value,
            "parent_instance_id": event.event.parent_instance_id,
            "parent_flow_name": event.event.parent_flow_name,
            "task_id": event.event.task_id,
            "task_name": event.event.task_name,
            "task_display_name": event.event.task_display_name,
            "error": json.dumps(event.event.error.model_dump()) if event.event.error else None,
            "output": json.dumps(event.output) if event.output else None,
            "elicitation": json.dumps(event.elicitation.model_dump()) if event.elicitation else None,
        }
        
        # Insert the event into the table
        result = table.insert_one(event_data)
        
        return FlowEventResult(
            event_id=event_id,
            success=True,
            message=f"Successfully stored flow event {event_id}",
            event_kind=event_data["event_kind"]
        )
        
    except Exception as e:
        logging.error(f"Failed to store flow event in database: {type(e).__name__}: {e}")
        raise Exception(f"Failed to store flow event: {str(e)}")


@tool(
    permission=ToolPermission.READ_WRITE,
    description="Store flow callback events in the database for tracking and auditing purposes. This is a fire-and-forget callback handler that accepts an array of events.",
    expected_credentials=[
        ExpectedCredentials(app_id=CONNECTION_FLOW_CALLBACK, type=ConnectionType.KEY_VALUE)
    ]
)
def flow_callback_handler(
    events: List[FlowCallbackEventPayload]
) -> FlowEventsResult:
    """
    Handle flow callback events by storing them in the AstraDB flow_events table.
    
    This tool captures an array of flow callback events and stores them for tracking,
    auditing, and analysis. This is a fire-and-forget callback that does not return
    data to the flow execution.

    Args:
        events: List of FlowCallbackEventPayload objects, where each event contains
                metadata, status, and optional elicitation or output data.

    Returns:
        A FlowEventsResult object containing the storage status for all events.
        
    Raises:
        ValueError: If database credentials are not configured
        Exception: If database insert fails
    """
    # Get credentials from connections or environment variables
    api_token, api_endpoint, keyspace = get_astra_credentials()
    
    # Store all events in database
    results = []
    successful = 0
    failed = 0
    
    for event_data in events:
        try:
            # Convert dict to FlowCallbackEventPayload if needed
            if isinstance(event_data, dict):
                event = FlowCallbackEventPayload(**event_data)
            else:
                event = event_data
            
            result = store_flow_event_in_db(
                api_token=api_token,
                api_endpoint=api_endpoint,
                keyspace=keyspace,
                event=event
            )
            results.append(result)
            if result.success:
                successful += 1
            else:
                failed += 1
        except Exception as e:
            # Create a failed result for this event
            # Try to extract event_id from dict or object
            try:
                if isinstance(event_data, dict):
                    event_id = event_data.get('event', {}).get('id', 'unknown')
                    event_kind = event_data.get('event', {}).get('kind', 'unknown')
                else:
                    event_id = event_data.event.id
                    event_kind = event_data.event.kind.value
            except:
                event_id = 'unknown'
                event_kind = 'unknown'
            
            failed_result = FlowEventResult(
                event_id=event_id,
                success=False,
                message=f"Failed to store event: {str(e)}",
                event_kind=event_kind
            )
            results.append(failed_result)
            failed += 1
            logging.error(f"Failed to store event {event_id}: {e}")
    
    return FlowEventsResult(
        total_events=len(events),
        successful=successful,
        failed=failed,
        results=results
    )


if __name__ == '__main__':
    # Test the tool directly (bypassing decorator for testing)
    import sys
    from .flow_callback_types import (
        FlowCallbackEventPayload,
        EventMetadata,
        FlowCallbackEventKind,
        FlowState
    )
    
    # Get credentials
    try:
        if len(sys.argv) < 2:
            print("Usage: python flow_callback_handler.py <event_kind>")
            print("Example: python flow_callback_handler.py flow:on_flow_start")
            sys.exit(1)
        
        # Parse event kind argument
        event_kind_str = sys.argv[1]
        try:
            event_kind = FlowCallbackEventKind(event_kind_str)
        except ValueError:
            print(f"Invalid event kind: {event_kind_str}")
            print(f"Valid kinds: {[e.value for e in FlowCallbackEventKind]}")
            sys.exit(1)
        
        api_token, api_endpoint, keyspace = get_astra_credentials()
        
        # Create a test payload
        timestamp = datetime.now(timezone.utc).isoformat()
        instance_id = "test-instance-123"
        event_id = f"{instance_id}_{timestamp}"
        
        test_payload = FlowCallbackEventPayload(
            event=EventMetadata(
                id=event_id,
                kind=event_kind,
                created_at=timestamp,
                instance_id=instance_id,
                flow_name="Test Flow",
                environment_id="draft",
                state=FlowState.WORKING,
                parent_instance_id=None,
                parent_flow_name=None,
                task_id="test-task-123" if "task" in event_kind_str else None,
                task_name="test_task" if "task" in event_kind_str else None,
                task_display_name="Test Task" if "task" in event_kind_str else None,
                error=None
            ),
            output=None,
            elicitation=None
        )
        
        result = store_flow_event_in_db(api_token, api_endpoint, keyspace, test_payload)
        
        print(f"Storage Result:")
        print(f"  Success: {result.success}")
        print(f"  Message: {result.message}")
        print(f"  Event ID: {result.event_id}")
        print(f"  Event Kind: {result.event_kind}")
        
        sys.exit(0 if result.success else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Made with Bob