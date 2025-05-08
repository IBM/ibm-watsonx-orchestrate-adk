from ibm_watsonx_orchestrate.cli.commands.toolkit import toolkit_command
from ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller import ToolkitKind
from unittest.mock import patch


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
