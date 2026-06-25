"""Tests for the generate command"""
from unittest.mock import patch, MagicMock
import pytest

try:
    from ibm_watsonx_orchestrate.cli.commands.evaluations import evaluations_command
except ImportError as e:
    import traceback

    traceback.print_exc()
    pytest.skip(f"Missing required dependencies: {e}", allow_module_level=True)


class TestGenerate:
    """Tests for the generate command"""

    @pytest.fixture
    def generate_paths(self):
        return {
            "stories_path": "test_stories.csv",
            "tools_path": "test_tools",
            "output_dir": "test_output",
        }

    def test_generate_success(self, generate_paths, user_env_file):
        mock_controller = MagicMock()
        mock_controller.generate.return_value = {"status": "success"}
        
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command._import_error",
            False
        ):
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command.EvaluationsController",
                return_value=mock_controller,
                create=True
            ):
                evaluations_command.generate(**generate_paths, user_env_file=user_env_file)
                mock_controller.generate.assert_called_once_with(**generate_paths)

    def test_generate_with_empty_stories(self, generate_paths, user_env_file):
        mock_controller = MagicMock()
        
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command._import_error",
            False
        ):
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command.EvaluationsController",
                return_value=mock_controller,
                create=True
            ):
                paths = generate_paths.copy()
                paths["stories_path"] = ""
                evaluations_command.generate(**paths, user_env_file=user_env_file)
                mock_controller.generate.assert_called_once_with(**paths)

# Made with Bob
