import re
from typing import Literal
from unittest import mock
from unittest.mock import call

from ibm_watsonx_orchestrate.agent_builder.tools.python_tool import PythonTool
from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolsController, ToolKind, _get_kind_from_spec
from ibm_watsonx_orchestrate.agent_builder.tools.types import ToolPermission, ToolSpec
from ibm_watsonx_orchestrate.agent_builder.tools.openapi_tool import OpenAPITool
from ibm_watsonx_orchestrate.cli.commands.tools.types import RegistryType
from ibm_watsonx_orchestrate.cli.config import DEFAULT_CONFIG_FILE_CONTENT, PYTHON_REGISTRY_HEADER, \
    PYTHON_REGISTRY_TYPE_OPT
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.connections.connections_client import ListConfigsResponse
from typer import BadParameter
import json
import pytest
import uuid
import tempfile
import os
import sys
from pathlib import Path

from mocks.mock_base_api import MockListConnectionResponse


def drop_module(name: str):
    # system caches loaded modules (including the ones that are loaded dynamically, using importlib) into cache. this
    # causes problems in some tests where a cached module's py binding function value is not correct. this happens when
    # we're executing all the tests in this file at once and not when executing tests individually. as such, this
    # function will help idempotently drop such dynamic modules when and where necessary to avoid needless failures
    # (/assertion errors).
    if sys.modules.get(name):
        del sys.modules[name]

def get_file_lines(file_path: str):
    lines = []
    with open(file_path, 'r') as fp:
        lines = fp.readlines()

    return lines


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
    def __init__(self, expected=None, get_response=[], tool_name="", file_path="", already_existing=False, get_draft_by_name_response=None, download_tools_artifact_response=None, get_draft_by_id_response=None):
        self.expected = expected
        self.get_response = get_response
        self.tool_name = tool_name
        self.file_path = file_path
        self.already_existing = already_existing
        self.published_file_path = None
        self.get_draft_by_name_response = get_draft_by_name_response
        self.download_tools_artifact_response = download_tools_artifact_response
        self.get_draft_by_id_response = get_draft_by_id_response

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
        self. published_file_path = file_path
        assert file_path.endswith(self.file_path)

    def delete(self, tool_id):
        pass

    def upload_tools_artifact(self, tool_id: str, file_path: str):
        self.published_file_path = file_path
        assert file_path.endswith(self.file_path)

    def get_draft_by_name(self, tool_name):
        if self.get_draft_by_name_response:
            return self.get_draft_by_name_response
        if self.already_existing:
            return [{"name": tool_name, "id": uuid.uuid4()}]
        return []
    
    def get_drafts_by_names(self, agents):
        ids = []
        for agent in agents:
            ids.append({"name": agent, "id": str(uuid.uuid4())})
        return ids
    
    def get_draft_by_id(self, tool_id: str) -> dict | Literal[""]:
        if tool_id is None:
            return ""
        if self.get_draft_by_id_response:
            return self.get_draft_by_id_response
        return ""
    
    def download_tools_artifact(self, tool_id):
        return self.download_tools_artifact_response


class MockConnectionClient:
    def __init__(self, get_response=[], get_by_id_response=[], get_conn_by_id_response=[], list_conn_response=[]):
        self.get_by_id_response = get_by_id_response
        self.get_response = get_response
        self.get_conn_by_id_response = get_conn_by_id_response
        self.list_conn_response = list_conn_response

    def get_draft_by_app_id(self, app_id: str):
        return self.get_by_id_response
    
    def get(self, app_id: str):
        return self.get_response
    
    def get_draft_by_id(self, conn_id: str):
        return self.get_conn_by_id_response

    def list(self):
        return self.list_conn_response

class MockConnection:
    def __init__(self, appid, connection_type):
        self.appid = appid
        self.connection_type = connection_type
        self.connection_id = "12345"

@pytest.fixture(autouse=True)
def run_around_tests():
    import pathlib
    path = str(pathlib.Path(__file__).parent.parent.parent.parent.parent)
    print(path)
    original_path = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(original_path)



def test_openapi_params_valid():
    calls = []

    async def create_openapi_json_tools_from_uri(*args, **kwargs):
        calls.append((args, kwargs))
        return []

    client = MockConnectionClient(
        get_by_id_response=MockListConnectionResponse(connection_id='connectionId'),
        list_conn_response=[]
        )
    with mock.patch(
        'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.create_openapi_json_tools_from_uri',
        create_openapi_json_tools_from_uri
    ), mock.patch(
        'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.get_connections_client') \
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

# def test_flow_with_python_based_flow():
#     tools_controller = ToolsController()
#     tools = list(tools_controller.import_tool(ToolKind.flow,
#                                               file="tests/cli/resources/flow_samples/get_pet_facts/get_pet_facts.py"))
    
#     assert len(tools) == 2
#     assert tools[0].__tool_spec__.binding.openapi.http_method == "POST"
#     assert tools[0].__tool_spec__.binding.openapi.http_path == "/run/async"
#     assert tools[0].__tool_spec__.name == "get_pet_facts"
#     assert tools[0].__tool_spec__.permission == ToolPermission.READ_ONLY
#     assert tools[1].__tool_spec__.binding.openapi.http_method == "GET"
#     assert tools[1].__tool_spec__.binding.openapi.http_path == "/v1/flows"
#     assert tools[1].__tool_spec__.name == "get_flow_status"
#     assert tools[1].__tool_spec__.permission == ToolPermission.READ_ONLY
   
# def test_flow_with_json_based_flow():
#     tools_controller = ToolsController()
#     tools = list(tools_controller.import_tool(ToolKind.flow,
#                                               file="tests/cli/resources/flow_samples/get_pet_facts/get_pet_facts.json"))
    
#     assert len(tools) == 2
#     assert tools[0].__tool_spec__.binding.openapi.http_method == "POST"
#     assert tools[0].__tool_spec__.binding.openapi.http_path == "/run/async"
#     assert tools[0].__tool_spec__.name == "get_pet_facts"
#     assert tools[0].__tool_spec__.permission == ToolPermission.READ_ONLY
#     assert tools[1].__tool_spec__.binding.openapi.http_method == "GET"
#     assert tools[1].__tool_spec__.binding.openapi.http_path == "/v1/flows"
#     assert tools[1].__tool_spec__.name == "get_flow_status"
#     assert tools[1].__tool_spec__.permission == ToolPermission.READ_ONLY

# def test_flow_no_file():
#     with pytest.raises(BadParameter):
#         tools_controller = ToolsController()
#         tools = tools_controller.import_tool(ToolKind.flow, file=None)
#         list(tools)
# def test_flow_wrong_file_extension():
#     with pytest.raises(BadParameter) as e:
#         tools_controller = ToolsController()
#         tools = tools_controller.import_tool(ToolKind.flow, file="tests/cli/resources/flow_samples/get_pet_facts/get_pet_facts.yaml")
#         list(tools)
#     assert "Unknown file type.  Only python or json are supported." in str(e)

# def test_flow_file_not_exists():
#     with pytest.raises(BadParameter) as e:
#         tools_controller = ToolsController()
#         tools = tools_controller.import_tool(ToolKind.flow, file="file_not_exists.json")
#         list(tools)
#     assert "Failed to load model from file file_not_exists.json: [Errno 2] No such file or directory: 'file_not_exists.json'" in str(e)

def test_openapi_no_app_id():
    calls = []

    async def create_openapi_json_tools_from_uri(*args, **kwargs):
        calls.append((args, kwargs))
        return []

    with mock.patch(
            'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.create_openapi_json_tools_from_uri',
            create_openapi_json_tools_from_uri
    ), \
        mock.patch(
            'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.get_connections_client'
        ) as mock_conn_client:
        
        mock_conn_client.return_value = MockConnectionClient()

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

def test_openapi_app_id_key_value(caplog):
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.get_connections_client') as mock_client:
        mock_client.return_value = MockConnectionClient(
            get_response=MockConnection(appid="test", connection_type="key_value"),
            get_by_id_response=[MockConnection(appid="test", connection_type="key_value")],
            list_conn_response=[ListConfigsResponse(**{
                    "connection_id": "12345",
                    "app_id": "test",
                    "auth_type": None,
                    "security_scheme": "key_value_creds",
            })]
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

def test_python_file_is_dir():
    with pytest.raises(BadParameter) as ex:
        tools_controller = ToolsController()
        list(tools_controller.import_tool(ToolKind.python, file="tests/cli"))

    assert str(ex.value) == "Provided tool file path is not a file."

def test_python_file_is_symlink():
    drop_module('testtool1')
    with pytest.raises(BadParameter) as ex:
        with tempfile.TemporaryDirectory() as tempdir:
            symlink_path = os.path.join(tempdir, "symlink_to_a_file")
            os.symlink("test/cli/resources/python_multi_file_samples/testtool1/testtool1.py", symlink_path)

            tools_controller = ToolsController()
            list(tools_controller.import_tool(ToolKind.python, file=symlink_path))

    assert str(ex.value) == "Symbolic links are not supported for tool file path."

def test_python_package_root_is_not_directory():
    with pytest.raises(BadParameter) as ex:
        tools_controller = ToolsController()
        list(tools_controller.import_tool(ToolKind.python, file="tests/cli"))

    assert str(ex.value) == "Provided tool file path is not a file."

def test_python_package_root_is_symlink():
    drop_module('testtool1')
    with pytest.raises(BadParameter) as ex:
        with tempfile.TemporaryDirectory() as tempdir:
            symlink_path = os.path.join(tempdir, "symlink_to_dir")
            os.symlink("test/cli/resources/python_multi_file_samples/testtool1", symlink_path)

            tools_controller = ToolsController()
            list(tools_controller.import_tool(ToolKind.python,
                                              file="tests/cli/resources/python_multi_file_samples/testtool1/testtool1.py",
                                              package_root=symlink_path))

    assert str(ex.value) == "The provided package root is not a directory."

def test_python_package_root_is_not_base_path_of_file():
    drop_module('testtool1')
    with pytest.raises(BadParameter) as ex:
        tools_controller = ToolsController()
        list(tools_controller.import_tool(ToolKind.python,
                                          file="tests/cli/resources/python_multi_file_samples/testtool1/testtool1.py",
                                          package_root="tests/agent_builder"))

    assert str(ex.value) == "The provided tool file path does not belong to the provided package root."

def test_python_with_package_root_binding_function_is_set():
    drop_module('testtool1')
    tools_controller = ToolsController()
    tools = list(tools_controller.import_tool(ToolKind.python,
                                              file="tests/cli/resources/python_multi_file_samples/testtool1/testtool1.py",
                                              package_root="tests/cli/resources/python_multi_file_samples/testtool1"))

    assert len(tools) == 1
    assert tools[0].__tool_spec__.binding.python.function == "testtool1:my_tool"
    assert tools[0].__tool_spec__.name == "testtool1_name"
    assert tools[0].__tool_spec__.permission == ToolPermission.READ_ONLY
    assert tools[0].__tool_spec__.binding.python.requirements == ["pytest>=8.3.4,<9.0.0", "requests==2.32.3"]

def test_python_with_package_root_with_trailing_slash_binding_function_is_set():
    drop_module('testtool2')
    tools_controller = ToolsController()
    tools = list(tools_controller.import_tool(ToolKind.python,
                                              file="tests/cli/resources/python_multi_file_samples/testtool2_single_file/testtool2.py",
                                              package_root="tests/cli/resources/python_multi_file_samples/"))

    assert len(tools) == 1
    assert (tools[0]).__tool_spec__.binding.python.function == "testtool2_single_file.testtool2:my_tool"
    assert tools[0].__tool_spec__.name == "testtool2_name"
    assert tools[0].__tool_spec__.permission == ToolPermission.READ_ONLY
    assert tools[0].__tool_spec__.binding.python.requirements == ["pytest>=8.3.4,<9.0.0"]

def test_python_with_package_root_binding_function_is_set2():
    drop_module('testtool1')
    tools_controller = ToolsController()
    tools = list(tools_controller.import_tool(ToolKind.python,
                                              file="tests/cli/resources/python_multi_file_samples/testtool1/testtool1.py",
                                              package_root="tests/cli/resources"))

    assert len(tools) == 1
    assert tools[0].__tool_spec__.binding.python.function == "python_multi_file_samples.testtool1.testtool1:my_tool"
    assert tools[0].__tool_spec__.name == "testtool1_name"
    assert tools[0].__tool_spec__.permission == ToolPermission.READ_ONLY
    assert tools[0].__tool_spec__.binding.python.requirements == ["pytest>=8.3.4,<9.0.0", "requests==2.32.3"]

def test_python_with_package_root_binding_function_is_set_when_package_root_is_tests():
    drop_module('testtool1')
    tools_controller = ToolsController()
    tools = list(tools_controller.import_tool(ToolKind.python,
                                              file="tests/cli/resources/python_multi_file_samples/testtool1/testtool1.py",
                                              package_root="tests"))

    assert len(tools) == 1
    assert tools[0].__tool_spec__.binding.python.function == "cli.resources.python_multi_file_samples.testtool1.testtool1:my_tool"
    assert tools[0].__tool_spec__.name == "testtool1_name"
    assert tools[0].__tool_spec__.permission == ToolPermission.READ_ONLY
    assert tools[0].__tool_spec__.binding.python.requirements == ["pytest>=8.3.4,<9.0.0", "requests==2.32.3"]

def test_python_with_package_root_binding_function_is_set_when_package_root_is_dir_of_tool():
    drop_module('testtool1')
    tools_controller = ToolsController()
    tools = list(tools_controller.import_tool(ToolKind.python,
                                              file="tests/cli/resources/python_multi_file_samples/testtool1/testtool1.py",
                                              package_root="tests/cli/resources/python_multi_file_samples/testtool1"))

    assert len(tools) == 1
    assert tools[0].__tool_spec__.binding.python.function == "testtool1:my_tool"
    assert tools[0].__tool_spec__.name == "testtool1_name"
    assert tools[0].__tool_spec__.permission == ToolPermission.READ_ONLY
    assert tools[0].__tool_spec__.binding.python.requirements == ["pytest>=8.3.4,<9.0.0", "requests==2.32.3"]

def test_python_without_package_root_binding_function_is_set():
    drop_module('testtool1')
    tools_controller = ToolsController()
    tools = list(tools_controller.import_tool(ToolKind.python,
                                              file="tests/cli/resources/python_multi_file_samples/testtool1/testtool1.py",
                                              package_root=None))

    assert len(tools) == 1
    assert tools[0].__tool_spec__.binding.python.function == "testtool1:my_tool"
    assert tools[0].__tool_spec__.name == "testtool1_name"
    assert tools[0].__tool_spec__.permission == ToolPermission.READ_ONLY
    assert tools[0].__tool_spec__.binding.python.requirements == ["pytest>=8.3.4,<9.0.0", "requests==2.32.3"]

def test_python_with_package_root_as_empty_string_binding_function_is_set():
    drop_module('testtool1')
    tools_controller = ToolsController()
    tools = list(tools_controller.import_tool(ToolKind.python,
                                              file="tests/cli/resources/python_multi_file_samples/testtool1/testtool1.py",
                                              package_root=""))

    assert len(tools) == 1
    assert tools[0].__tool_spec__.binding.python.function == "testtool1:my_tool"
    assert tools[0].__tool_spec__.name == "testtool1_name"
    assert tools[0].__tool_spec__.permission == ToolPermission.READ_ONLY
    assert tools[0].__tool_spec__.binding.python.requirements == ["pytest>=8.3.4,<9.0.0", "requests==2.32.3"]

def test_python_with_package_root_as_whitespace_string_binding_function_is_set():
    drop_module('testtool1')
    tools_controller = ToolsController()
    tools = list(tools_controller.import_tool(ToolKind.python,
                                              file="tests/cli/resources/python_multi_file_samples/testtool1/testtool1.py",
                                              package_root="    "))

    assert len(tools) == 1
    assert tools[0].__tool_spec__.binding.python.function == "testtool1:my_tool"
    assert tools[0].__tool_spec__.name == "testtool1_name"
    assert tools[0].__tool_spec__.permission == ToolPermission.READ_ONLY
    assert tools[0].__tool_spec__.binding.python.requirements == ["pytest>=8.3.4,<9.0.0", "requests==2.32.3"]

def test_python_with_package_root_binding_function_is_set_when_package_root_is_wrapped_in_whitespace():
    drop_module('testtool1')
    tools_controller = ToolsController()
    tools = list(tools_controller.import_tool(ToolKind.python,
                                              file="tests/cli/resources/python_multi_file_samples/testtool1/testtool1.py",
                                              package_root="  tests/cli/resources/python_multi_file_samples   "))

    assert len(tools) == 1
    assert tools[0].__tool_spec__.binding.python.function == "testtool1.testtool1:my_tool"
    assert tools[0].__tool_spec__.name == "testtool1_name"
    assert tools[0].__tool_spec__.permission == ToolPermission.READ_ONLY
    assert tools[0].__tool_spec__.binding.python.requirements == ["pytest>=8.3.4,<9.0.0", "requests==2.32.3"]

def test_python_with_no_package_root_fails_when_file_name_has_unsupported_characters():
    with pytest.raises(BadParameter) as ex:
        tools_controller = ToolsController()
        list(tools_controller.import_tool(ToolKind.python,
                                          file="tests/cli/resources/python_multi_file_samples/testtool3/test-tool 3.py",
                                          package_root=None))

    assert str(ex.value) == "File name contains unsupported characters. Only alphanumeric characters and underscores are allowed. Filename: \"test-tool 3\""

def test_python_with_package_root_fails_when_file_name_has_unsupported_characters():
    with pytest.raises(BadParameter) as ex:
        tools_controller = ToolsController()
        list(tools_controller.import_tool(ToolKind.python,
                                          file="tests/cli/resources/python_multi_file_samples/testtool3/test-tool 3.py",
                                          package_root="tests/cli/resources/python_multi_file_samples"))

    assert str(ex.value) == "File name contains unsupported characters. Only alphanumeric characters and underscores are allowed. Filename: \"test-tool 3\""

def test_python_with_no_package_root_and_unsupported_path_to_tool():
    drop_module('test_tool_4')
    tools_controller = ToolsController()
    tools = list(tools_controller.import_tool(ToolKind.python,
                                              file="tests/cli/resources/python_multi_file_samples/test-tool 4/testtool_4.py",
                                              package_root=None))

    assert len(tools) == 1
    assert tools[0].__tool_spec__.binding.python.function == "testtool_4:my_tool"
    assert tools[0].__tool_spec__.name == "testtool4_name"
    assert tools[0].__tool_spec__.permission == ToolPermission.READ_ONLY
    assert tools[0].__tool_spec__.binding.python.requirements == ["pytest>=8.3.4,<9.0.0"]

def test_python_with_package_root_and_unsupported_path_to_tool():
    with pytest.raises(BadParameter) as ex:
        tools_controller = ToolsController()
        list(tools_controller.import_tool(ToolKind.python,
                                          file="tests/cli/resources/python_multi_file_samples/test-tool 4/test_tool_4.py",
                                          package_root="tests/cli/resources"))

    assert str(ex.value) == "Path to tool file contains unsupported characters. Only alphanumeric characters and underscores are allowed. Path: \"python_multi_file_samples/test-tool 4/test_tool_4.py\""

def test_python_with_no_package_root_tool_name_has_unsupported_characters():
    drop_module('testtool5')
    with pytest.raises(BadParameter) as ex:
        tools_controller = ToolsController()
        list(tools_controller.import_tool(ToolKind.python,
                                          file="tests/cli/resources/python_multi_file_samples/testtool5/test_tool_5.py",
                                          package_root=None))

    assert str(ex.value) == "Tool name contains unsupported characters. Only alphanumeric characters and underscores are allowed. Name: \"test-tool 5 name\""

def test_python_with_package_root_tool_name_has_unsupported_characters():
    drop_module('testtool5')
    with pytest.raises(BadParameter) as ex:
        tools_controller = ToolsController()
        list(tools_controller.import_tool(ToolKind.python,
                                          file="tests/cli/resources/python_multi_file_samples/testtool5/test_tool_5.py",
                                          package_root="tests/cli/resources/python_multi_file_samples"))

    assert str(ex.value) == "Tool name contains unsupported characters. Only alphanumeric characters and underscores are allowed. Name: \"test-tool 5 name\""

def test_python_with_tool_in_subfolder_with_relative_imports():
    drop_module('testtool6')
    tools_controller = ToolsController()
    tools = list(tools_controller.import_tool(ToolKind.python,
                                              file="tests/cli/resources/python_multi_file_samples/testtool6/tools/testtool6.py",
                                              package_root="tests/cli/resources/python_multi_file_samples/testtool6",))

    assert len(tools) == 1
    assert tools[0].__tool_spec__.binding.python.function == "tools.testtool6:my_tool"
    assert tools[0].__tool_spec__.name == "testtool6_name"
    assert tools[0].__tool_spec__.permission == ToolPermission.READ_ONLY
    assert tools[0].__tool_spec__.binding.python.requirements == ["pytest>=8.3.4,<9.0.0", "requests==2.32.3"]

def test_python_with_tool_in_subfolder_with_package_level():
    drop_module('testtool7')
    tools_controller = ToolsController()
    tools = list(tools_controller.import_tool(ToolKind.python,
                                              file="tests/cli/resources/python_multi_file_samples/testtool7/tools/testtool7.py",
                                              package_root="tests/cli/resources/python_multi_file_samples/testtool7",))

    assert len(tools) == 1
    assert tools[0].__tool_spec__.binding.python.function == "tools.testtool7:my_tool"
    assert tools[0].__tool_spec__.name == "testtool7_name"
    assert tools[0].__tool_spec__.permission == ToolPermission.READ_ONLY
    assert tools[0].__tool_spec__.binding.python.requirements == ["pytest>=8.3.4,<9.0.0", "requests==2.32.3"]

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
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.get_connections_client') as mock_client:
        mock_response = MockListConnectionResponse(connection_id="12345")
        mock_client.return_value = MockConnectionClient(
            get_by_id_response=mock_response,
            get_response=mock_response
        )

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
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.get_connections_client') as mock_client:
        mock_response = MockListConnectionResponse(connection_id="12345")
        mock_client.return_value = MockConnectionClient(
            get_by_id_response=mock_response,
            get_response=mock_response
            )

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
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.get_connections_client') as mock_client:
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
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.get_connections_client') as mock_client:
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
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.get_connections_client') as mock_client:
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

    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.get_connections_client') as mock_client:
        mock_response = MockListConnectionResponse(connection_id="12345")
        mock_client.return_value = MockConnectionClient(
            get_response=MockConnection(appid="test", connection_type="basic_auth"),
            get_by_id_response=[mock_response],
            list_conn_response=[ListConfigsResponse(**{
                    "connection_id": "12345",
                    "app_id": "test",
                    "auth_type": None,
                    "security_scheme": "basic_auth",
            })]
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
    except ValueError as e:
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
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as client_mock, \
         mock.patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.is_local_dev", return_value=True), \
         mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.get_connections_client') as conn_client_mock:
        conn_client_mock.return_value = MockConnectionClient()
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

def test_single_publish_python_with_package_root_and_reqs_file():
    package_root = None
    tool_name = "testtool2"
    tool_description = ""
    tool_filename = "testtool2.py"
    tool_file = os.path.join("tests/cli/resources/python_multi_file_samples/testtool2_single_file", tool_filename)
    expected_requirements_file = 'tests/cli/resources/python_multi_file_samples/testtool2_single_file/requirements.txt'
    expected_binding_function = "python_multi_file_samples.testtool2_single_file.testtool2:my_tool"

    with mock.patch(
            'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client, \
            mock.patch('zipfile.ZipFile') as mock_zipfile, \
            mock.patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.Config") as mock_cfg:
        cfg = MockConfig2()
        cfg.save(DEFAULT_CONFIG_FILE_CONTENT)
        cfg.write(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, RegistryType.LOCAL)
        mock_cfg.return_value = cfg
        spec = ToolSpec(
            name=tool_name,
            description=tool_description,
            permission=ToolPermission.READ_ONLY,
            binding={"python": {
                "function": expected_binding_function,
                "requirements": get_file_lines(expected_requirements_file),
            }}
        )
        tools = [
            PythonTool(fn=expected_binding_function, spec=spec)
        ]

        mock_instantiate_client.return_value = MockToolClient(
            expected=spec.model_dump(exclude_none=True, exclude_defaults=True),
            tool_name=tool_name,
            file_path="artifacts.zip"
        )

        tools_controller = ToolsController(ToolKind.python,
                                           file=tool_file,
                                           requirements_file=expected_requirements_file)

        tools_controller.publish_or_update_tools(tools, package_root=package_root)

        mock_instantiate_client.assert_called_once_with(ToolClient)
        mock_zipfile.assert_called
        mock_zipfile.write.assert_called

        published_artifact_dir = Path(mock_instantiate_client.return_value.published_file_path).parent

        mock_zipfile.return_value.__enter__.return_value.write.assert_has_calls(
            [
                call(Path(tool_file), arcname=tool_filename),
                call(published_artifact_dir.joinpath("requirements.txt"), arcname="requirements.txt")
            ],
            any_order=True
        )

        mock_zipfile.return_value.__enter__.return_value.writestr.assert_has_calls(
            [
                call("bundle-format", "2.0.0\n")
            ],
            any_order=True
        )

def test_single_publish_python_with_reqs_file_no_package_root():
    package_root = None
    tool_name = "testtool2"
    tool_description = ""
    tool_filename = "testtool2.py"
    tool_file = os.path.join("tests/cli/resources/python_multi_file_samples/testtool2_single_file", tool_filename)
    requirements_file = 'tests/cli/resources/python_multi_file_samples/testtool2_single_file/requirements.txt'
    expected_requirements_file = 'tests/cli/resources/python_multi_file_samples/testtool2_single_file/requirements.txt'
    expected_binding_function = "python_multi_file_samples.testtool2_single_file.testtool2:my_tool"

    with mock.patch(
            'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client, \
            mock.patch('zipfile.ZipFile') as mock_zipfile, \
            mock.patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.Config") as mock_cfg:
        cfg = MockConfig2()
        cfg.save(DEFAULT_CONFIG_FILE_CONTENT)
        cfg.write(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, RegistryType.LOCAL)
        mock_cfg.return_value = cfg
        spec = ToolSpec(
            name=tool_name,
            description=tool_description,
            permission=ToolPermission.READ_ONLY,
            binding={"python": {
                "function": expected_binding_function,
                "requirements": get_file_lines(expected_requirements_file),
            }}
        )
        tools = [
            PythonTool(fn=expected_binding_function, spec=spec)
        ]

        mock_instantiate_client.return_value = MockToolClient(
            expected=spec.model_dump(exclude_none=True, exclude_defaults=True),
            tool_name=tool_name,
            file_path="artifacts.zip"
        )

        tools_controller = ToolsController(ToolKind.python,
                                           file=tool_file,
                                           requirements_file=requirements_file)

        tools_controller.publish_or_update_tools(tools, package_root=package_root)

        mock_instantiate_client.assert_called_once_with(ToolClient)
        mock_zipfile.assert_called
        mock_zipfile.write.assert_called

        published_artifact_dir = Path(mock_instantiate_client.return_value.published_file_path).parent

        mock_zipfile.return_value.__enter__.return_value.write.assert_has_calls(
            [
                call(Path(tool_file), arcname=tool_filename),
                call(published_artifact_dir.joinpath("requirements.txt"), arcname="requirements.txt")
            ],
            any_order=True
        )

        mock_zipfile.return_value.__enter__.return_value.writestr.assert_has_calls(
            [
                call("bundle-format", "2.0.0\n")
            ],
            any_order=True
        )

def test_single_publish_python_with_no_reqs_file_no_package_root():
    package_root = None
    tool_name = "testtool2"
    tool_description = ""
    tool_filename = "testtool2.py"
    tool_file = os.path.join("tests/cli/resources/python_multi_file_samples/testtool2_single_file", tool_filename)
    requirements_file = None
    expected_requirements_file = 'tests/cli/resources/python_multi_file_samples/testtool2_single_file/requirements.txt'
    expected_binding_function = "python_multi_file_samples.testtool2_single_file.testtool2:my_tool"

    with mock.patch(
            'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client, \
            mock.patch('zipfile.ZipFile') as mock_zipfile, \
            mock.patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.Config") as mock_cfg:
        cfg = MockConfig2()
        cfg.save(DEFAULT_CONFIG_FILE_CONTENT)
        cfg.write(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, RegistryType.LOCAL)
        mock_cfg.return_value = cfg
        spec = ToolSpec(
            name=tool_name,
            description=tool_description,
            permission=ToolPermission.READ_ONLY,
            binding={"python": {
                "function": expected_binding_function,
                "requirements": get_file_lines(expected_requirements_file),
            }}
        )
        tools = [
            PythonTool(fn=expected_binding_function, spec=spec)
        ]

        mock_instantiate_client.return_value = MockToolClient(
            expected=spec.model_dump(exclude_none=True, exclude_defaults=True),
            tool_name=tool_name,
            file_path="artifacts.zip"
        )

        tools_controller = ToolsController(ToolKind.python,
                                           file=tool_file,
                                           requirements_file=requirements_file)

        tools_controller.publish_or_update_tools(tools, package_root=package_root)

        mock_instantiate_client.assert_called_once_with(ToolClient)
        mock_zipfile.assert_called
        mock_zipfile.write.assert_called

        published_artifact_dir = Path(mock_instantiate_client.return_value.published_file_path).parent

        mock_zipfile.return_value.__enter__.return_value.write.assert_has_calls(
            [
                call(Path(tool_file), arcname=tool_filename),
                call(published_artifact_dir.joinpath("requirements.txt"), arcname="requirements.txt")
            ],
            any_order=True
        )

        mock_zipfile.return_value.__enter__.return_value.writestr.assert_has_calls(
            [
                call("bundle-format", "2.0.0\n")
            ],
            any_order=True
        )

def test_single_publish_python_with_package_root_and_no_reqs_file():
    package_root = "tests/cli/resources/python_multi_file_samples"
    tool_name = "testtool2"
    tool_description = ""
    tool_filename = "testtool2.py"
    tool_file = os.path.join("tests/cli/resources/python_multi_file_samples/testtool2_single_file", tool_filename)
    requirements_file = None
    expected_requirements_file = 'tests/cli/resources/python_multi_file_samples/testtool2_single_file/requirements.txt'
    expected_binding_function = "python_multi_file_samples.testtool2_single_file.testtool2:my_tool"

    with mock.patch(
            'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client, \
            mock.patch('zipfile.ZipFile') as mock_zipfile, \
            mock.patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.Config") as mock_cfg:
        cfg = MockConfig2()
        cfg.save(DEFAULT_CONFIG_FILE_CONTENT)
        cfg.write(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, RegistryType.LOCAL)
        mock_cfg.return_value = cfg
        spec = ToolSpec(
            name=tool_name,
            description=tool_description,
            permission=ToolPermission.READ_ONLY,
            binding={"python": {
                "function": expected_binding_function,
                "requirements": get_file_lines(expected_requirements_file),
            }}
        )
        tools = [
            PythonTool(fn=expected_binding_function, spec=spec)
        ]

        mock_instantiate_client.return_value = MockToolClient(
            expected=spec.model_dump(exclude_none=True, exclude_defaults=True),
            tool_name=tool_name,
            file_path="artifacts.zip"
        )

        tools_controller = ToolsController(ToolKind.python,
                                           file=tool_file,
                                           requirements_file=requirements_file)

        tools_controller.publish_or_update_tools(tools, package_root=package_root)

        mock_instantiate_client.assert_called_once_with(ToolClient)
        mock_zipfile.assert_called
        mock_zipfile.write.assert_called

        published_artifact_dir = Path(mock_instantiate_client.return_value.published_file_path).parent

        mock_zipfile.return_value.__enter__.return_value.write.assert_has_calls(
            [
                call(tool_file, arcname="testtool2_single_file/testtool2.py"),
                call(published_artifact_dir.joinpath("requirements.txt"), arcname="requirements.txt")
            ],
            any_order=True
        )

        mock_zipfile.return_value.__enter__.return_value.writestr.assert_has_calls(
            [
                call("bundle-format", "2.0.0\n")
            ],
            any_order=True
        )

def test_single_publish_python_with_package_root_and_reqs_file():
    package_root = "tests/cli/resources/python_multi_file_samples"
    tool_name = "testtool2"
    tool_description = ""
    tool_filename = "testtool2.py"
    tool_file = os.path.join("tests/cli/resources/python_multi_file_samples/testtool2_single_file", tool_filename)
    requirements_file = 'tests/cli/resources/python_multi_file_samples/testtool1/requirements.txt'
    expected_requirements_file = 'tests/cli/resources/python_multi_file_samples/testtool1/requirements.txt'
    expected_binding_function = "python_multi_file_samples.testtool2_single_file.testtool2:my_tool"

    with mock.patch(
            'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client, \
            mock.patch('zipfile.ZipFile') as mock_zipfile, \
            mock.patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.Config") as mock_cfg:
        cfg = MockConfig2()
        cfg.save(DEFAULT_CONFIG_FILE_CONTENT)
        cfg.write(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, RegistryType.LOCAL)
        mock_cfg.return_value = cfg
        spec = ToolSpec(
            name=tool_name,
            description=tool_description,
            permission=ToolPermission.READ_ONLY,
            binding={"python": {
                "function": expected_binding_function,
                "requirements": get_file_lines(expected_requirements_file),
            }}
        )
        tools = [
            PythonTool(fn=expected_binding_function, spec=spec)
        ]

        mock_instantiate_client.return_value = MockToolClient(
            expected=spec.model_dump(exclude_none=True, exclude_defaults=True),
            tool_name=tool_name,
            file_path="artifacts.zip"
        )

        tools_controller = ToolsController(ToolKind.python,
                                           file=tool_file,
                                           requirements_file=requirements_file)

        tools_controller.publish_or_update_tools(tools, package_root=package_root)

        mock_instantiate_client.assert_called_once_with(ToolClient)
        mock_zipfile.assert_called
        mock_zipfile.write.assert_called

        published_artifact_dir = Path(mock_instantiate_client.return_value.published_file_path).parent

        mock_zipfile.return_value.__enter__.return_value.write.assert_has_calls(
            [
                call(tool_file, arcname="testtool2_single_file/testtool2.py"),
                call(published_artifact_dir.joinpath("requirements.txt"), arcname="requirements.txt")
            ],
            any_order=True
        )

        mock_zipfile.return_value.__enter__.return_value.writestr.assert_has_calls(
            [
                call("bundle-format", "2.0.0\n")
            ],
            any_order=True
        )

def test_multifile_publish_python_with_package_root_and_reqs_file():
    package_root = "tests/cli/resources/python_multi_file_samples"
    tool_name = "testtool1"
    tool_description = ""
    tool_filename = "testtool1.py"
    tool_file_dir = "tests/cli/resources/python_multi_file_samples/testtool1"
    tool_file = os.path.join(tool_file_dir, tool_filename)
    requirements_file = 'tests/cli/resources/python_multi_file_samples/testtool1/requirements.txt'
    expected_requirements_file = 'tests/cli/resources/python_multi_file_samples/testtool1/requirements.txt'
    expected_binding_function = "python_multi_file_samples.testtool1.testtool1:my_tool"

    with mock.patch(
            'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client, \
            mock.patch('zipfile.ZipFile') as mock_zipfile, \
            mock.patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.Config") as mock_cfg:
        cfg = MockConfig2()
        cfg.save(DEFAULT_CONFIG_FILE_CONTENT)
        cfg.write(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, RegistryType.LOCAL)
        mock_cfg.return_value = cfg
        spec = ToolSpec(
            name=tool_name,
            description=tool_description,
            permission=ToolPermission.READ_ONLY,
            binding={"python": {
                "function": expected_binding_function,
                "requirements": get_file_lines(expected_requirements_file),
            }}
        )
        tools = [
            PythonTool(fn=expected_binding_function, spec=spec)
        ]

        mock_instantiate_client.return_value = MockToolClient(
            expected=spec.model_dump(exclude_none=True, exclude_defaults=True),
            tool_name=tool_name,
            file_path="artifacts.zip"
        )

        tools_controller = ToolsController(ToolKind.python,
                                           file=tool_file,
                                           requirements_file=requirements_file)

        tools_controller.publish_or_update_tools(tools, package_root=package_root)

        mock_instantiate_client.assert_called_once_with(ToolClient)
        mock_zipfile.assert_called
        mock_zipfile.write.assert_called

        published_artifact_dir = Path(mock_instantiate_client.return_value.published_file_path).parent

        mock_zipfile.return_value.__enter__.return_value.write.assert_has_calls(
            [
                call(tool_file, arcname="testtool1/testtool1.py"),
                call(os.path.join(tool_file_dir, "libref/sidemod.py"), arcname="testtool1/libref/sidemod.py"),
                call(os.path.join(tool_file_dir, "__init__.py"), arcname="testtool1/__init__.py"),
                call(published_artifact_dir.joinpath("requirements.txt"), arcname="requirements.txt")
            ],
            any_order=True
        )

        mock_zipfile.return_value.__enter__.return_value.writestr.assert_has_calls(
            [
                call("bundle-format", "2.0.0\n")
            ],
            any_order=True
        )

def test_multifile_publish_python_with_no_package_root_and_reqs_file():
    package_root = None
    tool_name = "testtool1"
    tool_description = ""
    tool_filename = "testtool1.py"
    tool_file_dir = "tests/cli/resources/python_multi_file_samples/testtool1"
    tool_file = os.path.join(tool_file_dir, tool_filename)
    requirements_file = 'tests/cli/resources/python_multi_file_samples/testtool1/requirements.txt'
    expected_requirements_file = 'tests/cli/resources/python_multi_file_samples/testtool1/requirements.txt'
    expected_binding_function = "python_multi_file_samples.testtool1.testtool1:my_tool"

    with mock.patch(
            'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client, \
            mock.patch('zipfile.ZipFile') as mock_zipfile, \
            mock.patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.Config") as mock_cfg:
        cfg = MockConfig2()
        cfg.save(DEFAULT_CONFIG_FILE_CONTENT)
        cfg.write(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, RegistryType.LOCAL)
        mock_cfg.return_value = cfg
        spec = ToolSpec(
            name=tool_name,
            description=tool_description,
            permission=ToolPermission.READ_ONLY,
            binding={"python": {
                "function": expected_binding_function,
                "requirements": get_file_lines(expected_requirements_file),
            }}
        )
        tools = [
            PythonTool(fn=expected_binding_function, spec=spec)
        ]

        mock_instantiate_client.return_value = MockToolClient(
            expected=spec.model_dump(exclude_none=True, exclude_defaults=True),
            tool_name=tool_name,
            file_path="artifacts.zip"
        )

        tools_controller = ToolsController(ToolKind.python,
                                           file=tool_file,
                                           requirements_file=requirements_file)

        tools_controller.publish_or_update_tools(tools, package_root=package_root)

        mock_instantiate_client.assert_called_once_with(ToolClient)
        mock_zipfile.assert_called
        mock_zipfile.write.assert_called

        published_artifact_dir = Path(mock_instantiate_client.return_value.published_file_path).parent

        mock_zipfile.return_value.__enter__.return_value.write.assert_has_calls(
            [
                call(Path(tool_file), arcname="testtool1.py"),
                call(published_artifact_dir.joinpath("requirements.txt"), arcname="requirements.txt")
            ],
            any_order=True
        )

        mock_zipfile.return_value.__enter__.return_value.writestr.assert_has_calls(
            [
                call("bundle-format", "2.0.0\n")
            ],
            any_order=True
        )

def test_multifile_publish_python_with_package_root_and_reqs_file2():
    package_root = "tests/cli/resources/python_multi_file_samples/testtool1"
    tool_name = "testtool1"
    tool_description = ""
    tool_filename = "testtool1.py"
    tool_file_dir = "tests/cli/resources/python_multi_file_samples/testtool1"
    tool_file = os.path.join(tool_file_dir, tool_filename)
    requirements_file = 'tests/cli/resources/python_multi_file_samples/testtool1/requirements.txt'
    expected_requirements_file = 'tests/cli/resources/python_multi_file_samples/testtool1/requirements.txt'
    expected_binding_function = "python_multi_file_samples.testtool1.testtool1:my_tool"

    with mock.patch(
            'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client, \
            mock.patch('zipfile.ZipFile') as mock_zipfile, \
            mock.patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.Config") as mock_cfg:
        cfg = MockConfig2()
        cfg.save(DEFAULT_CONFIG_FILE_CONTENT)
        cfg.write(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, RegistryType.LOCAL)
        mock_cfg.return_value = cfg
        spec = ToolSpec(
            name=tool_name,
            description=tool_description,
            permission=ToolPermission.READ_ONLY,
            binding={"python": {
                "function": expected_binding_function,
                "requirements": get_file_lines(expected_requirements_file),
            }}
        )
        tools = [
            PythonTool(fn=expected_binding_function, spec=spec)
        ]

        mock_instantiate_client.return_value = MockToolClient(
            expected=spec.model_dump(exclude_none=True, exclude_defaults=True),
            tool_name=tool_name,
            file_path="artifacts.zip"
        )

        tools_controller = ToolsController(ToolKind.python,
                                           file=tool_file,
                                           requirements_file=requirements_file)

        tools_controller.publish_or_update_tools(tools, package_root=package_root)

        mock_instantiate_client.assert_called_once_with(ToolClient)
        mock_zipfile.assert_called
        mock_zipfile.write.assert_called

        published_artifact_dir = Path(mock_instantiate_client.return_value.published_file_path).parent

        mock_zipfile.return_value.__enter__.return_value.write.assert_has_calls(
            [
                call(tool_file, arcname="testtool1.py"),
                call(os.path.join(tool_file_dir, "libref/sidemod.py"), arcname="libref/sidemod.py"),
                call(os.path.join(tool_file_dir, "__init__.py"), arcname="__init__.py"),
                call(published_artifact_dir.joinpath("requirements.txt"), arcname="requirements.txt")
            ],
            any_order=True
        )

        mock_zipfile.return_value.__enter__.return_value.writestr.assert_has_calls(
            [
                call("bundle-format", "2.0.0\n")
            ],
            any_order=True
        )

def test_get_kind_from_spec_python():
    mock_tool_name = "test_tool"
    mock_spec = {
        "name": mock_tool_name,
        "binding": {
            "python": {}
        }
    }
    result = _get_kind_from_spec(mock_spec)

    assert result == ToolKind.python

def test_get_kind_from_spec_openapi():
    mock_tool_name = "test_tool"
    mock_spec = {
        "name": mock_tool_name,
        "binding": {
            "openapi": {}
        }
    }
    result = _get_kind_from_spec(mock_spec)

    assert result == ToolKind.openapi

def test_get_kind_from_spec_invalid(caplog):
    mock_tool_name = "test_tool"
    mock_spec = {
        "name": mock_tool_name,
        "binding": {
            "test": {}
        }
    }

    with pytest.raises(SystemExit):
        result = _get_kind_from_spec(mock_spec)

    captured = caplog.text

    assert f"Could not determine 'kind' of tool '{mock_tool_name}'" in captured

def test_download_tool_python():
    mock_tool_name = "test_tool"
    mock_tool_id = "test_tool_id"
    mock_download_reponse = b"1234"
    tc = ToolsController()

    tc.client = MockToolClient(get_draft_by_name_response=[
        {
            "name": mock_tool_name,
            "id": mock_tool_id,
            "binding": {
                "python": {}
            }
        }
    ],
    download_tools_artifact_response=mock_download_reponse
    )

    response = tc.download_tool(mock_tool_name)

    assert response == mock_download_reponse

def test_download_tool_openapi(caplog):
    mock_tool_name = "test_tool"
    mock_tool_id = "test_tool_id"
    tc = ToolsController()

    tc.client = MockToolClient(get_draft_by_name_response=[
        {
            "name": mock_tool_name,
            "id": mock_tool_id,
            "binding": {
                "openapi": {}
            }
        }
    ],
    )

    response = tc.download_tool(mock_tool_name)

    captured = caplog.text

    assert response is None
    assert f"Skipping '{mock_tool_name}', openapi tools are currently unsupported by export" in captured

def test_download_tool_no_tool(caplog):
    mock_tool_name = "test_tool"
    tc = ToolsController()

    tc.client = MockToolClient(get_draft_by_name_response=[]
    )

    with pytest.raises(SystemExit):
        response = tc.download_tool(mock_tool_name)

    captured = caplog.text
    assert f"No tool named '{mock_tool_name}' found" in captured

def test_download_tool_multiple_tools(caplog):
    mock_tool_name = "test_tool"
    tc = ToolsController()

    tc.client = MockToolClient(get_draft_by_name_response=[{},{}]
    )

    with pytest.raises(SystemExit):
        response = tc.download_tool(mock_tool_name)

    captured = caplog.text
    assert f"Multiple existing tools found with name '{mock_tool_name}'. Failed to get tool" in captured

def test_export_tool(caplog):
    mock_tool_name = "test_tool"
    mock_output_file = "test_file_out.zip"
    mock_tool_id = "test_tool_id"
    mock_download_reponse = b"1234"
    tc = ToolsController()

    tc.client = MockToolClient(get_draft_by_name_response=[
        {
            "name": mock_tool_name,
            "id": mock_tool_id,
            "binding": {
                "python": {}
            }
        }
    ],
    download_tools_artifact_response=mock_download_reponse
    )

    with mock.patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.zipfile.ZipFile") as mock_zipfile:

        mock_zipfile().__enter__().infolist.return_value = [mock.MagicMock()]

        tc.export_tool(name=mock_tool_name, output_path=mock_output_file)

    captured = caplog.text

    assert f"Exporting tool definition for '{mock_tool_name}' to '{mock_output_file}'" in captured
    assert f"Successfully exported tool definition for '{mock_tool_name}' to '{mock_output_file}'" in captured

def test_export_tool_no_data(caplog):
    mock_tool_name = "test_tool"
    mock_output_file = "test_file_out.zip"
    mock_tool_id = "test_tool_id"
    mock_download_reponse = None
    tc = ToolsController()

    tc.client = MockToolClient(get_draft_by_name_response=[
        {
            "name": mock_tool_name,
            "id": mock_tool_id,
            "binding": {
                "python": {}
            }
        }
    ],
    download_tools_artifact_response=mock_download_reponse
    )

    with mock.patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.zipfile.ZipFile") as mock_zipfile:
        tc.export_tool(name=mock_tool_name, output_path=mock_output_file)

    captured = caplog.text

    assert f"Exporting tool definition for '{mock_tool_name}' to '{mock_output_file}'" in captured
    assert f"Successfully exported tool definition for '{mock_tool_name}' to '{mock_output_file}'" not in captured

def test_export_tool_invalid_output_file(caplog):
    mock_tool_name = "test_tool"
    mock_output_file = "test_file_out.txt"
    tc = ToolsController()

    tc.client = MockToolClient()

    with mock.patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.zipfile.ZipFile") as mock_zipfile:
        with pytest.raises(SystemExit):
            tc.export_tool(name=mock_tool_name, output_path=mock_output_file)

    captured = caplog.text

    assert f"Exporting tool definition for '{mock_tool_name}' to '{mock_output_file}'" not in captured
    assert f"Successfully exported tool definition for '{mock_tool_name}' to '{mock_output_file}'" not in captured
    assert f"Output file must end with the extension '.zip'. Provided file '{mock_output_file}' ends with 'txt'"