import logging
import asyncio
import importlib
import inspect
import sys
import tempfile
import requests
import zipfile
from enum import Enum
from os import path
from pathlib import Path
from typing import Iterable, List
import rich

import rich.table
import typer

from ibm_watsonx_orchestrate.agent_builder.tools import BaseTool, ToolSpec
from ibm_watsonx_orchestrate.agent_builder.tools.openapi_tool import create_openapi_json_tools_from_uri
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client

logger = logging.getLogger(__name__)


class ToolKind(str, Enum):
    openapi = "openapi"
    python = "python"
    # skill = "skill"

def validate_params(kind: ToolKind, **args) -> None:
    if kind != 'openapi' and args.get('app_id') is not None:
        raise typer.BadParameter(
            "--app_id parameter can only be used with openapi tools"
        )

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

def import_python_tool(file: str, requirements_file: str = None) -> None:
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
            tools.append(obj)
    
    return tools

async def import_openapi_tool(file: str, app_id: str) -> List[BaseTool]:
    tools = await create_openapi_json_tools_from_uri(file, app_id)
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
        validate_params(kind=kind, **args)

        match kind:
            case "python":
                tools = import_python_tool(file=args["file"], requirements_file=args["requirements_file"])
            case "openapi":
                tools = asyncio.run(import_openapi_tool(file=args["file"], app_id=args.get('app_id')))
            case "skill":
                tools = []
                logger.warning("Skill Import not implemented yet")
            case _:
                raise ValueError("Invalid kind selected")

        for tool in tools:
            yield tool
    
    def list_tools(self, verbose=False):
        response = self.get_client().get()
        tool_specs = [ToolSpec.model_validate(tool) for tool in response]
        tools = [BaseTool(spec=spec) for spec in tool_specs]

        if verbose:
            for tool in tools:
                rich.print(tool.dumps_spec())
        else:
            table = rich.table.Table(show_header=True, header_style="bold white", show_lines=True)
            columns = ["Name", "Description", "Permission", "Type"]
            for column in columns:
                table.add_column(column)
            
            for tool in tools:
                tool_binding = tool.__tool_spec__.binding
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
                )

            rich.print(table)

    def get_all_tools(self) -> dict:
        return {entry["name"]: entry["id"] for entry in self.get_client().get()}

    def publish_or_update_tools(self, tools: Iterable[BaseTool]) -> None:
        # Zip the tool's supporting artifacts for python tools
        with tempfile.TemporaryDirectory() as tmpdir:
            existing_tools = None
            for tool in tools:
                exist = False
                tool_id = None

                if not existing_tools:
                    existing_tools = self.get_all_tools()
                if tool.__tool_spec__.name in existing_tools:
                    tool_id = tool.__tool_spec__.name
                    exist = True

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
                        requirements.append('/packages/ibm_watsonx_orchestrate-0.1.0-py3-none-any.whl\n')
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

        self.get_client().create(tool_spec)

        if tool_artifact is not None:
            tool_name: str = tool_spec.get("name")
            self.get_client().upload_tools_artifact(tool_name=tool_name, file_path=tool_artifact)

        logger.info(f"Tool '{tool.__tool_spec__.name}' imported successfully")

    def update_tool(self, tool_id: str, tool: BaseTool, tool_artifact: str) -> None:
        tool_spec = tool.__tool_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)

        logger.info(f"Existing Tool '{tool.__tool_spec__.name}' found. Updating...")

        self.get_client().update(tool_id, tool_spec)

        if tool_artifact is not None:
            tool_name: str = tool_spec.get("name")
            self.get_client().upload_tools_artifact(tool_name=tool_name, file_path=tool_artifact)

        logger.info(f"Tool '{tool.__tool_spec__.name}' updated successfully")
    
    def remove_tool(self, name: str):
        try:
            self.get_client().delete(agent_id=name)
            logger.info(f"Successfully removed tool {name}")
        except requests.HTTPError as e:
            logger.error(e.response.text)
            exit(1)
