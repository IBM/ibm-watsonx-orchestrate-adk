

from typing import List
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, UserNode, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import Assignment, UserFieldKind
from ibm_watsonx_orchestrate.flow_builder.data_map import DataMap

class Name(BaseModel):
    """
    This class represents a person's name.

    Attributes:
        name (str): The person's first name.
    """
    first_name: str = Field(default="John Doe", description="First name")

@flow(
    name ="user_flow_example",
    display_name="user_flow_example",
    description="Example user flow.",
    input_schema=Name,
)
def build_user_flow(aflow: Flow = None) -> Flow:
    # user_flow which is a subflow to be added to the aflow
    user_flow = aflow.userflow()




    # add file upload
    user_node1 = user_flow.field(direction="input",name="upload", display_name="File upload 1",  kind=UserFieldKind.File)

    # add file download
    data_map = DataMap()
    data_map.add(Assignment(target_variable="self.input.value",value_expression="flow[\"userflow_1\"][\"File upload 1\"].output.value"))
    user_node2 = user_flow.field(direction="output",name="download", display_name="Download file",  kind=UserFieldKind.File, input_map=data_map)

    # add a Display user text field
    user_node3 = user_flow.field(direction="output",name="display_first_name", display_name="Display first name", kind=UserFieldKind.Text, text="Display of first name is {flow.input.first_name}")

    # add a text input field
    user_node4 = user_flow.field(direction="input",name="last_name", display_name="Last name",  kind=UserFieldKind.Text, text="Enter last name")
    
    # add a Number input field
    user_node5 = user_flow.field(direction="input",name="age", display_name="Age",  kind=UserFieldKind.Number, text="Enter Age")

    # create a data map to build an array to be assigned to a user field of kind List
    data_map = DataMap()
    data_map.add(Assignment(target_variable="self.input.value",value_expression="[\"Alice\", \"Bob\", \"Charlie\", \"Diana\", \"Ethan\", \"Fiona\", \"George\"]"))
    user_node6 = user_flow.field(direction="output",name="Friends", display_name="List of friends", kind=UserFieldKind.List, input_map=data_map)

    # A user flow edges
    user_flow.edge(START, user_node1)
    user_flow.edge(user_node1, user_node2)
    user_flow.edge(user_node2, user_node3)
    user_flow.edge(user_node3, user_node4)
    user_flow.edge(user_node4, user_node5)
    user_flow.edge(user_node5, user_node6)
    user_flow.edge(user_node6, END)
    
    # add the user flow to the flow sequence to create the flow edges
    aflow.sequence(START, user_flow, END)

    return aflow
