import re
from unittest import mock
from ibm_watsonx_orchestrate.agent_builder.tools.python_tool import PythonTool
from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolsController, ToolKind
from ibm_watsonx_orchestrate.agent_builder.tools.types import ToolPermission, ToolSpec
from ibm_watsonx_orchestrate.agent_builder.tools.openapi_tool import OpenAPITool
from ibm_watsonx_orchestrate.cli.commands.tools.types import RegistryType
from ibm_watsonx_orchestrate.cli.config import DEFAULT_CONFIG_FILE_CONTENT, PYTHON_REGISTRY_HEADER, \
    PYTHON_REGISTRY_TYPE_OPT
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from typer import BadParameter
import json
import pytest
import uuid
from ibm_watsonx_orchestrate.utils.request import BadRequest

from mocks.mock_base_api import MockListConnectionResponse

class MockConfig2():
    def __init__(self):
        self.config = {}

    def read(self, section, option):
        return self.config.get(section, {}).get(option)

    def get(self, *args):
        nested_value = self.config.copy()
        for arg in args:
            nested_value = nested_value[arg]
        return nested_value

    def write(self, section, option, value):
        if not section in self.config:
            self.config[section] = {}
        self.config[section][option] = value

    def save(self, data):
        self.config.update(data)

    def delete(self, *args, **kwargs):
        pass


class MockSDKResponse:
    def __init__(self, response_obj):
        self.response_obj = response_obj

    def dumps_spec(self):
        return json.dumps(self.response_obj)


class MockToolClient:
    def __init__(self, expected=None, get_response=[], tool_name="", file_path="", already_existing=False):
        self.expected = expected
        self.get_response = get_response
        self.tool_name = tool_name
        self.file_path = file_path
        self.already_existing = already_existing

    def create(self, spec):
        for key in self.expected:
            assert spec[key] == self.expected[key]
        return {"id": uuid.uuid4()}

    def get(self):
        return self.get_response

    def update(self, name, spec):
        for key in self.expected:
            assert spec[key] == self.expected[key]

    def delete(self, agent_id):
        assert agent_id == self.tool_name

    def upload_tools_artifact(self, tool_id: str, file_path: str):
        assert file_path.endswith(self.file_path)

    def delete(self, tool_id):
        pass

    def upload_tools_artifact(self, tool_id: str, file_path: str):
        assert file_path.endswith(self.file_path)

    def get_draft_by_name(self, tool_name):
        if self.already_existing:
            return [{"name": tool_name, "id": uuid.uuid4()}]
        return []


class MockConnectionClient:
    def __init__(self, get_response=[], get_by_id_response=[], get_conn_by_id_response=[]):
        self.get_by_id_response = get_by_id_response
        self.get_response = get_response
        self.get_conn_by_id_response = get_conn_by_id_response

    def get_draft_by_app_id(self, app_id: str):
        return self.get_by_id_response
    
    def get(self):
        return self.get_response
    
    def get_draft_by_id(self, conn_id: str):
        return self.get_conn_by_id_response

class MockConnection:
    def __init__(self, appid, connection_type):
        self.appid = appid
        self.connection_type = connection_type
        self.connection_id = "12345"


def test_openapi_params_valid():
    calls = []

    async def create_openapi_json_tools_from_uri(*args, **kwargs):
        calls.append((args, kwargs))
        return []

    client = MockConnectionClient(get_by_id_response=[MockListConnectionResponse(connection_id='connectionId')])
    with mock.patch(
        'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.create_openapi_json_tools_from_uri',
        create_openapi_json_tools_from_uri
    ), mock.patch(
        'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') \
    as client_mock:
        client_mock.return_value = client
        file = "../resources/yaml_samples/tool.yaml"
        tools =ToolsController.import_tool(
            ToolKind.openapi,
            file=file,
            app_id='appId'
        )
        list(tools)

        assert calls == [
            (
                ('../resources/yaml_samples/tool.yaml', 'connectionId'),
                {}
            )
        ]


def test_openapi_no_app_id():
    calls = []

    async def create_openapi_json_tools_from_uri(*args, **kwargs):
        calls.append((args, kwargs))
        return []

    with mock.patch(
            'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.create_openapi_json_tools_from_uri',
            create_openapi_json_tools_from_uri
    ):
        tools_controller = ToolsController()
        tools = tools_controller.import_tool(ToolKind.openapi, file="tests/cli/resources/yaml_samples/tool.yaml",
                                             app_id=None)
        list(tools)
        assert calls == [
            (
                ('tests/cli/resources/yaml_samples/tool.yaml', None),
                {}
            )
        ]

def test_openapi_multiple_app_ids():
    with pytest.raises(BadParameter) as e:
        tools_controller = ToolsController()
        tools = tools_controller.import_tool(ToolKind.openapi, file="tests/cli/resources/yaml_samples/tool.yaml",  app_id=["test1", "test2"])
        list(tools)
    assert "Kind 'openapi' can only take one app-id" in str(e)

def test_openapi_appi_id_key_value(caplog):
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client:
        mock_instantiate_client.return_value = MockConnectionClient(
            get_response=[MockConnection(appid="test", connection_type="key_value")]
        )

        with pytest.raises(SystemExit) as e:
            tools_controller = ToolsController()
            tools = tools_controller.import_tool(ToolKind.openapi, file="tests/cli/resources/yaml_samples/tool.yaml",  app_id="test")
            list(tools)

        captured = caplog.text
        assert "Key value application connections can not be bound to an openapi tool" in captured


def test_openapi_no_file():
    with pytest.raises(BadParameter):
        tools_controller = ToolsController()
        tools = tools_controller.import_tool(ToolKind.openapi, file=None)
        list(tools)


def test_publish_openapi():
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client:
        spec = ToolSpec(
            name="test",
            description="test",
            permission=ToolPermission.READ_ONLY,
            binding={"openapi": {
                "http_method": "GET",
                "http_path": "/test",
                "servers": ["test"],
            }}
        )
        tools = [
            OpenAPITool(spec=spec)
        ]

        mock_instantiate_client.return_value = MockToolClient(
            expected=spec.model_dump(exclude_none=True, exclude_defaults=True)
        )

        tools_controller = ToolsController()
        tools_controller.publish_or_update_tools(tools)

        mock_instantiate_client.assert_called_once_with(ToolClient)


def test_update_openapi():
    with mock.patch(
            'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client:
        spec = ToolSpec(
            name="test",
            description="test",
            permission=ToolPermission.READ_ONLY,
            binding={"openapi": {
                "http_method": "GET",
                "http_path": "/test",
                "servers": ["test"],
            }}
        )
        tools = [
            OpenAPITool(spec=spec)
        ]

        mock_instantiate_client.return_value = MockToolClient(
            expected=spec.model_dump(exclude_none=True, exclude_defaults=True),
            get_response=[{"name": "test", "id": "123"}],
            already_existing=True
        )

        tools_controller = ToolsController()
        tools_controller.publish_or_update_tools(tools)


        mock_instantiate_client.assert_called_once_with(ToolClient)


def test_python_params_valid():
    tools_controller = ToolsController()
    tools = tools_controller.import_tool(
        ToolKind.python,
        file="tests/cli/resources/python_samples/tool_w_metadata.py",
        requirements_file="tests/cli/resources/python_samples/requirements.txt"
    )

    tools = list(tools)
    assert len(tools) > 0

    tool = tools[0]
    assert tool.__tool_spec__.name == "myName"
    assert tool.__tool_spec__.permission == ToolPermission.ADMIN

def test_python_params_valid_with_app_ids():
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client:
        mock_response = MockListConnectionResponse(connection_id="12345")
        mock_instantiate_client.return_value = MockConnectionClient(get_by_id_response=[mock_response])

        tools_controller = ToolsController()
        tools = tools_controller.import_tool(
            ToolKind.python, 
            file = "tests/cli/resources/python_samples/tool_w_metadata.py",
            requirements_file = "tests/cli/resources/python_samples/requirements.txt",
            app_id=["test"]
        )

        tools = list(tools)
        assert len(tools) > 0    
        
        tool = tools[0]
        assert tool.__tool_spec__.name == "myName"
        assert tool.__tool_spec__.permission == ToolPermission.ADMIN
        assert tool.__tool_spec__.binding.python.connections == {"test": "12345"}

def test_python_params_valid_with_split_app_id():
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client:
        mock_response = MockListConnectionResponse(connection_id="12345")
        mock_instantiate_client.return_value = MockConnectionClient(get_by_id_response=[mock_response])

        tools_controller = ToolsController()
        tools = tools_controller.import_tool(
            ToolKind.python, 
            file = "tests/cli/resources/python_samples/tool_w_metadata.py",
            requirements_file = "tests/cli/resources/python_samples/requirements.txt",
            app_id=["test!1=test\\=123"]
        )

        tools = list(tools)
        assert len(tools) > 0    
        
        tool = tools[0]
        assert tool.__tool_spec__.name == "myName"
        assert tool.__tool_spec__.permission == ToolPermission.ADMIN
        assert tool.__tool_spec__.binding.python.connections == {"test_1": "12345"}

def test_python_params_valid_with_split_app_id_invalid_equals():
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client:
        with pytest.raises(BadParameter) as e:
            tools_controller = ToolsController()
            tools = tools_controller.import_tool(
                ToolKind.python, 
                file = "tests/cli/resources/python_samples/tool_w_metadata.py",
                requirements_file = "tests/cli/resources/python_samples/requirements.txt",
                app_id=["test!1=test=123"]
            )
            tools = list(tools)   
        
        assert "The provided --app-id \'test!1=test=123\' is not valid. This is likely caused by having mutliple equal signs, please use \'\\\\=\' to represent a literal \'=\' character" in str(e)

def test_python_params_valid_with_split_app_id_missing_app_id():
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client:
        with pytest.raises(BadParameter) as e:
            tools_controller = ToolsController()
            tools = tools_controller.import_tool(
                ToolKind.python, 
                file = "tests/cli/resources/python_samples/tool_w_metadata.py",
                requirements_file = "tests/cli/resources/python_samples/requirements.txt",
                app_id=["test="]
            )
            tools = list(tools)   
        
        assert "The provided --app-id \'test=\' is not valid. --app-id cannot be empty or whitespace" in str(e)

def test_python_params_valid_with_split_app_id_missing_runtime_app_id():
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client:
        with pytest.raises(BadParameter) as e:
            tools_controller = ToolsController()
            tools = tools_controller.import_tool(
                ToolKind.python, 
                file = "tests/cli/resources/python_samples/tool_w_metadata.py",
                requirements_file = "tests/cli/resources/python_samples/requirements.txt",
                app_id=["=test"]
            )
            tools = list(tools)   
        
        assert "The provided --app-id \'=test\' is not valid. --app-id cannot be empty or whitespace" in str(e)

def test_python_tool_expected_connections():

    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client:
        mock_response = MockListConnectionResponse(connection_id="12345")
        mock_instantiate_client.return_value = MockConnectionClient(
            get_response=[MockConnection(appid="test", connection_type="basic_auth")],
            get_by_id_response=[mock_response]
        )

        tools_controller = ToolsController()
        tools = tools_controller.import_tool(
            ToolKind.python, 
            file = "tests/cli/resources/python_samples/tool_w_expectations.py",
            requirements_file = "tests/cli/resources/python_samples/requirements.txt",
            app_id=["test"]
        )
        tools = list(tools) 

        tool = tools[0]
        assert tool.__tool_spec__.name == "my_tool"
        assert tool.__tool_spec__.permission == ToolPermission.READ_ONLY
        assert tool.__tool_spec__.binding.python.connections == {"test": "12345"}  

        tool = tools[1]
        assert tool.__tool_spec__.name == "my_tool_w_type"
        assert tool.__tool_spec__.permission == ToolPermission.READ_ONLY
        assert tool.__tool_spec__.binding.python.connections == {"test": "12345"}

def test_python_no_file():
    with pytest.raises(BadParameter):
        tools_controller = ToolsController()
        tools = tools_controller.import_tool(ToolKind.python, file=None, requirements_file=None)
        list(tools)


def test_python_file_not_readable():
    with pytest.raises(BadParameter,
                       match="Failed to load python module from file does_not_exist.py: No module named 'does_not_exist'") as e:
        tools_controller = ToolsController()
        tools = tools_controller.import_tool(ToolKind.python, file="does_not_exist.py",
                                             requirements_file="tests/cli/resources/python_samples/requirements.txt")
        list(tools)


def test_python_requirements_file_not_readable():
    with pytest.raises(BadParameter, match=re.escape(
            "Failed to read file does_not_exist.txt [Errno 2] No such file or directory: 'does_not_exist.txt'")):
        tools_controller = ToolsController()
        tools = tools_controller.import_tool(ToolKind.python,
                                             file="tests/cli/resources/python_samples/tool_w_metadata.py",
                                             requirements_file="does_not_exist.txt")
        list(tools)


def test_skill_valid():
    tools_controller = ToolsController()
    tools = tools_controller.import_tool(
        "skill",
        skillset_id="fake_skillset",
        skill_id="fake_skill",
        skill_operation_path="fake_operation_path",
    )
    list(tools)


def test_skill_missing_args():
    with pytest.raises(BadParameter):
        tools_controller = ToolsController()
        tools = tools_controller.import_tool(
            "skill", skillset_id=None, skill_id=None, skill_operation_path=None
        )
        list(tools)


def test_invalid_kind():
    try:
        tools_controller = ToolsController()
        tools = tools_controller.import_tool("invalid")
        list(tools)
        assert False
    except BadRequest as e:
        assert True
        assert str(e) == "Invalid kind selected"

def test_publish_python():
    with mock.patch(
            'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client, \
            mock.patch('zipfile.ZipFile') as mock_zipfile, \
            mock.patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.Config") as mock_cfg:
        cfg = MockConfig2()
        cfg.save(DEFAULT_CONFIG_FILE_CONTENT)
        cfg.write(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, RegistryType.LOCAL)
        mock_cfg.return_value = cfg
        spec = ToolSpec(
            name="test",
            description="test",
            permission=ToolPermission.READ_ONLY,
            binding={"python": {
                "function": "test_tool:my_tool",
                "requirements": ["some_lib:1.0.0"],
            }}
        )
        tools = [
            PythonTool(fn="test_tool:my_tool", spec=spec)
        ]

        mock_instantiate_client.return_value = MockToolClient(
            expected=spec.model_dump(exclude_none=True, exclude_defaults=True),
            tool_name="test",
            file_path="artifacts.zip"
        )

        tools_controller = ToolsController(ToolKind.python, "test_tool.py",
                                           'tests/cli/resources/python_samples/requirements.txt')
        tools_controller.publish_or_update_tools(tools)

        mock_instantiate_client.assert_called_once_with(ToolClient)
        mock_zipfile.assert_called


def test_update_python():
    with mock.patch(
            'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client, \
            mock.patch('zipfile.ZipFile') as mock_zipfile, \
            mock.patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.Config") as mock_cfg:
        cfg = MockConfig2()
        cfg.save(DEFAULT_CONFIG_FILE_CONTENT)
        cfg.write(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, RegistryType.LOCAL)
        mock_cfg.return_value = cfg
        spec = ToolSpec(
            name="test",
            description="test",
            permission=ToolPermission.READ_ONLY,
            binding={"python": {
                "function": "my_tool:myTool",
                "requirements": ["some_lib:1.0.0"],
            }}
        )
        tools = [
            PythonTool(fn="test_tool:my_tool", spec=spec)
        ]

        mock_instantiate_client.return_value = MockToolClient(
            expected=spec.model_dump(exclude_none=True, exclude_defaults=True),
            get_response=[{"name": "test", "id": "123"}],
            tool_name="test",
            file_path="artifacts.zip",
            already_existing=True
        )

        tools_controller = ToolsController()
        tools_controller.publish_or_update_tools(tools)

        mock_instantiate_client.assert_called_once_with(ToolClient)
        mock_zipfile.assert_called


@mock.patch(
    "ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.ToolsController.get_client",
    return_value=MockToolClient(tool_name="test_tool", already_existing=True)
)
def test_tool_remove(mock, caplog):
    tools_controller = ToolsController()
    tool_name = "test_tool"
    tools_controller.remove_tool(name=tool_name)

    captured = caplog.text
    assert f"Successfully removed tool {tool_name}" in captured


@mock.patch(
    "ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.ToolsController.get_client",
    return_value=MockToolClient(tool_name="test_tool", already_existing=False)
)
def test_tool_remove_non_existent(mock, caplog):
    tools_controller = ToolsController()
    tool_name = "test_tool"
    tools_controller.remove_tool(name=tool_name)

    captured = caplog.text
    assert f"Successfully removed tool {tool_name}" not in captured
    assert f"No tool named '{tool_name}' found" in captured

@mock.patch(
    "ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.ToolsController.get_client",
    return_value=MockToolClient(get_response=[
        {
            "name": "test_tool",
            "description": "testing_tool",
            "permission": "read_only",
            "binding": {
                "python": {"function": "test_function"}
            }
        }
    ])
)
def test_tool_list(mock_get_client):
    client = MockConnectionClient(get_response=[MockListConnectionResponse(connection_id='connectionId')])
    with mock.patch(
        'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client'
    ) as client_mock:
        client_mock.return_value = client
        tools_controller = ToolsController()
        tools_controller.list_tools()



@mock.patch(
    "ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.ToolsController.get_client",
    return_value=MockToolClient(get_response=[
        {
            "name": "test_tool",
            "description": "testing_tool",
            "permission": "read_only",
            "binding": {
                "python": {"function": "test_function"}
            }
        }
    ])
)
def test_tool_list_verbose(mock, capsys):
    tools_controller = ToolsController()
    tools_controller.list_tools(verbose=True)

    captured = capsys.readouterr()

    assert "test_tool" in captured.out
    assert "testing_tool" in captured.out
    assert "read_only" in captured.out
