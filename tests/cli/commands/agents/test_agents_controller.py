import json
from unittest.mock import patch, mock_open, MagicMock
import pytest
import uuid
import requests
from unittest import mock

from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import DownloadResult, ToolKind
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
import logging

from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import (
    AgentsController,
    import_python_agent,
    create_agent_from_spec,
    parse_file,
    parse_create_native_args,
    parse_create_external_args,
    parse_create_assistant_args,
    get_conn_id_from_app_id,
    get_agent_details
    )
from ibm_watsonx_orchestrate.cli.commands.connections.connections_controller import get_app_id_from_conn_id

from ibm_watsonx_orchestrate.agent_builder.agents import AgentKind, AgentStyle, SpecVersion, Agent, ExternalAgent, AssistantAgent, AgentProvider, ExternalAgentAuthScheme
from ibm_watsonx_orchestrate.agent_builder.agents.webchat_customizations import AgentPrompt, StarterPrompts, WelcomeContent
from ibm_watsonx_orchestrate.client.connections.connections_client import GetConnectionResponse
from ibm_watsonx_orchestrate.agent_builder.agents.types import ExternalAgentConfig, AssistantAgentConfig
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient, AgentUpsertResponse
from ibm_watsonx_orchestrate.client.agents.external_agent_client import ExternalAgentClient
from ibm_watsonx_orchestrate.client.agents.assistant_agent_client import AssistantAgentClient
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.knowledge_bases.knowledge_base_client import KnowledgeBaseClient

from cli.commands.tools.test_tools_controller import MockToolClient

agents_controller = AgentsController()


@pytest.fixture(params=['normal', 'planner-join_tool', 'planner-structured_output'])
def native_agent_content(request) -> dict:
    param = request.param
    if param == 'planner-join_tool':
        return {
            "spec_version": SpecVersion.V1,
            "kind": AgentKind.NATIVE,
            "name": "test_native_agent",
            "description": "Test Object for planner agent",
            "llm": "test_llm",
            "style": AgentStyle.PLANNER,
            "custom_join_tool":"test_tool_3",
            "collaborators": [
                "test_agent_1",
                "test_agent_2"
            ],
            "tools": [
                "test_tool_1",
                "test_tool_2"
            ]
        }
    elif param == 'planner-structured_output':
        return {
            "spec_version": SpecVersion.V1,
            "kind": AgentKind.NATIVE,
            "name": "test_native_agent",
            "description": "Test Object for planner agent",
            "llm": "test_llm",
            "style": AgentStyle.PLANNER,
            "structured_output": {"type": "object", "additionalProperties": False, "properties": {}},
            "collaborators": [
                "test_agent_1",
                "test_agent_2"
            ],
            "tools": [
                "test_tool_1",
                "test_tool_2"
            ]
        }
        
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
        ],
        "guidelines": [
            {
                "action": "test_action_1",
                "condition": "test_condition_1",
                "tool": "test_tool_1"
            }
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

@pytest.fixture
def join_tool_spec():
    return {
        "name": "test_tool_1",
        "description": "Test Tool 1",
        "permission": "read_only",
        "binding": {
            "python": {
                "function": "test_function",
            }
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                    },
                },
                "task_results": {
                    "type": "object",
                },
                "original_query": {
                    "type": "string",
                },
            },
            "required": {"original_query", "task_results", "messages"},
        },
        "output_schema": {
            "type": "string",
        }
    }

@pytest.fixture
def agent_spec_with_starter_prompt():
    return {
        "spec_version": SpecVersion.V1,
        "kind": AgentKind.NATIVE,
        "style": "react",
        "name": "webchat_customization_test_agent",
        "llm": "watsonx/meta-llama/llama-3-1-70b-instruct",
        "description":  '',
        "instructions": '',
        "collaborators": [],
        "tools": [],
        "hidden": False,
        "starter_prompts": {
            "is_default_prompts": False,
            "prompts": [
                {
                    "id": "prompt_id_1",
                    "title": "Hello1",
                    "subtitle": "",
                    "prompt": "This is the msg for Hello1 prompt",
                    "state": "active"
                }
            ]
        }
    }

@pytest.fixture
def agent_spec_with_starter_prompts():
    return {
        "spec_version": SpecVersion.V1,
        "kind": AgentKind.NATIVE,
        "style": AgentStyle.REACT,
        "name": "webchat_customization_test_agent",
        "llm": "watsonx/meta-llama/llama-3-1-70b-instruct",
        "description":  '',
        "instructions": '',
        "collaborators": [],
        "tools": [],
        "hidden": False,
        "starter_prompts": {
            "is_default_prompts": False,
            "prompts": [
                {
                    "id": "prompt_id_1",
                    "title": "Hello1",
                    "subtitle": "",
                    "prompt": "This is the msg for Hello1 prompt",
                    "state": "active"
                },
                {
                    "id": "prompt_id_2",
                    "title": "Hello2",
                    "subtitle": "",
                    "prompt": "This is the msg for Hello2 prompt",
                    "state": "inactive"
                },
                {
                    "id": "prompt_id_3",
                    "title": "Hello3",
                    "subtitle": "",
                    "prompt": "This is the msg for Hello3 prompt",
                    "state": "active"
                },
                {
                    "id": "prompt_id_4",
                    "title": "Hello4",
                    "subtitle": "",
                    "prompt": "This is the msg for Hello4 prompt",
                    "state": "active"
                }
            ]
        }
    }

@pytest.fixture
def agent_spec_with_welcome_content():
    return {
        "spec_version": SpecVersion.V1,
        "kind": AgentKind.NATIVE,
        "style": AgentStyle.REACT,
        "name": "webchat_customization_test_agent",
        "llm": "watsonx/meta-llama/llama-3-1-70b-instruct",
        "description":  '',
        "instructions": '',
        "collaborators": [],
        "tools": [],
        "hidden": False,
        "welcome_content":{
            "welcome_message" : "Hello, I'm Agent Test. Welcome to Watson Orchestrate!",
            "description" : "This is not default",
            "is_default_message" : False
        }
    }

@pytest.fixture
def agent_spec_with_webchat_customizations():
    return {
        "spec_version": SpecVersion.V1,
        "kind": AgentKind.NATIVE,
        "style": AgentStyle.REACT,
        "name": "webchat_customization_test_agent",
        "llm": "watsonx/meta-llama/llama-3-1-70b-instruct",
        "description":  '',
        "instructions": '',
        "collaborators": [],
        "tools": [],
        "hidden": False,
        "starter_prompts": {
            "is_default_prompts": False,
            "prompts": [
                {
                    "id": "prompt_id_1",
                    "title": "Hello1",
                    "subtitle": "",
                    "prompt": "This is the msg for Hello1 prompt",
                    "state": "active"
                }
            ]
        },
        "welcome_content":{
            "welcome_message" : "Hello, I'm Agent Test. Welcome to Watson Orchestrate!",
            "description" : "This is not default",
            "is_default_message" : False
        }
    }

class MockSDKResponse:
    def __init__(self, response_obj):
        self.response_obj = response_obj

    def dumps_spec(self):
        return json.dumps(self.response_obj)

class MockAgent:
    def __init__(self, expected_name=None, expected_agent_spec=None, fake_agent=None, skip_deref=False, already_existing=False, return_get_drafts_by_ids=True, get_draft_by_name_response=None, creation_warning=None):
        self.expected_name = expected_name
        self.fake_agent = fake_agent
        self.skip_deref = skip_deref
        self.already_existing = already_existing
        self.expected_agent_spec = expected_agent_spec
        self.return_get_drafts_by_ids = return_get_drafts_by_ids
        self.get_draft_by_name_response = get_draft_by_name_response
        self.creation_warning = creation_warning
        self.base_endpoint = "/api/v1/agents"

    def delete(self, agent_id):
        pass
    
    def create(self, agent_spec):
        assert agent_spec == self.expected_agent_spec
        return AgentUpsertResponse(warning=self.creation_warning)

    def update(self, agent_id, agent_spec):
        assert agent_spec == self.expected_agent_spec
        return AgentUpsertResponse(warning=self.creation_warning)
    
    def _post(self, endpoint, data):
        """Mock _post method for publish_agent"""
        return {"id": "mock-agent-id"}
    
    def get(self):
        return [self.fake_agent]
    
    def get_drafts_by_names(self, agents):
        ids = []
        if not self.skip_deref:
            for agent in agents:
                ids.append({"name": agent, "id": str(uuid.uuid4())})
        return ids

    def get_draft_by_name(self, agent):
        if self.get_draft_by_name_response:
            return self.get_draft_by_name_response
        if self.already_existing:
            return [{"name": agent, "id": str(uuid.uuid4())}]
        return []

    def get_drafts_by_ids(self, agent_ids):
        response = []
        if not self.return_get_drafts_by_ids:
            return response
        for id in agent_ids:
            response.append({"id": id, "name": str(uuid.uuid4())})
        return response

    def get_draft_by_id(self, agent_id):
        return self.fake_agent
    
    def get_by_id(self, knowledge_base_id):
        return self.fake_agent

class TestImportPythonAgent:
    def test_import_python_agent(self, native_agent_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.import_python_tool") as python_tool_import_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.import_python_knowledge_base") as python_knowledge_base_import_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.inspect.getmembers") as getmembers_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.importlib.import_module") as import_module_mock:
            
            sample_native_agent = Agent(**native_agent_content)
            # sample_external_agent = ExternalAgent(**external_agent_content)
            # sample_assitant_agent = AssistantAgent(**assistant_agent_content)

            getmembers_mock.return_value = [(None, sample_native_agent)]

            agents = import_python_agent("test.py")

            python_tool_import_mock.assert_called_once_with("test.py")
            python_knowledge_base_import_mock.assert_called_once_with("test.py")
            import_module_mock.assert_called_with("test")
            getmembers_mock.assert_called()

            assert len(agents) == 1

    def test_import_python_external_agent(self, external_agent_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.import_python_tool") as python_tool_import_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.import_python_knowledge_base") as python_knowledge_base_import_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.inspect.getmembers") as getmembers_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.importlib.import_module") as import_module_mock:
            
            sample_external_agent = ExternalAgent(**external_agent_content)
            getmembers_mock.return_value = [(None, sample_external_agent)]

            agents = import_python_agent("test.py")

            python_tool_import_mock.assert_called_once_with("test.py")
            python_knowledge_base_import_mock.assert_called_once_with("test.py")
            import_module_mock.assert_called_with("test")
            getmembers_mock.assert_called()

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

    def test_create_assistant_agent_from_spec(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AssistantAgent.from_spec") as mock:
            create_agent_from_spec("test.yaml", AgentKind.ASSISTANT)

            mock.assert_called_once_with("test.yaml")

    def test_create_invalid_agent_from_spec(self):
        with pytest.raises(BadRequest) as e:
            create_agent_from_spec("test.yaml", "fake")

            assert "'kind' must be either 'native'" in str(e)



class TestParseFile:
    def test_parse_file_yaml(self, native_agent_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.Agent.from_spec") as from_spec_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.safe_open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.yaml.load") as mock_loader:
            
            mock_loader.return_value = native_agent_content

            parse_file("test.yaml")

            from_spec_mock.assert_called_once_with("test.yaml")
            mock_file.assert_called_once_with("test.yaml", "r")
            mock_loader.assert_called_once()

    def test_parse_file_json(self, native_agent_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.Agent.from_spec") as from_spec_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.safe_open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.json.load") as mock_loader:
            
            mock_loader.return_value = native_agent_content

            parse_file("test.json")

            from_spec_mock.assert_called_once_with("test.json")
            mock_file.assert_called_once_with("test.json", "r")
            mock_loader.assert_called_once()

    def test_parse_file_yaml_external(self, external_agent_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ExternalAgent.from_spec") as from_spec_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.safe_open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.yaml.load") as mock_loader:
            
            mock_loader.return_value = external_agent_content

            parse_file("test.yaml")

            from_spec_mock.assert_called_once_with("test.yaml")
            mock_file.assert_called_once_with("test.yaml", "r")
            mock_loader.assert_called_once()

    def test_parse_file_json_external(self, external_agent_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ExternalAgent.from_spec") as from_spec_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.safe_open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.json.load") as mock_loader:
            
            mock_loader.return_value = external_agent_content

            parse_file("test.json")

            from_spec_mock.assert_called_once_with("test.json")
            mock_file.assert_called_once_with("test.json", "r")
            mock_loader.assert_called_once()

    def test_parse_file_py(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.import_python_tool") as python_tool_import_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.import_python_knowledge_base") as python_knowledge_base_import_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.inspect.getmembers") as getmembers_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.importlib.import_module") as import_module_mock:

            getmembers_mock.return_value = []
            agents = parse_file("test.py")

            python_tool_import_mock.assert_called_once_with("test.py")
            python_knowledge_base_import_mock.assert_called_once_with("test.py")
            import_module_mock.assert_called_with("test")
            getmembers_mock.assert_called()

            assert len(agents) == 0

    def test_parse_file_invalid(self):
        with pytest.raises(BadRequest) as e:
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

class TestParseCreateAssistantArgs:
    def test_parse_create_assistant_args(self):
        parsed_args = parse_create_assistant_args(
            name="test_assistant_agent",
            kind=AgentKind.ASSISTANT,
            description="Test Assistant Agent Description",
            title="Test Assistant Agent",
            tags=["tag1", "tag2"],
            config='{"api_version": "2021-11-27", "assistant_id": "test_id", "crn": "test_crn", "instance_url": "test_instance_url", "environment_id": "test_env", "app_id": "test_app_id"}',
            nickname="some_nickname",
        )

        assert parsed_args["name"] == "test_assistant_agent"
        assert parsed_args["kind"] == AgentKind.ASSISTANT
        assert parsed_args["description"] == "Test Assistant Agent Description"
        assert parsed_args["title"] == "Test Assistant Agent"
        assert parsed_args["tags"] == ["tag1", "tag2"]
        assert parsed_args["config"] == '{"api_version": "2021-11-27", "assistant_id": "test_id", "crn": "test_crn", "instance_url": "test_instance_url", "environment_id": "test_env", "app_id": "test_app_id"}'
        assert parsed_args["nickname"] == "some_nickname"

class TestGetConnIdFromAppId:
    mock_app_id = "test_app_id"
    mock_conn_id = "test_conn_id"

    def test_get_conn_id_from_app_id(self):
        mock_connection_client = MockConnectionClient(
            get_draft_by_app_id_reponse=GetConnectionResponse(
                connection_id=self.mock_conn_id
            )
        )
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_get_connection_client:
            mock_get_connection_client.return_value = mock_connection_client

            response = get_conn_id_from_app_id(self.mock_app_id)

            assert response == self.mock_conn_id 
    
    def test_get_conn_id_from_app_id_no_connections(self, caplog):
        mock_connection_client = MockConnectionClient()
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_get_connection_client:
            mock_get_connection_client.return_value = mock_connection_client

            with pytest.raises(SystemExit):
                get_conn_id_from_app_id(self.mock_app_id)

            
            captured = caplog.text

            assert f"No connection exists with the app-id '{self.mock_app_id}'" in captured 

class TestGetAppIdFromConnId:
    mock_app_id = "test_app_id"
    mock_conn_id = "test_conn_id"

    def test_get_app_id_from_conn_id(self):
        mock_connection_client = MockConnectionClient(
            get_draft_by_id_response=self.mock_app_id
        )
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_get_connection_client:
            mock_get_connection_client.return_value = mock_connection_client

            response = get_app_id_from_conn_id(self.mock_conn_id)

            assert response == self.mock_app_id 
    
    def test_get_app_id_from_conn_id_no_connections(self, caplog):
        mock_connection_client = MockConnectionClient()
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_get_connection_client:
            mock_get_connection_client.return_value = mock_connection_client

            with pytest.raises(SystemExit):
                get_app_id_from_conn_id(self.mock_conn_id)

            
            captured = caplog.text

            assert f"No connection exists with the connection id '{self.mock_conn_id}'" in captured 

class TestGetAgentDetails:
    mock_agent_name = "test_agent"

    def test_get_agent_details(self):
        mock_agent_client = MockAgent(already_existing=True)

        response = get_agent_details(name=self.mock_agent_name, client = mock_agent_client)

        assert response.get("name") == self.mock_agent_name
    
    def test_get_agent_details_no_agent(self, caplog):
        mock_agent_client = MockAgent(already_existing=False)

        with pytest.raises(SystemExit):
            get_agent_details(name=self.mock_agent_name, client = mock_agent_client)

        captured = caplog.text

        assert f"No agents with the name '{self.mock_agent_name}' found." in captured
    
    def test_get_agent_details_multiple_agents(self, caplog):
        mock_agent_client = MagicMock(get_draft_by_name=MagicMock(return_value=[{}, {}]))

        with pytest.raises(SystemExit):
            get_agent_details(name=self.mock_agent_name, client = mock_agent_client)

        captured = caplog.text

        assert f"Multiple agents with the name '{self.mock_agent_name}' found." in captured

class TestAgentsControllerGetClients:
    def test_get_native_client(self):
        ac = AgentsController()
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.instantiate_client") as mock_instantiate_client:
            mock_instantiate_client.return_value = AgentClient("test")
            ac.get_native_client()
        assert isinstance(ac.native_client, AgentClient)
    
    def test_get_external_client(self):
        ac = AgentsController()
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.instantiate_client") as mock_instantiate_client:
            mock_instantiate_client.return_value = ExternalAgentClient("test")
            ac.get_external_client()
        assert isinstance(ac.external_client, ExternalAgentClient)
    
    def test_get_assistant_client(self):
        ac = AgentsController()
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.instantiate_client") as mock_instantiate_client:
            mock_instantiate_client.return_value = AssistantAgentClient("test")
            ac.get_assistant_client()
        assert isinstance(ac.assistant_client, AssistantAgentClient)
    
    def test_get_tool_client(self):
        ac = AgentsController()
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.instantiate_client") as mock_instantiate_client:
            mock_instantiate_client.return_value = ToolClient("test")
            ac.get_tool_client()
        assert isinstance(ac.tool_client, ToolClient)
    
    def test_get_knowledge_base_client(self):
        ac = AgentsController()
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.instantiate_client") as mock_instantiate_client:
            mock_instantiate_client.return_value = KnowledgeBaseClient("test")
            ac.get_knowledge_base_client()
        assert isinstance(ac.knowledge_base_client, KnowledgeBaseClient)

class TestAgentsControllerGenerateAgentSpec:
    mock_agent_name = "test_agent"
    mock_agent_description = "Test Agent Description"
    mock_agent_title = "Test Agent Title"
    mock_agent_tags = ["tag1", "tag2"]
    mock_nickname = "test_nickname"

    def test_generate_native_agent_spec(self):
        mock_llm = "test_llm"
        mock_collaborators = ["agent1", "    "]
        mock_tools = ["  tool1  ", "tool2"]

        agent = AgentsController.generate_agent_spec(
            name=self.mock_agent_name,
            kind=AgentKind.NATIVE,
            description=self.mock_agent_description,
            llm=mock_llm,
            style=AgentStyle.REACT,
            collaborators=mock_collaborators,
            tools=mock_tools
        )
        
        assert agent.name == self.mock_agent_name
        assert agent.kind == AgentKind.NATIVE
        assert agent.description == self.mock_agent_description
        assert agent.llm == mock_llm
        assert agent.style == AgentStyle.REACT
        assert agent.collaborators == ["agent1"]
        assert agent.tools == ["tool1", "tool2"]
    
    def test_generate_external_agent_spec(self):
        mock_api_url = "https://someurl.com"
        mock_chat_params = {"stream": True}
        mock_config = {"hidden": False, "enable_cot": False}
        mock_app_id = "mock_app_id"
        mock_conn_id = "mock_conn_id"

        mock_connection_client = MockConnectionClient(
            get_draft_by_app_id_reponse=GetConnectionResponse(
                connection_id=mock_conn_id
            )
        )
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_get_connection_client:
            mock_get_connection_client.return_value = mock_connection_client
            agent = AgentsController.generate_agent_spec(
                name=self.mock_agent_name,
                kind=AgentKind.EXTERNAL,
                provider = AgentProvider.EXT_CHAT,
                auth_scheme = ExternalAgentAuthScheme.API_KEY,
                description=self.mock_agent_description,
                title=self.mock_agent_title,
                api_url=mock_api_url,
                tags=self.mock_agent_tags,
                chat_params=mock_chat_params,
                config=mock_config,
                nickname=self.mock_nickname,
                app_id=mock_app_id
            )
        
        assert agent.name == self.mock_agent_name
        assert agent.kind == AgentKind.EXTERNAL
        assert agent.provider == AgentProvider.EXT_CHAT
        assert agent.auth_scheme == ExternalAgentAuthScheme.API_KEY
        assert agent.description == self.mock_agent_description
        assert agent.title == self.mock_agent_title
        assert agent.api_url == mock_api_url
        assert agent.tags == self.mock_agent_tags
        assert agent.chat_params == mock_chat_params
        assert agent.config == ExternalAgentConfig(**mock_config)
        assert agent.nickname == self.mock_nickname
        assert agent.app_id == mock_app_id
    
    def test_generate_assistant_agent_spec(self):
        mock_config = {"api_version": "2021-11-27", "assistant_id": "test_id", "crn": "test_crn", "instance_url": "test_instance_url", "environment_id": "test_env", "app_id": "test_app_id"}

        agent = AgentsController.generate_agent_spec(
            name=self.mock_agent_name,
            kind=AgentKind.ASSISTANT,
            description=self.mock_agent_description,
            title=self.mock_agent_title,
            tags=self.mock_agent_tags,
            config=mock_config,
            nickname=self.mock_nickname,
        )
        
        assert agent.name == self.mock_agent_name
        assert agent.kind == AgentKind.ASSISTANT
        assert agent.description == self.mock_agent_description
        assert agent.title == self.mock_agent_title
        assert agent.tags == self.mock_agent_tags
        assert agent.config == AssistantAgentConfig(**mock_config)
        assert agent.nickname == self.mock_nickname
        

    @pytest.mark.parametrize(
            "kind",
            [
                "invalid",
                "fake"
            ]
    )
    def test_generate_agent_spec_invalid_kind(self, kind):
        with pytest.raises(ValueError) as e:
            AgentsController.generate_agent_spec(
                name="test_agent",
                kind=kind,
                description="Test Agent Description",
            )

        assert "'kind' must be 'native' or 'external' for agent creation" in str(e)

class TestAgentsControllerGetAllAgents:
    mock_agent_name = "test_agent"
    mock_agent_id= "1234"

    def test_get_all_agents(self):
        mock_client = MockAgent(fake_agent = {
            "name": self.mock_agent_name,
            "id": self.mock_agent_id
        })

        response = agents_controller.get_all_agents(client = mock_client)

        assert response[self.mock_agent_name] == self.mock_agent_id

class TestAgentsControllerPublishOrUpdateAgents:
    def test_publish_or_update_native_agent_publish(self, native_agent_content, join_tool_spec):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as native_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client") as external_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client") as assistant_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_tool_client") as tool_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.publish_agent") as publish_mock:

            native_client_mock.return_value = MockAgent(fake_agent=Agent(**native_agent_content))
            external_client_mock.return_value = MockAgent(skip_deref=True)
            assistant_client_mock.return_value = MockAgent(skip_deref=True)
            tool_client_mock.return_value = MockToolClient(get_draft_by_id_response=join_tool_spec)

            agent = Agent(**native_agent_content)
            agent.collaborators = [agent.name]

            agent.tools = []

            agents_controller.publish_or_update_agents(
                [agent]
            )

            publish_mock.assert_called_once()

    def test_publish_or_update_native_agent_update(self, native_agent_content, join_tool_spec):
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
            
            tool_client_mock.return_value = MockToolClient(get_draft_by_id_response=join_tool_spec)

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
                "api_url": "https://mock-api.com",
                "hidden": False,
                "enable_cot": False
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
            native_client_mock.return_value = MockAgent(expected_agent_spec=agent.model_dump(exclude_none=True))

            agents_controller.publish_agent(agent)

            native_client_mock.assert_called_once()
            
            captured = caplog.text

            assert f"Agent '{agent.name}' imported successfully" in captured
    
    def test_publish_external_agent(self, external_agent_content, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client") as external_client_mock:
            agent = ExternalAgent(**external_agent_content)
            external_client_mock.return_value = MockAgent(expected_agent_spec=agent.model_dump(exclude_none=True))

            agents_controller.publish_agent(agent)

            external_client_mock.assert_called_once()
            
            captured = caplog.text

            assert f"External Agent '{agent.name}' imported successfully" in captured

    def test_publish_assistant_agent(self, assistant_agent_content, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client") as assistant_client_mock:
            
            agent = AssistantAgent(**assistant_agent_content)
            assistant_client_mock.return_value = MockAgent(expected_agent_spec=agent.model_dump(exclude_none=True, by_alias=True))

            agents_controller.publish_agent(agent)

            assistant_client_mock.assert_called_once()
            
            captured = caplog.text

            assert f"Assistant Agent '{agent.name}' imported successfully" in captured

class TestAgentsControllerUpdateAgent:
    def test_update_native_agent(self, native_agent_content, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as native_client_mock:
            agent = Agent(**native_agent_content)
            native_client_mock.return_value = MockAgent(expected_agent_spec=agent.model_dump(exclude_none=True))

            agents_controller.update_agent(agent=agent, agent_id="test")

            native_client_mock.assert_called_once()
            
            captured = caplog.text

            assert f"Agent '{agent.name}' updated successfully" in captured
    
    def test_update_external_agent(self, external_agent_content, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client") as external_client_mock:
            agent = ExternalAgent(**external_agent_content)
            external_client_mock.return_value = MockAgent(expected_agent_spec=agent.model_dump(exclude_none=True))

            agents_controller.update_agent(agent=agent, agent_id="test")

            external_client_mock.assert_called_once()
            
            captured = caplog.text

            assert f"External Agent '{agent.name}' updated successfully" in captured

    def test_update_assistant_agent(self, assistant_agent_content, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client") as assistant_client_mock:
            
            agent = AssistantAgent(**assistant_agent_content)
            assistant_client_mock.return_value = MockAgent(expected_agent_spec=agent.model_dump(exclude_none=True, by_alias=True))

            agents_controller.update_agent(agent=agent, agent_id="test")

            assistant_client_mock.assert_called_once()
            
            captured = caplog.text

            assert f"Assistant Agent '{agent.name}' updated successfully" in captured

class MockConnectionClient:
    def __init__(self, get_response=[], get_draft_by_id_response=None, get_draft_by_app_id_reponse=None):
        self.get_response = get_response
        self.get_draft_by_id_response = get_draft_by_id_response
        self.get_draft_by_app_id_reponse = get_draft_by_app_id_reponse
    
    def get(self):
        return self.get_response
    
    def get_draft_by_id(self, conn_id):
        return self.get_draft_by_id_response
    
    def get_draft_by_app_id(self, app_id):
        return self.get_draft_by_app_id_reponse

class TestListAgents:
    @mock.patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_tool_client')
    @mock.patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_knowledge_base_client')
    @mock.patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client')
    @mock.patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client')
    @mock.patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client')
    @mock.patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_agent_collaborator_names')
    @mock.patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_agent_tool_names')
    @mock.patch('ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client')
    @mock.patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_agent_knowledge_base_names')
    def test_list_agents(self, get_agent_knowledge_base_names, mock_get_connections_client, mock_get_agent_tool_names, mock_get_agent_collaborator_names, mock_get_assistant_client, mock_get_external_client, mock_get_native_client, mock_get_knowledge_base_client, mock_get_tool_client):
        mock_get_connections_client.return_value = MockConnectionClient()
        
        # Mock responses for collaborator and tool names
        mock_get_agent_collaborator_names.return_value = ['Collaborator 1']
        mock_get_agent_tool_names.return_value = ['Test Tool']
        get_agent_knowledge_base_names.return_value = ['Test Knowledge Base']
        
        # Mock native client response (Native agents)
        mock_get_native_client.return_value.get.side_effect = [
            [{'id': 'agent1', 'name': 'Agent 1', 'description': 'Test agent 1', 'llm': 'llm_model_1', 'style': 'default', 'collaborators': ['collab_id_1'], 'tools': ['tool_id_1'], 'knowledge_base': ['knowledge_base_id_1']}],
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
                'hidden': False,
                'enable_cot': False
            }]
        ]

        mock_get_assistant_client.return_value.get.side_effect = [
            [{
                'id': 'external_agent1',
                'name': 'Agent 1',
                'title': 'Agent Title',
            }]
        ]
        
        # Mock tool client response
        mock_get_tool_client.return_value.get_draft_by_id.return_value = {'name': 'Test Tool'}

        # Mock knowledge base client
        mock_get_knowledge_base_client.return_value.get_by_id.return_value = {'name': 'Test Knowledge Base'}
        
        # Test for Native agents
        agents_controller = AgentsController()
        agents_controller.list_agents(kind=AgentKind.NATIVE)
        
        assert mock_get_native_client.call_count == 2, f"Expected get_native_client to be called once, but got {mock_get_native_client.call_count}"
        assert mock_get_tool_client.call_count == 1, f"Expected get_tool_client to be called 0 times, but got {mock_get_tool_client.call_count}"
        assert mock_get_knowledge_base_client.call_count == 1, f"Expected get_knowledge_base_client to be called 0 times, but got {mock_get_knowledge_base_client.call_count}"
        
        mock_get_tool_client.reset_mock()
        mock_get_knowledge_base_client.reset_mock()
        # Test for External agents
        agents_controller.list_agents(kind=AgentKind.EXTERNAL)

        assert mock_get_external_client.call_count == 2, f"Expected get_external_client to be called once, but got {mock_get_external_client.call_count}"
        assert mock_get_tool_client.call_count == 0, f"Expected get_tool_client to be called 0 times, but got {mock_get_tool_client.call_count}"
        assert mock_get_knowledge_base_client.call_count == 0, f"Expected get_knowledge_base_client to be called 0 times, but got {mock_get_knowledge_base_client.call_count}"
        
        # Final assertions for mock return values
        assert mock_get_agent_collaborator_names.return_value == ['Collaborator 1'], "Collaborators list should be mocked correctly"
        assert mock_get_agent_tool_names.return_value == ['Test Tool'], "Tool names list should be mocked correctly"
        assert get_agent_knowledge_base_names.return_value == ['Test Knowledge Base'], "Knowledge Base names list should be mocked correctly"


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

            with pytest.raises(BadRequest) as e:
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

class TestAgentsControllerGetSpecFileContent:
    def test_get_spec_file_content_native_agent(self, native_agent_content):
        ac = AgentsController()
        ac.native_client = MockAgent()
        ac.external_client = MockAgent(return_get_drafts_by_ids=False)
        ac.assistant_client = MockAgent(return_get_drafts_by_ids=False)
        ac.tool_client = MockAgent()

        agent = Agent(**native_agent_content)

        spec_file_content = ac.get_spec_file_content(agent)
        
        assert spec_file_content["spec_version"] == native_agent_content["spec_version"]
        assert spec_file_content["name"] == native_agent_content["name"]
        assert spec_file_content["kind"] == native_agent_content["kind"]
        assert spec_file_content["description"] == native_agent_content["description"]
        assert spec_file_content["llm"] == native_agent_content["llm"]
        assert spec_file_content["style"] == native_agent_content["style"]

    def test_get_spec_file_content_external_agent(self, external_agent_content):
        ac = AgentsController()
        ac.native_client = MockAgent()
        ac.external_client = MockAgent(return_get_drafts_by_ids=False)
        ac.assistant_client = MockAgent(return_get_drafts_by_ids=False)
        ac.tool_client = MockAgent()

        agent = ExternalAgent(**external_agent_content)

        mock_connection_client = MockConnectionClient(
            get_draft_by_id_response="testing"
        )
        with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_get_connection_client:
            mock_get_connection_client.return_value = mock_connection_client

            spec_file_content = ac.get_spec_file_content(agent)
        
        assert spec_file_content["spec_version"] == external_agent_content["spec_version"]
        assert spec_file_content["name"] == external_agent_content["name"]
        assert spec_file_content["kind"] == external_agent_content["kind"]
        assert spec_file_content["description"] == external_agent_content["description"]
        assert spec_file_content["title"] == external_agent_content["title"]
        assert spec_file_content["nickname"] == external_agent_content["nickname"]


    def test_get_spec_file_content_assistant_agent(self, assistant_agent_content):
        ac = AgentsController()
        ac.native_client = MockAgent()
        ac.external_client = MockAgent(return_get_drafts_by_ids=False)
        ac.assistant_client = MockAgent(return_get_drafts_by_ids=False)
        ac.tool_client = MockAgent()

        agent = AssistantAgent(**assistant_agent_content)

        spec_file_content = ac.get_spec_file_content(agent)
        
        assert spec_file_content["spec_version"] == assistant_agent_content["spec_version"]
        assert spec_file_content["name"] == assistant_agent_content["name"]
        assert spec_file_content["kind"] == assistant_agent_content["kind"]
        assert spec_file_content["description"] == assistant_agent_content["description"]
        assert spec_file_content["title"] == assistant_agent_content["title"]
        assert spec_file_content["nickname"] == assistant_agent_content["nickname"]

class TestAgentsControllerGetAgent:
    mock_agent_name = "test_agent"

    @pytest.mark.parametrize(
            ("kind", "expected_agent_type"),
            [
                (AgentKind.NATIVE, Agent),
                (AgentKind.EXTERNAL, ExternalAgent),
                (AgentKind.ASSISTANT, AssistantAgent),
            ]
    )
    def test_get_agent(self, kind, expected_agent_type, native_agent_content, external_agent_content, assistant_agent_content):
        ac = AgentsController()
        ac.native_client = MockAgent(get_draft_by_name_response=[native_agent_content])
        ac.external_client = MockAgent(get_draft_by_name_response=[external_agent_content])
        ac.assistant_client = MockAgent(get_draft_by_name_response=[assistant_agent_content])

        agent = ac.get_agent(name=self.mock_agent_name, kind=kind)

        assert isinstance(agent, expected_agent_type)

class TestAgentsControllerGetAgentById:
    mock_agent_id = "1234"

    def test_get_agent_by_id_native(self, native_agent_content):
        ac = AgentsController()
        ac.native_client = MockAgent(fake_agent=native_agent_content)
        ac.external_client = MockAgent()
        ac.assistant_client = MockAgent()

        agent = ac.get_agent_by_id(self.mock_agent_id)

        assert isinstance(agent, Agent)
    
    def test_get_agent_by_id_external(self, external_agent_content):
        ac = AgentsController()
        ac.native_client = MockAgent()
        ac.external_client = MockAgent(fake_agent=external_agent_content)
        ac.assistant_client = MockAgent()

        agent = ac.get_agent_by_id(self.mock_agent_id)

        assert isinstance(agent, ExternalAgent)
    
    def test_get_agent_by_id_assistant(self, assistant_agent_content):
        ac = AgentsController()
        ac.native_client = MockAgent()
        ac.external_client = MockAgent()
        ac.assistant_client = MockAgent(fake_agent=assistant_agent_content)

        agent = ac.get_agent_by_id(self.mock_agent_id)

        assert isinstance(agent, AssistantAgent)

class TestAgentsControllerExportAgent:
    mock_agent_name = "test_agent"
    mock_zip_file_path = "test_mock_zip.zip"
    mock_yaml_file_path = "test_mock_yaml.yaml"
    mock_kb_name = "test_kb"

    @pytest.mark.parametrize(
            "kind",
            [
                AgentKind.NATIVE,
                AgentKind.EXTERNAL,
                AgentKind.ASSISTANT
            ]
    )
    def test_export_agent(self, caplog, kind, native_agent_content, external_agent_content, assistant_agent_content):
        native_agent_content["knowledge_base"] = ["kb_1"]

        ac = AgentsController()
        ac.native_client = MockAgent(get_draft_by_name_response=[native_agent_content], return_get_drafts_by_ids=False)
        ac.external_client = MockAgent(get_draft_by_name_response=[external_agent_content], return_get_drafts_by_ids=False)
        ac.assistant_client = MockAgent(get_draft_by_name_response=[assistant_agent_content], fake_agent=assistant_agent_content)
        ac.tool_client = MockAgent()
        ac.knowledge_base_client = MockAgent(fake_agent={"name": self.mock_kb_name})

        mock_connection_client = MockConnectionClient(
            get_draft_by_id_response="testing"
        )

        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ToolsController") as mock_tools_controller, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.KnowledgeBaseController") as mock_kb_controller, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ModelsController") as mock_models_controller, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.zipfile.ZipFile") as mock_zipfile, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_get_connection_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.export_connection") as mock_export_connection:
            
            mock_get_connection_client.return_value = mock_connection_client

            mock_tools_controller.return_value = MagicMock(
                download_tool=MagicMock(return_value=DownloadResult(
                    kind=ToolKind.python,
                    content=b"abc"
                )))
            
            mock_kb_controller.return_value = MagicMock(
                knowledge_base_export=MagicMock()
            )

            mock_models_controller.return_value = MagicMock(
                get_models_client=MagicMock()
            )

            mock_zipfile().__enter__().infolist.return_value = [MagicMock()]

            ac.export_agent(
                name = self.mock_agent_name,
                kind = kind,
                output_path = self.mock_zip_file_path
            )
        
        captured = caplog.text

        assert f"Exporting agent definition for '{self.mock_agent_name}'" in captured
        assert f"Successfully wrote agents and tools to '{self.mock_zip_file_path}'" in captured

    @pytest.mark.parametrize(
            "kind",
            [
                AgentKind.NATIVE,
                AgentKind.EXTERNAL,
                AgentKind.ASSISTANT
            ]
    )
    def test_export_agent_agent_only(self, caplog, kind, native_agent_content, external_agent_content, assistant_agent_content):

        ac = AgentsController()
        ac.native_client = MockAgent(get_draft_by_name_response=[native_agent_content], return_get_drafts_by_ids=False)
        ac.external_client = MockAgent(get_draft_by_name_response=[external_agent_content], return_get_drafts_by_ids=False)
        ac.assistant_client = MockAgent(get_draft_by_name_response=[assistant_agent_content], fake_agent=assistant_agent_content)
        ac.tool_client = MockAgent()

        mock_connection_client = MockConnectionClient(
            get_draft_by_id_response="testing"
        )

        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.yaml") as mock_yaml, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_get_connection_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.safe_open", mock_open()) as mock_file:
            
            mock_get_connection_client.return_value = mock_connection_client
            mock_yaml.return_value = MagicMock(dump=MagicMock())

            ac.export_agent(
                name = self.mock_agent_name,
                kind = kind,
                output_path = self.mock_yaml_file_path,
                agent_only_flag=True
            )
        
        captured = caplog.text
        mock_file.assert_called_with(self.mock_yaml_file_path, "w")
        assert f"Exported agent definition for '{self.mock_agent_name}' to '{self.mock_yaml_file_path}'" in captured

    def test_export_agent_existing_agent(self, caplog, native_agent_content, external_agent_content, assistant_agent_content):
        ac = AgentsController()
        ac.native_client = MockAgent(get_draft_by_name_response=[native_agent_content], return_get_drafts_by_ids=False)
        ac.external_client = MockAgent(get_draft_by_name_response=[external_agent_content], return_get_drafts_by_ids=False)
        ac.assistant_client = MockAgent(get_draft_by_name_response=[assistant_agent_content], fake_agent=assistant_agent_content)
        ac.tool_client = MockAgent()

        mock_connection_client = MockConnectionClient(
            get_draft_by_id_response="testing"
        )

        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ToolsController") as mock_tools_controller, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.zipfile.ZipFile") as mock_zipfile, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.check_file_in_zip") as mock_zip_check, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_get_connection_client:
            
            mock_get_connection_client.return_value = mock_connection_client
            mock_zip_check.return_value = True
            mock_tools_controller.return_value = MagicMock(
                download_tool=MagicMock(return_value=DownloadResult(
                    kind=ToolKind.python,
                    content=b"abc"
                )))

            ac.export_agent(
                name = self.mock_agent_name,
                kind = AgentKind.NATIVE,
                output_path = self.mock_zip_file_path
            )
        
        captured = caplog.text

        assert f"Exporting agent definition for '{self.mock_agent_name}'" in captured
        assert f"Skipping {native_agent_content.get('name')}, agent with that name already exists in the output folder" in captured
    
    def test_export_agent_existing_tool(self, caplog, native_agent_content, external_agent_content, assistant_agent_content):
        ac = AgentsController()
        ac.native_client = MockAgent(get_draft_by_name_response=[native_agent_content], return_get_drafts_by_ids=False)
        ac.external_client = MockAgent(get_draft_by_name_response=[external_agent_content], return_get_drafts_by_ids=False)
        ac.assistant_client = MockAgent(get_draft_by_name_response=[assistant_agent_content], fake_agent=assistant_agent_content)
        ac.tool_client = MockAgent()

        mock_connection_client = MockConnectionClient(
            get_draft_by_id_response="testing"
        )

        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ToolsController") as mock_tools_controller, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.zipfile.ZipFile") as mock_zipfile, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ModelsController") as mock_models_controller, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.check_file_in_zip") as mock_zip_check, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_get_connection_client:
            
            mock_get_connection_client.return_value = mock_connection_client
            mock_zip_check.side_effect = lambda file_path, zip_file : True if "tools" in file_path else False
            mock_tools_controller.return_value = MagicMock(
                download_tool=MagicMock(return_value=DownloadResult(
                    kind=ToolKind.python,
                    content=b"abc"
                )))
            
            mock_models_controller.return_value = MagicMock(
                get_models_client=MagicMock()
            )

            ac.export_agent(
                name = self.mock_agent_name,
                kind = AgentKind.NATIVE,
                output_path = self.mock_zip_file_path
            )
        
        captured = caplog.text

        assert f"Exporting agent definition for '{self.mock_agent_name}'" in captured
        assert f"Skipping {native_agent_content.get('name')}, agent with that name already exists in the output folder" not in captured
        assert f"Exporting tool" not in captured
        assert f"Successfully wrote agents and tools to '{self.mock_zip_file_path}'" in captured
    
    def test_export_agent_no_tool(self, caplog, native_agent_content, external_agent_content, assistant_agent_content):
        ac = AgentsController()
        ac.native_client = MockAgent(get_draft_by_name_response=[native_agent_content], return_get_drafts_by_ids=False)
        ac.external_client = MockAgent(get_draft_by_name_response=[external_agent_content], return_get_drafts_by_ids=False)
        ac.assistant_client = MockAgent(get_draft_by_name_response=[assistant_agent_content], fake_agent=assistant_agent_content)
        ac.tool_client = MockAgent()

        mock_connection_client = MockConnectionClient(
            get_draft_by_id_response="testing"
        )

        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ToolsController") as mock_tools_controller, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.zipfile.ZipFile") as mock_zipfile, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ModelsController") as mock_models_controller, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_get_connection_client:
            
            mock_get_connection_client.return_value = mock_connection_client
            mock_tools_controller.return_value = MagicMock(
                download_tool=MagicMock(return_value=DownloadResult(
                    kind=ToolKind.python,
                    content=b"abc"
                )))
            mock_models_controller.return_value = MagicMock(
                get_models_client=MagicMock()
            )

            ac.export_agent(
                name = self.mock_agent_name,
                kind = AgentKind.NATIVE,
                output_path = self.mock_zip_file_path
            )
        
        captured = caplog.text

        assert f"Exporting agent definition for '{self.mock_agent_name}'" in captured
        assert f"Successfully wrote agents and tools to '{self.mock_zip_file_path}'" in captured
 
    def test_export_agent_missing_collaborators(self, caplog, native_agent_content, external_agent_content, assistant_agent_content):
        native_agent_content["knowledge_base"] = ["kb_1"]

        ac = AgentsController()
        ac.native_client = MockAgent(get_draft_by_name_response=[native_agent_content], return_get_drafts_by_ids=False)
        ac.external_client = MockAgent(get_draft_by_name_response=[external_agent_content], return_get_drafts_by_ids=False)
        ac.assistant_client = MockAgent(get_draft_by_name_response=[assistant_agent_content], fake_agent=assistant_agent_content)
        ac.tool_client = MockAgent()
        ac.knowledge_base_client = MockAgent(fake_agent={"name": self.mock_kb_name})

        mock_connection_client = MockConnectionClient(
            get_draft_by_id_response="testing"
        )

        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ToolsController") as mock_tools_controller, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.zipfile.ZipFile") as mock_zipfile, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.ModelsController") as mock_models_controller, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.KnowledgeBaseController") as mock_kb_controller, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_agent_by_id") as mock_get_agent, \
            patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_controller.get_connections_client") as mock_get_connection_client:
            
            mock_get_connection_client.return_value = mock_connection_client
            mock_get_agent.return_value = None

            mock_tools_controller.return_value = MagicMock(
                download_tool=MagicMock(return_value=DownloadResult(
                    kind=ToolKind.python,
                    content=b"abc"
                )))
            
            mock_kb_controller.return_value = MagicMock(
                knowledge_base_export=MagicMock()
            )

            mock_models_controller.return_value = MagicMock(
                get_models_client=MagicMock()
            )

            mock_zipfile().__enter__().infolist.return_value = [MagicMock()]

            ac.export_agent(
                name = self.mock_agent_name,
                kind = AgentKind.NATIVE,
                output_path = self.mock_zip_file_path
            )
        
        captured = caplog.text

        assert f"Exporting agent definition for '{self.mock_agent_name}'" in captured
        assert f"Successfully wrote agents and tools to '{self.mock_zip_file_path}'" in captured
        assert f"Skipping {self.mock_kb_name}, knowledge_bases are currently unsupported by export"
        assert f"Skipping {native_agent_content.get('collaborators')[0]}, no agent with id {native_agent_content.get('collaborators')[0]} found" in captured

    def test_export_agent_bad_file_type(self, caplog, native_agent_content):
        ac = AgentsController()
        ac.native_client = MockAgent(get_draft_by_name_response=[native_agent_content])
        ac.external_client = MockAgent()
        ac.assistant_client = MockAgent()

        with pytest.raises(SystemExit):
            ac.export_agent(
                name = self.mock_agent_name,
                kind = AgentKind.NATIVE,
                output_path = self.mock_yaml_file_path
            )
        
        captured = caplog.text

        assert f"Output file must end with the extension '.zip'. Provided file '{self.mock_yaml_file_path}' ends with '.yaml'"
        assert f"Exporting agent definition for '{self.mock_agent_name}'" not in captured
        assert f"Successfully wrote agents and tools to '{self.mock_zip_file_path}'" not in captured
    
    def test_export_agent_agent_only_bad_file_type(self, caplog, native_agent_content):
        ac = AgentsController()
        ac.native_client = MockAgent(get_draft_by_name_response=[native_agent_content])
        ac.external_client = MockAgent()
        ac.assistant_client = MockAgent()

        with pytest.raises(SystemExit):
            ac.export_agent(
                name = self.mock_agent_name,
                kind = AgentKind.NATIVE,
                output_path = self.mock_zip_file_path,
                agent_only_flag=True
            )
        
        captured = caplog.text

        assert f"Output file must end with the extension '.yaml' or '.yml'. Provided file '{self.mock_zip_file_path}' ends with '.zip'"
        assert f"Exported agent definition for '{self.mock_agent_name}' to '{self.mock_yaml_file_path}'" not in captured

class TestAgentWebchatCustomizations:
    def test_create_agent_with_welcome_content(self, agent_spec_with_welcome_content):
        test_agent=Agent(**agent_spec_with_welcome_content)
        assert type(test_agent.welcome_content) is WelcomeContent

    def test_create_agent_with_starter_prompt(self, agent_spec_with_starter_prompt):
        test_agent=Agent(**agent_spec_with_starter_prompt)
        assert type(test_agent.starter_prompts) is StarterPrompts
        assert len(test_agent.starter_prompts.prompts) == 1
        for p in test_agent.starter_prompts.prompts:
            assert type(p) is AgentPrompt

    def test_create_agent_with_many_starter_prompts(self, agent_spec_with_starter_prompts):
        test_agent=Agent(**agent_spec_with_starter_prompts)
        assert type(test_agent.starter_prompts) is StarterPrompts
        assert len(test_agent.starter_prompts.prompts) == len(agent_spec_with_starter_prompts["starter_prompts"]["prompts"])
        for p in test_agent.starter_prompts.prompts:
            assert type(p) is AgentPrompt

    def test_create_Agent_with_all_webchat_customizations(self, agent_spec_with_webchat_customizations):
        test_agent=Agent(**agent_spec_with_webchat_customizations)
        assert type(test_agent.welcome_content) is WelcomeContent
        assert type(test_agent.starter_prompts) is StarterPrompts
        assert len(test_agent.starter_prompts.prompts) == len(agent_spec_with_webchat_customizations["starter_prompts"]["prompts"])
        for p in test_agent.starter_prompts.prompts:
            assert type(p) is AgentPrompt
    
class TestAgentDeploy:
    def test_deploy_agent_success(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as mock_get_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client") as external_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client") as assistant_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False):

            mock_client = MagicMock()
            mock_client.get_environments_for_agent.return_value = [
                {"name": "live", "id": "env_live"}
            ]
            mock_client.get_draft_by_name.return_value = [
                {"id": "agent123"}
            ]
            mock_client.deploy.return_value = True
            mock_get_client.return_value = mock_client
            external_client_mock.return_value = mock_client
            assistant_client_mock.return_value = mock_client

            controller = AgentsController()

            with caplog.at_level(logging.INFO):
                controller.deploy_agent("finance_agent")

            assert "Successfully deployed agent" in caplog.text

    def test_deploy_agent_failure(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as mock_get_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client") as external_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client") as assistant_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False):

            mock_client = MagicMock()
            mock_client.get_environments_for_agent.return_value = [
                {"name": "live", "id": "env_live"}
            ]
            mock_client.get_draft_by_name.return_value = [
               {"id": "agent123"}
            ]
            mock_client.deploy.return_value = False
            mock_get_client.return_value = mock_client
            external_client_mock.return_value = mock_client
            assistant_client_mock.return_value = mock_client

            controller = AgentsController()

            with caplog.at_level(logging.ERROR):
                controller.deploy_agent("finance_agent")

            assert "Error deploying agent" in caplog.text

    def test_undeploy_agent_success(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as mock_get_client, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client") as external_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client") as assistant_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False):

            mock_client = MagicMock()
            mock_client.get_environments_for_agent.return_value = [
                {"name": "live", "current_version": "version456"},
                {"name": "draft", "id": "env_draft"}
            ]
            mock_client.get_draft_by_name.return_value = [
                {"id": "agent123"}
            ]
            mock_client.undeploy.return_value = True
            mock_get_client.return_value = mock_client
            external_client_mock.return_value = mock_client
            assistant_client_mock.return_value = mock_client

            controller = AgentsController()

            with caplog.at_level(logging.INFO):
                controller.undeploy_agent("finance_agent")

            assert "Successfully undeployed agent" in caplog.text

    def test_undeploy_agent_failure(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_native_client") as mock_get_client, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_external_client") as external_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController.get_assistant_client") as assistant_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.is_local_dev", return_value=False):

            mock_client = MagicMock()
            mock_client.get_environments_for_agent.return_value = [
                {"name": "live", "current_version": "version456"},
                {"name": "draft", "id": "env_draft"}
            ]
            mock_client.get_draft_by_name.return_value = [
                {"id": "agent123"}
            ]
            mock_client.undeploy.return_value = False
            mock_get_client.return_value = mock_client
            external_client_mock.return_value = mock_client
            assistant_client_mock.return_value = mock_client

            controller = AgentsController()

            with caplog.at_level(logging.ERROR):
                controller.undeploy_agent("finance_agent")

            assert "Error undeploying agent" in caplog.text


