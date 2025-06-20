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

class PopulationData(BaseModel):
    population: str = Field(description="Population")
    coordinates: str = Field(description="Coordinates")

class CityFoundingDate(BaseModel):
    founding_date: str = Field(description="Founding Date")

class Fact(BaseModel):
    wind_speed: float = Field(description="Wind Speed")
    temperature: float = Field(description="Temperature")
    current_weather: str = Field(description="Current Weather")
    population: str = Field(description="Population")
    coordinates: str = Field(description="Coordinates")
    city: str = Field(description="City Name")
    founding_date: str = Field(description="City Founding Date")


@flow(
    name = "collaborator_agents_flow",
    input_schema=FlowInput,
    output_schema=FlowOutput
)
def build_collaborator_agents_flow(aflow: Flow) -> Flow:
    """
    Return information about a city.
    """
    # Flow will take an input 'city' which is a city. Try to input one of these four cities: San Jose, Fremont, New York or Los Angeles
    # 1st agent will take city as an input and look up the date which the citi was founded
    # 2nd agent will take city as an input and look up real time weather data
    # 3rd agent will take city as an input and look up current population and coordinates of the city
    # 4th agent will take the results from 3 agents above as an input:
    #     city: str,  coordinates: str, population : str,temperature : float, wind_speed: float, current_weather : str, founding_date: str
    # and generete a str based on those input
    # e:g input: Fremont
    #     output: These are the info of city of Fremont where its coordinates is 42.99092,-71.14256 and was founded on January 23, 1956.
    #               Fremont current population is 2738000. The weather is overcast, temperature is 14C and wind speed is 11 mph.

    ask_city_founding_date_agent = aflow.agent(
        name="ask_city_founding_date_agent",
        agent="city_founding_date_agent",
        description="Ask the agent to get founding date of a city",
        message="Give a founding date in provided city",
        input_schema=FlowInput,
        output_schema=CityFoundingDate,
    )

    ask_weather_agent = aflow.agent(
        name="ask_weather_agent",
        agent="weather_agent",
        description="Ask the agent to get information about weather in a city",
        message="Give a real time weather data in provided city",
        input_schema=FlowInput,
        output_schema=WeatherData,
    )

    ask_population_agent = aflow.agent(
        name="ask_population_agent",
        agent="population_agent",
        description="Ask the agent to get information about population in a city",
        message="Give a population and coordinate data in provided city",
        input_schema=FlowInput,
        output_schema=PopulationData,
    )



    ask_aggregate_agent = aflow.agent(
        name="ask_aggregate_agent",
        agent="aggregate_agent",
        description="Ask the agent to aggregate information about a city",
        message="Invoke the aggregate_data tool with provided input",
        input_schema=Fact,
        output_schema=FlowOutput
    )

    aflow.sequence(START, ask_city_founding_date_agent, ask_weather_agent, ask_population_agent, ask_aggregate_agent, END)
    return aflow