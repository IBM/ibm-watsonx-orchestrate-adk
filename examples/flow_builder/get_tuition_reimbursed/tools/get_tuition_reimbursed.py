from typing import List
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END, Branch
)
from ibm_watsonx_orchestrate.flow_builder.types import Assignment, MatchPolicy
from .auto_approval import auto_approval
from .auto_denial import auto_deny_request
from .require_manager_approval import require_manager_approval
from .get_requests import get_requests
from pydantic import BaseModel, Field

class RequestID(BaseModel):
    ids: str = Field(description="a series of id seperated by comma")

class RequestInfo(BaseModel):
    tuition_amount: int = Field(description="Tuition amount")
    overall_grade: str = Field(description="OverAll Grade")
    is_fulltime: bool = Field(description="Employee's employment status")
    first_name: str = Field(description="Employee's first name")
    last_name: str = Field(description="Employee's first name")

class RequestResults(BaseModel):
    results: List[str]

@flow(
    name = "get_tuition_reimbursed",
    input_schema=RequestID,
    output_schema=str,
    description="A flow can take employee id and find if they are eligible for tuition reimbursed"
)
def build_get_tuition_reimbursed_flow(aflow: Flow) -> Flow:
    # The flow will take ids as an input which is a string: eg : "1,2"
    # each id will represent an employee id.
    # The flow will go to get_requests_info_node to get employee information and return corresponding employee information
    #     {
    #         "1" : RequestInfo(tuition_amount=10000, overall_grade="A",is_fulltime=True, first_name="Boogey", last_name="Man"),
    #         "2" : RequestInfo(tuition_amount=9000, overall_grade="B",is_fulltime=True, first_name="Invisible", last_name="Man"),
    #         "3" : RequestInfo(tuition_amount=8000, overall_grade="C",is_fulltime=True, first_name="Aqua", last_name="Man"),
    #         "4" : RequestInfo(tuition_amount=7777, overall_grade="A",is_fulltime=False, first_name="Bat", last_name="Man"),
    #         "5" : RequestInfo(tuition_amount=7777, overall_grade="A",is_fulltime=False, first_name="Ant", last_name="Man"),
    #     }
    # After getting employee information, each employee will be checked based on this criteria:
    #    if employee employment status is not full time: -> AUTO DENY
    #    else :
    #       if employee tuition amount is greater than 10000: -> AUTO DENY
    #       else:
    #          if employee over all grade is A: -> AUTO APPROVE
    #          else:
    #             if employee over all grade is B: -> REQUIRE APPROVAL FROM MANAGER
    #             else:
    #               if employee over all grade is C: -> AUTO DENY
    # e.g:   input:  {"ids" : "1,2"}
    #        ouput:
    #           Employee Boogey Man(FULL-TIME) with a request of tuition 10000 and over all grade A is automatically APPROVED. 
    #           Employee Invisible Man(FULL-TIME) with a request of tuition 9000 and over all grade B requires MANAGER APPROVAL.
    foreach_flow: Flow = aflow.foreach(item_schema=RequestInfo, output_schema=RequestResults)
    
    auto_denial_node = foreach_flow.tool(auto_deny_request, input_schema=RequestInfo, output_schema=str)
    
    auto_approval_node = foreach_flow.tool(auto_approval,input_schema=RequestInfo, output_schema=str)
    
    require_manager_approval_node = foreach_flow.tool(require_manager_approval,input_schema=RequestInfo, output_schema=str)
    
    check_overall_grade_branch: Branch = (foreach_flow.branch(evaluator="parent._current_item.overall_grade.strip().upper()")\
                    .case("A",auto_approval_node)\
                    .case("B", require_manager_approval_node)\
                    .case("C", auto_denial_node)\
                    .default(auto_denial_node)
                    )
    check_amount_branch: Branch = foreach_flow.branch(evaluator="parent._current_item.tuition_amount > 10000")\
                            .case(True, auto_denial_node)\
                            .case(False,check_overall_grade_branch)
    
    check_fulltime_branch: Branch = foreach_flow.branch(evaluator="parent._current_item.is_fulltime == True")\
                                .case(True, check_amount_branch)\
                                .case(False,auto_denial_node)
    foreach_flow.edge(START, check_fulltime_branch)
    foreach_flow.edge(auto_denial_node, END)
    foreach_flow.edge(require_manager_approval_node, END)
    foreach_flow.edge(auto_approval_node, END)
    
    get_requests_info_node = aflow.tool(get_requests, input_schema=RequestID, output_schema=RequestInfo)

    aflow.sequence(START, get_requests_info_node, foreach_flow, END)
    return aflow

