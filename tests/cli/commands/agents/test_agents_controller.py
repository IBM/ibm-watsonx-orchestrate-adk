from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import (
    AgentsController,
    AgentTypes,
)
from ibm_watsonx_orchestrate.agent_builder.agents.types import SupervisorConfig
from ibm_watsonx_orchestrate.agent_builder.agents.orchestrate_agent import (
    OrchestrateAgent,
)
from ibm_watsonx_orchestrate.agent_builder.agents.expert_agent import ExpertAgent
import os
import json
from typer import BadParameter
from unittest.mock import patch
import pytest

agents_controller = AgentsController()


@pytest.fixture
def expert_agent_content() -> dict:
    return {
        "name": "research_agent",
        "type": "expert",
        "description": "A Research Assistant which can query the web to help the user with research tasks that require current knowledge or open data from the web to complete.",
        "role": "You are a helpful and ethical AI research assistant that uses web search tools to answer user questions.",
        "goal": "Answer the user's question using the information found on the web.",
        "instructions": "Use the tools provided to answer the user's question.  If you do not have enough information to answer the question, say so.  If you need more information, ask follow up questions.",
        "tools": ["web_search"],
    }


@pytest.fixture
def orchestrate_agent_content() -> dict:
    return {
        "name": "my_agent",
        "type": "orchestrator",
        "management_style": "supervisor",
        "management_style_config": {
            "reflection_enabled": True,
            "reflection_retry_count": 3,
        },
        "llm": "granite",
        "agents": ["research_agent", "sales_agent"],
    }


class MockSDKResponse:
    def __init__(self, response_obj):
        self.response_obj = response_obj

    def dumps_spec(self):
        return json.dumps(self.response_obj)


@patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ExpertAgent")
def test_expert_agent_import_yaml(mock, capsys, expert_agent_content):
    mock.return_value = MockSDKResponse(expert_agent_content)
    file = "tests/cli/resources/yaml_samples/expert_agent.yaml"
    for agent in agents_controller.import_agent(file=file):
        assert agent.response_obj == expert_agent_content
        break


@patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ExpertAgent")
def test_expert_agent_import_json(mock, capsys, expert_agent_content):
    mock.return_value = MockSDKResponse(expert_agent_content)
    file = "tests/cli/resources/json_samples/expert_agent.json"
    for agent in agents_controller.import_agent(file=file):
        assert agent.response_obj == expert_agent_content
        break


def test_expert_agent_import_python(capsys):
    file = os.path.join(os.path.dirname(__file__), "../../resources/python_samples/base_expert_agent.py")
    agents = list(agents_controller.import_agent(file=file))
    assert agents[0].name == "sample_orchestrator_agent"
    assert isinstance(agents[0], OrchestrateAgent)

    assert agents[1].name == "research_agent"
    assert (
        agents[1].description
        == "A Research Assistant which can query the web to help the user with research tasks that require current knowledge or open data from the web to complete."
    )
    assert isinstance(agents[1], ExpertAgent)


def test_orchestrate_agent_import_yaml():
    file = "tests/cli/resources/yaml_samples/orchestrator_agent.yaml"
    agents = list(agents_controller.import_agent(file=file))
    assert agents[0].name == "my_agent"
    assert agents[0].agents == ["research_agent", "sales_agent"]


def test_orchestrate_agent_import_json():
    file = "tests/cli/resources/json_samples/orchestrator_agent.json"
    agents = list(agents_controller.import_agent(file=file))
    assert agents[0].name == "my_agent"
    assert agents[0].agents == ["research_agent", "sales_agent"]


def test_agent_import_no_file():
    with pytest.raises(TypeError):
        agents_controller.import_agent()


def test_agent_import_missing_file():
    with pytest.raises(FileNotFoundError):
        agents = agents_controller.import_agent("ok")


def test_agent_import_invalid_file_type():
    with pytest.raises(ValueError):
        agents_controller.import_agent("tests/cli/resources/misc/sample.txt")


@patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.yaml.load")
def test_agent_import_invaild_type(mock):
    mock.return_value = {"type": "fake"}
    file = "tests/cli/resources/yaml_samples/orchestrator_agent.yaml"
    with pytest.raises(ValueError):
        agents_controller.import_agent(file=file)


@patch(
    "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_all_expert_agents",
    return_value={},
)
@patch(
    "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_agent",
    return_value=True,
)
def test_expert_agent_create(mock1, mock2):

    agent_spec = agents_controller.generate_agent_spec(
        name="research_agent",
        type=AgentTypes("expert"),
        description="Test for expert agent description",
        role="Test for expert agent role",
        goal="Test for expert agent goal",
        instructions="Test for expert agent instructions",
        tools="web_search, test_tool_2",
    )
    assert isinstance(agent_spec, ExpertAgent)
    agents_controller.publish_or_update_agents([agent_spec])

    mock1.assert_called_once_with(agent_spec)


def test_expert_agent_create_missing_args():

    with pytest.raises(BadParameter):
        agents_controller.generate_agent_spec(
            name="",
            type=AgentTypes("expert"),
            description=None,
            role=None,
            goal=None,
            instructions=None,
            tools=None,
        )


def test_orchestrator_agent_create():

    orchestrate_agent_spec = agents_controller.generate_agent_spec(
        name="my_agent",
        type=AgentTypes("orchestrator"),
        management_style="supervisor",
        management_style_config="reflection_enabled=true,reflection_retry_count=3",
        llm="granite",
        agents="research_agent, sales_agent",
    )
    assert orchestrate_agent_spec.name == "my_agent"


def test_orchestrator_agent_create_no_args():
    with pytest.raises(BadParameter):
        agents_controller.generate_agent_spec(
            name="",
            type=AgentTypes("orchestrator"),
            management_style=None,
            management_style_config=None,
            llm=None,
            agents=None,
        )
