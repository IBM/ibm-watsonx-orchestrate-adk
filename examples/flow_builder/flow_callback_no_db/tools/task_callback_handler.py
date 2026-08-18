"""
Flow Callback Handler Tool

This tool handles flow callback events from other flows.
It accepts FlowCallbackEventPayload as defined in flow_callback_types.py.
"""

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
    name="callback_handler_on_task_wait",
    display_name="Flow callback for task notification",
    description="A flow that receives callback events on task wait from other flows",
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
