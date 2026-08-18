import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import yaml
import csv
import shutil
import json

try:
    from ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller import (
        EvaluationsController,
        EvaluateMode,
    )
    from ibm_watsonx_orchestrate.cli.config import AUTH_MCSP_TOKEN_OPT

    # Suppresses fuzzywuzzy warning coming from eval
    from warnings import filterwarnings

    filterwarnings("ignore", category=UserWarning, module=r"fuzzywuzzy\.fuzz")

    from agentops.arg_configs import (
        TestConfig,
        AttackGeneratorConfig,
        AttackConfig,
        QuickEvalConfig,
    )
except ImportError as e:
    import traceback

    traceback.print_exc()
    pytest.skip(f"Missing required dependencies: {e}", allow_module_level=True)


@pytest.fixture(autouse=True, scope="module")
def mock_config_for_all_tests():
    """Mock Config class to prevent API key prompts during controller instantiation"""
    with patch(
        "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.Config"
    ) as mock_config:
        mock_config.return_value = MagicMock()
        yield mock_config


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


class MockConfig:
    def __init__(self, a=None, b=None):
        pass

    def get_active_env_config(self, a=None):
        return "test-url"

    def get_active_env(self):
        return "test-tenant"

    def get(self, a=None):
        return {"test-tenant": {AUTH_MCSP_TOKEN_OPT: "test-token"}}


class TestEvaluationsController:
    @pytest.fixture
    def controller(self):
        return EvaluationsController()

    def test_get_env_config(self, controller):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.Config",
            MockConfig,
        ):
            url, tenant_name, token = controller._get_env_config()

            assert url == "test-url"
            assert tenant_name == "test-tenant"
            assert token == "test-token"

    def test_evaluate_with_config_file(self, controller):
        config_content = {
            "test_paths": ["test/path1", "test/path2"],
            "output_dir": "test_output",
            "auth_config": {
                "url": "test-url",
                "tenant_name": "test-tenant",
                "token": "test-token",
            },
            "llm_user_config": {"model_id": "test-model"},
        }

        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".yaml", delete=False
        ) as tmp:
            yaml.dump(config_content, tmp)
            tmp.flush()
            config_file_path = tmp.name

        try:
            with patch("agentops.main.main") as mock_evaluate, patch.object(
                controller,
                "_get_env_config",
                return_value=("test-url", "test-tenant", "test-token"),
            ):

                controller.evaluate(config_file=config_file_path)
                mock_evaluate.assert_called_once()
                actual_config = mock_evaluate.call_args[0][0]
                assert isinstance(actual_config, TestConfig)
                assert actual_config.test_paths == ["test/path1", "test/path2"]
                assert actual_config.output_dir == "test_output"
        finally:
            Path(config_file_path).unlink()

    def test_quick_eval_with_config_file(self, controller):
        config_content = {
            "test_paths": ["test/path1", "test/path2"],
            "output_dir": "test_output",
            "auth_config": {
                "url": "test-url",
                "tenant_name": "test-tenant",
                "token": "test-token",
            },
            "llm_user_config": {"model_id": "test-model"},
        }

        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".yaml", delete=False
        ) as tmp:
            yaml.dump(config_content, tmp)
            tmp.flush()
            config_file_path = tmp.name

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".py", delete=False) as tmp:
            tmp.write(
                """
                def tool1():
                    '''A test tool'''
                    pass

                def tool2():
                    '''Another test tool'''
                    pass
            """
            )
            tmp.flush()
            tools_file = tmp.name

        try:
            with patch("agentops.quick_eval.main") as mock_evaluate, patch.object(
                controller,
                "_get_env_config",
                return_value=("test-url", "test-tenant", "test-token"),
            ):

                controller.evaluate(
                    config_file=config_file_path,
                    tools_path=tools_file,
                    mode=EvaluateMode.referenceless,
                )
                mock_evaluate.assert_called_once()
                actual_config = mock_evaluate.call_args[0][0]

                assert isinstance(actual_config, QuickEvalConfig)
                assert actual_config.test_paths == ["test/path1", "test/path2"]
                assert actual_config.output_dir == "test_output"
                assert actual_config.tools_path == tools_file
        finally:
            Path(config_file_path).unlink()
            Path(tools_file).unlink()

    def test_record(self, controller, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / ".cache" / "orchestrate").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".config" / "orchestrate").mkdir(parents=True, exist_ok=True)
        mock_runs = []
        # Mock get_recent_runs to prevent HTTP requests but allow record_chats to execute
        with patch(
            "agentops.record.record_chat.get_recent_runs", return_value=mock_runs
        ), patch.object(
            controller,
            "_get_env_config",
            return_value=("https://test-url", "test-tenant", "test-token"),
        ), patch(
            "time.sleep", side_effect=KeyboardInterrupt
        ):  # Simulate Ctrl+C
            output_dir = "test_output"
            controller.record(output_dir)

            assert Path(output_dir).exists()

    def test_record_with_context_variables(self, controller, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / ".cache" / "orchestrate").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".config" / "orchestrate").mkdir(parents=True, exist_ok=True)
        mock_runs = []
        context_vars_json = '{"user_id": "user123", "environment": "production"}'
        
        with patch(
            "agentops.record.record_chat.get_recent_runs", return_value=mock_runs
        ), patch.object(
            controller,
            "_get_env_config",
            return_value=("https://test-url", "test-tenant", "test-token"),
        ), patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.record_chats"
        ) as mock_record_chats:
            output_dir = "test_output"
            controller.record(output_dir, context_variables=context_vars_json)

            # Verify record_chats was called with context_variables as JSON string in config
            assert mock_record_chats.called
            call_args = mock_record_chats.call_args
            config = call_args[0][0]  # First positional argument is the config
            assert hasattr(config, 'context_variables')
            assert config.context_variables == context_vars_json

    def test_generate(self, controller):
        # Create temporary CSV file with test data
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False) as tmp:
            writer = csv.DictWriter(tmp, fieldnames=["agent", "story"])
            writer.writeheader()
            writer.writerow({"agent": "test_agent", "story": "test story"})
            tmp.flush()
            stories_path = tmp.name

        # Create temporary directory with mock tool file
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

        try:
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.get_provider"
            ) as mock_get_provider, patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.get_wxo_client"
            ) as mock_get_wxo_client, patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.WXORuntimeAdapter"
            ) as mock_adapter, patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.AutomaticEvalDataGenerator"
            ) as mock_generator_cls, patch.object(
                controller,
                "_get_env_config",
                return_value=("test-url", "test-tenant", "test-token"),
            ):
                mock_get_provider.return_value = MagicMock()
                mock_get_wxo_client.return_value = MagicMock()
                mock_adapter.return_value = MagicMock()

                mock_generator = MagicMock()
                mock_generator.generate_eval_data.return_value = {}
                mock_generator_cls.return_value = mock_generator

                output_dir = "test_output"
                controller.generate(stories_path, tools_dir, output_dir)

                mock_get_provider.assert_called()
                mock_generator_cls.assert_called_once()
                mock_generator.generate_eval_data.assert_called_once()
        finally:
            Path(stories_path).unlink()
            shutil.rmtree(tools_dir)

    def test_analyze(self, controller):
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create messages directory
            messages_dir = Path(temp_dir) / "messages"
            messages_dir.mkdir()

            # Create sample summary_metrics.csv with correct format for non-legacy evaluation
            metrics_file = Path(temp_dir) / "summary_metrics.csv"
            csv_content = (
                "run_idx,orchestrate_agent_routing_accuracy,total_steps,llm_steps,average_agent_response_time,"
                "total_tool_calls,expected_tool_calls,correct_tool_calls,missed_tool_calls,relevant_tool_calls,"
                "tool_calls_with_incorrect_parameter,tool_call_recall,tool_call_precision,tool_match_success,"
                "keyword_match,semantic_match,text_match,is_success,dataset_name,text_match_comment\n"
                "1,1,8,4,0.475,3,3,2,1,2,0,0.67,0.67,False,False,False,,False,data_complex,Matched 0/0 text goals\n"
                "1,1,10,5,0.665,4,4,4,0,4,0,1.0,1.0,True,False,False,,True,data_simple,Matched 0/0 text goals\n"
            )
            metrics_file.write_text(csv_content)

            # Create messages files for both test cases
            for test_case in ["data_complex", "data_simple"]:
                message_file = messages_dir / f"{test_case}.messages.analyze.json"
                message_content = [
                    {
                        "message": {
                            "role": "user",
                            "content": "test message",
                            "type": "text",
                        },
                        "reason": None,
                    },
                    {
                        "message": {
                            "role": "assistant",
                            "content": "test response",
                            "type": "text",
                        },
                        "reason": None,
                    },
                ]
                message_file.write_text(json.dumps(message_content, indent=2))

                # Create metrics file
                metrics_file = messages_dir / f"{test_case}.metrics.json"
                metrics_content = {
                    "total_tool_calls": 5,
                    "expected_tool_calls": 5,
                    "relevant_tool_calls": 3,
                    "correct_tool_calls": 3,
                    "total_routing_calls": 2,
                    "expected_routing_calls": 2,
                }
                metrics_file.write_text(json.dumps(metrics_content, indent=2))

            # Create a dummy tool definition file
            tool_def_file = Path(temp_dir) / "tools.py"
            tool_def_file.write_text("def dummy_tool(): pass")

            from agentops.arg_configs import AnalyzeConfig, AnalyzeMode
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.run_analyze"
            ) as mock_run_analyze:
                controller.analyze(
                    data_path=temp_dir,
                    tool_definition_path=str(tool_def_file),
                    mode=AnalyzeMode.default,
                )
                mock_run_analyze.assert_called_once()
                actual_config = mock_run_analyze.call_args[0][0]
                assert isinstance(actual_config, AnalyzeConfig)
                assert actual_config.data_path == temp_dir
                assert actual_config.tool_definition_path == str(tool_def_file)
                assert actual_config.mode is AnalyzeMode.default

    def test_external_validate(self, controller):
        config = {"auth_scheme": "api_key", "api_url": "test-url"}
        test_data = ["input1", "input2"]
        credential = "test-cred"

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.ExternalAgentValidation"
        ) as mock_validator_class:
            for add_context in [True, False]:
                mock_validator = MagicMock()
                mock_validator_class.return_value = mock_validator
                mock_validator.call_validation.return_value = ["result1", "result2"]

                result = controller.external_validate(
                    config, test_data, credential, add_context=add_context
                )

                mock_validator_class.assert_called_once_with(
                    credential=credential,
                    auth_scheme=config["auth_scheme"],
                    service_url=config["api_url"],
                )

                assert mock_validator.call_validation.call_count == 2
                mock_validator.call_validation.assert_any_call("input1", add_context)
                mock_validator.call_validation.assert_any_call("input2", add_context)

                assert len(result) == 2
                assert result[0] == ["result1", "result2"]
                assert result[1] == ["result1", "result2"]

                mock_validator_class.reset_mock()

    def test_generate_performance_test(self, controller):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.ExternalAgentPerformanceTest"
        ) as mock_validator_class:
            mock_validator = MagicMock()
            mock_validator_class.return_value = mock_validator
            mock_validator.generate_tests.return_value = ["result1"]

            controller.generate_performance_test(
                agent_name="dummy_agent", test_data=[("dummy story", "dummy_response")]
            )
            mock_validator_class.assert_called_once_with(
                agent_name="dummy_agent", test_data=[("dummy story", "dummy_response")]
            )

    def test_generate_red_teaming_attacks(self, controller):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.attack_generator.main"
        ) as mock_gen:
            mock_gen.return_value = ["attack1"]

            controller.generate_red_teaming_attacks(
                attacks_list="attackA,attackB",
                datasets_path="datasets",
                agents_list_or_path="agents",
                target_agent_name="target_agent",
                output_dir="test_output",
                max_variants=2,
            )

            mock_gen.assert_called_once()
            passed_cfg = mock_gen.call_args[0][0]

            assert isinstance(passed_cfg, AttackGeneratorConfig)
            assert passed_cfg.attacks_list == ["attackA", "attackB"]
            assert passed_cfg.datasets_path == ["datasets"]
            assert passed_cfg.agents_list_or_path == ["agents"]
            assert passed_cfg.target_agent_name == "target_agent"
            assert passed_cfg.output_dir == "test_output"
            assert passed_cfg.max_variants == 2

    def test_run_red_teaming_attacks(self, controller, monkeypatch):
        # Using wx.ai provider
        monkeypatch.setenv("WATSONX_SPACE_ID", "id")
        monkeypatch.setenv("WATSONX_APIKEY", "key")

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.run_attacks"
        ) as mock_run, patch.object(
            controller,
            "_get_env_config",
            return_value=("test-url", "test-tenant", "test-token"),
        ):
            controller.run_red_teaming_attacks(
                attack_paths="att1,att2", output_dir="test_output"
            )

            mock_run.assert_called_once()
            passed_cfg = mock_run.call_args[0][0]

            assert isinstance(passed_cfg, AttackConfig)
            assert passed_cfg.attack_paths == ["att1", "att2"]
            assert passed_cfg.output_dir == "test_output"
