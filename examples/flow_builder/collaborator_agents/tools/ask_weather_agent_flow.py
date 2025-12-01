from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)
from pydantic import BaseModel, Field


class FlowOutput(BaseModel):
    result: str = Field(description="Information about a city")

class FlowInput(BaseModel):
    city: str = Field(description="City Name")

class WeatherData(BaseModel):
    wind_speed: float = Field(description="Wind Speed")
    temperature: float = Field(description="Temperature")
    current_weather: str = Field(description="Current Weather")


@flow(
    name = "ask_weather_agent_flow",
    input_schema=FlowInput,
    output_schema=FlowOutput
)
def build_ask_weather_agent_flow(aflow: Flow) -> Flow:
    """
    Return city weather.
    """
    # Flow will take an input 'city' which is a city. Try to input one of these four cities: San Jose, Fremont, New York or Los Angeles
    # The agent will take city as an input and look up real time weather data
    # and generete a str based on those input
    # e:g input: Fremont
    #     output: The weather is overcast, temperature is 14C and wind speed is 11 mph.

    ask_weather_agent = aflow.agent(
        name="ask_weather_agent",
        agent="weather_agent",
        description="Ask the agent to get information about weather in a city",
        message="Give a real time weather data in provided city",
        input_schema=FlowInput,
        output_schema=WeatherData
    )

    aflow.sequence(START, ask_weather_agent, END)
    return aflow
