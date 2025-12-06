from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from pydantic import BaseModel, Field

class RequestInfo(BaseModel):
    tuition_amount: int = Field(description="Tuition amount")
    overall_grade: str = Field(description="OverAll Grade")
    is_fulltime: bool = Field(description="Employee's employment status")
    first_name: str = Field(description="Employee's first name")
    last_name: str = Field(description="Employee's first name")


@tool(
    permission=ToolPermission.READ_ONLY
)
def require_manager_approval(request: RequestInfo) -> str:
    """
    Return a message 
    Args:
        request (RequestInfo): Request Info inpt

    Returns:
        str: A message based on request
    """
    ft = "FULL-TIME" if request.is_fulltime is True else "INTERN"
    return f"Employee {request.first_name} {request.last_name}({ft}) with a request of tuition {request.tuition_amount} and over all grade {request.overall_grade} requires MANAGER APPROVAL."