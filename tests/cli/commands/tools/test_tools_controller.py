from unittest import mock
from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolsController
from ibm_watsonx_orchestrate.agent_builder.tools.types import ToolPermission, ToolSpec
from ibm_watsonx_orchestrate.agent_builder.tools.openapi_tool import OpenAPITool
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from typer import BadParameter
import json
import os
import pytest
import typer

from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolKind


class MockSDKResponse:
    def __init__(self, response_obj):
        self.response_obj = response_obj

    def dumps_spec(self):
        return json.dumps(self.response_obj)

class MockToolClient:
    def __init__(self, expected, get_reponse=[]):
        self.expected = expected
        self.get_reponse = get_reponse
        
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
    try:
        tools_controller = ToolsController()
        tools = tools_controller.import_tool(ToolKind.openapi, file=None)
        list(tools)
        assert False
    except BadParameter:
        assert True


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
    # TODO: Mock importlib or Mock Tool
    tools_controller = ToolsController()
    tools = tools_controller.import_tool(
        "python", file=os.path.join(os.path.dirname(__file__), "../../resources/python_samples/tool_w_metadata.py")
    )

    tools = list(tools)
    assert len(tools) > 0    
    
    tool = tools[0]
    assert tool.__tool_spec__.name == "myName"
    assert tool.__tool_spec__.permission == ToolPermission.ADMIN


def test_python_no_file():
    try:
        tools_controller = ToolsController()
        tools = tools_controller.import_tool("python", file=None)
        list(tools)
        assert False
    except BadParameter:
        assert True


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
    try:
        tools_controller = ToolsController()
        tools=tools_controller.import_tool(
            "skill", skillset_id=None, skill_id=None, skill_operation_path=None
        )
        list(tools)
        assert False
    except BadParameter:
        assert True

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
