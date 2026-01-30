import importlib
import inspect
import json
import os
import sys
from types import MappingProxyType
from typing import Any, Callable, Dict, List, Optional, get_type_hints
import logging

from pydantic import TypeAdapter, BaseModel

from ibm_watsonx_orchestrate.run.context import AgentRun
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.agent_builder.connections import ExpectedCredentials
from .base_tool import BaseTool
from .types import JsonSchemaTokens, PythonToolKind, ToolSpec, ToolPermission, ToolRequestBody, ToolResponseBody, JsonSchemaObject, ToolBinding, \
    PythonToolBinding
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest, ToolContextException
from ibm_watsonx_orchestrate.agent_builder.tools._internal.tool_response import ToolResponse

_all_tools = []
logger = logging.getLogger(__name__)

JOIN_TOOL_PARAMS = {
    'original_query': str,
    'task_results': Dict[str, Any],
    'messages': List[Dict[str, Any]],
}

TOOLS_DYNAMIC_PARAM_FLAG = "x-ibm-dynamic-field"
TOOLS_DYNAMIC_SCHEMA_FLAG = "x-ibm-dynamic-schema"


def _parse_expected_credentials(expected_credentials: ExpectedCredentials | dict):
    parsed_expected_credentials = []
    if expected_credentials:
        for credential in expected_credentials:
            if isinstance(credential, ExpectedCredentials):
                parsed_expected_credentials.append(credential)
            else:
                parsed_expected_credentials.append(ExpectedCredentials.model_validate(credential))
    
    return parsed_expected_credentials
    

def _merge_dynamic_schema(base_schema: ToolRequestBody | ToolResponseBody, dynamic_schema: Optional[ToolRequestBody|ToolResponseBody]) -> None:
    """
    Merge dynamic schema properties and required fields into the base schema.
    Modifies base_schema in place.
    
    :param base_schema: The base schema to merge into
    :param dynamic_schema: The dynamic schema to merge from
    :raises ValueError: If duplicate property names are found between base and dynamic schemas
    """
    if not dynamic_schema:
        return
    
    # Initialize required list if None
    if base_schema.required is None:
        base_schema.required = []
    
    # Extend required fields from dynamic schema
    if dynamic_schema.required:
        base_schema.required.extend(dynamic_schema.required)
    
    # Initialize properties dict if None
    if base_schema.properties is None:
        base_schema.properties = {}
    
    # Update properties from dynamic schema
    if dynamic_schema.properties:
        # Check if dynamic schema has properties with the same name as properties in base schema
        duplicated_properties = set(base_schema.properties.keys()) & set(dynamic_schema.properties.keys())
        if duplicated_properties:
            logger.error(f"Dynamic schema can't have the same properties as base schema.\nDuplicate properties found: {duplicated_properties}")
            raise ValueError("Duplicate properties found")

        for prop_schema in dynamic_schema.properties.values():
            # JsonSchemaObject has extra='allow'
            setattr(prop_schema, TOOLS_DYNAMIC_PARAM_FLAG , True)
        base_schema.properties.update(dynamic_schema.properties)
        setattr(base_schema, TOOLS_DYNAMIC_SCHEMA_FLAG, True)


class PythonTool(BaseTool):
    def __init__(self,
                fn,
                name: str = None,
                description: str = None,
                input_schema: ToolRequestBody = None,
                output_schema: ToolResponseBody = None,
                permission: ToolPermission = ToolPermission.READ_ONLY,
                expected_credentials: List[ExpectedCredentials] = None,
                display_name: str = None,
                kind: PythonToolKind = PythonToolKind.TOOL,
                spec=None,
                enable_dynamic_input_schema: bool = False,
                enable_dynamic_output_schema: bool = False,
                dynamic_input_schema: Optional[ToolRequestBody] = None,
                dynamic_output_schema: Optional[ToolResponseBody] = None,
                ):
        self.fn = fn
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.permission = permission
        self.display_name = display_name
        self.kind = kind
        self.expected_credentials=_parse_expected_credentials(expected_credentials)
        self._spec = None
        if spec:
            self._spec = spec
        self.enable_dynamic_input_schema = enable_dynamic_input_schema
        self.enable_dynamic_output_schema = enable_dynamic_output_schema
        self.dynamic_input_schema = dynamic_input_schema
        self.dynamic_output_schema = dynamic_output_schema

    def __call__(self, *args, **kwargs):

        run_context_param = self.get_run_param()
        context_object = None

        if run_context_param:
            context_param_value = kwargs.get(run_context_param)
            if context_param_value:
                context_object = context_param_value if isinstance(context_param_value,AgentRun) \
                    else AgentRun(request_context=context_param_value)
                kwargs[run_context_param] = context_object


        result = self.fn(*args, **kwargs)
        context_updates = context_object.get_context_updates() if context_object else {}

        # Temporarily needed to address a backend limitation with nesting bytes
        if type(result) == bytes:
            return result

        return ToolResponse(content=result,context_updates=context_updates)

    
    @property
    def __tool_spec__(self):
        if self._spec:
            return self._spec
        
        import docstring_parser
        from langchain_core.tools.base import create_schema_from_function
        from langchain_core.utils.json_schema import dereference_refs

        if self.fn.__doc__ is not None:
            doc = docstring_parser.parse(self.fn.__doc__)
        else:
            doc = None

        _desc = self.description
        doc_arg_descriptions = {}

        if doc is not None:
            if self.description is None:
                _desc = doc.description
            
            doc_arg_descriptions = { arg.arg_name: arg.description for arg in doc.params }

        
        spec = ToolSpec(
            name=self.name or self.fn.__name__,
            display_name=self.display_name,
            description=_desc,
            permission=self.permission
        )

        spec.binding = ToolBinding(python=PythonToolBinding(function=''))

        linux_friendly_os_cwd = os.getcwd().replace("\\", "/")
        function_binding = (inspect.getsourcefile(self.fn)
                            .replace("\\", "/")
                            .replace(linux_friendly_os_cwd+'/', '')
                            .replace('.py', '')
                            .replace('/','.') +
                            f":{self.fn.__name__}")
        spec.binding.python.function = function_binding

        sig = inspect.signature(self.fn)
        
        # If the function is a join tool, validate its signature matches the expected parameters. If not, raise error with details.
        if self.kind == PythonToolKind.JOIN_TOOL:
            _validate_join_tool_func(self.fn, sig, spec.name)

        if not self.input_schema:
            input_schema_model = None
            try:
                input_schema_model: type[BaseModel] = create_schema_from_function(spec.name, self.fn, parse_docstring=True)
            except ValueError as e:
                err_msg = str(e)
                if "Found invalid Google-Style docstring" in err_msg:
                    logger.warning("Unable to properly parse parameter descriptions due to incorrectly formatted docstring. This may result in degraded agent performance. To fix this, please ensure the docstring conforms to Google's docstring format.")
                elif "in docstring not found in function signature." in err_msg:
                    logger.warning("Unable to properly parse parameter descriptions due to missing or incorrect type hints. This may result in degraded agent performance. To fix this, please ensure the tool inputs have type hints that match those in the docstring.")
                else:
                    logger.warning("Unable to properly parse parameter descriptions. This may result in degraded agent performance.")
            except Exception as e:
                logger.warning("Unable to properly parse parameter descriptions. This may result in degraded agent performance.")
            finally:
                if not input_schema_model:   
                    input_schema_model: type[BaseModel] = create_schema_from_function(spec.name, self.fn, parse_docstring=False)

            input_schema_json_original = input_schema_model.model_json_schema()
            input_schema_json = dereference_refs(input_schema_json_original)
            # fix missing default during dereference
            for k, v in input_schema_json.get("properties", {}).items():
                # in case of args like `specialty: HealthcareSpeciality = HealthcareSpeciality.GENERAL_MEDICINE`
                # the default value is lost during `dereference_refs`
                if isinstance(input_schema_json_original.get("properties", {}).get(k, {}).get("default"), str) and \
                    v.get("type") == "string" and v.get("default") is None:
                    v["default"] = input_schema_json_original.get("properties", {}).get(k, {}).get("default")
                # in case the original arg has description but the reference doesn't
                if v.get("description") is None:
                    if input_schema_json_original.get("properties", {}).get(k, {}).get("description"):
                        v["description"] = input_schema_json_original.get("properties", {}).get(k, {}).get("description")
                    elif doc_arg_descriptions.get(k,None):
                        v["description"] = doc_arg_descriptions[k]
                    
                
            # Convert the input schema to a JsonSchemaObject
            input_schema_obj = JsonSchemaObject(**input_schema_json)
            input_schema_obj = _fix_optional(input_schema_obj)

            spec.input_schema = ToolRequestBody(
                type='object',
                properties=input_schema_obj.properties or {},
                required=input_schema_obj.required or []
            )
        else:
            spec.input_schema = self.input_schema

        # Extract context param and note the param name in the tool binding
        context_param = _extract_context_param(name=self.name, input_schema=spec.input_schema)

        if context_param:
            spec.binding.python.agent_run_paramater = context_param



        # Merge dynamic input schema if provided
        if self.enable_dynamic_input_schema:
            _merge_dynamic_schema(spec.input_schema, self.dynamic_input_schema)
        
        _validate_input_schema(spec.input_schema, self.enable_dynamic_input_schema)

        if not self.output_schema:
            ret = sig.return_annotation
            if ret != sig.empty:
                _schema = dereference_refs(TypeAdapter(ret).json_schema())
                if '$defs' in _schema:
                    _schema.pop('$defs')
                spec.output_schema = _fix_optional(ToolResponseBody(**_schema))

                if _schema.get('type') == 'string' and _schema.get('format', None) is not None:
                    spec.output_schema.format = _schema.get('format')

            else:
                spec.output_schema = ToolResponseBody()

            if doc is not None and doc.returns is not None and doc.returns.description is not None:
                spec.output_schema.description = doc.returns.description

        else:
            spec.output_schema = ToolResponseBody()

        if self.enable_dynamic_output_schema:
            _merge_dynamic_schema(spec.output_schema, self.dynamic_output_schema)
        
         # Validate the generated schema still conforms to the requirement for a join tool
        if self.kind == PythonToolKind.JOIN_TOOL:
            if not spec.is_custom_join_tool():
                raise ValueError(f"Join tool '{spec.name}' does not conform to the expected join tool schema. Please ensure the input schema has the required fields: {JOIN_TOOL_PARAMS.keys()} and the output schema is a string.")
        

        self._spec = spec
        return spec
    
    def get_run_param(self):
        return self.__tool_spec__.binding.python.agent_run_paramater
    
    @staticmethod
    def from_spec(file: str) -> 'PythonTool':
        with safe_open(file, 'r') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                spec = ToolSpec.model_validate(yaml_safe_load(f))
            elif file.endswith('.json'):
                spec = ToolSpec.model_validate(json.load(f))
            else:
                raise BadRequest('file must end in .json, .yaml, or .yml')

        if spec.binding.python is None:
            raise BadRequest('failed to load python tool as the tool had no python binding')

        [module, fn_name] = spec.binding.python.function.split(':')
        fn = getattr(importlib.import_module(module), fn_name)

        return PythonTool(fn=fn, spec=spec)

    def __repr__(self):
        return f"PythonTool(fn={self.__tool_spec__.binding.python.function}, name='{self.__tool_spec__.name}', display_name='{self.__tool_spec__.display_name or ''}', description='{self.__tool_spec__.description}')"

    def __str__(self):
        return self.__repr__()

def _fix_optional(schema):
    if schema.properties is None:
        return schema
    # Pydantic tends to create types of anyOf: [{type: thing}, {type: null}] instead of simply
    # while simultaneously marking the field as required, which can be confusing for the model.
    # This removes union types with null and simply marks the field as not required
    not_required = []
    replacements = {}
    if schema.required is None:
        schema.required = []
    for k, v in schema.properties.items():
        # Simple null type & required -> not required
        if v.type == 'null' and k in schema.required:
            not_required.append(k)
        # Optional with null & required
        if v.anyOf is not None and [x for x in v.anyOf if x.type == 'null']:
            if k in schema.required:
            # required with default -> not required 
            # required without default -> required & remove null from union
                if v.default is not None:
                    not_required.append(k)
                else:
                    v.anyOf = list(filter(lambda x: x.type != 'null', v.anyOf))
                if len(v.anyOf) == 1:
                    replacements[k] = v.anyOf[0]
            else:
            # not required with default -> no change
            # not required without default -> means default input is 'None'
            # if None is returned here then the creation of the jsonchema will remove the key
            # so instead we use an Identifier, which is replaced later
                v.default = JsonSchemaTokens.NONE if v.default is None else v.default

    schema.required = list(filter(lambda x: x not in not_required, schema.required if schema.required is not None else []))
    for k, v in replacements.items():
        combined = {
            **schema.properties[k].model_dump(exclude_unset=True, exclude_none=True),
            **v.model_dump(exclude_unset=True, exclude_none=True)
        }
        schema.properties[k] = JsonSchemaObject(**combined)
        schema.properties[k].anyOf = None
        
    for k, v in schema.properties.items():
        if v.anyOf:
            new_any_of = []
            for item in v.anyOf:
                if item.type == 'object':
                    new_any_of.append(_fix_optional(item))
                else:
                    new_any_of.append(item)
            v.anyOf = new_any_of
        elif v.type == 'object':
            schema.properties[k] = _fix_optional(v)

    return schema

def _validate_input_schema(input_schema: ToolRequestBody, enable_dynamic_schema: bool) -> None:
    props = input_schema.properties
    
    # Remove kwargs if dynamic schema is enabled
    if enable_dynamic_schema and "kwargs" in props:
        del props["kwargs"]
    
    for prop in props:
        property_schema = props.get(prop)
        if not (property_schema.type or property_schema.anyOf):
            logger.warning(f"Missing type hint for tool property '{prop}' defaulting to 'str'. To remove this warning add a type hint to the property in the tools signature. See Python docs for guidance: https://docs.python.org/3/library/typing.html")

def _validate_join_tool_func(fn: Callable, sig: inspect.Signature | None = None, name: str | None = None) -> None:
    if sig is None:
        sig = inspect.signature(fn)
    if name is None:
        name = fn.__name__
    
    params = sig.parameters
    type_hints = get_type_hints(fn)
    
    # Validate parameter order
    actual_param_names = list(params.keys())
    expected_param_names = list(JOIN_TOOL_PARAMS.keys())
    if actual_param_names[:len(expected_param_names)] != expected_param_names:
        raise ValueError(
            f"Join tool function '{name}' has incorrect parameter names or order. Expected: {expected_param_names}, got: {actual_param_names}"
        )
    
    # Validate the type hints
    for param, expected_type in JOIN_TOOL_PARAMS.items():
        if param not in type_hints:
            raise ValueError(f"Join tool function '{name}' is missing type for parameter '{param}'")
        actual_type = type_hints[param]
        if actual_type != expected_type:
            raise ValueError(f"Join tool function '{name}' has incorrect type for parameter '{param}'. Expected {expected_type}, got {actual_type}")

def _extract_context_param(name: str, input_schema: ToolRequestBody) -> Optional[str]:
    agent_run_param = None

    if input_schema.properties:
        for k,v in input_schema.properties.items():
            if v.title == 'AgentRun':
                if agent_run_param:
                    raise ToolContextException(f"Tool {name} has multiple run context objects")
                agent_run_param = k

    # if agent_run_param:
    #     if agent_run_param in input_schema.properties:
    #         del input_schema.properties[agent_run_param]
    #     if agent_run_param in input_schema.required:
    #         input_schema.required.remove(agent_run_param)

    return agent_run_param


def tool(
    *args,
    name: str = None,
    description: str = None,
    input_schema: ToolRequestBody = None,
    output_schema: ToolResponseBody = None,
    permission: ToolPermission = ToolPermission.READ_ONLY,
    expected_credentials: List[ExpectedCredentials] = None,
    display_name: str = None,
    kind: PythonToolKind = PythonToolKind.TOOL,
    enable_dynamic_input_schema: bool = False,
    enable_dynamic_output_schema: bool = False,
    dynamic_input_schema: Optional[ToolRequestBody | dict] = None,
    dynamic_output_schema: Optional[ToolResponseBody | dict] = None,
) -> Callable[[{__name__, __doc__}], PythonTool]:
    """
    Decorator to convert a python function into a callable tool.

    :param name: the agent facing name of the tool (defaults to the function name)
    :param description: the description of the tool (used for tool routing by the agent)
    :param input_schema: the json schema args to the tool
    :param output_schema: the response json schema for the tool
    :param permission: the permissions needed by the user of the agent to invoke the tool
    :param enable_dynamic_input_schema: if dynamic input schema is enabled
    :param enable_dynamic_output_schema: if dynamic output schema is enabled
    :param dynamic_input_schema: the dynamic input schema for the tool - used to validate params passed under **kwargs
    :param dynamic_output_schema: the dynamic output schema for the tool - used to validate dynamic return values
    :return:
    """
    # inspiration: https://github.com/pydantic/pydantic/blob/main/pydantic/validate_call_decorator.py    
    if dynamic_input_schema and not isinstance(dynamic_input_schema, ToolRequestBody):
        dynamic_input_schema = ToolRequestBody(**dynamic_input_schema)

    if dynamic_output_schema and not isinstance(dynamic_output_schema, ToolResponseBody):
        dynamic_output_schema = ToolResponseBody(**dynamic_output_schema)

    def _tool_decorator(fn):

        t = PythonTool(
            fn=fn,
            name=name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            permission=permission,
            expected_credentials=expected_credentials,
            display_name=display_name,
            kind=kind,
            enable_dynamic_input_schema=enable_dynamic_input_schema,
            enable_dynamic_output_schema=enable_dynamic_output_schema,
            dynamic_input_schema=dynamic_input_schema,
            dynamic_output_schema=dynamic_output_schema
        )
            
        _all_tools.append(t)
        return t

    if len(args) == 1 and callable(args[0]):
        return _tool_decorator(args[0])
    return _tool_decorator


def get_all_python_tools():
    return [t for t in _all_tools]
