from dataclasses import dataclass
from enum import Enum
import inspect
import logging
from typing import (
    Any, Callable, cast, Literal, List, NamedTuple, Optional, Sequence, Union
)

import docstring_parser
from munch import Munch
from pydantic import BaseModel, Field

from langchain_core.tools.base import create_schema_from_function
from langchain_core.utils.json_schema import dereference_refs

from ibm_watsonx_orchestrate.agent_builder.tools import PythonTool
from ibm_watsonx_orchestrate.experimental.flow_builder.flows.constants import ANY_USER
from ibm_watsonx_orchestrate.agent_builder.tools.types import (
    ToolSpec, ToolRequestBody, ToolResponseBody, JsonSchemaObject
)
from .utils import get_valid_name

logger = logging.getLogger(__name__)

class JsonSchemaObjectRef(JsonSchemaObject):
    ref: str=Field(description="The id of the schema to be used.", serialization_alias="$ref")

class SchemaRef(BaseModel):
 
    ref: str = Field(description="The id of the schema to be used.", serialization_alias="$ref")

def _assign_attribute(obj, attr_name, schema):
    if hasattr(schema, attr_name) and (getattr(schema, attr_name) is not None):
        obj[attr_name] = getattr(schema, attr_name)

def _to_json_from_json_schema(schema: JsonSchemaObject) -> dict[str, Any]:
    model_spec = {}
    if isinstance(schema, dict):
        schema = Munch(schema)
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
    _assign_attribute(model_spec, "aliasName", schema)

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
        model_spec["required"] = request_body.required
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
 
    kind: Literal["node", "tool", "user", "script", "agent", "flow", "start", "decisions", "prompt", "branch", "wait", "foreach", "loop", "end"] = "node"
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
    
class UserNodeSpec(NodeSpec):
 
    owners: Sequence[str] = ANY_USER

    def __init__(self, **data):
        super().__init__(**data)
        self.kind = "user"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        if self.owners:
            model_spec["owners"] = self.owners
        return model_spec

class AgentNodeSpec(ToolNodeSpec):
 
    message: str | None = Field(default=None, description="The instructions for the task.")
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
    initiators: Sequence[str] = ANY_USER

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.kind = "flow"

    def to_json(self) -> dict[str, Any]:
        model_spec = super().to_json()
        if self.initiators:
            model_spec["initiators"] = self.initiators

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
 
    ON_TASK_WAIT = "on_task_wait" # the task is waiting for inputs before proceeding
    ON_TASK_START = "on_task_start"
    ON_TASK_END = "on_task_end"
    ON_TASK_STREAM = "on_task_stream"
    ON_TASK_ERROR = "on_task_error"

class FlowContext(BaseModel):
 
    name: str | None = None # name of the process or task
    task_id: str | None = None # id of the task, this is at the task definition level
    flow_id: str | None = None # id of the flow, this is at the flow definition level
    instance_id: str | None = None
    thread_id: str | None = None
    instance_id: str | None = None
    thread_id: str | None = None
    parent_context: Any | None = None
    child_context: List["FlowContext"] | None = None
    metadata: dict = Field(default_factory=dict[str, Any])
    data: dict = Field(default_factory=dict[str, Any])

    def get(self, key: str) -> Any:
     
        if key in self.data:
            return self.data[key]

        if self.parent_context:
            pc = cast(FlowContext, self.parent_conetxt)
            return pc.get(key)

class FlowEventType(Enum):
 
    ON_FLOW_START = "on_flow_start"
    ON_FLOW_END = "on_flow_end"
    ON_FLOW_ERROR = "on_flow_error"


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
    target: str
    source: str
    
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
    elif isinstance(return_type, type) and issubclass(return_type, BaseModel):
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
