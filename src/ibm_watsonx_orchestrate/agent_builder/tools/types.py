from enum import Enum
import os
from typing import List, Any, Dict, Literal, Optional, Union
import logging

from pydantic import BaseModel, GetCoreSchemaHandler, GetJsonSchemaHandler, SerializerFunctionWrapHandler, ValidationError, ValidationInfo, field_serializer, model_serializer, model_validator, ConfigDict, Field, AliasChoices
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema
import requests
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.agent_builder.connections import KeyValueConnectionCredentials

logger = logging.getLogger(__name__)

class ToolPermission(str, Enum):
    READ_ONLY = 'read_only'
    WRITE_ONLY = 'write_only'
    READ_WRITE = 'read_write'
    ADMIN = 'admin'

class PythonToolKind(str, Enum):
    JOIN_TOOL = 'join_tool'
    TOOL = 'tool'

class JsonSchemaTokens(str, Enum):
    NONE = '__null__'


class JsonSchemaObject(BaseModel):
    model_config = ConfigDict(
        extra='allow'
    )

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
    wrap_data: Optional[bool] = True
    "Runtime feature where the sdk can provide the original name of a field before prefixing"

    @model_validator(mode='after')
    def normalize_type_field(self) -> 'JsonSchemaObject':
        if isinstance(self.type, list):
            self.type = self.type[0]
        return self
    

    @model_serializer(mode='wrap')
    def default_field_serializer(self, handler: SerializerFunctionWrapHandler):
        # JsonSchemaTokens will automatically be converted to string
        serialized = handler(self)

        if serialized and serialized.get('default') == JsonSchemaTokens.NONE:
            serialized['default'] = None

        return serialized


class ToolRequestBody(BaseModel):
    model_config = ConfigDict(extra='allow')

    type: Literal['object', 'string']
    properties: Optional[Dict[str, JsonSchemaObject]] = {}
    required: Optional[List[str]] = []


class ToolResponseBody(BaseModel):
    model_config = ConfigDict(extra='allow')

    type: Literal['object', 'string', 'number', 'integer', 'boolean', 'array','null'] = None
    description: str = None
    properties: Dict[str, JsonSchemaObject] = None
    items: JsonSchemaObject = None
    uniqueItems: bool = None
    anyOf: List['JsonSchemaObject'] = None
    required: Optional[List[str]] = None
    format: Optional[str] = None

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
            raise BadRequest("'scheme' is required when type is 'http'")

        if self.type == 'oauth2' and self.flows is None:
            raise BadRequest("'flows' is required when type is 'oauth2'")

        if self.type == 'openIdConnect' and self.open_id_connect_url is None:
            raise BadRequest("'open_id_connect_url' is required when type is 'openIdConnect'")

        if self.type == 'apiKey':
            if self.name is None:
                raise BadRequest("'name' is required when type is 'apiKey'")
            if self.in_field is None:
                raise BadRequest("'in_field' is required when type is 'apiKey'")

        return self


HTTP_METHOD = Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

class CallbackBinding(BaseModel):
    callback_url: str
    method: HTTP_METHOD
    input_schema: Optional[ToolRequestBody] = None
    output_schema: ToolResponseBody

class AcknowledgementBinding(BaseModel):
    output_schema: ToolResponseBody


class OpenApiToolBinding(BaseModel):
    http_method: HTTP_METHOD
    http_path: str
    success_status_code: int = 200  # this is a diff from the spec
    security: Optional[List[OpenApiSecurityScheme]] = None
    servers: Optional[List[str]] = None
    connection_id: str | None = None
    callback: Optional[CallbackBinding] = None
    acknowledgement: Optional[AcknowledgementBinding] = None

    @model_validator(mode='after')
    def validate_openapi_tool_binding(self, info: ValidationInfo):
        context = getattr(info, "context", None)

        if len(self.servers) != 1:
            if isinstance(context, str) and context == "list":
                logger.warning("OpenAPI definition must include exactly one server")
            else:
                raise BadRequest("OpenAPI definition must include exactly one server")
        return self


class PythonToolBinding(BaseModel):
    function: str
    requirements: Optional[List[str]] = []
    connections: dict[str, str] = None
    agent_run_paramater: Optional[str] = None


class WxFlowsToolBinding(BaseModel):
    endpoint: str
    flow_name: str
    security: OpenApiSecurityScheme

    @model_validator(mode='after')
    def validate_security_scheme(self) -> 'WxFlowsToolBinding':
        if self.security.type != 'apiKey':
            raise BadRequest("'security' scheme must be of type 'apiKey'")
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
    source: str | None
    connections: Dict[str, str] | None

class FlowToolBinding(BaseModel):
    flow_id: str
    model: Optional[dict] = None

class LangflowToolBinding(BaseModel):
    langflow_id: Optional[str] = None
    project_id: Optional[str] = None
    langflow_version: str
    connections: Optional[dict] = None

    @model_validator(mode='after')
    def validate_connection_type(self) -> 'LangflowToolBinding':
        if self.connections:
            for k,v in self.connections.items():
                if not v:
                    raise ValidationError(f"No connection provided for '{k}'")
        return self


class ToolBinding(BaseModel):
    openapi: OpenApiToolBinding = None
    python: PythonToolBinding = None
    wxflows: WxFlowsToolBinding = None
    skill: SkillToolBinding = None
    client_side: ClientSideToolBinding = None
    mcp: McpToolBinding = None
    flow: FlowToolBinding = None
    langflow: LangflowToolBinding = None

    @model_validator(mode='after')
    def validate_binding_type(self) -> 'ToolBinding':
        bindings = [
            self.openapi is not None,
            self.python is not None,
            self.wxflows is not None,
            self.skill is not None,
            self.client_side is not None,
            self.mcp is not None,
            self.flow is not None,
            self.langflow is not None
        ]
        if sum(bindings) == 0:
            raise BadRequest("One binding must be set")
        if sum(bindings) > 1:
            raise BadRequest("Only one binding can be set")
        return self

class ToolSpec(BaseModel):
    name: str
    id: str | None = None
    display_name: str | None = None
    description: str
    permission: ToolPermission
    input_schema: ToolRequestBody = None
    output_schema: ToolResponseBody = None
    binding: ToolBinding = None
    toolkit_id: str | None = None
    is_async: bool = False

    def is_custom_join_tool(self) -> bool:
        if self.binding.python is None:
            return False

        # The code below validates the input schema to have the following structure:
        # {
        #     "type": "object",
        #     "properties": {
        #         "messages": {
        #             "type": "array",
        #             "items": {
        #                 "type": "object",
        #             },
        #         },
        #         "task_results": {
        #             "type": "object",
        #         },
        #         "original_query": {
        #             "type": "string",
        #         },
        #     },
        #     "required": {"original_query", "task_results", "messages"},
        # }

        input_schema = self.input_schema
        if input_schema.type != 'object':
            return False

        required_fields = {"original_query", "task_results", "messages"}
        if input_schema.required is None or set(input_schema.required) != required_fields:
            return False
        if input_schema.properties is None or set(input_schema.properties.keys()) != required_fields:
            return False

        if input_schema.properties["messages"].type != "array":
            return False
        if not input_schema.properties["messages"].items or input_schema.properties["messages"].items.type != "object":
            return False
        if input_schema.properties["task_results"].type != "object":
            return False
        if input_schema.properties["original_query"].type != "string":
            return False

        return True


CONNECTION_TIMEOUT_SECONDS = 30
READ_TIMEOUT_SECONDS = 30
X_AMZ_META_HEADER_PREFIX = os.getenv("X_AMZ_META_HEADER_PREFIX", "x-amz-meta-")


class WXOFile(str):

    @classmethod
    def get_file_name(cls, url: str) -> str | None:
        """Returns the file name."""
        return cls._get_headers(url).get(f"{X_AMZ_META_HEADER_PREFIX}filename", None)

    @classmethod
    def get_file_size(cls, url: str) -> int | None:
        """Returns the file size in bytes."""
        size = cls._get_headers(url).get(f"{X_AMZ_META_HEADER_PREFIX}size", None)
        return int(size) if size is not None else None

    @classmethod
    def get_file_type(cls, url: str) -> str | None:
        """Returns the MIME type of the file based on S3 metadata or file extension."""
        return cls._get_headers(url).get(f"{X_AMZ_META_HEADER_PREFIX}content-type", None)

    @classmethod
    def get_content(cls, url: str) -> bytes:
        """Retuns the contents"""
        try:
            res = requests.get(url)
            return res.content
        except Exception as e:
            raise e

    @classmethod
    def _get_headers(cls, url: str) -> dict:
        try:
            res = requests.get(url, 
                               headers={'Range': 'bytes=0-0'}, 
                               timeout=(CONNECTION_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS))
            return res.headers
        except Exception as e:
            raise e

    @classmethod
    def validate(cls, value: Any) -> "WXOFile":
        if not isinstance(value, str):
            raise TypeError("File must be a document reference (string)")
        return cls(value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_wrap_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: str(v))
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {
            "type": "string",
            "title": "File reference",
            "format": "wxo-file",
            "description": "A URL identifying the File to be used.",
        }


class ToolListEntry(BaseModel):
    name: str = Field(description="The name of the tool")
    description: Optional[str] = Field(description="A description of the purpose of the tool")
    type: Optional[str] = Field(description="The type of the tool"),
    toolkit: Optional[str] = Field(description="The name of the Toolkit the tool belongs. Empty if the tool is not from a Toolkit"),
    app_ids: Optional[List[str]] = Field(description="A list of app_ids that show what connections are bound to a tool")

    def get_row_details(self):
        app_ids = ", ".join(self.app_ids) if self.app_ids else ""
        return [self.name, self.description, self.type, self.toolkit, app_ids]
