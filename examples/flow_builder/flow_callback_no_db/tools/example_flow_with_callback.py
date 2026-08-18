"""
Example demonstrating how to use Flow callbacks.

This example shows how to add callbacks to a Flow that will be invoked
when specific events occur during flow execution.
"""

from pydantic import BaseModel
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow,
    flow,
    START,
    END
)
from ibm_watsonx_orchestrate.flow_builder.flow_callback_types import FlowCallbackEventKind


class FlowInput(BaseModel):
    """Input schema for the example flow."""
    message: str


class FlowOutput(BaseModel):
    """Output schema for the example flow."""
    result: str


@flow(
    name="flow_with_callback_tool",
    display_name="Flow with Tool as Callback",
    input_schema=FlowInput,
    output_schema=FlowOutput
)
def build_example_flow_with_callbacks(aflow: Flow) -> Flow:
    """
    Creates a flow with callbacks configured.
    
    The callbacks will be invoked when:
    - Flow starts execution
    - Flow completes execution
    - Flow encounters an error
    - A task is waiting for user input
    - A task encounters an error
    
    Args:
        aflow (Flow): The flow to be built.
        
    Returns:
        Flow: The created flow with callbacks configured.
    """
    user_flow = aflow.userflow()
    user_flow.spec.display_name= "Application"

    # Create form with default submit button and visible cancel button
    user_node_with_form = user_flow.form(
        name="ApplicationForm",
        display_name="Application",
        cancel_button_label="Cancel"
    )

    #Text: Last Name
    user_node_with_form.text_input_field(name="lastName", label="Last name", required=True, placeholder_text="Enter your name here", help_text="Enter name")
    
    user_flow.edge(START, user_node_with_form)
    user_flow.edge(user_node_with_form, END)
    aflow.sequence(START, user_flow, END)
    
    aflow.add_callback(
        tool="flow_as_callback_handler",
        events=[
            FlowCallbackEventKind.ON_FLOW_START,
            FlowCallbackEventKind.ON_FLOW_END,
            FlowCallbackEventKind.ON_FLOW_ERROR,
        ]
    )

    aflow.add_callback(
        tool="callback_handler_on_task_wait",
        events=[
            FlowCallbackEventKind.ON_TASK_WAIT,
            FlowCallbackEventKind.ON_TASK_ERROR
        ]
    )

    return aflow

