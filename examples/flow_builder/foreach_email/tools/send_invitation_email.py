"""
In this example, the user is retrieving a set of email addresses from a contact list, and 
for each email address, sending out an invitation.
"""

from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

class CustomerRecord(BaseModel):
    '''TODO: Docstring'''
    name: str| None = Field(description="The name of the customer")
    email: str | None = Field(description="The email address of the customer")

@tool(
    permission=ToolPermission.READ_ONLY
)
def send_invitation_email(record: CustomerRecord) -> str:
    """
    Send an invitation email to a given email address. 
    Returns the email body that was sent.
    """
    return f"Sending invitation email to {record['email']} with the message: Hello {record['name']}! Please join us!"

