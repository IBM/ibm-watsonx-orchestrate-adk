from dataclasses import dataclass
from enum import Enum, StrEnum, auto
from datetime import date
import numbers
import inspect
import logging
from typing import (
    Annotated, Any, Callable, Self, cast, Literal, List, NamedTuple, Optional, Sequence, Union, NewType
)
from typing_extensions import Doc

import docstring_parser
from pydantic import BaseModel, Field, GetCoreSchemaHandler, GetJsonSchemaHandler, RootModel
from pydantic_core import core_schema
from pydantic.json_schema import JsonSchemaValue

from langchain_core.tools.base import create_schema_from_function
from langchain_core.utils.json_schema import dereference_refs

from ibm_watsonx_orchestrate.agent_builder.tools import PythonTool
from ibm_watsonx_orchestrate.flow_builder.flows.constants import ANY_USER
from ibm_watsonx_orchestrate.agent_builder.tools.types import (
    ToolSpec, ToolRequestBody, ToolResponseBody, JsonSchemaObject
)
from .utils import get_valid_name

logger = logging.getLogger(__name__)

class JsonSchemaObjectRef(JsonSchemaObject):
    ref: str=Field(description="The id of the schema to be used.", serialization_alias="$ref")

class SchemaRef(BaseModel):
 
    ref: str = Field(description="The id of the schema to be used.", serialization_alias="$ref")

def _assign_attribute(model_spec, attr_name, schema):
    if hasattr(schema, attr_name) and (getattr(schema, attr_name) is not None):
        model_spec[attr_name] = getattr(schema, attr_name)

def _to_json_from_json_schema(schema: JsonSchemaObject) -> dict[str, Any]:
    model_spec = {}
    if isinstance(schema, dict):
        schema = JsonSchemaObject.model_validate(schema)
    _assign_attribute(model_spec, "type", schema)
    _assign_attribute(model_spec, "title", schema)
    _assign_attribute(model_spec, "description", schema)
    _assign_attribute(model_spec, "required", schema)

    if hasattr(schema, "properties") and (schema.properties is not None):
        model_spec["properties"] = {}
        for prop_name, prop_schema in schema.properties.items():
            model_spec["properties"][prop_name] = _to_json_from_json_schema(prop_schema)
    if hasattr(schema, "items") and (schema.items is not None):
        model_spec["items"] = _to_json_from_json_schema(schema.items)
    
    _assign_attribute(model_spec, "default", schema)
    _assign_attribute(model_spec, "enum", schema)
    _assign_attribute(model_spec, "minimum", schema)
    _assign_attribute(model_spec, "maximum", schema)
    _assign_attribute(model_spec, "minLength", schema)
    _assign_attribute(model_spec, "maxLength", schema)
    _assign_attribute(model_spec, "format", schema)
    _assign_attribute(model_spec, "pattern", schema)

    if hasattr(schema, "anyOf") and getattr(schema, "anyOf") is not None:
        model_spec["anyOf"] = [_to_json_from_json_schema(schema) for schema in schema.anyOf]

    _assign_attribute(model_spec, "in_field", schema)
    _assign_attribute(model_spec, "in", schema)
    _assign_attribute(model_spec, "aliasName", schema)

    if hasattr(schema, 'model_extra') and schema.model_extra:
        # for each extra fiels, add it to the model spec
        for key, value in schema.model_extra.items():
            if value is not None:
                model_spec[key] = value

    if isinstance(schema, JsonSchemaObjectRef):
        model_spec["$ref"] = schema.ref
    return model_spec


def _to_json_from_input_schema(schema: Union[ToolRequestBody, SchemaRef]) -> dict[str, Any]:
    model_spec = {}
    if isinstance(schema, ToolRequestBody):
        request_body = cast(ToolRequestBody, schema)
        model_spec["type"] = request_body.type
        if request_body.properties:
            model_spec["properties"] = {}
            for prop_name, prop_schema in request_body.properties.items():
                model_spec["properties"][prop_name] = _to_json_from_json_schema(prop_schema)
        model_spec["required"] = request_body.required if request_body.required else []
        if schema.model_extra:
            for k, v in schema.model_extra.items():
                model_spec[k] = v
        
    elif isinstance(schema, SchemaRef):
        model_spec["$ref"] = schema.ref
    
    return model_spec

def _to_json_from_output_schema(schema: Union[ToolResponseBody, SchemaRef]) -> dict[str, Any]:
    model_spec = {}
    if isinstance(schema, ToolResponseBody):
        response_body = cast(ToolResponseBody, schema)
        model_spec["type"] = response_body.type
        if response_body.description:
            model_spec["description"] = response_body.description
        if response_body.properties:
            model_spec["properties"] = {}
            for prop_name, prop_schema in response_body.properties.items():
                model_spec["properties"][prop_name] = _to_json_from_json_schema(prop_schema)
        if response_body.items:
            model_spec["items"] = _to_json_from_json_schema(response_body.items)
        if response_body.uniqueItems:
            model_spec["uniqueItems"] = response_body.uniqueItems
        if response_body.anyOf:
            model_spec["anyOf"] = [_to_json_from_json_schema(schema) for schema in response_body.anyOf]
        if response_body.required and len(response_body.required) > 0:
            model_spec["required"] = response_body.required
    elif isinstance(schema, SchemaRef):
        model_spec["$ref"] = schema.ref
    
    return model_spec

class NodeSpec(BaseModel):
    kind: Literal["node", "tool", "user", "agent", "flow", "start", "decisions", "prompt", "branch", "wait", "foreach", "loop", "userflow", "end", "docproc" ] = "node"
    name: str
    display_name: str | None = None
    description: str | None = None
    input_schema: ToolRequestBody | SchemaRef | None = None
    output_schema: ToolResponseBody | SchemaRef | None = None
    output_schema_object: JsonSchemaObject | SchemaRef | None = None

    def __init__(self, **data):
        super().__init__(**data)

        if not self.name:
            if self.display_name:
                self.name = get_valid_name(self.display_name)
            else:
                raise ValueError("Either name or display_name must be specified.")

        if not self.display_name:
            if self.name:
                self.display_name = self.name
            else:
                raise ValueError("Either name or display_name must be specified.")

        # need to make sure name is valid
        self.name = get_valid_name(self.name)

    def to_json(self) -> dict[str, Any]:
        '''Create a JSON object representing the data'''
        model_spec = {}
        model_spec["kind"] = self.kind
        model_spec["name"] = self.name
        if self.display_name:
            model_spec["display_name"] = self.display_name
        if self.description:
            model_spec["description"] = self.description
        if self.input_schema:
            model_spec["input_schema"] = _to_json_from_input_schema(self.input_schema)
        if self.output_schema:
            if isinstance(self.output_schema, ToolResponseBody):
                if self.output_schema.type != 'null':
                    model_spec["output_schema"] = _to_json_from_output_schema(self.output_schema)
            else:
                model_spec["output_schema"] = _to_json_from_output_schema(self.output_schema)

        return model_spec

class DocExtConfigEntity(BaseModel):
    name: str = Field(description="Entity name")
    type: Literal["string", "date", "number"] = Field(default="string",  description="The type of the entity values")
    description: str = Field(title="Description", description="Description of the entity", default="")
    field_name: str = Field(title="Field Name", description="The normalized name of the entity", default="")
    multiple_mentions: bool = Field(title="Multiple mentions",description="When true, we can produce multiple mentions of this entity", default=False)
    example_value: str = Field(description="Value of example", default="")
    examples: list[str] = Field(title="Examples", description="Examples that help the LLM understand the expected entity mentions", default=[])

class DocExtConfig(BaseModel):
    domain: str = Field(description="Domiain of the document", default="other")
    type: str = Field(description="Document type", default="agreement")
    llm: str = Field(description="The LLM used for the document extraction", default="meta-llama/llama-3-2-11b-vision-instruct")
    entities: list[DocExtConfigEntity] = Field(default=[])

class LanguageCode(StrEnum):
    en = auto()
    fr = auto()

class DocProcCommonNodeSpec(NodeSpec):
    enable_hw: bool | None = Field(description="Boolean value indicating if hand-written feature is enabled.", title="Enable handwritten", default=False)

class DocExtSpec(DocProcCommonNodeSpec):
    version : str = Field(description="A version of the spec")
    config : DocExtConfig

    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "docext"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        model_spec["version"] = self.version
        model_spec["config"] = self.config.model_dump()
        return model_spec
    
class DocProcField(BaseModel):
    description: str = Field(description="A description of the field to extract from the document.")
    example: str = Field(description="An example of the field to extract from the document.", default='')
    default: Optional[str] = Field(description="A default value for the field to extract from the document.", default='')

class DocProcTable(BaseModel):
    type: Literal["array"]
    description: str = Field(description="A description of the table to extract from the document.")
    columns: dict[str,DocProcField] = Field(description="The columns to extract from the table. These are the keys in the table extraction result.")

class DocProcKVPSchema(BaseModel):
    document_type: str = Field(description="A label for the kind of documents we want to extract")
    document_description: str = Field(description="A description of the kind of documents we want to extractI. This is used to select which schema to use for extraction.")
    fields: dict[str, DocProcField | DocProcTable] = Field(description="The fields to extract from the document. These are the keys in the KVP extraction result.")

class DocProcBoundingBox(BaseModel):
    x: float = Field(description="The x coordinate of the bounding box.")
    y: float = Field(description="The y coordinate of the bounding box.")
    width: float = Field(description="The width of the bounding box.")
    height: float = Field(description="The height of the bounding box.")
    page_number: int = Field(description="The page number of the bounding box in the document.")

class KVPBaseEntry(BaseModel):
    id: str = Field(description="A unique identifier.")
    raw_text: str = Field(description="The raw text.")
    normalized_text: Optional[str] = Field(description="The normalized text.", default=None)
    confidence_score: Optional[float] = Field(description="The confidence score.", default=None)
    bbox: Optional[DocProcBoundingBox] = Field(description="The bounding box in the document.", default=None)
    
class DocProcKey(KVPBaseEntry):
    semantic_label: str = Field(description="A semantic label for the key.")

class DocProcValue(KVPBaseEntry):
    pass

class DocProcKVP(BaseModel):
    id: str = Field(description="A unique identifier for the key-value pair.")
    type: Literal["key_value","only_value"]
    key: DocProcKey = Field(description="The key of the key-value pair.")
    value: DocProcValue = Field(description="The value of the key-value pair.")
    group_id: Optional[str] = Field(default=None, description="The group id of the key-value pair. This is used to group key-value pairs together.")
    table_id: Optional[str] = Field(default=None, description="The table id of the key-value pair. This is used to group key-value pairs together in a table.")
    table_name: Optional[str] = Field(default=None, description="The name of the table the key-value pair belongs to. This is used to group key-value pairs together in a table.")
    table_row_index: Optional[int] = Field(default=None, description="The index of the row in the table the key-value pair belongs to. This is used to group key-value pairs together in a table.")

class DocProcTask(StrEnum):
    '''
    Possible names for the Document processing task parameter
    '''
    text_extraction = auto()

class DocProcSpec(DocProcCommonNodeSpec):
    task: DocProcTask = Field(description='The document processing operation name', default=DocProcTask.text_extraction)
    kvp_schema: List[DocProcKVPSchema] | None = Field(
        title='KVP schemas',
        description="Optional list of key-value pair schemas to use for extraction.",
        default=None)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "docproc"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        model_spec["task"] = self.task
        return model_spec
    
class StartNodeSpec(NodeSpec):
    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "start"

class EndNodeSpec(NodeSpec):
    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "end"

class ToolNodeSpec(NodeSpec):
    tool: Union[str, ToolSpec] = Field(default = None, description="the tool to use")

    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "tool"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        if self.tool:
            if isinstance(self.tool, ToolSpec):
                model_spec["tool"] = self.tool.model_dump(exclude_defaults=True, exclude_none=True, exclude_unset=True)
            else:
                model_spec["tool"] = self.tool
        return model_spec


class UserFieldValue(BaseModel):
    text: str | None = None
    value: str | None = None

    def __init__(self, text: str | None = None, value: str | None = None):
        super().__init__(text=text, value=value)
        if self.value is None:
            self.value = self.text

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        if self.text:
            model_spec["text"] = self.text
        if self.value:
            model_spec["value"] = self.value

        return model_spec

class UserFieldOption(BaseModel):
    label: str
    values: list[UserFieldValue] | None = None

    # create a constructor that will take a list and create UserFieldValue
    def __init__(self, label: str, values=list[str]):
        super().__init__(label=label)
        self.values = []
        for value in values:
            item = UserFieldValue(text=value)
            self.values.append(item)

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        model_spec["label"] = self.label
        if self.values and len(self.values) > 0:
            model_spec["values"] = [value.to_json() for value in self.values]
        return model_spec
    
class UserFieldKind(str, Enum):
    Text: str = "text"
    Date: str = "date"
    DateTime: str = "datetime"
    Time: str = "time"
    Number: str = "number"
    Document: str = "document"
    Boolean: str = "boolean"
    Object: str = "object"

    def convert_python_type_to_kind(python_type: type) -> "UserFieldKind":
        if inspect.isclass(python_type):
            raise ValueError("Cannot convert class to kind")
        
        if python_type == str:
            return UserFieldKind.Text
        elif python_type == int:
            return UserFieldKind.Number
        elif python_type == float:
            return UserFieldKind.Number
        elif python_type == bool:
            return UserFieldKind.Boolean
        elif python_type == list:
            raise ValueError("Cannot convert list to kind")
        elif python_type == dict:
            raise ValueError("Cannot convert dict to kind")
        
        return UserFieldKind.Text
    
    def convert_kind_to_schema_property(kind: "UserFieldKind", name: str, description: str, 
                                        default: Any, option: UserFieldOption,
                                        custom: dict[str, Any]) -> dict[str, Any]:
        model_spec = {}
        model_spec["title"] = name
        model_spec["description"] = description
        model_spec["default"] = default

        model_spec["type"] = "string"
        if kind == UserFieldKind.Date:
            model_spec["format"] = "date"
        elif kind == UserFieldKind.Time:
            model_spec["format"] = "time"
        elif kind == UserFieldKind.DateTime:
            model_spec["format"] = "datetime"
        elif kind == UserFieldKind.Number:
            model_spec["format"] = "number"
        elif kind == UserFieldKind.Boolean:
            model_spec["type"] = "boolean"
        elif kind == UserFieldKind.Document:
            model_spec["format"] = "uri"
        elif kind == UserFieldKind.Object:
            raise ValueError("Object user fields are not supported.")
        
        if option:
            model_spec["enum"] = [value.text for value in option.values]

        if custom:
            for key, value in custom.items():
                model_spec[key] = value
        return model_spec


class UserField(BaseModel):
    name: str
    kind: UserFieldKind = UserFieldKind.Text
    text: str | None = Field(default=None, description="A descriptive text that can be used to ask user about this field.")
    display_name: str | None = None
    description: str | None = None
    default: Any | None = None
    option: UserFieldOption | None = None
    min: Any | None = None,
    max: Any | None = None,
    is_list: bool = False
    custom: dict[str, Any] | None = None
    widget: str | None = None

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        if self.name:
            model_spec["name"] = self.name
        if self.kind:
            model_spec["kind"] = self.kind.value
        if self.text:
            model_spec["text"] = self.text
        if self.display_name:
            model_spec["display_name"] = self.display_name
        if self.description:
            model_spec["description"] = self.description
        if self.default:
            model_spec["default"] = self.default
        if self.min:
            model_spec["min"] = self.min
        if self.max:
            model_spec["min"] = self.max
        if self.is_list:
            model_spec["is_list"] = self.is_list
        if self.option:
            model_spec["option"] = self.option.to_json()
        if self.custom:
            model_spec["custom"] = self.custom
        if self.widget:
            model_spec["widget"] = self.widget
        return model_spec

class UserNodeSpec(NodeSpec):
    owners: Sequence[str] | None = None
    text: str | None = None
    fields: list[UserField] | None = None

    def __init__(self, **data):
        super().__init__(**data)
        self.fields = []
        self.kind = "user"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        # remove input schema
        # if "input_schema" in model_spec:
        #    raise ValueError("Input schema is not allowed for user node.")
        #    del model_spec["input_schema"]

        if self.owners:
            model_spec["owners"] = self.owners
        if self.text:
            model_spec["text"] = self.text
        if self.fields and len(self.fields) > 0:
            model_spec["fields"] = [field.to_json() for field in self.fields]

        return model_spec

    def field(self, name: str, 
              kind: UserFieldKind, 
              text: str | None = None,
              display_name: str | None = None, 
              description: str | None = None, 
              default: Any | None = None, 
              option: list[str] | None = None, 
              min: Any | None = None,
              max: Any | None = None,
              is_list: bool = False,
              custom: dict[str, Any] | None = None,
              widget: str | None = None):
        userfield = UserField(name=name, 
                              kind=kind, 
                              text=text,
                              display_name=display_name, 
                              description=description, 
                              default=default, 
                              option=option, 
                              min=min,
                              max=max,
                              is_list=is_list,
                              custom=custom,
                              widget=widget)
        
        # find the index of the field
        i = 0
        for field in self.fields:
            if field.name == name:
                break
        
        if (len(self.fields) - 1) >= i:
            self.fields[i] = userfield # replace
        else:
            self.fields.append(userfield) # append

    def setup_fields(self):
        # make sure fields are not there already
        if hasattr(self, "fields") and len(self.fields) > 0:
            raise ValueError("Fields are already defined.")
        
        if self.output_schema:
            if isinstance(self.output_schema, SchemaRef):
                schema = dereference_refs(schema)
        schema = self.output_schema

        # get all the fields from JSON schema
        if self.output_schema and isinstance(self.output_schema, ToolResponseBody):
            self.fields = []
            for prop_name, prop_schema in self.output_schema.properties.items():
                self.fields.append(UserField(name=prop_name,
                                             kind=UserFieldKind.convert_python_type_to_kind(prop_schema.type),
                                             display_name=prop_schema.title,
                                             description=prop_schema.description,
                                             default=prop_schema.default,
                                             option=self.setup_field_options(prop_schema.title, prop_schema.enum),
                                             is_list=prop_schema.type == "array",
                                             min=prop_schema.minimum,
                                             max=prop_schema.maximum,
                                             custom=prop_schema.model_extra))

    def setup_field_options(self, name: str, enums: List[str]) -> UserFieldOption:
        if enums:
            option = UserFieldOption(label=name, values=enums)
            return option
        else:
            return None



class AgentNodeSpec(ToolNodeSpec):
    message: str | None = Field(default=None, description="The instructions for the task.")
    title: str | None = Field(default=None, description="The title of the message.")
    guidelines: str | None = Field(default=None, description="The guidelines for the task.")
    agent: str

    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "agent"
    
    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        if self.message:
            model_spec["message"] = self.message
        if self.guidelines:
            model_spec["guidelines"] = self.guidelines
        if self.agent:
            model_spec["agent"] = self.agent
        if self.title:
            model_spec["title"] = self.title
        return model_spec

class PromptLLMParameters(BaseModel):
    temperature: Optional[float] = None
    min_new_tokens: Optional[int] = None
    max_new_tokens: Optional[int] = None
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    stop_sequences: Optional[list[str]] = None
        
    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        if self.temperature:
            model_spec["temperature"] = self.temperature
        if self.min_new_tokens:
            model_spec["min_new_tokens"] = self.min_new_tokens
        if self.max_new_tokens:
            model_spec["max_new_tokens"] = self.max_new_tokens
        if self.top_k:
            model_spec["top_k"] = self.top_k
        if self.top_p:
            model_spec["top_p"] = self.top_p
        if self.stop_sequences:
            model_spec["stop_sequences"] = self.stop_sequences
        return model_spec


class PromptNodeSpec(NodeSpec):
    system_prompt: str | list[str]
    user_prompt: str | list[str]
    llm: Optional[str] 
    llm_parameters: Optional[PromptLLMParameters] 

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.kind = "prompt"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        if self.system_prompt:
            model_spec["system_prompt"] = self.system_prompt
        if self.user_prompt:
            model_spec["user_prompt"] = self.user_prompt
        if self.llm:
            model_spec["llm"] = self.llm
        if self.llm_parameters:
            model_spec["llm_parameters"] = self.llm_parameters.to_json()

        return model_spec
    

class Expression(BaseModel):
    '''An expression could return a boolean or a value'''
    expression: str = Field(description="A python expression to be run by the flow engine")

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        model_spec["expression"] = self.expression;
        return model_spec
    
class MatchPolicy(Enum):
 
    FIRST_MATCH = 1
    ANY_MATCH = 2

class FlowControlNodeSpec(NodeSpec):
    ...

class BranchNodeSpec(FlowControlNodeSpec):
    '''
    A node that evaluates an expression and executes one of its cases based on the result.

    Parameters:
    evaluator (Expression): An expression that will be evaluated to determine which case to execute. The result can be a boolean, a label (string) or a list of labels.
    cases (dict[str | bool, str]): A dictionary of labels to node names. The keys can be strings or booleans.
    match_policy (MatchPolicy): The policy to use when evaluating the expression.
    '''
    evaluator: Expression
    cases: dict[str | bool, str] = Field(default = {},
                                         description="A dictionary of labels to node names.")
    match_policy: MatchPolicy = Field(default = MatchPolicy.FIRST_MATCH)

    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "branch"
    
    def to_json(self) -> dict[str, Any]:
        my_dict = super().to_json()

        if self.evaluator:
            my_dict["evaluator"] = self.evaluator.to_json()

        my_dict["cases"] = self.cases
        my_dict["match_policy"] = self.match_policy.name
        return my_dict


class WaitPolicy(Enum):
 
    ONE_OF = 1
    ALL_OF = 2
    MIN_OF = 3

class WaitNodeSpec(FlowControlNodeSpec):
 
    nodes: List[str] = []
    wait_policy: WaitPolicy = Field(default = WaitPolicy.ALL_OF)
    minimum_nodes: int = 1 # only used when the policy is MIN_OF

    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "wait"
    
    def to_json(self) -> dict[str, Any]:
        my_dict = super().to_json()

        my_dict["nodes"] = self.nodes
        my_dict["wait_policy"] = self.wait_policy.name
        if (self.wait_policy == WaitPolicy.MIN_OF):
            my_dict["minimum_nodes"] = self.minimum_nodes

        return my_dict

class FlowSpec(NodeSpec):
    # who can initiate the flow
    initiators: Sequence[str] = [ANY_USER]
    schedulable: bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.kind = "flow"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        if self.initiators:
            model_spec["initiators"] = self.initiators
        
        model_spec["schedulable"] = self.schedulable

        return model_spec

class LoopSpec(FlowSpec):
 
    evaluator: Expression = Field(description="the condition to evaluate")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.kind = "loop"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        if self.evaluator:
            model_spec["evaluator"] = self.evaluator.to_json()

        return model_spec

class UserFlowSpec(FlowSpec):
    owners: Sequence[str] = [ANY_USER]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.kind = "userflow"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        if self.initiators:
            model_spec["owners"] = self.initiators

        return model_spec

class ForeachPolicy(Enum):
 
    SEQUENTIAL = 1
    # support only SEQUENTIAL for now
    # PARALLEL = 2

class ForeachSpec(FlowSpec):
 
    item_schema: JsonSchemaObject | SchemaRef = Field(description="The schema of the items in the list")
    foreach_policy: ForeachPolicy = Field(default=ForeachPolicy.SEQUENTIAL, description="The type of foreach loop")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.kind = "foreach"

    def to_json(self) -> dict[str, Any]:
        my_dict = super().to_json()

        if isinstance(self.item_schema, JsonSchemaObject):
            my_dict["item_schema"] = _to_json_from_json_schema(self.item_schema)
        else:
            my_dict["item_schema"] = self.item_schema.model_dump(exclude_defaults=True, exclude_none=True, exclude_unset=True)

        my_dict["foreach_policy"] = self.foreach_policy.name
        return my_dict

class TaskData(NamedTuple):
 
    inputs: dict | None = None
    outputs: dict | None = None

class TaskEventType(Enum):
 
    ON_TASK_WAIT = "task:on_task_wait" # the task is waiting for inputs before proceeding
    ON_TASK_START = "task:on_task_start"
    ON_TASK_END = "task:on_task_end"
    ON_TASK_STREAM = "task:on_task_stream"
    ON_TASK_ERROR = "task:on_task_error"
    ON_TASK_RESUME= "task:on_task_resume"

class FlowData(BaseModel):
    '''This class represents the data that is passed between tasks in a flow.'''
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)

class FlowContext(BaseModel):
 
    name: str | None = None # name of the process or task
    task_id: str | None = None # id of the task, this is at the task definition level
    flow_id: str | None = None # id of the flow, this is at the flow definition level
    instance_id: str | None = None
    thread_id: str | None = None
    correlation_id: str | None = None
    tenant_id: str | None = None
    parent_context: Any | None = None
    child_context: List["FlowContext"] | None = None
    metadata: dict = Field(default_factory=dict[str, Any])
    data: Optional[FlowData] = None

    def get(self, key: str) -> Any:
     
        if key in self.data:
            return self.data[key]

        if self.parent_context:
            pc = cast(FlowContext, self.parent_conetxt)
            return pc.get(key)
    
class FlowEventType(Enum):
 
    ON_FLOW_START = "flow:on_flow_start"
    ON_FLOW_END = "flow:on_flow_end"
    ON_FLOW_ERROR = "flow:on_flow_error"
    ON_FLOW_RESUME = "flow:on_flow_resume"

@dataclass
class FlowEvent:
 
    kind: Union[FlowEventType, TaskEventType] # type of event
    context: FlowContext
    error: dict | None = None # error message if any


class Assignment(BaseModel):
    '''
    This class represents an assignment in the system.  Specify an expression that 
    can be used to retrieve or set a value in the FlowContext

    Attributes:
        target (str): The target of the assignment.  Always assume the context is the current Node. e.g. "name"
        source (str): The source code of the assignment.  This can be a simple variable name or a more python expression.  
            e.g. "node.input.name" or "=f'{node.output.name}_{node.output.id}'"

    '''
    target_variable: str
    value_expression: str | None = None
    has_no_value: bool = False
    default_value: Any | None = None
    metadata: dict = Field(default_factory=dict[str, Any])

class LanguageCode(StrEnum):
    '''
    The ISO-639 language codes understood by Document Processing functions.
    A special 'en_hw' code is used to enable an English handwritten model.
    '''
    en = auto()
    fr = auto()
    en_hw = auto()


class File(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_wrap_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda v: str(v))
        )

    @classmethod
    def validate(cls, value: Any) -> "File":
        if not isinstance(value, str):
            raise TypeError("File must be a document reference (string)")
        return cls(value)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {
            "type": "string",
            "title": "Document reference",
            "format": "binary",
            "description": "Either an ID or a URL identifying the document to be used.",
            "wrap_data": False,
            "required": []
        }
    
class DocExtInput(BaseModel):
    document_ref: bytes | File = Field(description="Either an ID or a URL identifying the document to be used.", title='Document reference', default=None, json_schema_extra={"format": "binary"})


class DocProcInput(BaseModel):
    '''
    This class represents the input of a Document processing task. 

    Attributes:
        document_ref (bytes|str): This is either a URL to the location of the document bytes or an ID that we use to resolve the location of the document
        language (LanguageCode): Optional language code used when processing the input document
        kvp_schemas (List[DocProcKVPSchema]): Optional list of key-value pair schemas to use for extraction. If not provided or None, no KVPs will be extracted. If an empty list is provided, we will use the internal schemas to extract KVPS.
    '''
    # This is declared as bytes but the runtime will understand if a URL is send in as input.
    # We need to use bytes here for Chat-with-doc to recognize the input as a File.
    document_ref: bytes | File = Field(description="Either an ID or a URL identifying the document to be used.", title='Document reference', default=None, json_schema_extra={"format": "binary"})
    kvp_schemas: Optional[List[DocProcKVPSchema]] = Field(
        title='KVP schemas',
        description="Optional list of key-value pair schemas to use for extraction.",
        default=None)

class TextExtractionResponse(BaseModel):
    '''
    The text extraction operation response.
    Attributes:
        text (str): the text extracted from the input document.
        kvps (Optional[list[DocProcKVP]]): A list of key-value pairs extracted from the document. If no KVPs were extracted, this will be None.
    '''
    text: str = Field(description='The text extracted from the input document', title='text')
    kvps: Optional[list[DocProcKVP]] = Field(description="A list of key-value pairs extracted from the document.", default=None)


class DecisionsCondition(BaseModel):
    _condition: str | None = None

    def greater_than(self, value: Union[numbers.Number, date, str]) -> Self:
        self._check_type_is_number_or_date_or_str(value)
        self._condition = f"> {self._format_value(value)}"
        return self

    def greater_than_or_equal(self, value: Union[numbers.Number, date, str]) -> Self:
        self._check_type_is_number_or_date_or_str(value)
        self._condition = f">= {self._format_value(value)}"
        return self

    def less_than(self, value: Union[numbers.Number, date, str]) -> Self:
        self._check_type_is_number_or_date_or_str(value)
        self._condition = f"< {self._format_value(value)}"
        return self

    def less_than_or_equal(self, value: Union[numbers.Number, date, str]) -> Self:
        self._check_type_is_number_or_date_or_str(value)
        self._condition = f"<= {self._format_value(value)}"
        return self

    def equal(self, value: Union[numbers.Number, date, str]) -> Self:
        self._check_type_is_number_or_date_or_str(value)
        self._condition = f"== {self._format_value(value)}"
        return self

    def not_equal(self, value: Union[numbers.Number, date, str]) -> Self:
        self._check_type_is_number_or_date_or_str(value)
        self._condition = f"== {self._format_value(value)}"
        return self
    
    def contains(self, value: str) -> Self:
        self._check_type_is_str(value)
        self._condition = f"contains {self._format_value(value)}"
        return self

    def not_contains(self, value: str) -> Self:
        self._check_type_is_str(value)
        self._condition = f"doesNotContain {self._format_value(value)}"
        return self

    def is_in(self, value: str) -> Self:
        self._check_type_is_str(value)
        self._condition = f"in {self._format_value(value)}"
        return self

    def is_not_in(self, value: str) -> Self:
        self._check_type_is_str(value)
        self._condition = f"notIn {self._format_value(value)}"
        return self

    def startswith(self, value: str) -> Self:
        self._check_type_is_str(value)
        self._condition = f"startsWith {self._format_value(value)}"
        return self

    def endswith(self, value: str) -> Self:
        self._check_type_is_str(value)
        self._condition = f"endsWith {self._format_value(value)}"
        return self


    def in_range(self, startValue: Union[numbers.Number, date], endValue: Union[numbers.Number, date], 
                 startsInclusive: bool = False, endsInclusive: bool = False) -> Self:
        self._check_type_is_number_or_date_or_str(startValue)
        self._check_type_is_number_or_date_or_str(endValue)
        if type(startValue) is not type(endValue):
            raise TypeError("startValue and endValue must be of the same type")
        start_op = "[" if startsInclusive else "("    # [ is inclusive, ( is exclusive
        end_op =  "]" if endsInclusive else ")" 
        self._condition = f"{start_op}{self._format_value(startValue)}:{self._format_value(endValue)}{end_op}"
        return self

    def _check_type_is_number_or_date(self, value: Union[numbers.Number, date]):
        if not isinstance(value, (numbers.Number, date)):
            raise TypeError("Value must be a number or a date")

    def _check_type_is_number_or_date_or_str(self, value: Union[numbers.Number, date, str]):
        if not isinstance(value, (numbers.Number, date, str)):
            raise TypeError("Value must be a number or a date or a string")
        
    def _check_type_is_str(self, value: str):
        if not isinstance(value, str):
            raise TypeError("Value must be a string")
    
    @staticmethod
    def _format_value(value: Union[numbers.Number, date, str]):
        if isinstance(value, numbers.Number):
            return f"{value}"
        if isinstance(value, date):
            return f"\"{value.strftime('%B %d, %Y')}\""
        return f"\"{value}\""
    
    def condition(self):
        return self._condition



class DecisionsRule(BaseModel):
    '''
    A set of decisions rules.
    '''
    _conditions: dict[str, str]
    _actions: dict[str, Union[numbers.Number, str]]

    def __init__(self, **data):
        super().__init__(**data)
        self._conditions = {}
        self._actions = {}

    def condition(self, key: str, cond: DecisionsCondition) -> Self:
        self._conditions[key] = cond.condition()
        return self
    
    def action(self, key: str, value: Union[numbers.Number, date, str]) -> Self:
        if isinstance(value, date):
            self._actions[key] = value.strftime("%B %d, %Y")
            return self
        self._actions[key] = value
        return self

    def to_json(self) -> dict[str, Any]:
        '''
        Serialize the rules into JSON object
        '''
        model_spec = {}
        if self._conditions:
            model_spec["conditions"] = self._conditions
        if self._actions:
            model_spec["actions"] = self._actions
        return model_spec


class DecisionsNodeSpec(NodeSpec):
    '''
    Node specification for Decision Table
    '''
    locale: str | None = None
    rules: list[DecisionsRule]
    default_actions: dict[str, Union[int, float, complex, str]] | None

    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "decisions"

    def default_action(self, key: str, value: Union[int, float, complex, date, str]) -> Self:
        '''
        create a new default action
        '''
        if isinstance(value, date):
            self.default_actions[key] = value.strftime("%B %d, %Y")
            return self
        self.default_actions[key] = value
        return self

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        if self.locale:
            model_spec["locale"] = self.locale
        if self.rules:
            model_spec["rules"] = [rule.to_json() for rule in self.rules]
        if self.default_actions:
            model_spec["default_actions"] = self.default_actions

        return model_spec


def extract_node_spec(
        fn: Callable | PythonTool,
        name: Optional[str] = None,
        description: Optional[str] = None) -> NodeSpec:
    """Extract the task specification from a function. """
    if isinstance(fn, PythonTool):
        fn = cast(PythonTool, fn).fn

    if fn.__doc__ is not None:
        doc = docstring_parser.parse(fn.__doc__)
    else:
        doc = None

    # Use the function docstring if no description is provided
    _desc = description
    if description is None and doc is not None:
        _desc = doc.description

    # Use the function name if no name is provided
    _name = name or fn.__name__

    # Create the input schema from the function
    input_schema: type[BaseModel] = create_schema_from_function(_name, fn, parse_docstring=False)
    input_schema_json = input_schema.model_json_schema()
    input_schema_json = dereference_refs(input_schema_json)
    # logger.info("Input schema: %s", input_schema_json)

    # Convert the input schema to a JsonSchemaObject
    input_schema_obj = JsonSchemaObject(**input_schema_json)

    # Get the function signature
    sig = inspect.signature(fn)

    # Get the function return type
    return_type = sig.return_annotation
    output_schema =  ToolResponseBody(type='null')
    output_schema_obj = None

    if not return_type or return_type == inspect._empty:
        pass
    elif inspect.isclass(return_type) and issubclass(return_type, BaseModel):
        output_schema_json = return_type.model_json_schema()
        output_schema_obj = JsonSchemaObject(**output_schema_json)
        output_schema = ToolResponseBody(
            type="object",
            properties=output_schema_obj.properties or {},
            required=output_schema_obj.required or []
        )
    elif isinstance(return_type, type):
        schema_type = 'object'
        if return_type == str:
            schema_type = 'string'
        elif return_type == int:
            schema_type = 'integer'
        elif return_type == float:
            schema_type = 'number'
        elif return_type == bool:
            schema_type = 'boolean'
        elif issubclass(return_type, list):
            schema_type = 'array'
            # TODO: inspect the list item type and use that as the item type
        output_schema = ToolResponseBody(type=schema_type)

    # Create the tool spec
    spec = NodeSpec(
        name=_name,
        description=_desc,
        input_schema=ToolRequestBody(
            type=input_schema_obj.type,
            properties=input_schema_obj.properties or {},
            required=input_schema_obj.required or []
        ),
        output_schema=output_schema,
        output_schema_object = output_schema_obj
    )

    # logger.info("Generated node spec: %s", spec)
    return spec
