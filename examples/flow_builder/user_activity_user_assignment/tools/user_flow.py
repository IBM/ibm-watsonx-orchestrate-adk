

from ibm_watsonx_orchestrate.flow_builder.flows.flow import UserFlow


from typing import List
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, UserNode, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import Assignment, UserAssignmentPolicy, UserFieldKind
from ibm_watsonx_orchestrate.flow_builder.data_map import DataMap
from ibm_watsonx_orchestrate_core.types.tools.types import WXOUser

class Name(BaseModel):
    """
    This class represents a person's name.

    Attributes:
        name (str): The person's first name.
    """
    first_name: str = Field(default="John Doe", description="First name")

class PrivateData(BaseModel):
    """
    Private data schema for the flow.
    
    Attributes:
        designated (WXOUser): The designated user for this flow
    """
    designated: WXOUser = Field(
        description="The designated user that will run the user flow"
    )
@flow(
    name ="user_flow_assigned_user",
    display_name="user_flow_assigned_user",
    description="Example of a user flow send to a different user than the initiator.",
    input_schema=Name,
    private_schema=PrivateData
)
def build_user_flow(aflow: Flow = None) -> Flow:
    
    init_script = """flow.private.designated = system.user.search_by_email('wxo.archer@ibm.com')[0]"""
    
    # TODO if running in a non local environment, replace with a real user email.
    # init_script = """flow.private.designated = system.user.search_by_email('user_email')[0]"""
    
    init_data = aflow.script(name="init_data", script=init_script)
    
    # user_flow which is a subflow to be added to the aflow
    user_flow: UserFlow = aflow.userflow()
    user_flow.assign_to(policy=UserAssignmentPolicy.USER, assignees='flow.private.designated')

    # add a text input field
    user_node1 = user_flow.field(direction="input",name="last_name", display_name="Last name",  kind=UserFieldKind.Text, text="Enter last name")

   # add user_flow edges
    user_flow.edge(START, user_node1)
    user_flow.edge(user_node1, END)


    initiator_user_flow: UserFlow = aflow.userflow()
    initiator_user_flow.assign_to(policy=UserAssignmentPolicy.FLOW_INITIATOR)
    # add a Display user text field
    user_node2 = initiator_user_flow.field(direction="output",name="display_first_name", display_name="Display the name", kind=UserFieldKind.Text, text="Welcome {flow.userflow_1[\"Last name\"].output.value}")

    initiator_user_flow.edge(START, user_node2)
    initiator_user_flow.edge(user_node2, END) 
    
    # add the user_flow to the flow sequence to create the flow edges
    aflow.edge(START, init_data)
    aflow.edge(init_data, user_flow)
    aflow.edge(user_flow, initiator_user_flow)
    aflow.edge(initiator_user_flow, END)

    return aflow
