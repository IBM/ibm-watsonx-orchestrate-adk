from typing import List, Dict, Optional
from enum import Enum
from pydantic import BaseModel, model_validator

class ToolkitKind(str, Enum):
    MCP = "mcp"

class Language(str, Enum):
    NODE = "node"
    PYTHON ="python"

class ToolkitSource(str, Enum):
    FILES = "files"
    PUBLIC_REGISTRY = "public-registry"



class McpModel(BaseModel):
    source: str
    command: str
    args: List[str]
    tools: List[str]
    connections: Dict[str, str]


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

    @model_validator(mode='after')
    def validate_tools_and_mcp(self) -> 'ToolkitSpec':
        if self.mcp.source not in {"files", "public-registry"}:
            raise ValueError("MCP source must be either 'files' or 'public-registry'.")
        return self
