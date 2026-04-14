import importlib
import inspect
import re
import logging
import uuid
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

from enum import Enum
class Operator(str, Enum):
    """Supported operators for RuleBuilder conditions."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"

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
     "time": {
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "string", "format": "time"}},
            required=["value"],
            additionalProperties=False # pyright: ignore[reportCallIssue]
        )
    },
     "datetime": {
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "string", "format": "datetime"}},
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
                "max_date": {"type": "string", "format": "date"},
                "min_date": {"type": "string", "format": "date"}
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
    
    # Time input templates
    "time": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={
                "default": {"type": "string", "format": "time"}
            },
            required=[]
        ),
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "string", "format": "time"}},
            required=["value"]
        ),
        "ui": {
            "ui:widget": "TimeWidget",
            "ui:title": "",  # Will be filled in
        }
    },
    
    # DateTime input templates
    "datetime": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={
                "default": {"type": "string", "format": "date-time"}
            },
            required=[]
        ),
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "string", "format": "date-time"}},
            required=["value"]
        ),
        "ui": {
            "ui:widget": "TimeWidget",
            "ui:title": "",  # Will be filled in
        }
    },
    
    # Date range templates
    "date_range": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={
                "default_start": {"type": "string", "format": "date"},
                "default_end": {"type": "string", "format": "date"},
                "value": {
                    "type": "object",
                    "properties": {
                        "max_date": {"type": "string", "format": "date"},
                        "min_date": {"type": "string", "format": "date"}
                    }
                }
            },
            required=[]
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
    
    # Time range templates
    "time_range": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={
                "default_start": {"type": "string", "format": "time"},
                "default_end": {"type": "string", "format": "time"}
            },
            required=[]
        ),
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={
                "value": {
                    "type": "object",
                    "properties": {
                        "end": {"type": "string", "format": "time"},
                        "start": {"type": "string", "format": "time"}
                    }
                }
            },
            required=["value"]
        ),
        "ui": {
            "ui:widget": "TimeWidget",
            "ui:options": {"is_range": True, "is_timezone": True, "is_datepicker": False},
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
            properties={
                "min_num_files": {"type": "integer"},
                "max_num_files": {"type": "integer"}
            },
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
    },
    
    # User input templates
    "user": {
        "input": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={
                "min_num_users": {"type": "number"},
                "max_num_users": {"type": "number"}
            },
            required=[]
        ),
        "output": JsonSchemaObject( # pyright: ignore[reportCallIssue]
            type='object',
            properties={"value": {"type": "array", "items": {"type": "string", "format": "wxo-user"}}},
            required=["value"],
            additionalProperties=False
        ),
        "ui": {
            "ui:widget": "UserWidget",
            "ui:title": ""  # Will be filled in
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
            tool_name = parse_tool_name_id(tool_name)[0]
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

# Dynamic Forms Helper Functions

def create_allof_condition(conditions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Create an allOf (AND) condition for combining multiple field conditions.
    
    Args:
        conditions: List of condition dictionaries, each with properties
        
    Returns:
        Dictionary with allOf structure
        
    Example:
        create_allof_condition([
            {"properties": {"field1": {"const": "A"}}},
            {"properties": {"field2": {"const": "B"}}}
        ])
        # Returns: {"allOf": [{"properties": {"field1": {"const": "A"}}}, ...]}
    """
    return {"allOf": conditions}


def create_anyof_condition(conditions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Create an anyOf (OR) condition for alternative field conditions.
    
    Args:
        conditions: List of condition dictionaries, each with properties
        
    Returns:
        Dictionary with anyOf structure
        
    Example:
        create_anyof_condition([
            {"properties": {"field1": {"const": "A"}}},
            {"properties": {"field1": {"const": "B"}}}
        ])
        # Returns: {"anyOf": [{"properties": {"field1": {"const": "A"}}}, ...]}
    """
    return {"anyOf": conditions}


def create_json_schema_condition(
    if_condition: dict[str, Any],
    then_effect: dict[str, Any],
    else_effect: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Create a JSON Schema if/then/else condition structure for dynamic forms.
    
    Supports simple conditions with single field checks, as well as complex
    conditions using allOf (AND) and anyOf (OR) operators. Can be nested
    for multi-level conditional logic.
    
    Args:
        if_condition: The condition to evaluate (can include allOf/anyOf)
        then_effect: The effect to apply when condition is true
        else_effect: Optional effect to apply when condition is false
        
    Returns:
        Dictionary with if/then/else structure
        
    Example (simple):
        create_json_schema_condition(
            if_condition={"properties": {"country": {"const": "USA"}}},
            then_effect={"properties": {"zipcode": {"x-is-visible": True}}},
            else_effect={"properties": {"zipcode": {"x-is-visible": False}}}
        )
        
    Example (complex with allOf):
        create_json_schema_condition(
            if_condition=create_allof_condition([
                {"properties": {"field1": {"const": "A"}}},
                {"properties": {"field2": {"const": "B"}}}
            ]),
            then_effect={"properties": {"field3": {"title": "Both A and B"}}},
            else_effect={"properties": {"field3": {"title": "Other"}}}
        )
        
    Example (nested):
        create_json_schema_condition(
            if_condition={"properties": {"field1": {"const": "A"}}},
            then_effect={"properties": {"field2": {"title": "Option A"}}},
            else_effect=create_json_schema_condition(
                if_condition={"properties": {"field1": {"const": "B"}}},
                then_effect={"properties": {"field2": {"title": "Option B"}}},
                else_effect={"properties": {"field2": {"title": "Other"}}}
            )
        )
    """
    condition = {
        "if": if_condition,
        "then": then_effect
    }
    
    if else_effect is not None:
        condition["else"] = else_effect
    
    return condition

def _build_operator_condition(field_name: str, field_value: Any, operator: str) -> dict[str, Any]:
    """
    Build JSON Schema condition based on operator type.
    
    Args:
        field_name: The field to check
        field_value: The value to compare against
        operator: One of: "equals", "not_equals", "minimum", "maximum"
        
    Returns:
        JSON Schema condition dictionary
        
    Raises:
        ValueError: If operator is not supported
        
    Example:
        _build_operator_condition("age", 18, "minimum")
        # Returns: {"properties": {"age": {"minimum": 18}}}
    """
    if operator == Operator.EQUALS:
        return {"properties": {field_name: {"const": field_value}}}
    elif operator == Operator.NOT_EQUALS:
        return {"properties": {field_name: {"not": {"const": field_value}}}}
    elif operator == Operator.MINIMUM:
        return {"properties": {field_name: {"minimum": field_value}}}
    elif operator == Operator.MAXIMUM:
        return {"properties": {field_name: {"maximum": field_value}}}
    else:
        valid_operators = [op.value for op in Operator]
        raise ValueError(
            f"Unsupported operator: '{operator}'. Must be one of: {valid_operators}"
        )

def create_visibility_condition(
    field_name: str,
    field_value: Any,
    impacted_field: str,
    visible_when_true: bool = True,
    operator: str = None
) -> dict[str, Any]:
    """
    Create a visibility condition for showing/hiding fields based on another field's value.
    
    Args:
        field_name: The field to check
        field_value: The value to compare against
        impacted_field: The field whose visibility will be controlled
        visible_when_true: Whether to show (True) or hide (False) when condition matches
        
    Returns:
        Complete condition dictionary with if/then/else structure
        
    Raises:
        ValueError: If operator is not provided or is invalid
        
    Examples:
        # Equals operator
        create_visibility_condition(
            field_name="country",
            field_value="USA",
            impacted_field="zipcode",
            visible_when_true=True,
            operator="equals"
        )
        # Shows zipcode when country equals USA, hides it otherwise
        
        # Not equals operator
        create_visibility_condition(
            field_name="country",
            field_value="USA",
            impacted_field="international_shipping",
            visible_when_true=True,
            operator="not_equals"
        )
        # Shows international_shipping when country is NOT USA
        
        # Minimum operator (>=)
        create_visibility_condition(
            field_name="age",
            field_value=18,
            impacted_field="adult_content",
            visible_when_true=True,
            operator="minimum"
        )
        # Shows adult_content when age >= 18
    """
    if operator is None:
        raise ValueError("operator parameter is required. Must be one of: equals, not_equals, minimum, maximum")
    
    return create_json_schema_condition(
        if_condition={"properties": {field_name: {"const": field_value}}},
        then_effect={"properties": {impacted_field: {"x-is-visible": visible_when_true}}},
        else_effect={"properties": {impacted_field: {"x-is-visible": not visible_when_true}}}
    )


def create_label_condition(
    field_name: str,
    field_value: Any,
    impacted_field: str,
    label_when_true: str,
    label_when_false: str,
    operator: str = None
) -> dict[str, Any]:
    """
    Create a label condition for changing field labels based on another field's value.
    
    Args:
        field_name: The field to check
        field_value: The value to compare against
        impacted_field: The field whose label will be changed
        label_when_true: Label to use when condition matches
        label_when_false: Label to use when condition doesn't match
        operator: Comparison operator - one of: "equals", "not_equals", "minimum", "maximum" (required)
        
    Returns:
        Complete condition dictionary with if/then/else structure
        
    Raises:
        ValueError: If operator is not provided or is invalid
        
    Examples:
        # Equals operator
        create_label_condition(
            field_name="country",
            field_value="USA",
            impacted_field="region",
            label_when_true="State",
            label_when_false="Province"
        )
        # Changes region label to "State" for USA, "Province" otherwise

        # Maximum operator (<=)
        create_label_condition(
            field_name="age",
            field_value=65,
            impacted_field="discount_type",
            label_when_true="Senior Discount",
            label_when_false="Regular Price",
            operator="maximum"
        )
        # Changes label to "Senior Discount" when age <= 65
    """
    if operator is None:
        raise ValueError("operator parameter is required. Must be one of: equals, not_equals, minimum, maximum")
    return create_json_schema_condition(
        if_condition=_build_operator_condition(field_name, field_value, operator),
        then_effect={"properties": {impacted_field: {"title": label_when_true}}},
        else_effect={"properties": {impacted_field: {"title": label_when_false}}}
    )


def create_tool_input_map(mappings: list[dict[str, str]]) -> dict[str, Any]:
    """
    Create a tool input map for value source behaviours.
    
    Args:
        mappings: List of mapping dictionaries with keys:
            - target_variable: Target tool input parameter (e.g., "self.tool.input.country")
            - value_expression: Source expression (e.g., "parent.field.country" for form fields)
            - assignment_type: Type of assignment ("field", "literal", or "variable")
            
    Returns:
        DataMapSpec dictionary structure
        
    Example:
        For referencing a form field in value-source behaviour:
        create_tool_input_map([
            {
                "target_variable": "self.tool.input.country",
                "value_expression": "parent.field.country",
                "assignment_type": "field"
            }
        ])
        
    Note:
        - Use "parent.field.fieldName" to reference form fields in Chat UI
        - Use "self.tool.input.paramName" for tool input parameters
        - Field names are case-sensitive
    """
    from .data_map import Assignment
    
    maps = []
    for mapping in mappings:
        assignment = Assignment(
            target_variable=mapping["target_variable"],
            value_expression=mapping["value_expression"],
            metadata={"assignmentType": mapping.get("assignment_type", "field")}
        )
        maps.append(assignment.model_dump())
    
    return {
        "spec": {
            "maps": maps
        }
    }


def validate_behaviour_field_references(form_fields: list[str], behaviour: dict[str, Any]) -> list[str]:
    """
    Validate that all field references in a behaviour exist in the form.
    
    Args:
        form_fields: List of field names in the form
        behaviour: Behaviour dictionary to validate
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Check on_change_to_field
    if "on_change_to_field" in behaviour:
        field = behaviour["on_change_to_field"]
        if field not in form_fields:
            errors.append(f"on_change_to_field '{field}' does not exist in form")
    
    # Check impacted_field in behaviours
    if "behaviours" in behaviour:
        for rule in behaviour["behaviours"]:
            if "impacted_field" in rule:
                field = rule["impacted_field"]
                if field not in form_fields:
                    errors.append(f"impacted_field '{field}' does not exist in form")
    
    return errors


def validate_tool_format(tool: str) -> bool:
    """
    Validate that a tool identifier is in the correct format "name:uuid".
    
    Args:
        tool: Tool identifier string
        
    Returns:
        True if valid, False otherwise
    """
    if not tool or ':' not in tool:
        return False
    
    parts = tool.split(':')
    if len(parts) != 2:
        return False
    
    name, uuid_part = parts
    if not name or not uuid_part:
        return False
    
    # Basic UUID format check (8-4-4-4-12 hex digits)
    import re
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, uuid_part, re.IGNORECASE))


def detect_circular_dependencies(behaviours: list[dict[str, Any]]) -> list[str]:
    """
    Detect circular dependencies in behaviour definitions.
    
    Args:
        behaviours: List of behaviour dictionaries
        
    Returns:
        List of error messages describing circular dependencies (empty if none)
    """
    errors = []
    
    # Build dependency graph
    dependencies = {}
    for behaviour in behaviours:
        trigger = behaviour.get("on_change_to_field")
        if not trigger:
            continue
            
        impacted = set()
        if "behaviours" in behaviour:
            for rule in behaviour["behaviours"]:
                if "impacted_field" in rule:
                    impacted.add(rule["impacted_field"])
        
        dependencies[trigger] = impacted
    
    # Check for cycles using DFS
    def has_cycle(node: str, visited: set, rec_stack: set, path: list) -> bool:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        if node in dependencies:
            for neighbor in dependencies[node]:
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack, path):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    errors.append(f"Circular dependency detected: {' -> '.join(cycle)}")
                    return True
        
        path.pop()
        rec_stack.remove(node)
        return False
    
    visited = set()
    for node in dependencies:
        if node not in visited:
            has_cycle(node, visited, set(), [])
    
    return errors
    return tools


def is_valid_uuid(value: str) -> bool:
    """
    Check if a string is a valid UUID.
    
    Args:
        value: String to check
        
    Returns:
        True if the string is a valid UUID, False otherwise
    """
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def parse_tool_name_id(tool: str) -> tuple[str, str | None]:
    """
    Parse tool name and ID from a tool string.
    
    Supports multiple formats:
    1. tool_name -> (tool_name, None)
    2. tool_name:tool_id -> (tool_name, tool_id) where tool_id is a UUID
    3. MCP_kit:MCP_tool_name -> (MCP_kit:MCP_tool_name, None)
    4. MCP_kit:MCP_tool_name:MCP_tool_id -> (MCP_kit:MCP_tool_name, MCP_tool_id) where MCP_tool_id is a UUID
    
    The last portion after a colon is treated as a tool_id only if it's a valid UUID.
    Otherwise, the entire string is treated as the tool name.
    
    Args:
        tool: Tool string to parse
        
    Returns:
        (tool_name, tool_id) where tool_id is None if not present or not a UUID
    """
    name_part, sep, id_part = tool.rpartition(":")
    
    if sep and is_valid_uuid(id_part):
        return name_part, id_part
    
    return tool, None

def normalize_and_validate_tool_spec(tool_spec_raw: dict) -> ToolSpec:
    """
    Normalize and validate a tool spec.
    
    Removes empty dict {} for schemas before validation to let Pydantic use defaults.
    This prevents validation errors when the server returns empty schemas.
    
    Args:
        tool_spec_raw: Raw tool spec from the server
        
    Returns:
        Validated ToolSpec object
    """
    if 'output_schema' in tool_spec_raw and tool_spec_raw['output_schema'] == {}:
        del tool_spec_raw['output_schema']
    if 'input_schema' in tool_spec_raw and tool_spec_raw['input_schema'] == {}:
        del tool_spec_raw['input_schema']
    return ToolSpec.model_validate(tool_spec_raw)


class RuleBuilder:
    """
    Builder class for creating user-friendly form behavior rules.
    
    This class provides static methods to create rules for dynamic forms
    without requiring knowledge of JSON Schema condition syntax. It wraps
    the existing helper functions and provides a consistent API.
    
    Example:Supported operators:
        - "equals": Exact match (field == value)
        - "not_equals": Not equal (field != value)
        - "minimum": Greater than or equal (field >= value)
        - "maximum": Less than or equal (field <= value)
    
    Examples:
        # Create label rules with equals operator
        rules = [
            RuleBuilder.label_rule(
                field_name="country",
                field_value="USA",
                impacted_field="region",
                label_when_true="State",
                label_when_false="Province",
                operator="equals"
            )
        ]
        
        # Create visibility rules with minimum operator
        rules = [
            RuleBuilder.visibility_rule(
                field_name="age",
                field_value=18,
                impacted_field="adult_content",
                visible_when_true=True,
                operator="minimum"
            )
        ]
    """
    
    @staticmethod
    def label_rule(
        field_name: str,
        field_value: Any,
        impacted_field: str,
        label_when_true: str,
        label_when_false: str,
        operator: str = None
    ) -> dict[str, Any]:
        """
        Create a rule that changes a field's label based on another field's value.
        
        Args:
            field_name: The field to monitor for changes
            field_value: The value to check against
            impacted_field: The field whose label will change
            label_when_true: Label to display when condition matches
            label_when_false: Label to display when condition doesn't match
            operator: Comparison operator - one of: "equals", "not_equals", "minimum", "maximum" (required)
            
        Returns:
            Complete rule dictionary ready for use in label_behaviour_field
            
        Raises:
            ValueError: If operator is not provided or is invalid
            
        Examples:
            # Equals operator
            RuleBuilder.label_rule(
                field_name="country",
                field_value="USA",
                impacted_field="code",
                label_when_true="Zip code",
                label_when_false="Postal code",
                operator="equals"
            )
            
            # Maximum operator (<=)
            RuleBuilder.label_rule(
                field_name="age",
                field_value=65,
                impacted_field="discount_type",
                label_when_true="Senior Discount",
                label_when_false="Regular Price",
                operator="maximum"
            )
        """
        return {
            "condition": create_label_condition(
                field_name=field_name,
                field_value=field_value,
                impacted_field=impacted_field,
                label_when_true=label_when_true,
                label_when_false=label_when_false,
                operator=operator
            ),
            "impacted_field": impacted_field
        }
    
    @staticmethod
    def visibility_rule(
        field_name: str,
        field_value: Any,
        impacted_field: str,
        visible_when_true: bool = True,
        operator: str = None
    ) -> dict[str, Any]:
        """
        Create a rule that shows or hides a field based on another field's value.
        
        Args:
            field_name: The field to monitor for changes
            field_value: The value to check against
            impacted_field: The field whose visibility will be controlled
            visible_when_true: Whether to show (True) or hide (False) when condition matches
            operator: Comparison operator - one of: "equals", "not_equals", "minimum", "maximum" (required)
            
        Returns:
            Complete rule dictionary ready for use in visibility_behaviour_field
            
        Raises:
            ValueError: If operator is not provided or is invalid
            
        Examples:
            # Equals operator
            RuleBuilder.visibility_rule(
                field_name="country",
                field_value="USA",
                impacted_field="city",
                visible_when_true=True,
                operator="equals"
            )
            
            # Not equals operator
            RuleBuilder.visibility_rule(
                field_name="country",
                field_value="USA",
                impacted_field="international_shipping",
                visible_when_true=True,
                operator="not_equals"
            )
            
            # Minimum operator (>=)
            RuleBuilder.visibility_rule(
                field_name="age",
                field_value=18,
                impacted_field="adult_content",
                visible_when_true=True,
                operator="minimum"
            )
        """
        return {
            "condition": create_visibility_condition(
                field_name=field_name,
                field_value=field_value,
                impacted_field=impacted_field,
                visible_when_true=visible_when_true,
                operator=operator
            ),
            "impacted_field": impacted_field
        }
    
    @staticmethod
    def custom_rule(
        if_condition: dict[str, Any],
        then_effect: dict[str, Any],
        else_effect: dict[str, Any] | None,
        impacted_field: str
    ) -> dict[str, Any]:
        """
        Create a custom rule with full control over JSON Schema conditions.
        
        Use this for advanced scenarios not covered by label_rule or visibility_rule.
        
        ** This is intended to be used later if runtime supports nested
           conditions and rules **
        
        Args:
            if_condition: The condition to evaluate
            then_effect: Effect to apply when condition is true
            else_effect: Effect to apply when condition is false (optional)
            impacted_field: The field affected by this rule
            
        Returns:
            Complete rule dictionary ready for use in behavior fields
            
        Example:
            RuleBuilder.custom_rule(
                if_condition={"properties": {"field1": {"const": "value"}}},
                then_effect={"properties": {"field2": {"title": "New Label"}}},
                else_effect={"properties": {"field2": {"title": "Default"}}},
                impacted_field="field2"
            )
        """
        return {
            "condition": create_json_schema_condition(
                if_condition=if_condition,
                then_effect=then_effect,
                else_effect=else_effect
            ),
            "impacted_field": impacted_field
        }


def create_value_source_config(
    tool_name: str,
    tool_id: str,
    field_mappings: dict[str, str],
    client: Any = None
) -> dict[str, Any]:
    """
    Create configuration for value_source_behaviour_field with simplified API.
    
    This helper function simplifies the creation of value source behaviors by:
    1. Auto-fetching tool schema from the API (if client provided)
    2. Auto-constructing the tool parameter in "name:id" format
    3. Auto-generating the tool_input_map from simple field mappings
    
    Args:
        tool_name: Name of the tool (e.g., "get_states_or_provinces")
        tool_id: UUID of the tool (e.g., "9f0ecb53-dbd9-4e41-be46-29c8d47d6df8")
        field_mappings: Dictionary mapping tool parameters to form field expressions
                       Format: {"tool_param": "parent.field.form_field"}
        client: Optional ToolClient instance to auto-fetch tool schema
        
    Returns:
        Dictionary with 'tool', 'tool_input_schema', and 'tool_input_map' keys
        
    Example:
        from ibm_watsonx_orchestrate.client import WxOClient
        
        client = WxOClient()
        config = create_value_source_config(
            tool_name="get_states_or_provinces",
            tool_id="9f0ecb53-dbd9-4e41-be46-29c8d47d6df8",
            field_mappings={
                "country": "parent.field.country"
            },
            client=client.tools
        )
        
        # Use in form
        form_node.value_source_behaviour_field(
            name="value_source",
            on_change_to_field="country",
            impacted_field="region",
            **config
        )
    """
    # Construct tool parameter in required format
    tool = f"{tool_name}:{tool_id}"
    
    # Fetch tool schema if client provided
    tool_input_schema = None
    if client:
        try:
            tool_spec = client.get_draft_by_id(tool_id)
            if tool_spec and isinstance(tool_spec, dict):
                tool_input_schema = tool_spec.get('input_schema')
        except Exception as e:
            logger.warning(f"Failed to fetch tool schema for {tool_name}:{tool_id}: {e}")
    
    # Generate tool_input_map from field_mappings
    tool_input_map = create_tool_input_map([
        {
            "target_variable": f"self.tool.input.{param}",
            "value_expression": expr,
            "assignment_type": "variable"
        }
        for param, expr in field_mappings.items()
    ])
    
    return {
        "tool": tool,
        "tool_input_schema": tool_input_schema,
        "tool_input_map": tool_input_map
    }