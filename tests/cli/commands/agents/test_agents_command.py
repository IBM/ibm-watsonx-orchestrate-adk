from ibm_watsonx_orchestrate.cli.commands.agents import agents_command
from ibm_watsonx_orchestrate.agent_builder.agents import AgentKind, AgentStyle, ExternalAgentAuthScheme, AgentProvider
from unittest.mock import patch

class TestAgentImport:
    def test_agent_import(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.import_agent") as import_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_or_update_agents") as publish_mock:
            agents_command.agent_import(file="test.yaml")
            import_mock.assert_called_once_with(
                file="test.yaml",
                app_id=None
            )
            publish_mock.assert_called_once()
    
    def test_agent_import_no_file(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.import_agent") as import_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_or_update_agents") as publish_mock:
            agents_command.agent_import(file=None)
            import_mock.assert_called_once_with(
                file=None,
                app_id=None
            )
            publish_mock.assert_called_once()

class TestAgentCreate:
    def test_create_native_agent(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.generate_agent_spec") as generate_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_or_update_agents") as publish_mock:
            agents_command.agent_create(
                name="test",
                kind=AgentKind.NATIVE,
                description="test_agent",
                title="test",
                api_url=None,
                auth_scheme=ExternalAgentAuthScheme.API_KEY,
                auth_config='{}',
                provider=AgentProvider.EXT_CHAT,
                llm="test_llm",
                style=AgentStyle.DEFAULT,
                custom_join_tool=None,
                structured_output=None,
                collaborators=[],
                tools=[],
                knowledge_base=[],
                tags=None, 
                chat_params='{}', 
                config='{}', 
                nickname=None, 
                app_id=None,
                output_file="test.yaml",
                context_access_enabled=True,
                context_variables=None,
                )
            generate_mock.assert_called_once_with(
                name="test",
                kind=AgentKind.NATIVE,
                description="test_agent",
                title="test",
                api_url=None,
                auth_scheme=ExternalAgentAuthScheme.API_KEY,
                auth_config={},
                provider=AgentProvider.EXT_CHAT,
                llm="test_llm",
                style=AgentStyle.DEFAULT,
                custom_join_tool=None,
                structured_output=None,
                collaborators=[],
                tools=[],
                knowledge_base=[],
                tags=None, 
                chat_params={}, 
                config={}, 
                nickname=None, 
                app_id=None,
                output_file="test.yaml",
                context_access_enabled=True,
                context_variables=None,
            )
            publish_mock.assert_called_once()

    def test_create_native_agent_planner(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.generate_agent_spec") as generate_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_or_update_agents") as publish_mock:
            agents_command.agent_create(
                name="test",
                kind=AgentKind.NATIVE,
                description="test_agent",
                title="test",
                api_url=None,
                auth_scheme=ExternalAgentAuthScheme.API_KEY,
                auth_config='{}',
                provider=AgentProvider.EXT_CHAT,
                llm="test_llm",
                style=AgentStyle.PLANNER,
                custom_join_tool='test_join_tool',
                structured_output='{"type": "object", "additionalProperties": false, "properties": {}}',
                collaborators=[],
                tools=[],
                knowledge_base=[],
                tags=None, 
                chat_params='{}', 
                config='{}', 
                nickname=None, 
                app_id=None,
                output_file="test.yaml",
                context_access_enabled=True,
                context_variables=None,
                )
            generate_mock.assert_called_once_with(
                name="test",
                kind=AgentKind.NATIVE,
                description="test_agent",
                title="test",
                api_url=None,
                auth_scheme=ExternalAgentAuthScheme.API_KEY,
                auth_config={},
                provider=AgentProvider.EXT_CHAT,
                llm="test_llm",
                style=AgentStyle.PLANNER,
                custom_join_tool='test_join_tool',
                structured_output={"type": "object", "additionalProperties": False, "properties": {}},
                collaborators=[],
                tools=[],
                knowledge_base=[],
                tags=None, 
                chat_params={}, 
                config={}, 
                nickname=None, 
                app_id=None,
                output_file="test.yaml",
                context_access_enabled=True,
                context_variables=None,
            )
            publish_mock.assert_called_once()


class TestAgentList:
    def test_agent_list_agents_non_verbose(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.list_agents"
        ) as mock:
            agents_command.list_agents()

            mock.assert_called_once_with(
                kind=None,
                verbose=False
            )

    def test_agent_list_agents_verbose(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.list_agents"
        ) as mock:
            agents_command.list_agents(verbose=True)

            mock.assert_called_once_with(
                kind=None,
                verbose=True
            )

class TestAgentDelete:
    def test_agent_remove_native_agent(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.remove_agent"
        ) as mock:
            agents_command.remove_agent(
                name="test_native_agent",
                kind=AgentKind.NATIVE,
            )

            mock.assert_called_once_with(
                name="test_native_agent",
                kind=AgentKind.NATIVE,
            )

class TestAgentExport:
    def test_agent_export(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.export_agent"
        ) as mock:
            agents_command.export_agent(
                name="test_native_agent",
                kind=AgentKind.NATIVE,
                output_file="test_output.zip"
            )

            mock.assert_called_once_with(
                name="test_native_agent",
                kind=AgentKind.NATIVE,
                output_path="test_output.zip",
                agent_only_flag=False
            )
