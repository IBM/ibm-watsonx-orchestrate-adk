"""
Simple test flow for translation integration testing with user interaction.
"""

from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import END, Flow, flow, START
from ibm_watsonx_orchestrate.flow_builder.types import UserFieldKind

from .echo_tool import echo_message


class TestInput(BaseModel):
    """
    Input schema for the translation test flow.
    
    Attributes:
        message: The message to process
    """
    message: str = Field(default="Hello", description="Input message")


@flow(
    name="translation_test_flow",
    description="A simple test flow for translation testing with user interaction",
    input_schema=TestInput
)
def build_translation_test_flow(aflow: Flow = None) -> Flow:
    """
    Creates a simple flow with a tool and user interaction for translation testing.
    
    Args:
        aflow: The flow to be built
        
    Returns:
        The created flow
    """
    # Create a user flow with one simple text input field
    user_flow = aflow.userflow()
    user_node_with_form = user_flow.form(
        name="ApplicationForm",
        display_name="Application",
        cancel_button_label="Cancel"
    )

    #Boolean: Married
    user_node_with_form.boolean_input_field(name="married", label="Married", single_checkbox = True, true_label="Married", false_label="Not married")

    # Connect the user flow
    user_flow.edge(START, user_node_with_form)
    user_flow.edge(user_node_with_form, END)
    
    # Add the echo tool
    echo_node = aflow.tool(echo_message)
    
    aflow.sequence(START, user_flow, echo_node, END)
    aflow.target_locales(['fr'])
    
    return aflow
