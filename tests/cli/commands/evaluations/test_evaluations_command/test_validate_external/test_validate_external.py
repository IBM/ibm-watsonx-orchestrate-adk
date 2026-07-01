"""Tests for the validate-external command"""
from unittest.mock import patch, MagicMock
import json
import tempfile
import pytest
from pathlib import Path

try:
    from ibm_watsonx_orchestrate.cli.commands.evaluations import evaluations_command
except ImportError as e:
    import traceback

    traceback.print_exc()
    pytest.skip(f"Missing required dependencies: {e}", allow_module_level=True)


class TestValidateExternal:
    """Tests for the validate-external command"""

    @pytest.fixture
    def csv_file(self):
        csv_content = "test input 1\ntest input 2"
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".csv", delete=False
        ) as csv_tmp:
            csv_tmp.write(csv_content)
            csv_tmp.flush()
            csv_path = csv_tmp.name
            yield csv_path
            Path(csv_path).unlink()

    def test_validate_external_success(
        self, external_agent_config, csv_file, user_env_file
    ):
        mock_controller = MagicMock()
        mock_controller.external_validate.return_value = [
            {"success": "True", "logged_events": [], "messages": []}
        ]
        
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command._import_error",
            False
        ):
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command.EvaluationsController",
                return_value=mock_controller,
                create=True
            ):
                evaluations_command.validate_external(
                    data_path=csv_file,
                    external_agent_config=external_agent_config,
                    credential="test-cred",
                    output_dir="test_output",
                    user_env_file=user_env_file,
                )
                mock_controller.external_validate.assert_called()

    def test_validate_external_with_empty_csv(
        self, external_agent_config, user_env_file
    ):
        # Since empty CSV is handled gracefully by the code, we'll verify the behavior
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".csv", delete=False
        ) as csv_tmp:
            csv_tmp.write("")
            csv_tmp.flush()
            csv_path = csv_tmp.name
            try:
                mock_controller = MagicMock()
                mock_controller.external_validate.return_value = [{"success": "True"}]
                
                with patch(
                    "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command._import_error",
                    False
                ):
                    with patch(
                        "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command.EvaluationsController",
                        return_value=mock_controller,
                        create=True
                    ):
                        evaluations_command.validate_external(
                            data_path=csv_path,
                            external_agent_config=external_agent_config,
                            credential="test-cred",
                            output_dir="test_output",
                            user_env_file=user_env_file,
                        )
                        # Verify that it was called with an empty list
                        # Called twice because of single and block validation
                        assert mock_controller.external_validate.call_count == 2
                        mock_controller.external_validate.assert_any_call(
                            json.loads(Path(external_agent_config).read_text()),
                            [],
                            "test-cred",
                            add_context=True,
                        )
                        mock_controller.external_validate.assert_any_call(
                            json.loads(Path(external_agent_config).read_text()),
                            [],
                            "test-cred",
                        )
            finally:
                Path(csv_path).unlink()

