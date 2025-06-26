"""
In this example, the user is retrieving a set of email addresses from a contact list, and 
for each email address, sending out an invitation.
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

