import inspect
import json
from pathlib import Path
import re
import logging
import importlib.resources
import yaml

from pydantic import BaseModel
from typing import types

from langchain_core.utils.json_schema import dereference_refs
import typer

from ibm_watsonx_orchestrate.agent_builder.connections.types import ConnectionEnvironment, ConnectionPreference, ConnectionSecurityScheme
from ibm_watsonx_orchestrate.agent_builder.tools.openapi_tool import create_openapi_json_tools_from_content
from ibm_watsonx_orchestrate.agent_builder.tools.types import JsonSchemaObject
from ibm_watsonx_orchestrate.cli.commands.connections.connections_controller import add_connection, configure_connection, set_credentials_connection
from ibm_watsonx_orchestrate.client.connections.utils import get_connections_client
from ibm_watsonx_orchestrate.client.tools.tempus_client import TempusClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client, is_local_dev

logger = logging.getLogger(__name__)

def get_valid_name(name: str) -> str:
 
    return re.sub('\\W|^(?=\\d)','_', name)

def _get_json_schema_obj(parameter_name: str, type_def: type[BaseModel] | None) -> JsonSchemaObject:
    if not type_def or type_def is None or type_def == inspect._empty:
        return None

    if issubclass(type_def, BaseModel):
        input_schema_json = type_def.model_json_schema()
        input_schema_json = dereference_refs(input_schema_json)
        input_schema_obj = JsonSchemaObject(**input_schema_json)
        if input_schema_obj.required is None:
            input_schema_obj.required = []
        return input_schema_obj
    
    if isinstance(type_def, type):
        schema_type = 'object'
        if type_def == str:
            schema_type = 'string'
        elif type_def == int:
            schema_type = 'integer'
        elif type_def == float:
            schema_type = 'number'
        elif type_def == bool:
            schema_type = 'boolean'
        else:
            schema_type = 'string'
        # TODO: inspect the list item type and use that as the item type
        return JsonSchemaObject(type=schema_type, properties={}, required=[])
   
    raise ValueError(
        f"Parameter {parameter_name} must be of type BaseModel or a primitive type.")

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
    with importlib.resources.open_text('ibm_watsonx_orchestrate.experimental.flow_builder.resources', 'flow_status.openapi.yml', encoding='utf-8') as f:
        get_status_openapi = f.read()

    get_flow_status_spec = yaml.safe_load(get_status_openapi)
    tools.extend(await create_openapi_json_tools_from_content(get_flow_status_spec, connections.connection_id))


    return tools
