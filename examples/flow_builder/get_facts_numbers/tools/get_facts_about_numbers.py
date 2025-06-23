from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
import requests

class FlowOutput(BaseModel):
    info: str = Field(description="Fact about a number")

@tool(
    permission=ToolPermission.READ_ONLY
)
def get_facts_about_numbers(number: int) -> FlowOutput:
    """
    Returns an Info object which is a fact about a number

    Args:
        number (int): a number to get the fact.

    Returns:
        Info: A Info object
    """
    url = f'http://numbersapi.com/{number}'

    response = requests.get(url)

    if response.status_code == 200:
        return FlowOutput(info=response.text)
    return FlowOutput(info=f"{number} is a lucky number")