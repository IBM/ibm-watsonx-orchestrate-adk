'''TODO: Docstring'''
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

@tool(
    permission=ToolPermission.READ_ONLY
)
def combine_names(first_name: str, last_name: str) -> str:
    """
    Combine first and last name to create a full name.

    Args:
        first_name (str): The first name.
        last_name (str): The last name.

    Returns:
        str: The combined first and last name.
    """
    return f"{first_name} {last_name}"
