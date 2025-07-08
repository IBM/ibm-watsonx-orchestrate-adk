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
        name = "hello_message_flow",
        input_schema=Name,
        output_schema=Message
    )
def build_hello_message_flow(aflow: Flow = None) -> Flow:
    """
    Creates a flow with two tools: get_hello_message and combine_names.
    This flow will rely on the Flow engine to perform automatic data mapping at runtime.
    Args:
        flow (Flow, optional): The flow to be built. Defaults to None.
    Returns:
        Flow: The created flow.
    """
    combine_names_node = aflow.tool(combine_names)
    get_hello_message_node = aflow.tool(get_hello_message, output_schema=Message)

    aflow.edge(START, combine_names_node).edge(combine_names_node, get_hello_message_node).edge(get_hello_message_node, END)

    # alternative syntax
    # aflow.sequence(START, node1, node2, END)

    # alternative 3
    # aflow.edge(START, node1)
    # aflow.edge(node1, node2)
    # aflow.edge(node2, END)

    return aflow
