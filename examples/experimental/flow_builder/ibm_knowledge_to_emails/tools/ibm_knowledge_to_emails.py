'''
Build a simple flow that will sequence call two agents.
'''

from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.experimental.flow_builder.flows import Flow, flow
from ibm_watsonx_orchestrate.experimental.flow_builder.flows.constants import END, START

class FlowInput(BaseModel):
    question: str = Field(description="A topic to search for about IBM")
    emails: list[str] = Field(description="a list of email address")

class FlowOutput(BaseModel):
    question: str = Field(description="A topic to search for about IBM")
    answer: str = Field(description="A fact about IBM")
    emails: list[str] = Field(description="The email addresse the we sent")

class IBMAgentInput(BaseModel):
    question: str = Field(description="A topic to search for")

class IBMAgentOutput(BaseModel):
    question: str = Field(description="A topic to search for")
    answer: str = Field(description="A fact about IBM")

class EmailAgentInput(BaseModel):
    emails: list[str] = Field(description="The email addresses")
    question: str = Field(description="A topic to search for about IBM")
    answer: str = Field(description="The email content")

class EmailAgentOutput(BaseModel):
    message: str = Field(description="The message we sent.")

@flow(
    name="ibm_knowledge_to_emails",
    description="This flow will send a random fact about IBM to a group of people",
    input_schema=FlowInput,
    output_schema=FlowOutput
)
def build_ibm_knowledge_to_emails(aflow: Flow) -> Flow:
    """ Retrieve a random fact about IBM and send it out to an email list. """

    ask_agent_for_ibm_knowledge = aflow.agent(
        name="ask_agent_for_ibm_knowledge",
        agent="ibm_agent",
        display_name="ask_agent_for_ibm_knowledge",
        description="Get a random fact about IBM.",
        message="Please retrieve a random fact about IBM on a topic.",
        input_schema=IBMAgentInput,
        output_schema=IBMAgentOutput,
    )

    ask_agent_to_send_email_node = aflow.agent(
        name="ask_agent_to_send_email",
        agent="email_agent",
        display_name="ask_agent_to_send_email",
        description="This agent will send email content to a list of email addresses",
        message="Please send email based on the following email addresses and based on a fact about IBM.'",
        input_schema=EmailAgentInput,
        output_schema=EmailAgentOutput,
    )
    
    aflow.sequence(START, ask_agent_for_ibm_knowledge, ask_agent_to_send_email_node, END)

    return aflow

