from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from pydantic import BaseModel, Field


class FlowOutput(BaseModel):
    result: str = Field(description="Information about a city")

class FlowInput(BaseModel):
    city: str = Field(description="City Name")

class CityFoundingDate(BaseModel):
    founding_date: str = Field(description="Founding Date")
    

@flow(
    name = "ask_city_founding_date_agent_flow",
    input_schema=FlowInput,
    output_schema=FlowOutput
)
def build_ask_city_founding_date_agent_flow(aflow: Flow) -> Flow:
    """
    Return city founding date.
    """
    # Flow will take an input 'city' which is a city. Try to input one of these four cities: San Jose, Fremont, New York or Los Angeles
    # The agent will take city as an input and look up the date which the citi was founded
    # and generete a str based on those input
    # e:g input: Fremont
    #     output: Fremont was founded on January 23, 1956.

    ask_city_founding_date_agent = aflow.agent(
        name="ask_city_founding_date_agent",
        agent="city_founding_date_agent",
        description="Ask the agent to get founding date of a city",
        message="Give a founding date in provided city",
        input_schema=FlowInput,
        output_schema=CityFoundingDate
    )

    aflow.sequence(START, ask_city_founding_date_agent, END)
    return aflow
