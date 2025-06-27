'''
Build a get random fact about inputted number flow
'''

from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import END, Flow, flow, START
from .get_facts_about_numbers import get_facts_about_numbers
from .get_request_status import get_request_status

class InputtedNumber(BaseModel):
    number : int = Field(description="Inputted number from user")

class Attempt(BaseModel):
    atmp : int = Field(description="Represent each attemp to check if the request is finish", default=0)


class FlowOutput(BaseModel):
    info: str = Field(description="Fact about a number")

@flow(
    name = "get_number_random_fact_flow",
    input_schema=InputtedNumber,
    output_schema=FlowOutput

)
def get_number_random_fact_flow(aflow: Flow) -> Flow:
    # This flow will take a number as an input and find a fact about that number.

    # First, the flow will go to get_facts_about_numbers_node to get the fact of the number by making a request
    # to an external API. The request to an external only take some ms to complete.

    # There is one scenario when you have your own agent and make an external call to a source which takes sometime to complete.
    # So you might want to use the while loop to query the tool which is used to make that external call until it is completed.
    # For demonstration purpose of the scenario above and show how while loop works,
    # we mimic the behavior by get the flow executes the while_loop node to loop 5 times. Each time, it will go to get_request_status node and sleep for 1s.
    # After 5 attempts, the flow will display the fact of the number
    
    get_facts_about_numbers_node = aflow.tool(get_facts_about_numbers, input_schema=InputtedNumber, output_schema=FlowOutput)

    while_loop: Flow = aflow.loop(evaluator = "\"get_request_status\" not in parent or parent.get_request_status.input.attempt.atmp < 5",
                                                    input_schema=Attempt,
                                                    output_schema=FlowOutput)
    get_request_status_node =  while_loop.tool(get_request_status)
    
    while_loop.sequence(START, get_request_status_node, END)

    aflow.sequence(START, get_facts_about_numbers_node, while_loop, END)

    return aflow
