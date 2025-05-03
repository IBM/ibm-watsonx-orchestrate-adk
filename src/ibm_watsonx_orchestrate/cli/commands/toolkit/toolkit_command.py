import typer
from typing import List
from typing_extensions import Annotated, Optional
from ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller import ToolkitController, ToolkitKind

toolkits_app = typer.Typer(no_args_is_help=True)

@toolkits_app.command(name="import")
def import_toolkit(
    kind: Annotated[
        ToolkitKind,
        typer.Option("--kind", "-k", help="Kind of toolkit, currently only MCP is supported"),
    ],
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the toolkit"),
    ],
    description: Annotated[
        str,
        typer.Option("--description", help="Description of the toolkit"),
    ],
    package_root: Annotated[
        str,
        typer.Option("--package-root", "-p", help="Root directory of the MCP server package"),
    ],
    command: Annotated[
        str,
        typer.Option(
            "--command", 
            help="Command to start the MCP server. Can be a string (e.g. 'node dist/index.js --transport stdio') "
                "or a JSON-style list of arguments (e.g. '[\"node\", \"dist/index.js\", \"--transport\", \"stdio\"]'). "
                "The first argument will be used as the executable, the rest as its arguments."
        ),
    ],
    tools: Annotated[
        Optional[str],
        typer.Option("--tools", "-t", help="Comma-separated list of tools to import. Or you can use `*` to use all tools"),
    ] = None,
    app_id: Annotated[
        List[str],
        typer.Option(
            "--app-id", "-a", 
            help='The app id of the connection to associate with this tool. A application connection represents the server authentication credentials needed to connect to this tool. Only type key_value is currently supported for MCP.'
        )
    ] = None
):
    if tools == "*":
        tool_list = ["*"] # Wildcard to use all tools
    elif tools:
        tool_list = [tool.strip() for tool in tools.split(",")]
    else:
        tool_list = None

    toolkit_controller = ToolkitController(
    kind=kind,
    name=name,
    description=description,
    package_root=package_root,
    command=command,
)
    toolkit_controller.import_toolkit(tools=tool_list, app_id=app_id)

@toolkits_app.command(name="remove")
def remove_toolkit(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the toolkit you wish to remove"),
    ],
):  
    toolkit_controller = ToolkitController()
    toolkit_controller.remove_toolkit(name=name)
