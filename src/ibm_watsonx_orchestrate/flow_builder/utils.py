import importlib
import inspect
import re
import logging
from copy import deepcopy
from typing import Any, Dict, Optional

from pydantic import BaseModel, TypeAdapter

from langchain_core.utils.json_schema import dereference_refs
import typer

from ibm_watsonx_orchestrate.agent_builder.tools.base_tool import BaseTool
from ibm_watsonx_orchestrate.agent_builder.tools.flow_tool import create_flow_json_tool
from ibm_watsonx_orchestrate.agent_builder.tools.openapi_tool import OpenAPITool, create_openapi_json_tools_from_content
from ibm_watsonx_orchestrate.agent_builder.tools.types import JsonSchemaObject, OpenApiToolBinding, ToolBinding, ToolRequestBody, ToolResponseBody, ToolSpec
from typing import Dict, List, Any, Optional
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


def _get_tool_request_body(schema_obj: JsonSchemaObject | ToolRequestBody) -> ToolRequestBody:
    if schema_obj is None:
        return None
    
    if isinstance(schema_obj, ToolRequestBody):
        return schema_obj

    if isinstance(schema_obj, JsonSchemaObject):
        if schema_obj.type == "object":
            request_obj = ToolRequestBody(type='object', properties=schema_obj.properties, required=schema_obj.required)
            if schema_obj.model_extra:
                request_obj.__pydantic_extra__ = schema_obj.model_extra
        else:  
            if schema_obj.wrap_data:
                # we need to wrap a simple type with an object
                request_obj = ToolRequestBody(type='object', properties={}, required=[])
                request_obj.properties["data"] = schema_obj
            else:
                request_obj = ToolRequestBody(type=schema_obj.type, title=schema_obj.title, description=schema_obj.description, format=schema_obj.format)
            if schema_obj.model_extra:
                request_obj.__pydantic_extra__ = schema_obj.model_extra

        return request_obj
    
    raise ValueError(f"Invalid schema object: {schema_obj}")

def _get_tool_response_body(schema_obj: JsonSchemaObject | ToolResponseBody) -> ToolResponseBody:
    if schema_obj is None:
        return None
    
    if isinstance(schema_obj, ToolResponseBody):
        return schema_obj
        
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

        if schema_obj.type == 'string' and schema_obj.format is not None:
            response_obj.format = schema_obj.format

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

def import_flow_support_tools(model):     
    schedulable = False
    if "schedulable" in model["spec"]:
        schedulable = model["spec"]["schedulable"]

    logger.info(f"Import 'get_flow_status' tool spec...")
    tools = [create_flow_status_tool("i__get_flow_status_intrinsic_tool__")]

    if schedulable:
        get_schedule_tool = create_get_schedule_tool("i__get_schedule_intrinsic_tool__")
        delete_schedule_tool = create_delete_schedule_tool("i__delete_schedule_intrinsic_tool__")
        tools.extend([get_schedule_tool, delete_schedule_tool])

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
        http_path="/v1/flows",
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


def create_get_schedule_tool(name: str, TEMPUS_ENDPOINT: str="http://wxo-tempus-runtime:9044") -> dict:

    spec = ToolSpec(
        name=name,
        description="Use this tool to show the current schedules.",
        permission='read_only',
        display_name= "Get Schedules"
    )

    openapi_binding = OpenApiToolBinding(
        http_path="/v1/schedules/simple",
        http_method="GET",
        security=[],
        servers=[TEMPUS_ENDPOINT]
    )
    
    spec.binding = ToolBinding(openapi=openapi_binding)
    # Input Schema
    properties = {
        "query_schedule_id": {
            "type": "string",
            "title": "schedule_id",
            "description": "Identifies the schedule instance.",
            "in": "query"
        },
        "query_schedule_name": {
            "type": "string",
            "title": "schedule_name",
            "description": "Identifies the schedule name.",
            "in": "query"
        },
    }
    
    spec.input_schema = ToolRequestBody(
        type='object',
        properties=properties,
        required=[]
    )

    response_properties = {
        "schedule_id": {
            "type": "string",
        },
        "schedule_name": {
            "type": "string",
        },
        "schedule_data": {
            "type": "string",
        },
        "schedule_time": {
            "type": "string",
        }
    }

    spec.output_schema = ToolResponseBody(type='object',
                                          properties=response_properties,
                                          description='Return the information about the schedule.')

    return OpenAPITool(spec=spec)


def create_delete_schedule_tool(name: str, TEMPUS_ENDPOINT: str="http://wxo-tempus-runtime:9044") -> dict:

    spec = ToolSpec(
        name=name,
        description="Use this tool to delete/remove a schedule based on the schedule_id.",
        permission='read_only',
        display_name= "Delete Schedule"
    )

    openapi_binding = OpenApiToolBinding(
        http_path="/v1/schedules/{schedule_id}",
        http_method="DELETE",
        security=[],
        servers=[TEMPUS_ENDPOINT]
    )
    
    spec.binding = ToolBinding(openapi=openapi_binding)
    # Input Schema
    properties = {
        "path_schedule_id": {
            "type": "string",
            "title": "schedule_id",
            "description": "Identifies the schedule instance.",
            "in": "query"
        }
    }
    
    spec.input_schema = ToolRequestBody(
        type='object',
        properties=properties,
        required=[]
    )

    spec.output_schema = ToolResponseBody(type='object',
                                          description='Schedule deleted.')

    return OpenAPITool(spec=spec)

# Schema templates for standalone fields
FIELD_INPUT_SCHEMA_TEMPLATES = {
    # Text input templates
    "text": {
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "string"}},
            required=["value"],
            additionalProperties=False
        )
    },

    # Boolean input templates
    "boolean": {
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "boolean"}},
            required=["value"],
            additionalProperties=False
        )
    },

    # Number input templates
    "number": {
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "number"}},
            required=["value"],
            additionalProperties=False
        )
    },

    # Choice input templates
    "any": {
        "input": JsonSchemaObject(  # pyright: ignore[reportCallIssue]
            type='object',
            properties={
                "choices": {"type": "array", "items": {}},
                "display_items": {"type": "array", "items": {}},
                "display_text": {"type": "string"}
            },
            required=["choices"]
        ),
        "output": JsonSchemaObject(  # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "object", "properties": {}}},
            required=["value"],
            additionalProperties=False
        )
    },

    # Date input templates
    "date": {
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "string", "format": "date"}},
            required=["value"],
            additionalProperties=False # pyright: ignore[reportCallIssue]
        )
    },

    # File upload templates
    "file": {
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "string", "format": "wxo-file"}},
            required=["value"]
        )
    },
}

# Schema templates for standalone fields
FIELD_OUTPUT_SCHEMA_TEMPLATES = {
    # Text input templates
    "text": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "string"}},
            required=["value"]
        ),
    },

    # Choice input templates
    "array": {
        "input": JsonSchemaObject(  # pyright: ignore[reportCallIssue]
            type='object',
            properties={
                "choices": {"type": "array", "items": {}},
            },
            required=["value"]
        )
    },

    # File download templates
    "file": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "string", "format": "wxo-file"}},
            required=["value"]
        )
    },
}

# Schema templates for UserForm fields
FORM_SCHEMA_TEMPLATES = {
    # Text input templates
    "text": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"default": {"type": "string"}},
            required=[]
        ),
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "string"}},
            required=["value"]
        ),
        "ui": {
            "ui:widget": "TextWidget",
            "ui:title": ""  # Will be filled in
        }
    },
    
    # Boolean input templates
    "boolean": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"default": {"type": "boolean"}},
            required=[]
        ),
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "boolean"}},
            required=["value"]
        ),
        "ui": {
            "ui:widget": "CheckboxWidget",
            "ui:title": ""  # Will be filled in
        }
    },
    
    # Number input templates
    "number": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={},
            required=[]
        ),
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "number"}},
            required=["value"]
        ),
        "ui": {
            "ui:widget": "NumberWidget",
            "ui:title": ""  # Will be filled in
        }
    },
    
    # Date input templates
    "date": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={
                "default": {"type": "string", "format": "date"},
                "maximum": {"type": "string", "format": "date"},
                "minimum": {"type": "string", "format": "date"}
            },
            required=[]
        ),
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "string", "format": "date"}},
            required=["value"]
        ),
        "ui": {
            "ui:widget": "DateWidget",
            "ui:title": "",  # Will be filled in
            "format": "YYYY-MM-DD"
        }
    },
    
    # Date range templates
    "date_range": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={
                "value": {
                    "type": "object",
                    "properties": {
                        "maximum": {"type": "string", "format": "date"},
                        "minimum": {"type": "string", "format": "date"}
                    }
                }
            },
            required=["value"]
        ),
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={
                "value": {
                    "type": "object",
                    "properties": {
                        "end": {"type": "string", "format": "date"},
                        "start": {"type": "string", "format": "date"}
                    }
                }
            },
            required=["value"]
        ),
        "ui": {
            "ui:widget": "DateWidget",
            "format": "YYYY-MM-DD",
            "ui:options": {"range": True},
            "ui:order": ["start", "end"]
        }
    },
    
    # Choice input templates
    "choice": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={
                "choices": {"type": "array", "items": {}},
                "display_items": {"type": "array", "items": {}},
                "display_text": {"type": "string"},
                "default":{}
            },
            required=["choices"]
        ),
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "array"}},
            required=["value"]
        ),
        "ui": {
            "ui:widget": "ComboboxWidget",
            "ui:placeholder": ""
        }
    },
    
    # File upload templates
    "file": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={},
            required=[]
        ),
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "string", "format": "wxo-file"}},
            required=["value"]
        ),
        "ui": {
            "ui:widget": "FileUpload",
            "ui:upload_button_label": ""
        }
    },
    
    # Message output templates
    "message": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "string"}},
            required=["value"]
        ),
        "ui": {
            "ui:widget": "DataWidget",
            "ui:options": {"label": False}
        }
    },
    
    # List output templates
    "list": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"choices": {"type": "array", "items": {}}},
            required=["choices"]
        ),
        "ui": {
            "ui:widget": "BulletList"
        }
    },

    # List input template
    "list_input": {
        "input": JsonSchemaObject(
            type='object',
            properties={"default": {"type": "array", "items": {}}},
            required=["default"],
            additionalProperties=False
        ),
        "output": JsonSchemaObject(
            type='object',
            properties={"value": {"type": "array", "items": {}}},
            required=["value"],
            additionalProperties=False
        ),
        "ui": {
            "ui:widget": "EditableTable",
            "ui:options": {"label": False}
        }
    },
    
    # Field output templates
    "field": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"anyOf": [
                {"type": "string"}, {"type": "number"}, {"type": "integer"}, {"type": "boolean"}]}},
            required=["value"]
        ),
        "ui": {
            "ui:widget": "DataWidget",
            "ui:options": {"label": True}
        }
    }
}

def get_form_schema_template(template_type: str) -> Dict[str, Any]:
    """
    Get a schema template by type
    
    Args:
        template_type: The type of template to get ('text', 'boolean', etc.)
        
    Returns:
        dict: A dictionary containing the template schemas
        
    Raises:
        ValueError: If the template type is not found
    """

    if template_type == "any":
        template_type = "choice"
    elif template_type == "array":
        template_type = "list"

    if template_type not in FORM_SCHEMA_TEMPLATES:
        raise ValueError(f"Unknown template type: {template_type}")
        
    return FORM_SCHEMA_TEMPLATES[template_type]

def clone_form_schema(template_type: str, customize: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Clone a schema template and optionally customize it
    
    Args:
        template_type: The type of template to clone ('text', 'boolean', etc.)
        customize: Optional dict of customizations to apply
        
    Returns:
        dict: A dictionary containing cloned input_schema, output_schema, and ui_schema
        
    Raises:
        ValueError: If the template type is not found
    """
    template = get_form_schema_template(template_type)
    
    # Deep copy the schemas to avoid modifying templates
    result = {
        "input_schema": JsonSchemaObject.model_validate(template["input"].model_dump()),
        "output_schema": JsonSchemaObject.model_validate(template["output"].model_dump()) if "output" in template else None,
        "ui_schema": deepcopy(template["ui"])  # Simple dict copy is sufficient for UI schema
    }
    
    # Apply customizations if provided
    if customize:
        if "input" in customize and result["input_schema"]:
            for key, value in customize["input"].items():
                if key == "properties":
                    # Merge properties
                    if not result["input_schema"].properties:
                        result["input_schema"].properties = {}
                    result["input_schema"].properties.update(value)
                else:
                    # Set attribute directly
                    setattr(result["input_schema"], key, value)
                    
        if "output" in customize and result["output_schema"]:
            for key, value in customize["output"].items():
                if key == "properties":
                    # Merge properties
                    if not result["output_schema"].properties:
                        result["output_schema"].properties = {}
                    result["output_schema"].properties.update(value)
                else:
                    # Set attribute directly
                    setattr(result["output_schema"], key, value)
                    
        if "ui" in customize and result["ui_schema"]:
            result["ui_schema"].update(customize["ui"])
            
    return result

def get_all_tools_in_flow(flow: dict) -> list[str]:
    '''Get all tool names used in the flow'''
    tools: list[Any] = []

    # iterate over all key and values in a dict
    for key, value in flow['nodes'].items():
        spec = value.get("spec")
        kind: Any = spec.get("kind")
        if kind == 'tool':
            tool_name = spec.get('tool')
            # the tool name might be the format of name:uuid.. we just need the name
            tool_name = tool_name.split(':')[0]
            if tool_name not in tools:
                tools.append(tool_name)
        elif kind == 'foreach' or kind == "loop" or kind == "user_flow" or kind == "userflow":
            # recursively get all tools in the subflow
            embedded_tools: list[str] = get_all_tools_in_flow(value)
            # we need to merge with the tools in subflow but only if does not already exist in the parent tool list
            for tool in embedded_tools:
                if tool not in tools:
                    tools.append(tool)
    return tools