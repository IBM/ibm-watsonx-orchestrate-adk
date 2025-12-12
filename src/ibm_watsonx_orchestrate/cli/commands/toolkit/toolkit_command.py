import typer
from typing import List
from typing_extensions import Annotated, Optional
from ibm_watsonx_orchestrate.agent_builder.toolkits.types import ToolkitKind, Language, ToolkitTransportKind
from ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller import ToolkitController
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

toolkits_app = typer.Typer(no_args_is_help=True)

@toolkits_app.command(name="import")
def import_toolkit(
    file: Annotated[
        Path,
        typer.Option("--file", "-f",
                      help="Path to the MCP spec file",
                      exists=True,
                      file_okay=True,
                      dir_okay=False,
                      readable=True
        ),
    ],
    app_id: Annotated[
        List[str],
        typer.Option(
            "--app-id", "-a", 
            help='The app ids of the connections to associate with this tool. A application connection represents the server authentication credentials needed to connect to this tool. Only type key_value is currently supported for STDIO MCP.'
        )
    ] = None
):
    toolkit_controller = ToolkitController()
    toolkits = toolkit_controller.import_toolkit(file=file, app_id=app_id)
    toolkit_controller.publish_or_update_toolkits(toolkits)

@toolkits_app.command(name="add")
def add_toolkit(
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
    url: Annotated[
        Optional[str],
        typer.Option("--url", "-u", help="The URL of the remote MCP server"),
    ] = None,
    transport: Annotated[
        ToolkitTransportKind,
        typer.Option("--transport", help="The communication protocol to use for the remote MCP server. Only \"sse\" or \"streamable_http\" supported"),
    ] = None,
    tools: Annotated[
        Optional[str],
        typer.Option("--tools", "-t", help="Comma-separated list of tools to import. Or you can use \"*\" to use all tools"),
    ] = None,
    app_id: Annotated[
        List[str],
        typer.Option(
            "--app-id", "-a", 
            help='The app ids of the connections to associate with this tool. A application connection represents the server authentication credentials needed to connect to this tool. Only type key_value is currently supported for STDIO MCP.'
        )
    ] = None
):
    toolkit_controller = ToolkitController()
    toolkit = toolkit_controller.create_toolkit(
        kind=kind,
        name=name,
        description=description,
        package=package,
        package_root=package_root,
        language=language,
        command=command,
        url=url,
        transport=transport,
        tools=tools,
        app_id=app_id
    )
    toolkit_controller.publish_or_update_toolkits([toolkit])

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

@toolkits_app.command(name="export")
def export_toolkit(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the toolkit you wish to remove"),
    ],
    output_file: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Path to a where the file containing the exported data should be saved. Should send in '.zip'",
        )
    ]
):  
    toolkit_controller = ToolkitController()
    toolkit_controller.export_toolkit(name=name, output_file=output_file)
