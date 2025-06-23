"""
In this example, the user is retrieving a set of email addresses from a contact list, and 
for each email address, sending out an invitation.
"""

from typing import List

from pydantic import BaseModel, Field

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END

from .send_invitation_email import send_invitation_email
from .get_emails_from_customer import get_emails_from_customer, CustomerRecord


class CustomerName(BaseModel):
    name: str = Field(description="The name of the customer")

@flow(
    name="send_invitation_to_customer",
    input_schema=CustomerName,
    output_schema=None
)
def build_send_invitation_to_customer_flow(aflow: Flow) -> Flow:
    """ Given a list of customers, we will iterate through the list and send email to each """
    
    get_customer_list_node = aflow.tool(get_emails_from_customer)

    # calling add_foreach will create a subflow, and we can add more node to the subflow
    foreach_flow: Flow = aflow.foreach(item_schema = CustomerRecord,
                                       output_schema=CustomerRecord)
    
    node2 = foreach_flow.tool(send_invitation_email)
    foreach_flow.sequence(START, node2, END)

    # add the foreach flow to the main flow
    aflow.edge(START, get_customer_list_node)
    aflow.edge(get_customer_list_node, foreach_flow)
    aflow.edge(foreach_flow, END)

    return aflow
