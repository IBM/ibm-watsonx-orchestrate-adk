"""Tests for the analyze command"""
from unittest.mock import patch, MagicMock
import pytest

try:
    from ibm_watsonx_orchestrate.cli.commands.evaluations import evaluations_command
except ImportError as e:
    import traceback

    traceback.print_exc()
    pytest.skip(f"Missing required dependencies: {e}", allow_module_level=True)


class TestAnalyze:
    """Tests for the analyze command"""

    def test_analyze_success(self, user_env_file):
        mock_controller = MagicMock()
        mock_controller.analyze.return_value = {"metrics": {"accuracy": 0.95}}
        
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command._import_error",
            False
        ):
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command.EvaluationsController",
                return_value=mock_controller,
                create=True
            ):
                data_path = "test_data"
                evaluations_command.analyze(
                    data_path=data_path, user_env_file=user_env_file
                )
                mock_controller.analyze.assert_called_once_with(
                    data_path=data_path, tool_definition_path=None, mode="default"
                )

    def test_analyze_with_empty_data_path(self, user_env_file):
        mock_controller = MagicMock()
        mock_controller.analyze.side_effect = ValueError("Empty data path")
        
        with pytest.raises(ValueError):
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command._import_error",
                False
            ):
                with patch(
                    "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command.EvaluationsController",
                    return_value=mock_controller,
                    create=True
                ):
                    evaluations_command.analyze(data_path="", user_env_file=user_env_file)

    def test_analyze_with_invalid_mode(self, user_env_file):
        with pytest.raises(SystemExit):
            evaluations_command.analyze(
                data_path="", user_env_file=user_env_file, mode="wrong_mode"
            )




    def test_analyze_with_evaluation_results_dir(self, evaluation_results_dir, user_env_file):
        """Test analyze command with evaluation results directory structure"""
        mock_controller = MagicMock()
        mock_controller.analyze.return_value = {"metrics": {"accuracy": 0.95, "precision": 0.92}}
        
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command._import_error",
            False
        ):
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command.EvaluationsController",
                return_value=mock_controller,
                create=True
            ):
                evaluations_command.analyze(
                    data_path=evaluation_results_dir,
                    user_env_file=user_env_file
                )
                
                # Verify the controller was called with the correct folder path
                mock_controller.analyze.assert_called_once_with(
                    data_path=evaluation_results_dir,
                    tool_definition_path=None,
                    mode="default"
                )
