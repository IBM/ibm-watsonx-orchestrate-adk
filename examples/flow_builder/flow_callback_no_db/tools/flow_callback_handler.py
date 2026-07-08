"""
Flow Callback Handler Tool

This tool handles flow events by storing them in the AstraDB flow_events table.
It accepts FlowCallbackEventPayload as defined in flow_callback_types.py.
"""

import logging
from typing import List
from pydantic import BaseModel, Field

from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow,
    flow,
    START,
    END
)
from ibm_watsonx_orchestrate.flow_builder.flow_callback_types import (
    FlowCallbackEventsPayload
)


class ScriptOutputSchema(BaseModel):
    """Output schema for the script node."""
    outEvents: List = Field(..., description="The processed callback events")


@flow(
    name="flow_as_callback_handler",
    display_name="Flow as Tool Callback",
    description="A flow that receives callback events from other flows",
    input_schema=FlowCallbackEventsPayload
)
def build_example_flow_callbacks(aflow: Flow) -> Flow:
    """
    A simple callback handler flow that receives flow events.
    
    This flow accepts FlowCallbackEventsPayload which contains an array of
    FlowCallbackEventPayload objects. Each event includes:
    - event: EventMetadata (id, kind, created_at, instance_id, flow_name, etc.)
    - output: Optional output data (when flow completes)
    - elicitation: Optional elicitation details (when user input is required)
    
    Args:
        aflow: The flow builder instance
        
    Returns:
        The configured flow
    """
    # Add a simple script node to process the events and set output
    script_node = aflow.script(
        name="process_events",
        output_schema=ScriptOutputSchema,
        script="""

self.output.outEvents = flow.input.events
"""
    )
    
    # Connect the flow
    aflow.sequence(START, script_node, END)
    
    return aflow
