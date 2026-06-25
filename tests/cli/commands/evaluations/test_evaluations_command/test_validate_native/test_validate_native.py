"""Tests for the validate-native command"""
from unittest.mock import patch, MagicMock
import tempfile
import pytest
from pathlib import Path

try:
    from ibm_watsonx_orchestrate.cli.commands.evaluations import evaluations_command
except ImportError as e:
    import traceback

    traceback.print_exc()
    pytest.skip(f"Missing required dependencies: {e}", allow_module_level=True)


class TestValidateNativeAgent:
    """Tests for the validate-native command"""

    @pytest.fixture
    def tsv_file(self):
        csv_content = "user story 1\texpected response 1\tagent1"
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".csv", delete=False
        ) as csv_tmp:
            csv_tmp.write(csv_content)
            csv_tmp.flush()
            csv_path = csv_tmp.name
            yield csv_path
            Path(csv_path).unlink()

    def test_validate_native_agent(self, tsv_file, user_env_file):
        # Mock the EvaluationsController class before it's instantiated
        mock_controller = MagicMock()
        mock_controller.generate_performance_test.return_value = [{"test": "data"}]
        
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command._import_error",
            False
        ):
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command.EvaluationsController",
                return_value=mock_controller,
                create=True
            ):
                with patch(
                    "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command.evaluate"
                ) as mock_evaluate:
                    evaluations_command.validate_native(
                        data_path=tsv_file,
                        output_dir="test_output",
                        user_env_file=user_env_file,
                    )

                mock_controller.generate_performance_test.assert_called()
                mock_evaluate.assert_called_once_with(
                    output_dir="test_output/native_agent_evaluations",
                    test_paths=str(
                        "test_output/native_agent_evaluations/generated_test_data"
                    ),
                )

# Made with Bob
