from typing import List, Literal, Optional
from ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller import ToolkitController, BaseToolkit
from ibm_watsonx_orchestrate.cli.common import ListFormats

from ibm_watsonx_orchestrate_mcp_server.src.toolkits.types import AddToolKitOptions
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

def add_toolkit(options: AddToolKitOptions) -> BaseToolkit:
    """
    Add a toolkit (MCP server) into the watsonx Orchestrate platform.

    Args:
        options (AddToolKitOptions): The options required to add a toolkit into the watsonx Orchestrate platform
    
    Returns:
        BaseToolkit: The toolkit that has been created
    """
    working_directory_package_root: str | None = get_working_directory_path(options.package_root) if options.package_root else None
    tools: Optional[str] = ",".join(options.tools) if options.tools else None
    tc: ToolkitController = ToolkitController()
    toolkit = silent_call(
        fn=tc.create_toolkit,
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

    silent_call(
        fn=tc.publish_or_update_toolkits, 
        toolkits = [toolkit]
    )
    return toolkit

def import_toolkit(path: str, app_id: Optional[List[str]]) -> List[BaseToolkit]:
    """
    Import a toolkit (MCP server) from a spec file into the watsonx Orchestrate platform.

    Args:
        path (str): The absolute of relative path to a toolkit spec file
        app_id (List[str] | None): An optional list of app_ids which relates Orchestrate connection objects to the Toolkit. Use to provide credentials or other confidential settings to the Toolkit. Overrides app_ids set in the spec file.
    
    Returns:
        List[BaseToolkit]: A list of the toolkits successfully imported
    """
    working_directory_path: str = get_working_directory_path(path)
    tc: ToolkitController = ToolkitController()
    toolkits = silent_call(
        fn=tc.import_toolkit,
        file=working_directory_path,
        app_id=app_id
    )

    silent_call(
        fn=tc.publish_or_update_toolkits, 
        toolkits = toolkits
    )
    return toolkits

def remove_toolkit(name: str) -> str:
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

def export_toolkit(name: str, output_file_path: str) -> str:
    """
    Export a toolkit from the watsonx Orchestrate platform.
    Args:
        name (str): The name of the toolkit to export
        output_file_path (str): The path to export the toolkit to. Should be a zip file with a '.zip' extension.
    
    Returns:
        str: A message indicating the success of the export
    """
    working_directory_output_path: str = get_working_directory_path(output_file_path)
    tc: ToolkitController = ToolkitController()
    silent_call(fn=tc.export_toolkit, name=name, output_file=working_directory_output_path)
    
    return f"The Toolkit {name} successfully exported"

__tools__ = [list_toolkits, import_toolkit, remove_toolkit, add_toolkit, export_toolkit]