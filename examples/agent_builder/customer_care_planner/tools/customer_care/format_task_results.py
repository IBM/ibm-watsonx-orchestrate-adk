import json
from typing import Dict, List, Any
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.agent_builder.tools.types import PythonToolKind

@tool(permission=ToolPermission.READ_ONLY, kind=PythonToolKind.JOIN_TOOL)
def format_task_results(original_query: str, task_results: Dict[str, Any], messages: List[Dict[str, Any]]) -> str:
    """
    Format the results from various tasks executed by a planner agent into a cohesive response.
    
    Args:
        original_query (str): The initial query submitted by the user.
        task_results (Dict[str, Any]): A dictionary containing the outcomes of each task executed within the agent's plan.
        messages (List[Dict[str, Any]]): The history of messages in the current conversation.
        
    Returns:
        str: A formatted string containing the consolidated results.
    """
    # Create a summary header
    output = f"## Results for: {original_query}\n\n"
    
    # Add each task result in a structured format
    for task_name, result in task_results.items():
        output += f"### {task_name}\n"
        
        # Handle different result types appropriately
        if isinstance(result, dict):
            # Pretty format dictionaries
            output += "```json\n"
            output += json.dumps(result, indent=2)
            output += "\n```\n\n"
        elif isinstance(result, list):
            # Format lists as bullet points
            output += "\n".join([f"- {item}" for item in result])
            output += "\n\n"
        else:
            # Plain text for other types
            output += f"{result}\n\n"
    
    # Add a summary section
    output += "## Summary\n"
    output += f"Completed {len(task_results)} tasks related to your query about {original_query.lower()}.\n"
    
    return output 
