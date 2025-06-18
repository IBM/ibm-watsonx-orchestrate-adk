import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import yaml
import csv
import shutil
import json
from ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller import EvaluationsController
from ibm_watsonx_orchestrate.cli.config import AUTH_MCSP_TOKEN_OPT
from wxo_agentic_evaluation.arg_configs import TestConfig, AnalyzeConfig

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
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.Config", MockConfig) :
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
                "token": "test-token"
            },
            "llm_user_config": {
                "model_id": "test-model"
            }
        }

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".yaml", delete=False) as tmp:
            yaml.dump(config_content, tmp)
            tmp.flush()
            config_file_path = tmp.name

        try:
            with patch("wxo_agentic_evaluation.main.main") as mock_evaluate, \
                 patch.object(controller, "_get_env_config", return_value=("test-url", "test-tenant", "test-token")):
                
                controller.evaluate(config_file=config_file_path)
                mock_evaluate.assert_called_once()
                actual_config = mock_evaluate.call_args[0][0]
                assert isinstance(actual_config, TestConfig)
                assert actual_config.test_paths == ["test/path1", "test/path2"]
                assert actual_config.output_dir == "test_output"
        finally:
            Path(config_file_path).unlink()

    def test_record(self, controller):
        mock_runs = []
        # Mock get_all_runs to prevent HTTP requests but allow record_chats to execute
        with patch("wxo_agentic_evaluation.record_chat.get_all_runs", return_value=mock_runs), \
             patch.object(controller, "_get_env_config", return_value=("https://test-url", "test-tenant", "test-token")), \
             patch("time.sleep", side_effect=KeyboardInterrupt):  # Simulate Ctrl+C
            output_dir = "test_output"
            controller.record(output_dir)
            
            assert Path(output_dir).exists()

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
        tools_file.write_text("""
def tool1():
    '''A test tool'''
    pass

def tool2():
    '''Another test tool'''
    pass
""")

        example_json = {
            "utterance": "test story",
            "tools": ["tool1", "tool2"],
            "expected": {
                "tools": ["tool1", "tool2"],
                "args": [{"arg1": "val1"}, {"arg2": "val2"}]
            }
        }

        try:
            with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.build_snapshot") as mock_build_snapshot, \
                 patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.generate_test_cases_from_stories") as mock_generate, \
                 patch("wxo_agentic_evaluation.batch_annotate.load_example", return_value=example_json), \
                 patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.AgentsController") as mock_agent_controller:

                mock_agent = MagicMock()
                mock_agent_controller_instance = MagicMock()
                mock_agent_controller.return_value = mock_agent_controller_instance
                mock_agent_controller_instance.get_agent.return_value = mock_agent
                mock_agent_controller_instance.get_agent_tool_names.return_value = ["tool1", "tool2"]

                output_dir = "test_output"
                controller.generate(stories_path, tools_dir, output_dir)

                mock_build_snapshot.assert_called_once()
                mock_generate.assert_called_once()
        finally:
            Path(stories_path).unlink()
            shutil.rmtree(tools_dir)

    def test_analyze(self, controller):
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create messages directory
            messages_dir = Path(temp_dir) / "messages"
            messages_dir.mkdir()

            # Create sample summary_metrics.csv
            metrics_file = Path(temp_dir) / "summary_metrics.csv"
            csv_content = (
                "test_case,Total Step,Agent Step,Ground Truth Calls,Wrong Function Calls,Wrong Parameters,"
                "Wrong Routing Calls,Text Match,Journey Success,Avg Resp Time (Secs)\n"
                "data_complex,18,9,5,0,2,0,Summary Matched,False,2.09\n"
                "data_simple,12,6,2,0,0,0,Summary Matched,True,2.43\n"
                "Summary (Average),15.0,7.5,3.5,0.0,0.29,0.0,1.0,0.5,2.26\n"
            )
            metrics_file.write_text(csv_content)
            
            # Create messages file
            message_file = messages_dir / "data_complex.messages.analyze.json"
            message_content = [
                {
                    "message": {
                        "role": "user",
                        "content": "test message",
                        "type": "text"
                    },
                    "reason": None
                },
                {
                    "message": {
                        "role": "assistant",
                        "content": "test response",
                        "type": "text"
                    },
                    "reason": None
                }
            ]
            message_file.write_text(json.dumps(message_content, indent=2))
            
            # Create metrics file
            metrics_file = messages_dir / "data_complex.metrics.json"
            metrics_content = {
                "total_tool_calls": 5,
                "expected_tool_calls": 5,
                "relevant_tool_calls": 3,
                "correct_tool_calls": 3,
                "total_routing_calls": 2,
                "expected_routing_calls": 2
            }
            metrics_file.write_text(json.dumps(metrics_content, indent=2))

            with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.analyze") as mock_analyze:
                controller.analyze(temp_dir)

                mock_analyze.assert_called_once()
                actual_config = mock_analyze.call_args[0][0]
                assert isinstance(actual_config, AnalyzeConfig)
                assert actual_config.data_path == temp_dir

    def test_external_validate(self, controller):
        with patch("ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.ExternalAgentValidation") as mock_validator_class:
            mock_validator = MagicMock()
            mock_validator_class.return_value = mock_validator
            mock_validator.call_validation.return_value = ["result1", "result2"]
            
            config = {
                "auth_scheme": "api_key",
                "api_url": "test-url"
            }
            test_data = ["input1", "input2"]
            credential = "test-cred"
            
            result = controller.external_validate(config, test_data, credential)
            
            mock_validator_class.assert_called_once_with(
                credential=credential,
                auth_scheme=config["auth_scheme"],
                service_url=config["api_url"]
            )
            
            assert mock_validator.call_validation.call_count == 2
            mock_validator.call_validation.assert_any_call("input1")
            mock_validator.call_validation.assert_any_call("input2")
            
            assert len(result) == 2
            assert result[0] == {"input1": ["result1", "result2"]}
            assert result[1] == {"input2": ["result1", "result2"]}
