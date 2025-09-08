from datetime import datetime
import json
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


@tool(name="get_assignment_id_hr_agent", description="get the assignment id from username", permission=ToolPermission.ADMIN)
def get_assignment_id_hr_agent(username: str) -> str:
    """
    get the assignment id from username

    Args:
        username: username of the employee
    """
    if username=="nwaters":
        return "15778303"
    if username=="johndoe":
        return "15338303"
    return "not found"

def validate_datetime(date_text):
    try:
        format = "%Y-%m-%d"
        datetime.strptime(date_text, format)
        return True
    except ValueError:
        return False


@tool(name="get_timeoff_schedule_hr_agent", description="get timeoff_schedule", permission=ToolPermission.ADMIN)
def get_timeoff_schedule_hr_agent(assignment_id: str, start_date: str, end_date: str) -> str:
    """
    get timeoff schedule for employee based on assignment id, start date and end date

    Args:
        assignment_id: assignment_id of the user
        start_date: start date of the timeoff scheduel, in YYYY-MM-DD format
        end_date: end date of the timeoff scheduel, in YYYY-MM-DD format
    """

    if not validate_datetime(start_date):
        return f"Incorrect date format {start_date}, should be YYYY-MM-DD"
    if not validate_datetime(end_date):
        return f"Incorrect date format {end_date}, should be YYYY-MM-DD"
    if assignment_id=="15338303":
        return json.dumps(["20250411", "20250311", "20250101"])
    if assignment_id=="15778303":
        return json.dumps(["20250105"])
    return []


@tool(name="get_direct_reports_hr_agent", description="get direct reports", permission=ToolPermission.ADMIN)
def get_direct_reports_hr_agent(username: str) -> str:
    """
    get direct reports for a given username

    Args:
        username: username of the user you want to get reports for
    """

    return json.dumps(["nwaters", "johndoe"])

@tool(name="request_compensation_change_hr_agent", description="Request a compensation change for a user", permission=ToolPermission.ADMIN)
def request_compensation_change_hr_agent(user_id: str, new_compensation: float) -> str:
    """
    Request a compensation change for a user.

    Args:
        user_id: The ID of the user whose compensation is to be changed.
        new_compensation: The new compensation amount.
    """
    return f"Compensation change requested for user {user_id} to {new_compensation}."
