from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

@tool(
    permission=ToolPermission.READ_ONLY
)
def send_emails(email_addresses: str, content: str) -> str:
    """
    Send email to a list of email addresses with a content

    Args:
        email_addresses: The list of email address in string to send, comman separated.
        content: The content of the email

    Returns:
        The status of the send
    """
    return f"Email content: '{content}' has been sent to addresses: '{email_addresses}'"
