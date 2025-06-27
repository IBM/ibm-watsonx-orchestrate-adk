from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
import time

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
    attempt['atmp'] += 1 
    time.sleep(1)
    return attempt