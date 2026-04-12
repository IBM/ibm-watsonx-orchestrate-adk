from typing import List
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from pydantic import BaseModel, Field
class RequestID(BaseModel):
    ids: str = Field(description="a series of id seperated by comma")

class RequestInfo(BaseModel):
    tuition_amount: int = Field(description="Tuition amount")
    overall_grade: str = Field(description="OverAll Grade")
    is_fulltime: bool = Field(description="Employee's employment status")
    first_name: str = Field(description="Employee's first name")
    last_name: str = Field(description="Employee's first name")

@tool(
    permission=ToolPermission.READ_ONLY
)
def get_requests(request: RequestID) -> List[RequestInfo]:
    """
    Returns a list of RequestInfo object that match the request['ids']

    Args:
        request (RequestID):  RequestID Pydantic model

    Returns:
        List[RequestInfo]: A list of RequestInfo object
    """
    req = {
            "1" : RequestInfo(tuition_amount=10000, overall_grade="A",is_fulltime=True, first_name="Boogey", last_name="Man"),
            "2" : RequestInfo(tuition_amount=9000, overall_grade="B",is_fulltime=True, first_name="Invisible", last_name="Man"),
            "3" : RequestInfo(tuition_amount=8000, overall_grade="C",is_fulltime=True, first_name="Aqua", last_name="Man"),
            "4" : RequestInfo(tuition_amount=7777, overall_grade="A",is_fulltime=False, first_name="Bat", last_name="Man"),
            "5" : RequestInfo(tuition_amount=7777, overall_grade="A",is_fulltime=False, first_name="Ant", last_name="Man"),
        }
    res = []
    if request and request.ids is not None:
        for n in request.ids.split(","):
            if n in req.keys():
                res.append(req[n])
    return res