from pydantic import BaseModel, Field
from typing import Optional
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

class ProcessedOutput(BaseModel):
    user_id: str = Field(description="Generated user ID")
    health_insurance: str = Field(description="Health insurance number")
    middle_name: Optional[str] = Field(default=None, description="Optional middle name (nullable string)")
    status: str = Field(description="Processing status")

@tool(
    permission=ToolPermission.READ_WRITE
)
def process_user_data(username: str, ssn: str, middle_name: Optional[str] = None) -> ProcessedOutput:
    """
    Process user data and return masked sensitive information.
    
    Args:
        username: User's username
        ssn: Social Security Number (will be masked)
        middle_name: Optional middle name (will be masked if provided)
    
    Returns:
        ProcessedOutput with masked sensitive data
    """
    user_id = f"USR-{hash(username) % 100000:05d}"
    health_insurance = f"111_222_333_444_555_666"
    middle_name= f"Johanson"
    
    return ProcessedOutput(
        user_id=user_id,
        health_insurance=health_insurance,
        middle_name=middle_name,
        status="PROCESSED"
    )
