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
from ibm_watsonx_orchestrate.flow_builder.types import FlowCallback
from ibm_watsonx_orchestrate.flow_builder.flow_callback_types import FlowCallbackEventKind

from .greeting_tool import greeting_tool


class FlowInput(BaseModel):
    """Input schema for the example flow."""
    message: str


class FlowOutput(BaseModel):
    """Output schema for the example flow."""
    result: str


@flow(
    name="example_flow_with_callbacks",
    display_name="Example Flow with Callbacks",
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
    
    # Add the greeting tool node
    greeting_node = aflow.tool(greeting_tool)
    
    # Connect the flow
    aflow.sequence(START, greeting_node, END)
    
    # Method 1: Add callback using just tool name (server default batch interval)
    aflow.add_callback(
        tool="flow_callback_handler",
        events=[
            FlowCallbackEventKind.ON_FLOW_START,
            FlowCallbackEventKind.ON_FLOW_END,
            FlowCallbackEventKind.ON_FLOW_ERROR
        ]
        # batch_interval not specified - server will use default
    )
    
    # # Method 2: Add callback with toolkit:tool format and custom batch interval
    # aflow.add_callback(
    #     tool="monitoring_toolkit:task_event_handler",
    #     events=[
    #         FlowCallbackEventKind.ON_TASK_WAIT,
    #         FlowCallbackEventKind.ON_TASK_ERROR,
    #         FlowCallbackEventKind.ON_TASK_MESSAGE
    #     ],
    #     batch_interval=30000  # Custom: 30 seconds
    # )
    
    # # Method 3: Add callback with specific tool instance
    # aflow.add_callback(
    #     tool="error_handler:abc-123-def-456",
    #     events=[FlowCallbackEventKind.ON_FLOW_ERROR],
    #     batch_interval=10000  # Custom: 10 seconds
    # )
    
    # # Method 4: Directly append to callbacks list with toolkit:tool:uuid format
    # callback = FlowCallback(
    #     tool="audit_toolkit:audit_logger:xyz-789-ghi-012",
    #     events=[FlowCallbackEventKind.ON_FLOW_START, FlowCallbackEventKind.ON_FLOW_END],
    #     batch_interval=60000  # Custom: 60 seconds
    # )
    # aflow.callbacks.append(callback)
    
    return aflow

# Made with Bob
