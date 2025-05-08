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
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.utils import sanatize_app_id
from ibm_watsonx_orchestrate.client.connections import get_connections_client
import typer
import json
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from ibm_watsonx_orchestrate.client.utils import is_local_dev

logger = logging.getLogger(__name__)

class ToolkitKind(str, Enum):
    MCP = "mcp"

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
        package_root: str  = None,
        command: str  = None,
    ):
        self.kind = kind
        self.name = name
        self.description = description
        self.package_root = package_root
        self.command = command
        self.client = None

    def get_client(self) -> ToolKitClient:
        if not self.client:
            self.client = instantiate_client(ToolKitClient)
        return self.client

    def import_toolkit(self, tools: Optional[List[str]] = None, app_id: Optional[List[str]] = None):
        if not is_local_dev():
            logger.error("This functionality is only available for Local Environments")
            sys.exit(1)

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

        with tempfile.TemporaryDirectory() as tmpdir:
            # Handle zip file or directory
            if self.package_root.endswith(".zip") and os.path.isfile(self.package_root):
                zip_file_path = self.package_root
            else:
                zip_file_path = os.path.join(tmpdir, os.path.basename(f"{self.package_root.rstrip(os.sep)}.zip"))
                with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as mcp_zip_tool_artifacts:
                    self._populate_zip(self.package_root, mcp_zip_tool_artifacts)

            try:
                command_parts = json.loads(self.command)
                if not isinstance(command_parts, list):
                    raise ValueError("JSON command must be a list of strings")
            except (json.JSONDecodeError, ValueError):
                command_parts = self.command.split()

            command = command_parts[0]
            args = command_parts[1:]

            console = Console()
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
                # Normalize tools to a list of tool names
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
                    "source": "files",
                    "command": command,
                    "args": args,
                    "tools": tools,
                    "connections": remapped_connections,
                }
            }
            toolkit = self.get_client().create_toolkit(payload)
            toolkit_id = toolkit["id"]

            console = Console()
            # Upload zip file
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
        if not is_local_dev():
            logger.error("This functionality is only available for Local Environments")
            sys.exit(1)
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