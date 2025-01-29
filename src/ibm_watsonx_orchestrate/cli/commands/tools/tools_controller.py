import asyncio

import typer
from typing import Iterable, List
from enum import Enum
import importlib
import sys
from pathlib import Path
import inspect
from ibm_watsonx_orchestrate.agent_builder.tools import BaseTool, create_openapi_json_tools_from_uri

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

def import_python_tool(file: str) -> List[BaseTool]:
    file_path = Path(file)
    file_directory = file_path.parent
    file_name = file_path.stem
    sys.path.append(str(file_directory))
    module = importlib.import_module(file_name)
    del sys.path[-1]

    tools = []

    for _, obj in inspect.getmembers(module):
        if isinstance(obj, BaseTool) :
            tools.append(obj)

    return tools


async def import_openapi_tool(file: str, app_id: str) -> List[BaseTool]:
    tools = await create_openapi_json_tools_from_uri(file, app_id)
    return tools

class ToolsController:
    def __init__(self):
        self.client = None

    def get_client(self):
        if not self.client:
            self.client = instantiate_client(ToolClient)
        return self.client

    @staticmethod
    def import_tool(kind: ToolKind, **args) -> Iterable:
        validate_params(kind=kind, **args)
        match kind:
            case "python":
                tools = import_python_tool(file=args["file"])
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
        existing_tools = None
        for tool in tools:
            exist = False
            tool_id = None

            if not existing_tools:
                existing_tools = self.get_all_tools()
            if tool.__tool_spec__.name in existing_tools:
                tool_id = tool.__tool_spec__.name
                exist = True

            if exist:
                self.update_tool(tool_id=tool_id, tool=tool)
            else:
                self.publish_tool(tool)

    def publish_tool(self, tool: BaseTool) -> None:
        tool_spec = tool.__tool_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)

        self.get_client().create(tool_spec)

        print(f"Tool '{tool.__tool_spec__.name}' imported successfully")

    def update_tool(self, tool_id: str, tool: BaseTool) -> None:
        tool_spec = tool.__tool_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)

        print(f"Existing Tool '{tool.__tool_spec__.name}' found. Updating...")

        self.get_client().update(tool_id, tool_spec)

        print(f"Tool '{tool.__tool_spec__.name}' updated successfully")