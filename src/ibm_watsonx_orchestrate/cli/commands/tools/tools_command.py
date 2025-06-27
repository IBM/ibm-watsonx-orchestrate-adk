import typer
from typing import List
from typing_extensions import Annotated
from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolsController, ToolKind
tools_app= typer.Typer(no_args_is_help=True)

@tools_app.command(name="import", help='Import a tool into the active environment')
def tool_import(
    kind: Annotated[
        ToolKind,
        typer.Option("--kind", "-k", help="Import Source Format"),
    ],
    file: Annotated[
        str,
        typer.Option(
            "--file",
            "-f",
            help="Path to Python, OpenAPI spec YAML file or flow JSON or python file. Required for kind openapi, python and flow",
        ),
    ] = None,
    # skillset_id: Annotated[
    #     str, typer.Option("--skillset_id", help="ID of skill set in WXO")
    # ] = None,
    # skill_id: Annotated[
    #     str, typer.Option("--skill_id", help="ID of skill in WXO")
    # ] = None,
    # skill_operation_path: Annotated[
    #     str, typer.Option("--skill_operation_path", help="Skill operation path in WXO")
    # ] = None,
    app_id: Annotated[
        List[str], typer.Option(
            '--app-id', '-a',
            help='The app id of the connection to associate with this tool. A application connection represents the server authentication credentials needed to connection to this tool (for example Api Keys, Basic, Bearer or OAuth credentials).'
        )
    ] = None,
    requirements_file: Annotated[
        str,
        typer.Option(
            "--requirements-file",
            "-r",
            help="Path to Python requirements.txt file. Required for kind python",
        ),
    ] = None,
    package_root: Annotated[
        str,
        typer.Option("--package-root", "-p", help="""When specified, the package root will be treated 
as the current working directory from which the module specified by --file will be invoked. All files and dependencies 
included in this folder will be included within the uploaded package. Local dependencies can either be imported 
relative to this package root folder or imported using relative imports from the --file. This only applies when the 
--kind=python. If not specified it is assumed only a single python file is being uploaded."""),
    ] = None,
):
    tools_controller = ToolsController(kind, file, requirements_file)
    tools = tools_controller.import_tool(
        kind=kind,
        file=file,
        # skillset_id=skillset_id,
        # skill_id=skill_id,
        # skill_operation_path=skill_operation_path,
        app_id=app_id,
        requirements_file=requirements_file,
        package_root=package_root
    )
    
    tools_controller.publish_or_update_tools(tools, package_root=package_root)

@tools_app.command(name="list", help='List the imported tools in the active environment')
def list_tools(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="List full details of all tools as json"),
    ] = False,
):  
    tools_controller = ToolsController()
    tools_controller.list_tools(verbose=verbose)

@tools_app.command(name="remove", help='Remove a tool from the active environment')
def remove_tool(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the tool you wish to remove"),
    ],
):  
    tools_controller = ToolsController()
    tools_controller.remove_tool(name=name)

@tools_app.command(name="export", help='Export a tool to a zip file')
def tool_export(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="The name of the tool you want to export"),
    ],
    output_file: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Path to a where the zip file containing the exported data should be saved",
        ),
    ],
):
    tools_controller = ToolsController()
    tools_controller.export_tool(
        name=name,
        output_path=output_file
    )
