from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

class Attempt(BaseModel):
    atmp : int = Field(description="Represent each attemp to check if the request is finish.", default=0)

@tool(
    permission=ToolPermission.READ_ONLY
)
def get_request_status(attempt: Attempt) -> Attempt:
    """
    Increase attemp['atmp'] by 1 according to the input

    Args:
        attempt (Attempt): A Attemp object

    Returns:
        Attempt: A Attempt object
    """
    if attempt is None:
        attempt = Attempt(atmp=0)

    if attempt and attempt.atmp is None:
        attempt.atmp = 0
        
    attempt.atmp += 1 
    return attempt