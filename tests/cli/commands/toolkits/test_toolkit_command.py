from ibm_watsonx_orchestrate.cli.commands.toolkit import toolkit_command
from ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller import ToolkitKind
from unittest.mock import patch

class TestImportToolkit:
    def test_import_toolkit(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command.ToolkitController.import_toolkit") as mock_create_toolkit, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command.ToolkitController.publish_or_update_toolkits") as mock_publish_or_update_toolits:
            toolkit_command.import_toolkit(
                file="test_file.yaml",
                app_id=["test_app_id"]
            )
            mock_create_toolkit.assert_called_once_with(
                file="test_file.yaml",
                app_id=["test_app_id"]
            )
            mock_publish_or_update_toolits.assert_called_once()

class TestAddToolkit:
    def test_add_toolkit(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command.ToolkitController.create_toolkit") as mock_create_toolkit, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command.ToolkitController.publish_or_update_toolkits") as mock_publish_or_update_toolits:
            toolkit_command.add_toolkit(
                kind=ToolkitKind.MCP,
                name="mcp-eric101",
                description="test description",
                package_root="/some/path",
                command="node dist/index.js --transport stdio"
            )
            mock_create_toolkit.assert_called_once_with(
                kind=ToolkitKind.MCP,
                name="mcp-eric101",
                description="test description",
                package=None,
                package_root="/some/path",
                language=None,
                command="node dist/index.js --transport stdio",
                url=None,
                transport=None,
                tools=None,
                app_id=None
            )
            mock_publish_or_update_toolits.assert_called_once()

class TestRemoveToolkit:
    def test_remove_toolkit(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command.ToolkitController.remove_toolkit") as mock:
            toolkit_command.remove_toolkit(name="mcp-eric101")
            mock.assert_called_once_with(name="mcp-eric101")

class TestListToolkits:
    def test_list_toolkits_verbose(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command.ToolkitController.list_toolkits") as mock:
            toolkit_command.list_toolkits(verbose=True)
            mock.assert_called_once_with(verbose=True)


    def test_list_toolkits_non_verbose(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command.ToolkitController.list_toolkits") as mock:
            toolkit_command.list_toolkits()
            mock.assert_called_once_with(verbose=False)
