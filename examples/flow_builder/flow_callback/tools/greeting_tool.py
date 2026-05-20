"""
Simple greeting tool for the flow callback example.

This tool takes a message and returns a greeting with that message.
"""

from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool(
    description="Generate a greeting message"
)
def greeting_tool(message: str) -> str:
    """
    Generate a greeting message.
    
    Args:
        message: The message to include in the greeting
        
    Returns:
        A greeting string with the provided message
    """
    return f"Hello! {message}"

# Made with Bob
