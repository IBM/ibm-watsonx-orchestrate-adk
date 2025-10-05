import requests
from ibm_watsonx_orchestrate.agent_builder.tools import tool
from typing import List, Dict, Union


@tool()
def get_universities_by_country(country: str) -> Union[List[Dict], Dict]:
    """Get a list of universities for a specific country.

    Args:
        country (str): The name of the country to search for universities.

    Returns:
        list: A list of universities in the specified country.
    """
    url = f"http://universities.hipolabs.com/search?country={country}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        universities = response.json()
        
        # Format the response to be more readable
        formatted_universities = []
        for university in universities:
            formatted_university = {
                "name": university.get("name", ""),
                "country": university.get("country", ""),
                "state_province": university.get("state-province", ""),
                "website": university.get("web_pages", [""])[0] if university.get("web_pages") else "",
                "domains": university.get("domains", [])
            }
            formatted_universities.append(formatted_university)
        
        return formatted_universities
    except Exception as e:
        return {"error": str(e)}  # Error case returns a dictionary

# Made with Bob
