"""Tests for the record command"""
from unittest.mock import patch, MagicMock
import json
import pytest
import typer

try:
    from ibm_watsonx_orchestrate.cli.commands.evaluations import evaluations_command
except ImportError as e:
    import traceback

    traceback.print_exc()
    pytest.skip(f"Missing required dependencies: {e}", allow_module_level=True)


class TestRecord:
    """Tests for the record command"""

    @pytest.fixture
    def output_dir(self):
        return "test_output"

    def test_record_success(self, output_dir, user_env_file):
        mock_controller = MagicMock()
        mock_controller.record.return_value = {"status": "success"}
        
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command._import_error",
            False
        ):
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command.EvaluationsController",
                return_value=mock_controller,
                create=True
            ):
                evaluations_command.record(
                    output_dir=output_dir, user_env_file=user_env_file
                )
                mock_controller.record.assert_called_once_with(
                    output_dir=output_dir, context_variables=None
                )

    def test_record_with_nonexistent_dir(self, user_env_file):
        mock_controller = MagicMock()
        mock_controller.record.side_effect = NotADirectoryError("Directory not found")
        
        with pytest.raises(NotADirectoryError):
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command._import_error",
                False
            ):
                with patch(
                    "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command.EvaluationsController",
                    return_value=mock_controller,
                    create=True
                ):
                    evaluations_command.record(
                        output_dir="nonexistent_dir", user_env_file=user_env_file
                    )

    def test_record_with_context_variables(self, output_dir, user_env_file):
        mock_controller = MagicMock()
        mock_controller.record.return_value = {"status": "success"}
        context_variables = json.dumps({"key": "value"})

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command._import_error",
            False
        ):
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command.EvaluationsController",
                return_value=mock_controller,
                create=True
            ):
                evaluations_command.record(
                    output_dir=output_dir,
                    user_env_file=user_env_file,
                    context_variables=context_variables,
                )
                mock_controller.record.assert_called_once_with(
                    output_dir=output_dir, context_variables=context_variables
                )

    def test_record_with_invalid_json_context_variables(self, output_dir, user_env_file):
        mock_controller = MagicMock()

        with pytest.raises(typer.BadParameter):
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command._import_error",
                False
            ):
                with patch(
                    "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command.EvaluationsController",
                    return_value=mock_controller,
                    create=True
                ):
                    evaluations_command.record(
                        output_dir=output_dir,
                        user_env_file=user_env_file,
                        context_variables="not valid json{",
                    )

    def test_record_with_non_dict_context_variables(self, output_dir, user_env_file):
        mock_controller = MagicMock()

        with pytest.raises(typer.BadParameter):
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command._import_error",
                False
            ):
                with patch(
                    "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command.EvaluationsController",
                    return_value=mock_controller,
                    create=True
                ):
                    evaluations_command.record(
                        output_dir=output_dir,
                        user_env_file=user_env_file,
                        context_variables='["not", "a", "dict"]',
                    )

    def test_record_without_context_variables(self, output_dir, user_env_file):
        mock_controller = MagicMock()
        mock_controller.record.return_value = {"status": "success"}

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command._import_error",
            False
        ):
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command.EvaluationsController",
                return_value=mock_controller,
                create=True
            ):
                evaluations_command.record(
                    output_dir=output_dir,
                    user_env_file=user_env_file,
                    context_variables=None,
                )
                mock_controller.record.assert_called_once_with(
                    output_dir=output_dir, context_variables=None
                )

# Made with Bob
