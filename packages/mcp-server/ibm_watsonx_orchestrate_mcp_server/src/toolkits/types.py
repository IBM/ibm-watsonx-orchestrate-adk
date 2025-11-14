from ibm_watsonx_orchestrate.agent_builder.toolkits.types import Language, ToolkitKind, ToolkitTransportKind
from pydantic import BaseModel, Field
from typing import List, Optional

class AddToolKitOptions(BaseModel):
    """
    Options for importing a toolkit (MCP server) into the watsonx Orchestrate platform.
    """
    kind: ToolkitKind = Field(description="Kind of toolkit. Allowed values ['mcp']")
    name: str = Field(description="Arbitrary name to identify the toolkit. It should be unique from other toolkits")
    description: str = Field(description ="A description if the toolkit and its contents")
    package: Optional[str] = Field(default=None, description="Name of the package in the npm or pypi repository. Used when pulling the MCP server files from a public repository. Cannot be used with the 'package-root' option")
    package_root: Optional[str] = Field(default=None, description="File path to the root of the MCP Server or a zip file with the MCP Server. Used when uploading the MCP server files from the local machine. Cannot be used with the 'package'")
    language: Optional[Language] = Field(default=None, description="The language of the toolkit. Used to infer a default 'command' when using the package option (For node its 'npx -y <package>' and for python its 'python -m <package>')")
    command: Optional[str] = Field(default=None, description="Command used to start the MCP server")
    url: Optional[str] = Field(default=None, description="URL to the MCP server. Used when using a remote MCP server via transports 'streamable_http' or 'sse'")
    transport: Optional[ToolkitTransportKind] = Field(default=None, description="Used for remote MCP server. Valid options are 'streamable_http' or 'sse'. For 'stdio' leave this as null and specify either the 'package' or 'package-root' options")
    tools: Optional[List[str]] = Field(default=["*"], description="List of tools to be used with the MCP server. '[*]' means all tools on the server will be imported. Additionally, null will also cause all tools to be imported.")
    app_id: Optional[List[str]] = Field(default=None, description="List of app ids related to connections in the Orchestrate platform. For 'stdio'/local these should be key_value connections which will be exposed as env vars for the server. For remote MCP servers these will be used to authenticate requests and can be other kinds like basic or api key auth.")
