from ibm_watsonx_orchestrate.cli.commands.toolkit import toolkit_command
from ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller import ToolkitKind, Language
from unittest.mock import patch
import pytest


def test_import_toolkit_basic_call():
    with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command.ToolkitController.import_toolkit") as mock:
        toolkit_command.import_toolkit(
            kind=ToolkitKind.MCP,
            name="mcp-eric101",
            description="test description",
            package_root="/some/path",
            command="node dist/index.js --transport stdio"
        )
        mock.assert_called_once_with(
            tools=None,
            app_id=None
        )


def test_import_toolkit_with_tools_and_app_id():
    with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command.ToolkitController.import_toolkit") as mock:
        toolkit_command.import_toolkit(
            kind=ToolkitKind.MCP,
            name="mcp-eric102",
            description="toolkit with tools and app id",
            package_root="/some/other/path",
            command="node dist/index.js --transport stdio",
            tools="list-repositories,get-user",
            app_id=["github"]
        )
        mock.assert_called_once_with(
            tools=["list-repositories", "get-user"],
            app_id=["github"]
        )


def test_import_toolkit_with_star_tools():
    with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command.ToolkitController.import_toolkit") as mock:
        toolkit_command.import_toolkit(
            kind=ToolkitKind.MCP,
            name="mcp-eric103",
            description="toolkit using *",
            package_root="/some/path",
            command="node dist/index.js --transport stdio",
            tools="*",
            app_id=["github"]
        )
        mock.assert_called_once_with(
            tools=["*"],
            app_id=["github"]
        )


def test_remove_toolkit_call():
    with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command.ToolkitController.remove_toolkit") as mock:
        toolkit_command.remove_toolkit(name="mcp-eric101")
        mock.assert_called_once_with(name="mcp-eric101")


def test_list_toolkits_verbose():
    with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command.ToolkitController.list_toolkits") as mock:
        toolkit_command.list_toolkits(verbose=True)
        mock.assert_called_once_with(verbose=True)


def test_list_toolkits_non_verbose():
    with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command.ToolkitController.list_toolkits") as mock:
        toolkit_command.list_toolkits()
        mock.assert_called_once_with(verbose=False)


def test_import_toolkit_requires_command_with_package_root():
    with pytest.raises(SystemExit):
        toolkit_command.import_toolkit(
            kind=ToolkitKind.MCP,
            name="mcp-invalid",
            description="missing command",
            package_root="/some/path"
        )


def test_import_toolkit_conflicting_package_and_package_root():
    with pytest.raises(SystemExit):
        toolkit_command.import_toolkit(
            kind=ToolkitKind.MCP,
            name="mcp-invalid",
            description="conflicting flags",
            package="some-pkg",
            package_root="/some/path",
            command="node dist/index.js"
        )


def test_import_toolkit_requires_language_for_inferred_command():
    with pytest.raises(SystemExit):
        toolkit_command.import_toolkit(
            kind=ToolkitKind.MCP,
            name="mcp-invalid",
            description="missing language",
            package="some-pkg"
        )


def test_import_toolkit_infers_node_command():
    with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command.ToolkitController.import_toolkit") as mock:
        toolkit_command.import_toolkit(
            kind=ToolkitKind.MCP,
            name="mcp-node",
            description="Node pkg",
            package="@myorg/my-mcp-toolkit",
            language=Language.NODE
        )
        mock.assert_called_once()
        args, kwargs = mock.call_args
        assert kwargs["app_id"] is None
        assert kwargs["tools"] is None


def test_import_toolkit_infers_python_command():
    with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command.ToolkitController.import_toolkit") as mock:
        toolkit_command.import_toolkit(
            kind=ToolkitKind.MCP,
            name="mcp-py",
            description="Python pkg",
            package="my_python_toolkit",
            language=Language.PYTHON
        )
        mock.assert_called_once()
        args, kwargs = mock.call_args
        assert kwargs["tools"] is None
        assert kwargs["app_id"] is None
