"""
Query tool for retrieving flow events from AstraDB.

This tool allows agents to query and retrieve flow callback events
that have been stored in AstraDB by the flow_callback_handler.
"""

import logging
import os
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from astrapy import DataAPIClient

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType, ExpectedCredentials
from ibm_watsonx_orchestrate.run import connections

# Suppress AstraDB warnings
logging.getLogger("astrapy").setLevel(logging.ERROR)

# Connection ID for Flow Callback App (contains token, url, and keyspace)
CONNECTION_FLOW_CALLBACK = 'flow_callback_app'


class FlowEventQuery(BaseModel):
    """Query parameters for retrieving flow events."""
    instance_id: Optional[str] = Field(None, description="Filter by flow instance ID")
    event_kind: Optional[str] = Field(None, description="Filter by event kind (e.g., 'flow:on_flow_start', 'task:on_task_wait')")
    limit: int = Field(10, description="Maximum number of events to return", ge=1, le=100)


class FlowEventResult(BaseModel):
    """Result containing flow events."""
    events: List[Dict[str, Any]] = Field(description="List of flow events")
    count: int = Field(description="Number of events returned")


def get_astra_credentials() -> tuple[str, str, str]:
    """
    Get AstraDB credentials from connections or environment variables.
    
    Returns:
        Tuple of (api_token, api_endpoint, keyspace)
        
    Raises:
        ValueError: If credentials are not found
    """
    # Check environment variables first
    api_token = os.getenv("ASTRA_TOKEN")
    api_endpoint = os.getenv("ASTRA_URL")
    keyspace = os.getenv("ASTRA_NAMESPACE", "default_keyspace")
    
    # If env vars are not set, try to get from connection
    if not api_token or not api_endpoint:
        try:
            conn_creds = connections.key_value(CONNECTION_FLOW_CALLBACK)
            if not api_token:
                api_token = conn_creds.get("ASTRA_TOKEN")
            if not api_endpoint:
                api_endpoint = conn_creds.get("ASTRA_URL")
            if not keyspace or keyspace == "default_keyspace":
                conn_keyspace = conn_creds.get("ASTRA_NAMESPACE")
                if conn_keyspace:
                    keyspace = conn_keyspace
        except Exception as e:
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


@tool(
    description="Query and retrieve flow callback events from AstraDB. Use this to check recent flow executions, monitor task status, or investigate errors.",
    permission=ToolPermission.READ_ONLY,
    expected_credentials=[
        ExpectedCredentials(app_id=CONNECTION_FLOW_CALLBACK, type=ConnectionType.KEY_VALUE)
    ]
)
def query_flow_events(query: FlowEventQuery) -> FlowEventResult:
    """
    Query flow callback events stored in AstraDB.
    
    This tool retrieves flow execution events that have been captured by
    the flow callback handler. You can filter by instance ID, event kind,
    or retrieve the most recent events.
    
    Args:
        query: Query parameters (instance_id, event_kind, limit)
        
    Returns:
        FlowEventResult containing the list of matching events
        
    Example queries:
        - Get recent events: query_flow_events(FlowEventQuery(limit=10))
        - Get events for a specific flow: query_flow_events(FlowEventQuery(instance_id="flow-123"))
        - Get error events: query_flow_events(FlowEventQuery(event_kind="flow:on_flow_error"))
    """
    try:
        # Get credentials from connections or environment
        api_token, api_endpoint, keyspace = get_astra_credentials()
        
        # Initialize AstraDB client
        client = DataAPIClient(api_token)
        database = client.get_database(api_endpoint, keyspace=keyspace)
        
        # Get the flow_events table
        table = database.get_table("flow_events")
        
        # Build filter
        filter_dict = {}
        if query.instance_id:
            filter_dict["instance_id"] = query.instance_id
        if query.event_kind:
            filter_dict["event_kind"] = query.event_kind
        
        # Query the table with sort by created_at descending (latest first)
        sort = {"created_at": -1}
        
        if filter_dict:
            cursor = table.find(filter=filter_dict, sort=sort, limit=query.limit)
        else:
            cursor = table.find(sort=sort, limit=query.limit)
        
        # Collect results
        events = list(cursor)
        
        return FlowEventResult(
            events=events,
            count=len(events)
        )
        
    except Exception as e:
        logging.error(f"Failed to query flow events: {type(e).__name__}: {e}")
        # Return empty result on error
        return FlowEventResult(
            events=[],
            count=0
        )

