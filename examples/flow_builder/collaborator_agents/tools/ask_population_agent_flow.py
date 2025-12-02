from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from pydantic import BaseModel, Field


class FlowOutput(BaseModel):
    result: str = Field(description="Information about a city")

class FlowInput(BaseModel):
    city: str = Field(description="City Name")

class PopulationData(BaseModel):
    population: str = Field(description="Population")
    coordinates: str = Field(description="Coordinates")


@flow(
    name = "ask_population_agent_flow",
    input_schema=FlowInput,
    output_schema=FlowOutput
)
def build_ask_population_agent_flow(aflow: Flow) -> Flow:
    """
    Return city population.
    """
    # Flow will take an input 'city' which is a city. Try to input one of these four cities: San Jose, Fremont, New York or Los Angeles
    # The agent will take city as an input and look up current population and coordinates of the city
    # and generete a str based on those input
    # e:g input: Fremont
    #     output: Fremont current population is 2738000.

    ask_population_agent = aflow.agent(
        name="ask_population_agent",
        agent="population_agent",
        description="Ask the agent to get information about population in a city",
        message="Give a population and coordinate data in provided city",
        input_schema=FlowInput,
        output_schema=PopulationData
    )

    aflow.sequence(START, ask_population_agent, END)
    return aflow

