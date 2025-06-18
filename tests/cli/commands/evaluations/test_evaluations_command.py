from unittest.mock import patch
import yaml
import tempfile
import pytest
import shutil
from pathlib import Path
from ibm_watsonx_orchestrate.cli.commands.evaluations import evaluations_command

@pytest.fixture(autouse=True, scope="module")
def user_env_file():
    env_content = """WATSONX_SPACE_ID=id
WATSONX_APIKEY=key"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".env", delete=False) as tmp:
        tmp.write(env_content)
        tmp.flush()
        env_path = tmp.name
        yield env_path
        Path(env_path).unlink()

@pytest.fixture(autouse=True, scope="module")
def cleanup_test_output():
    # Setup - ensure we start with a clean state
    test_output_dir = Path("test_output")
    if test_output_dir.exists():
        shutil.rmtree(test_output_dir)
    
    yield  # Run the tests
    
    # Cleanup after all tests in this module
    if test_output_dir.exists():
        shutil.rmtree(test_output_dir)

class TestEvaluate:
    @pytest.fixture
    def valid_config(self):
        return {
            "test_paths": ["test/path1", "test/path2"],
            "output_dir": "test_output",
            "auth_config": {
                "url": "test-url",
                "tenant_name": "test-tenant",
                "token": "test-token"
            }
        }

    @pytest.fixture
    def config_file(self, valid_config):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as tmp:
            yaml.dump(valid_config, tmp)
            tmp.flush()
            config_path = tmp.name
            yield config_path
            Path(config_path).unlink()

    def test_evaluate_with_config_file(self, config_file, user_env_file):
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.evaluate") as mock_evaluate:
            evaluations_command.evaluate(config_file=config_file, user_env_file=user_env_file)
            mock_evaluate.assert_called_once_with(
                config_file=config_file,
                test_paths=None,
                output_dir=None
            )

    def test_evaluate_with_command_line_args(self, user_env_file):
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.evaluate") as mock_evaluate:
            test_paths = "path1,path2"
            output_dir = "output_dir"
            evaluations_command.evaluate(test_paths=test_paths, output_dir=output_dir, user_env_file=user_env_file)
            mock_evaluate.assert_called_once_with(
                config_file=None,
                test_paths=test_paths,
                output_dir=output_dir
            )

    def test_evaluate_with_empty_test_paths(self, user_env_file):
        with pytest.raises(SystemExit) as exc_info:
            evaluations_command.evaluate(test_paths="", output_dir="output_dir", user_env_file=user_env_file)
        assert exc_info.value.code == 1

class TestRecord:
    @pytest.fixture
    def output_dir(self):
        return "test_output"

    def test_record_success(self, output_dir, user_env_file):
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.record") as mock_record:
            mock_record.return_value = {"status": "success"}
            evaluations_command.record(output_dir=output_dir, user_env_file=user_env_file)
            mock_record.assert_called_once_with(output_dir=output_dir)

    def test_record_with_nonexistent_dir(self, user_env_file):
        with pytest.raises(NotADirectoryError):
            with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.record") as mock_record:
                mock_record.side_effect = NotADirectoryError("Directory not found")
                evaluations_command.record(output_dir="nonexistent_dir", user_env_file=user_env_file)

class TestGenerate:
    @pytest.fixture
    def generate_paths(self):
        return {
            "stories_path": "test_stories.csv",
            "tools_path": "test_tools",
            "output_dir": "test_output"
        }

    def test_generate_success(self, generate_paths, user_env_file):
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.generate") as mock_generate:
            mock_generate.return_value = {"status": "success"}
            evaluations_command.generate(**generate_paths, user_env_file=user_env_file)
            mock_generate.assert_called_once_with(**generate_paths)

    def test_generate_with_empty_stories(self, generate_paths, user_env_file):
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.generate") as mock_generate:
            paths = generate_paths.copy()
            paths["stories_path"] = ""
            evaluations_command.generate(**paths, user_env_file=user_env_file)
            mock_generate.assert_called_once_with(**paths)

class TestAnalyze:
    def test_analyze_success(self, user_env_file):
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.analyze") as mock_analyze:
            mock_analyze.return_value = {"metrics": {"accuracy": 0.95}}
            data_path = "test_data"
            evaluations_command.analyze(data_path=data_path, user_env_file=user_env_file)
            mock_analyze.assert_called_once_with(data_path=data_path)

    def test_analyze_with_empty_data_path(self, user_env_file):
        with pytest.raises(ValueError):
            with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.analyze") as mock_analyze:
                mock_analyze.side_effect = ValueError("Empty data path")
                evaluations_command.analyze(data_path="", user_env_file=user_env_file)

class TestValidateExternal:
    @pytest.fixture
    def config_content(self):
        return {
            "auth_scheme": "api_key",
            "api_url": "test-url"
        }

    @pytest.fixture
    def config_file(self, config_content):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as tmp:
            yaml.dump(config_content, tmp)
            tmp.flush()
            config_path = tmp.name
            yield config_path
            Path(config_path).unlink()

    @pytest.fixture
    def csv_file(self):
        csv_content = "test input 1\ntest input 2"
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False) as csv_tmp:
            csv_tmp.write(csv_content)
            csv_tmp.flush()
            csv_path = csv_tmp.name
            yield csv_path
            Path(csv_path).unlink()

    def test_validate_external_success(self, config_content, config_file, csv_file, user_env_file):
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.external_validate") as mock_validate:
            mock_validate.return_value = {"test": "result"}
            evaluations_command.validate_external(
                data_path=csv_file,
                config=config_file,
                credential="test-cred",
                output_dir="test_output",
                user_env_file=user_env_file
            )
            mock_validate.assert_called_once_with(
                config_content,
                ["test input 1", "test input 2"],
                "test-cred"
            )

    def test_validate_external_with_invalid_config(self, csv_file, user_env_file):
        with pytest.raises(yaml.YAMLError):
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as tmp:
                tmp.write("invalid: yaml: content:")
                tmp.flush()
                config_path = tmp.name
                try:
                    evaluations_command.validate_external(
                        data_path=csv_file,
                        config=config_path,
                        credential="test-cred",
                        user_env_file=user_env_file
                    )
                finally:
                    Path(config_path).unlink()

    def test_validate_external_with_empty_csv(self, config_file, user_env_file):
        # Since empty CSV is handled gracefully by the code, we'll verify the behavior
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False) as csv_tmp:
            csv_tmp.write("")
            csv_tmp.flush()
            csv_path = csv_tmp.name
            try:
                with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.external_validate") as mock_validate:
                    mock_validate.return_value = {"test": "result"}
                    evaluations_command.validate_external(
                        data_path=csv_path,
                        config=config_file,
                        credential="test-cred",
                        output_dir="test_output",
                        user_env_file=user_env_file
                    )
                    # Verify that it was called with an empty list
                    mock_validate.assert_called_once_with(
                        yaml.safe_load(Path(config_file).read_text()),
                        [],
                        "test-cred"
                    )
            finally:
                Path(csv_path).unlink()
