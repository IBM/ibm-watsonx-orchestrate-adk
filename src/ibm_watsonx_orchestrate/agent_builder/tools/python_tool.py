import importlib
import inspect
import json
import os
from typing import Callable

import docstring_parser
import yaml
from langchain_core.tools.base import create_schema_from_function
from langchain_core.utils.json_schema import dereference_refs
from pydantic import TypeAdapter, BaseModel

from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from .base_tool import BaseTool
from .types import ToolSpec, ToolPermission, ToolRequestBody, ToolResponseBody, JsonSchemaObject, ToolBinding, \
    PythonToolBinding

_all_tools = []


class PythonTool(BaseTool):
    def __init__(self, fn, spec: ToolSpec):
        BaseTool.__init__(self, spec=spec)
        self.fn = fn

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
        return f"PythonTool(fn={self.__tool_spec__.binding.python.function}, name='{self.__tool_spec__.name}', description='{self.__tool_spec__.description}')"

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


def tool(
    name: str = None,
    description: str = None,
    input_schema: ToolRequestBody = None,
    output_schema: ToolResponseBody = None,
    permission: ToolPermission = ToolPermission.READ_ONLY
) -> Callable[[{__name__, __doc__}], PythonTool]:
    """
    Decorator to convert a python function into a callable tool.

    Support level: Beta

    :param name: the agent facing name of the tool (defaults to the function name)
    :param description: the description of the tool (used for tool routing by the agent)
    :param input_schema: the json schema args to the tool
    :param output_schema: the response json schema for the tool
    :param permission: the permissions needed by the user of the agent to invoke the tool
    :return:
    """
    # inspiration: https://github.com/pydantic/pydantic/blob/main/pydantic/validate_call_decorator.py
    def _tool_decorator(fn):
        spec = ToolSpec()
        spec.name = name or fn.__name__
        spec.description = description
        spec.permission = permission

        t = PythonTool(fn=fn, spec=spec)
        spec.binding = ToolBinding(python=PythonToolBinding(function=''))

        if fn.__doc__ is not None:
            doc = docstring_parser.parse(fn.__doc__)
        else:
            doc = None

        if spec.description is None and doc is not None:
            spec.description = doc.description

        function_binding = (inspect.getsourcefile(fn)
                            .replace(os.getcwd()+'/', '')
                            .replace('.py', '')
                            .replace('/','.') +
                            f":{fn.__name__}")
        spec.binding.python.function = function_binding

        sig = inspect.signature(fn)
        if not input_schema:
            input_schema_model: type[BaseModel] = create_schema_from_function(spec.name, fn, parse_docstring=True)
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
        _all_tools.append(t)
        return t

    return _tool_decorator


def get_all_python_tools():
    return [t for t in _all_tools]
