from typing import List, Dict, Optional, Union, Tuple
from enum import Enum
import json
from pydantic import BaseModel, Field, model_validator
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
import logging

logger = logging.getLogger(__name__)

class ToolkitKind(str, Enum):
    MCP = "mcp"

class ToolkitSource(str, Enum):
    FILES = "files"
    PUBLIC_REGISTRY = "public-registry"
    REMOTE = "remote" # Internal use only server does not accept

class ToolkitTransportKind(str, Enum):
    STREAMABLE_HTTP = "streamable_http"
    SSE = "sse"

class Language(str, Enum):
    NODE = "node"
    PYTHON ="python"

class BaseMcpModel(BaseModel):
    tools: Optional[List[str]] = None
    connections: Dict[str, str] | List[str] = {}

class LocalMcpModel(BaseMcpModel):
    source: ToolkitSource
    command: str
    args: List[str] = []
    package: Optional[str] = None
    package_root: Optional[str] = None

class RemoteMcpModel(BaseMcpModel):
    server_url: str
    transport: ToolkitTransportKind

McpModel = Union[LocalMcpModel, RemoteMcpModel]

class ToolkitMCPInputSpec(BaseModel):
    kind: ToolkitKind = ToolkitKind.MCP
    name: str
    description: str
    transport: Optional[ToolkitTransportKind] = None
    package: Optional[str] = None
    package_root: Optional[str] = None
    language: Optional[Language] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    tools: Optional[List[str]] = None
    connections: Optional[List[str]] = None
    source: Optional[ToolkitSource] = None

    def __parse_tool_string(tool_string: str) -> List[str]:
        if tool_string == "*": # Wildcard to use all tools for MCP    
            tool_list = ["*"] 
        elif tool_string:
            tool_list = [tool.strip() for tool in tool_string.split(",")]
        else:
            tool_list = None
        return tool_list
    
    def __infer_command(command: str, package: str, language: Language) -> str:
        if not package:
            return command
        if not command:
            if language == Language.NODE:
                command = f"npx -y {package}"
            elif language == Language.PYTHON:
                command = f"python -m {package}"
            else:
                raise BadRequest("Unable to infer start up command: 'language' must be either 'node' or 'python' when providing the 'package' option without 'command'.")
        else:
            logger.warning(f"Default package installation command for package '{package}' overridden with command '{command}'.")
        return command

    def __split_command_parts(command: str) -> Tuple[str, List[str]]:
        if not command:
                command_parts = []
        else:
            try:
                command_parts = json.loads(command)
                if not isinstance(command_parts, list):
                    raise ValueError("JSON command must be a list of strings")
            except (json.JSONDecodeError, ValueError):
                command_parts = command.split()

        if command_parts:
            command = command_parts[0]
            args = command_parts[1:]
        else:
            command = None
            args = []
        return (command, args)
    
    def __combine_command_parts(self, command: str, args: Optional[List[str]] = []) -> str:
        if not command:
            return None
        args = args or []

        return f"{command} {' '.join(args)}".strip()

    @model_validator(mode="before")
    def pre_validate_mcp(cls, values):
        tools = values.get("tools")
        if isinstance(tools, str):
            values["tools"] = cls.__parse_tool_string(tools)
        
        values["command"] = cls.__infer_command(
            values.get("command"),
            values.get("package"),
            values.get("language"),
        )
        (command, args) = cls.__split_command_parts(values.get("command"))
        values["command"] = command
        values["args"] = args or values.get("args", [])
        return values
    
    @model_validator(mode="after")
    def post_validate_mcp(self):
        if self.kind != ToolkitKind.MCP:
            raise BadRequest(f"Unsupported toolkit kind: {self.kind}")

        # Local MCP validation
        if not self.url and not self.transport:
            if not self.package and not self.package_root and not self.command:
                raise BadRequest("You must provide either 'package', 'package-root' or 'command'.")

            if self.package_root and not self.command:
                raise BadRequest("Error: 'command' must be provided when 'package-root' is specified.")
            
            if self.package_root and self.package:
                raise BadRequest("Please choose either 'package-root' or 'package' but not both.")

            if self.package_root:
                self.source = ToolkitSource.FILES
            else:
                self.source = ToolkitSource.PUBLIC_REGISTRY

        # Remote MCP Validation
        if (self.url and not self.transport) or (self.transport and not self.url):
            raise BadRequest("Both 'url' and 'transport' must be provided together for remote MCP.")

        if self.url and self.transport:
            forbidden_local_opts = []
            if self.package:
                forbidden_local_opts.append("package")
            if self.package_root:
                forbidden_local_opts.append("package-root")
            if self.language:
                forbidden_local_opts.append("language")
            if self.command:
                forbidden_local_opts.append("command")

            if forbidden_local_opts:
                raise BadRequest(
                    f"When using 'url' and 'transport' for a remote MCP, you cannot specify: {', '.join(forbidden_local_opts)}"
                )

            self.source = ToolkitSource.REMOTE
        return self
    
    def model_dump(self, export_format: bool = False, *args, **kwargs) -> str:
        content = super().model_dump(*args, **kwargs)
        if export_format and self.command:
            content["command"] = self.__combine_command_parts(self.command, self.args)
        content.pop("args", None)
        content.pop("source", None)
        return content

# Remove generate from class into controller
class ToolkitSpec(BaseModel):
    id: Optional[str] = None
    tenant_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    created_on: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
    created_by_username: Optional[str] = None
    tools: Optional[List[str]] = []
    mcp: McpModel
    
    @staticmethod
    def generate_toolkit_spec(input_spec: ToolkitMCPInputSpec) -> 'ToolkitSpec':

        if not input_spec.connections:
            input_spec.connections = {}

        mcp_config = None
        if input_spec.source == ToolkitSource.REMOTE:
            mcp_config = RemoteMcpModel(
                server_url=input_spec.url,
                transport=input_spec.transport,
                tools=input_spec.tools,
                connections=input_spec.connections
            )
        else:
            mcp_config = LocalMcpModel(
                source=input_spec.source,
                command=input_spec.command,
                args=input_spec.args,
                tools=input_spec.tools,
                connections=input_spec.connections,
                package=input_spec.package,
                package_root=input_spec.package_root
            )

        return ToolkitSpec(
            name=input_spec.name,
            description=input_spec.description,
            mcp=mcp_config
        )


class ToolkitListEntry(BaseModel):
    name: str = Field(description="The name of the Toolkit")
    description: Optional[str] = Field(description="The description of the Toolkit")
    type: str = Field(default="MCP", description="The type of Toolkit.")
    tools: Optional[List[str]] = Field(description = "A list of tool names for every tool in the Toolkit")
    app_ids: Optional[List[str]] = Field(description = "A list of connection app_ids showing every connection bound to the Toolkit")

    def get_row_details(self):
        tools = ", ".join(self.tools) if self.tools else ""
        app_ids = ", ".join(self.app_ids) if self.app_ids else ""
        return [self.name, self.description, self.type, tools, app_ids]


        
