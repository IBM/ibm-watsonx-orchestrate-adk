from unittest.mock import patch
import json
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

@pytest.fixture
def external_agent_config():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
        ext_agent_config = {
            "spec_version": "v1",
            "kind": "external",
            "name": "news_agent",
            "title": "News Agent",
            "nickname": "news_agent",
            "provider": "external_chat",
            "description": "An agent built in langchain which searches the news.\n",
            "tags": [
                "test"
            ],
            "api_url": "https://someurl.com",
            "auth_scheme": "BEARER_TOKEN",
            "version": "1.0.1",
            "publisher": "11x",
            "language_support": ["English"],
            "icon": "<svg>",
            
        }
        json.dump(ext_agent_config, tmp)
        tmp.flush()
        config_path = tmp.name
        yield config_path
        Path(config_path).unlink()

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
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
            json.dump(valid_config, tmp)
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
            mock_analyze.assert_called_once_with(data_path=data_path, tool_definition_path=None)

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
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
            json.dump(config_content, tmp)
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

    def test_validate_external_success(self, config_content, external_agent_config, csv_file, user_env_file):
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.external_validate") as mock_validate:
            mock_validate.return_value = [{"success": "True", "logged_events": [], "messages": []}]
            evaluations_command.validate_external(
                data_path=csv_file,
                external_agent_config=external_agent_config,
                credential="test-cred",
                output_dir="test_output",
                user_env_file=user_env_file
            )
            mock_validate.assert_called()

    def test_validate_external_with_empty_csv(self, external_agent_config, user_env_file):
        # Since empty CSV is handled gracefully by the code, we'll verify the behavior
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False) as csv_tmp:
            csv_tmp.write("")
            csv_tmp.flush()
            csv_path = csv_tmp.name
            try:
                with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.external_validate") as mock_validate:
                    mock_validate.return_value = [{"success": "True"}]
                    evaluations_command.validate_external(
                        data_path=csv_path,
                        external_agent_config=external_agent_config,
                        credential="test-cred",
                        output_dir="test_output",
                        user_env_file=user_env_file
                    )
                    # Verify that it was called with an empty list
                    # Called twice because of single and block validation
                    assert mock_validate.call_count == 2
                    print(mock_validate.mock_calls)
                    mock_validate.assert_any_call(
                        json.loads(
                            Path(external_agent_config).read_text()
                        ),
                            [],
                            "test-cred",
                            add_context=True
                        )
                    mock_validate.assert_any_call(
                        json.loads(Path(external_agent_config).read_text()),
                        [],
                        "test-cred"
                    )
            finally:
                Path(csv_path).unlink()


class TestRedTeaming:
    def test_list_plans_calls_controller(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.list_red_teaming_attacks") as mock_list:
            evaluations_command.list_plans()
            mock_list.assert_called_once()

    def test_plan_calls_generate_red_teaming_attacks(self, user_env_file):
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.generate_red_teaming_attacks") as mock_generate:
            evaluations_command.plan(
                attacks_list="attack1,attack2",
                datasets_path="datasets",
                agents_path="agents",
                target_agent_name="target_agent",
                output_dir="test_output",
                user_env_file=user_env_file,
                max_variants=5,
            )

            mock_generate.assert_called_once_with(
                attacks_list="attack1,attack2",
                datasets_path="datasets",
                agents_path="agents",
                target_agent_name="target_agent",
                output_dir="test_output",
                max_variants=5,
            )

    def test_run_calls_run_red_teaming_attacks(self, user_env_file):
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.run_red_teaming_attacks") as mock_run:
            evaluations_command.run(
                attack_paths="attacks",
                output_dir="test_output",
                user_env_file=user_env_file,
            )

            mock_run.assert_called_once_with(attack_paths="attacks", output_dir="test_output")
