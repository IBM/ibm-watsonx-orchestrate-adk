"""Simple echo tool for translation testing."""

from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool
def echo_message(message: str) -> str:
    """
    Echo back the input message.
    
    Args:
        message: The message to echo
        
    Returns:
        The echoed message
    """
    return f"Echo: {message}"
