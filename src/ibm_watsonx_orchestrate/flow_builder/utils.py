import importlib
import inspect
import re
import logging

from pydantic import BaseModel, TypeAdapter

from langchain_core.utils.json_schema import dereference_refs
from rpds import List
import typer
import yaml

from ibm_watsonx_orchestrate.agent_builder.tools.base_tool import BaseTool
from ibm_watsonx_orchestrate.agent_builder.tools.flow_tool import create_flow_json_tool
from ibm_watsonx_orchestrate.agent_builder.tools.openapi_tool import OpenAPITool, create_openapi_json_tools_from_content
from ibm_watsonx_orchestrate.agent_builder.tools.types import JsonSchemaObject, OpenApiToolBinding, ToolBinding, ToolRequestBody, ToolResponseBody, ToolSpec
from ibm_watsonx_orchestrate.client.tools.tempus_client import TempusClient
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client, is_local_dev

logger = logging.getLogger(__name__)

def get_valid_name(name: str) -> str:
 
    return re.sub('\\W|^(?=\\d)','_', name)

def _get_json_schema_obj(parameter_name: str, type_def: type[BaseModel] | ToolRequestBody | ToolResponseBody | None, openapi_decode: bool = False) -> JsonSchemaObject:
    if not type_def or type_def is None or type_def == inspect._empty:
        return None

    if inspect.isclass(type_def) and issubclass(type_def, BaseModel):
        schema_json = type_def.model_json_schema()
        schema_json = dereference_refs(schema_json)
        schema_obj = JsonSchemaObject(**schema_json)
        if schema_obj.required is None:
            schema_obj.required = []
        return schema_obj
    
    if isinstance(type_def, ToolRequestBody) or isinstance(type_def, ToolResponseBody):
        schema_json = type_def.model_dump()
        schema_obj = JsonSchemaObject.model_validate(schema_json)

        if openapi_decode:
            # during tool import for openapi - we convert header, path and query parameter
            # with a prefix "header_", "path_" and "query_".  We need to remove it.
            if schema_obj.type == 'object':
                # for each element in properties, we need to check the key and if it is
                # prefixed with "header_", "path_" and "query_", we need to remove the prefix.
                if hasattr(schema_obj, "properties"):
                    new_properties = {}
                    for key, value in schema_obj.properties.items():
                        if key.startswith('header_'):
                            new_properties[key[7:]] = value
                        elif key.startswith('path_'):
                            new_properties[key[5:]] = value
                        elif key.startswith('query_'):
                            new_properties[key[6:]] = value
                        else:
                            new_properties[key] = value
                        
                    schema_obj.properties = new_properties     

                # we also need to go thru required and replace it
                if hasattr(schema_obj, "required"):
                    new_required = []
                    for item in schema_obj.required:
                        if item.startswith('header_'):
                            new_required.append(item[7:])
                        elif item.startswith('path_'):
                            new_required.append(item[5:])
                        elif item.startswith('query_'):
                            new_required.append(item[6:])
                        else:
                            new_required.append(item)
                    schema_obj.required = new_required

        return schema_obj

    # handle the non-obvious cases
    schema_json = TypeAdapter(type_def).json_schema()
    schema_json = dereference_refs(schema_json)
    return JsonSchemaObject.model_validate(schema_json)


def _get_tool_request_body(schema_obj: JsonSchemaObject) -> ToolRequestBody:
    if schema_obj is None:
        return None
    
    if isinstance(schema_obj, JsonSchemaObject):
        request_obj = ToolRequestBody(type='object', properties=schema_obj.properties, required=schema_obj.required)
        if schema_obj.model_extra:
            request_obj.__pydantic_extra__ = schema_obj.model_extra

        return request_obj
    
    raise ValueError(f"Invalid schema object: {schema_obj}")

def _get_tool_response_body(schema_obj: JsonSchemaObject) -> ToolResponseBody:
    if schema_obj is None:
        return None
    
    if isinstance(schema_obj, JsonSchemaObject):
        response_obj = ToolResponseBody(type=schema_obj.type)
        if schema_obj.title:
            response_obj.title = schema_obj.title
        if schema_obj.description:
            response_obj.description = schema_obj.description
        if schema_obj.properties:
            response_obj.properties = schema_obj.properties
        if schema_obj.items:
            response_obj.items = schema_obj.items
        if schema_obj.uniqueItems:
            response_obj.uniqueItems = schema_obj.uniqueItems
        if schema_obj.anyOf:
            response_obj.anyOf = schema_obj.anyOf
        if schema_obj.required:
            response_obj.required = schema_obj.required

        if schema_obj.model_extra:
            response_obj.__pydantic_extra__ = schema_obj.model_extra

        return response_obj
    
    raise ValueError(f"Invalid schema object: {schema_obj}")


async def import_flow_model(model):

    if not is_local_dev():
        raise typer.BadParameter(f"Flow tools are only supported in local environment.")

    if model is None:
        raise typer.BadParameter(f"No model provided.")

    tool = create_flow_json_tool(name=model["spec"]["name"],
                                description=model["spec"]["description"], 
                                permission="read_only", 
                                flow_model=model) 

    client = instantiate_client(ToolClient)

    tool_id = None
    exist = False
    existing_tools = client.get_draft_by_name(tool.__tool_spec__.name)
    if len(existing_tools) > 1:
        raise ValueError(f"Multiple existing tools found with name '{tool.__tool_spec__.name}'. Failed to update tool")

    if len(existing_tools) > 0:
        existing_tool = existing_tools[0]
        exist = True
        tool_id = existing_tool.get("id")

    tool_spec = tool.__tool_spec__.model_dump(mode='json', exclude_unset=True, exclude_none=True, by_alias=True)
    name = tool_spec['name']
    if exist:
        logger.info(f"Updating flow '{name}'")
        client.update(tool_id, tool_spec)
    else:
        logger.info(f"Deploying flow '{name}'")
        response = client.create(tool_spec)
        tool_id = response["id"]

    return tool_id

def import_flow_support_tools():

    if not is_local_dev():
        # we can't import support tools into non-local environments yet
        return []

    client = instantiate_client(TempusClient)

    logger.info(f"Import 'get_flow_status' tool spec...")
    tools = [create_flow_status_tool("i__get_flow_status_intrinsic_tool__")]

    return tools

# Assisted by watsonx Code Assistant

def create_flow_status_tool(flow_status_tool: str, TEMPUS_ENDPOINT: str="http://wxo-tempus-runtime:9044") -> dict:

    spec = ToolSpec(
        name=flow_status_tool,
        description="We can use the flow instance id to get the status of a flow. Only call this on explicit request by the user.",
        permission='read_only',
        display_name= "Get flow status"
    )

    openapi_binding = OpenApiToolBinding(
        http_path="/flows",
        http_method="GET",
        security=[],
        servers=[TEMPUS_ENDPOINT]
    )
    
    spec.binding = ToolBinding(openapi=openapi_binding)
    # Input Schema
    properties = {
        "query_instance_id": {
            "type": "string",
            "title": "instance_id",
            "description": "Identifies the instance ID of the flow.",
            "in": "query"
        }
    }
    
    spec.input_schema = ToolRequestBody(
        type='object',
        properties=properties,
        required=[]
    )
    spec.output_schema = ToolResponseBody(type='array', description='Return the status of a flow instance.')

    return OpenAPITool(spec=spec)

