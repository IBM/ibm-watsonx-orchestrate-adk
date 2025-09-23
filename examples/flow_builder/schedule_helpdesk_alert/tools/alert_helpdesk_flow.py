'''
Build a simple hello world flow that will combine the result of two tools.
'''

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import END, Flow, flow, START, PromptNode, AgentNode

from .alert_helpdesk import alert_helpdesk
from .check_support_system import check_support_system

class Message(BaseModel):
    message: str = Field(description="A Message")

class Product(BaseModel):
    product_name: str = Field(description="The product that we should search for support alert.")

class Alert(BaseModel):
    product_name: str = Field(description="The product that we should search for support alert.")
    high_priority_tickets: int = Field(description="Number of high priority tickets")
    medium_priority_tickets: int = Field(description="Number of medium priority tickets")   
    low_priority_tickets: int = Field(description="Number of low priority tickets") 

def build_alert_message_node(aflow: Flow) -> PromptNode:
    prompt_node = aflow.prompt(
        name="generate_alert_message",
        display_name="Generate a simple alert message.",
        description="Generate a simple alert message.",
        system_prompt=[
            "You are a customer support processing assistant.",
            "Generate a summary message based on the supplied number of ticket that can be used to send to helpdesk.",
            "Please state the number of tickets per priority in the summary."
        ],
        user_prompt=[
            "Here is the alert."
        ],
        llm="meta-llama/llama-3-3-70b-instruct",
        llm_parameters={    
            "temperature": 0,
            "min_new_tokens": 5,
            "max_new_tokens": 400,
            "top_k": 1,
            "stop_sequences": ["Human:", "AI:"]
        },
        error_handler_config={
            "error_message": "An error has occured while invoking the LLM",
            "max_retries": 1,
            "retry_interval": 1000
        },
        input_schema=Alert,
        output_schema=Message
    )
    return prompt_node

def build_agent_notification_node(aflow: Flow) -> AgentNode:
    notify_user_node = aflow.agent(
        name="notify_user_via_agent",
        agent="schedule_inform_agent",
        title="Inform alert",
        description="Summarize the alert message that was sent to the helpdesk.",
        message="Summarize the alert message that was sent to the helpdesk.",
        input_schema=Message,
        output_schema=Message
    )

    return notify_user_node

@flow(
        name = "alert_helpdesk_flow",
        input_schema=Product,
        output_schema=Message,
        schedulable=True
    )
def build_alert_helpdesk_flow(aflow: Flow = None) -> Flow:
    """
    Build a simple system that will check for an alert in the support system and send a summary to the helpdesk.

    Ask specifically the product name to use. Do not just make it up.
    """
    check_support_system_node = aflow.tool(check_support_system)
    alert_helpdesk_node = aflow.tool(alert_helpdesk)
    generate_alert_message_node = build_alert_message_node(aflow)
    notify_user_node = build_agent_notification_node(aflow)

    aflow.sequence(START, check_support_system_node, generate_alert_message_node, alert_helpdesk_node, notify_user_node, END)

    return aflow
