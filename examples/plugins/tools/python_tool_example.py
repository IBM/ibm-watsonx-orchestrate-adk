
from ibm_watsonx_orchestrate.agent_builder.tools import tool

@tool( description="sample python tool")
def send_email_tool(mail_id: str, body: str) -> str:
    return f"Email successfully sent to: {mail_id} with the body : {body}"




