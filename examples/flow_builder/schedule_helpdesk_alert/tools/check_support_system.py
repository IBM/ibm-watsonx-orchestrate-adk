"""
In this example, the user is retrieving a set of email addresses from a contact list, and 
for each email address, sending out an invitation.
"""

import random
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

class Product(BaseModel):
    product_name: str = Field(description="The product that we should search for support alert.")

class Alert(BaseModel):
    product_name: str = Field(description="The product that we should search for support alert.")
    high_priority_tickets: int = Field(description="Number of high priority tickets")
    medium_priority_tickets: int = Field(description="Number of medium priority tickets")   
    low_priority_tickets: int = Field(description="Number of low priority tickets") 

@tool(
    permission=ToolPermission.READ_ONLY
)
def check_support_system() -> Alert:
    """
    Check support system and return current set of open tickets
    """

    alert = Alert(
        product_name="CRM",
        high_priority_tickets=random.randint(0, 5),
        medium_priority_tickets=random.randint(3, 10),
        low_priority_tickets=random.randint(5, 15)
    )
    return alert

