import importlib
import inspect
import json
import os
from typing import Any, Callable, Dict, List, get_type_hints
import logging

import docstring_parser
from langchain_core.tools.base import create_schema_from_function
from langchain_core.utils.json_schema import dereference_refs
from pydantic import TypeAdapter, BaseModel

from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from ibm_watsonx_orchestrate.agent_builder.connections import ExpectedCredentials
from .base_tool import BaseTool
from .types import PythonToolKind, ToolSpec, ToolPermission, ToolRequestBody, ToolResponseBody, JsonSchemaObject, ToolBinding, \
    PythonToolBinding

_all_tools = []
logger = logging.getLogger(__name__)

JOIN_TOOL_PARAMS = {
    'original_query': str,
    'task_results': Dict[str, Any],
    'messages': List[Dict[str, Any]],
}

class PythonTool(BaseTool):
    def __init__(self, fn, spec: ToolSpec, expected_credentials: List[ExpectedCredentials]=None):
        BaseTool.__init__(self, spec=spec)
        self.fn = fn
        self.expected_credentials=expected_credentials

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

    @staticmethod
    def from_spec(file: str) -> 'PythonTool':
        with open(file, 'r') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                spec = ToolSpec.model_validate(yaml_safe_load(f))
            elif file.endswith('.json'):
                spec = ToolSpec.model_validate(json.load(f))
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')

        if spec.binding.python is None:
            raise ValueError('failed to load python tool as the tool had no python binding')

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
        if v.type == 'null' and k in schema.required:
            not_required.append(k)
        if v.anyOf is not None and next(filter(lambda x: x.type == 'null', v.anyOf)) and k in schema.required:
            v.anyOf = list(filter(lambda x: x.type != 'null', v.anyOf))
            if len(v.anyOf) == 1:
                replacements[k] = v.anyOf[0]
            not_required.append(k)
    schema.required = list(filter(lambda x: x not in not_required, schema.required if schema.required is not None else []))
    for k, v in replacements.items():
        combined = {
            **schema.properties[k].model_dump(exclude_unset=True, exclude_none=True),
            **v.model_dump(exclude_unset=True, exclude_none=True)
        }
        schema.properties[k] = JsonSchemaObject(**combined)
        schema.properties[k].anyOf = None

    for k in schema.properties.keys():
        if schema.properties[k].type == 'object':
            schema.properties[k] = _fix_optional(schema.properties[k])

    return schema

def _validate_input_schema(input_schema: ToolRequestBody) -> None:
    props = input_schema.properties
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
) -> Callable[[{__name__, __doc__}], PythonTool]:
    """
    Decorator to convert a python function into a callable tool.

    :param name: the agent facing name of the tool (defaults to the function name)
    :param description: the description of the tool (used for tool routing by the agent)
    :param input_schema: the json schema args to the tool
    :param output_schema: the response json schema for the tool
    :param permission: the permissions needed by the user of the agent to invoke the tool
    :return:
    """
    # inspiration: https://github.com/pydantic/pydantic/blob/main/pydantic/validate_call_decorator.py
    def _tool_decorator(fn):
        if fn.__doc__ is not None:
            doc = docstring_parser.parse(fn.__doc__)
        else:
            doc = None

        _desc = description
        if description is None and doc is not None:
            _desc = doc.description

        
        spec = ToolSpec(
            name=name or fn.__name__,
            display_name=display_name,
            description=_desc,
            permission=permission
        )

        parsed_expected_credentials = []
        if expected_credentials:
            for credential in expected_credentials:
                if isinstance(credential, ExpectedCredentials):
                    parsed_expected_credentials.append(credential)
                else:
                    parsed_expected_credentials.append(ExpectedCredentials.model_validate(credential))
        
        t = PythonTool(fn=fn, spec=spec, expected_credentials=parsed_expected_credentials)
        spec.binding = ToolBinding(python=PythonToolBinding(function=''))

        linux_friendly_os_cwd = os.getcwd().replace("\\", "/")
        function_binding = (inspect.getsourcefile(fn)
                            .replace("\\", "/")
                            .replace(linux_friendly_os_cwd+'/', '')
                            .replace('.py', '')
                            .replace('/','.') +
                            f":{fn.__name__}")
        spec.binding.python.function = function_binding

        sig = inspect.signature(fn)
        
        # If the function is a join tool, validate its signature matches the expected parameters. If not, raise error with details.
        if kind == PythonToolKind.JOIN_TOOL:
            _validate_join_tool_func(fn, sig, spec.name)
        
        if not input_schema:
            try:
                input_schema_model: type[BaseModel] = create_schema_from_function(spec.name, fn, parse_docstring=True)
            except:
                logger.warning("Unable to properly parse parameter descriptions due to incorrectly formatted docstring. This may result in degraded agent performance. To fix this, please ensure the docstring conforms to Google's docstring format.")
                input_schema_model: type[BaseModel] = create_schema_from_function(spec.name, fn, parse_docstring=False)
            input_schema_json = input_schema_model.model_json_schema()
            input_schema_json = dereference_refs(input_schema_json)

            # Convert the input schema to a JsonSchemaObject
            input_schema_obj = JsonSchemaObject(**input_schema_json)
            input_schema_obj = _fix_optional(input_schema_obj)

            spec.input_schema = ToolRequestBody(
                type='object',
                properties=input_schema_obj.properties or {},
                required=input_schema_obj.required or []
            )
        else:
            spec.input_schema = input_schema
        
        _validate_input_schema(spec.input_schema)

        if not output_schema:
            ret = sig.return_annotation
            if ret != sig.empty:
                _schema = dereference_refs(TypeAdapter(ret).json_schema())
                if '$defs' in _schema:
                    _schema.pop('$defs')
                spec.output_schema = _fix_optional(ToolResponseBody(**_schema))
            else:
                spec.output_schema = ToolResponseBody()

            if doc is not None and doc.returns is not None and doc.returns.description is not None:
                spec.output_schema.description = doc.returns.description

        else:
            spec.output_schema = ToolResponseBody()
        
        # Validate the generated schema still conforms to the requirement for a join tool
        if kind == PythonToolKind.JOIN_TOOL:
            if not spec.is_custom_join_tool():
                raise ValueError(f"Join tool '{spec.name}' does not conform to the expected join tool schema. Please ensure the input schema has the required fields: {JOIN_TOOL_PARAMS.keys()} and the output schema is a string.")
            
        _all_tools.append(t)
        return t

    if len(args) == 1 and callable(args[0]):
        return _tool_decorator(args[0])
    return _tool_decorator


def get_all_python_tools():
    return [t for t in _all_tools]
