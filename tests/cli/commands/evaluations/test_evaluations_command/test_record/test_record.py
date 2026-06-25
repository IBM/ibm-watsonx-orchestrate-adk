"""Tests for the record command"""
from unittest.mock import patch, MagicMock
import pytest

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
                mock_controller.record.assert_called_once_with(output_dir=output_dir)

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

# Made with Bob
