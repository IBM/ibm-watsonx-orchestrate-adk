from typing import List, Literal, Optional
from ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command import import_toolkit as import_toolkit_command
from ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller import ToolkitController
from ibm_watsonx_orchestrate.cli.common import ListFormats

from ibm_watsonx_orchestrate_mcp_server.src.toolkits.types import ImportToolKitOptions
from ibm_watsonx_orchestrate_mcp_server.utils.common import silent_call
from ibm_watsonx_orchestrate_mcp_server.utils.files.files import get_working_directory_path

def list_toolkits(verbose:bool=False)-> List[dict]:
    """
    Lists the avalible toolkits (MCP Servers) available on the watsonx Orchestrate platform.

    Args:
        verbose (bool, optional): Return verbose information without processing. Should only be used for getting extra details. Defaults to False.
    
    Returns:
        List[dict]: A list of dictionaries containing information about the toolkits available on the watsonx Orchestrate platform.
    """
    tc: ToolkitController = ToolkitController()
    format: Literal[ListFormats.JSON] | None = ListFormats.JSON if not verbose else None
    tools: List[dict] = silent_call(fn=tc.list_toolkits, verbose=verbose, format=format)
    return tools

def import_toolkit(options: ImportToolKitOptions) -> str:
    """
    Import a toolkit (MCP server) into the watsonx Orchestrate platform.

    Args:
        options (ImportToolKitOptions): The options required to import a toolkit into the watsonx Orchestrate platform
    
    Returns:
        str: A success message indicating the toolkit was successfully imported
    """
    working_directory_package_root: str | None = get_working_directory_path(options.package_root) if options.package_root else None
    tools: Optional[str] = ",".join(options.tools) if options.tools else None
    silent_call(
        fn=import_toolkit_command, 
        kind=options.kind,
        name=options.name,
        description=options.description,
        package=options.package,
        package_root=working_directory_package_root,
        language=options.language,
        command=options.command,
        url=options.url,
        transport=options.transport,
        tools=tools,
        app_id=options.app_id
    )
    return f"The toolking {options.name} has been imported successfully"

def remove_toolkit(name: str)-> str:
    """
    Remove a toolkit (MCP server) from the watsonx Orchestrate platform.

    Args:
        name (str): The name of the toolkit to remove
    
    Returns:
        str: A success message indicating the toolkit was successfully removed
    """
    tc: ToolkitController = ToolkitController()
    silent_call(fn=tc.remove_toolkit, name=name)
    return f"The toolkit {name} has been removed successfully"

__tools__ = [list_toolkits, import_toolkit, remove_toolkit]