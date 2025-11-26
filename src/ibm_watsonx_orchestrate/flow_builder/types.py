from dataclasses import dataclass
from enum import Enum, StrEnum, auto
from datetime import date
import numbers
import inspect
import logging

import uuid
import re
import time
from typing import (
    Any, Callable, Self, cast, Literal, List, NamedTuple, Optional, Sequence, Union
)

import docstring_parser
from ibm_watsonx_orchestrate.flow_builder.utils import clone_form_schema, get_valid_name
from pydantic import computed_field, field_validator
from pydantic import BaseModel, Field, GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic_core import core_schema
from pydantic.json_schema import JsonSchemaValue

from langchain_core.tools.base import create_schema_from_function
from langchain_core.utils.json_schema import dereference_refs

from ibm_watsonx_orchestrate.agent_builder.tools import PythonTool
from ibm_watsonx_orchestrate.flow_builder.data_map import Assignment, DataMap, add_assignment, ensure_datamap
from ibm_watsonx_orchestrate.flow_builder.flows.constants import ANY_USER
from ibm_watsonx_orchestrate.agent_builder.tools.types import (
    ToolSpec, ToolRequestBody, ToolResponseBody, JsonSchemaObject, WXOFile
)
from ibm_watsonx_orchestrate.flow_builder.utils import ( _get_tool_request_body, _get_tool_response_body )



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


def _to_json_from_input_schema(schema: Union[ToolRequestBody, SchemaRef, JsonSchemaObject]) -> dict[str, Any]:
    model_spec = {}

    if isinstance(schema, JsonSchemaObject):
        schema = _get_tool_request_body(schema)
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

def _to_json_from_output_schema(schema: Union[ToolResponseBody, SchemaRef, JsonSchemaObject]) -> dict[str, Any]:
    model_spec = {}
    if isinstance(schema, JsonSchemaObject):
        schema = _get_tool_response_body(schema)
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
        if response_body.type == "string" and response_body.format is not None:
            model_spec["format"] = response_body.format
    elif isinstance(schema, SchemaRef):
        model_spec["$ref"] = schema.ref
    
    return model_spec

class Position(BaseModel):
    x: float
    y: float

class NodeSpec(BaseModel):
    kind: Literal["node", "tool", "user", "agent", "flow", "start", "decisions", "prompt", "timer", "branch", "wait", "foreach", "loop", "userflow", "end", "docproc", "docext", "docclassifier", "user_flow", "script" ] = "node"
    name: str
    display_name: str | None = None
    description: str | None = None
    input_schema: ToolRequestBody | SchemaRef | None = None
    output_schema: ToolResponseBody | SchemaRef | None = None
    output_schema_object: JsonSchemaObject | SchemaRef | None = None
    position: Position | None = None

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
        if self.position:
            model_spec["position"] = self.position

        return model_spec

class DocExtConfigField(BaseModel):
    name: str = Field(description="Entity name")
    type: Literal["string", "date", "number", "table"] = Field(default="string",  description="The type of the entity values")
    description: str = Field(title="Description", description="Description of the entity", default="")
    field_name: str = Field(title="Field Name", description="The normalized name of the entity", default="")
    multiple_mentions: bool = Field(title="Multiple mentions",description="When true, we can produce multiple mentions of this entity", default=False)
    example_value: str = Field(description="Value of example", default="")
    examples: list[str] = Field(title="Examples", description="Examples that help the LLM understand the expected entity mentions", default=[])

class DocExtConfigTableField(DocExtConfigField):
    """
    A table field in the Document Extraction Config.
    """
    fields: List[DocExtConfigField] = Field(description="Fields within the table.")
    
    def __init__(self, **data):
        # Set type to "table" for table fields
        data['type'] = 'table'
        super().__init__(**data)

class DocExtConfig(BaseModel):
    domain: str = Field(description="Domain of the document", default="other")
    type: str = Field(description="Document type", default="agreement")
    llm: str = Field(description="The LLM used for the document extraction", default="meta-llama/llama-3-2-11b-vision-instruct")
    fields: list[Union[DocExtConfigField, DocExtConfigTableField]] = Field(default=[], description="Fields to extract from the document, including regular fields and table fields")
    field_extraction_method: str = Field(description="The method used to extract fields from the document", default="classic")

class LanguageCode(StrEnum):
    en = auto()
    fr = auto()

class DocProcTask(StrEnum):
    '''
    Possible names for the Document processing task parameter
    '''
    text_extraction = auto()
    custom_field_extraction = auto()
    custom_document_classification = auto()

class CustomClassOutput(BaseModel):
    class_name: str = Field(
        title="Class Name",
        description="Class Name of the Document",
        default=[],
    )

class DocumentClassificationResponse(BaseModel):
    custom_class_response: CustomClassOutput = Field(
        title="Custom Classification",
        description="The Class extracted by the llm",
    )

class DocClassifierClass(BaseModel):
    class_name: str = Field(title='Class Name', description="The predicted, normalized document class name based on provided name")

    @field_validator("class_name", mode="before")
    @classmethod
    def normalize_name(cls, name) -> str:
        pattern = r'^[a-zA-Z0-9_]{1,29}$'
        if not re.match(pattern, name): 
            raise ValueError(f"class_name \"{name}\" is not valid. class_name should contain only letters (a-z, A-Z), digits (0-9), and underscores (_)")
        return name
    
    @computed_field(description="A uuid for identifying classes, For easy filtering of documents classified in a class", return_type=str)
    def class_id(self) -> str:
        return str(uuid.uuid5(uuid.uuid1(), self.class_name + str(time.time())))

class DocClassifierConfig(BaseModel):
    domain: str = Field(description="Domain of the document", default="other",title="Domain")
    type: Literal["class_configuration"] = Field(description="Document type", default="class_configuration",title="Type")
    llm: str = Field(description="The LLM used for the document classfier", default="watsonx/meta-llama/llama-3-2-11b-vision-instruct",title="LLM")
    min_confidence: float = Field(description="The minimal confidence acceptable for an extracted field value", default=0.0,le=1.0, ge=0.0 ,title="Minimum Confidence")
    classes: list[DocClassifierClass] = Field(default=[], description="Classes which are needed to classify provided by user", title="Classes")

class DocProcCommonNodeSpec(NodeSpec):
    task: DocProcTask = Field(description='The document processing operation name', default=DocProcTask.text_extraction)
    enable_hw: bool | None = Field(description="Boolean value indicating if hand-written feature is enabled.", title="Enable handwritten", default=False)

    def __init__(self, **data):
        super().__init__(**data)
    
    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        model_spec["task"] = self.task
        model_spec["enable_hw"] = self.enable_hw
        
        return model_spec
    
class DocClassifierSpec(DocProcCommonNodeSpec):
    version : str = Field(description="A version of the spec")
    config : DocClassifierConfig
    enable_review: bool = Field(description="Indicate if enable human in the loop review", default=False)

    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "docclassifier"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        model_spec["version"] = self.version
        model_spec["config"] = self.config.model_dump()
        model_spec["task"] = DocProcTask.custom_document_classification
        model_spec["enable_review"] = self.enable_review
        return model_spec
    
class DocExtSpec(DocProcCommonNodeSpec):
    version : str = Field(description="A version of the spec")
    config : DocExtConfig
    min_confidence: float = Field(description="The minimal confidence acceptable for an extracted field value", default=0.0,le=1.0, ge=0.0 ,title="Minimum Confidence")
    review_fields: List[str] = Field(description="The fields that require user to review", default=[])
    enable_review: bool = Field(description="Enable human in the loop review", default=False)

    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "docext"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        model_spec["version"] = self.version
        model_spec["config"] = self.config.model_dump()
        model_spec["task"] = DocProcTask.custom_field_extraction
        model_spec["min_confidence"] = self.min_confidence
        model_spec["review_fields"] = self.review_fields
        model_spec["enable_review"] = self.enable_review
        return model_spec
    
class DocProcField(BaseModel):
    description: str = Field(description="A description of the field to extract from the document.")
    example: str = Field(description="An example of the field to extract from the document.", default='')
    default: Optional[str] = Field(description="A default value for the field to extract from the document.", default='')
    available_options: Optional[list[str]] = Field(description="A list of possible values for the field.", default=None) 

class DocProcTable(BaseModel):
    type: Literal["array"]
    description: str = Field(description="A description of the table to extract from the document.")
    columns: dict[str,DocProcField] = Field(description="The columns to extract from the table. These are the keys in the table extraction result.")

class DocProcKVPSchema(BaseModel):
    document_type: str = Field(description="A label for the kind of documents we want to extract")
    document_description: str = Field(description="A description of the kind of documents we want to extractI. This is used to select which schema to use for extraction.")
    additional_prompt_instructions: Optional[str] = Field(description="Additional instructions to guide the extraction. This is used to provide more context to the model about the document.", default=None)
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

class PlainTextReadingOrder(StrEnum):
    block_structure = auto()
    simple_line = auto()

class DocProcOutputFormat(StrEnum):
    '''
    Output format for document processing results.
    - docref: Output will be a document reference (default)
    - object: Output will be a JSON object
    '''
    docref = auto()
    object = auto()

class DocProcSpec(DocProcCommonNodeSpec):
    '''
    Document Processing Node Specification for flow-based document analysis.
    
    This class defines the configuration for a document processing node in a workflow,
    enabling text extraction, structure analysis, and key-value pair (KVP) extraction
    from documents using IBM Watson Document Understanding (WDU) service. It extends
    DocProcCommonNodeSpec to provide comprehensive document processing capabilities.
    
    The DocProcSpec node can perform multiple operations simultaneously:
    - Plain text extraction with configurable reading order
    - Document structure analysis (sections, tables, paragraphs, etc.)
    - LLM-based key-value pair extraction using custom schemas
    - Handwritten text recognition

    Attributes:
        kvp_schemas (List[DocProcKVPSchema] | None): Optional list of schemas defining
            the key-value pairs to extract from documents. Each schema specifies:
            - document_type: Label for the document category
            - document_description: Description for schema selection
            - fields: Dictionary of fields/tables to extract
            - additional_prompt_instructions: Extra guidance for the LLM
            
            Behavior:
            - None: No KVP extraction performed (default)
            - Empty list []: Uses internal predefined schemas
            - List with schemas: Uses provided custom schemas
            
        kvp_model_name (str | None): The LLM model identifier for KVP extraction.
            Examples: "watsonx/mistralai/mistral-medium-2505"
            Default: None (uses system default model)
            
        kvp_force_schema_name (str | None): Forces the KVP extractor to use a specific
            schema by its document_type name, bypassing automatic schema selection.
            Useful when you know the exact document type and want to skip classification.
            Default: None (automatic schema selection based on document content)
            
        kvp_enable_text_hints (bool | None): Controls whether to provide text and layout
            information extracted from the document to the LLM during KVP extraction.
            - True: LLM receives both page image and extracted text/layout (recommended)
            - False: LLM relies only on the page image
            Default: True (better accuracy with text hints)
            
        plain_text_reading_order (PlainTextReadingOrder): Determines how text is ordered
            when extracting plain text from the document:
            - block_structure: Respects document layout blocks (default, recommended)
            - simple_line: Simple line-by-line reading order
            Default: PlainTextReadingOrder.block_structure
            
        document_structure (bool): Controls whether to extract and return the complete
            document structure (sections, paragraphs, tables, lists, images, etc.).
            - True: Returns full structure in AssemblyJsonOutput format
            - False: Returns only plain text (faster, smaller response)
            Default: False
            
        output_format (DocProcOutputFormat): Specifies the response format:
            - docref: Returns a reference URL to a file containing results (default)
              Response type: TextExtractionResponse
            - object: Returns results as inline JSON object
              Response type: TextExtractionObjectResponse
            Default: DocProcOutputFormat.docref
    
    Inherited Attributes (from DocProcCommonNodeSpec):
        task (DocProcTask): The document processing operation type
            Default: DocProcTask.text_extraction
        enable_hw (bool): Enable handwritten text recognition
            Default: False
    
    Inherited Attributes (from NodeSpec):
        name (str): Unique identifier for the node
        display_name (str | None): Human-readable name
        description (str | None): Node description
        input_schema (ToolRequestBody | SchemaRef | None): Input schema definition
        output_schema (ToolResponseBody | SchemaRef | None): Output schema definition
    '''    
    kvp_schemas: List[DocProcKVPSchema] | None = Field(
        title='KVP schemas',
        description="Optional list of key-value pair schemas for LLM-based extraction. "
                   "None = no KVP extraction, [] = use internal schemas, "
                   "[schema1, schema2, ...] = use custom schemas. Each schema defines "
                   "document type, fields to extract, and extraction instructions.",
        default=None)
    kvp_model_name: str | None = Field(
        title='KVP Model Name',
        description="LLM model identifier for key-value pair extraction. "
                   "Examples: 'meta-llama/llama-3-2-11b-vision-instruct', 'gpt-4-vision'. "
                   "None uses the system default model. Choose based on accuracy needs "
                   "and performance requirements.",
        default=None
    )
    kvp_force_schema_name: str | None = Field(
        title='KVP Force Schema Name',
        description="Forces the KVP extractor to use a specific schema by its document_type "
                   "name, bypassing automatic schema selection. Use when document type is "
                   "known in advance to improve performance and accuracy. None enables "
                   "automatic schema selection based on document content.",
        default=None
    )
    kvp_enable_text_hints: bool | None = Field(
        title='KVP Enable Text Hints',
        description="Determines whether to provide extracted text and layout information "
                   "to the LLM during KVP extraction, in addition to the page image. "
                   "True (recommended) = LLM receives both image and text hints for better "
                   "accuracy. False = LLM relies only on page image. Text hints significantly "
                   "improve extraction quality with minimal performance impact.",
        default=True
    )
    plain_text_reading_order : PlainTextReadingOrder = Field(
        default=PlainTextReadingOrder.block_structure,
    )
    document_structure: bool = Field(
        title="Document Structure",
        default=False,
        description="Requests the complete document structure computed by Watson Document "
                   "Understanding (WDU) to be returned. When True, the response includes "
                   "hierarchical structure (sections, paragraphs, tables, lists, images, etc.) "
                   "with bounding boxes and relationships. When False, only plain text is "
                   "extracted (faster, smaller response). Set to True when structural analysis "
                   "or spatial information is needed."
    )
    output_format: DocProcOutputFormat = Field(
        title="Output Format",
        default=DocProcOutputFormat.docref, 
        description="Output format for document processing results. "
                   "'docref' (default) returns a URL reference to a file containing results "
                   "(TextExtractionResponse). 'object' returns results as inline JSON "
                   "(TextExtractionObjectResponse). Use 'docref' for large documents or when "
                   "results will be stored/processed separately. Use 'object' for small documents "
                   "or immediate inline processing."
    )
    
    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "docproc"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        model_spec["document_structure"] = self.document_structure
        model_spec["task"] = self.task
        if self.plain_text_reading_order != PlainTextReadingOrder.block_structure:
            model_spec["plain_text_reading_order"] = self.plain_text_reading_order
        if self.kvp_schemas is not None:
            model_spec["kvp_schemas"] = self.kvp_schemas
        if self.kvp_model_name is not None:
            model_spec["kvp_model_name"] = self.kvp_model_name
        if self.kvp_force_schema_name is not None:
            model_spec["kvp_force_schema_name"] = self.kvp_force_schema_name
        if self.kvp_enable_text_hints is not None:
            model_spec["kvp_enable_text_hints"] = self.kvp_enable_text_hints
        if self.output_format != DocProcOutputFormat.docref:
            model_spec["output_format"] = self.output_format
        return model_spec

class StartNodeSpec(NodeSpec):
    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "start"

class EndNodeSpec(NodeSpec):
    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "end"

class NodeErrorHandlerConfig(BaseModel):
    error_message: Optional[str] = None
    max_retries: Optional[int] = None
    retry_interval: Optional[int] = None
        
    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        if self.error_message:
            model_spec["error_message"] = self.error_message
        if self.max_retries:
            model_spec["max_retries"] = self.max_retries
        if self.retry_interval:
            model_spec["retry_interval"] = self.retry_interval
        return model_spec

class ToolNodeSpec(NodeSpec):
    tool: Union[str, ToolSpec, None] = Field(default = None, description="the tool to use")
    error_handler_config: Optional[NodeErrorHandlerConfig] = None

    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "tool"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        if self.error_handler_config:
            model_spec["error_handler_config"] = self.error_handler_config.to_json()  
        if self.tool:
            if isinstance(self.tool, ToolSpec):
                model_spec["tool"] = self.tool.model_dump(exclude_defaults=True, exclude_none=True, exclude_unset=True)
            else:
                model_spec["tool"] = self.tool
        return model_spec
    
class ScriptNodeSpec(NodeSpec):
     fn: str = Field(default = None, description="the script to execute")

     def __init__(self, **data):
         super().__init__(**data)
         self.kind = "script"

     def to_json(self) -> dict[str, Any]:
         model_spec = super().to_json()
         if self.fn:
             model_spec["fn"] = self.fn
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
    Text = "text"
    Date = "date"
    DateTime = "datetime"
    Time = "time"
    Number = "number"
    File = "file"
    Boolean = "boolean"
    Object = "object"
    Choice = "any"
    List = "array"  # used to display list output
    DateRange = "date-range"
    Field = "field"
    MultiChoice = "array"
    Array = "array"  # this is a duplicate of List

    @staticmethod
    def str_to_kind(kind: str) -> "UserFieldKind":
        # convert a string to the corresponding Kind
        if kind == "text":
            return UserFieldKind.Text
        elif kind == "date":
            return UserFieldKind.Date
        elif kind == "datetime":
            return UserFieldKind.DateTime
        elif kind == "time":
            return UserFieldKind.Time
        elif kind == "number":
            return UserFieldKind.Number
        elif kind == "file":
            return UserFieldKind.File
        elif kind == "boolean":
            return UserFieldKind.Boolean
        elif kind == "object":
            return UserFieldKind.Object
        elif kind == "any":
            return UserFieldKind.Choice
        elif kind == "list":
            return UserFieldKind.List
        elif kind == "date-range":
            return UserFieldKind.DateRange
        elif kind == "field":
            return UserFieldKind.Field
        elif kind == "array":
            return UserFieldKind.List
        else:
            raise ValueError(f"Invalid kind: {kind}")

    @staticmethod
    def str_to_code(kind: str) -> str:
        # convert a string to the corresponding Kind
        if kind == "text":
            return "UserFieldKind.Text"
        elif kind == "date":
            return "UserFieldKind.Date"
        elif kind == "datetime":
            return "UserFieldKind.DateTime"
        elif kind == "time":
            return "UserFieldKind.Time"
        elif kind == "number":
            return "UserFieldKind.Number"
        elif kind == "file":
            return "UserFieldKind.File"
        elif kind == "boolean":
            return "UserFieldKind.Boolean"
        elif kind == "object":
            return "UserFieldKind.Object"
        elif kind == "any":
            return "UserFieldKind.Choice"
        elif kind == "list":
            return "UserFieldKind.List"
        elif kind == "date-range":
            return "UserFieldKind.DateRange"
        elif kind == "field":
            return "UserFieldKind.Field"
        elif kind == "array":
            return "UserFieldKind.List"
        else:
            raise ValueError(f"Invalid kind: {kind}")



class UserField(BaseModel):
    name: str
    kind: UserFieldKind = UserFieldKind.Text
    display_name: str | None = None
    direction: str | None = None
    text: str | None = None
    input_map: Any | None = None
    input_schema: ToolRequestBody | SchemaRef | JsonSchemaObject | None = None
    output_schema: ToolResponseBody | SchemaRef | JsonSchemaObject | None = None
    uiSchema: dict[str, Any] | None = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.input_map:
            from .data_map import DataMapSpec
            if isinstance(self.input_map, dict):
                self.input_map = DataMapSpec(**self.input_map)

    def _fixup_input_output_schema_for_form(self):
        if self.input_schema is None and self.output_schema is None:
            field_kind = self.kind.value
            if self.direction == "output" and self.kind.value == "text":
                field_kind = "message"
            schemas = clone_form_schema(field_kind)
            if self.direction == "output" and self.kind == UserFieldKind.File:
                # we need to override File download
                schemas["input"] = {
                    "properties": {"value": {"type": "string", "format": "wxo-file"}},
                    "required": ["value"]
                }
            self.input_schema = schemas["input_schema"] if "input_schema" in schemas else None
            self.output_schema = schemas["output_schema"] if "output_schema" in schemas else None
        
        if self.input_schema and isinstance(self.input_schema, JsonSchemaObject):
            self.input_schema = _get_tool_request_body(self.input_schema)
        if self.output_schema and isinstance(self.output_schema, JsonSchemaObject):
            self.output_schema = _get_tool_response_body(self.output_schema)

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        if self.name:
            model_spec["name"] = self.name
        if self.kind:
            model_spec["kind"] = self.kind.value
        if self.text:
            model_spec["text"] = self.text
        if self.direction:
            model_spec["direction"] = self.direction
        if self.display_name:
            model_spec["display_name"] = self.display_name      
        if self.input_map:
            # workaround for circular dependency related to Assigments in the Datamap module
            from .data_map import DataMapSpec, DataMap
            if self.input_map and not isinstance(self.input_map, DataMapSpec):
                if isinstance(self.input_map, DataMap):
                    self.input_map = DataMapSpec(spec=self.input_map)
                else:
                    raise ValueError("input_map must be of type DataMapSpec or DataMap")
            if self.input_map and isinstance(self.input_map, DataMapSpec):
                model_spec["input_map"] = self.input_map.to_json() 

        self._fixup_input_output_schema_for_form()

        if self.input_schema:
            model_spec["input_schema"] = _to_json_from_input_schema(self.input_schema)
        if self.output_schema:
            if isinstance(self.output_schema, ToolResponseBody):
                if self.output_schema.type != 'null':
                    model_spec["output_schema"] = _to_json_from_output_schema(self.output_schema)
            else:
                model_spec["output_schema"] = _to_json_from_output_schema(self.output_schema)
        if self.uiSchema:
            model_spec["uiSchema"] = self.uiSchema   
        return model_spec

class UserFormButton(BaseModel):
    name: str
    kind: Literal["submit", "cancel"]
    display_name: str | None = None
    visible: bool = True
    edge_id: str | None = None

    def __init__(self, **data):
        super().__init__(**data)

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        if self.name:
            model_spec["name"] = self.name
        if self.kind:
            model_spec["kind"] = self.kind
        if self.display_name:
            model_spec["display_name"] = self.display_name
        if self.visible:
            model_spec["visible"] = self.visible
        if self.edge_id: 
            model_spec["edge_id"] = self.edge_id
        return model_spec    

class UserForm(BaseModel):

    name: str
    kind: str = "form"
    display_name: str | None = None
    instructions: str | None = None
    fields: list[UserField] = []  
    jsonSchema: JsonSchemaObject | SchemaRef | None = None
    buttons: list[UserFormButton]

    @field_validator("buttons", mode="before")
    def default_buttons(cls, v):
        if not v:
            return [
                UserFormButton(name="submit", kind="submit", display_name="Submit", visible=True),
                UserFormButton(name="cancel", kind="cancel", display_name="Cancel", visible=True),
            ]
        return v
        
    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "form"
        
        # Initialize jsonSchema if not provided
        if not hasattr(self, 'jsonSchema') or self.jsonSchema is None:
            self.jsonSchema = JsonSchemaObject( # pyright: ignore[reportCallIssue]
                type='object', 
                properties={}, 
                required=[], 
                description=self.instructions if hasattr(self, 'instructions') else None
            )
        
        if not hasattr(self, 'fields') or self.fields is None:
            self.fields = []

        if not hasattr(self, 'buttons') or self.buttons is None:
            self.buttons = [
                UserFormButton(name="submit", kind="submit", display_name="Submit", visible=True),
                UserFormButton(name="cancel", kind="cancel", display_name="Cancel", visible=True),
            ]

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        if self.name:
            model_spec["name"] = self.name
        if self.kind:
            model_spec["kind"] = self.kind
        if self.display_name:
            model_spec["display_name"] = self.display_name
        if self.fields and len(self.fields) > 0:
            model_spec["fields"] = [field.to_json() for field in self.fields]
        if self.jsonSchema:
            model_spec["jsonSchema"] = _to_json_from_input_schema(self.jsonSchema)
        if self.buttons and len(self.buttons) > 0:
            model_spec["buttons"] = [button.to_json() for button in self.buttons]     

        return model_spec

    def add_or_replace_field(self, name: str, userfield: UserField):
        """
        Replace an existing field (by name) in self.fields or append a new one.
        """
        # fixup input and output schema for fields
        if userfield is None:
            return

        userfield._fixup_input_output_schema_for_form()

        for i, field in enumerate(self.fields):
            if field.name == name:
                self.fields[i] = userfield
                return
        # if no match found, append it
        self.fields.append(userfield)

    def text_input_field(
            self,
            name: str,
            label: str | None = None,
            required: bool = False,
            single_line: bool = True,
            placeholder_text: str| None = None,
            help_text: str | None = None,
            input_map: Any| None=None,
    ) -> UserField:
        # Use the template system from utils
        schemas = clone_form_schema("text", {
            "ui": {
                "ui:title": label if label is not None else name,
                "ui:widget": "TextWidget" if single_line else "TextareaWidget"
            }
        })
        
        # Add additional UI properties if provided
        if help_text is not None:
            schemas["ui_schema"]["ui:help"] = help_text
        if placeholder_text is not None:
            schemas["ui_schema"]["ui:placeholder"] = placeholder_text
        
        # Create the field
        userfield = UserField(
            name=name,
            kind=UserFieldKind.Text,
            display_name=label,
            direction="input",
            input_map=input_map,
            output_schema=schemas["output_schema"],
            input_schema=schemas["input_schema"],
            uiSchema=schemas["ui_schema"],
        )
        
        # Add or replace the field
        self.add_or_replace_field(name, userfield)
        
        # Update JSON schema
        self.jsonSchema.properties[name] = {"type": "string", "title": label}
        if required and name not in self.jsonSchema.required:
            self.jsonSchema.required.append(name)

        return userfield

    def boolean_input_field(
            self,
            name: str,
            label: str | None = None,
            single_checkbox: bool = True,
            input_map: Any| None=None,
            true_label: str = "True",
            false_label: str = "False"
    ) -> UserField:
        # Use the template system from utils
        widget = "CheckboxWidget" if single_checkbox else "RadioWidget"
        
        ui_config = {
            "ui:title": label if label is not None else name,
            "ui:widget": widget
        }
        
        if widget == "CheckboxWidget":
            ui_config["ui:options"] = {"label": False}
        
        schemas = clone_form_schema("boolean", {"ui": ui_config})
        
        # Set up default input_map if not provided
        if input_map is None:
            input_map = DataMap(maps=[
                Assignment(
                    target_variable=f"self.input.default",
                    value_expression="False",
                    metadata={"assignmentType": "literal"}
                )
            ])
        
        # Create the field
        userfield = UserField(
            name=name,
            kind=UserFieldKind.Boolean,
            display_name=label,
            direction="input",
            input_map=input_map,
            output_schema=schemas["output_schema"],
            input_schema=schemas["input_schema"],
            uiSchema=schemas["ui_schema"],
        )
        
        # Add or replace the field
        self.add_or_replace_field(name, userfield)
        
        # Update JSON schema
        self.jsonSchema.properties[name] = {
            "type": "boolean",
                "oneOf": [
                    {"const": True, "title": true_label},
                    {"const": False, "title": false_label}
            ],
            "title": label
        }

        return userfield

    def date_range_input_field(
            self,
            name: str,
            label: str | None = None,
            required: bool = False,
            start_date_label:str | None = None,
            end_date_label:str | None = None,
            default_start: Any| None = None,
            default_end: Any| None = None
    ) -> UserField:
        ensure_datamap(default_start, "default_start")
        ensure_datamap(default_end, "default_end")
        
        # Use the template system from utils
        schemas = clone_form_schema("date_range", {
            "ui": {
                "ui:title": label if label is not None else name,
                "ui:widget": "DateWidget",
                "format": "YYYY-MM-DD",
                "ui:options": {"range": True},
                "ui:order": ["start", "end"]
            }
        })
        
        # Add additional UI properties if provided
        if start_date_label:
            schemas["ui_schema"]["ui:start_label"] = start_date_label
        if end_date_label:
            schemas["ui_schema"]["ui:end_label"] = end_date_label
        
        # Set up input_map
        if default_start:
            input_map = default_start
            add_assignment(input_map, default_end)
        else:
            input_map = default_end
        
        # Create the field
        userfield = UserField(
            name=name,
            kind=UserFieldKind.DateRange,
            display_name=label,
            direction="input",
            input_schema=schemas["input_schema"],
            output_schema=schemas["output_schema"],
            input_map=input_map,
            uiSchema=schemas["ui_schema"],
        )
        
        # Add or replace the field
        self.add_or_replace_field(name, userfield)
        
        # Update JSON schema
        self.jsonSchema.properties[name] = {
            "type": "array",
            "items": {"type": "string", "format": "date"},
            "title": label
        }
        
        if required and name not in self.jsonSchema.required:
            self.jsonSchema.required.append(name)

        return userfield
         
    def date_input_field(
            self,
            name: str,
            label: str | None = None,
            required: bool = False,
            initial_value: Any| None=None,
    ) -> UserField:
        # Use the template system from utils
        schemas = clone_form_schema("date", {
            "ui": {
                "ui:title": label if label is not None else name,
                "ui:widget": "DateWidget",
                "format": "YYYY-MM-DD"
            }
        })
        
        # Create the field
        userfield = UserField(
            name=name,
            kind=UserFieldKind.Date,
            display_name=label,
            direction="input",
            input_schema=schemas["input_schema"],
            output_schema=schemas["output_schema"],
            input_map=initial_value,
            uiSchema=schemas["ui_schema"],
        )
        
        # Add or replace the field
        self.add_or_replace_field(name, userfield)
        
        # Update JSON schema
        self.jsonSchema.properties[name] = {
            "type": "string",
            "title": label,
            "format": "date"
        }
        
        if required and name not in self.jsonSchema.required:
            self.jsonSchema.required.append(name)

        return userfield

    def choice_input_field(
            self,
            name: str,
            label: str | None = None,
            required: bool = False,
            source: Any| None=None,
            show_as_dropdown: bool = True,
            dropdown_item_column: str | None = None,
            placeholder_text: str | None = None,
            initial_value: Any | None = None,
            columns: dict[str, str]| None = None,
            isMultiSelect: bool = False,
    ) -> UserField:
        # Use the template system from utils
        widget = "MultiselectDropdown" if (show_as_dropdown and isMultiSelect) else \
                 "ComboboxWidget" if (show_as_dropdown or columns is None) else \
                 "Table"
        
        ui_config = {
            "ui:title": label if label is not None else name,
            "ui:widget": widget,
            "ui:placeholder": placeholder_text
        }
        
        if widget == "Table":
            ui_config["ui:options"] = {"label": False}
        
        schemas = clone_form_schema("choice", {"ui": ui_config})
        
        # Validate inputs
        if source is None:
            raise TypeError("source must be provided")
        ensure_datamap(source, "source")
        ensure_datamap(initial_value, "initial value")
        
        # Configure source data mapping
        if show_as_dropdown and dropdown_item_column is not None:
            # Build a list of strings like "item.name", "item.address", etc.
            source.add(
                Assignment(
                    target_variable="self.input.display_text",
                    value_expression=f"item.{dropdown_item_column}"
                )
            )
        
        if not show_as_dropdown and columns is not None:
            # Build a list of strings like "item.name", "item.address", etc.
            item_fields = [f'item.{key}' for key in columns.keys()]
            # Convert that list into a JSON-style string list
            value_expression = "[" + ", ".join(f'"{field}"' for field in item_fields) + "]"
            # Create the assignment and add it to source
            source.add(
                Assignment(
                    target_variable="self.input.display_items",
                    value_expression=value_expression
                )
            )
        else:
            # If there are no columns, create the empty list
            source.add(
                Assignment(
                    target_variable="self.input.display_items",
                    value_expression="[]"
                )
            )
        
        # Add initial value if provided
        add_assignment(source, initial_value)

        # Create the field
        userfield = UserField(
            name=name,
            kind=UserFieldKind.MultiChoice if isMultiSelect else UserFieldKind.Choice,
            display_name=label,
            direction="input",
            input_schema=schemas["input_schema"],
            output_schema=schemas["output_schema"],
            input_map=source,
            uiSchema=schemas["ui_schema"],
        )
        
        # Add or replace the field
        self.add_or_replace_field(name, userfield)
        
        # Update JSON schema
        if isMultiSelect and columns is not None:
            properties = {}
            for key, val in columns.items():
                properties[key] = {
                    "type": "string",
                    "title": val if val else key  # use value if present, else fallback to key
                }
            self.jsonSchema.properties[name] = {
                "type": "array",
                "items": {"type": "string"},
                "properties": properties,
                "title": label
            }
        elif isMultiSelect:
            self.jsonSchema.properties[name] = {
                "type": "array",
                "items": {"type": "string"},
                "title": label
            }
        else:
            self.jsonSchema.properties[name] = {"title": label}

        if required and name not in self.jsonSchema.required:
            self.jsonSchema.required.append(name)

        return userfield

    def number_input_field(
            self,
            name: str,
            label: str | None = None,
            required: bool = False,
            is_integer: bool = True,
            help_text: str | None = None,
            initial_value: Any| None=None,
            minimum_value: Any | None=None,
            maximum_value: Any | None=None
    ) -> UserField:
        # Use the template system from utils
        schemas = clone_form_schema("number", {
            "ui": {
                "ui:title": label if label is not None else name,
                "ui:widget": "NumberWidget"
            }
        })
        
        # Add help text if provided
        if help_text is not None:
            schemas["ui_schema"]["ui:help"] = help_text
        
        # Validate inputs
        ensure_datamap(initial_value, "initial value")
        ensure_datamap(minimum_value, "minimum_value")
        ensure_datamap(minimum_value, "maximum_value")
        
        # Customize input schema based on parameters
        num_type = "integer" if is_integer else "number"
        
        # Build the input_map by computing all assignments from the initial_value, min and max value
        if initial_value is not None:
            add_assignment(initial_value, minimum_value)
            add_assignment(initial_value, maximum_value)
        elif minimum_value is not None:
            initial_value = minimum_value
            add_assignment(initial_value, maximum_value)
        elif maximum_value is not None:
            initial_value = maximum_value
        
        # Create the field
        userfield = UserField(
            name=name,
            kind=UserFieldKind.Number,
            display_name=label,
            direction="input",
            input_schema=schemas["input_schema"],
            output_schema=schemas["output_schema"],
            input_map=initial_value,
            uiSchema=schemas["ui_schema"],
        )
        
        # Add or replace the field
        self.add_or_replace_field(name, userfield)
        
        # Update JSON schema
        self.jsonSchema.properties[name] = {"type": num_type, "title": label}
        if required and name not in self.jsonSchema.required:
            self.jsonSchema.required.append(name)

        return userfield

    def file_upload_field(
            self,
            name: str,
            label: str | None = None,
            required: bool = False,
            instructions: str | None = None,
            button_label : str | None = None,
            allow_multiple_files: bool = False,
            file_max_size: int=10,
            supported_file_types : List[str] | None = None,
    ) -> UserField:
        # Use the template system from utils
        schemas = clone_form_schema("file", {
            "ui": {
                "ui:title": label if label is not None else name,
                "ui:widget": "FileUpload"
            }
        })
        
        # Add button label if provided
        if button_label:
            schemas["ui_schema"]["ui:upload_button_label"] = button_label
        
        # Customize output schema based on whether multiple files are allowed
        if allow_multiple_files:
            output_schema = JsonSchemaObject(
                type='object',
                properties={"value": {"type": "array", "items": {"type": "string", "format": "wxo-file"}}},
                required=["value"]
            )
        else:
            output_schema = schemas["output_schema"]
        
        # Create the field
        userfield = UserField(
            name=name,
            kind=UserFieldKind.File,
            display_name=label,
            direction="input",
            input_schema=schemas["input_schema"],
            output_schema=output_schema,
            uiSchema=schemas["ui_schema"],
            input_map=None
        )
        
        # Add or replace the field
        self.add_or_replace_field(name, userfield)
        
        # Update JSON schema
        self.jsonSchema.properties[name] = {
            "description": instructions,
            "items":{},
            "file_max_size": file_max_size,
            "multi": allow_multiple_files,
            "type": "array",
            "title": label,
            "file_types": supported_file_types
        }
        
        if required and name not in self.jsonSchema.required:
            self.jsonSchema.required.append(name)

        return userfield

    def message_output_field(
            self,
            name: str,
            label: str | None = None,
            message: str | None = None,
    ) -> UserField:
        # Use the template system from utils
        schemas = clone_form_schema("message", {
            "ui": {
                "ui:title": label if label is not None else name
            }
        })
        
        # Create the field
        userfield = UserField(
            name=name,
            kind=UserFieldKind.Text,
            display_name=label,
            direction="output",
            input_schema=schemas["input_schema"],
            uiSchema=schemas["ui_schema"],
            text=message,
            input_map=None
        )
        
        # Add or replace the field
        self.add_or_replace_field(name, userfield)
        
        # Update JSON schema
        self.jsonSchema.properties[name] = {"type": "string", "title": label}

        return userfield

    def field_output_field(
            self,
            name: str,
            label: str | None = None,
            source: Any | None = None,
    ) -> UserField:
        ensure_datamap(source, "source")
        
        # Use the template system from utils
        schemas = clone_form_schema("field", {
            "ui": {
                "ui:title": label if label is not None else name
            }
        })
        
        # Create the field
        userfield = UserField(
            name=name,
            kind=UserFieldKind.Field,
            display_name=label,
            direction="output",
            input_schema=schemas["input_schema"],
            uiSchema=schemas["ui_schema"],
            input_map=source
        )
        
        # Add or replace the field
        self.add_or_replace_field(name, userfield)
        
        # Update JSON schema
        self.jsonSchema.properties[name] = {"type": "string", "title": label}

        return userfield

    def list_output_field(
            self,
            name: str,
            label: str | None = None,
            source: Any | None = None,
            # A dictionary or columns names and their corresponding labels
            columns: dict[str, str]| None = None
    ) -> UserField:
        ensure_datamap(source, "source")
        isBulletList = columns is None
        widget = "BulletList" if isBulletList else "Table"
        
        ui_config = {
            "ui:title": label if label is not None else name,
            "ui:widget": widget
        }
        
        if widget == "Table":
            ui_config["ui:options"] = {"label": False}
        
        # Use the template system from utils
        schemas = clone_form_schema("list", {"ui": ui_config})
        
        # Configure input schema based on list type
        if not isBulletList:
            schemas["input_schema"].properties["display_items"] = {"type": "array", "items": {}}
        
        # Configure source data mapping
        if columns is not None:
            # Build a list of strings like "item.name", "item.address", etc.
            item_fields = [f'item.{key}' for key in columns.keys()]
            # Convert into a JSON-style string list
            value_expression = "[" + ", ".join(f'"{field}"' for field in item_fields) + "]"
            # Create the assignment and add it to source
            source.add(
                Assignment(
                    target_variable="self.input.display_items",
                    value_expression=value_expression,
                    metadata={"assignmentType": "variable"}
                )
            )
        else:
            # If there are no columns create the empty list
            source.add(
                Assignment(
                    target_variable="self.input.display_items",
                    value_expression="[]"
                )
            )
        
        # Create the field
        userfield = UserField(
            name=name,
            kind=UserFieldKind.List,
            display_name=label,
            direction="output",
            input_schema=schemas["input_schema"],
            uiSchema=schemas["ui_schema"],
            input_map=source
        )
        
        # Add or replace the field
        self.add_or_replace_field(name, userfield)
        
        # Update JSON schema based on list type
        if isBulletList:
            self.jsonSchema.properties[name] = {
                "type": "array",
                "items": {"type": "string"},
                "title": label
            }
        else:
            properties = {}
            if columns is not None:
                for key, val in columns.items():
                    properties[key] = {
                        "type": "string",
                        "title": val if val else key  # use value if present, else fallback to key
                    }
            self.jsonSchema.properties[name] = {
                "type": "array",
                "items": {"type": "string"},
                "properties": properties,
                "title": label
            }

        return userfield
    
    def list_input_field(
            self,
            name: str,
            label: str | None = None,
            isRowAddable: bool = False,
            isRowDeletable: bool= False,
            default: Any | None = None,
            # A dictionary or columns names and their corresponding labels
            columns: dict[str, str]| None = None
    ) -> UserField:
        ensure_datamap(default, "default")

        # Use the template system from utils
        schemas = clone_form_schema("list_input")
        
        # Configure input schema based on list type
        schemas["input_schema"].properties["display_items"] = {"type": "array", "items": {}}
        
        # Configure source data mapping
        if columns is not None:
            # Build a list of strings like "item.name", "item.address", etc.
            item_fields = [f'item.{key}' for key in columns.keys()]
            # Convert into a JSON-style string list
            value_expression = "[" + ", ".join(f'"{field}"' for field in item_fields) + "]"
            # Create the assignment and add it to source
            default.add(
                Assignment(
                    target_variable="self.input.display_items",
                    value_expression=value_expression,
                    metadata={"assignmentType": "variable"}
                )
            )
        else:
            # If there are no columns create the empty list
            default.add(
                Assignment(
                    target_variable="self.input.display_items",
                    value_expression="[]"
                )
            )
        
        # Create the field
        userfield = UserField(
            name=name,
            kind=UserFieldKind.List,
            display_name=label,
            direction="input",
            input_schema=schemas["input_schema"],
            output_schema=schemas["output_schema"],
            uiSchema=schemas["ui_schema"],
            input_map=default
        )
        
        # Add or replace the field
        self.add_or_replace_field(name, userfield)
        
        # Update JSON schema based on list type
        properties = {}
        if columns is not None:
            for key, val in columns.items():
                properties[key] = {
                    "type": "string",
                    "title": val if val else key  # use value if present, else fallback to key
                }
        self.jsonSchema.properties[name] = {
            "type": "array",
            "items": {"type": "string"},
            "properties": properties,
            "title": label,
            "isRowAddable": isRowAddable,
            "isRowDeletable": isRowDeletable
        }

        if name not in self.jsonSchema.required:
            self.jsonSchema.required.append(name)
        
        return userfield

    def file_download_field(
            self,
            name: str,
            label: str | None = None,
            source_file: Any | None = None,
    ) -> UserField:
        ensure_datamap(source_file, "source_file")
        
        # Create a custom schema since there's no direct template for file download
        # We'll use the file template but customize it for download
        schemas = clone_form_schema("file", {
            "input": {
                "properties": {"value": {"type": "string", "format": "wxo-file"}},
                "required": ["value"]
            },
            "ui": {
                "ui:title": label if label is not None else name,
                "ui:widget": "FileDownloadWidget"
            }
        })
        
        # Create the field
        userfield = UserField(
            name=name,
            kind=UserFieldKind.File,
            display_name=label,
            direction="output",
            input_schema=schemas["input_schema"],
            uiSchema=schemas["ui_schema"],
            input_map=source_file
        )
        
        # Add or replace the field
        self.add_or_replace_field(name, userfield)
        
        # Update JSON schema - use model_construct to bypass validation for custom "file" type
        # pyright: ignore[reportCallIssue]
        self.jsonSchema.properties[name] = JsonSchemaObject.model_construct(type="file", title=label)

        return userfield

class UserNodeSpec(NodeSpec):
    owners: Sequence[str] | None = None
    fields: list[UserField] | None = None
    form: UserForm | None = None

    def __init__(self, **data):
        super().__init__(**data)
        self.fields = []
        self.kind = "user"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()

        # UserNode input and output schema will always be empty
        if "input_schema" in model_spec:
            del model_spec["input_schema"]
        if "output_schema" in model_spec:
            del model_spec["output_schema"]

        if self.owners:
            model_spec["owners"] = self.owners
        if self.fields and len(self.fields) > 0:
            model_spec["fields"] = [field.to_json() for field in self.fields]
        else : 
             model_spec["fields"] = []
        if self.form:
            model_spec["form"] = self.form.to_json()

        return model_spec

    def field(self, 
              name: str, 
              kind: UserFieldKind, 
              text: str | None = None,
              display_name: str | None = None, 
              input_map: Any | None = None,
              direction: str | None = None,
              input_schema: ToolRequestBody | SchemaRef | None = None,
              output_schema: ToolResponseBody | SchemaRef | None = None) -> UserField:
        
        # workaround for circular dependency related to Assigments in the Datamap module
        from .data_map import DataMapSpec, DataMap
        if input_map and not isinstance(input_map, (DataMap, DataMapSpec)):
            raise TypeError("input_map must be an instance of DataMap or DataMapSpec")

        if input_map and isinstance(input_map, DataMap):
            input_map = DataMapSpec(spec = input_map)

        userfield: UserField = UserField(name=name, 
                                         kind=kind, 
                                         display_name=display_name, 
                                         text=text,
                                         direction=direction,
                                         input_map=input_map if input_map is not None else None,
                                         input_schema=input_schema,
                                         output_schema=output_schema)

        # find the index of the field
        if self.fields is None:
            self.fields = [userfield]
        elif self.fields is not None and len(self.fields) > 0:
            if (self.fields[0].name == name):
                self.fields[0] = userfield
            else:
                raise ValueError(f"There can be only one standalone field in a user node.")
        else:
            self.fields = [userfield]

    def get_or_create_form(self, name: str, display_name: str | None = None, instructions: str | None = None) -> UserForm:

        if hasattr(self, "form") and self.form is not None:
            self.form.name = name
            self.form.display_name = display_name
            self.form.jsonSchema.description = instructions
        else:
            self.form = UserForm(name=name, 
                              kind="form", 
                              display_name=display_name, 
                              instructions=instructions,
                              buttons=None) 
        return self.form


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
    
class PromptExample(BaseModel):
    input: Optional[str] = None
    expected_output: Optional[str] = None
    enabled: bool

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        if self.input:
            model_spec["input"] = self.input
        if self.expected_output:
            model_spec["expected_output"] = self.expected_output
        if self.enabled:
            model_spec["enabled"] = self.enabled
        return model_spec



class PromptNodeSpec(NodeSpec):
    system_prompt: str | list[str]
    user_prompt: str | list[str]
    prompt_examples: Optional[list[PromptExample]] = None
    llm: Optional[str] = None
    llm_parameters: Optional[PromptLLMParameters] = None
    error_handler_config: Optional[NodeErrorHandlerConfig] = None
    metadata: dict[str, Any] | None = None
    test_input_data: dict[str, Any] | None = None

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
        if self.error_handler_config:
            model_spec["error_handler_config"] = self.error_handler_config.to_json()            
        if self.prompt_examples:
            model_spec["prompt_examples"] = []
            for example in self.prompt_examples:
                model_spec["prompt_examples"].append(example.to_json())
        if self.metadata:
            model_spec["metadata"] = self.metadata
        if self.test_input_data:
            model_spec["test_input_data"] = self.test_input_data
        return model_spec
    
class TimerNodeSpec(NodeSpec):
    delay: int 
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.kind = "timer"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        if self.delay:
            model_spec["delay"] = self.delay
        return model_spec

class Expression(BaseModel):
    '''An expression could return a boolean or a value'''
    expression: str = Field(description="A python expression to be run by the flow engine")

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        model_spec["expression"] = self.expression;
        return model_spec
    
class NodeIdCondition(BaseModel):
    '''One Condition contains an expression, a node_id that branch should go to when expression is true, and a default indicator. '''
    expression: Optional[str] = Field(description="A python expression to be run by the flow engine", default=None)
    node_id: str = Field(description="ID of the node in the flow that branch node should go to")
    default: bool = Field(description="Boolean indicating if the condition is default case")
    metadata: Optional[dict[str, Any]] = Field(description="Metadata about the condition", default=None)

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        if self.expression:
            model_spec["expression"] = self.expression
        model_spec["node_id"] = self.node_id
        model_spec["default"] = self.default
        return model_spec


class EdgeIdCondition(BaseModel):
    '''One Condition contains an expression, an edge_id that branch should go to when expression is true, and a default indicator. '''
    expression: Optional[str] = Field(description="A python expression to be run by the flow engine", default=None)
    edge_id: str = Field(description="ID of the edge in the flow that branch node should go to")
    default: bool = Field(description="Boolean indicating if the condition is default case")
    metadata: Optional[dict[str, Any]] = Field(description="Metadata about the condition", default=None)

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        if self.expression:
            model_spec["expression"] = self.expression
        model_spec["edge_id"] = self.edge_id
        model_spec["default"] = self.default
        return model_spec

class Conditions(BaseModel):
    '''One Conditions is an array represents the if-else conditions of a complex branch'''
    conditions: List[Union[NodeIdCondition, EdgeIdCondition]]

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        condition_list = []
        for condition in self.conditions:
            if isinstance(condition, NodeIdCondition):
                condition_list.append(NodeIdCondition.model_validate(condition).to_json())
            elif isinstance(condition, EdgeIdCondition):
                condition_list.append(EdgeIdCondition.model_validate(condition).to_json())
            else:
                raise ValueError(f"Invalid condition type: {type(condition)}")
        model_spec["conditions"] = condition_list
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
    evaluator: Expression | Conditions
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
    
class FlowContextWindow(BaseModel):
    '''Indicate the context window setting for the LLM model used by the flow'''
    compression_threshold: Optional[int] = Field(description="Trigger compression when the context window reaches to a specific amount of tokens", default=None)
    compression_instruction: Optional[str] = Field(description="An instruction being used for the compression", default=None)
    max_tokens: Optional[int] = Field(description="The maximum number of token supported by the LLM model", default=None)
    allow_compress: Optional[bool] = Field(description="Indicates whether compression is allowed", default=True)

class Dimensions(BaseModel):
    width: float
    height: float

class FlowSpec(NodeSpec):
    # who can initiate the flow
    initiators: Sequence[str] = [ANY_USER]
    schedulable: bool = False

    # flow can have private schema
    private_schema: JsonSchemaObject | SchemaRef | None = None
    dimensions: Dimensions | None = None

    context_window: FlowContextWindow | None = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.kind = "flow"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        if self.initiators:
            model_spec["initiators"] = self.initiators
        if self.dimensions:
            model_spec["dimensions"] = self.dimensions
        if self.schedulable:
            model_spec["schedulable"] = self.schedulable
        if self.private_schema:
            model_spec["private_schema"] = _to_json_from_input_schema(self.private_schema)
        if self.context_window:
            model_spec["context_window"] = self.context_window.model_dump()
        
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
        self.kind = "user_flow"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        if self.initiators:
            model_spec["owners"] = self.initiators

        return model_spec

class ForeachPolicy(Enum):
 
    SEQUENTIAL = 1
    PARALLEL = 2

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
            my_dict["item_schema"] = self.item_schema.model_dump(exclude_defaults=True, exclude_none=True, exclude_unset=True, by_alias=True)

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
    input: dict[str, Any] | Any = Field(default_factory=dict)
    output: dict[str, Any] | Any = Field(default_factory=dict)
    private: dict[str, Any] | Any = Field(default_factory=dict)

class FlowContext(BaseModel):
 
    name: str | None = None # name of the flow
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
    assignee: str | None = None # id of the assignee 
    task_name: str | None = None # name of the current task, a task is an instance of a node
    task_display_name: str | None = None # display name of the current task
    task_kind: str | None = None # type of the current task
 
    def get(self, key: str) -> Any:
     
        if key in self.data:
            return self.data[key]

        if self.parent_context:
            pc = cast(FlowContext, self.parent_context)
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


# class Assignment(BaseModel):
#     '''
#     This class represents an assignment in the system.  Specify an expression that 
#     can be used to retrieve or set a value in the FlowContext

#     Attributes:
#         target (str): The target of the assignment.  Always assume the context is the current Node. e.g. "name"
#         source (str): The source code of the assignment.  This can be a simple variable name or a more python expression.  
#             e.g. "node.input.name" or "=f'{node.output.name}_{node.output.id}'"

#     '''
#     target_variable: str
#     value_expression: str | None = None
#     has_no_value: bool = False
#     default_value: Any | None = None
#     metadata: dict = Field(default_factory=dict[str, Any])

class Style(BaseModel):
    style_id: str = Field(default="", description="Style Identifier which will be used for reference in other objects")
    font_size: str = Field(default="", description="Font size")
    font_name: str = Field(default="", description="Font name")
    is_bold: str = Field(default="", description="Whether or not the the font is bold")
    is_italic: str = Field(default="", description="Whether or not the the font is italic")

class PageMetadata(BaseModel):
    page_number: Optional[int] = Field(default=None, description="Page number, starting from 1")
    page_image_width: Optional[int] = Field(default=None, description="Width of the page in pixels, assuming the page is an image with default 72 DPI")
    page_image_height: Optional[int] = Field(default=None, description="Height of the page in pixels, assuming the page is an image with default 72 DPI")
    dpi: Optional[int] = Field(default=None, description="The DPI to use for the page image, as specified in the input to the API")
    document_type: Optional[str] = Field(default="", description="Document type")

class Metadata(BaseModel):
    num_pages: int = Field(description="Total number of pages in the document")
    title: Optional[str] = Field(default=None, description="Document title as obtained from source document")
    language: Optional[str] = Field(default=None, description="Determined by the lang specifier in the <html> tag, or <meta> tag")
    url: Optional[str] = Field(default=None, description="URL of the document")
    keywords: Optional[str] = Field(default=None, description="Keywords associated with document")
    author: Optional[str] = Field(default=None, description="Author of the document")
    publication_date: Optional[str] = Field(default=None, description="Best effort bases for a publication date (may be the creation date)")
    subject: Optional[str] = Field(default=None, description="Subject as obtained from the source document")
    charset: str = Field(default="", description="Character set used for the output")
    output_tokens_flag: Optional[bool] = Field(default=None, description="Whether individual tokens are output, as specified in the input to the API")
    output_bounding_boxes_flag: Optional[bool] = Field(default=None, description="Whether bounding boxes are output, as requested in the input to the API")
    pages_metadata: Optional[List[PageMetadata]] = Field(default=[], description="List of page-level metadata objects")

class Section(BaseModel):
    id: str = Field(default="", description="Unique identifier for the section")
    parent_id: str = Field(default="", description="Unique identifier which denotes parent of this structure")
    children_ids: List[str] = Field(default="", description="Unique Ids of first level children structures under this structure in correct sequence")
    section_number: str = Field(default="", description="Section identifier identified in the document")
    section_level: str = Field(default="", description="Nesting level of section identified in the document")
    bbox_list: Optional[List[DocProcBoundingBox]] = Field(default=None, description="Cross-pages bounding boxes of that section")


class SectionTitle(BaseModel):
    id: str = Field(default="", description="Unique identifier for the section")
    parent_id: str = Field(default="", description="Unique identifier which denotes parent of this structure")
    children_ids: Optional[List[str]] = Field(default=None, description="Unique Ids of first level children structures under this structure in correct sequence")
    text_alignment: Optional[str] = Field(default="", description="Text alignment of the section title")
    text: str = Field(default="", description="Text property added to all objects")
    bbox: Optional[DocProcBoundingBox] = Field(default=None, description="The bounding box of the section title")

class List_(BaseModel):
    id: str = Field(..., description="Unique identifier for the list")
    title: Optional[str] = Field(None, description="List title")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    children_ids: List[str] = Field(..., description="Unique Ids of first level children structures under this structure in correct sequence")
    bbox_list: Optional[List[DocProcBoundingBox]] = Field(None, description="Cross-pages bounding boxes of that table")


class ListItem(BaseModel):
    id: str = Field(..., description="Unique identifier for the list item")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    children_ids: Optional[List[str]] = Field(None, description="Unique Ids of first level children structures under this structure in correct sequence")
    text: str = Field(..., description="Text property added to all objects")
    bbox: Optional[DocProcBoundingBox] = Field(None, description="The bounding box of the list item")


class ListIdentifier(BaseModel):
    id: str = Field(..., description="Unique identifier for the list item")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    children_ids: List[str] = Field(..., description="Unique Ids of first level children structures under this structure in correct sequence")

class Table(BaseModel):
    id: str = Field(..., description="Unique identifier for the table")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    children_ids: List[str] = Field(..., description="Unique Ids of first level children structures under this structure in correct sequence, in this case, table rows")
    bbox_list: Optional[List[DocProcBoundingBox]] = Field(None, description="Cross-pages bounding boxes of that table")


class TableRow(BaseModel):
    id: str = Field(..., description="Unique identifier for the table row")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    children_ids: List[str] = Field(..., description="Unique Ids of first level children structures under this structure in correct sequence, in this case, table cells")
    bbox: Optional[DocProcBoundingBox] = Field(None, description="The bounding box of the table row")


class TableCell(BaseModel):
    id: str = Field(..., description="Unique identifier for the table cell")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    is_row_header: bool = Field(..., description="Whether the cell is part of row header or not")
    is_col_header: bool = Field(..., description="Whether the cell is part of column header or not")
    col_span: int = Field(..., description="Column span of the cell")
    row_span: int = Field(..., description="Row span of the cell")
    col_start: int = Field(..., description="Column start of the cell within the table")
    row_start: int = Field(..., description="Row start of the cell within the table")
    children_ids: Optional[List[str]] = Field(None, description="Children structures, e.g., paragraphs")
    text: str = Field(..., description="Text property added to all objects")
    bbox: Optional[DocProcBoundingBox] = Field(None, description="The bounding box of the table cell")

class Subscript(BaseModel):
    id: str = Field(..., description="Unique identifier for the subscript")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    children_ids: List[str] = Field(default_factory=list, description="Unique Ids of first level children structures under this structure in correct sequence")
    token_id_ref: Optional[str] = Field(None, description="Id of the token to which the subscript belongs")
    text: str = Field(..., description="Text property added to all objects")


class Superscript(BaseModel):
    id: str = Field(..., description="Unique identifier for the superscript")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    footnote_ref: str = Field(..., description="Matching footnote id found on the page")
    token_id_ref: Optional[str] = Field(None, description="Id of the token to which the superscript belongs")
    children_ids: List[str] = Field(default_factory=list, description="Unique Ids of first level children structures under this structure in correct sequence")
    text: str = Field(..., description="Text property added to all objects")


class Footnote(BaseModel):
    id: str = Field(..., description="Unique identifier for the footnote")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    children_ids: List[str] = Field(default_factory=list, description="Unique Ids of first level children structures under this structure in correct sequence")
    text: str = Field(..., description="Text property added to all objects")


class Paragraph(BaseModel):
    id: str = Field(..., description="Unique identifier for the paragraph")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    children_ids: List[str] = Field(default_factory=list, description="Unique Ids of first level children structures under this structure in correct sequence, in this case, tokens")
    text_alignment: Optional[str] = Field(None, description="Text alignment of the paragraph")
    indentation: Optional[int] = Field(None, description="Paragraph indentation")
    text: str = Field(..., description="Text property added to all objects")
    bbox_list: Optional[DocProcBoundingBox] = Field(default=None, description="Cross-pages bounding boxes of that Paragraph")


class CodeSnippet(BaseModel):
    id: str = Field(..., description="Unique identifier for the code snippet")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    children_ids: List[str] = Field(default_factory=list, description="Unique Ids of first level children structures under this structure in correct sequence, in this case, tokens")
    text: str = Field(..., description="Text of the code snippet. It can contain multiple lines, including empty lines or lines with leading spaces.")


class Picture(BaseModel):
    id: str = Field(..., description="Unique identifier for the picture")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    children_ids: List[str] = Field(default_factory=list, description="Unique identifiers of the tokens extracted from this picture, if any")
    text: Optional[str] = Field(None, description="Text extracted from this picture")
    verbalization: Optional[str] = Field(None, description="Verbalization of this picture")
    path: Optional[str] = Field(None, description="Path in the output location where the picture itself was saved")
    picture_class: Optional[str] = Field(None, description="The classification result of the picture")
    bbox: Optional[DocProcBoundingBox] = Field(None, description="The bounding box of the picture in the context of the page, expressed as pixel coordinates with respect to pages_metadata.page_image_height and pages_metadata.page_image_width")


class PageHeader(BaseModel):
    id: str = Field(..., description="Unique identifier for the page header")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    text: Optional[str] = Field(None, description="The page header text")
    bbox: Optional[DocProcBoundingBox] = Field(None, description="The bounding box of the page header")
    children_ids: List[str] = Field(default_factory=list, description="Unique Ids of first level children structures under this structure in correct sequence, in this case, tokens")


class PageFooter(BaseModel):
    id: str = Field(..., description="Unique identifier for the page footer")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    text: Optional[str] = Field(None, description="The page footer text")
    bbox: Optional[DocProcBoundingBox] = Field(None, description="The bounding box of the page footer")
    children_ids: List[str] = Field(default_factory=list, description="Unique Ids of first level children structures under this structure in correct sequence, in this case, tokens")


class BarCode(BaseModel):
    id: str = Field(..., description="Unique identifier for the bar code")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    text: Optional[str] = Field(None, description="The value of the bar code")
    format: Optional[str] = Field(None, description="The format of the bar code")
    path: Optional[str] = Field(None, description="Path in the output location where the var code picture is saved")
    bbox: Optional[DocProcBoundingBox] = Field(None, description="The bounding box of the bar code in the context of the page, expressed as pixel coordinates with respect to pages_metadata.page_image_height and pages_metadata.page_image_width")


class QRCode(BaseModel):
    id: str = Field(..., description="Unique identifier for the QR code")
    parent_id: str = Field(..., description="Unique identifier which denotes parent of this structure")
    text: Optional[str] = Field(None, description="The value of the QR code")
    path: Optional[str] = Field(None, description="Path in the output location where the var code picture is saved")
    bbox: Optional[DocProcBoundingBox] = Field(None, description="The bounding box of the bar code in the context of the page, expressed as pixel coordinates with respect to pages_metadata.page_image_height and pages_metadata.page_image_width")


class Token(BaseModel):
    id: str = Field(..., description="Unique identifier for the list identifier")
    parent_id: Optional[str] = Field(None, description="Unique identifier which denotes parent of this structure")
    style_id: Optional[str] = Field(None, description="Identifier of the style object associated with this token")
    text: str = Field(..., description="Actual text of the token")
    bbox: Optional[DocProcBoundingBox] = Field(None, description="The bounding box of the token in the context of the page, expressed as pixel coordinates with respect to pages_metadata.page_image_height and pages_metadata.page_image_width")
    confidence: Optional[float] = Field(None, description="Confidence score for the token")

class Structures(BaseModel):
    sections: Optional[List[Section]] = Field(
        default=None, description="All Section objects found in the document"
    )
    section_titles: Optional[List[SectionTitle]] = Field(
        default=None, description="All SectionTitle objects found in the document"
    )
    lists: Optional[List[List_]] = Field(
        default=None, description="All List objects found in the document"
    )
    list_items: Optional[List[ListItem]] = Field(
        default=None, description="All ListItem objects found in the document"
    )
    list_identifiers: Optional[List[ListIdentifier]] = Field(
        default=None, description="All ListIdentifier objects found in the document"
    )
    tables: Optional[List[Table]] = Field(
        default=None, description="All Table objects found in the document"
    )
    table_rows: Optional[List[TableRow]] = Field(
        default=None, description="All TableRow objects found in the document"
    )
    table_cells: Optional[List[TableCell]] = Field(
        default=None, description="All TableCell objects found in the document"
    )
    subscripts: Optional[List[Subscript]] = Field(
        default=None, description="All Subscript objects found in the document"
    )
    superscripts: Optional[List[Superscript]] = Field(
        default=None, description="All Superscript objects found in the document"
    )
    footnotes: Optional[List[Footnote]] = Field(
        default=None, description="All Footnote objects found in the document"
    )
    paragraphs: Optional[List[Paragraph]] = Field(
        default=None, description="All Paragraph objects found in the document"
    )
    code_snippets: Optional[List[CodeSnippet]] = Field(
        default=None, description="All CodeSnippet objects found in the document"
    )
    pictures: Optional[List[Picture]] = Field(
        default=None, description="All Picture objects found in the document"
    )
    page_headers: Optional[List[PageHeader]] = Field(
        default=None, description="All PageHeader objects found in the document"
    )
    page_footers: Optional[List[PageFooter]] = Field(
        default=None, description="All PageFooter objects found in the document"
    )
    bar_codes: Optional[List[BarCode]] = Field(
        default=None, description="All BarCode objects found in the document"
    )
    tokens: Optional[List[Token]] = Field(
        default=None, description="All Token objects found in the document"
    )

class AssemblyJsonOutput(BaseModel):
    '''
    Base class for document processing assembly JSON output format.
    
    This class represents the complete structured output from document processing operations,
    containing the document's hierarchical structure, metadata, styling information, and 
    extracted key-value pairs. It serves as the foundation for document analysis results
    returned by the Watson Document Understanding (WDU) service.
    
    Attributes:
        metadata (Optional[Metadata]): Document-level metadata including page count, title,
            author, language, publication date, and other document properties. Contains
            information about the document source and processing configuration.
            
        styles (Optional[List[Style]]): Collection of font styles used throughout the document.
            Each style includes font name, size, and formatting attributes (bold, italic).
            Styles are referenced by ID from text tokens to maintain formatting information.
            
        kvps (Optional[List[DocProcKVP]]): Key-value pairs extracted from the document using
            LLM-based extraction. Includes both structured form fields and semantic key-value
            relationships identified in the document content. 
            
        top_level_structures (Optional[List[str]]): Array of structure IDs representing the
            top-level elements directly under the document root. These IDs reference elements
            in the all_structures field and define the document's primary organization.
            Typically includes sections, tables, and other major structural components.
            
        all_structures (Optional[Structures]): Comprehensive collection of all document
            structures organized by type. Contains flattened lists of sections, paragraphs,
            tables, lists, images, headers, footers, and other structural elements. Each
            structure includes hierarchical relationships (parent/child IDs) and spatial
            information (bounding boxes).
    
    Structure Hierarchy:
        The document structure is represented as a tree where:
        - top_level_structures contains root-level element IDs
        - Each structure has parent_id and children_ids for navigation
        - Structures are organized by type in all_structures
        - Spatial information is preserved via bounding boxes
    
    Related Classes:
        - TextExtractionObjectResponse: Extends this class with plain text field
        - Metadata: Document-level metadata container
        - Structures: Container for all structural elements
        - DocProcKVP: Key-value pair representation
        - Style: Font and formatting information
    
    Notes:
        - Structure IDs are unique within a document and used for cross-referencing
        - Bounding boxes use pixel coordinates relative to page dimensions
        - This format is compatible with IBM Watson Document Understanding output
    
    See Also:
        - DocProcSpec: Configuration for document processing operations
        - DocProcOutputFormat: Output format selection (object vs docref)
        - TextExtractionObjectResponse: Subclass with extracted text
    '''
    metadata: Optional[Metadata] = Field(
        default=None, 
        description="Document-level metadata including page count, title, author, language, "
                   "and processing configuration. None if metadata extraction was not requested.")
    styles: Optional[List[Style]] = Field(
        default=None,
        description="Font styles used in the document, referenced by style_id from tokens. "
                   "Includes font name, size, bold, and italic attributes. None if style "
                   "extraction (document_structure=False) was not requested.")
    kvps: Optional[List[DocProcKVP]] = Field(
        default=None,
        description="Key-value pairs extracted from the document using LLM-based extraction. "
                   "Includes form fields and semantic relationships with spatial information. "
                   "None if KVP extraction (kvp_schemas) was not requested or configured.")
    top_level_structures: Optional[List[str]] = Field(
        default=None,
        description="Array of structure IDs for top-level document elements (sections, tables, etc.) "
                   "that belong directly under the document root. Used to navigate the document "
                   "hierarchy. None if structure extraction (document_structure=False) was not requested.")
    all_structures: Optional[Structures] = Field(
        default=None,
        description="Comprehensive collection of all document structures organized by type "
                   "(sections, paragraphs, tables, lists, images, etc.). Each structure includes "
                   "hierarchical relationships and spatial information. None if structure extraction "
                   "(document_structure=False) was not requested.")

class LanguageCode(StrEnum):
    '''
    The ISO-639 language codes understood by Document Processing functions.
    A special 'en_hw' code is used to enable an English handwritten model.
    '''
    en = auto()
    fr = auto()
    en_hw = auto()


class DocumentProcessingCommonInput(BaseModel):
    '''
    This class represents the common input of docext, docproc and docclassifier node 

    Attributes:
        document_ref (bytes|str): This is either a URL to the location of the document bytes or an ID that we use to resolve the location of the document
    '''
    document_ref: bytes | WXOFile | None = Field(description="Either an ID or a URL identifying the document to be used.", title='Document reference', default=None, json_schema_extra={"format": "binary"})

class DocProcInput(DocumentProcessingCommonInput):
    '''
    This class represents the input of a Document processing task. 

    Attributes:
        kvp_schemas (List[DocProcKVPSchema]): Optional list of key-value pair schemas to use for extraction. If not provided or None, no KVPs will be extracted. If an empty list is provided, we will use the internal schemas to extract KVPs.
        kvp_model_name (str | None): The LLM model to be used for key-value pair extraction
        kvp_force_schema_name (str | None): The name of the schema to use for KVP extraction. If not provided or None, the default schema will be used.
        kvp_enable_text_hints (bool): Whether to enable text hints for KVP extraction
    '''
    # This is declared as bytes but the runtime will understand if a URL is send in as input.
    # We need to use bytes here for Chat-with-doc to recognize the input as a File.
    kvp_schemas: Optional[List[DocProcKVPSchema]] | str = Field(
        title='KVP schemas',
        description="Optional list of key-value pair schemas to use for extraction.",
        default=None)
    kvp_model_name: str | None = Field(
        title='KVP Model Name',
        description="The LLM model to be used for key-value pair extraction",
        default=None
    )
    kvp_force_schema_name: str | None = Field(
        title='KVP Force Schema Name',
        description='Forces the kvp extractor to use a specified schema directly for value extraction by setting the schema document_type.',
        default=None
    )
    kvp_enable_text_hints: bool | None = Field(
        title='KVP Enable Text Hints',
        description='Determines whether to use text hints such as the text and layout information extracted from the document when extracting values in addition to the page image (True), or just rely on the page image itself (False)',
        default=True
    )

class TextExtractionObjectResponse(AssemblyJsonOutput):
    '''
    The text extraction operation response when output_format is set to "object".
    
    This class represents the structured response from a document text extraction operation,
    containing both the extracted plain text and the complete document structure metadata
    inherited from AssemblyJsonOutput.
    
    Attributes:
        text (str): The extracted plain text content from the document. This is the 
                   concatenated text from all pages and structures in reading order.
                   Empty string if no text could be extracted.
    
    Note:
        - This response type is used when DocProcSpec.output_format is set to 
          DocProcOutputFormat.object
        - For file reference responses, use TextExtractionResponse instead
        - The text field contains only plain text; structured data is in inherited fields
    '''
    text: str = Field(title='Text', description='The raw text extracted from the input document')

class TextExtractionResponse(BaseModel):
    '''
    The text extraction operation response when output_format is set to "docref" (default).
    Attributes:
        output_file_ref (str): The url to the file that contains the extracted text and kvps.
    '''
    output_file_ref: str = Field(description='The url to the file that contains the extracted text and kvps.', title="output_file_ref")


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
