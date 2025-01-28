from ibm_watsonx_orchestrate.cli.commands.agents import agents_command
from ibm_watsonx_orchestrate.agent_builder.agents.types import (
    DEFAULT_LLM,
    AgentManagementStyle,
)
from unittest.mock import patch


def test_agent_import_call_no_file():
    with patch(
        "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.import_agent"
    ) as mock:
        agents_command.agent_import(file=None)
        mock.assert_called_once_with(
            file=None,
        )


def test_agent_import_call_with_file():
    with patch(
        "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.import_agent"
    ) as mock:
        agents_command.agent_import(file="/tests/test_file")
        mock.assert_called_once_with(
            file="/tests/test_file",
        )


def test_agent_create_call_expert_agent():
    with patch(
        "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.generate_agent_spec"
    ) as mock:
        agents_command.agent_create(
            name="test_expert_agent",
            type="expert",
            description="Test for expert agent description",
            role="Test for expert agent role",
            goal="Test for expert agent goal",
            instructions="Test for expert agent instructions",
            tools="test_tool_1, test_tool_2",
        )

        mock.assert_called_once_with(
            name="test_expert_agent",
            type="expert",
            description="Test for expert agent description",
            role="Test for expert agent role",
            goal="Test for expert agent goal",
            instructions="Test for expert agent instructions",
            tools="test_tool_1, test_tool_2",
            management_style=AgentManagementStyle.SUPERVISOR,
            management_style_config=None,
            llm=DEFAULT_LLM,
            agents=None,
            output_file=None,
        )


def test_agent_create_call_orchestrator_agent():
    with patch(
        "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.generate_agent_spec"
    ) as mock:
        agents_command.agent_create(
            name="test_orchestrator_agent",
            type="orchestrator",
            management_style="supervisor",
            management_style_config="reflection_enabled=true,reflection_retry_count=3",
            llm="granite",
            agents="test_agent_1, test_agent_2",
        )

        mock.assert_called_once_with(
            name="test_orchestrator_agent",
            type="orchestrator",
            description=None,
            role=None,
            goal=None,
            instructions=None,
            tools=None,
            management_style="supervisor",
            management_style_config="reflection_enabled=true,reflection_retry_count=3",
            llm="granite",
            agents="test_agent_1, test_agent_2",
            output_file=None,
        )
