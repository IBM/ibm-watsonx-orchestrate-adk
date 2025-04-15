import logging
import asyncio
import importlib
import inspect
import sys
import re
import tempfile
import requests
import zipfile
from enum import Enum
from os import path
from pathlib import Path
from typing import Iterable, List
import rich
import json
from rich.json import JSON

import rich.table
import typer

from ibm_watsonx_orchestrate.agent_builder.tools import BaseTool, ToolSpec
from ibm_watsonx_orchestrate.agent_builder.tools.openapi_tool import create_openapi_json_tools_from_uri
from ibm_watsonx_orchestrate.cli.commands.tools.types import RegistryType
from ibm_watsonx_orchestrate.cli.config import Config, CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT, \
    PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT, \
    DEFAULT_CONFIG_FILE_CONTENT
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.connections.applications_connections_client import ApplicationConnectionsClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.utils import sanatize_app_id
from ibm_watsonx_orchestrate.utils.request import BadRequest

logger = logging.getLogger(__name__)


class ToolKind(str, Enum):
    openapi = "openapi"
    python = "python"
    # skill = "skill"

def validate_app_ids(kind: ToolKind, **args) -> None:
    app_ids = args.get("app_id")
    if not app_ids:
        return
    
    if kind == ToolKind.openapi:
        if app_ids and len(app_ids) > 1:
            raise typer.BadParameter(
                "Kind 'openapi' can only take one app-id"
            )
    
    connections_client = instantiate_client(ApplicationConnectionsClient)

    imported_connections_list = connections_client.get()
    imported_connections = {conn.appid:conn for conn in imported_connections_list}

    for app_id in app_ids:
        if kind == ToolKind.python:
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
            
        if app_id not in imported_connections:
            logger.warning(f"No connection found for provided app-id '{app_id}'. Please create the connection using `orchestrate connections application create`")

        else:
            if kind == ToolKind.openapi and imported_connections.get(app_id).connection_type == 'key_value':
                logger.error(f"Key value application connections can not be bound to an openapi tool")
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
    connections_client = instantiate_client(ApplicationConnectionsClient)
    connection_id = None
    if app_id is not None:
        connections = connections_client.get_draft_by_app_id(app_id=app_id)
        if len(connections) == 0:
            logger.error(f"No connection exists with the app-id '{app_id}'")
            exit(1)
        elif len(connections) > 1:
            logger.error(f"Internal error, ambiguious request, multiple Connection IDs found for app-id {', '.join(list(map(lambda e: e.connection_id, connections)))}")
            exit(1)
        connection_id = connections[0].connection_id
    return connection_id


def parse_python_app_ids(app_ids: List[str]) -> dict[str,str]:
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

        runtime_id = sanatize_app_id(runtime_id)
        app_id_dict[runtime_id] = get_connection_id(local_id)

    return app_id_dict

def validate_python_connections(tool: BaseTool):
    if not tool.expected_credentials:
        return
    
    connections_client = instantiate_client(ApplicationConnectionsClient)
    connections = tool.__tool_spec__.binding.python.connections

    provided_connections = list(connections.keys()) if connections else []
    imported_connections_list = connections_client.get()
    imported_connections = {conn.connection_id:conn for conn in imported_connections_list}

    validation_failed = False

    existing_sanatized_expected_tool_app_ids = set()

    for expected_cred in tool.expected_credentials:
        expected_tool_app_id=None
        expected_tool_type=None

        if isinstance(expected_cred, str):
            expected_tool_app_id = expected_cred
        else:
            expected_tool_app_id = expected_cred.get("app_id")
            expected_tool_type = expected_cred.get("type")
        
        sanatized_expected_tool_app_id = sanatize_app_id(expected_tool_app_id)
        if sanatized_expected_tool_app_id in existing_sanatized_expected_tool_app_ids:
            logger.error(f"Duplicate App ID found '{expected_tool_app_id}'. Multiple expected app ids in the tool '{tool.__tool_spec__.name}' collide after sanaitization to '{sanatized_expected_tool_app_id}'. Please rename the offending app id in your tool.")
            sys.exit(1)
        existing_sanatized_expected_tool_app_ids.add(sanatized_expected_tool_app_id)
        
        if sanatized_expected_tool_app_id not in provided_connections:
            logger.error(f"The tool '{tool.__tool_spec__.name}' requires an app-id '{expected_tool_app_id}'. Please use the `--app-id` flag to provide the required app-id")
            validation_failed = True

        if not connections:
            continue

        connection_id = connections.get(sanatized_expected_tool_app_id)
        
        imported_connection = imported_connections.get(connection_id)

        if connection_id and not imported_connection:
            logger.error(f"The expected connection id '{connection_id}' does not match any known connection. This is likely caused by the connection being delted. Please rec-reate the connection and re-import the tool")
            validation_failed = True

        if imported_connection and expected_tool_type and expected_tool_type != imported_connection.connection_type:
            logger.error(f"The app-id '{imported_connection.appid}' is of type '{imported_connection.connection_type}'. The tool '{tool.__tool_spec__.name}' expects this connection to be of type '{expected_tool_type}'. Use `orchestrate connections application list` to view current connections and use `orchestrate connections application create` to create or update the relevent connection")
            validation_failed = True
        
    if validation_failed:
        exit(1)


def import_python_tool(file: str, requirements_file: str = None, app_id: List[str] = None) -> None:
    try:
        file_path = Path(file)
        file_directory = file_path.parent
        file_name = file_path.stem
        sys.path.append(str(file_directory))
        module = importlib.import_module(file_name)
        del sys.path[-1]
    except Exception as e:
        raise typer.BadParameter(f"Failed to load python module from file {file}: {e}")

    requirements = []
    if requirements_file is not None:
        try:
            requirements_file_path = Path(requirements_file)
            with open(requirements_file_path) as read_requirements:
                while line := read_requirements.readline():
                    requirements.append(line.rstrip())
        except Exception as e:
            raise typer.BadParameter(f"Failed to read file {requirements_file} {e}")

    tools = []
    for _, obj in inspect.getmembers(module):
        if isinstance(obj, BaseTool) :
            obj.__tool_spec__.binding.python.requirements = requirements
            if app_id and len(app_id):
                obj.__tool_spec__.binding.python.connections = parse_python_app_ids(app_id)
            validate_python_connections(obj)
            tools.append(obj)
    
    return tools

async def import_openapi_tool(file: str, connection_id: str) -> List[BaseTool]:
    tools = await create_openapi_json_tools_from_uri(file, connection_id)
    return tools

class ToolsController:
    def __init__(self, tool_kind: ToolKind = None, file: str = None, requirements_file: str = None):
        self.client = None
        self.tool_kind = tool_kind
        self.file = file
        self.requirements_file = requirements_file

    def get_client(self) -> ToolClient:
        if not self.client:
            self.client = instantiate_client(ToolClient)
        return self.client

    @staticmethod
    def import_tool(kind: ToolKind, **args) -> Iterable:
        # Ensure app_id is a list
        if args.get("app_id") and isinstance(args.get("app_id"), str):
            args["app_id"] = [args.get("app_id")]
    
        validate_params(kind=kind, **args)

        match kind:
            case "python":
                tools = import_python_tool(file=args["file"], requirements_file=args["requirements_file"], app_id=args.get("app_id"))
            case "openapi":
                connections_client: ApplicationConnectionsClient =  instantiate_client(ApplicationConnectionsClient)
                app_id = args.get('app_id', None)
                connection_id = None
                if app_id is not None:
                    app_id = app_id[0]
                    connections = connections_client.get_draft_by_app_id(app_id=app_id)
                    if len(connections) == 0:
                        logger.error(f"No connection exists with the app-id '{app_id}'")
                        exit(1)
                    elif len(connections) > 1:
                        logger.error(f"Internal error, ambiguious request, multiple Connection IDs found for app-id {', '.join(list(map(lambda e: e.connection_id, connections)))}")
                        exit(1)
                    connection_id = connections[0].connection_id
                tools = asyncio.run(import_openapi_tool(file=args["file"], connection_id=connection_id))
            case "skill":
                tools = []
                logger.warning("Skill Import not implemented yet")
            case _:
                raise BadRequest("Invalid kind selected")

        for tool in tools:
            yield tool


    def list_tools(self, verbose=False):
        response = self.get_client().get()
        tool_specs = [ToolSpec.model_validate(tool) for tool in response]
        tools = [BaseTool(spec=spec) for spec in tool_specs]
        

        if verbose:
            tools_list = []
            for tool in tools:

                tools_list.append(json.loads(tool.dumps_spec()))

            rich.print(JSON(json.dumps(tools_list, indent=4)))
        else:
            table = rich.table.Table(show_header=True, header_style="bold white", show_lines=True)
            columns = ["Name", "Description", "Permission", "Type", "App ID"]
            for column in columns:
                table.add_column(column)
            
            for tool in tools:
                tool_binding = tool.__tool_spec__.binding
                
                connection_ids = []

                if tool_binding is not None:
                    if tool_binding.openapi is not None and hasattr(tool_binding.openapi, "connection_id"):
                        connection_ids = [tool_binding.openapi.connection_id]
                    elif tool_binding.python is not None and hasattr(tool_binding.python, "connections") and tool_binding.python.connections is not None:
                        for conn in tool_binding.python.connections:
                            connection_ids.append(tool_binding.python.connections[conn])
                
                connections_client: ApplicationConnectionsClient = instantiate_client(ApplicationConnectionsClient)
                app_ids = []
                for connection_id in connection_ids:
                    app_id = str(connections_client.get_draft_by_id(connection_id))
                    app_ids.append(app_id)

                if tool_binding.python is not None:
                        tool_type=ToolKind.python
                elif tool_binding.openapi is not None:
                        tool_type=ToolKind.openapi
                else:
                        tool_type="Unknown"
                
                table.add_row(
                    tool.__tool_spec__.name,
                    tool.__tool_spec__.description,
                    tool.__tool_spec__.permission,
                    tool_type,
                    ", ".join(app_ids),
                )

            rich.print(table)

    def get_all_tools(self) -> dict:
        return {entry["name"]: entry["id"] for entry in self.get_client().get()}

    def publish_or_update_tools(self, tools: Iterable[BaseTool]) -> None:
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
                        file_path = Path(self.file)
                        zip_tool_artifacts.write(file_path, arcname=f"{tool.__tool_spec__.name}.py")

                        requirements = []
                        if self.requirements_file is not None:
                            with open(self.requirements_file, 'r') as fp:
                                requirements = fp.readlines()
                        # Ensure there is a newline at the end of the file
                        if len(requirements) > 0 and not requirements[-1].endswith("\n"):
                            requirements[-1] = requirements[-1]+"\n"

                        cfg = Config()
                        registry_type = cfg.read(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT) or DEFAULT_CONFIG_FILE_CONTENT[PYTHON_REGISTRY_HEADER][PYTHON_REGISTRY_TYPE_OPT]

                        version = importlib.import_module('ibm_watsonx_orchestrate').__version__
                        if registry_type == RegistryType.LOCAL:
                            requirements.append(f"/packages/ibm_watsonx_orchestrate-0.6.0-py3-none-any.whl\n")
                        elif registry_type == RegistryType.PYPI:
                            requirements.append(f"ibm-watsonx-orchestrate=={version}\n")
                        elif registry_type == RegistryType.TESTPYPI:
                            override_version = cfg.get(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT) or version
                            orchestrate_links = requests.get('https://test.pypi.org/simple/ibm-watsonx-orchestrate').text
                            wheel_files = [x.group(1) for x in re.finditer( r'href="(.*\.whl).*"', orchestrate_links)]
                            wheel_file = next(filter(lambda x: override_version in x, wheel_files), None)
                            if not wheel_file:
                                logger.error(f"Could not find ibm-watsonx-orchestrate@{override_version} on https://test.pypi.org/project/ibm-watsonx-orchestrate")
                                exit(1)
                            requirements.append(f"ibm-watsonx-orchestrate @ {wheel_file}\n")
                        else:
                            logger.error(f"Unrecognized registry type provided to orchestrate env activate local --registry <registry>")
                            exit(1)
                        requirements_file = path.join(tmpdir, 'requirements.txt')

                        with open(requirements_file, 'w') as fp:
                            fp.writelines(requirements)
                        requirements_file_path = Path(requirements_file)
                        zip_tool_artifacts.write(requirements_file_path, arcname='requirements.txt')

                        bundle_format_file = path.join(tmpdir, 'bundle-format')
                        with open(bundle_format_file, 'w') as fp:
                            fp.writelines(['1.0.0'])
                        zip_tool_artifacts.write(Path(bundle_format_file), arcname='bundle-format')

                if exist:
                    self.update_tool(tool_id=tool_id, tool=tool, tool_artifact=tool_artifact)
                else:
                    self.publish_tool(tool, tool_artifact=tool_artifact)

    def publish_tool(self, tool: BaseTool, tool_artifact: str) -> None:
        tool_spec = tool.__tool_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)

        response = self.get_client().create(tool_spec)
        tool_id = response.get("id")

        if tool_artifact is not None:
            self.get_client().upload_tools_artifact(tool_id=tool_id, file_path=tool_artifact)

        logger.info(f"Tool '{tool.__tool_spec__.name}' imported successfully")

    def update_tool(self, tool_id: str, tool: BaseTool, tool_artifact: str) -> None:
        tool_spec = tool.__tool_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)

        logger.info(f"Existing Tool '{tool.__tool_spec__.name}' found. Updating...")

        self.get_client().update(tool_id, tool_spec)

        if tool_artifact is not None:
            self.get_client().upload_tools_artifact(tool_id=tool_id, file_path=tool_artifact)

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
