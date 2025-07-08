import smtplib


from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

@tool(
    permission=ToolPermission.READ_ONLY
)
def send_email_to_helpdesk(message: str) -> str:
    """
    Just return the same message.
    """
    LOGIN_ID = '<user_id>'
    LOGIN_PASSWORD = ''
    SENDER = '<sender_id>'
    RECIPIENT = '<sender_id>'

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login('<user_id>', '<password>')
    server.sendmail('<sender_id>', '<sender_id>', f'Message to Helpdesk! {message}')
    return message
