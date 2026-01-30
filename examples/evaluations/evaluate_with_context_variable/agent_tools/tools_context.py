"""
Context Variable-aware HR Tools

These tools are designed to work with context variables. They extend the base HR tools
to support scenarios where user identity is provided via context variables (e.g., sap_username).
"""

from datetime import datetime
import json
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


# Mock database of users with their details
USER_DATABASE = {
    "nwaters": {
        "assignment_id": "15778303",
        "email": "nwaters@company.com",
        "full_name": "Nancy Waters",
        "department": "Engineering",
        "manager_id": "15338304"
    },
    "johndoe": {
        "assignment_id": "15338303",
        "email": "johndoe@company.com",
        "full_name": "John Doe",
        "department": "Marketing",
        "manager_id": "15338304"
    },
    "nken": {
        "assignment_id": "15338304",
        "email": "nken@company.com",
        "full_name": "Nathan Ken",
        "department": "Engineering",
        "manager_id": None,
        "is_manager": True
    },
    "asmith": {
        "assignment_id": "15448305",
        "email": "asmith@company.com",
        "full_name": "Alice Smith",
        "department": "HR",
        "manager_id": "15338304"
    }
}

# Timeoff schedules by assignment_id
TIMEOFF_DATABASE = {
    "15338303": ["2025-04-11", "2025-03-11", "2025-01-01"],
    "15778303": ["2025-01-05", "2025-02-14"],
    "15338304": ["2025-02-05", "2025-12-24", "2025-12-25"],
    "15448305": ["2025-03-15", "2025-07-04"]
}

# Direct reports by username
DIRECT_REPORTS_DATABASE = {
    "nken": ["nwaters", "johndoe", "asmith"]
}


def validate_datetime(date_text: str) -> bool:
    """Validate date format is YYYY-MM-DD"""
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return True
    except ValueError:
        return False


@tool(
    name="get_assignment_id_hr_context",
    description="Get the assignment id from username",
    permission=ToolPermission.ADMIN
)
def get_assignment_id_hr_context(username: str) -> str:
    """
    Get the assignment id from username.

    Args:
        username: Username of the employee (can be obtained from sap_username context variable)
    """
    user = USER_DATABASE.get(username)
    if user:
        return user["assignment_id"]
    return "Error: User not found"


@tool(
    name="get_timeoff_schedule_hr_context",
    description="Get timeoff schedule for employee based on assignment id, start date and end date",
    permission=ToolPermission.ADMIN
)
def get_timeoff_schedule_hr_context(assignment_id: str, start_date: str, end_date: str) -> str:
    """
    Get timeoff schedule for employee based on assignment id, start date and end date.

    Args:
        assignment_id: Assignment ID of the user
        start_date: Start date of the timeoff schedule, in YYYY-MM-DD format
        end_date: End date of the timeoff schedule, in YYYY-MM-DD format
    """
    if not validate_datetime(start_date):
        return f"Error: Incorrect date format {start_date}, should be YYYY-MM-DD"
    if not validate_datetime(end_date):
        return f"Error: Incorrect date format {end_date}, should be YYYY-MM-DD"

    timeoffs = TIMEOFF_DATABASE.get(assignment_id, [])
    if timeoffs:
        # Filter by date range
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        filtered = [
            t for t in timeoffs
            if start <= datetime.strptime(t, "%Y-%m-%d") <= end
        ]
        return json.dumps(filtered)
    return json.dumps([])


@tool(
    name="get_direct_reports_hr_context",
    description="Get direct reports for a given username",
    permission=ToolPermission.ADMIN
)
def get_direct_reports_hr_context(username: str) -> str:
    """
    Get direct reports for a given username.

    Args:
        username: Username of the manager
    """
    reports = DIRECT_REPORTS_DATABASE.get(username, [])
    return json.dumps(reports)
