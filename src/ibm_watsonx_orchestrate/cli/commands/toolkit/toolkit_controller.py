import os
import zipfile
import tempfile
from typing import List, Optional
from enum import Enum
import logging
import sys
import re
import requests
from ibm_watsonx_orchestrate.client.toolkit.toolkit_client import ToolKitClient
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit import BaseToolkit, ToolkitSpec
from ibm_watsonx_orchestrate.agent_builder.toolkits.types import ToolkitKind, Language, ToolkitSource
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.utils import sanatize_app_id
from ibm_watsonx_orchestrate.client.connections import get_connections_client
import typer
import json
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from ibm_watsonx_orchestrate.client.utils import is_local_dev
from rich.json import JSON
import rich
import rich.table
import json

logger = logging.getLogger(__name__)

def get_connection_id(app_id: str) -> str:
    connections_client = get_connections_client()
    existing_draft_configuration = connections_client.get_config(app_id=app_id, env='draft')
    existing_live_configuration = connections_client.get_config(app_id=app_id, env='live')

    for config in [existing_draft_configuration, existing_live_configuration]:
        if config and config.security_scheme != 'key_value_creds':
            logger.error("Only key_value credentials are currently supported")
            exit(1)
    connection_id = None
    if app_id is not None:
        connection = connections_client.get(app_id=app_id)
        if  not connection:
            logger.error(f"No connection exists with the app-id '{app_id}'")
            exit(1)
        connection_id = connection.connection_id
    return connection_id

def validate_params(kind: str):
    if kind != ToolkitKind.MCP:
        raise ValueError(f"Unsupported toolkit kind: {kind}")


class ToolkitController:
    def __init__(
        self,
        kind: ToolkitKind = None,
        name: str = None,
        description: str = None,
        package: str = None,
        package_root: str = None,
        language: Language = None,
        command: str = None,
    ):
        self.kind = kind
        self.name = name
        self.description = description
        self.package = package
        self.package_root = package_root
        self.language = language
        self.command = command
        self.client = None

        self.source: ToolkitSource = (
            ToolkitSource.PUBLIC_REGISTRY if package else ToolkitSource.FILES
        )

    def get_client(self) -> ToolKitClient:
        if not self.client:
            self.client = instantiate_client(ToolKitClient)
        return self.client

    def import_toolkit(self, tools: Optional[List[str]] = None, app_id: Optional[List[str]] = None):

        if app_id and isinstance(app_id, str):
            app_id = [app_id]
        elif not app_id:
            app_id = []

        validate_params(kind=self.kind)

        remapped_connections = self._remap_connections(app_id)

        client = self.get_client()
        draft_toolkits = client.get_draft_by_name(toolkit_name=self.name)
        if len(draft_toolkits) > 0:
            logger.error(f"Existing toolkit found with name '{self.name}'. Failed to create toolkit.")
            sys.exit(1)

        try:
            command_parts = json.loads(self.command)
            if not isinstance(command_parts, list):
                raise ValueError("JSON command must be a list of strings")
        except (json.JSONDecodeError, ValueError):
            command_parts = self.command.split()

        command = command_parts[0]
        args = command_parts[1:]

        console = Console()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Handle zip file or directory
            if self.package_root:
                if self.package_root.endswith(".zip") and os.path.isfile(self.package_root):
                    zip_file_path = self.package_root
                else:
                    zip_file_path = os.path.join(tmpdir, os.path.basename(f"{self.package_root.rstrip(os.sep)}.zip"))
                    with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as mcp_zip_tool_artifacts:
                        self._populate_zip(self.package_root, mcp_zip_tool_artifacts)

            # List tools if not provided
            if tools is None:
                with Progress(
                    SpinnerColumn(spinner_name="dots"),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True,
                    console=console,
                ) as progress:
                    progress.add_task(description="No tools specified, retrieving all tools from provided MCP server", total=None)
                    tools = self.get_client().list_tools(
                        zip_file_path=zip_file_path,
                        command=command,
                        args=args,
                    )
                
                tools = [
                    tool["name"] if isinstance(tool, dict) and "name" in tool else tool
                    for tool in tools
                ]

                logger.info("✅ The following tools will be imported:")
                for tool in tools:
                    console.print(f"  • {tool}")

            # Create toolkit metadata
            payload = {
                "name": self.name,
                "description": self.description,
                "mcp": {
                    "source": self.source.value,
                    "command": command,
                    "args": args,
                    "tools": tools,
                    "connections": remapped_connections,
                }
            }


            with Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
                console=console,
            ) as progress:
                progress.add_task(description="Creating toolkit...", total=None)
                toolkit = self.get_client().create_toolkit(payload)

            toolkit_id = toolkit["id"]



            # Upload zip file
            if self.package_root:
                with Progress(
                    SpinnerColumn(spinner_name="dots"),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True,
                    console=console,
                ) as progress:
                    progress.add_task(description="Uploading toolkit zip file...", total=None)
                    self.get_client().upload(toolkit_id=toolkit_id, zip_file_path=zip_file_path)

        logger.info(f"Successfully imported tool kit {self.name}")

    def _populate_zip(self, package_root: str, zipfile: zipfile.ZipFile) -> str:
        for root, _, files in os.walk(package_root):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, start=package_root)
                zipfile.write(full_path, arcname=relative_path)
        return zipfile

    def _remap_connections(self, app_ids: List[str]):
        app_id_dict = {}
        for app_id in app_ids:        
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

    
    def remove_toolkit(self, name: str):
        try:
            client = self.get_client()
            draft_toolkits = client.get_draft_by_name(toolkit_name=name)
            if len(draft_toolkits) > 1:
                logger.error(f"Multiple existing toolkits found with name '{name}'. Failed to remove toolkit")
                sys.exit(1)
            if len(draft_toolkits) > 0:
                draft_toolkit = draft_toolkits[0]
                toolkit_id = draft_toolkit.get("id")
                self.get_client().delete(toolkit_id=toolkit_id)
                logger.info(f"Successfully removed tool {name}")
            else:
                logger.warning(f"No toolkit named '{name}' found")
        except requests.HTTPError as e:
            logger.error(e.response.text)
            exit(1)

    def list_toolkits(self, verbose=False):
        client = self.get_client()
        response = client.get()
        toolkit_spec = [ToolkitSpec.model_validate(toolkit) for toolkit in response]
        toolkits = [BaseToolkit(spec=spec) for spec in toolkit_spec]

        if verbose:
            tools_list = []
            for toolkit in toolkits:
                tools_list.append(json.loads(toolkit.dumps_spec()))
            rich.print(JSON(json.dumps(tools_list, indent=4)))
        else:
            table = rich.table.Table(show_header=True, header_style="bold white", show_lines=True)
            column_args = {
                "Name": {"overflow": "fold"},
                "Kind": {},
                "Description": {},
                "Tools": {},
                "App ID": {"overflow": "fold"}
            }
            for column in column_args:
                table.add_column(column,**column_args[column])

            tools_client = instantiate_client(ToolClient)

            connections_client = get_connections_client()
            connections = connections_client.list()

            connections_dict = {conn.connection_id: conn for conn in connections}

            for toolkit in toolkits:
                tool_ids = toolkit.__toolkit_spec__.tools or []
                tool_names = []
                if len(tool_ids) == 0:
                    logger.warning("This toolkit contains no tools.")

                for tool_id in tool_ids:
                    tool = tools_client.get_draft_by_id(tool_id)
                    tool_names.append(tool["name"])

                app_ids = []
                connection_ids = toolkit.__toolkit_spec__.mcp.connections.values()

                for connection_id in connection_ids:
                    connection = connections_dict.get(connection_id)
                    if connection:
                        app_id = str(connection.app_id or connection.connection_id)
                    elif connection_id:
                        app_id = str(connection_id)
                    else:
                        app_id = ""
                    app_ids.append(app_id)



                table.add_row(
                    toolkit.__toolkit_spec__.name,
                    "MCP",
                    toolkit.__toolkit_spec__.description,
                    ", ".join(tool_names),
                    ", ".join(app_ids),
                )

            rich.print(table)