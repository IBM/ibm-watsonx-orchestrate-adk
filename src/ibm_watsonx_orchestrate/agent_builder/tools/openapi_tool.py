import copy
import json
import os.path
import logging
from typing import Dict, Any, List

import yaml
import yaml.constructor
import re
import httpx
import jsonref
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from .types import ToolSpec
from .base_tool import BaseTool
from .types import HTTP_METHOD, ToolPermission, ToolRequestBody, ToolResponseBody, \
    OpenApiToolBinding, \
    JsonSchemaObject, ToolBinding, OpenApiSecurityScheme, CallbackBinding

import json

logger = logging.getLogger(__name__)

# disables the automatic conversion of date-time objects to datetime objects and leaves them as strings
yaml.constructor.SafeConstructor.yaml_constructors[u'tag:yaml.org,2002:timestamp'] = \
    yaml.constructor.SafeConstructor.yaml_constructors[u'tag:yaml.org,2002:str']


class HTTPException(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"{status_code} {message}")

    def __str__(self):
        return f"{self.status_code} {self.message}"


class OpenAPITool(BaseTool):
    def __init__(self, spec: ToolSpec):
        BaseTool.__init__(self, spec=spec)

        if self.__tool_spec__.binding.openapi is None:
            raise ValueError('Missing openapi binding')

    async def __call__(self, **kwargs):
        raise RuntimeError('OpenAPI Tools are only available when deployed onto watson orchestrate or the watson '
                           'orchestrate-light runtime')

    @staticmethod
    def from_spec(file: str) -> 'OpenAPITool':
        with open(file, 'r') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                spec = ToolSpec.model_validate(yaml_safe_load(f))
            elif file.endswith('.json'):
                spec = ToolSpec.model_validate(json.load(f))
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')

        if spec.binding.openapi is None or spec.binding.openapi is None:
            raise ValueError('failed to load python tool as the tool had no openapi binding')

        return OpenAPITool(spec=spec)

    def __repr__(self):
        return f"OpenAPITool(method={self.__tool_spec__.binding.openapi.http_method}, path={self.__tool_spec__.binding.openapi.http_path}, name='{self.__tool_spec__.name}', description='{self.__tool_spec__.description}')"

    def __str__(self):
        return self.__repr__()

    @property
    def __doc__(self):
        return self.__tool_spec__.description


def create_openapi_json_tool(
        openapi_spec: dict,
        http_path: str,
        http_method: HTTP_METHOD,
        http_success_response_code: int = 200,
        http_response_content_type='application/json',
        name: str = None,
        description: str = None,
        permission: ToolPermission = None,
        input_schema: ToolRequestBody = None,
        output_schema: ToolResponseBody = None,
        connection_id: str = None
) -> OpenAPITool:
    """
    Creates a tool from an openapi spec

    :param openapi_spec: The parsed dictionary representation of an openapi spec
    :param http_path: Which path to create a tool for
    :param http_method: Which method on that path to create the tool for
    :param http_success_response_code: Which http status code should be considered a successful call (defaults to 200)
    :param http_response_content_type: Which http response type should be considered successful (default to application/json)
    :param name: The name of the resulting tool (used to invoke the tool by the agent)
    :param description: The description of the resulting tool (used as the semantic layer to help the agent with tool selection)
    :param permission: Which orchestrate permission level does a user need to have to invoke this tool
    :param input_schema: The JSONSchema of the inputs to the http request
    :param output_schema: The expected JSON schema of the outputs of the http response
    :param connection_id: The connection id of the application containing the credentials needed to authenticate against this api
    :return: An OpenAPITool that can be used by an agent
    """

    # limitation does not support circular $refs
    openapi_contents = jsonref.replace_refs(openapi_spec, jsonschema=True)

    paths = openapi_contents.get('paths', {})
    route = paths.get(http_path)
    if route is None:
        raise ValueError(f"Path {http_path} not found in paths. Available endpoints are: {list(paths.keys())}")

    route_spec = route.get(http_method.lower(), route.get(http_method.upper()))
    if route_spec is None:
        raise ValueError(
            f"Path {http_path} did not have an http_method {http_method}. Available methods are {list(route.keys())}")

    operation_id = re.sub( r'(\W|_)+', '_', route_spec.get('operationId') ) \
                     if route_spec.get('operationId', None) else None

    spec_name = name or operation_id
    spec_permission = permission or _action_to_perm(route_spec.get('x-ibm-operation', {}).get('action'))
    if spec_name is None:
        raise ValueError(
            f"No name provided for tool. {http_method}: {http_path} did not specify an operationId, and no name was provided")

    spec_description = description or route_spec.get('description')
    if spec_description is None:
        raise ValueError(
            f"No description provided for tool. {http_method}: {http_path} did not specify a description field, and no description was provided")

    spec = ToolSpec(
        name=spec_name,
        description=spec_description,
        permission=spec_permission
    )
    spec.is_async = 'callbacks' in route_spec

    spec.input_schema = input_schema or ToolRequestBody(
        type='object',
        properties={},
        required=[]
    )
    spec.output_schema = output_schema or ToolResponseBody(properties={}, required=[])

    parameters = route_spec.get('parameters') or []
    for parameter in parameters:
        name = f"{parameter['in']}_{parameter['name']}"
        if parameter.get('required'):
            spec.input_schema.required.append(name)
        parameter['schema']['title'] = parameter['name']
        parameter['schema']['description'] = parameter.get('description', None)
        spec.input_schema.properties[name] = JsonSchemaObject.model_validate(parameter['schema'])
        spec.input_schema.properties[name].in_field = parameter['in']
        spec.input_schema.properties[name].aliasName = parameter['name']

    # special case in runtime where __requestBody__ will be directly translated to the request body without translation
    request_body_params = route_spec.get('requestBody', {}).get('content', {}).get(http_response_content_type, {}).get(
        'schema', None)
    if request_body_params is not None:
        spec.input_schema.required.append('__requestBody__')
        request_body_params = copy.deepcopy(request_body_params)
        request_body_params['in'] = 'body'
        if request_body_params.get('title') is None:
            request_body_params['title'] = 'RequestBody'
        if request_body_params.get('description') is None:
            request_body_params['description'] = 'The html request body used to satisfy this user utterance.'

        spec.input_schema.properties['__requestBody__'] = JsonSchemaObject.model_validate(request_body_params)

    responses = route_spec.get('responses', {})
    response = responses.get(str(http_success_response_code), {})
    response_description = response.get('description')
    response_schema = response.get('content', {}).get(http_response_content_type, {}).get('schema', {})

    response_schema['required'] = []
    spec.output_schema = ToolResponseBody.model_validate(response_schema)
    spec.output_schema.description = response_description

    servers = list(map(lambda x: x if isinstance(x, str) else x['url'],
                       openapi_contents.get('servers', openapi_contents.get('x-servers', []))))

    raw_open_api_security_schemes = openapi_contents.get('components', {}).get('securitySchemes', {})
    security_schemes_map = {}
    for key, security_scheme in raw_open_api_security_schemes.items():
        security_schemes_map[key] = OpenApiSecurityScheme(
            type=security_scheme['type'],
            scheme=security_scheme.get('scheme'),
            flows=security_scheme.get('flows'),
            name=security_scheme.get('name'),
            open_id_connect_url=security_scheme.get('openId', {}).get('openIdConnectUrl'),
            in_field=security_scheme.get('in', security_scheme.get('in_field'))
        )

    # - Note it's possible for security to be configured per route or globally
    # - Note we have no concept of scope because to a user their auth cred either has access or it doesn't
    #   unless we ask them for a scope they don't know to validate it provides no value
    security = []
    for needed_security in route_spec.get('security', []) + openapi_spec.get('security', []):
        name = next(iter(needed_security.keys()), None)
        if name is None or name not in security_schemes_map:
            raise ValueError(f"Invalid openapi spec, {HTTP_METHOD} {http_path} asks for a security scheme of {name}, "
                             f"but no such security scheme was configured in the .security section of the spec")

        security.append(security_schemes_map[name])

    # If it's an async tool, add callback binding
    if spec.is_async:


        callbacks = route_spec.get('callbacks', {})
        callback_name = next(iter(callbacks.keys()))
        callback_spec = callbacks[callback_name]
        callback_path = next(iter(callback_spec.keys()))
        callback_method = next(iter(callback_spec[callback_path].keys()))
        
        # Phase 1: Create a separate input schema for callback that excludes callbackUrl
        # Note: Currently assuming the callback URL parameter will be named 'callbackUrl' in the OpenAPI spec
        # Future phases will handle other naming conventions
        callback_input_schema = ToolRequestBody(
            type='object',
            properties={k: v for k, v in spec.input_schema.properties.items() if not k.endswith('_callbackUrl')},
            required=[r for r in spec.input_schema.required if not r.endswith('_callbackUrl')]
        )

        if callback_input_schema:
            spec.input_schema = callback_input_schema

        callback_binding = CallbackBinding(
            callback_url=callback_path,
            method=callback_method.upper(),
            input_schema=callback_input_schema,
            output_schema=spec.output_schema
        )

    else:
        callback_binding = None

    openapi_binding = OpenApiToolBinding(
        http_path=http_path,
        http_method=http_method,
        security=security,
        servers=servers,
        connection_id=connection_id
    )
    
    if callback_binding is not None:
        openapi_binding.callback = callback_binding

    spec.binding = ToolBinding(openapi=openapi_binding)

    return OpenAPITool(spec=spec)


async def _get_openapi_spec_from_uri(openapi_uri: str) -> Dict[str, Any]:
    if os.path.exists(openapi_uri) or openapi_uri.startswith('file://'):
        with open(openapi_uri, 'r') as fp:
            if openapi_uri.endswith('.json'):
                openapi_contents = json.load(fp)
            elif openapi_uri.endswith('.yaml') or openapi_uri.endswith('.yml'):
                openapi_contents = yaml_safe_load(fp)
            else:
                raise ValueError(
                    f"Unexpected file extension for file {openapi_uri}, expected one of [.json, .yaml, .yml]")
    elif openapi_uri.endswith('.json'):
        async with httpx.AsyncClient() as client:
            r = await client.get(openapi_uri)
            if r.status_code != 200:
                raise ValueError(f"Failed to fetch an openapi spec from {openapi_uri}, status code: {r.status_code}")
            openapi_contents = r.json()
    elif openapi_uri.endswith('.yaml'):
        async with httpx.AsyncClient() as client:
            r = await client.get(openapi_uri)
            if r.status_code != 200:
                raise ValueError(f"Failed to fetch an openapi spec from {openapi_uri}, status code: {r.status_code}")
            openapi_contents = yaml_safe_load(r.text)

    if openapi_contents is None:
        raise ValueError(f"Unrecognized path or uri {openapi_uri}")

    return openapi_contents


def _action_to_perm(action: str) -> str:
    if action and (
            action.lower().startswith('create') or action.lower().startswith('update') or action.lower().startswith(
            'delete')):
        return ToolPermission.READ_WRITE
    return ToolPermission.READ_ONLY


async def create_openapi_json_tool_from_uri(
        openapi_uri: str,
        http_path: str,
        http_method: HTTP_METHOD,
        http_success_response_code: int = 200,
        http_response_content_type='application/json',
        permission: ToolPermission = ToolPermission.READ_ONLY,
        name: str = None,
        description: str = None,
        input_schema: ToolRequestBody = None,
        output_schema: ToolResponseBody = None,
        app_id: str = None
) -> OpenAPITool:
    """
    Creates a tool from an openapi spec

    :param openapi_uri: The uri to the openapi spec to generate the tool from (ie file://path/to/openapi_file.json, https://catfact.ninja/docs/api-docs.json)
    :param http_path: Which path to create a tool for
    :param http_method: Which method on that path to create the tool for
    :param http_success_response_code: Which http status code should be considered a successful call (defaults to 200)
    :param http_response_content_type: Which http response type should be considered successful (default to application/json)
    :param name: The name of the resulting tool (used to invoke the tool by the agent)
    :param description: The description of the resulting tool (used as the semantic layer to help the agent with tool selection)
    :param permission: Which orchestrate permission level does a user need to have to invoke this tool
    :param input_schema: The JSONSchema of the inputs to the http request
    :param output_schema: The expected JSON schema of the outputs of the http response
    :param app_id: The app id of the connection containing the credentials needed to authenticate against this api
    :return: An OpenAPITool that can be used by an agent
    """
    openapi_contents = await _get_openapi_spec_from_uri(openapi_uri)

    return create_openapi_json_tool(
        openapi_spec=openapi_contents,
        http_path=http_path,
        http_method=http_method,
        http_success_response_code=http_success_response_code,
        http_response_content_type=http_response_content_type,
        permission=permission,
        name=name,
        description=description,
        input_schema=input_schema,
        output_schema=output_schema,
        connection_id=app_id
    )


async def create_openapi_json_tools_from_uri(
        openapi_uri: str,
        connection_id: str = None
) -> List[OpenAPITool]:
    openapi_contents = await _get_openapi_spec_from_uri(openapi_uri)
    tools: List[OpenAPITool] = await create_openapi_json_tools_from_content(openapi_contents, connection_id)

    return tools

async def create_openapi_json_tools_from_content(
        openapi_contents: dict,
        connection_id: str = None
) -> List[OpenAPITool]:
   
    tools: List[OpenAPITool] = []

    for path, methods in openapi_contents.get('paths', {}).items():
        for method, spec in methods.items():
            if method.lower() == 'head':
                continue
            success_codes = list(filter(lambda code: 200 <= int(code) < 300, spec['responses'].keys()))
            if len(success_codes) > 1:
                logger.warning(
                    f"There were multiple candidate success codes for {method} {path}, using {success_codes[0]} to generate output schema")

            tools.append(create_openapi_json_tool(
                openapi_contents,
                http_path=path,
                http_method=method.upper(),
                http_success_response_code=success_codes[0] if len(success_codes) > 0 else None,
                connection_id=connection_id
            ))

    return tools
