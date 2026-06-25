"""Tests for the red-teaming commands"""
from unittest.mock import patch, MagicMock
import pytest

try:
    from ibm_watsonx_orchestrate.cli.commands.evaluations import evaluations_command
except ImportError as e:
    import traceback

    traceback.print_exc()
    pytest.skip(f"Missing required dependencies: {e}", allow_module_level=True)


class TestRedTeaming:
    """Tests for red-teaming commands"""

    def test_list_plans_calls_controller(self):
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
                evaluations_command.list_plans()
                mock_controller.list_red_teaming_attacks.assert_called_once()

    def test_plan_calls_generate_red_teaming_attacks(self, user_env_file):
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
                evaluations_command.plan(
                    attacks_list="attack1,attack2",
                    datasets_path="datasets",
                    agents_list_or_path="agents",
                    target_agent_name="target_agent",
                    output_dir="test_output",
                    user_env_file=user_env_file,
                    max_variants=5,
                )

                mock_controller.generate_red_teaming_attacks.assert_called_once_with(
                    attacks_list="attack1,attack2",
                    datasets_path="datasets",
                    agents_list_or_path="agents",
                    target_agent_name="target_agent",
                    output_dir="test_output",
                    max_variants=5,
                )

    def test_run_calls_run_red_teaming_attacks(self, user_env_file):
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
                evaluations_command.run(
                    attack_paths="attacks",
                    output_dir="test_output",
                    user_env_file=user_env_file,
                )

                mock_controller.run_red_teaming_attacks.assert_called_once_with(
                    attack_paths="attacks", output_dir="test_output"
                )

# Made with Bob
