import asyncio
import os
import typer
from typing import Iterable, List
from enum import Enum
import importlib
import sys
from pathlib import Path
import inspect
import zipfile

from ibm_watsonx_orchestrate.agent_builder.tools import BaseTool
from ibm_watsonx_orchestrate.agent_builder.tools.openapi_tool import create_openapi_json_tools_from_uri
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client

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
                print("Skill Import not implemented yet")
            case _:
                raise ValueError("Invalid kind selected")

        for tool in tools:
            yield tool

    def get_all_tools(self) -> dict:
        return {entry["name"]: entry["id"] for entry in self.get_client().get()}

    def publish_or_update_tools(self, tools: Iterable[BaseTool]) -> None:
        # Zip the tool's supporting artifacts for python tools
        tool_artifact = None
        if self.tool_kind == ToolKind.python:
            tool_artifact = "artifacts.zip"
            with zipfile.ZipFile(tool_artifact, "w", zipfile.ZIP_DEFLATED) as zip_tool_artifacts:
                file_path = Path(self.file)
                zip_tool_artifacts.write(file_path, arcname=file_path.name)

                if self.requirements_file is not None:
                    requirements_file_path = Path(self.requirements_file)
                    zip_tool_artifacts.write(requirements_file_path, arcname=requirements_file_path.name)

        existing_tools = None
        try:
            for tool in tools:
                exist = False
                tool_id = None

                if not existing_tools:
                    existing_tools = self.get_all_tools()
                if tool.__tool_spec__.name in existing_tools:
                    tool_id = tool.__tool_spec__.name
                    exist = True

                if exist:
                    self.update_tool(tool_id=tool_id, tool=tool, tool_artifact=tool_artifact)
                else:
                    self.publish_tool(tool, tool_artifact=tool_artifact)
        except Exception as e:
            raise e
        finally:
            if tool_artifact is not None and os.path.isfile(tool_artifact):
                os.remove(tool_artifact)

    def publish_tool(self, tool: BaseTool, tool_artifact: str) -> None:
        tool_spec = tool.__tool_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)

        self.get_client().create(tool_spec)

        if tool_artifact is not None:
            tool_name: str = tool_spec.get("name")
            self.get_client().upload_tools_artifact(tool_name=tool_name, file_path=tool_artifact)

        print(f"Tool '{tool.__tool_spec__.name}' imported successfully")

    def update_tool(self, tool_id: str, tool: BaseTool, tool_artifact: str) -> None:
        tool_spec = tool.__tool_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)

        print(f"Existing Tool '{tool.__tool_spec__.name}' found. Updating...")

        self.get_client().update(tool_id, tool_spec)

        if tool_artifact is not None:
            tool_name: str = tool_spec.get("name")
            self.get_client().upload_tools_artifact(tool_name=tool_name, file_path=tool_artifact)

        print(f"Tool '{tool.__tool_spec__.name}' updated successfully")
