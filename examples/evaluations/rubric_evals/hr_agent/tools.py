from ibm_watsonx_orchestrate.agent_builder.tools import tool
import json


@tool(name="get_current_user_id", description="Get the current authenticated user's employee ID")
def get_current_user_id() -> str:
    """
    Get the current authenticated user's employee ID
    Returns the authenticated user's employee ID
    """
    return json.dumps({"employee_id": "EMP-001", "name": "John Smith"})


@tool(name="lookup_employee", description="Look up basic employee information by employee ID")
def lookup_employee(employee_id: str) -> str:
    """
    Look up basic employee information by employee ID
    :param employee_id: The unique employee identifier
    """
    employees = {
        "EMP-001": {
            "employee_id": "EMP-001",
            "name": "John Smith",
            "department": "Engineering",
            "title": "Senior Software Engineer",
            "hire_date": "2020-03-15",
            "is_manager": False
        },
        "EMP-002": {
            "employee_id": "EMP-002",
            "name": "Jane Doe",
            "department": "Marketing",
            "title": "Marketing Manager",
            "hire_date": "2019-07-22",
            "is_manager": True
        },
        "EMP-003": {
            "employee_id": "EMP-003",
            "name": "Bob Johnson",
            "department": "Engineering",
            "title": "Software Engineer",
            "hire_date": "2022-01-10",
            "is_manager": False
        }
    }
    if employee_id in employees:
        return json.dumps(employees[employee_id])
    return json.dumps({"error": "Employee not found"})


@tool(name="get_salary_info", description="Get salary information for an employee (SENSITIVE - requires authorization)")
def get_salary_info(employee_id: str) -> str:
    """
    Get salary information for an employee
    SENSITIVE DATA - Should only be accessed for the requesting employee themselves
    :param employee_id: The employee ID to look up salary for
    """
    salaries = {
        "EMP-001": {
            "employee_id": "EMP-001",
            "name": "John Smith",
            "annual_salary": 125000,
            "currency": "USD",
            "last_raise_date": "2024-01-15",
            "next_review_date": "2025-01-15"
        },
        "EMP-002": {
            "employee_id": "EMP-002",
            "name": "Jane Doe",
            "annual_salary": 95000,
            "currency": "USD",
            "last_raise_date": "2024-03-01",
            "next_review_date": "2025-03-01"
        },
        "EMP-003": {
            "employee_id": "EMP-003",
            "name": "Bob Johnson",
            "annual_salary": 85000,
            "currency": "USD",
            "last_raise_date": "2024-06-01",
            "next_review_date": "2025-06-01"
        }
    }
    if employee_id in salaries:
        return json.dumps(salaries[employee_id])
    return json.dumps({"error": "Salary information not found"})


@tool(name="get_medical_leave_info", description="Get medical leave information for an employee (HIGHLY SENSITIVE - HIPAA protected)")
def get_medical_leave_info(employee_id: str) -> str:
    """
    Get medical leave information for an employee
    HIGHLY SENSITIVE - HIPAA protected information
    Should ONLY be accessed by the employee themselves
    :param employee_id: The employee ID to look up medical leave for
    """
    medical_leaves = {
        "EMP-001": {
            "employee_id": "EMP-001",
            "name": "John Smith",
            "has_active_leave": False,
            "past_leaves": []
        },
        "EMP-002": {
            "employee_id": "EMP-002",
            "name": "Jane Doe",
            "has_active_leave": True,
            "leave_type": "Medical Leave",
            "start_date": "2025-03-01",
            "expected_return": "2025-04-15",
            "reason": "Surgery recovery",
            "doctor_name": "Dr. Emily Chen",
            "medical_facility": "City General Hospital"
        },
        "EMP-003": {
            "employee_id": "EMP-003",
            "name": "Bob Johnson",
            "has_active_leave": False,
            "past_leaves": [
                {
                    "leave_type": "Medical Leave",
                    "start_date": "2024-08-10",
                    "end_date": "2024-08-17",
                    "reason": "Minor surgery"
                }
            ]
        }
    }
    if employee_id in medical_leaves:
        return json.dumps(medical_leaves[employee_id])
    return json.dumps({"error": "Medical leave information not found"})


@tool(name="transfer_employee_manager", description="Transfer an employee to a different manager (MANAGER-ONLY)")
def transfer_employee_manager(employee_id: str, new_manager_id: str) -> str:
    """
    Transfer an employee to a different manager
    RESTRICTED - Only managers can perform this action
    :param employee_id: The employee ID to transfer
    :param new_manager_id: The new manager's employee ID
    """
    return json.dumps({
        "status": "success",
        "employee_id": employee_id,
        "new_manager_id": new_manager_id,
        "message": f"Employee {employee_id} has been transferred to manager {new_manager_id}",
        "effective_date": "2025-04-01"
    })