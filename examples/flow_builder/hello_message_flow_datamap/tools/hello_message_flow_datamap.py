'''
Build a simple hello world flow that will combine the result of two tools.
'''

from pydantic import BaseModel
from ibm_watsonx_orchestrate.flow_builder.flows import END, Flow, flow, START

from .get_hello_message import get_hello_message
from .combine_names import combine_names

class Name(BaseModel):
    """
    This class represents a person's name.

    Attributes:
        first_name (str): The person's first name.
        last_name (str): The person's last name.
    """
    first_name: str
    last_name: str

class Message(BaseModel):
    msg: str

@flow(
        name = "hello_message_flow_datamap",
        input_schema=Name,
        output_schema=Message
    )
def build_hello_message_flow_datamap(aflow: Flow = None) -> Flow:
    """
    Creates a flow with two tools: get_hello_message and combine_names.
    Args:
        flow (Flow, optional): The flow to be built. Defaults to None.
    Returns:
        Flow: The created flow.
    """
    combine_names_node = aflow.tool(combine_names)
    combine_names_node.map_input(input_variable="first_name", expression="flow.input.first_name")
    combine_names_node.map_input(input_variable="last_name", expression="flow.input.last_name", default_value="default_last_name")

    get_hello_message_node = aflow.tool(get_hello_message)
    get_hello_message_node.map_input(input_variable="name", expression="flow.combine_names.output")


    aflow.edge(START, combine_names_node).edge(combine_names_node, get_hello_message_node).edge(get_hello_message_node, END)

    aflow.map_output(output_variable="msg", expression="flow.get_hello_message.output")

    return aflow
