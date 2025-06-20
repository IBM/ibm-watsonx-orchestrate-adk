'''
Build a simple flow that will sequence call two agents.
'''

from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow
from ibm_watsonx_orchestrate.flow_builder.flows.constants import END, START
from .send_emails import send_emails

class FlowInput(BaseModel):
    question: str = Field(description="A topic to search for about IBM")
    emails: str = Field(description="a list of comman separated email address")

class FlowOutput(BaseModel):
    question: str = Field(description="A topic to search for about IBM")
    answer: str = Field(description="A fact about IBM")
    emails: str = Field(description="The email addresse the we sent. comma separated.")

class IBMAgentInput(BaseModel):
    question: str = Field(description="A topic to search for")

class IBMAgentOutput(BaseModel):
    answer: str = Field(description="A fact about IBM")

class EmailAgentInput(BaseModel):
    emails: str = Field(description="Comma separated list of email addresses")
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

    # when talking to an agent, we need to be very precise on what we want to get done.
    # or there is a chance the agent will not be able to response correctly.
    # In the message, you should refer to information that the Flow engine will send 
    # to the agent.
    ask_agent_for_ibm_knowledge = aflow.agent(
        name="ask_agent_for_ibm_knowledge",
        agent="ibm_agent",
        description="Ask the IBM agent to get a fact based on the provided question.",
        message="Give an answer about IBM based on the provided question.  If you don't know the answer, just say 'I do not know'",
        input_schema=IBMAgentInput,
        output_schema=IBMAgentOutput,
    )

    send_emails_node = aflow.tool(send_emails)

    
    #ask_agent_to_send_email_node = aflow.agent(
    #    name="ask_agent_to_send_email",
    #    agent="email_agent",
    #    description="Ask the email agent to send email to the provided email list.",
    #    message="Please send an email to the provided email addresses with a content created based on the question and answer provided. Do not ask to provide emails or content.'",
    #    input_schema=EmailAgentInput,
    #    output_schema=EmailAgentOutput,
    #)
    
    aflow.sequence(START, ask_agent_for_ibm_knowledge, send_emails_node, END)

    return aflow

