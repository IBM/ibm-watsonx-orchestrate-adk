from typing import  Literal
from typing_extensions import List, Optional
from pathlib import Path

from tempfile import TemporaryDirectory
from ibm_watsonx_orchestrate.agent_builder.tools import BaseTool
from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolKind, ToolsController
from ibm_watsonx_orchestrate.cli.common import ListFormats

from ibm_watsonx_orchestrate_mcp_server.utils.files.files import get_working_directory_path
from ibm_watsonx_orchestrate_mcp_server.utils.common import silent_call

# Pseudo-resources
def get_tool_template() -> str:
    """
    Get a string template with placeholders for the format of a watsonx Orchestrate tool.

    Returns:
        str: The structure required for a watsonx Orchestrate python tool. Template placeholders are marked in angled brackets '<>'.
    """
    return """
from ibm_watsonx_orchestrate.agent_builder.tools import tool
<Any additional imports>

@tool(
    expected_credentials = [
        {"app_id": <An identifier used to reference the credentials>, "type": <A 'ConnectionType' or list of 'ConnectionType' specifying what type of credentials the tool supports>}
    ] # expected_credentials is optional and is only needed when tools make use of credentials/connections
)
def <tool_name>(<arguments with type hints>) -> <return type hint>:
    <python code>
"""

def create_tool(content: str, app_id: Optional[str] = None, requirements_filepath: Optional[str] = None) -> BaseTool:
    """
    Create a watsonx Orchestrate tool from a string of python code. The string should follow the pattern outlined in the template that can be gotten from the tool 'get_tool_template'.

    Args:
        content (str): Valid python code that conforms to the schema found using the tool 'get_tool_template'
        app_id (str | None): An optional app_id which relates an Orchestrate connection object to the tool. Used to provide credentials for the tool to make use of. Should match the app id of the expect_credentials object.
        requirements_filepath (str | None): An optional path to a requirements.txt file for python tools to allow for external packages avalible on pypi to be used.

    Returns:
        str: The constructed tool.
    """
    working_directory = get_working_directory_path(".")
    working_directory_requirements_path: str | None = get_working_directory_path(requirements_filepath) if requirements_filepath else None

    with TemporaryDirectory(dir=working_directory) as tmp_dir:
        tool_file_path = Path(tmp_dir) / "temp_tool.py"
        tool_file_path.write_text(content)
        
        tc: ToolsController = ToolsController(tool_kind=ToolKind.python, file=str(tool_file_path), requirements_file=working_directory_requirements_path)
        tools: List[BaseTool] = silent_call(
            fn=tc.import_tool,
            kind=ToolKind.python,
            file=str(tool_file_path),
            app_id=app_id,
            requirements_file=working_directory_requirements_path,
            package_root=None,
        )
        tools_list: list[BaseTool] = list(tools)
        silent_call(tc.publish_or_update_tools, tools_list, package_root=None)
    
    if len(tools_list):
        return tools_list[0]
    else:
        raise Exception("No valid tools created")
        

def import_tool(kind: ToolKind, path: str, app_id: Optional[str] = None, requirements_filepath: Optional[str] = None, package_root: Optional[str] = None) -> List[BaseTool]:
    """
    Import a tool into the watsonx Orchestrate platform

    Args:
        kind (ToolKind): The kind of tool to import. Valid options are ['python' | 'openapi' | 'flow']
        path (str): The path to the tool definition file.
        app_id (str | None): An optional app_id which relates an Orchestrate connection object to the tool. Used to provide credentials for the tool to make use of.
        requirements_filepath (str | None): An optional path to a requirements.txt file for python tools.
        package_root (str | None): An optional path to a packageroot for python tools with multiple files.
    
    Returns:
        List[BaseTool]: The newly created tools.
    """

    working_directory_path: str = get_working_directory_path(path)
    working_directory_requirements_path: str | None = get_working_directory_path(requirements_filepath) if requirements_filepath else None
    working_directory_package_root: str | None = get_working_directory_path(package_root) if package_root else None

    tc: ToolsController = ToolsController(tool_kind=kind, file=working_directory_path, requirements_file=working_directory_requirements_path)
    tools: List[BaseTool] = silent_call(
        fn=tc.import_tool,
        kind=kind,
        file=working_directory_path,
        app_id=app_id,
        requirements_file=working_directory_requirements_path,
        package_root=working_directory_package_root,
    )
    tools_list: list[BaseTool] = list(tools)
    silent_call(tc.publish_or_update_tools, tools_list, package_root=working_directory_package_root)
    return tools_list

def list_tools(verbose:bool=False)-> List[dict]:
    """
    Lists the tools available on the watsonx Orchestrate platform.

    Args:
        verbose (bool, optional): Return verbose information without processing. Should only be used for getting extra details. Defaults to False.
    
    Returns:
        List[dict]: A list of dictionaries containing information about the tools available on the watsonx Orchestrate platform.
    """
    tc: ToolsController = ToolsController()
    format: Literal[ListFormats.JSON] | None = ListFormats.JSON if not verbose else None
    tools: List[dict] = silent_call(fn=tc.list_tools, verbose=verbose, format=format)
    return tools


def remove_tool(name: str) -> str:
    """
    Removes a tool from the watsonx Orchestrate platform.

    Args:
        name (str): The name of the tool to remove.
    
    Returns:
        str: A message indicating the success of the removal
    """

    tc: ToolsController = ToolsController()
    silent_call(
        fn=tc.remove_tool,
        name=name
    )

    return f"The tool {name} has been removed successfully"

def export_tool(name: str, output_file_path: str) -> str:
    """
    Exports a tool from the watsonx Orchestrate platform.

    Args:
        name (str): The name of the tool to export
        output_file_path (str): The path to where the tool should create the output file. Should have a .zip extension
    """
    working_directory_output_path: str = get_working_directory_path(output_file_path)
    tc: ToolsController = ToolsController()
    silent_call(
        fn=tc.export_tool,
        name=name,
        output_path=working_directory_output_path
    )
    return f"The tool {name} has been exported successfully"

__tools__ = [get_tool_template, import_tool, list_tools, remove_tool, export_tool, create_tool]