"""Tests for the quick-eval command"""
from unittest.mock import patch
import tempfile
import pytest
from pathlib import Path

try:
    from ibm_watsonx_orchestrate.cli.commands.evaluations import evaluations_command
    from ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller import (
        EvaluateMode,
    )
except ImportError as e:
    import traceback

    traceback.print_exc()
    pytest.skip(f"Missing required dependencies: {e}", allow_module_level=True)


class TestQuickEval:
    """Tests for the quick-eval command"""

    @pytest.fixture
    def tools_path(self):
        tools_dir = tempfile.mkdtemp()
        tools_file = Path(tools_dir) / "test_tool.py"
        tools_file.write_text(
            """
            def tool1():
                '''A test tool'''
                pass

            def tool2():
                '''Another test tool'''
                pass
            """
        )

        return str(tools_file)

    def test_quick_eval_with_config_file(self, config_file, user_env_file, tools_path):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.evaluate"
        ) as mock_evaluate:
            evaluations_command.quick_eval(
                config_file=config_file,
                user_env_file=user_env_file,
                tools_path=tools_path,
            )
            mock_evaluate.assert_called_once_with(
                config_file=config_file,
                test_paths=None,
                output_dir=None,
                tools_path=tools_path,
                mode=EvaluateMode.referenceless,
            )

    def test_quick_eval_with_command_line_args(self, user_env_file, tools_path):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.evaluate"
        ) as mock_evaluate:
            test_paths = "path1,path2"
            output_dir = "output_dir"
            evaluations_command.quick_eval(
                test_paths=test_paths,
                output_dir=output_dir,
                user_env_file=user_env_file,
                tools_path=tools_path,
            )
            mock_evaluate.assert_called_once_with(
                config_file=None,
                test_paths=test_paths,
                output_dir=output_dir,
                tools_path=tools_path,
                mode=EvaluateMode.referenceless,
            )

