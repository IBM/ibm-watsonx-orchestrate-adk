import typer
from typing import List
from typing_extensions import Annotated, Optional
from ibm_watsonx_orchestrate.agent_builder.toolkits.types import ToolkitKind, Language
from ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller import ToolkitController
import logging
import sys

logger = logging.getLogger(__name__)

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
    package: Annotated[
        str,
        typer.Option("--package", help="NPM or Python package of the MCP server"),
    ] = None,
    package_root: Annotated[
        str,
        typer.Option("--package-root", help="Root directory of the MCP server package"),
    ] = None,
    language: Annotated[
        Language,
        typer.Option("--language", "-l", help="Language your package is based on")
    ] = None,
    command: Annotated[
        str,
        typer.Option(
            "--command", 
            help="Command to start the MCP server. Can be a string (e.g. 'node dist/index.js --transport stdio') "
                "or a JSON-style list of arguments (e.g. '[\"node\", \"dist/index.js\", \"--transport\", \"stdio\"]'). "
                "The first argument will be used as the executable, the rest as its arguments."
        ),
    ] = None,
    tools: Annotated[
        Optional[str],
        typer.Option("--tools", "-t", help="Comma-separated list of tools to import. Or you can use `*` to use all tools"),
    ] = None,
    app_id: Annotated[
        List[str],
        typer.Option(
            "--app-id", "-a", 
            help='The app ids of the connections to associate with this tool. A application connection represents the server authentication credentials needed to connect to this tool. Only type key_value is currently supported for MCP.'
        )
    ] = None
):
    if tools == "*": # Wildcard to use all tools for MCP    
        tool_list = ["*"] 
    elif tools:
        tool_list = [tool.strip() for tool in tools.split(",")]
    else:
        tool_list = None

    if not package and not package_root:
        logger.error("You must provide either '--package' or '--package-root'.")
        sys.exit(1)

    if package_root and not command:
        logger.error("Error: '--command' flag must be provided when '--package-root' is specified.")
        sys.exit(1)
    
    if package_root and package:
        logger.error("Please choose either '--package-root' or '--package' but not both.")
        sys.exit(1)

    if package and not package_root:
        if not command:
            if language == Language.NODE:
                command = f"npx -y {package}"
            elif language == Language.PYTHON:
                command = f"python -m {package}"
            else:
                logger.error("Unable to infer start up command: '--language' flag must be either 'node' or 'python' when using the '--package' flag without '--command' flag.")
                sys.exit(1)


    toolkit_controller = ToolkitController(
    kind=kind,
    name=name,
    description=description,
    package=package,
    package_root=package_root,
    language=language,
    command=command,
)
    toolkit_controller.import_toolkit(tools=tool_list, app_id=app_id)

@toolkits_app.command(name="list")
def list_toolkits(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="List full details of all toolkits as json"),
    ] = False,
):
    toolkit_controller = ToolkitController()
    toolkit_controller.list_toolkits(verbose=verbose)

@toolkits_app.command(name="remove")
def remove_toolkit(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the toolkit you wish to remove"),
    ],
):  
    toolkit_controller = ToolkitController()
    toolkit_controller.remove_toolkit(name=name)
