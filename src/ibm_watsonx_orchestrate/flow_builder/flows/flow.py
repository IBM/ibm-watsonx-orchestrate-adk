"""
The Flow model.  There are multiple methods to allow creation and population of 
the Flow model.
"""

import asyncio
from datetime import datetime
from enum import Enum
from pydantic.main import BaseModel
from ibm_watsonx_orchestrate.agent_builder.tools.types import JsonSchemaObject, ToolSpec
from ibm_watsonx_orchestrate.client.base_api_client import ClientAPIException
from ibm_watsonx_orchestrate.flow_builder.types import BranchNodeSpec, BranchNodeSpec, Conditions, Expression, ForeachSpec, PromptNodeSpec
from ibm_watsonx_orchestrate.flow_builder.node import Node, TimerNode
import inspect
from typing import (
    Any, AsyncIterator, Callable, Literal, Optional, cast, List, Sequence, Union, Tuple
)
import json
import logging
import copy
import uuid
import pytz
import os

from typing_extensions import Self
from pydantic import BaseModel, Field, SerializeAsAny, create_model, TypeAdapter
import yaml
from ibm_watsonx_orchestrate.agent_builder.tools.python_tool import PythonTool
from ibm_watsonx_orchestrate.agent_builder.models.types import ListVirtualModel
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.tools.tempus_client import TempusClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ..types import (
    Dimensions, DocProcKVPSchema, Assignment, Conditions, EndNodeSpec, Expression, ForeachPolicy, ForeachSpec, LoopSpec, BranchNodeSpec, MatchPolicy,
    NodeIdCondition, PlainTextReadingOrder, Position, PromptExample, PromptLLMParameters, PromptNodeSpec, ScriptNodeSpec, TextExtractionObjectResponse, TimerNodeSpec,
    NodeErrorHandlerConfig, NodeIdCondition, PlainTextReadingOrder, PromptExample, PromptLLMParameters, PromptNodeSpec,
    StartNodeSpec, ToolSpec, JsonSchemaObject, ToolRequestBody, ToolResponseBody, UserFieldKind, UserFieldOption, UserFlowSpec, UserNodeSpec, WaitPolicy, WaitNodeSpec,
    DocProcSpec, TextExtractionResponse, DocProcInput, DecisionsNodeSpec, DecisionsRule, DocExtSpec, DocumentClassificationResponse, DocClassifierSpec, DocumentProcessingCommonInput, DocProcOutputFormat
)
from .constants import CURRENT_USER, START, END, ANY_USER
from ..node import (
    EndNode, Node, PromptNode, ScriptNode, StartNode, TimerNode, UserNode, AgentNode, DataMap, ToolNode, DocProcNode, DecisionsNode, DocExtNode, DocClassifierNode
)
from ..types import (
    AgentNodeSpec, extract_node_spec, FlowContext, FlowEventType, FlowEvent, FlowSpec,
    NodeSpec, TaskEventType, ToolNodeSpec, SchemaRef, JsonSchemaObjectRef, FlowContextWindow, _to_json_from_json_schema
)

from ..data_map import DataMap, DataMapSpec
from ..utils import FIELD_INPUT_SCHEMA_TEMPLATES, FIELD_OUTPUT_SCHEMA_TEMPLATES, _get_json_schema_obj, get_valid_name, import_flow_model, _get_tool_request_body, _get_tool_response_body

from .events import StreamConsumer

logger = logging.getLogger(__name__)

# Mapping each event to its type
EVENT_TYPE_MAP = {
    FlowEventType.ON_FLOW_START: "informational",
    FlowEventType.ON_FLOW_END: "informational",
    FlowEventType.ON_FLOW_ERROR: "interrupting",
    TaskEventType.ON_TASK_WAIT: "interrupting",
    TaskEventType.ON_TASK_START: "informational",
    TaskEventType.ON_TASK_END: "informational",
    TaskEventType.ON_TASK_STREAM: "interrupting",
    TaskEventType.ON_TASK_ERROR: "interrupting",
}
        
class FlowEdge(BaseModel):
    '''Used to designate the edge of a flow.'''
    start: str
    end: str
    id: str | None = None

class Flow(Node):
    '''Flow represents a flow that will be run by wxO Flow engine.'''
    output_map: DataMapSpec | None = None
    nodes: dict[str, SerializeAsAny[Node]] = {}
    edges: List[FlowEdge] = []
    schemas: dict[str, Union[JsonSchemaObject, SchemaRef]] = {}
    compiled: bool = False
    validated: bool = False
    metadata: dict[str, str] = {}
    parent: Any = None
    _sequence_id: int = 0 # internal-id
    _tool_client: ToolClient = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # extract data schemas
        self._refactor_node_to_schemaref(self)

        # get Tool Client
        self._tool_client = instantiate_client(ToolClient)

        # set llm_model to use for the flow if any
        llm_model = kwargs.get("llm_model")
        if llm_model:
            if isinstance(llm_model, ListVirtualModel):
                self.metadata["llm_model"] = llm_model.name
            elif isinstance(llm_model, str):
                self.metadata["llm_model"] = llm_model
            else:
                raise AssertionError(f"flow llm_model should be either a str or ListVirtualModel")
        
        # set agent_conversation_memory_turns_limit for the flow if any
        agent_conversation_memory_turns_limit = kwargs.get("agent_conversation_memory_turns_limit")
        if agent_conversation_memory_turns_limit:
            self.metadata["agent_conversation_memory_turns_limit"] = agent_conversation_memory_turns_limit

    def _find_topmost_flow(self) -> Self:
        if self.parent:
            return self.parent._find_topmost_flow()
        return self
    
    def _next_sequence_id(self) -> int: 
        self._sequence_id += 1
        return self._sequence_id
    

    def _rewrite_local_refs(self, node):
        """Turn '#/$defs/Name' -> '#/schemas/Name' everywhere in a schema node."""
        if node is None:
            return
        # JsonSchemaObject / Pydantic-style
        if hasattr(node, "model_extra"):
            # rewrite model_extra in place
            self._rewrite_local_refs(node.model_extra)
            # walk common containers present on JsonSchemaObject
            for attr in ("properties", "items", "anyOf", "oneOf", "allOf"):
                if hasattr(node, attr):
                    self._rewrite_local_refs(getattr(node, attr))
            # discriminator.mapping holds strings that can be $ref-like targets
            if hasattr(node, "discriminator") and isinstance(node.discriminator, dict):
                mapping = node.discriminator.get("mapping")
                if isinstance(mapping, dict):
                    for k, v in list(mapping.items()):
                        if isinstance(v, str) and v.startswith("#/$defs/"):
                            mapping[k] = "#/schemas/" + v[len("#/$defs/"):]
            return

        # dict
        if isinstance(node, dict):
            for k, v in list(node.items()):
                if k == "$ref" and isinstance(v, str) and v.startswith("#/$defs/"):
                    node[k] = "#/schemas/" + v[len("#/$defs/"):]
                else:
                    self._rewrite_local_refs(v)
            return

        # list
        if isinstance(node, list):
            for i, v in enumerate(node):
                self._rewrite_local_refs(v)
            return 
    
    def _add_schema(self, schema: JsonSchemaObject, title: str = None) -> JsonSchemaObject:
        '''
        Adds a schema to the dictionary of schemas. If a schema with the same name already exists, it returns the existing schema. Otherwise, it creates a deep copy of the schema, adds it to the dictionary, and returns the new schema.

        Parameters:
        schema (JsonSchemaObject): The schema to be added.
        title (str, optional): The title of the schema. If not provided, it will be generated based on the schema's title or aliasName.

        Returns:
        JsonSchemaObject: The added or existing schema.
        '''

        # find the top most flow and add the schema to that scope
        top_flow = self._find_topmost_flow()

        # if there is already a schema with the same name, return it
        if title:
            if title in top_flow.schemas:
                existing_schema = top_flow.schemas[title]
                # we need a deep compare if the incoming schema and existing_schema is the same
                # pydantic suppport nested comparison by default

                if isinstance(schema, dict):
                    # recast schema to support direct access
                    schema = JsonSchemaObject.model_validate(schema)

                schema.title = title

                if schema == existing_schema:
                    return existing_schema
                # we need to do a deep compare
                incoming_model = schema.model_dump(exclude_none=True, exclude_unset=True)
                existing_model = existing_schema.model_dump(exclude_none=True, exclude_unset=True)

                # log the model
                # logger.info(f"incoming_model: {incoming_model}")
                # logger.info(f"existing_model: {existing_model}")

                if incoming_model == existing_model:
                    return existing_schema
                
                # else we need a new name, and create a new schema
                title = title + "_" + str(self._next_sequence_id())

        # otherwise, create a deep copy of the schema, add it to the dictionary and return it
        if schema:
            if isinstance(schema, dict):
                # recast schema to support direct access
                schema = JsonSchemaObject.model_validate(schema)

            
            # we should only add schema when it is a complex object
            complex_types = {"object", "array"}
            if schema.type not in complex_types:
                # Register simple defs (string/number/boolean/null) so they can be $ref’d
                new_schema = copy.deepcopy(schema)
                if not title:
                    if schema.title:
                        title = get_valid_name(schema.title)
                    elif schema.aliasName:
                        title = get_valid_name(schema.aliasName)
                    else:
                        title = "bo_" + str(self._next_sequence_id())
                new_schema.title = title

                top_flow = self._find_topmost_flow()
                
                self._rewrite_local_refs(new_schema)
                top_flow.schemas[title] = new_schema
                return new_schema

            new_schema = copy.deepcopy(schema)
            if not title:
                if schema.title:
                    title = get_valid_name(schema.title)
                elif schema.aliasName:
                    title = get_valid_name(schema.aliasName)
                else:
                    title = "bo_" + str(self._next_sequence_id())
            
            if new_schema.type == "object":
            # iterate the properties and add schema recursively
                if new_schema.properties is not None:
                    for key, value in new_schema.properties.items():
                        if isinstance(value, JsonSchemaObject):
                            if value.type == "object":
                                schema_ref = self._add_schema_ref(value, value.title)
                                new_schema.properties[key] = JsonSchemaObjectRef(title=value.title,
                                                                                ref = f"{schema_ref.ref}")
                            elif value.type == "array" and (value.items.type == "object" or value.items.type == "array"):
                                schema_ref = self._add_schema_ref(value.items, value.items.title)
                                new_schema.properties[key].items = JsonSchemaObjectRef(title=value.title,
                                                                                    ref = f"{schema_ref.ref}")
                            elif value.model_extra and hasattr(value.model_extra, "$ref"):
                                # there is already a reference, remove $/defs/ from the initial ref
                                ref_value = value.model_extra["$ref"]
                                schema_ref = f"#/schemas/{ref_value[8:]}"
                                new_schema.properties[key] = JsonSchemaObjectRef(ref = f"{schema_ref}")

            elif new_schema.type == "array":
                if new_schema.items.type == "object" or new_schema.items.type == "array":
                    schema_ref = self._add_schema_ref(new_schema.items, new_schema.items.title)
                    new_schema.items = JsonSchemaObjectRef(title=new_schema.items.title,
                                                           ref= f"{schema_ref.ref}")
            
            # we also need to unpack local references
            if hasattr(new_schema, "model_extra") and "$defs" in new_schema.model_extra:
                for schema_name, schema_def in new_schema.model_extra["$defs"].items():
                    self._add_schema(schema_def, schema_name)
                     # remove inline $defs now that they’ve been promoted
                    if hasattr(new_schema, "model_extra") and isinstance(new_schema.model_extra, dict):
                        # promote local defs
                        local_defs = new_schema.model_extra.get("$defs") or {}
                        for schema_name, schema_def in local_defs.items():
                            self._add_schema(schema_def, schema_name)
                        # strip inline $defs
                        new_schema.model_extra.pop("$defs", None)

            # makes sure every lingering #/$defs/... becomes #/schemas/... before serialization.            
            self._rewrite_local_refs(new_schema)
            # set the title
            new_schema.title = title
            top_flow.schemas[title] = new_schema

            return new_schema
        return None
    
    def _add_schema_ref(self, schema: JsonSchemaObject, title: str = None) -> SchemaRef:
        '''Create a schema reference'''
        if schema and (schema.type == "object" or schema.type == "array" or schema.type == "string"):
            new_schema = self._add_schema(schema, title)
            return SchemaRef(ref=f"#/schemas/{new_schema.title}")
        raise AssertionError(f"schema is not a complex object: {schema}")

    def _refactor_node_to_schemaref(self, node: Node):
        self._refactor_spec_to_schemaref(node.spec)
                
    def _refactor_spec_to_schemaref(self, spec: NodeSpec):
        if spec.input_schema and not isinstance(spec.input_schema, SchemaRef) and (spec.input_schema.type == "object" or spec.input_schema.type == "array") :
            if isinstance(spec.input_schema, ToolRequestBody):
                spec.input_schema = self._add_schema_ref(JsonSchemaObject(type = spec.input_schema.type,
                                                                                properties= spec.input_schema.properties,
                                                                                required= spec.input_schema.required), 
                                                                f"{spec.name}_input")
        if not isinstance(spec.output_schema, SchemaRef):
            if spec.output_schema_object is not None and spec.output_schema_object.type == "object":
                spec.output_schema = self._add_schema_ref(spec.output_schema_object, spec.output_schema_object.title)
                spec.output_schema_object = None
            elif spec.output_schema is not None:
                if isinstance(spec.output_schema, ToolResponseBody):
                    if spec.output_schema.type == "object":
                        json_obj = JsonSchemaObject(type = spec.output_schema.type,
                                description=spec.output_schema.description,
                                properties= spec.output_schema.properties,
                                items = spec.output_schema.items,
                                uniqueItems=spec.output_schema.uniqueItems,
                                anyOf=spec.output_schema.anyOf,
                                required= spec.output_schema.required)
                        spec.output_schema = self._add_schema_ref(json_obj, f"{spec.name}_output")
                    elif spec.output_schema.type == "array":
                        if hasattr(spec.output_schema, "items") and hasattr(spec.output_schema.items, "type") and spec.output_schema.items.type == "object":
                            schema_ref = self._add_schema_ref(spec.output_schema.items)
                            spec.output_schema.items = JsonSchemaObjectRef(ref=f"{schema_ref.ref}")
        
        if isinstance(spec, FlowSpec):
            if isinstance(spec.private_schema, JsonSchemaObject):
                spec.private_schema = self._add_schema_ref(spec.private_schema, title=f"{spec.private_schema.title}")

    # def refactor_datamap_spec_to_schemaref(self, spec: FnDataMapSpec):
    #    '''TODO'''
    #    if spec.input_schema:
    #        if isinstance(spec.input_schema, ToolRequestBody):
    #            spec.input_schema = self._add_schema_ref(JsonSchemaObject(type = spec.input_schema.type,
    #                                                                     properties= spec.input_schema.properties,
    #                                                                     required= spec.input_schema.required),
    #                                                            f"{spec.name}_input")
    #    if spec.output_schema_object is not None and spec.output_schema_object.type == "object":
    #        spec.output_schema = self._add_schema_ref(spec.output_schema_object, spec.output_schema_object.title)
    #        spec.output_schema_object = None
    #    elif spec.output_schema is not None:
    #        if isinstance(spec.output_schema, ToolResponseBody):
    #            spec.output_schema = self._add_schema_ref(JsonSchemaObject(type = spec.output_schema.type,
    #                                                                        Sdescription=spec.output_schema.description,
    #                                                                        properties= spec.output_schema.properties,
    #                                                                        items = spec.output_schema.items,
    #                                                                        uniqueItems=spec.output_schema.uniqueItems,
    #                                                                        anyOf=spec.output_schema.anyOf,
    #                                                                        required= spec.output_schema.required),
    #                                                            f"{spec.name}_output")          
                
    def _create_node_from_tool_fn(
        self,
        tool: Callable,
        error_handler_config: Optional[NodeErrorHandlerConfig] = None
    ) -> ToolNode:
        if not isinstance(tool, Callable):
            raise ValueError("Only functions with @tool decorator can be added.")

        spec = getattr(tool, "__tool_spec__", None)
        if not spec:
            raise ValueError("Only functions with @tool decorator can be added.")

        self._check_compiled()

        tool_spec = cast(ToolSpec, spec)

        # we need more information from the function signature
        spec = extract_node_spec(tool)

        toolnode_spec = ToolNodeSpec(type = "tool",
                                     name = tool_spec.name,
                                     display_name = tool_spec.name,
                                     description = tool_spec.description,
                                     input_schema = tool_spec.input_schema,
                                     output_schema = tool_spec.output_schema,
                                     output_schema_object = spec.output_schema_object,
                                     tool = tool_spec.name,
                                     error_handler_config = error_handler_config,)

        return ToolNode(spec=toolnode_spec)

    def tool(
        self,
        tool: Callable | str | None = None,
        name: str | None = None,
        display_name: str | None = None,
        description: str | None = None,
        input_schema: type[BaseModel] | None = None,
        output_schema: type[BaseModel] | None = None,
        error_handler_config: NodeErrorHandlerConfig | None = None,
        position: Position | None = None,
        dimensions: Dimensions | None = None
    ) -> ToolNode:
        '''create a tool node in the flow'''
        if tool is None:
            raise ValueError("tool must be provided")


        if isinstance(error_handler_config, dict):
            error_handler_config = NodeErrorHandlerConfig.model_validate(error_handler_config)    
        
        if isinstance(tool, str):        
            name = name if name is not None and name != "" else tool

            if input_schema is None and output_schema is None:
                # let's identify the correct tool id
                tool_name = name
                tool_id = None
                if tool is not None and isinstance(tool, str):
                    tool_name = tool
                    # if the tool id has a colon in it, we need to split it first
                    if ":" in tool:
                        tool_name = tool.split(":")[0]
                        tool_id = tool.split(":")[1]

                tool_spec = None
                # try to retrieve the schema from server
                if tool_id is not None:
                    try:
                        tool_spec_raw: dict | Literal[""] = self._tool_client.get_draft_by_id(tool_id)
                        if tool_spec_raw and isinstance(tool_spec_raw, dict):
                            tool_spec = ToolSpec.model_validate(tool_spec_raw)
                    except ClientAPIException as e:
                        # let's try with name as well before throwing error
                        pass

                if tool_spec is None and tool_name is not None:
                    tool_specs: List[dict] = self._tool_client.get_draft_by_name(tool_name)
                    if (tool_specs is None) or (len(tool_specs) == 0):
                        raise ValueError(f"tool '{tool_name}' not found")
                    
                elif tool_spec is None:
                    raise ValueError(f"tool id '{tool_id}' not found")

                input_schema_obj = None
                output_schema_obj = None

                if tool_spec is not None:
                    input_schema_obj = tool_spec.input_schema
                    output_schema_obj = tool_spec.output_schema
                # just pick the first one that is found
                if hasattr(tool_spec, "input_schema"):
                    input_schema_obj = _get_json_schema_obj("input", tool_spec.input_schema, True)
                if hasattr(tool_spec, "output_schema"):
                    output_schema_obj = _get_json_schema_obj("output", tool_spec.output_schema)
            else: 
                input_schema_obj = _get_json_schema_obj("input", input_schema)
                output_schema_obj = _get_json_schema_obj("output", output_schema)

            toolnode_spec = ToolNodeSpec(type = "tool",
                                     name = name,
                                     display_name = display_name,
                                     description = description,
                                     input_schema= _get_tool_request_body(input_schema_obj) if input_schema_obj is not None else None,
                                     output_schema= _get_tool_response_body(output_schema_obj) if output_schema_obj is not None else None,
                                     output_schema_object = output_schema_obj,
                                     tool = tool,
                                     error_handler_config = error_handler_config,
                                     position = position,
                                     dimensions = dimensions,
                                     )

            node = ToolNode(spec=toolnode_spec)
        elif isinstance(tool, PythonTool):
            if callable(tool):
                tool_spec = getattr(tool, "__tool_spec__", None)
                if tool_spec:
                    node = self._create_node_from_tool_fn(tool, error_handler_config = error_handler_config)
                else:
                    raise ValueError("Only functions with @tool decorator can be added.")
        else:
            raise ValueError(f"tool is not a string or Callable: {tool}")

        node = self._add_node(node)
        return cast(ToolNode, node)
    

    def script(
        self,
        script: str | None = "",
        name: str | None = None,
        display_name: str | None = None,
        description: str | None = None,
        input_schema: type[BaseModel] | None = None,
        output_schema: type[BaseModel] | None = None,
        position: Position | None = None,
        dimensions: Dimensions | None = None
    ) -> ScriptNode:
        '''create a script node in the flow'''    
        name = name if name is not None and name != "" else ""

        input_schema_obj = _get_json_schema_obj("input", input_schema)
        output_schema_obj = _get_json_schema_obj("output", output_schema)

        script_node_spec = ScriptNodeSpec(
                                name = name,
                                display_name = display_name,
                                description = description,
                                input_schema= _get_tool_request_body(input_schema_obj),
                                output_schema= _get_tool_response_body(output_schema_obj),
                                output_schema_object = output_schema_obj,
                                fn = script,
                                position = position,
                                dimensions = dimensions)

        node = ScriptNode(spec=script_node_spec)

        node = self._add_node(node)
        return cast(ScriptNode, node)
 
    def start(self, 
              name: str,
              display_name: str | None = None) -> StartNode:
        
        start_node: Node = self._add_node(StartNode(spec=StartNodeSpec(name=name, display_name=display_name)))
        return cast(StartNode, start_node)


    def end(self, 
            name: str,
            display_name: str | None = None) -> EndNode:
        
        end_node: Node = self._add_node(EndNode(spec=EndNodeSpec(name=name, display_name=display_name)))
        return cast(EndNode, end_node)


    def _add_node(self, node: Node) -> Node:
        self._check_compiled()

        if node.spec.name in self.nodes:
            raise ValueError(f"Node `{id}` already present.")

        # make a copy
        new_node = copy.copy(node)

        self._refactor_node_to_schemaref(new_node)

        self.nodes[node.spec.name] = new_node
        return new_node

    def agent(self, 
              name: str, 
              agent: str, 
              display_name: str|None=None,
              title: str | None = None,
              message: str | None = "Follow the agent instructions.",
              description: str | None = None,
              input_schema: type[BaseModel]|None = None, 
              output_schema: type[BaseModel]|None=None,
              guidelines: str|None=None) -> AgentNode:

         # create input spec
        input_schema_obj = _get_json_schema_obj(parameter_name = "input", type_def = input_schema)
        output_schema_obj = _get_json_schema_obj("output", output_schema)

        # Create the tool spec
        task_spec = AgentNodeSpec(
            name=name,
            display_name=display_name,
            description=description,
            agent=agent,
            title=title,
            message=message,
            guidelines=guidelines,
            input_schema=_get_tool_request_body(input_schema_obj),
            output_schema=_get_tool_response_body(output_schema_obj),
            output_schema_object = output_schema_obj
        )

        node = AgentNode(spec=task_spec)
        
        # add the node to the list of node
        node = self._add_node(node)
        return cast(AgentNode, node)
    
    def prompt(self, 
            name: str, 
            display_name: str|None=None,
            system_prompt: str | list[str] | None = None,
            user_prompt: str | list[str] | None = None,
            prompt_examples: list[PromptExample] | None = None,
            llm: str | None = None,
            llm_parameters: PromptLLMParameters | None = None,
            description: str | None = None,
            input_schema: type[BaseModel]|None = None, 
            output_schema: type[BaseModel]|None=None,
            error_handler_config: NodeErrorHandlerConfig | None = None,) -> PromptNode:

        if name is None:
            raise ValueError("name must be provided.")
        
         # create input spec
        input_schema_obj = _get_json_schema_obj(parameter_name = "input", type_def = input_schema)
        output_schema_obj = _get_json_schema_obj("output", output_schema)

        # Create the tool spec
        task_spec: PromptNodeSpec = PromptNodeSpec(
            name=name,
            display_name=display_name if display_name is not None else name,
            description=description,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            prompt_examples=prompt_examples,
            llm=llm,
            llm_parameters=llm_parameters,
            error_handler_config=error_handler_config,
            input_schema=_get_tool_request_body(input_schema_obj),
            output_schema=_get_tool_response_body(output_schema_obj),
            output_schema_object = output_schema_obj
        )

        node = PromptNode(spec=task_spec)
        
        # add the node to the list of node
        node = self._add_node(node)
        return cast(PromptNode, node)
    
    def docclassifier(self, 
            name: str, 
            llm : str = "watsonx/meta-llama/llama-3-2-90b-vision-instruct",
            version: str = "TIP",
            display_name: str| None = None,
            classes: type[BaseModel]| None = None, 
            description: str | None = None,
            min_confidence: float = 0.0,
            enable_review: bool = False) -> DocClassifierNode:
        
        if name is None :
            raise ValueError("name must be provided.")
        
        doc_classifier_config = DocClassifierNode.generate_config(llm=llm, min_confidence=min_confidence,input_classes=classes)

        input_schema_obj = _get_json_schema_obj(parameter_name = "input", type_def = DocumentProcessingCommonInput)
        output_schema_obj = _get_json_schema_obj(parameter_name = "output", type_def = DocumentClassificationResponse)
        
        if "$defs" in output_schema_obj.model_extra:
            output_schema_obj.model_extra.pop("$defs")
        # Create the docclassifier spec
        task_spec = DocClassifierSpec(
            name=name,
            display_name=display_name if display_name is not None else name,
            description=description,
            input_schema=_get_tool_request_body(input_schema_obj),
            output_schema=_get_tool_response_body(output_schema_obj),
            output_schema_object = output_schema_obj,
            config=doc_classifier_config,
            version=version,
            enable_review=enable_review
        )
        node = DocClassifierNode(spec=task_spec)
        
        # add the node to the list of node
        
        node = self._add_node(node)
        return cast(DocClassifierNode, node)
        
        
    def timer(self,
              name: str,
              delay: int,
              display_name: str | None = None,
              description: str | None = None) -> TimerNode:

        if name is None:
            raise ValueError("name must be provided.")
        if delay < 0:
            raise ValueError("delay must be non-negative.")

        timer_spec = TimerNodeSpec(
            name=name,
            display_name=display_name if display_name is not None else name,
            description=description,
            delay=delay
        )

        node: TimerNode = TimerNode(spec=timer_spec)
        node = self._add_node(node)
        return cast(TimerNode, node)

    
    def docext(self,
            name: str, 
            llm : str = "watsonx/meta-llama/llama-3-2-90b-vision-instruct",
            version: str = "TIP",
            display_name: str| None = None,
            fields: type[BaseModel]| None = None, 
            description: str | None = None,
            enable_hw: bool = False,
            min_confidence: float = 0, # Setting a small value because htil is not supported for pro code. 
            review_fields: List[str] = [],
            field_extraction_method: str = "classic",
            enable_review: bool = False) -> tuple[DocExtNode, type[BaseModel]]:
        
        if name is None :
            raise ValueError("name must be provided.")

        doc_ext_config = DocExtNode.generate_config(llm=llm, fields=fields, field_extraction_method=field_extraction_method)

        DocExtFieldValue = DocExtNode.generate_docext_field_value_model(fields=fields)
        
        input_schema_obj = _get_json_schema_obj(parameter_name = "input", type_def = DocumentProcessingCommonInput)
        output_schema_obj = _get_json_schema_obj("output", DocExtFieldValue)

        if "$defs" in output_schema_obj.model_extra:
            output_schema_obj.model_extra.pop("$defs")

        # Create the docext spec
        task_spec = DocExtSpec(
            name=name,
            display_name=display_name if display_name is not None else name,
            description=description,
            input_schema=_get_tool_request_body(input_schema_obj),
            output_schema=_get_tool_response_body(output_schema_obj),
            output_schema_object = output_schema_obj,
            config=doc_ext_config,
            version=version,
            enable_hw=enable_hw,
            min_confidence=min_confidence,
            review_fields=review_fields,
            field_extraction_method=field_extraction_method,
            enable_review=enable_review
        )
        node = DocExtNode(spec=task_spec)
        
        # add the node to the list of node
        
        node = self._add_node(node)
        return cast(DocExtNode, node), DocExtFieldValue

    def decisions(self, 
            name: str, 
            display_name: str|None=None,
            rules: list[DecisionsRule] | None = None,
            default_actions: dict[str, Any] = None,
            locale: str | None = None,
            description: str | None = None,
            input_schema: type[BaseModel]|None = None, 
            output_schema: type[BaseModel]|None=None) -> DecisionsNode:

        if name is None:
            raise ValueError("name must be provided.")
        
        if rules is None:
            raise ValueError("rules must be specified.")

         # create input spec
        input_schema_obj = _get_json_schema_obj(parameter_name = "input", type_def = input_schema)
        output_schema_obj = _get_json_schema_obj("output", output_schema)

        # Create the tool spec
        task_spec = DecisionsNodeSpec(
            name=name,
            display_name=display_name if display_name is not None else name,
            description=description,
            rules=rules,
            default_actions=default_actions,
            locale=locale,
            input_schema=_get_tool_request_body(input_schema_obj),
            output_schema=_get_tool_response_body(output_schema_obj),
            output_schema_object = output_schema_obj
        )

        node = DecisionsNode(spec=task_spec)
        
        # add the node to the list of node
        node = self._add_node(node)
        return cast(DecisionsNode, node)
    
    def docproc(self,
            name: str,
            task: str,
            plain_text_reading_order : PlainTextReadingOrder = PlainTextReadingOrder.block_structure,
            display_name: str|None=None,
            description: str | None = None,
            document_structure: bool = False,
            kvp_schemas: list[DocProcKVPSchema] | None = None,
            enable_hw: bool = False,
            kvp_model_name: str | None = None,
            kvp_force_schema_name: str | None = None,
            kvp_enable_text_hints: bool | None = True,
            output_format: DocProcOutputFormat | str = DocProcOutputFormat.docref) -> DocProcNode:

        if name is None :
            raise ValueError("name must be provided.")
        
        # Determine the output schema based on the output_format
        text_extraction_schema = TextExtractionResponse
        if output_format and output_format == DocProcOutputFormat.object:
            text_extraction_schema = TextExtractionObjectResponse
        
        output_schema_dict = {
            "text_extraction": text_extraction_schema
        }
         # create input spec
        input_schema_obj = _get_json_schema_obj(parameter_name = "input", type_def = DocProcInput)
        output_schema_obj = _get_json_schema_obj("output", output_schema_dict[task])
        if "$defs" in output_schema_obj.model_extra:
            output_schema_obj.model_extra.pop("$defs")
        # Convert string to enum if needed
        if isinstance(output_format, str):
            output_format = DocProcOutputFormat(output_format)
        
        # Create the docproc spec
        task_spec = DocProcSpec(
            name=name,
            display_name=display_name if display_name is not None else name,
            description=description,
            input_schema=_get_tool_request_body(input_schema_obj),
            output_schema=_get_tool_response_body(output_schema_obj),
            output_schema_object = output_schema_obj,
            task=task,
            document_structure=document_structure,
            plain_text_reading_order=plain_text_reading_order,
            enable_hw=enable_hw,
            kvp_schemas=kvp_schemas,
            kvp_model_name=kvp_model_name,
            kvp_force_schema_name=kvp_force_schema_name,
            kvp_enable_text_hints=kvp_enable_text_hints,
            output_format=output_format
        )

        node = DocProcNode(spec=task_spec)
        
        # add the node to the list of node
        node = self._add_node(node)
        return cast(DocProcNode, node)
    

    def node_exists(self, node: Union[str, Node]):
     
        if isinstance(node, Node):
            node_id = node.spec.name
        else:
            node_id = node

        if (node_id == END or node_id == START):
            return True
        if node_id in self.nodes:
            return True
        return False

    def edge(self,
             start_task: Union[str, Node],
             end_task: Union[str, Node],
             id: str | None = None) -> Self:
     
        self._check_compiled()

        start_id = self._get_node_id(start_task)
        end_id = self._get_node_id(end_task)

        if not self.node_exists(start_id):
            raise ValueError(f"Node {start_id} has not been added to the flow yet.")
        if not self.node_exists(end_id):
            raise ValueError(f"Node {end_id} has not been added to the flow yet.")
        if start_id == END:
            raise ValueError("END cannot be used as a start Node")
        if end_id == START:
            raise ValueError("START cannot be used as an end Node")


        # if the same edge has been added before, don't need to re-add it
        for edge in self.edges:
            if edge.start == start_id and edge.end == end_id:
                return self

        if id is None or len(id) == 0:
            id = None
            
        # Run this validation only for non-StateGraph graphs
        self.edges.append(FlowEdge(start = start_id, end = end_id, id = id))
        return self

    def sequence(self, *elements: Union[str, Node] | None) -> Self:
        '''TODO: Docstrings'''
        start_element: Union[str, Node] | None = None
        for element in elements:
            if not start_element:
                start_element = element
            else:
                end_element = element

                if isinstance(start_element, str):
                    start_node = start_element
                elif isinstance(start_element, Node):
                    start_node = start_element
                else:
                    start_node = START

                if isinstance(end_element, str):
                    end_node = end_element
                elif isinstance(end_element, Node):
                    end_node = end_element
                else:
                    end_node = END

                self.edge(start_node, end_node)

                # set start as the current end element
                start_element = end_element

        return self

    def starts_with(self, node: Union[str, Node]) -> Self:
        '''Create an edge with an automatic START node.'''
        return self.edge(START, node)

    def ends_with(self, node: Union[str, Node]) -> Self:
        '''Create an edge with an automatic END node.'''
        return self.edge(node, END)

    def starts_and_ends_with(self, node: Union[str, Node]) -> Self:
        '''Create a single node flow with an automatic START and END node.'''
        return self.sequence(START, node, END)

    def branch(self, 
               name: str = "",
               display_name: str = "",
               evaluator: Union[Callable, Expression, Conditions, None] = None) -> 'Branch':
        '''Create a BRANCH node'''
        e = evaluator
        if isinstance(evaluator, Callable):
            # We need to get the python tool representation of it
            raise ValueError("Branch with function as an evaluator is not supported yet.")
            # script_spec = getattr(evaluator, "__script_spec__", None)
            # if not script_spec:
            #    raise ValueError("Only functions with @script can be used as an evaluator.")
            # new_script_spec = copy.deepcopy(script_spec)
            # self._refactor_spec_to_schemaref(new_script_spec)
            # e = new_script_spec
        elif isinstance(evaluator, str):
            e = Expression(expression=evaluator)
        elif isinstance(evaluator, list):
            e = Conditions(conditions=evaluator)
        elif evaluator is None:
            e = Conditions(conditions=[])

        branch_name = name if name != "" else "branch_" + str(self._next_sequence_id())
        branch_display_name: str = display_name if display_name != "" else branch_name
        spec: BranchNodeSpec = BranchNodeSpec(name = branch_name, display_name = branch_display_name, evaluator=e)
        branch_node = Branch(spec = spec, containing_flow=self)
        return cast(Branch, self._add_node(branch_node))
    
    def conditions(self, 
                   name: str = "",
                   display_name: str = "") -> 'Branch':
        '''Create a Branch node with empty Conditions evaluator (if-else)'''
        branch_name = name if name != "" else "branch_" + str(self._next_sequence_id())
        branch_display_name: str = display_name if display_name != "" else branch_name

        spec = BranchNodeSpec(name = branch_name, display_name=branch_display_name, evaluator=Conditions(conditions=[]))
        branch_conditions_node = Branch(spec = spec, containing_flow=self)
        return cast(Branch, self._add_node(branch_conditions_node))
    
    def wait_for(self, *args) -> "Wait":
        '''Wait for all incoming nodes to complete.'''
        raise ValueError("Not implemented yet.")
        # spec = NodeSpec(name = "wait_" + uuid.uuid4().hex)
        # wait_node = Wait(spec = spec)

        # for arg in args:
        #    if isinstance(arg, Node):
        #        wait_node.node(arg)
        #    else:
        #        raise ValueError("Only nodes can be added to a wait node.")
            
        # return cast(Wait, self.node(wait_node))
            
    def map_flow_output_with_variable(self, target_output_variable: str, variable: str, default_value: str = None) -> Self:
        if self.output_map and self.output_map.spec:
            maps = self.output_map.spec.maps or []
        else:
            maps = []
        
        curr_map_metadata = {
            "assignmentType": "variable"
        }

        target_variable = "flow.output." + target_output_variable
        value_expression = "flow." + variable

        if default_value:
            maps.append(Assignment(target_variable=target_variable, value_expression=value_expression, default_value=default_value, metadata=curr_map_metadata))
        else:
            maps.append(Assignment(target_variable=target_variable, value_expression=value_expression, metadata=curr_map_metadata))

        flow_output_map_spec = DataMap(maps=maps)

        if self.output_map and self.output_map.spec:
            self.output_map.spec = flow_output_map_spec
        else:
            self.output_map = DataMapSpec(spec = flow_output_map_spec)
        return self
    
    def map_output(self, output_variable: str, expression: str, default_value: str = None) -> Self:
        if self.output_map and self.output_map.spec:
            maps = self.output_map.spec.maps or []
        else:
            maps = []
        
        curr_map_metadata = {
            "assignmentType": "pyExpression"
        }

        target_variable = "flow.output." + output_variable
        value_expression = expression

        if default_value:
            maps.append(Assignment(target_variable=target_variable, value_expression=value_expression, default_value=default_value, metadata=curr_map_metadata))
        else:
            maps.append(Assignment(target_variable=target_variable, value_expression=value_expression, metadata=curr_map_metadata))

        flow_output_map_spec = DataMap(maps=maps)

        if self.output_map and self.output_map.spec:
            self.output_map.spec = flow_output_map_spec
        else:
            self.output_map = DataMapSpec(spec = flow_output_map_spec)
        return self
    
    def map_flow_output_with_none(self, target_output_variable: str) -> Self:
        if self.output_map and self.output_map.spec:
            maps = self.output_map.spec.maps or []
        else:
            maps = []
        

        target_variable = "flow.output." + target_output_variable

        maps.append(Assignment(target_variable=target_variable, value_expression=None))

        flow_output_map_spec = DataMap(maps=maps)

        if self.output_map and self.output_map.spec:
            self.output_map.spec = flow_output_map_spec
        else:
            self.output_map = DataMapSpec(spec = flow_output_map_spec)
        return self


    def foreach(self, 
                item_schema: type[BaseModel],
                input_schema: type[BaseModel] |None=None,
                output_schema: type[BaseModel] |None=None,
                name: str | None = None,
                display_name: str | None = None) -> "Foreach": # return an Foreach object
        '''TODO: Docstrings'''

        output_schema_obj = _get_json_schema_obj("output", output_schema)
        input_schema_obj = _get_json_schema_obj("input", input_schema)
        foreach_item_schema = _get_json_schema_obj("item_schema", item_schema)

        if input_schema_obj is None:
            input_schema_obj = JsonSchemaObject(
                type = 'object',
                properties = {
                    "items": JsonSchemaObject(
                        type = "array",
                        items = foreach_item_schema)
                },
                required = ["items"])

        new_foreach_item_schema = self._add_schema(foreach_item_schema)

        foreach_name = name if (name is not None and len(name) > 0) else "foreach_" + str(self._next_sequence_id())
        foreach_display_name = display_name if display_name is not None else foreach_name
        foreach_output_schema = _get_json_schema_obj("output_schema", output_schema)
        spec = ForeachSpec(name = foreach_name,
                                        display_name=foreach_display_name,
                                        input_schema=_get_tool_request_body(input_schema_obj),
                                        output_schema=_get_tool_response_body(output_schema_obj),
                                        item_schema = new_foreach_item_schema)
        foreach_obj = Foreach(spec = spec, parent = self)
        foreach_node = self._add_node(foreach_obj)

        return cast(Foreach, foreach_node)

    def loop(self, 
             evaluator: Union[Callable, Expression],
             input_schema: type[BaseModel]|None=None, 
             output_schema: type[BaseModel]|None=None,
             name: str | None = None,
             display_name: str | None = None) -> "Loop": # return a WhileLoop object
        e = evaluator
        input_schema_obj = _get_json_schema_obj("input", input_schema)
        output_schema_obj = _get_json_schema_obj("output", output_schema)

        if isinstance(evaluator, Callable):
            # we need to get the python tool representation of it
            script_spec = getattr(evaluator, "__script_spec__", None)
            if not script_spec:
                raise ValueError("Only function with @script can be used as evaluator")
            new_script_spec = copy.deepcopy(script_spec)
            e = new_script_spec
        elif isinstance(evaluator, str):
            e = Expression(expression=evaluator)

        loop_name = name if (name is not None and len(name) > 0) else "loop_" + str(self._next_sequence_id())
        loop_display_name = display_name if display_name is not None else loop_name
        loop_spec = LoopSpec(name = loop_name, 
                                       display_name = loop_display_name,
                                       evaluator = e, 
                                       input_schema=_get_tool_request_body(input_schema_obj),
                                       output_schema=_get_tool_response_body(output_schema_obj))
        while_loop = Loop(spec = loop_spec, parent = self)
        while_node = self._add_node(while_loop)
        return cast(Loop, while_node)
    
    def userflow(self, 
                 owners: Sequence[str] = [],
                 input_schema: type[BaseModel] |None=None,
                 output_schema: type[BaseModel] |None=None,
                 name: str | None = None,
                 display_name: str | None = None,
                 position: Position | None = None,
                 dimensions: Dimensions | None = None) -> "UserFlow": # return a UserFlow object

        output_schema_obj = _get_json_schema_obj("output", output_schema)
        input_schema_obj = _get_json_schema_obj("input", input_schema)

        if name is None:
            name = "userflow_" + str(self._next_sequence_id())
        if display_name is None:
            display_name = name

        spec = UserFlowSpec(name = name,
                            display_name = display_name,
                            input_schema=_get_tool_request_body(input_schema_obj),
                            output_schema=_get_tool_response_body(output_schema_obj),
                            owners = owners,
                            position = position,
                            dimensions = dimensions)
        userflow_obj = UserFlow(spec = spec, parent = self)
        userflow_node = self._add_node(userflow_obj)

        return cast(UserFlow, userflow_node)

    def validate_model(self) -> bool:
        ''' Validate the model. '''
        validator = FlowValidator(flow=self)
        messages = validator.validate_model()
        if validator.no_error(messages):
            return True
        raise ValueError(f"Invalid flow: {messages}")

    def _check_compiled(self) -> None:
        if self.compiled:
            raise ValueError("Flow has already been compiled.")
    
    def compile(self, **kwargs) -> "CompiledFlow":
        """
        Compile the current Flow model into a CompiledFlow object.

        This method validates the flow model (if not already validated).

        To also deploy the model to the engine and test it use the compile_deploy() function. 

        Returns:
            CompiledFlow: An instance of the CompiledFlow class representing 
            the compiled flow.

        Raises:
            ValidationError: If the flow model is invalid and fails validation.
        """
        
        if not self.validated:
            # we need to validate the flow first
            self.validate_model()

        self.compiled = True
        self.metadata["source_kind"] = "adk/python"
        # self.metadata["source_kind"] = "ui"
        self.metadata["compiled_on"] = datetime.now(pytz.utc).isoformat()
        return CompiledFlow(flow=self, **kwargs)
    
    async def compile_deploy(self, **kwargs) -> "CompiledFlow":
        """
        Compile the current Flow model into a CompiledFlow object.

        This method validates the flow model (if not already validated), 
        deploys it to the engine, and marks it as compiled. 

        You can use the compiled flow to start a flow run.

        Returns:
            CompiledFlow: An instance of the CompiledFlow class representing 
            the compiled flow.

        Raises:
            ValidationError: If the flow model is invalid and fails validation.
        """
        
        compiled_flow = self.compile(**kwargs)
        
        # Deploy flow to the engine
        model = self.to_json()
        tool_id = await import_flow_model(model)

        compiled_flow.flow_id = tool_id
        compiled_flow.deployed = True

        return compiled_flow

    def to_json(self) -> dict[str, Any]:
        flow_dict = super().to_json()

        # serialize nodes
        nodes_dict = {}
        for key, value in self.nodes.items():
            nodes_dict[key] = value.to_json()
        flow_dict["nodes"] = nodes_dict

        # serialize edges
        flow_dict["edges"] = []
        for edge in self.edges:
            flow_dict["edges"].append(
                edge.model_dump(mode="json", exclude_unset=True, exclude_none=True, by_alias=True))

        schema_dict = {}
        for key, value in self.schemas.items():
            schema_dict[key] = _to_json_from_json_schema(value)
        flow_dict["schemas"] = schema_dict

        metadata_dict = {}
        for key, value in self.metadata.items():
            metadata_dict[key] = value
        flow_dict["metadata"] = metadata_dict

        if self.output_map and self.output_map.spec:
            flow_dict["output_map"] = {
                "spec": self.output_map.spec.to_json()
            }
        return flow_dict

    def _get_node_id(self, node: Union[str, Node]) -> str:
        if isinstance(node, Node):
            node_id = node.spec.name
        elif isinstance(node, FlowControl):
            node_id = node.spec.name
        elif isinstance(node, dict):
            if "node" in node:
                node_id: str = node.get("node", "unknown")
            else:
                raise ValueError("Node name is required")
        else:
            if (node == START):
                # need to create a start node if one does not yet exist
                if (START not in self.nodes):
                    start_node = StartNode(spec=StartNodeSpec(name=START))
                    self._add_node(start_node)
                return START
            if (node == END):
                if (END not in self.nodes):
                    end_node = EndNode(spec=EndNodeSpec(name=END))
                    self._add_node(end_node)
                return END
            node_id = node
        return node_id

    def _get_data_map(self, map: DataMap) -> DataMap:
        return map

class FlowRunStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    FAILED = "failed"

class FlowRun(BaseModel):
    '''Instance of a flow that is running.'''
    name: str | None = None
    id: str = None
    flow: Flow
    deployed_flow_id: str
    status: FlowRunStatus = FlowRunStatus.NOT_STARTED
    output: Any = None
    error: Any = None
    
    debug: bool = False
    on_flow_end_handler: Callable = None
    on_flow_error_handler: Callable = None

    model_config = {
        "arbitrary_types_allowed": True
    }           

    async def _arun_events(self, input_data:dict=None, filters: Sequence[Union[FlowEventType, TaskEventType]]=None) -> AsyncIterator[FlowEvent]:
        
        if self.status is not FlowRunStatus.NOT_STARTED:
            raise ValueError("Flow has already been started")

        # Start the flow
        client:TempusClient = instantiate_client(client=TempusClient)
        client.debug = self.debug
        logger.info(f"Launching flow instance...")
        ack = client.arun_flow(self.deployed_flow_id,input_data)
        self.id=ack["instance_id"]
        self.name = f"{self.flow.spec.name}:{self.id}"
        self.status = FlowRunStatus.IN_PROGRESS
        logger.info(f"Flow instance `{self.name}` started.")

        # Listen for events
        consumer = StreamConsumer(self.id)

        async for event in consumer.consume():
            if not event or (filters and event.kind not in filters):
                continue
            if self.debug:
                logger.debug(f"Flow instance `{self.name}` event: `{event.kind}`")
            
            self._update_status(event)

            if event.kind == FlowEventType.ON_FLOW_END:
                logger.info(f"Flow instance `{self.name}` completed.")
            elif event.kind == FlowEventType.ON_FLOW_ERROR:
                logger.error(f"Flow instance `{self.name}` failed with error: {event.error}")

            yield event
    
    def _update_status(self, event:FlowEvent):
        
        if event.kind == FlowEventType.ON_FLOW_END:
            self.status = FlowRunStatus.COMPLETED
        elif event.kind == FlowEventType.ON_FLOW_ERROR:
            self.status = FlowRunStatus.FAILED
        else:
            self.status = FlowRunStatus.INTERRUPTED if EVENT_TYPE_MAP.get(event.kind, "unknown") == "interrupting" else FlowRunStatus.IN_PROGRESS


        if self.debug:
            logger.debug(f"Flow instance `{self.name}` status change: `{self.status}`.  \nEvent: {event}")

    async def _arun(self, input_data: dict=None, **kwargs):
        
        if self.status is not FlowRunStatus.NOT_STARTED:
            raise ValueError("Flow has already been started")
        
        async for event in self._arun_events(input_data):
            if not event:
                continue
            
            if event.kind == FlowEventType.ON_FLOW_END:
                # result should come back on the event
                self._on_flow_end(event)
                break
            elif event.kind == FlowEventType.ON_FLOW_ERROR:
                # error should come back on the event
                self._on_flow_error(event)
                break   

    def update_state(self, task_id: str, data: dict) -> Self:
        '''Not Implemented Yet'''
        # update task and continue
        return self
    
    def _on_flow_end(self, event:FlowEvent):

        self.status = FlowRunStatus.COMPLETED
        self.output = event.context.data.output

        if self.debug:
            logger.debug(f"Flow run `{self.name}`: on_complete handler called. Output: {self.output}")

        if self.on_flow_end_handler:
            self.on_flow_end_handler(self.output)


    def _on_flow_error(self, event:FlowEvent):

        self.status = FlowRunStatus.FAILED
        self.error = event.error 

        if self.debug:
            logger.debug(f"Flow run `{self.name}`: on_error handler called.  Error: {self.error}")

        if self.on_flow_error_handler:
            self.on_flow_error_handler(self.error)
       

class CompiledFlow(BaseModel):
    '''A compiled version of the flow'''
    flow: Flow
    flow_id: str | None = None
    deployed: bool = False
    
    async def invoke(self, input_data:dict=None, on_flow_end_handler: Callable=None, on_flow_error_handler: Callable=None, debug:bool=False, **kwargs) -> FlowRun:
        """
        Sets up and initializes a FlowInstance for the current flow. This only works for CompiledFlow instances that have been deployed.

        Args:
            input_data (dict, optional): Input data to be passed to the flow. Defaults to None.
            on_flow_end_handler (callable, optional): A callback function to be executed 
                when the flow completes successfully. Defaults to None. Takes the flow output as an argument.
            on_flow_error_handler (callable, optional): A callback function to be executed 
                when an error occurs during the flow execution. Defaults to None.
            debug (bool, optional): If True, enables debug mode for the flow run. Defaults to False.

        Returns:
            FlowInstance: An instance of the flow initialized with the provided handlers 
            and additional parameters.
        """

        if self.deployed is False:
            raise ValueError("Flow has not been deployed yet. Please deploy the flow before invoking it by using the Flow.compile_deploy() function.")

        flow_run = FlowRun(flow=self.flow,  deployed_flow_id=self.flow_id, on_flow_end_handler=on_flow_end_handler, on_flow_error_handler=on_flow_error_handler, debug=debug, **kwargs)
        asyncio.create_task(flow_run._arun(input_data=input_data, **kwargs))
        return flow_run
    
    async def invoke_events(self, input_data:dict=None, filters: Sequence[Union[FlowEventType, TaskEventType]]=None, debug:bool=False) -> AsyncIterator[Tuple[FlowEvent,FlowRun]]:
        """
        Asynchronously runs the flow and yields events received from the flow for the client to handle. This only works for CompiledFlow instances that have been deployed.

        Args:
            input_data (dict, optional): Input data to be passed to the flow. Defaults to None.
            filters (Sequence[Union[FlowEventType, TaskEventType]], optional): 
                A sequence of event types to filter the events. Only events matching these types 
                will be yielded. Defaults to None.
            debug (bool, optional): If True, enables debug mode for the flow run. Defaults to False.

        Yields:
            FlowEvent: Events received from the flow that match the specified filters.
        """

        if self.deployed is False:
            raise ValueError("Flow has not been deployed yet. Please deploy the flow before invoking it by using the Flow.compile_deploy() function.")
        
        flow_run = FlowRun(flow=self.flow, deployed_flow_id=self.flow_id, debug=debug)
        async for event in flow_run._arun_events(input_data=input_data, filters=filters):
            yield (event, flow_run)
    
    def dump_spec(self, file: str) -> None:
        dumped = self.flow.to_json()
        with safe_open(file, 'w') as f:
            if file.endswith(".yaml") or file.endswith(".yml"):
                yaml.dump(dumped, f, allow_unicode=True)
            elif file.endswith(".json"):
                json.dump(dumped, f, indent=2)
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')

    def dumps_spec(self) -> str:
        dumped = self.flow.to_json()
        return json.dumps(dumped, indent=2)



class FlowFactory(BaseModel):
    '''A factory class to create a Flow model'''

    @staticmethod
    def create_flow(name: str|Callable,
                    display_name: str|None=None,
                    description: str|None=None,
                    initiators: Sequence[str]|None=None,
                    input_schema: type[BaseModel]|None=None,
                    output_schema: type[BaseModel]|None=None,
                    private_schema: type[BaseModel]|None=None,
                    schedulable: bool=False,
                    llm_model: str|ListVirtualModel|None=None,
                    agent_conversation_memory_turns_limit: int|None = None,
                    context_window: FlowContextWindow|None=None) -> Flow:
        if isinstance(name, Callable):
            flow_spec = getattr(name, "__flow_spec__", None)
            if not flow_spec:
                raise ValueError("Only functions with @flow_spec can be used to create a Flow specification.")
            return Flow(spec = flow_spec)

        input_schema_obj = _get_json_schema_obj(parameter_name = "input", type_def = input_schema)
        # create input spec
        output_schema_obj = _get_json_schema_obj("output", output_schema)
        private_schema_obj = _get_json_schema_obj("private", private_schema)
        if initiators is None:
            initiators = []

        flow_spec = FlowSpec(
            type="flow",
            name=name,
            display_name=display_name,
            description=description,
            initiators=initiators,
            input_schema=_get_tool_request_body(input_schema_obj),
            output_schema=_get_tool_response_body(output_schema_obj),
            private_schema = private_schema_obj,
            output_schema_object = output_schema_obj,
            schedulable=schedulable,
            context_window=context_window,
        )

        return Flow(spec = flow_spec, llm_model=llm_model, agent_conversation_memory_turns_limit=agent_conversation_memory_turns_limit)


class FlowControl(Node):
    '''A parent object representing a flow control node.'''
    ...

class Branch(FlowControl):   
    containing_flow: Flow = Field(description="The containing flow.")

    def __repr__(self):
        return f"MatchNode(name='{self.spec.name}', description='{self.spec.description}')" 

    def policy(self, kind: MatchPolicy) -> Self:
        '''
        Set the match policy for this node.

        Parameters:
        kind (MatchPolicy): The match policy to set.

        Returns:
        Self: The current node.
        '''
        if kind == MatchPolicy.ANY_MATCH:
            raise ValueError("Branch with policy ANY_MATCH is not supported yet.")
        
        self.spec.match_policy = kind
        return self

    def _add_case(self, label: str | bool, node: Node)->Self:
        '''
        Add a case to this branch.

        Parameters:
        label (str | bool): The label for this case.
        node (Node): The node to add as a case.

        Returns:
        Self: The current node.
        '''
        node_id = self.containing_flow._get_node_id(node)
        self.spec.cases[label] = {
            "display_name": node_id,
            "node": node_id 
        }
        self.containing_flow.edge(self, node)

        return self

    def case(self, label: str | bool, node: Node) -> Self:
        '''
        Add a case to this node.

        Parameters:
        label (str | bool): The label for this case.
        node (Node): The node to add as a case.

        Returns:
        Self: The current node.
        '''
        if label == "__default__":
            raise ValueError("Cannot have custom label __default__. Use default() instead.")

        return self._add_case(label, node)
    
    def condition(self, to_node: Node, expression: str="", default: bool=False) -> Self:
        '''
        Add a condition to this branch node. 

        Parameters:
        expression (str): The expression of this condition.
        to_node (Node): The node to go to when expression is evaluated to true.
        default (bool): The condition is the default (else) case.
        '''

        node_id = self.containing_flow._get_node_id(to_node)
        if default:
            condition = NodeIdCondition(node_id=node_id, default=default)
        else:
            condition = NodeIdCondition(expression=expression, node_id=node_id, default=default)

        evaluator: Expression | Conditions = self.get_spec().evaluator
        if evaluator is None:
            evaluator = Conditions(conditions=[])
        elif not isinstance(evaluator, Conditions):
            raise ValueError("evaluator must be a Conditions object")
        evaluator.conditions.append(condition)
        self.containing_flow.edge(self, to_node)

        return self

    def default(self, node: Node) -> Self:
        '''
        Add a default case to this node.

        Parameters:
        node (Node): The node to add as a default case.

        Returns:
        Self: The current node.
        '''
        return self._add_case("__default__", node)

    def to_json(self) -> dict[str, Any]:
        my_dict = super().to_json()

        return my_dict

    def get_spec(self) -> BranchNodeSpec:
        return cast(BranchNodeSpec, self.spec)


class Wait(FlowControl):
    '''
    A node that represents a wait in a pipeline.

    Attributes:
        spec (WaitSpec): The specification of the wait node.

    Methods:
        policy(kind: WaitPolicy) -> Self: Sets the wait policy for the wait node.
        node(node: Node) -> Self: Adds a node to the list of nodes to wait for.
        nodes(nodes: List[Node]) -> Self: Adds a list of nodes to the list of nodes to wait for.
        to_json() -> dict[str, Any]: Converts the wait node to a JSON dictionary.
    '''

    def policy(self, kind: WaitPolicy) -> Self:
        '''
        Sets the wait policy for the wait node.

        Args:
            kind (WaitPolicy): The wait policy to set.

        Returns:
            Self: The wait node object.
        '''
        self.spec.wait_policy = kind
        return self

    def node(self, node: Node) -> Self:
        '''
        Adds a node to the list of nodes to wait for.

        Args:
            node (Node): The node to add.

        Returns:
            Self: The wait node object.
        '''
        self.spec.nodes.append(node.spec.name)

    def nodes(self, nodes: List[Node]) -> Self:
        '''
        Adds a list of nodes to the list of nodes to wait for.

        Args:
            nodes (List[Node]): The list of nodes to add.

        Returns:
            Self: The wait node object.
        '''
        for node in nodes:
            self.spec.nodes.append(node.spec.name)

    def to_json(self) -> dict[str, Any]:
        my_dict = super().to_json()

        return my_dict

    def get_spec(self) -> WaitNodeSpec:
        return cast(WaitNodeSpec, self.spec)

class Loop(Flow):
    '''
    A Loop is a Flow that executes a set of steps repeatedly.

    Args:
        **kwargs (dict): Arbitrary keyword arguments.

    Returns:
        dict[str, Any]: A dictionary representation of the Loop object.
    '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_json(self) -> dict[str, Any]:
        my_dict = super().to_json()

        return my_dict

    def get_spec(self) -> LoopSpec:
        return cast(LoopSpec, self.spec)



class Foreach(Flow):
    '''
    A flow that iterates over a list of items.

    Args:
        **kwargs: Arbitrary keyword arguments.

    Returns:
        dict[str, Any]: A dictionary representation of the flow.
    '''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        spec: ForeachSpec = cast(ForeachSpec, self.spec)
        # refactor item schema
        if (isinstance(spec.item_schema, SchemaRef)):
            pass
        elif (spec.item_schema.type == "object"):
            spec.item_schema = self._add_schema_ref(spec.item_schema, spec.item_schema.title)

    def policy(self, kind: ForeachPolicy) -> Self:
        '''
        Sets the policy for the foreach flow.

        Args:
            kind (ForeachPolicy): The policy to set.

        Returns:
            Self: The current instance of the flow.
        '''
        self.get_spec().foreach_policy = kind
        return self

    def to_json(self) -> dict[str, Any]:
        my_dict = super().to_json()

        return my_dict

    def get_spec(self) -> ForeachSpec:
        return cast(ForeachSpec, self.spec)

class FlowValidationKind(str, Enum):
    '''
    This class defines the type of validation for a flow.

    Attributes:
        ERROR (str): Indicates an error in the flow.
        WARNING (str): Indicates a warning in the flow.
        INFO (str): Indicates informational messages related to the flow.
    '''
    ERROR = "ERROR",
    WARNING = "WARNING",
    INFO = "INFO"

class FlowValidationMessage(BaseModel):
    '''
    FlowValidationMessage class to store validation messages for a flow.

    Attributes:
        kind (FlowValidationKind): The kind of validation message.
        message (str): The validation message.
        node (Node): The node associated with the validation message.

    Methods:
        __init__(self, kind: FlowValidationKind, message: str, node: Node) -> None:
            Initializes the FlowValidationMessage object with the given parameters.
    '''
    kind: FlowValidationKind
    message: str
    node: Node

class FlowValidator(BaseModel):
    '''Validate the flow to ensure it is valid and runnable.'''
    flow: Flow

    def validate_model(self) -> List[FlowValidationMessage]:
        '''Check the model for possible errors.

        Returns:
            List[FlowValidationMessage]: A list of validation messages.
        '''
        return []

    def any_errors(self, messages: List[FlowValidationMessage]) -> bool:
        '''
        Check if any of the messages have a kind of ERROR.

        Args:
            messages (List[FlowValidationMessage]): A list of validation messages.

        Returns:
            bool: True if there are any errors, False otherwise.
        '''
        return any(m.kind == FlowValidationKind.ERROR for m in messages)

    def no_error(self, messages: List[FlowValidationMessage]) -> bool:
        '''Check if there are no errors in the messages.

        Args:
            messages (List[FlowValidationMessage]): A list of validation messages.

        Returns:
            bool: True if there are no errors, False otherwise.
        '''
        return not any(m.kind == FlowValidationKind.ERROR for m in messages)

class UserFlow(Flow):
    '''
    A flow that represents a series of user nodes. 
    A user flow can include other nodes, but not another User Flows.
    '''

    def __repr__(self):
        return f"UserFlow(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> UserFlowSpec:
        return cast(UserFlowSpec, self.spec)
    
    def to_json(self) -> dict[str, Any]:
        my_dict = super().to_json()

        return my_dict

    def field(self, 
              name: str, 
              kind: UserFieldKind = UserFieldKind.Text,
              display_name: str | None = None,
              description: str | None = None,
              direction: Literal["input", "output"] = "output",
              text: str | None = None, # The text used to ask question to the user, e.g. 'what is your name?'
              input_map: DataMap | DataMapSpec | None= None,
              default: Any | None = None) -> UserNode:
        '''create a node in the flow'''
        # create a json schema object based on the single field
        if not name:
            raise AssertionError("name cannot be empty")

        if direction == "input":
            if kind in FIELD_INPUT_SCHEMA_TEMPLATES:
                schema_obj = FIELD_INPUT_SCHEMA_TEMPLATES[kind]
            else:
                raise ValueError("Input kind {kind} is not support in UserField.")
        elif direction == "output":
            if kind in FIELD_OUTPUT_SCHEMA_TEMPLATES:
                schema_obj = FIELD_OUTPUT_SCHEMA_TEMPLATES[kind]
            else:
                raise ValueError("Output kind {kind} is not support in UserField.")

            if kind == UserFieldKind.Text and text is None:
                raise ValueError("Text field must be set for Text input.")

        # A user node will only has 1 field or 1 form.
        user_node_spec = UserNodeSpec(
            name=name,
            display_name=display_name,
            description=description,
            owners=[CURRENT_USER],
            input_schema=None,
            output_schema=None,
            output_schema_object = None,
        )

        node = UserNode(spec = user_node_spec)
        node.field(name = name,
                   kind = kind,
                   display_name = display_name,
                   text = text,
                   direction = direction,
                   input_map = input_map,
                   input_schema = _get_tool_request_body(schema_obj["input"]) if "input" in schema_obj else None,
                   output_schema = _get_tool_response_body(schema_obj["output"]) if "output" in schema_obj else None)

        node = self._add_node(node)
        return cast(UserNode, node)
    
    def form(self, 
              name: str, 
              display_name: str | None = None,
              instructions: str | None = None,
              submit_button_label: str | None = "Submit",
              cancel_button_label: str | None = None) -> UserNode:
        '''create a node in the flow with a form'''
        # create a json schema object based on the single field
        if not name:
            raise AssertionError("name cannot be empty")

        schema_obj = JsonSchemaObject(type="object", # type: ignore
                                      title=name,
                                      description=instructions)
        
        schema_obj.properties = {}
       
        task_spec = UserNodeSpec(
            name=name,
            display_name=display_name,
            description=instructions,
            owners=[CURRENT_USER],
            output_schema_object = schema_obj
        )

        node = UserNode(spec = task_spec)
        node.form(name = name,
                   display_name = display_name,
                   instructions = instructions,
                   submit_button_label = submit_button_label,
                   cancel_button_label = cancel_button_label
                 )

        node = self._add_node(node)
        return cast(UserNode, node)
    
