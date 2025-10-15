from typing import List, Dict, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field

class ToolkitKind(str, Enum):
    MCP = "mcp"

class ToolkitSource(str, Enum):
    FILES = "files"
    PUBLIC_REGISTRY = "public-registry"

class ToolkitTransportKind(str, Enum):
    STREAMABLE_HTTP = "streamable_http"
    SSE = "sse"

class Language(str, Enum):
    NODE = "node"
    PYTHON ="python"

class LocalMcpModel(BaseModel):
    source: ToolkitSource
    command: str
    args: List[str]
    tools: List[str]
    connections: Dict[str, str] = {}

class RemoteMcpModel(BaseModel):
    server_url: str
    transport: ToolkitTransportKind
    tools: List[str]
    connections: Dict[str, str] = {}

McpModel = Union[LocalMcpModel, RemoteMcpModel]

class ToolkitSpec(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str]
    created_on: str
    updated_at: str
    created_by: str
    created_by_username: str
    tools: List[str] | None
    mcp: McpModel

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