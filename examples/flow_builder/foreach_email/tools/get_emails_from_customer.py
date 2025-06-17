"""
In this example, the user is retrieving a set of email addresses from a contact list, and 
for each email address, sending out an invitation.
"""

from typing import List

from pydantic import BaseModel, Field

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

class CustomerRecord(BaseModel):
    name: str = Field(description="The name of the customer")
    email: str = Field(description="The email address of the customer")

@tool(
    permission=ToolPermission.READ_ONLY
)
def get_emails_from_customer(customer_name: str) -> List[CustomerRecord]:
    """
    Returns a list of email addresses based on the provided search string.

    Args:
        customer_name (str): The string to search for in email addresses.

    Returns:
        List[str]: A list of email addresses that match the search string.
    """
    return [CustomerRecord(name='Allen', email='allen@acme.com'),
            CustomerRecord(name='Sebastian', email='sebastian@acme.com')]

