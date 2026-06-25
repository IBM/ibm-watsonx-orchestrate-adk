"""Tests for the environment manager functionality"""
from unittest.mock import patch
import tempfile
import pytest
from pathlib import Path

try:
    from ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_environment_manager import (
        TestCaseManager,
    )
except ImportError as e:
    import traceback

    traceback.print_exc()
    pytest.skip(f"Missing required dependencies: {e}", allow_module_level=True)


class TestEnvironmentManager:
    """Tests for the environment manager and TestCaseManager"""

    @pytest.fixture
    def agent_and_tools(self):
        env_manager = {
            "env1": {
                "agent": {
                    "file": "path_to_agents_def.py",
                },
                "tools": {"file": "path_to_tools_def.py", "kind": "python"},
                "test_config": "dummy_path_config",
                "clean_up": False,
            }
        }

        return env_manager

    @pytest.fixture
    def env_kb_file(self):
        knowledge_cfg = """
                        spec_version: v1
                        kind: knowledge_base
                        name: hr_knowledge_base
                        description: HR policies like time off, pay schedules, holidays, business conduct guidelines
                        documents:
                            - list-of-pay-dates-and-dates-covered-2025.pdf
                    """
        dir = tempfile.mkdtemp()
        knowledge_file = Path(dir) / "knowledge_base.yaml"
        knowledge_file.write_text(knowledge_cfg)

        return str(knowledge_file)

    @pytest.fixture
    def agent_and_tools_and_knowledge(self, env_kb_file):
        env_manager = {
            "env1": {
                "agent": {
                    "file": "path_to_agents_def.py",
                },
                "tools": {"file": "path_to_tools_def.py", "kind": "python"},
                "knowledge": {
                    "file": env_kb_file,
                },
                "test_config": "dummy_path_config",
                "clean_up": False,
            }
        }

        return env_manager

    def test_case_manager(self, agent_and_tools, agent_and_tools_and_knowledge):
        """Test the TestCaseManager context manager with and without knowledge base"""
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.ToolsController.import_tool"
        ) as mock_import_tool:
            with patch(
                "ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.ToolsController.publish_or_update_tools"
            ) as mock_publish_tool:
                with patch(
                    "ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.import_knowledge_base"
                ) as mock_import_knowledge_base:
                    with patch(
                        "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.import_agent"
                    ) as mock_import_agent:
                        with patch(
                            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_or_update_agents"
                        ) as mock_publish_or_update_agents:
                            with patch(
                                "ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller.EvaluationsController.evaluate"
                            ) as mock_evaluate:
                                temp_dir = Path(tempfile.mkdtemp()) / "env1"
                                
                                # Test with agent and tools only
                                with TestCaseManager(
                                    agent_and_tools.get("env1"), output_dir=temp_dir
                                ) as t:
                                    mock_import_tool.assert_called()
                                    mock_publish_tool.assert_called()
                                    mock_import_agent.assert_called()
                                    mock_publish_or_update_agents.assert_called()
                                    mock_evaluate.assert_called()
                                    assert len(t.imported_artifacts) == 2
                                
                                # Test with agent, tools, and knowledge base
                                with TestCaseManager(
                                    agent_and_tools_and_knowledge.get("env1"),
                                    output_dir=temp_dir,
                                ) as t:
                                    mock_import_tool.assert_called()
                                    mock_publish_tool.assert_called()
                                    mock_import_agent.assert_called()
                                    mock_publish_or_update_agents.assert_called()
                                    mock_import_knowledge_base.assert_called()

                                    mock_evaluate.assert_called()
                                    assert len(t.imported_artifacts) == 3

# Made with Bob
