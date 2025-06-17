import inspect
import json
from pathlib import Path
import re
import logging
import importlib.resources
import yaml

from pydantic import BaseModel, TypeAdapter
from typing import types

from langchain_core.utils.json_schema import dereference_refs
import typer

from ibm_watsonx_orchestrate.agent_builder.connections.types import ConnectionEnvironment, ConnectionPreference, ConnectionSecurityScheme
from ibm_watsonx_orchestrate.agent_builder.tools.openapi_tool import create_openapi_json_tools_from_content
from ibm_watsonx_orchestrate.agent_builder.tools.types import JsonSchemaObject, ToolRequestBody, ToolResponseBody
from ibm_watsonx_orchestrate.cli.commands.connections.connections_controller import add_connection, configure_connection, set_credentials_connection
from ibm_watsonx_orchestrate.client.connections.utils import get_connections_client
from ibm_watsonx_orchestrate.client.tools.tempus_client import TempusClient
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
    
    tools = []
    
    flow_id = model["spec"]["name"]

    tempus_client: TempusClient =  instantiate_client(TempusClient)

    flow_open_api = tempus_client.create_update_flow_model(flow_id=flow_id, model=model)

    logger.info(f"Flow model `{flow_id}` deployed successfully.")

    connections_client = get_connections_client()
    
    app_id = "flow_tools_app"
    logger.info(f"Creating connection for flow model...")
    existing_app = connections_client.get(app_id=app_id)
    if not existing_app:
        # logger.info(f"Creating app `{app_id}`.")
        add_connection(app_id=app_id)
    # else:
    #     logger.info(f"App `{app_id}` already exists.")
    
    # logger.info(f"Creating connection for app...")
    configure_connection(
        type=ConnectionPreference.MEMBER,
        app_id=app_id,
        token=connections_client.api_key,
        environment=ConnectionEnvironment.DRAFT,
        security_scheme=ConnectionSecurityScheme.BEARER_TOKEN,
        shared=False
    )

    set_credentials_connection(app_id=app_id, environment=ConnectionEnvironment.DRAFT, token=connections_client.api_key)

    connections = connections_client.get_draft_by_app_id(app_id=app_id)

    # logger.info(f"Connection `{connections.connection_id}` created successfully.")
    
    tools = await create_openapi_json_tools_from_content(flow_open_api, connections.connection_id)

    logger.info(f"Generating 'get_flow_status' tool spec...")    
    # Temporary code to deploy a status tool until we have full async support
    with importlib.resources.open_text('ibm_watsonx_orchestrate.flow_builder.resources', 'flow_status.openapi.yml', encoding='utf-8') as f:
        get_status_openapi = f.read()

    get_flow_status_spec = yaml.safe_load(get_status_openapi)
    tools.extend(await create_openapi_json_tools_from_content(get_flow_status_spec, connections.connection_id))


    return tools
