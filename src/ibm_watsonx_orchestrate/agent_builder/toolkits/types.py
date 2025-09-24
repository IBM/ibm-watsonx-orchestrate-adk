from typing import List, Dict, Optional, Union
from enum import Enum
from pydantic import BaseModel 

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
    connections: Dict[str, str]

class RemoteMcpModel(BaseModel):
    server_url: str
    transport: ToolkitTransportKind
    tools: List[str]
    connections: Dict[str, str]

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