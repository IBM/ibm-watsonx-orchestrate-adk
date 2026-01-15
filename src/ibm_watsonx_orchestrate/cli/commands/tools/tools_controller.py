import logging
import importlib
import inspect
import os
import sys
import io
import re
import tempfile
from types import FunctionType
from pydantic import BaseModel
import requests
import zipfile
from enum import Enum
from os import path
from pathlib import Path
from typing import Iterable, List, Any, Optional, cast
import rich
import json
import glob

import rich.table
import typer

from rich.panel import Panel

from ibm_watsonx_orchestrate.agent_builder.tools import BaseTool, ToolSpec, ToolListEntry
from ibm_watsonx_orchestrate.agent_builder.tools.flow_tool import create_flow_json_tool
from ibm_watsonx_orchestrate.agent_builder.tools.langflow_tool import LangflowTool, create_langflow_tool
from ibm_watsonx_orchestrate.agent_builder.tools.openapi_tool import create_openapi_json_tools_from_uri
from ibm_watsonx_orchestrate.cli.commands.langflow.langflow_controller import LangflowController
from ibm_watsonx_orchestrate.cli.commands.models.models_controller import ModelHighlighter
from ibm_watsonx_orchestrate.cli.commands.tools.auto_discover.auto_discover import auto_discover_python_tools
from ibm_watsonx_orchestrate.cli.commands.tools.types import RegistryType
from ibm_watsonx_orchestrate.cli.commands.connections.connections_controller import export_connection
from ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller import ToolkitController 
from ibm_watsonx_orchestrate.cli.common import ListFormats, rich_table_to_markdown
from ibm_watsonx_orchestrate.agent_builder.connections.types import ConnectionEnvironment, ConnectionConfiguration, ConnectionPreference
from ibm_watsonx_orchestrate.cli.config import Config, CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT, \
    PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT, \
    DEFAULT_CONFIG_FILE_CONTENT, PYTHON_REGISTRY_SKIP_VERSION_CHECK_OPT
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionSecurityScheme
from ibm_watsonx_orchestrate.flow_builder.flows.decorators import FlowWrapper
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.toolkit.toolkit_client import ToolKitClient
from ibm_watsonx_orchestrate.client.connections import get_connections_client, get_connection_type
from ibm_watsonx_orchestrate.client.utils import instantiate_client, is_local_dev
from ibm_watsonx_orchestrate.flow_builder.utils import import_flow_support_tools
from ibm_watsonx_orchestrate.utils.utils import sanitize_app_id
from ibm_watsonx_orchestrate.utils.async_helpers import run_coroutine_sync
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.flow_builder.utils import get_all_tools_in_flow
from ibm_watsonx_orchestrate.agent_builder.tools.types import PythonToolKind

from  ibm_watsonx_orchestrate import __version__

logger = logging.getLogger(__name__)

__supported_characters_pattern = re.compile("^(\\w|_)+$")


DEFAULT_LANGFLOW_TOOL_REQUIREMENTS = [
    "lfx==0.2.1"
]

DEFAULT_LANGFLOW_RUNNER_MODULES = [
    "lfx",
    "lfx-nightly"
]

class ToolKind(str, Enum):
    openapi = "openapi"
    python = "python"
    mcp = "mcp"
    flow = "flow"
    langflow = "langflow"
    # skill = "skill"

def get_connection_configs(app_id: str) -> List[ConnectionConfiguration]:
    client = get_connections_client()
    connection_configs = []
    for env in ConnectionEnvironment:
        try:
            config = client.get_config(app_id=app_id,env=env)
            if not config:
                continue
            else:
                connection_configs.append( config.as_config() )
        except:
            logger.error(f"Unable to get {env.value.lower()} configs for connection '{app_id}'")

    return connection_configs

def check_plugin_connection(app_id: List[str]):
    app_ids = []
    connections_client = get_connections_client()
    connections = connections_client.get_draft_by_app_ids(app_id)

    for conn in connections:
        if isinstance(conn, tuple) and len(conn) == 2:
            key, value = conn
            if key == "app_id":
                app_ids.append(value)

    for app_id_check in app_ids:
        conn_configs = get_connection_configs(app_id_check)
        for conn_config in conn_configs:
            if conn_config.preference == ConnectionPreference.MEMBER:
                logger.error(f"{conn_config.app_id} connection has type of Member. Connection types for Plugin Tools must be Team and not Member")
                sys.exit(1)

class ToolKindImport(str, Enum):
    openapi = ToolKind.openapi.value
    python = ToolKind.python.value
    flow = ToolKind.flow.value
    langflow = ToolKind.langflow.value

def _get_connection_environments() -> List[ConnectionEnvironment]:
    if is_local_dev():
        return [ConnectionEnvironment.DRAFT]
    else:
        return [env.value for env in ConnectionEnvironment]

def validate_app_ids(kind: ToolKind, **args) -> None:
    
    environments = _get_connection_environments()
    
    app_ids = args.get("app_id")
    if not app_ids:
        return

    if kind == ToolKind.openapi:
        if app_ids and len(app_ids) > 1:
            raise typer.BadParameter(
                "Kind 'openapi' can only take one app-id"
            )

    connections_client = get_connections_client()

    imported_connections_list = connections_client.list()
    imported_connections = {}
    for conn in imported_connections_list:
        app_id = conn.app_id
        conn_env = conn.environment
        if app_id in imported_connections:
            imported_connections[app_id][conn_env] = conn
        else:
            imported_connections[app_id] = {conn_env: conn}

    for app_id in app_ids:
        
        if app_id not in imported_connections:
            logger.warning(f"No connection found for provided app-id '{app_id}'. Please create the connection using `orchestrate connections add`")
            if kind != ToolKind.python:
                continue

        permitted_connections_types = []

        match(kind):

            case ToolKind.python:
                # Split on = but not on \=
                split_pattern = re.compile(r"(?<!\\)=")
                split_id = re.split(split_pattern, app_id)
                split_id = [x.replace("\\=", "=") for x in split_id]
                if len(split_id) == 2:
                    _, app_id = split_id
                elif len(split_id) == 1:
                    app_id = split_id[0]
                else:
                    raise typer.BadParameter(f"The provided --app-id '{app_id}' is not valid. This is likely caused by having mutliple equal signs, please use '\\=' to represent a literal '=' character")
                continue

            # Validate that the connection is not key_value when the tool in openapi
            case ToolKind.openapi:
                permitted_connections_types.extend([
                    ConnectionSecurityScheme.API_KEY_AUTH,
                    ConnectionSecurityScheme.BASIC_AUTH,
                    ConnectionSecurityScheme.BEARER_TOKEN,
                    ConnectionSecurityScheme.OAUTH2
                ])

            # Validate that the connection is key_value when the tool in langflow
            case ToolKind.langflow:
                permitted_connections_types.append(ConnectionSecurityScheme.KEY_VALUE)

        imported_connection = imported_connections.get(app_id)

        for conn_environment in environments:
            conn = imported_connection.get(conn_environment)

            if conn is None or conn.security_scheme is None:
                message = f"Connection '{app_id}' is not configured in the '{conn_environment}' environment."
                if conn_environment == ConnectionEnvironment.DRAFT:
                    logger.error(message)
                    sys.exit(1)
                else:
                    logger.warning(message + " If you deploy this tool without setting the live configuration the tool will error during execution.")
                continue

            if conn.security_scheme not in permitted_connections_types:
                logger.error(f"{conn.security_scheme} application connections can not be bound to {kind.value} tools")
                exit(1)


            

def validate_params(kind: ToolKind, **args) -> None:
    if kind in {"openapi", "python"} and args["file"] is None:
        raise typer.BadParameter(
            "--file (-f) is required when kind is set to either python or openapi"
        )
    elif kind == "skill":
        missing_params = []
        if args["skillset_id"] is None:
            missing_params.append("--skillset_id")
        if args["skill_id"] is None:
            missing_params.append("--skill_id")
        if args["skill_operation_path"] is None:
            missing_params.append("--skill_operation_path")

        if len(missing_params) > 0:
            raise typer.BadParameter(
                f"Missing flags {missing_params} required for kind skill"
            )
    validate_app_ids(kind=kind, **args)

def get_connection_id(app_id: str) -> str:
    connections_client = get_connections_client()
    connection_id = None
    if app_id is not None:
        connection = connections_client.get(app_id=app_id)
        if  not connection:
            logger.error(f"No connection exists with the app-id '{app_id}'")
            exit(1)
        connection_id = connection.connection_id
    return connection_id

def get_connections(app_ids: list[str] | str = None, environment: str = None, allow_missing: bool = True) -> dict:
    if not app_ids:
        return {}
    if app_ids is str:
        app_ids = [app_ids]

    connections_client = get_connections_client()
    if environment:
        connections = { 
            x.app_id:x for x in connections_client.list() \
            if x.app_id in app_ids and x.environment == ConnectionEnvironment(environment) 
        }
    else:
        connections = { x.app_id:x for x in connections_client.list() if x.app_id in app_ids }


    missing = 0
    for id in app_ids:
        if not connections.get(id,None):
            missing += 1

    if missing > 0 and not allow_missing:
        raise ValueError(f"Could not find {missing} of {len(app_ids)} required connections")

    return connections

def get_connection_ids(app_ids: list[str] | str = None, environment: str = None, allow_missing: bool = True):
    connections = get_connections(app_ids=app_ids, environment=environment, allow_missing=allow_missing)
    return { k:v.connection_id for k,v in connections.items() }

def parse_app_ids(app_ids: List[str]) -> dict[str,str]:
    app_id_dict = {}
    for app_id in app_ids:
        # Split on = but not on \=
        split_pattern = re.compile(r"(?<!\\)=")
        split_id = re.split(split_pattern, app_id)
        split_id = [x.replace("\\=", "=") for x in split_id]
        if len(split_id) == 2:
            runtime_id, local_id = split_id
        elif len(split_id) == 1:
            runtime_id = split_id[0]
            local_id = split_id[0]
        else:
            raise typer.BadParameter(f"The provided --app-id '{app_id}' is not valid. This is likely caused by having mutliple equal signs, please use '\\=' to represent a literal '=' character")

        if not len(runtime_id.strip()) or not len(local_id.strip()):
            raise typer.BadParameter(f"The provided --app-id '{app_id}' is not valid. --app-id cannot be empty or whitespace")

        runtime_id = sanitize_app_id(runtime_id)
        app_id_dict[runtime_id] = get_connection_id(local_id)

    return app_id_dict

def validate_python_connections(tool: BaseTool):
    if not tool.expected_credentials:
        return

    connections_client = get_connections_client()
    connections = tool.__tool_spec__.binding.python.connections

    provided_connections = list(connections.keys()) if connections else []
    imported_connections_list = connections_client.list()
    imported_connections = {}
    for conn in imported_connections_list:
        conn_id = conn.connection_id
        conn_env = conn.environment
        if conn_id in imported_connections:
            imported_connections[conn_id][conn_env] = conn
        else:
            imported_connections[conn_id] = {conn_env: conn}

    validation_failed = False

    existing_sanatized_expected_tool_app_ids = set()

    for expected_cred in tool.expected_credentials:

        expected_tool_app_id = expected_cred.app_id
        if isinstance(expected_cred.type, List):
            expected_tool_conn_types = expected_cred.type
        else:
            expected_tool_conn_types = [expected_cred.type]

        sanatized_expected_tool_app_id = sanitize_app_id(expected_tool_app_id)
        if sanatized_expected_tool_app_id in existing_sanatized_expected_tool_app_ids:
            logger.error(f"Duplicate App ID found '{expected_tool_app_id}'. Multiple expected app ids in the tool '{tool.__tool_spec__.name}' collide after sanaitization to '{sanatized_expected_tool_app_id}'. Please rename the offending app id in your tool.")
            sys.exit(1)
        existing_sanatized_expected_tool_app_ids.add(sanatized_expected_tool_app_id)

        if sanatized_expected_tool_app_id not in provided_connections:
            logger.error(f"The tool '{tool.__tool_spec__.name}' requires an app-id '{expected_tool_app_id}'. Please use the `--app-id` flag to provide the required app-id")
            sys.exit(1)

        if not connections:
            continue
            
        connection_id = connections.get(sanatized_expected_tool_app_id)
        imported_connection = imported_connections.get(connection_id)

        if connection_id and not imported_connection:
            logger.error(f"The expected connection id '{connection_id}' does not match any known connection. This is likely caused by the connection being deleted. Please rec-reate the connection and re-import the tool")
            validation_failed = True
        
        environments = _get_connection_environments()

        for conn_environment in environments:
            conn = imported_connection.get(conn_environment)
            conn_identifier = conn.app_id if conn is not None else connection_id
            if conn is None or conn.security_scheme is None:
                message = f"Connection '{conn_identifier}' is not configured in the '{conn_environment}' environment."
                if conn_environment == ConnectionEnvironment.DRAFT:
                    logger.error(message)
                    sys.exit(1)
                else:
                    logger.warning(message + " If you deploy this tool without setting the live configuration the tool will error during execution.")
                continue

            imported_connection_auth_type = get_connection_type(security_scheme=conn.security_scheme, auth_type=conn.auth_type)

            if conn and len(expected_tool_conn_types) and imported_connection_auth_type not in expected_tool_conn_types:
                logger.error(f"The app-id '{conn.app_id}' is of type '{imported_connection_auth_type.value}' in the '{conn_environment}' environment. The tool '{tool.__tool_spec__.name}' accepts connections of the following types '{', '.join(expected_tool_conn_types)}'. Use `orchestrate connections list` to view current connections and use `orchestrate connections add` to create the relevent connection")
                validation_failed = True

    if validation_failed:
        exit(1)


def get_package_root(package_root):
    return None if package_root is None or package_root.strip() == "" else package_root.strip()

def get_resolved_py_tool_reqs_file (tool_file, requirements_file, package_root):
    resolved_requirements_file = requirements_file if requirements_file is not None else None
    tool_sibling_reqs_file = Path(tool_file).absolute().parent.joinpath("requirements.txt")
    package_root_reqs_file = Path(package_root).absolute().joinpath(
        "requirements.txt") if get_package_root(package_root) is not None else None

    if resolved_requirements_file is None:
        # first favor requirements which is sibling root. if not, fallback to the one at package root.
        if tool_sibling_reqs_file.exists():
            resolved_requirements_file = str(tool_sibling_reqs_file)

        elif package_root_reqs_file is not None and package_root_reqs_file.exists():
            resolved_requirements_file = str(package_root_reqs_file)

    return resolved_requirements_file

def get_requirement_lines (requirements_file, remove_trailing_newlines=True):
    requirements = []

    if requirements_file is not None:
        with safe_open(requirements_file, 'r') as fp:
            requirements = fp.readlines()

    if remove_trailing_newlines is True:
        requirements = [x.strip() for x in requirements]

    requirements = [x for x in requirements if not x.startswith("ibm-watsonx-orchestrate")]
    requirements = list(dict.fromkeys(requirements))

    return requirements



def import_python_tool(file: str, requirements_file: str = None, app_id: List[str] = None, package_root: str = None) -> List[BaseTool]:
    try:
        
        # standard file import
        file_path = Path(file).absolute()

        file_path_str = str(file_path)

        if file_path.is_dir():
            raise typer.BadParameter(f"Provided tool file path is not a file.")

        elif file_path.is_symlink():
            raise typer.BadParameter(f"Symbolic links are not supported for tool file path.")

        file_name = file_path.stem

        if __supported_characters_pattern.match(file_name) is None:
            raise typer.BadParameter(f"File name contains unsupported characters. Only alphanumeric characters and underscores are allowed. Filename: \"{file_name}\"")

        resolved_package_root = get_package_root(package_root)
        if resolved_package_root:
            resolved_package_root = str(Path(resolved_package_root).absolute())
            package_path = str(Path(resolved_package_root).parent.absolute())
            package_folder = str(Path(resolved_package_root).stem)
            sys.path.append(package_path)           # allows you to resolve non relative imports relative to the root of the module
            sys.path.append(resolved_package_root)  # allows you to resolve relative imports in combination with import_module(..., package=...)
            package = file_path_str.replace(resolved_package_root, '').replace('.py', '').replace('/', '.').replace('\\', '.')
            if not path.isdir(resolved_package_root):
                raise typer.BadParameter(f"The provided package root is not a directory.")

            elif not file_path_str.startswith(str(Path(resolved_package_root))):
                raise typer.BadParameter(f"The provided tool file path does not belong to the provided package root.")

            temp_path = Path(file_path_str[len(str(Path(resolved_package_root))) + 1:])
            if any([__supported_characters_pattern.match(x) is None for x in temp_path.parts[:-1]]):
                raise typer.BadParameter(f"Path to tool file contains unsupported characters. Only alphanumeric characters and underscores are allowed. Path: \"{temp_path}\"")
        else:
            package_folder = file_path.parent
            package = file_path.stem
            sys.path.append(str(package_folder))

        module = importlib.import_module(package, package=package_folder)

        if resolved_package_root:
            del sys.path[-1]
        del sys.path[-1]


    except typer.BadParameter as ex:
        raise ex

    except Exception as e:
        raise typer.BadParameter(f"Failed to load python module from file {file}: {e}")

    requirements = []
    resolved_requirements_file = get_resolved_py_tool_reqs_file(tool_file=file, requirements_file=requirements_file,
                                                                package_root=resolved_package_root)

    if resolved_requirements_file is not None:
        logger.info(f"Using requirement file: \"{resolved_requirements_file}\"")

    if resolved_requirements_file is not None:
        try:
            requirements = get_requirement_lines(resolved_requirements_file)

        except Exception as e:
            raise typer.BadParameter(f"Failed to read file {resolved_requirements_file} {e}")

    tools = []

    
    for _, obj in inspect.getmembers(module):
        if not isinstance(obj, BaseTool):
            continue
            

        # Plugin tool - if it was given an app-id
        if obj.kind in [PythonToolKind.AGENTPREINVOKE, PythonToolKind.AGENTPOSTINVOKE]:
            if app_id and len(app_id):
                check_plugin_connection(app_id)
            if obj.kind == PythonToolKind.AGENTPREINVOKE:
                obj.__tool_spec__.binding.python.type = PythonToolKind.AGENTPREINVOKE
            elif obj.kind == PythonToolKind.AGENTPOSTINVOKE:
                obj.__tool_spec__.binding.python.type = PythonToolKind.AGENTPOSTINVOKE

        obj.__tool_spec__.binding.python.requirements = requirements

        if __supported_characters_pattern.match(obj.__tool_spec__.name) is None:
            raise typer.BadParameter(f"Tool name contains unsupported characters. Only alphanumeric characters and underscores are allowed. Name: \"{obj.__tool_spec__.name}\"")

        elif resolved_package_root is None:
            fn = obj.__tool_spec__.binding.python.function[obj.__tool_spec__.binding.python.function.index(':')+1:]
            obj.__tool_spec__.binding.python.function = f"{file_name.replace('.py', '')}:{fn}"

        else:
            pkg = package[1:]
            fn = obj.__tool_spec__.binding.python.function[obj.__tool_spec__.binding.python.function.index(':')+1:]
            obj.__tool_spec__.binding.python.function = f"{pkg}:{fn}"

        if app_id and len(app_id):
            obj.__tool_spec__.binding.python.connections = parse_app_ids(app_id)

        validate_python_connections(obj)
        tools.append(obj)

    

    return tools
    


async def import_flow_tool(file: str) -> None:
    
    '''
    Import a flow tool from a file. The file can be either a python file or a json file.
    If the file is a python file, it should contain a flow model builder function decorated with the @flow decorator.
    If the file is a json file, it should contain a flow model in json format.
    Also, a connection will be created for the flow if one does not exists and the environment token will be used.  This is a 
    workaround until flow bindings are supported in the server.
    The function will return a list of tools created from the flow model.
    '''

    theme = rich.theme.Theme({"model.name": "bold cyan"})
    console = rich.console.Console(highlighter=ModelHighlighter(), theme=theme)
    
    message = f"""[bold cyan]Flow Tools[/bold cyan]
   
The [bold]flow tool[/bold] is being imported from [green]`{file}`[/green].  
    
[bold cyan]Additional information:[/bold cyan]

- The [bold green]Get flow status[/bold green] tool is being imported to support flow tools. This tool can query the status of a flow tool instance. You can add it to your agent using the UI or including the following tool name in your agent definition: [green]i__get_flow_status_intrinsic_tool__[/green].

[bold cyan]Experimental Features - Scheduling Flows and Agents: [/bold cyan]
- You can now schedule any Flows to be run on a later time.  Just include the [bold green]"schedulable=True"[/bold green] attribute in the @flow decorator.
- Once enabled, you can schedule a flow by saying something like: [bold green]Can you schedule the flow <flow_name> to run everyday at 7am EST for 3 times?[/bold green]
- To schedule an agent, see the example in [bold green]examples/flow_builder/agent_scheduler[/bold green]. Use that to import the [bold green]agent_run[/bold green] tool to your agent. 
- Use [bold green]agent_run[/bold green] tool to schedule an agent. For example: [bold green]Can you schedule the agent <agent_name> to run every weekday at 8am UK time?[/bold green]
- In scheduling, it is important to mention timezone or UTC time (also known as Greenwich Mean Time or Coordinated Universal Time) will be used.

    """

    console.print(Panel(message,  title="[bold blue]Flow tool support information[/bold blue]", border_style="bright_blue"))
   
    model = None
    
    # Load the Flow JSON model from the file
    try:
        file_path = Path(file).absolute()
        file_path_str = str(file_path)

        if file_path.is_dir():
            raise typer.BadParameter(f"Provided flow file path is not a file.")

        elif file_path.is_symlink():
            raise typer.BadParameter(f"Symbolic links are not supported for flow file path.")

        if file_path.suffix.lower() == ".py":
            
            # borrow code from python tool import to be able to load the script that holds the flow model

            resolved_package_root = get_package_root(str(file_path.parent))
            if resolved_package_root:
                resolved_package_root = str(Path(resolved_package_root).absolute())
                package_path = str(Path(resolved_package_root).parent.absolute())
                package_folder = str(Path(resolved_package_root).stem)
                sys.path.append(package_path)           # allows you to resolve non relative imports relative to the root of the module
                sys.path.append(resolved_package_root)  # allows you to resolve relative imports in combination with import_module(..., package=...)
                package = file_path_str.replace(resolved_package_root, '').replace('.py', '').replace('/', '.').replace('\\', '.')
                if not path.isdir(resolved_package_root):
                    raise typer.BadParameter(f"The provided package root is not a directory.")

                elif not file_path_str.startswith(str(Path(resolved_package_root))):
                    raise typer.BadParameter(f"The provided tool file path does not belong to the provided package root.")

                temp_path = Path(file_path_str[len(str(Path(resolved_package_root))) + 1:])
                if any([__supported_characters_pattern.match(x) is None for x in temp_path.parts[:-1]]):
                    raise typer.BadParameter(f"Path to tool file contains unsupported characters. Only alphanumeric characters and underscores are allowed. Path: \"{temp_path}\"")
            else:
                package_folder = file_path.parent
                package = file_path.stem
                sys.path.append(str(package_folder))

            module = importlib.import_module(package, package=package_folder)
            
            if resolved_package_root:
                del sys.path[-1]
            del sys.path[-1]

            for _, obj in inspect.getmembers(module):
                    
                if not isinstance(obj, FlowWrapper):
                    continue
                
                model = obj().to_json()
                # Ensure metadata exists and is correct
                if "metadata" not in model or not isinstance(model["metadata"], dict):
                    model["metadata"] = {}
                if "source_kind" not in model["metadata"]:
                    model["metadata"]["source_kind"] = "adk/python"
                break

        elif file_path.suffix.lower() == ".json":
            with safe_open(file) as f:
                model = json.load(f)
        else:
            raise typer.BadParameter(f"Unknown file type.  Only python or json are supported.")


    except typer.BadParameter as ex:
        raise ex
    
    except Exception as e:
        raise typer.BadParameter(f"Failed to load model from file {file}: {e}")
    
    tool = create_flow_json_tool(name=model["spec"]["name"],
                                 description=model["spec"]["description"], 
                                 permission="read_only", 
                                 flow_model=model)   
    tools = [tool]
    # tools = import_flow_support_tools(model=model)
    # tools.append(tool)

    return tools

async def import_openapi_tool(file: str, connection_id: str) -> List[BaseTool]:
    tools = await create_openapi_json_tools_from_uri(file, connection_id)
    return tools

async def import_langflow_tool(file: str, app_id: List[str] = None):    
    try:
        file_path = Path(file).absolute()

        if file_path.is_dir():
            raise typer.BadParameter(f"Provided langflow file path is not a file.")

        if file_path.is_symlink():
            raise typer.BadParameter(f"Symbolic links are not supported for langflow file path.")

        if file_path.suffix.lower() != ".json":
            raise typer.BadParameter(f"Unsupported langflow file type. Only json files are supported.")
        
        with safe_open(file) as f:
            imported_tool = json.load(f)

    except typer.BadParameter as ex:
        raise BadRequest(ex)
        

    except Exception:
        raise BadRequest(f"Failed to load langflow tool from file {file}")
    
    validate_app_ids(kind=ToolKind.langflow, app_ids=app_id)
    connections = get_connection_ids(app_ids=app_id, environment='draft')
    
    tool = create_langflow_tool(tool_definition=imported_tool, connections=connections)

    return tool    


def _get_kind_from_spec(spec: dict) -> ToolKind:
    name = spec.get("name")
    tool_binding = spec.get("binding")

    if ToolKind.python in tool_binding:
        return ToolKind.python
    elif ToolKind.openapi in tool_binding:
        return ToolKind.openapi
    elif ToolKind.langflow in tool_binding:
        return ToolKind.langflow
    elif ToolKind.mcp in tool_binding:
        return ToolKind.mcp
    elif 'flow' in tool_binding:
        return ToolKind.flow
    else:
        logger.error(f"Could not determine 'kind' of tool '{name}'")
        sys.exit(1) 

def _get_connection_ids_from_spec(spec: ToolSpec | dict) -> list[str]:
    if isinstance(spec, dict):
        spec = ToolSpec.model_validate(spec)

    connection_ids = []

    binding = spec.binding
    if binding is not None:
        if binding.openapi is not None and hasattr(binding.openapi, "connection_id"):
            connection_ids = [binding.openapi.connection_id]
        elif binding.python is not None and hasattr(binding.python, "connections") and binding.python.connections is not None:
            for conn in binding.python.connections:
                connection_ids.append(binding.python.connections[conn])
        elif binding.mcp is not None and hasattr(binding.mcp, "connections"):
            if binding.mcp.connections is None:
                connection_ids.append(None)
            else:
                for conn in binding.mcp.connections:
                    connection_ids.append(binding.mcp.connections[conn])
        elif binding.langflow is not None and hasattr(binding.langflow, "connections"):
            if binding.langflow.connections is None:
                connection_ids.append(None)
            else:
                for conn in binding.langflow.connections:
                    connection_ids.append(binding.langflow.connections[conn])
        
        return connection_ids

def get_whl_in_registry(registry_url: str, version: str) -> str| None:
    orchestrate_links = requests.get(registry_url).text
    wheel_files = [x.group(1) for x in re.finditer( r'href="(.*\.whl).*"', orchestrate_links)]
    wheel_file = next(filter(lambda x: f"{version}-py3-none-any.whl" in x, wheel_files), None)
    return wheel_file

    
class DownloadResult(BaseModel):
    content: bytes | None = None
    kind: ToolKind

class ToolsController:
    def __init__(self, tool_kind: ToolKind = None, file: str = None, requirements_file: Optional[str] = None):
        self.client = None
        self.tool_kind = tool_kind
        self.file = file
        self.cleanup_file = False
        self.requirements_file = requirements_file

    def get_client(self) -> ToolClient:
        if not self.client:
            self.client = instantiate_client(ToolClient)
        return self.client
    
    def resolve_file(self, name: str = None):        
        if not self.file and self.tool_kind == ToolKind.langflow:
            langflow_tool_json = LangflowController().export_tool_from_langflow(name)

            with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8", suffix=".json", delete=False) as fp:
                json.dump(langflow_tool_json, fp, indent=4)
                fp.flush()
                tempfile_path = os.path.abspath(fp.name)
                self.set_file(new_file=tempfile_path, cleanup=True)

        return self.file

    def set_file(self, new_file: str, cleanup: bool = False):
        self.file = new_file
        self.cleanup_file = cleanup

    def remove_temp_file(self):
        if self.cleanup_file:
            os.unlink(self.file)

    @staticmethod
    def import_tool(kind: ToolKind, **args) -> Iterable[BaseTool]:
        # Ensure app_id is a list
        if args.get("app_id") and isinstance(args.get("app_id"), str):
            args["app_id"] = [args.get("app_id")]

        validate_params(kind=kind, **args)

        match kind:
            case "python":
                tools = import_python_tool(
                    file=args["file"],
                    requirements_file=args.get("requirements_file"),
                    app_id=args.get("app_id"),
                    package_root=args.get("package_root")
                )

            case "openapi":
                connections_client = get_connections_client()
                app_id = args.get('app_id', None)
                connection_id = None
                if app_id is not None:
                    app_id = app_id[0]
                    connection = connections_client.get_draft_by_app_id(app_id=app_id)
                    connection_id = connection.connection_id
                tools = run_coroutine_sync(import_openapi_tool(file=args["file"], connection_id=connection_id))
            case "flow":
                tools = run_coroutine_sync(import_flow_tool(file=args["file"]))
            case "skill":
                tools = []
                logger.warning("Skill Import not implemented yet")
            case "langflow":
                app_id = args.get('app_id', None)
                file_path = args.get('file')
                tools = run_coroutine_sync(import_langflow_tool(file=file_path,app_id=app_id))
            case _:
                raise BadRequest("Invalid kind selected")

        if not isinstance(tools,list):
            tools = [tools]
        
        if len(tools) == 0:
            kind_str = kind.value if isinstance(kind, ToolKind) else kind
            logger.warning(f"No valid '{kind_str}' tools found in provided file '{args.get('file')}'. No tools have been imported")

        for tool in tools:
            yield tool


    def list_tools(self, verbose=False, format: ListFormats| None = None) -> List[dict[str, Any]] | str | None:
        if verbose and format:
            logger.error("For tools list, `--verbose` and `--format` are mutually exclusive options")
            sys.exit(1)

        response = self.get_client().get()
        tool_specs = []
        parse_errors = []

        for tool in response:
            try:
                tool_specs.append(ToolSpec.model_validate(tool, context="list"))
            except Exception as e:
                name = tool.get('name', None)
                parse_errors.append([
                    f"Tool '{name}' could not be parsed",
                    json.dumps(tool),
                    e
                ])

        tools = [BaseTool(spec=spec) for spec in tool_specs]

        if verbose:
            tools_list = []
            for tool in tools:
                tools_list.append(json.loads(tool.dumps_spec(exclude_none=False)))

            rich.print_json(json.dumps(tools_list, indent=4))
            return tools_list
        else:
            tool_details = []

            connections_client = get_connections_client()
            connections = connections_client.list()

            connections_dict = {conn.connection_id: conn for conn in connections}

            table = rich.table.Table(show_header=True, header_style="bold white", show_lines=True)
            column_args = {
                "Name": {"overflow": "fold"},
                "Description": {},
                "Type": {}, 
                "Toolkit": {}, 
                "App ID": {"overflow": "fold"}
            }
            for column in column_args:
                table.add_column(column,**column_args[column])

            for tool in tools:
                tool_binding = tool.__tool_spec__.binding

                connection_ids = _get_connection_ids_from_spec(spec=tool.__tool_spec__)

                app_ids = []
                for connection_id in connection_ids:
                    connection = connections_dict.get(connection_id)
                    if connection:
                        app_id = str(connection.app_id or connection.connection_id)
                    elif connection_id:
                        app_id = str(connection_id)
                    else:
                        app_id = ""
                    app_ids.append(app_id)

                if tool_binding.python is not None:
                        tool_type=ToolKind.python
                elif tool_binding.openapi is not None:
                        tool_type=ToolKind.openapi
                elif tool_binding.mcp is not None:
                        tool_type=ToolKind.mcp
                elif tool_binding.flow is not None:
                        tool_type=ToolKind.flow  
                elif tool_binding.langflow is not None:
                        tool_type=ToolKind.langflow      
                else:
                        tool_type="Unknown"
                
                toolkit_name = ""

                if tool.__tool_spec__.toolkit_id:
                    toolkit_client = instantiate_client(ToolKitClient)
                    toolkit = toolkit_client.get_draft_by_id(tool.__tool_spec__.toolkit_id)
                    if isinstance(toolkit, dict) and "name" in toolkit:
                        toolkit_name = toolkit["name"]
                    elif toolkit:
                        toolkit_name = str(toolkit)
                
                entry = ToolListEntry(
                    name=tool.__tool_spec__.name,
                    description=tool.__tool_spec__.description,
                    type=tool_type,
                    toolkit=toolkit_name,
                    app_ids=app_ids
                )

                if format == ListFormats.JSON:
                    tool_details.append(entry)
                else:
                    table.add_row(*entry.get_row_details())

            match format:
                case ListFormats.JSON:
                    return tool_details
                case ListFormats.Table:
                    return rich_table_to_markdown(table)
                case _:
                    rich.print(table)

        for error in parse_errors:
            for l in error:
                logger.error(l)

    def get_all_tools(self) -> dict:
        return {entry["name"]: entry["id"] for entry in self.get_client().get()}

    def publish_or_update_tools(self, tools: Iterable[BaseTool], package_root: str = None) -> None:
        resolved_package_root = get_package_root(package_root)

        # Zip the tool's supporting artifacts for python tools
        with tempfile.TemporaryDirectory() as tmpdir:
            for tool in tools:
                exist = False
                tool_id = None

                existing_tools = self.get_client().get_draft_by_name(tool.__tool_spec__.name)
                if len(existing_tools) > 1:
                    logger.error(f"Multiple existing tools found with name '{tool.__tool_spec__.name}'. Failed to update tool")
                    sys.exit(1)

                if len(existing_tools) > 0:
                    existing_tool = existing_tools[0]
                    exist = True
                    tool_id = existing_tool.get("id")

                tool_artifact = None
                if self.tool_kind == ToolKind.python:
                    tool_artifact = path.join(tmpdir, "artifacts.zip")
                    with zipfile.ZipFile(tool_artifact, "w", zipfile.ZIP_DEFLATED) as zip_tool_artifacts:
                        resolved_requirements_file = get_resolved_py_tool_reqs_file(tool_file=self.file,
                                                                                    requirements_file=self.requirements_file,
                                                                                    package_root=resolved_package_root)

                        if resolved_package_root is None:
                            # single file.
                            file_path = Path(self.file)
                            zip_tool_artifacts.write(file_path, arcname=f"{file_path.stem}.py")

                        else:
                            # multi-file.
                            path_strs = sorted(set([x for x in glob.iglob(path.join(resolved_package_root, '**/**'), include_hidden=True, recursive=True)]))
                            for path_str in path_strs:
                                path_obj = Path(path_str)

                                if not path_obj.is_file() or "/__pycache__/" in path_str or path_obj.name.lower() == "requirements.txt":
                                    continue

                                if path_obj.is_symlink():
                                    raise typer.BadParameter(f"Symbolic links in packages are not supported. - {path_str}")

                                try:
                                    zip_tool_artifacts.write(path_str, arcname=str(Path(path_str).relative_to(Path(resolved_package_root))))

                                except Exception as ex:
                                    logger.error(f"Could not write file {path_str} to artifact. {ex}")
                                    raise ex

                            zip_tool_artifacts.writestr("tool-spec.json", tool.dumps_spec())

                        requirements = []
                        if resolved_requirements_file is not None:
                            requirements = get_requirement_lines(requirements_file=resolved_requirements_file, remove_trailing_newlines=False)

                        # Ensure there is a newline at the end of the file
                        if len(requirements) > 0 and not requirements[-1].endswith("\n"):
                            requirements[-1] = requirements[-1]+"\n"

                        cfg = Config()
                        registry_type = cfg.read(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT) or DEFAULT_CONFIG_FILE_CONTENT[PYTHON_REGISTRY_HEADER][PYTHON_REGISTRY_TYPE_OPT]
                        skip_version_check = cfg.read(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_SKIP_VERSION_CHECK_OPT) or DEFAULT_CONFIG_FILE_CONTENT[PYTHON_REGISTRY_HEADER][PYTHON_REGISTRY_SKIP_VERSION_CHECK_OPT]

                        version = __version__
                        if registry_type == RegistryType.LOCAL:
                            logger.warning(f"Using a local registry which is for development purposes only")
                            requirements.append(f"/packages/ibm_watsonx_orchestrate-0.6.0-py3-none-any.whl\n")
                        elif registry_type == RegistryType.PYPI:
                            if not skip_version_check:
                                wheel_file = get_whl_in_registry(registry_url='https://pypi.org/simple/ibm-watsonx-orchestrate', version=version)
                                if not wheel_file:
                                    logger.error(f"Could not find ibm-watsonx-orchestrate@{version} on https://pypi.org/project/ibm-watsonx-orchestrate")
                                    exit(1)
                            requirements.append(f"ibm-watsonx-orchestrate=={version}\n")
                        elif registry_type == RegistryType.TESTPYPI:
                            override_version = cfg.get(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT) or version
                            wheel_file = get_whl_in_registry(registry_url='https://test.pypi.org/simple/ibm-watsonx-orchestrate', version=override_version)
                            if not wheel_file:
                                logger.error(f"Could not find ibm-watsonx-orchestrate@{override_version} on https://test.pypi.org/project/ibm-watsonx-orchestrate")
                                exit(1)
                            requirements.append(f"ibm-watsonx-orchestrate @ {wheel_file}\n")
                        else:
                            logger.error(f"Unrecognized registry type provided to orchestrate env activate local --registry <registry>")
                            exit(1)
                        requirements_file = path.join(tmpdir, 'requirements.txt')

                        requirements = list(dict.fromkeys(requirements))

                        with safe_open(requirements_file, 'w') as fp:
                            fp.writelines(requirements)
                        requirements_file_path = Path(requirements_file)
                        zip_tool_artifacts.write(requirements_file_path, arcname='requirements.txt')

                        zip_tool_artifacts.writestr("bundle-format", "2.0.0\n")
                        
                elif self.tool_kind == ToolKind.langflow:

                    tool_artifact = path.join(tmpdir, "artifacts.zip")

                    with zipfile.ZipFile(tool_artifact, "w", zipfile.ZIP_DEFLATED) as zip_tool_artifacts:
                        tool_path = Path(self.file)
                        zip_tool_artifacts.write(tool_path, arcname=f"{tool_path.stem}.json")

                        requirements = []

                        if self.requirements_file:
                            requirements_file_path = Path(self.requirements_file)
                            requirements.extend(
                                get_requirement_lines(requirements_file=requirements_file_path, remove_trailing_newlines=False)
                            )

                        langflowTool = cast(LangflowTool, tool)
                        # if there are additional requriements from the langflow model, we should add it to the requirement set
                        if langflowTool.requirements and len(langflowTool.requirements) > 0:
                            requirements.extend(langflowTool.requirements)

                        # now check if the requirements contain modules listed in DEFAULT_LANGFLOW_RUNNER_MODULES
                        # if it is needed, we are assuming the user wants to override the default langflow module
                        # with a specific version
                        runner_overridden = False
                        for r in requirements:
                            # get the module name from the requirements
                            module_name = r.strip().split('==')[0].split('=')[0].split('>=')[0].split('<=')[0].split('~=')[0].lower()
                            if not module_name.startswith('#'):
                                if module_name in DEFAULT_LANGFLOW_RUNNER_MODULES:
                                    runner_overridden = True
                        
                        if not runner_overridden:
                            # add the default runner to the top of requirement list
                            requirements = DEFAULT_LANGFLOW_TOOL_REQUIREMENTS + list(requirements)

                        requirements_content = '\n'.join(requirements) + '\n'
                        zip_tool_artifacts.writestr("requirements.txt",requirements_content)  
                        zip_tool_artifacts.writestr("bundle-format", "2.0.0\n")
                elif self.tool_kind == ToolKind.openapi:
                    tool_artifact = path.join(tmpdir, "artifacts.zip")

                    with zipfile.ZipFile(tool_artifact, "w", zipfile.ZIP_DEFLATED) as zip_tool_artifacts:
                        tool_path = Path(self.file)
                        zip_tool_artifacts.write(tool_path, arcname=tool_path.name)

                        zip_tool_artifacts.writestr("bundle-format", "2.0.0\n")
                if exist:
                    self.update_tool(tool_id=tool_id, tool=tool, tool_artifact=tool_artifact)
                else:
                    self.publish_tool(tool=tool, tool_artifact=tool_artifact)

    def publish_tool(self, tool: BaseTool, tool_artifact: str) -> None:
        tool_spec = tool.__tool_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)

        response = self.get_client().create(tool_spec)
        tool_id = response.get("id")

        if tool_artifact is not None:
            match self.tool_kind:
                case ToolKind.langflow | ToolKind.python | ToolKind.openapi:
                    self.get_client().upload_tools_artifact(tool_id=tool_id, file_path=tool_artifact)
                case _:
                    raise ValueError(f"Unexpected artifact for {self.tool_kind} tool")

        logger.info(f"Tool '{tool.__tool_spec__.name}' imported successfully")

    def update_tool(self, tool_id: str, tool: BaseTool, tool_artifact: str) -> None:
        tool_spec = tool.__tool_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)

        logger.info(f"Existing Tool '{tool.__tool_spec__.name}' found. Updating...")

        self.get_client().update(tool_id, tool_spec)

        if tool_artifact is not None:
            match self.tool_kind:
                case ToolKind.langflow | ToolKind.python | ToolKind.openapi:
                    self.get_client().upload_tools_artifact(tool_id=tool_id, file_path=tool_artifact)
                case _:
                    raise ValueError(f"Unexpected artifact for {self.tool_kind} tool")

        logger.info(f"Tool '{tool.__tool_spec__.name}' updated successfully")

    def remove_tool(self, name: str):
        try:
            client = self.get_client()
            draft_tools = client.get_draft_by_name(tool_name=name)
            if len(draft_tools) > 1:
                logger.error(f"Multiple existing tools found with name '{name}'. Failed to remove tool")
                sys.exit(1)
            if len(draft_tools) > 0:
                draft_tool = draft_tools[0]
                tool_id = draft_tool.get("id")
                self.get_client().delete(tool_id=tool_id)
                logger.info(f"Successfully removed tool {name}")
            else:
                logger.warning(f"No tool named '{name}' found")
        except requests.HTTPError as e:
            logger.error(e.response.text)
            exit(1)

    def serialize_to_json_in_zip(self, obj: any, filename: str) -> bytes:
        # Serialize the Python object to a JSON string
        json_str = json.dumps(obj, indent=2)
        
        # Create a BytesIO object to hold the in-memory zip file
        zip_in_memory = io.BytesIO()
        
        # Create a ZipFile object in append mode
        with zipfile.ZipFile(zip_in_memory, 'a') as zip_file:
            # Write the JSON string as a file named 'data.json' inside the zip
            zip_file.writestr(filename, json_str)
        
        # Seek to the beginning of the BytesIO object to return the in-memory zip file as bytes
        zip_in_memory.seek(0)
    
        return zip_in_memory.getvalue()

    def download_tool(self, name: str) -> DownloadResult | None:
        tool_client = self.get_client()
        draft_tools = tool_client.get_draft_by_name(tool_name=name)
        if len(draft_tools) > 1:
            logger.error(f"Multiple existing tools found with name '{name}'. Failed to get tool")
            sys.exit(1)
        if len(draft_tools) == 0:
            logger.error(f"No tool named '{name}' found")
            sys.exit(1)

        draft_tool = draft_tools[0]
        draft_tool_kind = _get_kind_from_spec(draft_tool)
        
        supported_toolkinds = [ToolKind.python,ToolKind.langflow,ToolKind.flow, ToolKind.openapi]
        if draft_tool_kind not in supported_toolkinds:
            logger.warning(f"Skipping '{name}', {draft_tool_kind.value} tools are currently unsupported by export")
            return

        tool_id = draft_tool.get("id")
        
        # Initialize tool_artifacts_bytes with an empty bytes object as default
        tool_artifacts_bytes = b''
        
        if tool_id is not None:
            try:
                downloaded_bytes = tool_client.download_tools_artifact(tool_id=tool_id)
                if downloaded_bytes is not None:
                    tool_artifacts_bytes = downloaded_bytes
                else:
                    logger.warning(f"No artifacts found for tool '{name}' of kind {draft_tool_kind.value}")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code != 404:
                    raise e
                if draft_tool_kind == ToolKind.openapi:
                    logger.warning(f"Skipping '{name}', could not find uploaded OpenAPI specification for this tool.")
                    return None
                else:
                    BadRequest(f"Could not find tool artifacts for tool '{name}'")
            except Exception as e:
                logger.warning(f"Error downloading artifacts for tool '{name}': {str(e)}")
                return None
        
        # Always return a DownloadResult with at least empty content
        return DownloadResult(content=tool_artifacts_bytes, kind=draft_tool_kind)
    
    def export_tool(
            self,
            name: str,
            output_path: str, 
            zip_file_out: Optional[zipfile.ZipFile] = None, 
            connections_output_path: str = "/connections", 
            spec: dict | None = None) -> None:
        
        output_file = Path(output_path)
        output_file_extension = output_file.suffix
        if not zip_file_out and  output_file_extension != ".zip":
            logger.error(f"Output file must end with the extension '.zip'. Provided file '{output_path}' ends with '{output_file_extension}'")
            sys.exit(1)
        
        if not spec:
            client = self.get_client()
            specs = client.get_draft_by_name(name)
            if len(specs):
                spec = specs[0]
            else:
                logger.error(f"Could not find tool spec for tool '{name}'")
                sys.exit(1)
        
        # Check if its an MCP tool if so call toolkit export instead
        kind = _get_kind_from_spec(spec)
        if kind == ToolKind.mcp:
            name_parts = name.split(":")

            if len(name_parts) < 2:
                BadRequest(f"The tool '{name}' does not match the naming scheme expected of an MCP tool '<toolkit_name>:<tool_name>'")
            toolkit_name = name_parts[0]
            tc = ToolkitController()
            tc.export_toolkit(
                name=toolkit_name,
                output_file=output_file,
                zip_file_out=zip_file_out,
                connections_output_path=connections_output_path
            )
            return
        
        logger.info(f"Exporting tool definition for '{name}' to '{output_path}'")

        tool_artifact: DownloadResult | None = self.download_tool(name)

        connection_ids = _get_connection_ids_from_spec(spec)
        connection_ids = [c for c in connection_ids if c]
        connections = get_connections_client().get_drafts_by_ids(connection_ids)
        app_ids = [conn.app_id for conn in connections]

        if not tool_artifact or not tool_artifact.content:
            return
        
        zip_file_root_folder = "/"
        if zip_file_out:
            zip_file_root_folder = output_path
        else:
            zip_file_out = zipfile.ZipFile(output_path, "w")
        
        with zipfile.ZipFile(io.BytesIO(tool_artifact.content), "r") as zip_file_in:
          
            for item in zip_file_in.infolist():
                buffer = zip_file_in.read(item.filename)
                if (item.filename != 'bundle-format'):
                    zip_file_out.writestr(f"{zip_file_root_folder}/{item.filename}", buffer)
        
        for app_id in app_ids:
            export_connection(output_file=connections_output_path, app_id=app_id, zip_file_out=zip_file_out)
        
        logger.info(f"Successfully exported tool definition for '{name}' to '{output_path}'")

        if tool_artifact.kind == ToolKind.flow:
            tools_in_flow = get_all_tools_in_flow(json.loads(buffer))

            for t in tools_in_flow:
                self.export_tool(
                    name=t,
                    output_path=f"{output_file.parent}/{t}",
                    zip_file_out=zip_file_out,
                    connections_output_path=connections_output_path
                )

    def auto_discover_tools(self, input_file: str, env_file: str, output_file: Optional[str] = None, llm: Optional[str] = None, function_names: Optional[list[str]] = None):
        
        if Path(input_file).suffix.lower() != ".py":
            raise typer.BadParameter(f"Auto-discover is only valid for python tools")
        
        if output_file and Path(output_file).suffix.lower() != ".py":
            raise typer.BadParameter(f"Output file must be a valid python file name")

        if not env_file:
            raise typer.BadParameter(f"Python tool auto discover requires an env file to be passed with the '--env-file' flag")
        
        if function_names is not None and not isinstance(function_names,list):
            function_names = [function_names]
        
        output_path = auto_discover_python_tools(
            file=input_file, 
            output_file=output_file,
            env_file=env_file,
            llm=llm,
            function_names=function_names
        )
        return Path(output_path).absolute()