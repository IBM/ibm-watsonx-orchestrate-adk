from copy import deepcopy
from unittest.mock import patch, MagicMock, call
from ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller import ToolkitController, ToolkitKind
import pytest
import tempfile
import os

from ibm_watsonx_orchestrate.cli.config import DEFAULT_CONFIG_FILE_CONTENT
from utils.matcher import MatchesStringContaining


def test_remove_toolkit_success():
    mock_client = MagicMock()
    mock_client.get_draft_by_name.return_value = [{"id": "123"}]

    with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.instantiate_client", return_value=mock_client), \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.is_local_dev", return_value=True):
        controller = ToolkitController()
        controller.remove_toolkit("test_toolkit")

        mock_client.delete.assert_called_once_with(toolkit_id="123")


def test_remove_toolkit_multiple_results():
    mock_client = MagicMock()
    mock_client.get_draft_by_name.return_value = [{"id": "123"}, {"id": "456"}]

    with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.instantiate_client", return_value=mock_client), \
         patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.is_local_dev", return_value=True), \
         patch("sys.exit") as mock_exit:
        controller = ToolkitController()
        controller.remove_toolkit("duplicate_toolkit")
        mock_exit.assert_called_once_with(1)


def test_remove_toolkit_not_found():
    mock_client = MagicMock()
    mock_client.get_draft_by_name.return_value = []

    with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.instantiate_client", return_value=mock_client), \
         patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.is_local_dev", return_value=True):
        controller = ToolkitController()
        controller.remove_toolkit("missing_toolkit")
        mock_client.delete.assert_not_called()


def test_remap_connections_single_id():
    with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.get_connection_id", return_value="conn-123"), \
         patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.is_local_dev", return_value=True):
        controller = ToolkitController()
        result = controller._remap_connections(["my_id"])
        assert result == {"my_id": "conn-123"}


def test_remap_connections_key_value_pair():
    with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.get_connection_id", return_value="conn-456"), \
         patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.is_local_dev", return_value=True):
        controller = ToolkitController()
        result = controller._remap_connections(["runtime=local"])
        assert result == {"runtime": "conn-456"}


def test_remap_connections_invalid_equal_signs():
    controller = ToolkitController()
    with pytest.raises(Exception):
        controller._remap_connections(["too=many=equals"])


def test_import_toolkit_exits_if_toolkit_exists():
    mock_client = MagicMock()
    mock_client.get_draft_by_name.return_value = [{"id": "already-there"}]

    with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.instantiate_client", return_value=mock_client), \
         patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.is_local_dev", return_value=True), \
         patch("sys.exit", side_effect=SystemExit) as mock_exit:
        controller = ToolkitController(
            kind=ToolkitKind.MCP,
            name="test",
            description="test desc",
            package_root="/tmp",
            command="node dist/index.js --stdio"
        )
        with pytest.raises(SystemExit):
            controller.import_toolkit()
        mock_exit.assert_called_once_with(1)


def test_import_toolkit_successful_path():
    mock_client = MagicMock()
    mock_client.get_draft_by_name.return_value = []
    mock_client.create_toolkit.return_value = {"id": "new-toolkit"}
    mock_client._create_zip.return_value = None

    with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.instantiate_client", return_value=mock_client), \
         patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController._populate_zip", return_value="dummy.zip"), \
         patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.is_local_dev", return_value=True), \
         patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.get_connection_id", return_value="conn-id"):

        controller = ToolkitController(
            kind=ToolkitKind.MCP,
            name="toolkit-name",
            description="desc",
            package_root="/tmp",
            command='["node", "dist/index.js", "--stdio"]'
        )
        controller.import_toolkit(tools=["tool1", "tool2"], app_id=["app1"])

        mock_client.create_toolkit.assert_called_once()
        mock_client.upload.assert_called_once_with(
            toolkit_id="new-toolkit",
            zip_file_path=MatchesStringContaining(".zip")
        )

