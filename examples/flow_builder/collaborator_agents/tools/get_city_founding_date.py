from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from pydantic import BaseModel, Field
from datetime import datetime
import requests

class CityFoundingDate(BaseModel):
    founding_date: str = Field(description="Founding Date")

@tool(
    permission=ToolPermission.READ_ONLY
)
def get_city_founding_date(city: str) -> CityFoundingDate:
    """
    Return a CityFoundingDate object
    Args:
        city (str): inputted city

    Returns:
        CityFoundingDate: A CityFoundingDate object
    """

    query = f"""
    SELECT ?cityLabel ?founding_date WHERE {{
      ?city rdfs:label "{city}"@en.
      ?city wdt:P571 ?founding_date.
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    """
    url = 'https://query.wikidata.org/sparql'
    headers = {'Accept': 'application/sparql-results+json'}
    response = requests.get(url, params={'query': query}, headers=headers)
    if response.status_code == 200:
        data = response.json()
        results = data.get("results", {}).get("bindings", [])
        if results:
            dt = datetime.strptime(results[0]['founding_date']['value'], "%Y-%m-%dT%H:%M:%SZ")
            return CityFoundingDate(founding_date=dt.strftime("%B %d, %Y"))
    return CityFoundingDate(founding_date="unknown")