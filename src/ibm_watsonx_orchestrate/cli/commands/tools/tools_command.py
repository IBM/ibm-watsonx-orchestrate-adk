import typer
from typing_extensions import Annotated
from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolsController, ToolKind
tools_app= typer.Typer(no_args_is_help=True)

@tools_app.command(name="import")
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
            help="Path to Python or OpenAPI spec YAML file. Required for kind openapi or python",
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
        str, typer.Option(
            '--app_id',
            help='The app_id of the connection to associate with this tool. A application connection represents the server authentication credentials needed to connection to this tool (for example Api Keys, Basic, Bearer or OAuth credentials).'
        )
    ] = None
):
    tools_controller = ToolsController()
    tools = tools_controller.import_tool(
        kind=kind,
        file=file,
        # skillset_id=skillset_id,
        # skill_id=skill_id,
        # skill_operation_path=skill_operation_path,
        app_id=app_id
    )
    
    tools_controller.publish_or_update_tools(tools)
