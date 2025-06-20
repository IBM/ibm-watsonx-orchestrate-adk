'''
Build a simple hello world flow that will combine the result of two tools.
'''

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import END, Flow, flow, START, PromptNode

from .email_helpdesk import email_helpdesk

class Message(BaseModel):
    """
    This class represents the content of a support request message.

    Attributes:
        message (str): support request message
    """
    message: str
    requester_name: Optional[str] = Field(default=None, description="Name of the support requestor.")
    requester_email: Optional[str] = Field(default=None, description="Email address of the support requestor.")
    received_on: Optional[str|datetime] = Field(default=None, description="The date when the support message was received.")

class SupportInformation(BaseModel):
    requester_name: str | None = Field(description="Name of the support requestor.")
    requester_email: str | None = Field(description="Email address of the support requestor.")
    summary: str = Field(description="A high level summary of the support issue.")
    details: str = Field(description="Original text of the support request.")
    order_number: str | None = Field(description="The order number.")
    received_on: datetime | None = Field(description="The date when the support message was received.")

def build_prompt_node(aflow: Flow) -> PromptNode:
    prompt_node = aflow.prompt(
        name="extract_support_info",
        display_name="Extract information from a support request message.",
        description="Extract information from a support request message.",
        system_prompt=[
            "You are a customer support processing assistant, your job take the supplied support request received from email,",
            "and extract the information in the output as specified in the schema."
        ],
        user_prompt=[
            "Here is the {message}"
        ],
        llm="meta-llama/llama-3-3-70b-instruct",
        llm_parameters={    
            "temperature": 0,
            "min_new_tokens": 5,
            "max_new_tokens": 400,
            "top_k": 1,
            "stop_sequences": ["Human:", "AI:"]
        },
        input_schema=Message,
        output_schema=SupportInformation
    )
    return prompt_node

@flow(
        name = "extract_support_info",
        input_schema=Message,
        output_schema=SupportInformation
    )
def build_extract_support_info(aflow: Flow = None) -> Flow:
    """
    Creates a flow that will use the Prompt node to extract information from a support
    message, and forward the summary to the helpdesk.
    This flow will rely on the Flow engine to perform automatic data mapping at runtime.
    Args:
        flow (Flow, optional): During deployment of the flow model, it will be passed a flow instance.
    Returns:
        Flow: The created flow.
    """
    email_helpdesk_node = aflow.tool(email_helpdesk)
    prompt_node = build_prompt_node(aflow)

    aflow.sequence(START, prompt_node, email_helpdesk_node, END)

    return aflow
