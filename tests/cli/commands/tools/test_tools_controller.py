from unittest import mock

from ibm_watsonx_orchestrate.cli.commands.tools import tools_controller
from typer import BadParameter
import json
from unittest.mock import patch
import os
import pytest
import typer

from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolKind


class MockSDKResponse:
    def __init__(self, response_obj):
        self.response_obj = response_obj

    def dumps_spec(self):
        return json.dumps(self.response_obj)


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
        tools_controller.import_tool(
            ToolKind.openapi,
            file=file,
            app_id='appId'
        )

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
        tools_controller.import_tool(ToolKind.openapi, file="tests/cli/resources/yaml_samples/tool.yaml",  app_id=None)
        assert calls == [
            (
                ('tests/cli/resources/yaml_samples/tool.yaml', None),
                {}
            )
        ]


def test_openapi_no_file():
    try:
        tools_controller.import_tool(ToolKind.openapi, file=None)
        assert False
    except BadParameter:
        assert True



def test_python_params_valid(capsys):
    # TODO: Mock importlib or Mock Tool
    tools_controller.import_tool(
        "python", file=os.path.join(os.path.dirname(__file__), "../../resources/python_samples/tool_w_metadata.py")
    )

    captured = capsys.readouterr()
    json_captured = json.loads(str(captured.out))

    assert json_captured["name"] == "myName"
    assert json_captured["permission"] == "admin"


def test_python_no_file():
    try:
        tools_controller.import_tool("python", file=None)
        assert False
    except BadParameter:
        assert True


def test_skill_valid():
    tools_controller.import_tool(
        "skill",
        skillset_id="fake_skillset",
        skill_id="fake_skill",
        skill_operation_path="fake_operation_path",
    )


def test_skill_missing_args():
    try:
        tools_controller.import_tool(
            "skill", skillset_id=None, skill_id=None, skill_operation_path=None
        )
        assert False
    except BadParameter:
        assert True


def test_invalid_kind():
    try:
        tools_controller.import_tool("invalid")
        assert False
    except ValueError as e:
        assert True
        assert str(e) == "Invalid kind selected"
