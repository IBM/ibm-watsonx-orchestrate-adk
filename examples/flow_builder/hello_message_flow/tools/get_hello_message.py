'''TODO: Docstring'''
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

@tool(
    permission=ToolPermission.READ_ONLY
)
def get_hello_message(name: str) -> str:
    """
    Returns a greeting message with the provided name.

    Args:
        name (str): The name to be greeted.

    Returns:
        str: The greeting message with the provided name.
    """
    return f"Hello {name}, how are you?"
