import random
from ibm_watsonx_orchestrate.agent_builder.tools import tool

@tool
def knowledge_base_tool(keyword: str) -> dict:
    """
    Simulates searching the internal knowledge base for known solutions or guides.

    Args:
        keyword: The main symptom or issue (e.g., "login failure", "app crash").

    Returns:
        A dictionary containing the search status and relevant solution articles.
    """
    print(f"--- Knowledge Base Tool Called: Searching for '{keyword}' ---")

    if "login" in keyword.lower():
        return {
            "status": "success",
            "results": [
                {"title": "KB-404: Resolving User Login Timeout Errors", "solution": "Clear cookies and try again. If failure persists, check account status via CRM."},
                {"title": "KB-405: Password Reset Form Not Working", "solution": "This is a known bug (ID: BUG-120). Workaround: use the mobile app to reset password."}
            ]
        }
    elif "crash" in keyword.lower() or "bug" in keyword.lower():
        return {
            "status": "success",
            "results": [
                {"title": "KB-512: Fixing Unexpected Application Crashes", "solution": "Ensure the application is updated to the latest version (v3.1.2). If on v3.1.1, downgrade or update immediately."}
            ]
        }
    else:
        # Simulate no relevant article found
        return {"status": "not_found", "results": []}