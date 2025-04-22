from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import (
    AgentsController,
    import_python_agent,
    create_agent_from_spec,
    parse_file,
    parse_create_native_args,
    parse_create_external_args
    )
from ibm_watsonx_orchestrate.agent_builder.agents import AgentKind, AgentStyle, SpecVersion, Agent, ExternalAgent, AssistantAgent
import json
from unittest.mock import patch, mock_open, MagicMock
import pytest
import uuid
import requests
from unittest import mock
import sys

agents_controller = AgentsController()


@pytest.fixture
def native_agent_content() -> dict:
    return {
        "spec_version": SpecVersion.V1,
        "kind": AgentKind.NATIVE,
        "name": "test_native_agent",
        "description": "Test Object for native agent",
        "llm": "test_llm",
        "style": AgentStyle.DEFAULT,
        "collaborators": [
            "test_agent_1",
            "test_agent_2"
        ],
        "tools": [
            "test_tool_1",
            "test_tool_2"
        ]
    }


@pytest.fixture
def external_agent_content() -> dict:
    return {
        "spec_version": SpecVersion.V1,
        "kind": AgentKind.EXTERNAL,
        "name": "test_external_agent",
        "title": "Test External",
        "description": "Test Object for external agent",
        "tags": [
            "tag1",
            "tag2"
        ],
        "api_url": "test",
        "chat_params": {
            "stream": True
        },
        "config":{
            "hidden": False,
            "enable_cot": False
        },
        "nickname": "test_agent",
        "app_id": "123"
    }

@pytest.fixture
def assistant_agent_content() -> dict:
    return {
        "spec_version": SpecVersion.V1,
        "kind": AgentKind.ASSISTANT,
        "name": "test_assistant_agent",
        "title": "Test Assistant",
        "description": "Test Object for assistant agent",
        "tags": [
            "tag1",
            "tag2"
        ],
        "config":{
            "api_version": "2021-11-27",
            "assistant_id": "27de49b4-4abc-4c1a-91d7-1a612c36fd18",
            "crn": "crn:v1:aws:public:wxo:us-east-1:sub/20240412-0950-3314-301c-8dfc5950d337:20240415-0552-2619-5017-c41d62e59413::",
            "instance_url": "https://api.us-east-1.aws.watsonassistant.ibm.com/instances/20240415-0552-2619-5017-c41d62e59413",
            "environment_id": "ef8b93b2-4a4c-4eb8-b479-3fc056c4aa4f",
        },
        "nickname": "test_agent",
        "app_id": "123"
    }


class MockSDKResponse:
    def __init__(self, response_obj):
        self.response_obj = response_obj

    def dumps_spec(self):
        return json.dumps(self.response_obj)

class MockAgent:
    def __init__(self, expected_name=None, expected_agent_spec=None, fake_agent=None, skip_deref=False, already_existing=False):
        self.expected_name = expected_name
        self.fake_agent = fake_agent
        self.skip_deref = skip_deref
        self.already_existing = already_existing
        self.expected_agent_spec = expected_agent_spec

    def delete(self, agent_id):
        pass
    
    def create(self, agent_spec):
        assert agent_spec == self.expected_agent_spec

    def update(self, agent_id, agent_spec):
        assert agent_spec == self.expected_agent_spec
    
    def get(self):
        return [self.fake_agent]
    
    def get_drafts_by_names(self, agents):
        ids = []
        if not self.skip_deref:
            for agent in agents:
                ids.append({"name": agent, "id": uuid.uuid4()})
        return ids

    def get_draft_by_name(self, agent):
        if self.already_existing:
            return [{"name": agent, "id": uuid.uuid4()}]
        return []
        
class TestImportPythonAgent:
    def test_import_python_agent(self, native_agent_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.import_python_tool") as python_tool_import_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.inspect.getmembers") as getmembers_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.importlib.import_module") as import_module_mock:
            
            sample_native_agent = Agent(**native_agent_content)
            # sample_external_agent = ExternalAgent(**external_agent_content)
            # sample_assitant_agent = AssistantAgent(**assistant_agent_content)

            getmembers_mock.return_value = [(None, sample_native_agent)]

            agents = import_python_agent("test.py")

            python_tool_import_mock.assert_called_once_with("test.py")
            import_module_mock.assert_called_with("test")
            getmembers_mock.assert_called_once()

            assert len(agents) == 1

    def test_import_python_external_agent(self, external_agent_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.import_python_tool") as python_tool_import_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.inspect.getmembers") as getmembers_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.importlib.import_module") as import_module_mock:
            
            sample_external_agent = ExternalAgent(**external_agent_content)
            getmembers_mock.return_value = [(None, sample_external_agent)]

            agents = import_python_agent("test.py")

            python_tool_import_mock.assert_called_once_with("test.py")
            import_module_mock.assert_called_with("test")
            getmembers_mock.assert_called_once()

            assert len(agents) == 1

class TestCreateAgentFromSpec:
    def test_create_native_agent_from_spec(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.Agent.from_spec") as mock:
            create_agent_from_spec("test.yaml", AgentKind.NATIVE)

            mock.assert_called_once_with("test.yaml")
        
    def test_create_native_agent_from_spec_no_kind(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.Agent.from_spec") as mock:
            create_agent_from_spec("test.yaml", None)

            mock.assert_called_once_with("test.yaml")

    def test_create_external_agent_from_spec(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ExternalAgent.from_spec") as mock:
            create_agent_from_spec("test.yaml", AgentKind.EXTERNAL)

            mock.assert_called_once_with("test.yaml")

    # def test_create_assistant_agent_from_spec(self):
    #     with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AssistantAgent.from_spec") as mock:
    #         create_agent_from_spec("test.yaml", AgentKind.ASSISTANT)

            # mock.assert_called_once_with("test.yaml")

    def test_create_invalid_agent_from_spec(self):
        with pytest.raises(ValueError) as e:
            create_agent_from_spec("test.yaml", "fake")

            assert "'kind' must be either 'native'" in str(e)

class TestParseFile:
    def test_parse_file_yaml(self, native_agent_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.Agent.from_spec") as from_spec_mock, \
             patch("builtins.open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.yaml.load") as mock_loader:
            
            mock_loader.return_value = native_agent_content

            parse_file("test.yaml")

            from_spec_mock.assert_called_once_with("test.yaml")
            mock_file.assert_called_once_with("test.yaml", "r")
            mock_loader.assert_called_once()

    def test_parse_file_json(self, native_agent_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.Agent.from_spec") as from_spec_mock, \
             patch("builtins.open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.json.load") as mock_loader:
            
            mock_loader.return_value = native_agent_content

            parse_file("test.json")

            from_spec_mock.assert_called_once_with("test.json")
            mock_file.assert_called_once_with("test.json", "r")
            mock_loader.assert_called_once()

    def test_parse_file_yaml_external(self, external_agent_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ExternalAgent.from_spec") as from_spec_mock, \
             patch("builtins.open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.yaml.load") as mock_loader:
            
            mock_loader.return_value = external_agent_content

            parse_file("test.yaml")

            from_spec_mock.assert_called_once_with("test.yaml")
            mock_file.assert_called_once_with("test.yaml", "r")
            mock_loader.assert_called_once()

    def test_parse_file_json_external(self, external_agent_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ExternalAgent.from_spec") as from_spec_mock, \
             patch("builtins.open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.json.load") as mock_loader:
            
            mock_loader.return_value = external_agent_content

            parse_file("test.json")

            from_spec_mock.assert_called_once_with("test.json")
            mock_file.assert_called_once_with("test.json", "r")
            mock_loader.assert_called_once()

    def test_parse_file_py(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.import_python_tool") as python_tool_import_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.inspect.getmembers") as getmembers_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.importlib.import_module") as import_module_mock:

            getmembers_mock.return_value = []
            agents = parse_file("test.py")


            python_tool_import_mock.assert_called_once_with("test.py")
            import_module_mock.assert_called_with("test")
            getmembers_mock.assert_called_once()

            assert len(agents) == 0

    def test_parse_file_invalid(self):
        with pytest.raises(ValueError) as e:
            parse_file("test.test")
            assert "file must end in .json, .yaml, .yml or .py" in str(e)

class TestParseCreateNativeArgs:
    def test_parse_create_native_args(self):
        parsed_args = parse_create_native_args(
            name="test_agent",
            kind=AgentKind.NATIVE,
            description="Test Agent Description",
            llm="test_llm",
            style=AgentStyle.REACT,
            collaborators=["agent1", "    "],
            tools=["  tool1  ", "tool2"]
        )

        assert parsed_args["name"] == "test_agent"
        assert parsed_args["kind"] == AgentKind.NATIVE
        assert parsed_args["description"] == "Test Agent Description"
        assert parsed_args["llm"] == "test_llm"
        assert parsed_args["style"] == AgentStyle.REACT
        assert parsed_args["collaborators"] == ["agent1"]
        assert parsed_args["tools"] == ["tool1", "tool2"]

class TestParseCreateExternalArgs:
    def test_parse_create_external_args(self):
        parsed_args = parse_create_external_args(
            name="test_external_agent",
            kind=AgentKind.EXTERNAL,
            description="Test External Agent Description",
            title="Test External Agent",
            api_url="https://someurl.com",
            tags=["tag1", "tag2"],
            chat_params='{{"stream": true}}',
            config='{"hidden": false, "enable_cot": false}',
            nickname="some_nickname",
            app_id="some_app_id"
        )

        assert parsed_args["name"] == "test_external_agent"
        assert parsed_args["kind"] == AgentKind.EXTERNAL
        assert parsed_args["description"] == "Test External Agent Description"
        assert parsed_args["title"] == "Test External Agent"
        assert parsed_args["api_url"] == "https://someurl.com"
        assert parsed_args["tags"] == ["tag1", "tag2"]
        assert parsed_args["chat_params"] == '{{"stream": true}}'
        assert parsed_args["config"] == '{"hidden": false, "enable_cot": false}'
        assert parsed_args["nickname"] == "some_nickname"
        assert parsed_args["app_id"] == "some_app_id"



class TestAgentsControllerGenerateAgentSpec:
    def test_generate_agent_spec(self):
        agent = AgentsController.generate_agent_spec(
            name="test_agent",
            kind=AgentKind.NATIVE,
            description="Test Agent Description",
            llm="test_llm",
            style=AgentStyle.REACT,
            collaborators=["agent1", "    "],
            tools=["  tool1  ", "tool2"]
        )
        
        assert agent.name == "test_agent"
        assert agent.kind == AgentKind.NATIVE
        assert agent.description == "Test Agent Description"
        assert agent.llm == "test_llm"
        assert agent.style == AgentStyle.REACT
        assert agent.collaborators == ["agent1"]
        assert agent.tools == ["tool1", "tool2"]

    @pytest.mark.parametrize(
            "kind",
            [
                AgentKind.EXTERNAL,
                # AgentKind.ASSISTANT,
                "invalid"
            ]
    )
    def test_generate_agent_spec_invalid_kind(self, kind):
        with pytest.raises(ValueError) as e:
            AgentsController.generate_agent_spec(
                name="test_agent",
                kind=kind,
                description="Test Agent Description",
            )

            assert "'kind' must be 'native' for agent creation" in str(e)

class TestAgentsControllerPublishOrUpdateAgents:
    def test_publish_or_update_native_agent_publish(self, native_agent_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as native_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client") as external_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client") as assistant_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_tool_client") as tool_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_agent") as publish_mock:
            
            native_client_mock.return_value = MockAgent(fake_agent=Agent(**native_agent_content))
            external_client_mock.return_value = MockAgent(skip_deref=True)
            assistant_client_mock.return_value = MockAgent(skip_deref=True)
            tool_client_mock.return_value = MockAgent()

            agent = Agent(**native_agent_content)
            agent.collaborators = [agent.name]

            agent.tools = []

            agents_controller.publish_or_update_agents(
                [agent]
            )

            publish_mock.assert_called_once()
    
    def test_publish_or_update_native_agent_update(self, native_agent_content):
        with patch("sys.exit") as sys_exit_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as native_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client") as external_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client") as assistant_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_tool_client") as tool_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.update_agent") as update_mock:
        
            native_client_mock.return_value = MagicMock(get_draft_by_name=MagicMock(return_value=[{
                "name": "test_native_agent",
                "id": "62562f01-5046-4e8f-b5b9-e91cdc17b5ce",
                "description": "Test Object for native agent",
            }]))
        
            external_client_mock.return_value = MagicMock(get_draft_by_name=MagicMock(return_value=[]))
            assistant_client_mock.return_value = MagicMock(get_draft_by_name=MagicMock(return_value=[]))  
            tool_client_mock.return_value = MockAgent()

            agent = Agent(**native_agent_content)
            agent.collaborators = ['test_native_agent'] 
            agent.tools = []
            agents_controller.publish_or_update_agents([agent])

            update_mock.assert_called_once()
        

            sys_exit_mock.assert_called_with(1)  


    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_conn_id_from_app_id")
    def test_publish_or_update_external_agent_publish(self, mock_get_conn_id, external_agent_content):
        with patch("sys.exit") as sys_exit_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as native_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client") as external_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client") as assistant_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_tool_client") as tool_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_agent") as publish_mock:
            
            # Mock get_conn_id_from_app_id to return a valid connection_id
            mock_get_conn_id.return_value = "mock-connection-id"

            native_client_mock.return_value = MagicMock(get_draft_by_name=MagicMock(return_value=[]))
            external_client_mock.return_value = MagicMock(get_draft_by_name=MagicMock(return_value=[]))
            assistant_client_mock.return_value = MagicMock(get_draft_by_name=MagicMock(return_value=[]))
            tool_client_mock.return_value = MockAgent()

            agent = ExternalAgent(**external_agent_content)

            agents_controller.publish_or_update_agents([agent])

            publish_mock.assert_called_once()
            sys_exit_mock.assert_not_called()

    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_conn_id_from_app_id")
    def test_publish_or_update_external_agent_update(self, mock_get_conn_id, external_agent_content):
        with patch("sys.exit") as sys_exit_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as native_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client") as assistant_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client") as external_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_tool_client") as tool_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.update_agent") as update_mock:
            
            # Mock get_conn_id_from_app_id to return a valid connection_id
            mock_get_conn_id.return_value = "mock-connection-id"

            native_client_mock.return_value = MagicMock(get_draft_by_name=MagicMock(return_value=[]))
            assistant_client_mock.return_value = MagicMock(get_draft_by_name=MagicMock(return_value=[]))
            external_client_mock.return_value = MagicMock(get_draft_by_name=MagicMock(return_value=[{
                "name": "test_external_agent",
                "id": "52101bd5-3395-47c8-adc8-506f4bd383ea",
                "type": "EXTERNAL",
                "description": "Mock description",
                "title": "Mock title",
                "api_url": "https://mock-api.com"
            }]))
            tool_client_mock.return_value = MockAgent()

            agent = ExternalAgent(**external_agent_content)

            agents_controller.publish_or_update_agents([agent])

            update_mock.assert_called_once()
            sys_exit_mock.assert_not_called()


    def test_publish_or_update_assistant_agent_publish(self, assistant_agent_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as native_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client") as assistant_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client") as external_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_agent") as publish_mock:
            
            native_client_mock.return_value = MagicMock(get_draft_by_name=MagicMock(return_value=[]))
            external_client_mock.return_value = MagicMock(get_draft_by_name=MagicMock(return_value=[]))
            assistant_client_mock.return_value = MockAgent()

            agent = AssistantAgent(**assistant_agent_content)

            agents_controller.publish_or_update_agents(
                [agent]
            )

            publish_mock.assert_called_once()
    
    @patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_conn_id_from_app_id")
    def test_publish_or_update_assistant_agent_update(self, mock_get_conn_id, assistant_agent_content):
        with patch("sys.exit") as sys_exit_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as native_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client") as assistant_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client") as external_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_tool_client") as tool_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.update_agent") as update_mock:
            
            # Mock get_conn_id_from_app_id to return a valid connection_id
            mock_get_conn_id.return_value = "mock-connection-id"
            
            native_client_mock.return_value = MagicMock(get_draft_by_name=MagicMock(return_value=[]))
            external_client_mock.return_value = MagicMock(get_draft_by_name=MagicMock(return_value=[]))
            assistant_client_mock.return_value = MagicMock(get_draft_by_name=MagicMock(return_value=[{
                "name": "test_assistant_agent",
                "id": "52101bd5-3395-47c8-adc8-506f4bd383ea",
                "type": "ASSISTANT",
                "description": "Mock description",
                "title": "Mock title",
                "api_url": "https://mock-api.com"
            }]))
            tool_client_mock.return_value = MockAgent()

            agent = AssistantAgent(**assistant_agent_content)

            agents_controller.publish_or_update_agents(
                [agent]
            )

            update_mock.assert_called_once()
            sys_exit_mock.assert_not_called()


class TestAgentsControllerPublishAgent:
    def test_publish_native_agent(self, native_agent_content, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as native_client_mock:
            agent = Agent(**native_agent_content)
            native_client_mock.return_value = MockAgent(expected_agent_spec=agent.model_dump())

            agents_controller.publish_agent(agent)

            native_client_mock.assert_called_once()
            
            captured = caplog.text

            assert f"Agent '{agent.name}' imported successfully" in captured
    
    def test_publish_external_agent(self, external_agent_content, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client") as external_client_mock:
            agent = ExternalAgent(**external_agent_content)
            external_client_mock.return_value = MockAgent(expected_agent_spec=agent.model_dump())

            agents_controller.publish_agent(agent)

            external_client_mock.assert_called_once()
            
            captured = caplog.text

            assert f"External Agent '{agent.name}' imported successfully" in captured

    def test_publish_assistant_agent(self, assistant_agent_content, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client") as assistant_client_mock:
            
            agent = AssistantAgent(**assistant_agent_content)
            assistant_client_mock.return_value = MockAgent(expected_agent_spec=agent.model_dump(by_alias=True))

            agents_controller.publish_agent(agent)

            assistant_client_mock.assert_called_once()
            
            captured = caplog.text

            assert f"Assistant Agent '{agent.name}' imported successfully" in captured

class TestAgentsControllerUpdateAgent:
    def test_update_native_agent(self, native_agent_content, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as native_client_mock:
            agent = Agent(**native_agent_content)
            native_client_mock.return_value = MockAgent(expected_agent_spec=agent.model_dump())

            agents_controller.update_agent(agent=agent, agent_id="test")

            native_client_mock.assert_called_once()
            
            captured = caplog.text

            assert f"Agent '{agent.name}' updated successfully" in captured
    
    def test_update_external_agent(self, external_agent_content, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client") as external_client_mock:
            agent = ExternalAgent(**external_agent_content)
            external_client_mock.return_value = MockAgent(expected_agent_spec=agent.model_dump())

            agents_controller.update_agent(agent=agent, agent_id="test")

            external_client_mock.assert_called_once()
            
            captured = caplog.text

            assert f"External Agent '{agent.name}' updated successfully" in captured

    def test_update_assistant_agent(self, assistant_agent_content, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client") as assistant_client_mock:
            
            agent = AssistantAgent(**assistant_agent_content)
            assistant_client_mock.return_value = MockAgent(expected_agent_spec=agent.model_dump(by_alias=True))

            agents_controller.update_agent(agent=agent, agent_id="test")

            assistant_client_mock.assert_called_once()
            
            captured = caplog.text

            assert f"Assistant Agent '{agent.name}' updated successfully" in captured

class MockConnectionClient:
    def __init__(self, get_response=[], get_draft_by_id_response=None):
        self.get_response = get_response
        self.get_draft_by_id_response = get_draft_by_id_response
    
    def get(self):
        return self.get_response
    
    def get_draft_by_id(self, connection_id):
        return self.get_draft_by_id_response

class TestListAgents:
    @mock.patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_tool_client')
    @mock.patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client')
    @mock.patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client')
    @mock.patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_agent_collaborator_names')
    @mock.patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_agent_tool_names')
    @mock.patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.get_connections_client')
    def test_list_agents(self, mock_get_connections_client, mock_get_agent_tool_names, mock_get_agent_collaborator_names, mock_get_external_client, mock_get_native_client, mock_get_tool_client):
        mock_get_connections_client.return_value = MockConnectionClient()
        # Mock responses for collaborator and tool names
    
        mock_get_agent_collaborator_names.return_value = ['Collaborator 1']
        mock_get_agent_tool_names.return_value = ['Test Tool']
        
        # Mock native client response (Native agents)
        mock_get_native_client.return_value.get.side_effect = [
            [{'id': 'agent1', 'name': 'Agent 1', 'description': 'Test agent 1', 'llm': 'llm_model_1', 'style': 'default', 'collaborators': ['collab_id_1'], 'tools': ['tool_id_1']}],
            [{'id': 'collab_id_1', 'name': 'Collaborator 1'}]
        ]
        
        # Mock external client response (External agents)
        mock_get_external_client.return_value.get.side_effect = [
            [{
                'id': 'external_agent1',
                'name': 'Agent 1',
                'title': 'Agent Title',
                'api_url': 'http://example.com/api',
                'description': 'Test agent 1',
                'llm': 'llm_model_1',
                'tags': ['tag1', 'tag2'],
                'chat_params': {},
                'nickname': 'agent_nickname',
                'app_id': 'app_id_example',
            }]
        ]
        
        # Mock tool client response
        mock_get_tool_client.return_value.get_draft_by_id.return_value = {'name': 'Test Tool'}
        
        # Test for Native agents
        agents_controller = AgentsController()
        agents_controller.list_agents(kind=AgentKind.NATIVE)
        
        assert mock_get_native_client.call_count == 1, f"Expected get_native_client to be called once, but got {mock_get_native_client.call_count}"
        assert mock_get_tool_client.call_count == 0, f"Expected get_tool_client to be called 0 times, but got {mock_get_tool_client.call_count}"
        
        # Test for External agents
        agents_controller.list_agents(kind=AgentKind.EXTERNAL)

        assert mock_get_external_client.call_count == 1, f"Expected get_external_client to be called once, but got {mock_get_external_client.call_count}"
        assert mock_get_tool_client.call_count == 0, f"Expected get_tool_client to be called 0 times, but got {mock_get_tool_client.call_count}"
        
        # Final assertions for mock return values
        assert mock_get_agent_collaborator_names.return_value == ['Collaborator 1'], "Collaborators list should be mocked correctly"
        assert mock_get_agent_tool_names.return_value == ['Test Tool'], "Tool names list should be mocked correctly"


class TestRemoveAgent:
    def test_remove_native_agent(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as native_client_mock:
            native_client_mock.return_value = MockAgent(already_existing=True)
            name = "test_agent"

            agents_controller.remove_agent(name=name, kind=AgentKind.NATIVE)

            captured = caplog.text

            assert f"Successfully removed agent {name}" in captured
    
    def test_remove_native_agent_non_existent(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as native_client_mock:
            native_client_mock.return_value = MockAgent(already_existing=False)
            name = "test_agent"

            agents_controller.remove_agent(name=name, kind=AgentKind.NATIVE)

            captured = caplog.text

            assert f"Successfully removed agent {name}" not in captured
            assert f"No agent named '{name}' found" in captured
    
    def test_remove_agent_invalid_kind(self, caplog):
            name = "test_agent"

            with pytest.raises(ValueError) as e:
                agents_controller.remove_agent(name=name, kind="test")
                

            captured = caplog.text
            assert f"Successfully removed agent {name}" not in captured

            assert "'kind' must be 'native'" in str(e)
    
    def test_remove_agent_http_error(self, caplog):
            with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as native_client_mock:
                name = "test_agent"

                expected_response = requests.models.Response()
                expected_response._content = str.encode("Expected Message")
                native_client_mock.side_effect = requests.HTTPError(response=expected_response)

                with pytest.raises(SystemExit) as e:
                    agents_controller.remove_agent(name=name, kind=AgentKind.NATIVE)
                    
                captured = caplog.text
                assert f"Successfully removed agent {name}" not in captured

                assert "Expected Message" in captured
