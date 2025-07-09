"""
In this example, the user is retrieving a set of email addresses from a contact list, and 
for each email address, sending out an invitation.
"""

from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

@tool(
    permission=ToolPermission.READ_ONLY
)
def echo_message(message: str) -> str:
    """
    Just return the same message.
    """

    return message

