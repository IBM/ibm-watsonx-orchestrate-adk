import os
import zipfile
import tempfile
import shutil
from typing import List, Optional, Any, Tuple, Dict
from pydantic import BaseModel
from io import BytesIO
import logging
import sys
import re
import requests
from ibm_watsonx_orchestrate.agent_builder.tools.utils import extract_python_tools,get_formated_requirements_lines, get_package_root
from ibm_watsonx_orchestrate.client.toolkit.toolkit_client import ToolKitClient
from ibm_watsonx_orchestrate_clients.common.base_client import ClientAPIException
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit import BaseToolkit, ToolkitSpec
from ibm_watsonx_orchestrate.agent_builder.toolkits.types import ToolkitKind, Language, ToolkitTransportKind, ToolkitListEntry, ToolkitMCPInputSpec, ToolkitPythonInputSpec, ToolkitDeploymentTiers, RemoteMcpModel, LocalMcpModel, ToolkitSource, PythonModel, ToolkitPythonTool, validate_context
from ibm_watsonx_orchestrate_core.types.spec.types import SpecVersion
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.utils import sanitize_app_id, check_file_in_zip
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.client.connections import get_connections_client
from ibm_watsonx_orchestrate.cli.commands.connections.connections_controller import export_connection
from ibm_watsonx_orchestrate.agent_builder.tools.base_tool import BaseTool
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.agent_builder.toolkits.utils import extract_python_toolkit_tools_from_folder
import typer
import json
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from ibm_watsonx_orchestrate.cli.common import ListFormats, rich_table_to_markdown
from rich.json import JSON
from pathlib import Path
import rich
import rich.table
import json
import yaml
import io

logger = logging.getLogger(__name__)

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

def get_app_ids(conn_ids: List[str]) -> List[str]:
    connections_client = get_connections_client()
    connections = connections_client.get_drafts_by_ids(conn_ids)
    return [conn.app_id for conn in connections]

class ToolkitController:
    client=None

    def get_client(self) -> ToolKitClient:
        if not self.client:
            self.client = instantiate_client(ToolKitClient)
        return self.client
    
    def __resolve_package_root_path(self, package_root: Path | str, file: Path | str) -> str:
        package_root = Path(package_root)

        if package_root.is_absolute():
            return str(package_root)

        file = Path(file)
        folder = file.parent

        return str(folder / package_root)
    
    def __extract_python_tools_from_folder(self, folder_path: Path, app_ids: Optional[List[str]] = None) -> List[BaseTool]:
            tools = extract_python_toolkit_tools_from_folder(folder_path=folder_path, app_ids=app_ids)
            toolkit_tools = [ToolkitPythonTool.create_from_base_tool_spec(tool) for tool in tools]
            return toolkit_tools

    
    def import_toolkit(self, file: Path | str, app_id: Optional[List[str] | str] = None, allowed_context: Optional[List[str]] = None) -> List[BaseToolkit]:
        file = Path(file)

        if not file.exists():
                raise FileNotFoundError(f"{file} does not exist")
        toolkits: List[BaseToolkit] = []
        if file.suffix == ".py":
            toolkits += BaseToolkit.from_python(file)
        else:
            toolkits.append(BaseToolkit.from_spec(file))
        
        if app_id and isinstance(app_id, str):
                app_id = [app_id]


        for toolkit in toolkits:
            kind = self.__get_kind_from_spec(toolkit.__toolkit_spec__)
            config = self.__get_toolkit_config_from_spec(toolkit.__toolkit_spec__, kind)

            if app_id:
                config.connections = app_id
            if allowed_context and isinstance(config, RemoteMcpModel):
                # Validate allowed_context values for remote mcp server
                validate_context(allowed_context)
                toolkit.__toolkit_spec__.mcp.metadata = {"allowed_context": allowed_context}
            if isinstance(config, LocalMcpModel) and config.package_root:
                config.package_root = self.__resolve_package_root_path(config.package_root, file)
            if isinstance(config, PythonModel) :
                config.package_root = self.__resolve_package_root_path(config.package_root, file)
                if not config.tools:
                    tools = extract_python_toolkit_tools_from_folder(folder_path=config.package_root, app_ids=app_id)
                    python_toolkit_tools = [ToolkitPythonTool.create_from_base_tool_spec(tool) for tool in tools]
                    config.tools =[tool.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True) for tool in python_toolkit_tools]

        return toolkits


    def create_toolkit(
        self,
        kind: ToolkitKind,
        name: str,
        description: str,
        transport: Optional[ToolkitTransportKind] = None,
        package: Optional[str] = None,
        package_root: Optional[str] = None,
        language: Optional[Language] = None,
        command: Optional[str] = None,
        url: Optional[str] = None,
        tools: Optional[str] = None,
        app_id: Optional[List[str] | str] = None,
        allowed_context: Optional[List[str]] = None,
        tier: Optional[ToolkitDeploymentTiers] = None
    ) -> BaseToolkit:

        if app_id and isinstance(app_id, str):
            app_id = [app_id]
        
        match kind:
            case ToolkitKind.MCP:
                toolkit_input = ToolkitMCPInputSpec(
                    kind=kind,
                    name=name,
                    description=description,
                    transport=transport,
                    package=package,
                    package_root=package_root,
                    language=language,
                    command=command,
                    url=url,
                    tools=tools,
                    connections=app_id,
                    allowed_context=allowed_context
                )
            case ToolkitKind.PYTHON:
                python_tool_bundle_path = Path(package_root)
                python_tools = self.__extract_python_tools_from_folder(folder_path=python_tool_bundle_path, app_ids=app_id)
                toolkit_input = ToolkitPythonInputSpec(
                    kind=kind,
                    name=name,
                    description=description,
                    connections=app_id,
                    deployment_tier=tier,
                    tools=python_tools,
                    package_root=package_root,
                )
            case _:
                raise BadRequest(f"Unexpected toolkit kind '{kind}'. Failed to import")

        toolkit_spec = ToolkitSpec.generate_toolkit_spec(toolkit_input)

        return BaseToolkit(spec=toolkit_spec)
    
    def __get_kind_from_spec(self, spec: ToolkitSpec) -> ToolkitKind:
        if spec.mcp:
            return ToolkitKind.MCP
        if spec.python:
            return ToolkitKind.PYTHON
    
    def __get_toolkit_config_from_spec(self, spec: ToolkitSpec, kind: ToolkitKind) -> LocalMcpModel | RemoteMcpModel | PythonModel:
        match kind:
            case ToolkitKind.MCP:
                return spec.mcp
            case ToolkitKind.PYTHON:
                return spec.python
            case _:
                raise ValueError(f"Unrecoginsed toolkit kind '{kind}'")
    
    def publish_or_update_toolkits(self, toolkits: List[BaseToolkit]) -> None:
        for toolkit in toolkits:
            spec = toolkit.__toolkit_spec__

            client = self.get_client()
            draft_toolkits = client.get_draft_by_name(toolkit_name=spec.name)
            if len(draft_toolkits) > 0:
                logger.error(f"Existing toolkit found with name '{spec.name}'. Failed to create toolkit.")
                sys.exit(1)
            
            kind = self.__get_kind_from_spec(spec)
            toolkit_config = self.__get_toolkit_config_from_spec(spec, kind)
            
            if isinstance(toolkit_config.connections, List):
                toolkit_config.connections = self.__remap_connections(toolkit_config.connections)
            
            package_root = getattr(toolkit_config, "package_root", None)
            if package_root:
                is_folder = os.path.isdir(package_root)
                is_zip_file = os.path.isfile(package_root) and zipfile.is_zipfile(package_root)

                if not is_folder and not is_zip_file:
                    logger.error(f"Unable to find a valid directory or zip file at location '{package_root}'")
                    sys.exit(1)

            console = Console()

            with tempfile.TemporaryDirectory() as tmpdir:
                # Handle zip file or directory
                if package_root:
                    if package_root.endswith(".zip") and os.path.isfile(package_root):
                        zip_file_path = package_root
                    else:
                        zip_file_path = os.path.join(tmpdir, os.path.basename(f"{package_root.rstrip(os.sep)}.zip"))
                        with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as mcp_zip_tool_artifacts:
                            self._populate_zip(package_root, mcp_zip_tool_artifacts)

                    # List tools if not provided
                    if kind == ToolkitKind.MCP:
                        if spec.mcp.tools is None:
                            with Progress(
                                SpinnerColumn(spinner_name="dots"),
                                TextColumn("[progress.description]{task.description}"),
                                transient=True,
                                console=console,
                            ) as progress:
                                progress.add_task(description="No tools specified, retrieving all tools from provided MCP server", total=None)
                                tools = self.get_client().list_tools(
                                    zip_file_path=zip_file_path,
                                    command=getattr(toolkit_config, "command", None),
                                    args=getattr(toolkit_config, "args", []),
                                )
                            
                            spec.mcp.tools = [
                                tool["name"] if isinstance(tool, dict) and "name" in tool else tool
                                for tool in tools
                            ]

                            logger.info("✅ The following tools will be imported:")
                            for tool in spec.mcp.tools:
                                console.print(f"  • {tool}")
                        elif spec.mcp.tools is None:
                            logger.info("No tools specified, retrieving all tools from provided MCP server")
                            spec.mcp.tools = ['*']
                    elif kind == ToolkitKind.PYTHON:
                        with tempfile.TemporaryDirectory() as tmpdir, \
                        zipfile.ZipFile(zip_file_path, "a", zipfile.ZIP_DEFLATED) as zip_tool_artifacts:
                            
                            requirements_file = os.path.join(package_root, 'requirements.txt')
                            requirements_lines = get_formated_requirements_lines(requirements_file)
                            
                            temp_requirements_file = os.path.join(tmpdir, 'requirements.txt')


                            with safe_open(temp_requirements_file, 'w') as fp:
                                fp.writelines(requirements_lines)
                            zip_tool_artifacts.write(temp_requirements_file, arcname='requirements.txt')
                            zip_tool_artifacts.writestr("bundle-format", "2.0.0\n")


                # Create toolkit metadata
                payload = spec.model_dump(exclude_unset=True)


                try:
                    with Progress(
                        SpinnerColumn(spinner_name="dots"),
                        TextColumn("[progress.description]{task.description}"),
                        transient=True,
                        console=console,
                    ) as progress:
                        progress.add_task(description="Creating toolkit...", total=None)
                        new_toolkit = self.get_client().create_toolkit(payload)
                except ClientAPIException as e:
                    error_msg = "Unknown error"
                    try:
                        # Don't rely on truthiness of response object - check if it's not None
                        if e.response is not None and hasattr(e.response, 'text'):
                            response_text = e.response.text
                            if response_text:
                                try:
                                    error_data = json.loads(response_text)
                                    error_msg = error_data.get('detail', response_text)
                                except:
                                    error_msg = response_text
                            else:
                                error_msg = str(e)
                        else:
                            error_msg = str(e)
                    except Exception:
                        error_msg = str(e)
                    
                    logger.error(f"Failed to create toolkit: {error_msg}")
                    sys.exit(1)

                toolkit_id = new_toolkit["id"]

                # Upload zip file
                if package_root:
                    with Progress(
                        SpinnerColumn(spinner_name="dots"),
                        TextColumn("[progress.description]{task.description}"),
                        transient=True,
                        console=console,
                    ) as progress:
                        progress.add_task(description="Uploading toolkit zip file...", total=None)
                        self.get_client().upload(toolkit_id=toolkit_id, zip_file_path=zip_file_path)

            logger.info(f"Successfully imported tool kit {spec.name}")

    def _populate_zip(self, package_root: str, zipfile: zipfile.ZipFile, location: Optional[str] = None, ignore: List[str] = []) -> str:
        for root, _, files in os.walk(package_root):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, start=package_root)
                if relative_path in ignore:
                    continue
                if location:
                    relative_path = os.path.join(location, relative_path)
                zipfile.write(full_path, arcname=relative_path)
        return zipfile

    def __remap_connections(self, app_ids: List[str]) -> Dict[str, str]:
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
                raise typer.BadParameter(f"The provided app-id '{app_id}' is not valid. This is likely caused by having mutliple equal signs, please use '\\=' to represent a literal '=' character")

            if not len(runtime_id.strip()) or not len(local_id.strip()):
                raise typer.BadParameter(f"The provided app-id '{app_id}' is not valid. app-id cannot be empty or whitespace")

            runtime_id = sanitize_app_id(runtime_id)
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
    
    def _fetch_and_parse_toolkits(self, workspace_id: Optional[str] = None) -> Tuple[List[BaseToolkit], List[List[str]]]:
        parse_errors = []
        client = self.get_client()
        
        # Use client method directly - it handles workspace_id parameter properly
        response = client.get(workspace_id=workspace_id)

        toolkits = []
        for toolkit in (response or []):
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
                "Description": {},
                "Kind": {},
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
                toolkit_kind = self.__get_kind_from_spec(toolkit.__toolkit_spec__)
                toolkit_config = self.__get_toolkit_config_from_spec(toolkit.__toolkit_spec__, toolkit_kind)
                connection_ids = toolkit_config.connections.values()

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
                    type = toolkit_kind,
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
    
    def __convert_mcp_spec_to_input_spec(self, spec: ToolkitSpec, connections: Optional[List[str]] = None, package_root: Optional[str] = None) -> ToolkitMCPInputSpec:
        input_spec_details = {
            "name": spec.name,
            "description": spec.description,
            "tools": spec.mcp.tools,
            "connections": connections
        }

        mcp_details = {}
        if isinstance(spec.mcp, RemoteMcpModel):
            mcp_details = {
                "url": spec.mcp.server_url,
                "transport": spec.mcp.transport
            }
        else:
            mcp_details = {
                "command": spec.mcp.command,
                "args": spec.mcp.args
            }
        
            if spec.mcp.source == ToolkitSource.FILES:
                mcp_details["package_root"] = package_root
        
        input_spec_details.update(mcp_details)

        return ToolkitMCPInputSpec.model_validate(input_spec_details)

    def __convert_python_spec_to_input_spec(self, spec: ToolkitSpec, connections: Optional[List[str]] = None, package_root: Optional[str] = None) -> ToolkitPythonInputSpec:
        input_spec_details = {
            "name": spec.name,
            "description": spec.description,
            "connections": connections,
            "python_version": spec.python.python_version,
            "environment": spec.python.env,
            "package_root": package_root
        }


        return ToolkitPythonInputSpec.model_validate(input_spec_details)
        

    def __convert_spec_to_input_spec(self, spec: ToolkitSpec, connections: Optional[List[str]] = None, package_root: Optional[str] = None, kind: ToolkitKind = ToolkitKind.MCP) -> ToolkitMCPInputSpec | ToolkitPythonInputSpec:
        match kind:
            case ToolkitKind.MCP:
                return self.__convert_mcp_spec_to_input_spec(spec=spec, connections=connections, package_root=package_root)
            case ToolkitKind.PYTHON:
                return self.__convert_python_spec_to_input_spec(spec=spec, connections=connections, package_root=package_root)

    
    def export_toolkit(
            self,
            name: str,
            output_file: Path | str,
            zip_file_out: Optional[zipfile.ZipFile] = None,
            connections_output_path: Path | str = "/connections",
            workspace_id: Optional[str] = None) -> None:
        
        output_file = Path(output_file)
        connections_output_path = Path(connections_output_path)

        output_file_extension = output_file.suffix
        if not zip_file_out and  output_file_extension != ".zip":
            BadRequest(f"Output file must end with the extension '.zip'. Provided file '{output_file}' ends with '{output_file_extension}'")
        
        logger.info(f"Exporting toolkit '{name}' to '{output_file}'")

        client = self.get_client()

        toolkit_specs = client.get_draft_by_name(toolkit_name=name, workspace_id=workspace_id)

        if not toolkit_specs:
            error_msg = f"No toolkit named '{name}' found. Please ensure the toolkit exists `orchestrate toolkits list`"
            logger.warning(error_msg)
            return  # Return early instead of raising exception - exporting of workspaces stops otherwise
        
        if len(toolkit_specs) > 1:
            error_msg = f"Multiple toolkits named '{name}' found. Unable to export due to ambiguity"
            logger.warning(error_msg)
            return  # Return early instead of raising exception - exporting of workspaces stops otherwise
        
        toolkit_spec = toolkit_specs[0]

        toolkit = BaseToolkit(spec=ToolkitSpec.model_validate(toolkit_spec))
        spec = toolkit.__toolkit_spec__

        kind = self.__get_kind_from_spec(spec)
        config = self.__get_toolkit_config_from_spec(spec, kind)

        package_root = name
        app_ids = [] if not config.connections else get_app_ids(config.connections.values())
        toolkit_input_spec = self.__convert_spec_to_input_spec(spec, app_ids, package_root, kind)

        content = toolkit_input_spec.model_dump(export_format=True, mode="json", exclude_none=True)
        content["spec_version"] = SpecVersion.V1.value

        zip_file_root_folder = Path()
        if zip_file_out:
            zip_file_root_folder = output_file
        else:
            zip_file_out = zipfile.ZipFile(output_file, "w")
        
        # Don't export if its already done
        if check_file_in_zip(str(zip_file_root_folder / f"{name}.yaml"), zip_file_out):
            return

        toolkit_spec_yaml = yaml.dump(content, sort_keys=False, default_flow_style=False, allow_unicode=True)
        toolkit_spec_yaml_bytes = toolkit_spec_yaml.encode("utf-8")
        toolkit_spec_yaml_file = io.BytesIO(toolkit_spec_yaml_bytes)

        zip_file_out.writestr(str(zip_file_root_folder /f"{name}.yaml"), toolkit_spec_yaml_file.getvalue())
        
        for app_id in app_ids:
            export_connection(output_file=connections_output_path, app_id=app_id, zip_file_out=zip_file_out)

        # Export supporting artifacts
        if (kind == ToolkitKind.PYTHON or toolkit_spec.get("mcp", {}).get("source") == ToolkitSource.FILES) and toolkit.__toolkit_spec__.id is not None:
            toolkit_artifact_bytes = None
            try:
                downloaded_bytes = client.download_artifact(toolkit.__toolkit_spec__.id)
                if downloaded_bytes is not None:
                    toolkit_artifact_bytes = downloaded_bytes
                else:
                    logger.warning(f"No artifacts found for toolkit '{name}'")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code != 404:
                    raise e
                else:
                    BadRequest(f"Could not find toolkit artifacts for toolkit '{name}'")
            except Exception as e:
                logger.warning(f"Error downloading artifacts for toolkit '{name}': {str(e)}")

            if toolkit_artifact_bytes:
                with zipfile.ZipFile(io.BytesIO(toolkit_artifact_bytes), "r") as zip_file_in:
          
                    for item in zip_file_in.infolist():
                        buffer = zip_file_in.read(item.filename)
                        if item.filename.startswith("node_modules/"):
                            continue
                        zip_file_out.writestr(str(zip_file_root_folder/ Path(package_root) / Path(item.filename)), buffer)
                
        logger.info(f"Successfully exported toolkit '{name}' to '{output_file}'")