from pathlib import Path
import typer
from typing import List
from typing_extensions import Annotated, Optional
from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolsController, ToolKindImport, ToolKind
from ibm_watsonx_orchestrate.cli.common import logger

tools_app= typer.Typer(no_args_is_help=True)

@tools_app.command(name="import", help='Import a tool into the active environment')
def tool_import(
    kind: Annotated[
        ToolKindImport,
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
        Optional[str],
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
    name: Annotated[
        Optional[str],
        typer.Option(
        "--name","-n",
        help="The name of the flow to import when importing from langflow, if an existing tool has the same name it will be updated"
        )
    ] = None,
    auto_discover: Annotated[
        Optional[bool],
        typer.Option(
            "--auto-discover",
            help="Automatically generates docstring for imported python file and converts it into a python tool"
        )
    ] = False,
    llm: Annotated[
        Optional[str],
        typer.Option(
            "--llm",
            help="Model name/id to be used for auto-discover llm callouts"
        )
    ] = None,
    env_file: Annotated[
        Optional[str],
        typer.Option(
            "--env-file",
            "-e",
            help="Path to a .env file with connection configurations for auto-discover llm callouts"
        )
    ] = None,
    function_names: Annotated[
        Optional[list[str]],
        typer.Option(
            "--function",
            help="Used to specify a function for autodiscover, all other functions will not be converted. (Default behavior is to convert all top level functions found)"
        )
    ] = None,
    save_flow_json: Annotated[
        Optional[str],
        typer.Option(
            "--save-flow-json",
            help="Path to save the compiled flow JSON file. Only applicable for flow imports (--kind=flow)"
        )
    ] = None,
    translation: Annotated[
        Optional[str],
        typer.Option(
            "--translation",
            help="Path to translation CSV file to import after tool creation. Only applicable for flow imports (--kind=flow)"
        )
    ] = None,
    safe: Annotated[
        bool,
        typer.Option(
            "--safe",
            help="Enable safe mode: prompt for confirmation before updating existing tools"
        )
    ] = False
):
    # Validate translation parameter
    if translation:
        if kind != ToolKindImport.flow:
            raise typer.BadParameter("--translation option is only valid for flow tools (--kind=flow)")
        
        # Validate that translation file path exists
        translation_path = Path(translation)
        if not translation_path.exists():
            raise typer.BadParameter(f"Translation file not found: {translation}")
        if not translation_path.is_file():
            raise typer.BadParameter(f"Translation path is not a file: {translation}")
    
    tools_controller = ToolsController(kind, file, requirements_file, safe_mode=safe)
    if auto_discover:
        if kind != ToolKindImport.python:
            raise typer.BadParameter(f"Auto-discover is only valid for python tools")
        
        resolved_file = tools_controller.auto_discover_tools(
            input_file=file,
            env_file=env_file,
            llm=llm,
            function_names=function_names
        )
        tools_controller.file = resolved_file
    else:
        resolved_file = tools_controller.resolve_file(name=name)
    try:
        tools = tools_controller.import_tool(
            kind=kind,
            file=resolved_file,
            # skillset_id=skillset_id,
            # skill_id=skill_id,
            # skill_operation_path=skill_operation_path,
            app_id=app_id,
            requirements_file=requirements_file,
            package_root=package_root,
            name=name,
            save_flow_json=save_flow_json,
        )
        published_tools = tools_controller.publish_or_update_tools(tools=tools, package_root=package_root)
        
        # Import translations after tool is published/updated (only for flow tools)
        if translation and published_tools:
            # Find the main flow tool (not support tools like get_flow_status)
            # Support tools have specific naming patterns (e.g., i__get_flow_status_intrinsic_tool__)
            main_flow_tool = None
            for tool in published_tools:
                # Skip intrinsic/support tools - they start with "i__" and end with "_intrinsic_tool__"
                if not tool["name"].startswith("i__") and not tool["name"].endswith("_intrinsic_tool__"):
                    main_flow_tool = tool
                    break
            
            if main_flow_tool:
                tool_id = main_flow_tool["id"]
            else:
                # Fallback: if no main tool identified, use the last tool
                # (main flow tool is appended last when support tools are enabled)
                tool_id = published_tools[-1]["id"]
            
            try:
                tools_controller.import_flow_translations(translation_path=translation, tool_id=tool_id)
            except Exception as e:
                logger.warning(f"Tool was successfully imported, but translation import failed: {str(e)}")
                logger.info(f"You can retry importing translations using: orchestrate tools translation-import -k flow --name <tool_name> --translation {translation}")
    finally:
        tools_controller.remove_temp_file()
 
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

@tools_app.command(
    name="auto-discover",
    help="Annotate and generate docstring for a python tool")
def tool_auto_discover(
    env_file: Annotated[
        str,
        typer.Option(
            "--env-file",
            "-e",
            help="Path to a .env file that overrides default.env. Then environment variables override both."
        )
    ],
    input_file: Annotated[
        str,
        typer.Option(
            "--file",
            "-f",
            help="Path to the python file to annotate"
        )
    ],
    output_file: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="File to export the annotated file to"
        )
    ],
    llm: Annotated[
        Optional[str],
        typer.Option(
            "--llm",
            help="Model name/id to be used for auto-discover llm callouts"
        )
    ] = None,
    function_names: Annotated[
        Optional[list[str]],
        typer.Option(
            "--function",
            help="Used to specify a function for autodiscover, all other functions will not be converted. (Default behavior is to convert all top level functions found)"
        )
    ] = None
):
    tools_controller = ToolsController(ToolKindImport.python, input_file)
    
    file = tools_controller.auto_discover_tools(
        input_file=input_file,
        output_file=output_file,
        env_file=env_file,
        llm=llm,
        function_names=function_names
    )
    tools_controller.file = file

@tools_app.command(
    name="translation-export",
    help="Retrieve translations for a flow tool"
)
def translation_export(
    kind: Annotated[
        ToolKind,
        typer.Option(
            "--kind",
            "-k",
            help="Type of tool to translate (currently only 'flow' is supported)"
        ),
    ],
    translation: Annotated[
        str,
        typer.Option(
            "--translation",
            help="File path where the translation CSV file will be saved"
        ),
    ],
    file: Annotated[
        Optional[str],
        typer.Option(
            "--file",
            "-f",
            help="Path to flow file (JSON or Python). Mutually exclusive with --name"
        ),
    ] = None,
    name: Annotated[
        Optional[str],
        typer.Option(
            "--name",
            help="Name of an imported flow tool. Mutually exclusive with --file"
        ),
    ] = None,
):
    """
    Retrieve translations for a flow tool.
    
    You must provide either --file or --name, but not both.
    
    Examples:
        orchestrate tools translation-export -k flow -f path/to/flow.json --translation translations.csv
        orchestrate tools translation-export -k flow --name my_flow_tool --translation translations.csv
    """
    # Validate that exactly one of file or name is provided
    if file and name:
        raise typer.BadParameter("Cannot specify both --file and --name. Please provide only one.")
    
    if not file and not name:
        raise typer.BadParameter("Must specify either --file or --name.")
    
    # Only flow kind is supported for now
    if kind != ToolKind.flow:
        raise typer.BadParameter(f"Kind '{kind}' is not supported. Currently only 'flow' is supported.")
    
    controller = ToolsController()
    controller.export_flow_translations(
        file=file,
        name=name,
        translation_output_path=translation
    )
@tools_app.command(
    name="translation-import",
    help="Import translations for a flow tool from a CSV file"
)
def translation_import(
    kind: Annotated[
        ToolKind,
        typer.Option(
            "--kind",
            "-k",
            help="Type of tool to import translations for (currently only 'flow' is supported)"
        ),
    ],
    translation: Annotated[
        str,
        typer.Option(
            "--translation",
            help="File path to the translation CSV file to import"
        ),
    ],
    name: Annotated[
        str,
        typer.Option(
            "--name",
            help="Name of an imported flow tool"
        ),
    ],
):
    """
    Import translations for a flow tool from a CSV file.
    
    The tool must already be imported before importing translations.
    
    Example:
        orchestrate tools translation-import -k flow --name my_flow_tool --translation translations.csv
    """
    
    # Only flow kind is supported for now
    if kind != ToolKind.flow:
        raise typer.BadParameter(f"Kind '{kind}' is not supported. Currently only 'flow' is supported.")
    
    # Validate that translation file path exists
    translation_path = Path(translation)
    if not translation_path.exists():
        raise typer.BadParameter(f"Translation file not found: {translation}")
    if not translation_path.is_file():
        raise typer.BadParameter(f"Translation path is not a file: {translation}")
    
    controller = ToolsController()
    
    # Pass the name parameter - the controller will look up the tool ID
    controller.import_flow_translations(translation_path=str(translation_path), name=name)


