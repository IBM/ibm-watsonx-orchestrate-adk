"""
Error Branching Example Flow

"""

from pydantic import BaseModel, Field

from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import (
    UserFieldKind,
    NodeErrorHandlerConfig
)

class PetFacts(BaseModel):
    facts: list[str] = Field(description="A list of facts about the pet")

@flow(
        name = "get_pet_facts_error_branching",
        output_schema = PetFacts,
        description="Demonstrates error branching - shows user message if dog facts fail"
)
def build_get_pet_facts_error_branching_flow(aflow: Flow) -> Flow:
    """
    Error branching flow that tries to get dog facts,
    but shows a user activity message if the dog facts tool fails.
    """
    
    # Create a user flow for displaying the error message
    user_flow = aflow.userflow()
    # Add a display text field to show the error message
    error_message_node = user_flow.field(
        direction="output",
        name="error_display",
        display_name="Error Message",
        kind=UserFieldKind.Text,
        text="Sorry, we couldn't fetch dog facts at this time. Please try again later."
    )

    # Connect the user flow nodes
    user_flow.edge(START, error_message_node)
    user_flow.edge(error_message_node, END)
    
    # Primary node - getDogFact with error branching configuration
    dog_fact_node = aflow.tool(
        "getDogFact",
        error_handler_config=NodeErrorHandlerConfig(
            error_message="Failed to get dog facts, showing error message to user",
            max_retries=0,  # No retries, branch immediately on error
            retry_interval=1000,
            on_error="branch",  # Enable error branching
            error_edge_id="dog_error_to_user_message"  # Edge ID for error path
        )
    )

    # Main flow sequence
    aflow.sequence(START, dog_fact_node, END)
    
    # Error branching path: if getDogFact fails, show user activity message
    # Note: The edge id must match the error_edge_id in error_handler_config
    aflow.edge(dog_fact_node, user_flow, id="dog_error_to_user_message")
    aflow.edge(user_flow, END)

    return aflow
