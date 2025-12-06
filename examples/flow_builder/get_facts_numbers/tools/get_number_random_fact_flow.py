'''
Build a get random fact about inputted number flow
'''

from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import END, Flow, flow, START
from .get_facts_about_numbers import get_facts_about_numbers
from .get_request_status import get_request_status

class InputtedNumber(BaseModel):
    number: int = Field(description="Inputted number from user")

class Attempt(BaseModel):
    atmp: int = Field(description="Represent each attemp to check if the request is finish", default=0)

class FlowOutput(BaseModel):
    info: str = Field(description="Fact about a number")

@flow(
    name="get_number_random_fact_flow",
    input_schema=InputtedNumber,
    output_schema=FlowOutput,
    description="A flow to get a random fact about a number"
)
def get_number_random_fact_flow(aflow: Flow) -> Flow:
    # This flow will take a number as an input and find a fact about that number.
    #
    # First, the flow executes the get_facts_about_numbers_node, which retrieves a fact
    # about the number via a fast external API call.
    #
    # In a real-world scenario, external calls may take time to complete (e.g., when made
    # through your own agent), so polling might be necessary.
    #
    # To demonstrate this polling pattern, the flow uses a while_loop that iterates 5 times.
    # On each iteration, it calls the get_request_status node and waits 1 second using a
    # timer node (instead of using sleep directly).
    #
    # After 5 polling attempts, the flow proceeds to display the fact.
    get_facts_about_numbers_node = aflow.tool(
        get_facts_about_numbers,
        error_handler_config={
            "error_message": "An error has occured while invoking the tool",
            "max_retries": 1,
            "retry_interval": 1000
        }
    )

    while_loop: Flow = aflow.loop(
        evaluator="not parent.get_request_status.input.attempt.atmp or parent.get_request_status.input.attempt.atmp < 5",
        input_schema=Attempt,
        output_schema=FlowOutput
    )

    timer_node = while_loop.timer(
        name="wait_1_sec",
        delay=1000,
        description="Wait for 1 second before polling again"
    )

    get_request_status_node = while_loop.tool(get_request_status)
    while_loop.sequence(START, get_request_status_node, timer_node, END)
    aflow.sequence(START, get_facts_about_numbers_node, while_loop, END)

    return aflow
