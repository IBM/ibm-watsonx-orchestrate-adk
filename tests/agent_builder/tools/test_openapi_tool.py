# Baseline testitall tests
# testitall is the assistant builder extension testing framework found here:
# https://github.com/watson-developer-cloud/assistant-toolkit/tree/master/integrations/extensions/starter-kits/testitall
import json
from os import path
import pytest
from pydantic import BaseModel, Field

# TO-DO: resolve path issue
try:
    from mocks.mock_httpx import get_mock_async_client, MockResponse
except:
    from tests.mocks.mock_httpx import get_mock_async_client, MockResponse
from ibm_watsonx_orchestrate.agent_builder.tools import create_openapi_json_tool


@pytest.fixture(scope='module')
def testitall():
    with open(path.join(path.dirname(path.realpath(__file__)), '../fixtures/testitall.openapi.json'), 'r') as fp:
        return json.load(fp)


@pytest.fixture(params=['GET', 'PUT', 'POST', 'DELETE'])  # we don't support HEAD
def openapispec_for_all_http_methods(request):
    return request.param, {
        'openapi': '3.0.3',
        'info': {},
         "servers": [
            {
            "url": "https://{host}:{port}",
            "description": "Your API server (with https enabled)",
            "variables": {
                "host": {
                "default": "",
                "description": "Hostname of the API server"
                },
                "port": {
                "default": "443",
                "description": "Port of the API server"
                }
            }
            }
        ],
        'paths': {
            '/test': {
                request.param: {
                    "summary": f"Test {request.param} with query parameters",
                    "description": "Test {request.param} with query parameters",
                    "operationId": "testParams",
                    "parameters": [
                        {
                            "in": "query",
                            "name": "query_param",
                            "required": False,
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "echoes back the params values",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object", "properties": {"query_param": {"type": "string"}}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }


@pytest.fixture(params=['header', 'query', 'cookie', 'path'])
def openapispec_for_in_parameter_locations(request):
    return request.param, {
        'openapi': '3.0.3',
        'info': {},
         "servers": [
            {
            "url": "https://{host}:{port}",
            "description": "Your API server (with https enabled)",
            "variables": {
                "host": {
                "default": "",
                "description": "Hostname of the API server"
                },
                "port": {
                "default": "443",
                "description": "Port of the API server"
                }
            }
            }
        ],
        'paths': {
            '/test/{param}' if request.param == 'path' else '/test': {
                'POST': {
                    "summary": f"Test {request.param} with query parameters",
                    "description": f"Test {request.param} with query parameters",
                    "operationId": "testParams",
                    "parameters": [
                        {
                            "in": request.param,
                            "name": "param",
                            "required": False,
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "echoes back the params values",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object", "properties": {"param": {"type": "string"}}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }


class AuthStrategyFixture(BaseModel):
    strategy: str
    in_field: str = Field(None, alias='in')
    config: dict = None
    matcher: dict = None

    def __repr__(self):
        return self.strategy

    def __str__(self):
        return self.strategy


auth_strategy_params = [
    AuthStrategyFixture(strategy='none'),
    AuthStrategyFixture(
        strategy='basic',
        in_field='header',
        config={
            "type": "http",
            "scheme": "basic"
        },
        matcher={
            'Authorization': 'Basic '
        }
    ),
    AuthStrategyFixture(
        strategy='apiKey',
        in_field='header',
        config={
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        },
        matcher={
            'X-API-Key': 'apikey'
        }
    ),
    AuthStrategyFixture(
        strategy='apiKey',
        in_field='query',
        config={
            "type": "apiKey",
            "in": "query",
            "name": "X-API-Key"
        },
        matcher={
            'X-API-Key': 'apikey'
        }
    ),
    AuthStrategyFixture(
        strategy='apiKey',
        in_field='cookie',
        config={
            "type": "apiKey",
            "in": "cookie",
            "name": "X-API-Key"
        },
        matcher={
            'X-API-Key': 'apikey'
        }
    )
]


@pytest.fixture(params=auth_strategy_params)
def openapi_global_authentication(request):
    return request.param, {
        'openapi': '3.0.3',
        'info': {},
        "servers": [
            {
            "url": "https://{host}:{port}",
            "description": "Your API server (with https enabled)",
            "variables": {
                "host": {
                "default": "",
                "description": "Hostname of the API server"
                },
                "port": {
                "default": "443",
                "description": "Port of the API server"
                }
            }
            }
        ],
        'paths': {
            '/test': {
                'POST': {
                    "summary": f"Test {request.param} with query parameters",
                    "description": f"Test {request.param} with query parameters",
                    "operationId": "testParams",
                    "responses": {
                        "200": {
                            "description": "echoes back the params values",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object", "properties": {"param": {"type": "string"}}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                'auth': request.param.config
            }
        } if request.param.strategy != 'none' else {},
        "security": [
            {'auth': []}
        ] if request.param.strategy != 'none' else [],
    }


@pytest.fixture(params=auth_strategy_params)
def openapi_route_authentication(request):
    return request.param, {
        'openapi': '3.0.3',
        'info': {},
        "servers": [
            {
            "url": "https://{host}:{port}",
            "description": "Your API server (with https enabled)",
            "variables": {
                "host": {
                "default": "",
                "description": "Hostname of the API server"
                },
                "port": {
                "default": "443",
                "description": "Port of the API server"
                }
            }
            }
        ],
        'paths': {
            '/test': {
                'POST': {
                    "summary": f"Test {request.param} with query parameters",
                    "description": f"Test {request.param} with query parameters",
                    "operationId": "testParams",
                    "security": [
                        {'auth': []}
                    ] if request.param.strategy != 'none' else [],
                    "responses": {
                        "200": {
                            "description": "echoes back the params values",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object", "properties": {"param": {"type": "string"}}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                'auth': request.param.config
            }
        } if request.param.strategy != 'none' else {}
    }


illegal_character_names = [
    ('api/test', 'api_test'),
    ('$api_test', '_api_test'),
    ('-test', '_test'),
    ('+test', '_test'),
    ('+_/test', '_test')
]


@pytest.fixture(params=illegal_character_names)
def openapi_illegal_operationid_characters(request):
    return request.param[0], request.param[1], {
        'openapi': '3.0.3',
        'info': {},
        "servers": [
            {
            "url": "https://{host}:{port}",
            "description": "Your API server (with https enabled)",
            "variables": {
                "host": {
                "default": "",
                "description": "Hostname of the API server"
                },
                "port": {
                "default": "443",
                "description": "Port of the API server"
                }
            }
            }
        ],
        'paths': {
            '/test': {
                'POST': {
                    "summary": f"Test {request.param[0]} with query parameters",
                    "description": f"Test {request.param[0]} with query parameters",
                    "operationId": f"{request.param[0]}",
                    "responses": {
                        "200": {
                            "description": "echoes back the params values",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object", "properties": {"param": {"type": "string"}}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }


############################################################
## Basic functional tests
############################################################
@pytest.mark.asyncio
async def test_all_supported_http_methods(mocker, snapshot, openapispec_for_all_http_methods):
    expected_response = {'status': 'got it'}
    AsyncClient, requests = get_mock_async_client(respond_with=MockResponse(json=expected_response))
    mocker.patch('httpx.AsyncClient', AsyncClient)
    method, openapispec = openapispec_for_all_http_methods

    tool = create_openapi_json_tool(
        openapispec,
        http_path='/test',
        http_method=method
    )
    snapshot.assert_match(json.loads(tool.dumps_spec()))
    try:
        await tool(query_param='potato')
        assert False, 'should have thrown'
    except RuntimeError as e:
        assert 'only available when deployed' in str(e), 'should show runtime message if called'


@pytest.mark.asyncio
async def test_all_supported_parameter_in_methods_except_body(mocker, snapshot, openapispec_for_in_parameter_locations):
    expected_response = {'status': 'got it'}
    AsyncClient, requests = get_mock_async_client(respond_with=MockResponse(json=expected_response))
    mocker.patch('httpx.AsyncClient', AsyncClient)
    in_location, openapispec = openapispec_for_in_parameter_locations

    tool = create_openapi_json_tool(
        openapispec,
        http_path='/test' if in_location != 'path' else '/test/{param}',
        http_method='POST'
    )
    snapshot.assert_match(json.loads(tool.dumps_spec()))
    try:
        await tool(param='potato')
        assert False, 'should have thrown'
    except RuntimeError as e:
        assert 'only available when deployed' in str(e), 'should show runtime message if called'


@pytest.mark.asyncio
async def test_body_parameters(mocker, snapshot):
    expected_response = {'status': 'got it'}
    AsyncClient, requests = get_mock_async_client(respond_with=MockResponse(json=expected_response))
    mocker.patch('httpx.AsyncClient', AsyncClient)

    tool = create_openapi_json_tool(
        {
            'openapi': '3.0.3',
            'info': {},
            "servers": [
                {
                "url": "https://{host}:{port}",
                "description": "Your API server (with https enabled)",
                "variables": {
                    "host": {
                    "default": "",
                    "description": "Hostname of the API server"
                    },
                    "port": {
                    "default": "443",
                    "description": "Port of the API server"
                    }
                }
                }
            ],
            'paths': {
                '/test': {
                    'POST': {
                        "summary": f"Test requestBody parameters",
                        "description": f"Test requestBody parameters",
                        "operationId": "testParams",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "param": {
                                                "type": "number",
                                                "example": 25
                                            }
                                        },
                                        "required": [
                                            "param"
                                        ]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "echoes back the params values",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object", "properties": {"param": {"type": "string"}}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        http_path='/test',
        http_method='POST'
    )
    snapshot.assert_match(json.loads(tool.dumps_spec()))
    try:
        await tool(requestBody={'param': 'potato'})
        assert False, 'should have thrown'
    except RuntimeError as e:
        assert 'only available when deployed' in str(e), 'should show runtime message if called'


@pytest.mark.asyncio
async def test_global_authentication(mocker, snapshot, openapi_global_authentication):
    expected_response = {'status': 'got it'}
    AsyncClient, requests = get_mock_async_client(respond_with=MockResponse(json=expected_response))
    mocker.patch('httpx.AsyncClient', AsyncClient)
    auth, openapispec = openapi_global_authentication

    if auth.strategy != 'none':
        tool = create_openapi_json_tool(
            openapispec,
            http_path='/test',
            http_method='POST'
        )
    else:
        tool = create_openapi_json_tool(
            openapispec,
            http_path='/test',
            http_method='POST'
        )
    snapshot.assert_match(json.loads(tool.dumps_spec()))

    try:
        await tool()
        assert False, 'should have thrown'
    except RuntimeError as e:
        assert 'only available when deployed' in str(e), 'should show runtime message if called'


@pytest.mark.asyncio
async def test_route_authentication(mocker, snapshot, openapi_route_authentication):
    expected_response = {'status': 'got it'}
    AsyncClient, requests = get_mock_async_client(respond_with=MockResponse(json=expected_response))
    mocker.patch('httpx.AsyncClient', AsyncClient)
    auth, openapispec = openapi_route_authentication

    if auth.strategy != 'none':
        tool = create_openapi_json_tool(
            openapispec,
            http_path='/test',
            http_method='POST'
        )
    else:
        tool = create_openapi_json_tool(
            openapispec,
            http_path='/test',
            http_method='POST',
        )

    try:
        await tool()
        assert False, 'should have thrown'
    except RuntimeError as e:
        assert 'only available when deployed' in str(e), 'should show runtime message if called'


@pytest.mark.asyncio
async def test_adds_app_id_to_binding(mocker):
    expected_response = {'status': 'got it'}
    AsyncClient, requests = get_mock_async_client(respond_with=MockResponse(json=expected_response))
    mocker.patch('httpx.AsyncClient', AsyncClient)

    tool = create_openapi_json_tool(
        {
            'openapi': '3.0.3',
            'info': {},
            "servers": [
                {
                "url": "https://{host}:{port}",
                "description": "Your API server (with https enabled)",
                "variables": {
                    "host": {
                    "default": "",
                    "description": "Hostname of the API server"
                    },
                    "port": {
                    "default": "443",
                    "description": "Port of the API server"
                    }
                }
                }
            ],
            'paths': {
                '/test': {
                    'POST': {
                        "summary": f"Test requestBody parameters",
                        "description": f"Test requestBody parameters",
                        "operationId": "testParams",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "param": {
                                                "type": "number"
                                            }
                                        },
                                        "required": [
                                            "param"
                                        ]
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "echoes back the params values",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object", "properties": {"param": {"type": "string"}}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        http_path='/test',
        http_method='POST',
        connection_id='connectionId'
    )
    assert tool.__tool_spec__.binding.openapi.connection_id == 'connectionId'


@pytest.mark.asyncio
async def test_should_escape_illegal_characters_in_operation_id(mocker, openapi_illegal_operationid_characters):
    expected_response = {'status': 'got it'}
    AsyncClient, requests = get_mock_async_client(respond_with=MockResponse(json=expected_response))
    mocker.patch('httpx.AsyncClient', AsyncClient)
    _, expected, spec = openapi_illegal_operationid_characters

    tool = create_openapi_json_tool(spec, http_path='/test', http_method='POST')
    spec = json.loads(tool.dumps_spec())
    assert spec['name'] == expected


##################################################################
##  More comprehensive "real world" scenarios based on testitall
##################################################################
@pytest.mark.asyncio
async def test_http_get_with_basic_auth(mocker, snapshot, testitall):
    expected_response = {'status': 'got it'}
    AsyncClient, requests = get_mock_async_client(respond_with=MockResponse(json=expected_response))
    mocker.patch('httpx.AsyncClient', AsyncClient)

    tool = create_openapi_json_tool(
        testitall,
        http_path='/test',
        http_method='GET'
    )
    assert tool.__doc__ == 'TEST GET'
    snapshot.assert_match(json.loads(tool.dumps_spec()))

    try:
        await tool()
        assert False, 'should have thrown'
    except RuntimeError as e:
        assert 'only available when deployed' in str(e), 'should show runtime message if called'


@pytest.mark.asyncio
async def test_http_get_with_api_key_auth(mocker, snapshot, testitall):
    expected_response = {'status': 'got it'}
    AsyncClient, requests = get_mock_async_client(respond_with=MockResponse(json=expected_response))
    mocker.patch('httpx.AsyncClient', AsyncClient)

    tool = create_openapi_json_tool(
        testitall,
        http_path='/test',
        http_method='GET'
    )
    assert tool.__doc__ == 'TEST GET'
    snapshot.assert_match(json.loads(tool.dumps_spec()))

    try:
        await tool()
        assert False, 'should have thrown'
    except RuntimeError as e:
        assert 'only available when deployed' in str(e), 'should show runtime message if called'


@pytest.mark.asyncio
async def test_http_post_with_header_query_and_path_params(mocker, snapshot, testitall):
    expected_response = {
        'path_param': 'potato',
        'header_param': 'tomato',
        'query_param': 'bacon'
    }
    AsyncClient, requests = get_mock_async_client(respond_with=MockResponse(json=expected_response))
    mocker.patch('httpx.AsyncClient', AsyncClient)

    tool = create_openapi_json_tool(
        testitall,
        http_path='/test/params/{path_param}',
        http_method='POST'
    )
    assert tool.__doc__ == 'Test we handle params  path, query, header'
    snapshot.assert_match(json.loads(tool.dumps_spec()))

    try:
        await tool(
            path_param='potato',
            header_param='tomato',
            query_param='bacon'
        )
        assert False, 'should have thrown'
    except RuntimeError as e:
        assert 'only available when deployed' in str(e), 'should show runtime message if called'


@pytest.mark.asyncio
async def test_http_put_with_json_request_body(mocker, snapshot, testitall):
    expected_response = {
        'status': 'put it'
    }
    AsyncClient, requests = get_mock_async_client(respond_with=MockResponse(json=expected_response))
    mocker.patch('httpx.AsyncClient', AsyncClient)

    tool = create_openapi_json_tool(
        testitall,
        http_path='/test',
        http_method='PUT'
    )
    assert tool.__doc__ == 'TEST PUT'
    snapshot.assert_match(json.loads(tool.dumps_spec()))

    try:
        await tool(
            some_content='potato',
            requestBody={
                'some_content': 'potato'
            }
        )
        assert False, 'should have thrown'
    except RuntimeError as e:
        assert 'only available when deployed' in str(e), 'should show runtime message if called'


@pytest.fixture
def openapi_async_callback_spec():
    return {
        'openapi': '3.0.3',
        'info': {},
        "servers": [
            {
            "url": "https://{host}:{port}",
            "description": "Your API server (with https enabled)",
            "variables": {
                "host": {
                "default": "",
                "description": "Hostname of the API server"
                },
                "port": {
                "default": "443",
                "description": "Port of the API server"
                }
            }
            }
        ],
        'paths': {
            '/test': {
                'POST': {
                    "summary": "Test async with callback",
                    "description": "Test async with callback",
                    "operationId": "testAsyncCallback",
                    "parameters": [
                        {
                            "in": "header",
                            "name": "callbackUrl",
                            "description": "The callback url for sending the response",
                            "required": True,
                            "schema": {
                                "type": "string"
                            }
                        }
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "param": {
                                            "type": "string"
                                        }
                                    },
                                    "required": [
                                        "param"
                                    ]
                                }
                            }
                        }
                    },
                    "callbacks": {
                        "callback": {
                            "{$request.header.callbackUrl}": {
                                "POST": {
                                    "requestBody": {
                                        "content": {
                                            "application/json": {
                                                "schema": {
                                                    "type": "object",
                                                    "properties": {
                                                        "result": {
                                                            "type": "string"
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    },
                                    "responses": {
                                        "200": {
                                            "description": "Callback response"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Success response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {
                                                "type": "string"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }


@pytest.mark.asyncio
async def test_async_spec_with_callback(mocker, snapshot, openapi_async_callback_spec):
    expected_response = {'status': 'got it'}
    AsyncClient, requests = get_mock_async_client(respond_with=MockResponse(json=expected_response))
    mocker.patch('httpx.AsyncClient', AsyncClient)

    tool = create_openapi_json_tool(
        openapi_async_callback_spec,
        http_path='/test',
        http_method='POST'
    )

    spec = json.loads(tool.dumps_spec())
    snapshot.assert_match(spec)
    
    assert spec['binding']['openapi']['callback'] is not None
    assert spec['binding']['openapi']['callback']['callback_url'] == '{$request.header.callbackUrl}'

    callback_input_schema = spec['binding']['openapi']['callback']['input_schema']
    assert 'header_callbackUrl' not in callback_input_schema['properties']
    assert 'header_callbackUrl' not in callback_input_schema['required']
    
    try:
        await tool()
        assert False, 'should have thrown'
    except RuntimeError as e:
        assert 'only available when deployed' in str(e), 'should show runtime message if called'
