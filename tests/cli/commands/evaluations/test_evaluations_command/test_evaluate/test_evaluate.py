"""Tests for the main evaluate command and USE_LEGACY_EVAL flag"""
from unittest.mock import patch
import importlib
import json
import tempfile
import pytest
import shutil
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


@pytest.fixture(autouse=True, scope="module")
def cleanup_test_output():
    """Setup - ensure we start with a clean state"""
    test_output_dir = Path("test_output")
    if test_output_dir.exists():
        shutil.rmtree(test_output_dir)

    yield  # Run the tests

    # Cleanup after all tests in this module
    if test_output_dir.exists():
        shutil.rmtree(test_output_dir)


class TestEvaluate:
    """Tests for the basic evaluate command"""

    def test_evaluate_with_config_file(self, config_file, user_env_file):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.evaluate"
        ) as mock_evaluate:
            evaluations_command.evaluate(
                config_file=config_file, user_env_file=user_env_file
            )
            mock_evaluate.assert_called_once_with(
                config_file=config_file,
                test_paths=None,
                output_dir=None,
                langfuse_enabled=False,
            )

    def test_evaluate_with_command_line_args(self, user_env_file):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.evaluate"
        ) as mock_evaluate:
            test_paths = "path1,path2"
            output_dir = "output_dir"
            evaluations_command.evaluate(
                test_paths=test_paths,
                output_dir=output_dir,
                user_env_file=user_env_file,
            )
            mock_evaluate.assert_called_once_with(
                config_file=None,
                test_paths=test_paths,
                output_dir=output_dir,
                langfuse_enabled=False,
            )

    def test_evaluate_with_empty_test_paths(self, user_env_file):
        with pytest.raises(SystemExit) as exc_info:
            evaluations_command.evaluate(
                test_paths="", output_dir="output_dir", user_env_file=user_env_file
            )
        assert exc_info.value.code == 1


def _reload_eval_modules():
    """Reload evaluations modules and return (evaluations_controller, eval_cmd).

    Must be called *after* setting USE_LEGACY_EVAL in the environment so the
    module-level constant picks up the new value.
    """
    from ibm_watsonx_orchestrate.cli.commands.evaluations import (
        evaluations_controller,
        evaluations_command as eval_cmd,
    )
    importlib.reload(evaluations_controller)
    importlib.reload(eval_cmd)
    return evaluations_controller, eval_cmd


class TestLegacyEvalFlag:
    """Test suite for USE_LEGACY_EVAL flag behavior"""

    def test_evaluate_with_legacy_eval_false(self, config_file, user_env_file, monkeypatch):
        """Test that evaluation works correctly when USE_LEGACY_EVAL=FALSE (beta mode)"""
        monkeypatch.setenv("USE_LEGACY_EVAL", "FALSE")
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.Config"), \
             patch("agentops.main.main"):
            evaluations_controller, eval_cmd = _reload_eval_modules()
            with patch.object(evaluations_controller.EvaluationsController, "evaluate") as mock_evaluate:
                eval_cmd.evaluate(config_file=config_file, user_env_file=user_env_file)
                mock_evaluate.assert_called_once_with(
                    config_file=config_file,
                    test_paths=None,
                    output_dir=None,
                    langfuse_enabled=False,
                )

    def test_evaluate_with_legacy_eval_true(self, config_file, user_env_file, monkeypatch):
        """Test that evaluation works correctly when USE_LEGACY_EVAL=TRUE (legacy mode)"""
        monkeypatch.setenv("USE_LEGACY_EVAL", "TRUE")
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.Config"), \
             patch("agentops.main.main"):
            evaluations_controller, eval_cmd = _reload_eval_modules()
            with patch.object(evaluations_controller.EvaluationsController, "evaluate") as mock_evaluate:
                eval_cmd.evaluate(config_file=config_file, user_env_file=user_env_file)
                mock_evaluate.assert_called_once_with(
                    config_file=config_file,
                    test_paths=None,
                    output_dir=None,
                    langfuse_enabled=False,
                )

    def test_warning_message_shown_with_beta_eval(self, config_file, user_env_file, monkeypatch, caplog):
        """Test that a deprecation warning is shown when USE_LEGACY_EVAL is set (flag is now ignored)"""
        import logging
        monkeypatch.setenv("USE_LEGACY_EVAL", "FALSE")
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.Config"), \
             patch("agentops.main.main"):
            evaluations_controller, eval_cmd = _reload_eval_modules()
            with patch.object(evaluations_controller.EvaluationsController, "evaluate"):
                with caplog.at_level(logging.WARNING):
                    eval_cmd.evaluate(config_file=config_file, user_env_file=user_env_file)
                    assert "USE_LEGACY_EVAL is deprecated" in caplog.text

    def test_warning_message_shown_with_legacy_eval(self, config_file, user_env_file, monkeypatch, caplog):
        """Test that a deprecation warning is shown when USE_LEGACY_EVAL=TRUE (flag is now ignored regardless of value)"""
        import logging
        monkeypatch.setenv("USE_LEGACY_EVAL", "TRUE")
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.Config"), \
             patch("agentops.main.main"):
            evaluations_controller, eval_cmd = _reload_eval_modules()
            with patch.object(evaluations_controller.EvaluationsController, "evaluate"):
                with caplog.at_level(logging.WARNING):
                    eval_cmd.evaluate(config_file=config_file, user_env_file=user_env_file)
                    assert "USE_LEGACY_EVAL is deprecated" in caplog.text


class TestEvaluateCommandOptions:
    """Test suite for all evaluate command options with USE_LEGACY_EVAL=FALSE"""

    @pytest.fixture
    def reloaded_modules(self, monkeypatch):
        """Reload evaluations modules with USE_LEGACY_EVAL=FALSE."""
        monkeypatch.setenv("USE_LEGACY_EVAL", "FALSE")
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.Config"), \
             patch("agentops.main.main"):
            yield _reload_eval_modules()

    @pytest.fixture
    def env_manager_file(self):
        """Create a temporary environment manager YAML file"""
        env_manager_content = """
env1:
  agent:
    file: path_to_agents_def.py
  tools:
    file: path_to_tools_def.py
    kind: python
  test_config: dummy_path_config
  clean_up: false
"""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".yaml", delete=False
        ) as tmp:
            tmp.write(env_manager_content)
            tmp.flush()
            yaml_path = tmp.name
            yield yaml_path
            Path(yaml_path).unlink()

    def test_evaluate_with_config_option(self, config_file, user_env_file, reloaded_modules):
        """Test evaluate command with --config/-c option and USE_LEGACY_EVAL=FALSE"""
        evaluations_controller, eval_cmd = reloaded_modules
        with patch.object(evaluations_controller.EvaluationsController, "evaluate") as mock_evaluate:
            eval_cmd.evaluate(config_file=config_file, user_env_file=user_env_file)
            mock_evaluate.assert_called_once_with(
                config_file=config_file,
                test_paths=None,
                output_dir=None,
                langfuse_enabled=False,
            )

    def test_evaluate_with_test_paths_option(self, user_env_file, reloaded_modules):
        """Test evaluate command with --test-paths/-p option and USE_LEGACY_EVAL=FALSE"""
        evaluations_controller, eval_cmd = reloaded_modules
        with patch.object(evaluations_controller.EvaluationsController, "evaluate") as mock_evaluate:
            test_paths = "path1,path2"
            output_dir = "test_output"
            eval_cmd.evaluate(test_paths=test_paths, output_dir=output_dir, user_env_file=user_env_file)
            mock_evaluate.assert_called_once_with(
                config_file=None,
                test_paths=test_paths,
                output_dir=output_dir,
                langfuse_enabled=False,
            )

    def test_evaluate_with_output_dir_option(self, user_env_file, reloaded_modules):
        """Test evaluate command with --output-dir/-o option and USE_LEGACY_EVAL=FALSE"""
        evaluations_controller, eval_cmd = reloaded_modules
        with patch.object(evaluations_controller.EvaluationsController, "evaluate") as mock_evaluate:
            test_paths = "test/path"
            output_dir = "custom_output_dir"
            eval_cmd.evaluate(test_paths=test_paths, output_dir=output_dir, user_env_file=user_env_file)
            mock_evaluate.assert_called_once_with(
                config_file=None,
                test_paths=test_paths,
                output_dir=output_dir,
                langfuse_enabled=False,
            )

    def test_evaluate_with_env_file_option(self, reloaded_modules):
        """Test evaluate command with --env-file/-e option and USE_LEGACY_EVAL=FALSE"""
        evaluations_controller, eval_cmd = reloaded_modules
        env_content = "WATSONX_SPACE_ID=custom_id\nWATSONX_APIKEY=custom_key"
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".env", delete=False) as tmp:
            tmp.write(env_content)
            tmp.flush()
            custom_env_path = tmp.name
        try:
            with patch.object(evaluations_controller.EvaluationsController, "evaluate") as mock_evaluate:
                test_paths = "test/path"
                output_dir = "test_output"
                eval_cmd.evaluate(test_paths=test_paths, output_dir=output_dir, user_env_file=custom_env_path)
                mock_evaluate.assert_called_once_with(
                    config_file=None,
                    test_paths=test_paths,
                    output_dir=output_dir,
                    langfuse_enabled=False,
                )
        finally:
            Path(custom_env_path).unlink()

    def test_evaluate_with_env_manager_path_option(self, env_manager_file, user_env_file, reloaded_modules):
        """Test evaluate command with --env-manager-path option and USE_LEGACY_EVAL=FALSE"""
        evaluations_controller, eval_cmd = reloaded_modules
        from ibm_watsonx_orchestrate.cli.commands.evaluations import evaluations_environment_manager
        importlib.reload(evaluations_environment_manager)
        importlib.reload(eval_cmd)

        with patch.object(eval_cmd, "run_environment_manager") as mock_env_manager:
            output_dir = "test_output"
            eval_cmd.evaluate(env_manager_path=env_manager_file, output_dir=output_dir, user_env_file=user_env_file)
            mock_env_manager.assert_called_once_with(
                environment_manager_path=env_manager_file,
                output_dir=output_dir,
            )

    def test_evaluate_with_langfuse_option(self, user_env_file, monkeypatch, reloaded_modules):
        """Test evaluate command with --with-langfuse/-l option and USE_LEGACY_EVAL=FALSE"""
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test_secret")
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test_public")
        monkeypatch.setenv("LANGFUSE_BASE_URL", "http://localhost:3000")
        evaluations_controller, eval_cmd = reloaded_modules
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            with patch.object(evaluations_controller.EvaluationsController, "evaluate") as mock_evaluate:
                test_paths = "test/path"
                output_dir = "test_output"
                eval_cmd.evaluate(test_paths=test_paths, output_dir=output_dir, user_env_file=user_env_file, langfuse_enabled=True)
                mock_evaluate.assert_called_once_with(
                    config_file=None,
                    test_paths=test_paths,
                    output_dir=output_dir,
                    langfuse_enabled=True,
                )

    def test_evaluate_all_options_combined(self, config_file, user_env_file, monkeypatch, reloaded_modules):
        """Test evaluate command with multiple options combined and USE_LEGACY_EVAL=FALSE"""
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test_secret")
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test_public")
        monkeypatch.setenv("LANGFUSE_BASE_URL", "http://localhost:3000")
        evaluations_controller, eval_cmd = reloaded_modules
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            with patch.object(evaluations_controller.EvaluationsController, "evaluate") as mock_evaluate:
                eval_cmd.evaluate(config_file=config_file, user_env_file=user_env_file, langfuse_enabled=True)
                mock_evaluate.assert_called_once_with(
                    config_file=config_file,
                    test_paths=None,
                    output_dir=None,
                    langfuse_enabled=True,
                )

