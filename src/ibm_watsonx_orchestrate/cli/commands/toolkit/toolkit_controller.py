import os
import zipfile
import tempfile
from typing import List, Optional, Any, Tuple
from pydantic import BaseModel
import logging
import sys
import re
import requests
from ibm_watsonx_orchestrate.client.toolkit.toolkit_client import ToolKitClient
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit import BaseToolkit, ToolkitSpec
from ibm_watsonx_orchestrate.agent_builder.toolkits.types import ToolkitKind, Language, ToolkitSource, ToolkitTransportKind, ToolkitListEntry
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.utils import sanitize_app_id
from ibm_watsonx_orchestrate.client.connections import get_connections_client
import typer
import json
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from ibm_watsonx_orchestrate.cli.common import ListFormats, rich_table_to_markdown
from rich.json import JSON
import rich
import rich.table
import json

logger = logging.getLogger(__name__)

def get_connection_id(app_id: str, is_local_mcp: bool) -> str:
    connections_client = get_connections_client()
    existing_draft_configuration = connections_client.get_config(app_id=app_id, env='draft')
    existing_live_configuration = connections_client.get_config(app_id=app_id, env='live')

    for config in [existing_draft_configuration, existing_live_configuration]:
        if is_local_mcp is True:
            if config and config.security_scheme != 'key_value_creds':
                logger.error("Only key_value credentials are currently supported for local MCP")
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
        url: str = None,
        transport: ToolkitTransportKind = None
    ):
        self.kind = kind
        self.name = name
        self.description = description
        self.package = package
        self.package_root = package_root
        self.language = language
        self.command = command
        self.client = None
        self.url = url
        self.transport = transport

        self.source: ToolkitSource = (
            ToolkitSource.FILES if package_root else ToolkitSource.PUBLIC_REGISTRY
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

        if not self.command:
            command_parts = []
        else:
            try:
                command_parts = json.loads(self.command)
                if not isinstance(command_parts, list):
                    raise ValueError("JSON command must be a list of strings")
            except (json.JSONDecodeError, ValueError):
                command_parts = self.command.split()

        if command_parts:
            command = command_parts[0]
            args = command_parts[1:]
        else:
            command = None
            args = []


        if self.package_root:
            is_folder = os.path.isdir(self.package_root)
            is_zip_file = os.path.isfile(self.package_root) and zipfile.is_zipfile(self.package_root)

            if not is_folder and not is_zip_file:
                logger.error(f"Unable to find a valid directory or zip file at location '{self.package_root}'")
                sys.exit(1)

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
            payload = {}

            if self.transport is not None and self.url is not None:
                payload = {
                    "name": self.name,
                    "description": self.description,
                    "mcp": {
                        "server_url": self.url,
                        "transport": self.transport.value,
                        "tools": tools,
                        "connections": remapped_connections,
                    }
                }
            else:
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

            runtime_id = sanitize_app_id(runtime_id)
            is_local_mcp = self.package is not None or self.package_root is not None
            app_id_dict[runtime_id] = get_connection_id(local_id, is_local_mcp)

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
    
    def _lookup_toolkit_resource_value(
            self,
            toolkit: BaseToolkit, 
            lookup_table: dict[str, str], 
            target_attr: str,
            target_attr_display_name: str
        ) -> List[str] | str | None:
        """
        Using a lookup table convert all the strings in a given field of an agent into their equivalent in the lookup table
        Example: lookup_table={1: obj1, 2: obj2} agent=Toolkit(tools=[1,2]) return. [obj1, obj2]

        Args:
            toolkit: A toolkit
            lookup_table: A dictionary that maps one value to another
            target_attr: The field to convert on the provided agent
            target_attr_display_name: The name of the field to be displayed in the event of an error
        """
        attr_value = getattr(toolkit, target_attr, None)
        if not attr_value:
            return
        
        if isinstance(attr_value, list):
            new_resource_list=[]
            for value in attr_value:
                if value in lookup_table:
                    new_resource_list.append(lookup_table[value])
                else:
                    logger.warning(f"{target_attr_display_name} with ID '{value}' not found. Returning {target_attr_display_name} ID")
                    new_resource_list.append(value)
            return new_resource_list
        else:
            if attr_value in lookup_table:
                return lookup_table[attr_value]
            else:
                logger.warning(f"{target_attr_display_name} with ID '{attr_value}' not found. Returning {target_attr_display_name} ID")
                return attr_value

    def _construct_lut_toolkit_resource(self, resource_list: List[dict], key_attr: str, value_attr) -> dict:
        """
            Given a list of dictionaries build a key -> value look up table
            Example [{id: 1, name: obj1}, {id: 2, name: obj2}] return {1: obj1, 2: obj2}

            Args:
                resource_list: A list of dictionries from which to build the lookup table from
                key_attr: The name of the field whose value will form the key of the lookup table
                value_attrL The name of the field whose value will form the value of the lookup table

            Returns:
                A lookup table
        """
        lut = {}
        for resource in resource_list:
            if isinstance(resource, BaseModel):
                resource = resource.model_dump()
            lut[resource.get(key_attr, None)] = resource.get(value_attr, None)
        return lut
    
    def _batch_request_resource(self, client_fn, ids, batch_size=50) -> List[dict]:
        resources = []
        for i in range(0, len(ids), batch_size):
                chunk = ids[i:i + batch_size]
                resources += (client_fn(chunk))
        return resources

    def _get_all_unique_toolkit_resources(self, toolkits: List[BaseToolkit], target_attr: str) -> List[str]:
        """
            Given a list of toolkits get all the unique values of a certain field
            Example: tk1.tools = [1 ,2 ,3] and tk2.tools = [2, 4, 5] then return [1, 2, 3, 4, 5]
            Example: tk1.id = "123" and tk2.id = "456" then return ["123", "456"]

            Args:
                toolkits: List of toolkits
                target_attr: The name of the field to access and get unique elements

            Returns:
                A list of unique elements from across all toolkits
        """
        all_ids = set()
        for toolkit in toolkits:
            attr_value = getattr(toolkit, target_attr, None)
            if attr_value:
                if isinstance(attr_value, list):
                    all_ids.update(attr_value)
                else:
                    all_ids.add(attr_value)
        return list(all_ids)
    
    def _bulk_resolve_toolkit_tools(self, toolkits: List[BaseToolkit]) -> List[BaseToolkit]:
        new_toolkit_specs = [tk.__toolkit_spec__ for tk in toolkits].copy()
        all_tools_ids = self._get_all_unique_toolkit_resources(new_toolkit_specs, "tools")
        if not all_tools_ids:
            return toolkits
        
        tool_client = instantiate_client(ToolClient)
        
        all_tools = self._batch_request_resource(tool_client.get_drafts_by_ids, all_tools_ids)

        tool_lut = self._construct_lut_toolkit_resource(all_tools, "id", "name")
        
        new_toolkits = []
        for toolkit_spec in new_toolkit_specs:
            tool_names = self._lookup_toolkit_resource_value(toolkit_spec, tool_lut, "tools", "Tool")
            if tool_names:
                toolkit_spec.tools = tool_names
            new_toolkits.append(BaseToolkit(toolkit_spec))
        return new_toolkits
    
    def _fetch_and_parse_toolkits(self) -> Tuple[List[BaseToolkit], List[List[str]]]:
        parse_errors = []
        client = self.get_client()
        response = client.get()

        toolkits = []
        for toolkit in response:
            try:
                spec = ToolkitSpec.model_validate(toolkit)
                toolkits.append(BaseToolkit(spec=spec))
            except Exception as e:
                name = toolkit.get('name', None)
                parse_errors.append([
                    f"Toolkit '{name}' could not be parsed",
                    json.dumps(toolkit),
                    e
                ])
        return (toolkits, parse_errors)

    def _log_parse_errors(self, parse_errors: List[List[str]]) -> None:
        for error in parse_errors:
                for l in error:
                    logger.error(l)

    def list_toolkits(self, verbose=False, format: ListFormats| None = None) -> List[dict[str, Any]] | List[ToolkitListEntry] | str | None:
        if verbose and format:
            logger.error("For toolkits list, `--verbose` and `--format` are mutually exclusive options")
            sys.exit(1)
        
        toolkits, parse_errors = self._fetch_and_parse_toolkits()

        if verbose:
            tools_list = []
            for toolkit in toolkits:
                tools_list.append(json.loads(toolkit.dumps_spec()))
            rich.print(JSON(json.dumps(tools_list, indent=4)))
            self._log_parse_errors(parse_errors)
            return tools_list
        else:
            toolkit_details = []

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

            connections_client = get_connections_client()
            connections = connections_client.list()

            connections_dict = {conn.connection_id: conn for conn in connections}

            resolved_toolkits = self._bulk_resolve_toolkit_tools(toolkits)

            for toolkit in resolved_toolkits:
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
                
                entry = ToolkitListEntry(
                    name = toolkit.__toolkit_spec__.name,
                    description = toolkit.__toolkit_spec__.description,
                    tools = toolkit.__toolkit_spec__.tools,
                    app_ids = app_ids
                )
                if format == ListFormats.JSON:
                    toolkit_details.append(entry)
                else:
                    table.add_row(*entry.get_row_details())
            
            response = None
            match format:
                case ListFormats.JSON:
                    response = toolkit_details
                case ListFormats.Table:
                    response = rich_table_to_markdown(table)
                case _:
                    rich.print(table)
            
            self._log_parse_errors(parse_errors)
            
            return response