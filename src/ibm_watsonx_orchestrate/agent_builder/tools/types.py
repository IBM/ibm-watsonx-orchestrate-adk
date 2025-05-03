from enum import Enum
from typing import List, Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, model_validator, ConfigDict, Field, AliasChoices


class ToolPermission(str, Enum):
    READ_ONLY = 'read_only'
    WRITE_ONLY = 'write_only'
    READ_WRITE = 'read_write'
    ADMIN = 'admin'


class JsonSchemaObject(BaseModel):
    model_config = ConfigDict(extra='allow')

    type: Optional[Union[Literal['object', 'string', 'number', 'integer', 'boolean', 'array', 'null'], List[Literal['object', 'string', 'number', 'integer', 'boolean', 'array', 'null']]]] = None
    title: str | None = None
    description: str | None = None
    properties: Optional[Dict[str, 'JsonSchemaObject']] = None
    required: Optional[List[str]] = None
    items: Optional['JsonSchemaObject'] = None
    uniqueItems: bool | None = None
    default: Any | None = None
    enum: List[Any] | None = None
    minimum: float | None = None
    maximum: float | None = None
    minLength: int | None = None
    maxLength: int | None = None
    format: str | None = None
    pattern: str | None = None
    anyOf: Optional[List['JsonSchemaObject']] = None
    in_field: Optional[Literal['query', 'header', 'path', 'body']] = Field(None, alias='in')
    aliasName: str | None = None
    "Runtime feature where the sdk can provide the original name of a field before prefixing"

    @model_validator(mode='after')
    def normalize_type_field(self) -> 'JsonSchemaObject':
        if isinstance(self.type, list):
            self.type = self.type[0]
        return self


class ToolRequestBody(BaseModel):
    model_config = ConfigDict(extra='allow')

    type: Literal['object']
    properties: Dict[str, JsonSchemaObject]
    required: Optional[List[str]] = None


class ToolResponseBody(BaseModel):
    model_config = ConfigDict(extra='allow')

    type: Literal['object', 'string', 'number', 'integer', 'boolean', 'array','null'] = None
    description: str = None
    properties: Dict[str, JsonSchemaObject] = None
    items: JsonSchemaObject = None
    uniqueItems: bool = None
    anyOf: List['JsonSchemaObject'] = None
    required: Optional[List[str]] = None

class OpenApiSecurityScheme(BaseModel):
    type: Literal['apiKey', 'http', 'oauth2', 'openIdConnect']
    scheme: Optional[Literal['basic', 'bearer', 'oauth']] = None
    in_field: Optional[Literal['query', 'header', 'cookie']] = Field(None, validation_alias=AliasChoices('in', 'in_field'), serialization_alias='in')
    name: str | None = None
    open_id_connect_url: str | None = None
    flows: dict | None = None

    @model_validator(mode='after')
    def validate_security_scheme(self) -> 'OpenApiSecurityScheme':
        if self.type == 'http' and self.scheme is None:
            raise ValueError("'scheme' is required when type is 'http'")

        if self.type == 'oauth2' and self.flows is None:
            raise ValueError("'flows' is required when type is 'oauth2'")

        if self.type == 'openIdConnect' and self.open_id_connect_url is None:
            raise ValueError("'open_id_connect_url' is required when type is 'openIdConnect'")

        if self.type == 'apiKey':
            if self.name is None:
                raise ValueError("'name' is required when type is 'apiKey'")
            if self.in_field is None:
                raise ValueError("'in_field' is required when type is 'apiKey'")

        return self


HTTP_METHOD = Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE']


class OpenApiToolBinding(BaseModel):
    http_method: HTTP_METHOD
    http_path: str
    success_status_code: int = 200  # this is a diff from the spec
    security: Optional[List[OpenApiSecurityScheme]] = None
    servers: Optional[List[str]] = None
    connection_id: str | None = None

    @model_validator(mode='after')
    def validate_openapi_tool_binding(self):
        if len(self.servers) != 1:
            raise ValueError("OpenAPI definition must include exactly one server")
        return self


class PythonToolBinding(BaseModel):
    function: str
    requirements: Optional[List[str]] = []
    connections: dict[str, str] = None


class WxFlowsToolBinding(BaseModel):
    endpoint: str
    flow_name: str
    security: OpenApiSecurityScheme

    @model_validator(mode='after')
    def validate_security_scheme(self) -> 'WxFlowsToolBinding':
        if self.security.type != 'apiKey':
            raise ValueError("'security' scheme must be of type 'apiKey'")
        return self


class SkillToolBinding(BaseModel):
    skillset_id: str
    skill_id: str
    skill_operator_path: str
    http_method: HTTP_METHOD


class ClientSideToolBinding(BaseModel):
    pass

class McpToolBinding(BaseModel):
    server_url: Optional[str] = None
    source: str
    connections: Dict[str, str]

class ToolBinding(BaseModel):
    openapi: OpenApiToolBinding = None
    python: PythonToolBinding = None
    wxflows: WxFlowsToolBinding = None
    skill: SkillToolBinding = None
    client_side: ClientSideToolBinding = None
    mcp: McpToolBinding = None

    @model_validator(mode='after')
    def validate_binding_type(self) -> 'ToolBinding':
        bindings = [
            self.openapi is not None,
            self.python is not None,
            self.wxflows is not None,
            self.skill is not None,
            self.client_side is not None,
            self.mcp is not None
        ]
        if sum(bindings) == 0:
            raise ValueError("One binding must be set")
        if sum(bindings) > 1:
            raise ValueError("Only one binding can be set")
        return self


class ToolSpec(BaseModel):
    name: str
    description: str
    permission: ToolPermission
    input_schema: ToolRequestBody = None
    output_schema: ToolResponseBody = None
    binding: ToolBinding = None
    toolkit_id: str | None = None

