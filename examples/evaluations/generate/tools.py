from datetime import datetime
import json
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

# Utility function
def _is_valid_date(date_str: str) -> bool:
    """Check if the provided date string is in YYYY-MM-DD format."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


@tool(name="fetch_assignment_id", description="Fetch assignment ID using employee username.", permission=ToolPermission.ADMIN)
def fetch_assignment_id(username: str) -> str:
    """
    Return the assignment ID for a given employee username.
    
    :param username: Employee's username
    :return: Assignment ID as a string or 'not found'
    """
    assignment_ids = {
        "nwaters": "15778303",
        "johndoe": "15338303",
        "nken": "15338304"
    }
    return assignment_ids.get(username, "not found")


@tool(name="retrieve_timeoff_schedule", description="Retrieve employee time-off schedule within a date range.", permission=ToolPermission.ADMIN)
def retrieve_timeoff_schedule(assignment_id: str, start_date: str, end_date: str) -> str:
    """
    Get time-off schedule for an employee within a given date range.
    
    :param assignment_id: Assignment ID of the employee
    :param start_date: Start date in YYYY-MM-DD format
    :param end_date: End date in YYYY-MM-DD format
    :return: JSON list of time-off dates or error message
    """
    if not _is_valid_date(start_date):
        return f"Invalid date format: {start_date}. Expected YYYY-MM-DD."
    if not _is_valid_date(end_date):
        return f"Invalid date format: {end_date}. Expected YYYY-MM-DD."

    timeoff_data = {
        "15338303": ["2025-04-11", "2025-03-11", "2025-01-01"],
        "15778303": ["2025-01-05"],
        "15338304": ["2025-01-15", "2025-02-20"]
    }

    return timeoff_data.get(assignment_id, [])


@tool(name="list_direct_reports", description="List direct reports for a given manager's assignment ID.", permission=ToolPermission.ADMIN)
def list_direct_reports(manager_assignment_id: str) -> str:
    """
    Retrieve the list of direct report Employee's username for a specified manager's assignment ID.

    :param manager_assignment_id: Assignment ID of the manager as a string
    :return: JSON-encoded list of Employee's username who report to the manager
    """
    mock_reports = {
        "15778303": ["johndoe", "nken"],
        "15338303": [],
        "15338304": []
    }

    return mock_reports.get(manager_assignment_id, [])

@tool(name="get_address_type", description="Get address type ID based on the address type name (e.g., 'Home', 'Work').", permission=ToolPermission.ADMIN)
def get_address_type(address_type_name: str) -> str:
    """
    Retrieve a string address type ID based on a given address type name.

    :param address_type_name: Address type as a string
    :return: Corresponding string address_type_id or -1 if not found
    """
    address_type_map = {
        "Home": "1",
        "Work": "2",
        "Other": "3"
    }

    return address_type_map.get(address_type_name.capitalize(), "-1")


@tool(name="update_address", description="Update the address for a given assignment ID and address type.", permission=ToolPermission.ADMIN)
def update_address(address_type_id: str, assignment_id: str, new_address: str) -> str:
    """
    Update the address for an employee based on assignment ID and address type.

    :param address_type_id: String representing the address type
    :param assignment_id: Employee's assignment ID
    :param new_address: New address string
    :return: Success or error message
    """
    if address_type_id not in ["1", "2", "3"]:
        return "Invalid address type ID."

    if not assignment_id or not new_address:
        return "Assignment ID and new address must be provided."

    # Simulated update logic
    return f"Address for assignment ID {assignment_id} updated to '{new_address}' (Type ID: {address_type_id})."
