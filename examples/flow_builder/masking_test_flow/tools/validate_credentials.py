from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
import hashlib

class ValidationOutput(BaseModel):
    valid: bool = Field(description="Whether credentials are valid")
    token: str = Field(description="Authentication token (sensitive)")
    expires_in: int = Field(description="Token expiration time in seconds")

@tool(
    permission=ToolPermission.READ_WRITE
)
def validateCredentials(username: str, api_key: str) -> ValidationOutput:
    """
    Validate credentials and return authentication token.
    
    Args:
        username: Username to validate
        api_key: API key to validate (will be masked)
    
    Returns:
        ValidationOutput with validation result and token
    """
    is_valid = True
    token_input = f"{username}:{api_key}:validated"
    auth_token = hashlib.sha256(token_input.encode()).hexdigest()
    
    return ValidationOutput(
        valid=is_valid,
        token=auth_token,
        expires_in=3600
    )
