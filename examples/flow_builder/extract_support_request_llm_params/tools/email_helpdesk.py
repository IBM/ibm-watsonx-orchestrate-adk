"""
In this example, the flow extracts a support request and emails the helpdesk.
"""

from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


@tool(
    permission=ToolPermission.READ_ONLY
)
def email_helpdesk(email: str) -> str:
    """
    Send an email to internal help desk.

    Args:
        email: email address

    Returns:
        The email body that was sent.
    """
    return f"Sent email to helpdesk@acme.org with the message: \n{email}."
