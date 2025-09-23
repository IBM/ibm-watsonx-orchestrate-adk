'''
Build a simple hello world flow that will combine the result of two tools.
'''

from pydantic import BaseModel
from ibm_watsonx_orchestrate.flow_builder.flows import END, Flow, flow, START


class GreetMessage(BaseModel):
    greeting: str

@flow(
        name = "hello_message_script_flow",
        private_schema=GreetMessage
    )
def build_hello_message_script_flow(aflow: Flow = None) -> Flow:
    """
    Creates a flow with two script nodes: set_greeting_node and return_greeting_node.
    Args:
        flow (Flow, optional): The flow to be built. Defaults to None.
    Returns:
        Flow: The created flow.
    """
    set_greeting_node = aflow.script(name="codeblock_1", script="flow.private.greeting = 'How are you doing today!'")
    return_greeting_node = aflow.script(name="codeblock_2", script="self.output.message = flow.private.greeting")
    aflow.edge(START, set_greeting_node).edge(set_greeting_node, return_greeting_node).edge(return_greeting_node, END)

    return aflow
