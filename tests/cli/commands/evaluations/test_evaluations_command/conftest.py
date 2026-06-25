"""Shared fixtures for all evaluation tests"""
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch


@pytest.fixture(autouse=True, scope="function")
def mock_get_env_config():
    """Mock _get_env_config to prevent API key prompts in all tests"""
    # Import the module first to ensure it exists before patching
    try:
        from ibm_watsonx_orchestrate.cli.commands.evaluations import evaluations_controller
        with patch.object(
            evaluations_controller.EvaluationsController,
            "_get_env_config",
            return_value=("http://test-url", "test-tenant", "test-token")
        ):
            yield
    except ImportError:
        # If import fails, just yield without patching (test will handle the import error)
        yield


@pytest.fixture(autouse=True, scope="module")
def user_env_file():
    """Create a temporary .env file with test credentials"""
    env_content = """WATSONX_SPACE_ID=id
WATSONX_APIKEY=key"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".env", delete=False) as tmp:
        tmp.write(env_content)
        tmp.flush()
        env_path = tmp.name
        yield env_path
        Path(env_path).unlink()


@pytest.fixture
def valid_config():
    """Standard valid configuration for tests"""
    return {
        "test_paths": ["test/path1", "test/path2"],
        "output_dir": "test_output",
        "auth_config": {
            "url": "test-url",
            "tenant_name": "test-tenant",
            "token": "test-token",
        },
    }


@pytest.fixture
def config_file(valid_config):
    """Create a temporary config file"""
    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".json", delete=False
    ) as tmp:
        json.dump(valid_config, tmp)
        tmp.flush()
        config_path = tmp.name
        yield config_path
        Path(config_path).unlink()


@pytest.fixture
def external_agent_config():
    """Create a temporary external agent config file"""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
        ext_agent_config = {
            "spec_version": "v1",
            "kind": "external",
            "name": "news_agent",
            "title": "News Agent",
            "nickname": "news_agent",
            "provider": "external_chat",
            "description": "An agent built in langchain which searches the news.\n",
            "tags": ["test"],
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

# Made with Bob



@pytest.fixture
def evaluation_results_dir():
    """Create a temporary directory with evaluation results structure
    
    Creates an exact replica of the structure found in:
    /Users/arjungupta/Documents/Development/non_legacy/2026-06-11_16-51-54/
    """
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create the expected folder structure with timestamp directory
        results_path = Path(temp_dir) / "2026-06-11_16-51-54"
        results_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (results_path / "debug").mkdir(exist_ok=True)
        (results_path / "knowledge_base_metrics").mkdir(exist_ok=True)
        (results_path / "messages").mkdir(exist_ok=True)
        
        # Create metadata files for 3 test cases
        test_ids = [
            "3d2b85b3-e2d8-4477-a927-bf7176d7d156",
            "75338adf-6673-4be3-8e78-7dd0149f4dfd",
            "778248ea-fd72-467c-8b23-546cb3a7b2e7"
        ]
        
        for test_id in test_ids:
            # Metadata file
            (results_path / f"{test_id}.metadata.json").write_text(
                '{\n    "thread_id": "test-thread-id"\n}'
            )
            
            # Messages files
            (results_path / "messages" / f"{test_id}.messages.json").write_text(
                '[{"role": "user", "content": "test message"}]'
            )
            (results_path / "messages" / f"{test_id}.messages.analyze.json").write_text(
                '{"analysis": "test"}'
            )
            (results_path / "messages" / f"{test_id}.metrics.json").write_text(
                '{"accuracy": 0.95}'
            )
        
        # Create average_metrics.json
        (results_path / "average_metrics.json").write_text('''{
    "Runs": 1.0,
    "Orchestrate Agent Routing F1": 1.0,
    "Total Steps": 10.0,
    "LLM Steps": 5.0,
    "Average Agent Response Time (s)": 0.63,
    "Total Tool Calls": 3.0,
    "Expected Tool Calls": 3.33,
    "Correct Tool Calls": 2.33,
    "Missed Tool Calls": 1.0,
    "Relevant Tool Calls": 2.33,
    "Tool Calls with Incorrect Parameters": 0.0,
    "Tool Call Recall": 0.67,
    "Tool Call Precision": 0.72,
    "Tool Match Success": 0.33,
    "Keyword Match": 0.0,
    "Semantic Match": 0.0,
    "Journey Success": 0.33
}''')
        
        # Create config.yml
        (results_path / "config.yml").write_text('''auth_config:
  tenant_name: local
  token: test-token
  url: http://localhost:4321
n_runs: 1
output_dir: results/rubric_evals/customer_support/normal/2026-06-10_15-34-32
skip_legacy_evaluation: true
metrics:
- JourneySuccessMetric
- ToolCalling
- OrchestrateAgentRoutingAccuracy
''')
        
        # Create summary_metrics.csv
        (results_path / "summary_metrics.csv").write_text('''run_idx,orchestrate_agent_routing_accuracy,total_steps,llm_steps,average_agent_response_time,total_tool_calls,expected_tool_calls,correct_tool_calls,missed_tool_calls,relevant_tool_calls,tool_calls_with_incorrect_parameter,tool_call_recall,tool_call_precision,tool_match_success,keyword_match,semantic_match,text_match,is_success,dataset_name,text_match_comment
1,1,8,4,0.475,3,3,2,1,2,0,0.67,0.67,False,False,False,,False,3d2b85b3-e2d8-4477-a927-bf7176d7d156,Matched 0/0 text goals
1,1,10,5,0.665,4,4,4,0,4,0,1.0,1.0,True,False,False,,True,75338adf-6673-4be3-8e78-7dd0149f4dfd,Matched 0/0 text goals
1,1,12,6,0.765,2,3,1,2,1,0,0.33,0.5,False,False,False,,False,778248ea-fd72-467c-8b23-546cb3a7b2e7,Matched 0/0 text goals
''')
        
        # Create debug/evaluation_order.txt
        (results_path / "debug" / "evaluation_order.txt").write_text('''Evaluation Order
┣━━ OrchestrateAgentRoutingAccuracy
┣━━ StepMetrics
┣━━ AgentResponseTime
┣━━ ToolCalling
┗━━ JourneySuccessMetric
''')
        
        yield str(results_path)
        # Cleanup happens automatically when context exits
