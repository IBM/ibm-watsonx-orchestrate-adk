import re
from unittest import mock
from ibm_watsonx_orchestrate.agent_builder.tools.python_tool import PythonTool
from ibm_watsonx_orchestrate.cli.commands.tools import tools_controller as ToolsControllerClass
from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolsController, ToolKind
from ibm_watsonx_orchestrate.agent_builder.tools.types import ToolPermission, ToolSpec
from ibm_watsonx_orchestrate.agent_builder.tools.openapi_tool import OpenAPITool
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from typer import BadParameter
import json
import pytest


class MockSDKResponse:
    def __init__(self, response_obj):
        self.response_obj = response_obj

    def dumps_spec(self):
        return json.dumps(self.response_obj)

class MockToolClient:
    def __init__(self, expected, get_reponse=[], tool_name="", file_path=""):
        self.expected = expected
        self.get_reponse = get_reponse
        self.tool_name = tool_name
        self.file_path = file_path
        
    def create(self, spec):
        for key in self.expected:
            assert spec[key] == self.expected[key]
    def get(self):
        return self.get_reponse
    def update(self, name, spec):
        assert name in [x["name"] for x in self.get_reponse]
        for key in self.expected:
            assert spec[key] == self.expected[key]
    def delete(self):
        pass
    def upload_tools_artifact(self, tool_name: str, file_path: str):
        assert tool_name == self.tool_name
        assert file_path.endswith(self.file_path)

def test_openapi_params_valid(capsys):
    calls = []

    async def create_openapi_json_tools_from_uri(*args, **kwargs):
        calls.append((args, kwargs))
        return []

    with mock.patch(
            'ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.create_openapi_json_tools_from_uri',
            create_openapi_json_tools_from_uri
    ):
        file = "../resources/yaml_samples/tool.yaml"
        tools_controller = ToolsController()

        tools = tools_controller.import_tool(
            ToolKind.openapi,
            file=file,
            app_id='appId'
        )

        list(tools)
        assert calls == [
            (
                ('../resources/yaml_samples/tool.yaml', 'appId'),
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
        tools = tools_controller.import_tool(ToolKind.openapi, file="tests/cli/resources/yaml_samples/tool.yaml",  app_id=None)
        list(tools)
        assert calls == [
            (
                ('tests/cli/resources/yaml_samples/tool.yaml', None),
                {}
            )
        ]


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
            expected=spec.model_dump(exclude_none=True, exclude_defaults=True),
            get_reponse=[{"name": "test", "id": "123"}]
        )

        tools_controller = ToolsController()
        tools_controller.publish_or_update_tools(tools)


        mock_instantiate_client.assert_called_once_with(ToolClient)


def test_python_params_valid():
    tools_controller = ToolsController()
    tools = tools_controller.import_tool(
        ToolKind.python, 
        file = "tests/cli/resources/python_samples/tool_w_metadata.py",
        requirements_file = "tests/cli/resources/python_samples/requirements.txt"
    )

    tools = list(tools)
    assert len(tools) > 0    
    
    tool = tools[0]
    assert tool.__tool_spec__.name == "myName"
    assert tool.__tool_spec__.permission == ToolPermission.ADMIN


def test_python_no_file():
    with pytest.raises(BadParameter):
        tools_controller = ToolsController()
        tools = tools_controller.import_tool(ToolKind.python, file=None, requirements_file=None)
        list(tools)

def test_python_file_not_readable():
    with pytest.raises(BadParameter, match="Failed to load python module from file does_not_exist.py: No module named 'does_not_exist'") as e:
        tools_controller = ToolsController()
        tools = tools_controller.import_tool(ToolKind.python, file="does_not_exist.py", requirements_file="tests/cli/resources/python_samples/requirements.txt")
        list(tools)
    
def test_python_requirements_file_not_readable():
    with pytest.raises(BadParameter, match=re.escape("Failed to read file does_not_exist.txt [Errno 2] No such file or directory: 'does_not_exist.txt'")):
        tools_controller = ToolsController()
        tools = tools_controller.import_tool(ToolKind.python, file="tests/cli/resources/python_samples/tool_w_metadata.py", requirements_file="does_not_exist.txt")
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
        tools=tools_controller.import_tool(
            "skill", skillset_id=None, skill_id=None, skill_operation_path=None
        )
        list(tools)

def test_invalid_kind():
    try:
        tools_controller = ToolsController()
        tools=tools_controller.import_tool("invalid")
        list(tools)
        assert False
    except ValueError as e:
        assert True
        assert str(e) == "Invalid kind selected"

def test_validate_params_app_id_for_incorrect_kind():

    with pytest.raises(BadParameter) as exc:
        tools_controller = ToolsController()
        tools=tools_controller.import_tool(kind='python', app_id="123")
        list(tools)

    assert exc.value.message == '--app_id parameter can only be used with openapi tools'


def test_publish_python():
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client, \
         mock.patch('zipfile.ZipFile') as mock_zipfile:
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

        tools_controller = ToolsController(ToolKind.python, "test_tool.py", 'tests/cli/resources/python_samples/requirements.txt')
        tools_controller.publish_or_update_tools(tools)


        mock_instantiate_client.assert_called_once_with(ToolClient)
        mock_zipfile.assert_called

def test_update_python():
    with mock.patch('ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.instantiate_client') as mock_instantiate_client, \
         mock.patch('zipfile.ZipFile') as mock_zipfile:
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
            get_reponse=[{"name": "test", "id": "123"}],
            tool_name="test",
            file_path="artifacts.zip"
        )

        tools_controller = ToolsController()
        tools_controller.publish_or_update_tools(tools)


        mock_instantiate_client.assert_called_once_with(ToolClient)
        mock_zipfile.assert_called
