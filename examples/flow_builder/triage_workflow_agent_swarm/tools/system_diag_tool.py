import random
from ibm_watsonx_orchestrate.agent_builder.tools import tool

@tool
def system_diag_tool(user_id: str) -> dict:
    """
    Simulates running diagnostic checks against the user's system configuration and logs.

    Args:
        user_id: The unique identifier of the user account.

    Returns:
        A dictionary containing the diagnostic status and any identified errors.
    """
    print(f"--- System Diag Tool Called: Running diagnostics for ID: {user_id} ---")

    # Simulate random errors for demonstration
    r = random.random()

    if r < 0.2:
        # Simulate a clean diagnosis
        return {
            "status": "clean",
            "message": "No critical errors found in system logs or account configuration.",
            "data": {"last_login_attempt": "2025-11-25 09:30:00 EST", "config_version": "v3.1.2"}
        }
    elif r < 0.6:
        # Simulate a technical error
        return {
            "status": "error_found",
            "message": "Found repeated 'Session Token Expired' errors.",
            "data": {"critical_error_code": "STX-701", "recommended_action": "Force session reset."}
        }
    else:
        # Simulate a non-technical error that requires Billing intervention
        return {
            "status": "non_technical_block",
            "message": "User account is suspended due to unpaid invoice.",
            "data": {"suspension_reason": "Invoice-INV987 overdue by 30 days."}
        }