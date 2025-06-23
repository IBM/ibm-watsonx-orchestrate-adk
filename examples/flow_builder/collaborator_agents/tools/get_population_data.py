from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from pydantic import BaseModel, Field
import requests
class PopulationData(BaseModel):
    population: str = Field(description="Population")
    coordinates: str = Field(description="Coordinates")

@tool(
    permission=ToolPermission.READ_ONLY
)
def get_population_data(city: str) -> PopulationData:
    """
    Return a PopulationData object
    Args:
        city (str): inputted city

    Returns:
        PopulationData: A PopulationData object
    """

    url = "https://public.opendatasoft.com/api/records/1.0/search/"
    params = {
        'dataset': 'geonames-all-cities-with-a-population-1000',
        'q': city,
        'rows': 1
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['records']:
            city_info = data['records'][0]['fields']
            return PopulationData(population=str((city_info.get('population') - 1000) * 1000),coordinates=",".join([str(x) for x in city_info.get('coordinates')]))
        return PopulationData(population="UNKNOWN",coordinates="UNKNOWN")
    return PopulationData(population="UNKNOWN",coordinates="UNKNOWN")