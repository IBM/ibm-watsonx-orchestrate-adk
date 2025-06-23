from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


class Fact(BaseModel):
    wind_speed: float = Field(description="Wind Speed")
    temperature: float = Field(description="Temperature")
    current_weather: str = Field(description="Current Weather")
    population: str = Field(description="Population")
    coordinates: str = Field(description="Coordinates")
    city: str = Field(description="City Name")
    founding_date: str = Field(description="City Founding Date")

@tool(
    permission=ToolPermission.READ_ONLY
)
def aggregate_data(city: str,  coordinates: str, population : str,temperature : float, wind_speed: float, current_weather : str, founding_date: str) -> str:
    """
    Return a str object by folling this format:
    These are the info of city of {city} where its coordinates is {coordinates} and was founded on {city_founding_date}. {city} current population is {population}.
    The weather is {current_weather}, temperature is {temperature}C and wind speed is {wind_speed} mph.
    Args:
        fact (Fact): Fact object

    Returns:
        str: A str object
    """

    return f"These are the info of city of {city} where its coordinates is {coordinates} and was founded on {founding_date}.\
    {city} current population is {population}. The weather is {current_weather}, temperature is {temperature}C and wind speed is {wind_speed} mph."