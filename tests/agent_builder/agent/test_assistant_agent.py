# import pytest
# from pydantic_core import ValidationError
# from unittest.mock import patch, mock_open
# from ibm_watsonx_orchestrate.agent_builder.agents import AssistantAgent, SpecVersion, AgentKind, AssistantAgentConfig

# @pytest.fixture()
# def valid_assistant_agent_sample():
#     return {
#         "spec_version": SpecVersion.V1,
#         "kind": AgentKind.ASSISTANT,
#         "name": "test_assistant_agent",
#         "title": "Test Assistant",
#         "description": "Test Object for assistant agent",
#         "tags": [
#             "tag1",
#             "tag2"
#         ],
#         "config":{
#             "api_version": "2021-11-27",
#             "assistant_id": "27de49b4-4abc-4c1a-91d7-1a612c36fd18",
#             "crn": "crn:v1:aws:public:wxo:us-east-1:sub/20240412-0950-3314-301c-8dfc5950d337:20240415-0552-2619-5017-c41d62e59413::",
#             "instance_url": "https://api.us-east-1.aws.watsonassistant.ibm.com/instances/20240415-0552-2619-5017-c41d62e59413",
#             "environment_id": "ef8b93b2-4a4c-4eb8-b479-3fc056c4aa4f",
#         },
#         "nickname": "test_agent",
#         "app_id": "123"
#     }

# @pytest.fixture()
# def default_values():
#     return {
#     }

# @pytest.fixture(params=['kind', 'spec_version', 'tags', 'nickname', 'app_id'])
# def assistant_agent_missing_optional_values(request, valid_assistant_agent_sample):
#     assistant_spec_definition = valid_assistant_agent_sample
#     assistant_spec_definition.pop(request.param, None)

#     return {
#         "missing" : request.param,
#         "spec" : assistant_spec_definition
#     }

# @pytest.fixture(params=['name', 'description', 'title', 'config'])
# def assistant_agent_missing_required_values(request, valid_assistant_agent_sample):
#     assistant_spec_definition = valid_assistant_agent_sample
#     assistant_spec_definition.pop(request.param, None)

#     return {
#         "missing" : request.param,
#         "spec" : assistant_spec_definition
#     }

# class TestAssistantAgentInit:
#     def test_valid_assistant_agent(self, valid_assistant_agent_sample):
#         assistant_spec_definition = valid_assistant_agent_sample

#         assistant_agent = AssistantAgent(
#             spec_version = assistant_spec_definition["spec_version"],
#             kind = assistant_spec_definition["kind"],
#             name = assistant_spec_definition["name"],
#             title = assistant_spec_definition["title"],
#             description = assistant_spec_definition["description"],
#             tags = assistant_spec_definition["tags"],
#             config = assistant_spec_definition["config"],
#             nickname = assistant_spec_definition["nickname"],
#             app_id = assistant_spec_definition["app_id"]
#             )
        
#         assert assistant_agent.spec_version == assistant_spec_definition["spec_version"]
#         assert assistant_agent.kind == assistant_spec_definition["kind"]
#         assert assistant_agent.name == assistant_spec_definition["name"]
#         assert assistant_agent.title == assistant_spec_definition["title"]
#         assert assistant_agent.description == assistant_spec_definition["description"]
#         assert assistant_agent.tags == assistant_spec_definition["tags"]
#         assert assistant_agent.config == AssistantAgentConfig(**assistant_spec_definition["config"])
#         assert assistant_agent.nickname == assistant_spec_definition["nickname"]
#         assert assistant_agent.app_id == assistant_spec_definition["app_id"]
        


#     def test_assistant_agent_missing_optional_params(self, assistant_agent_missing_optional_values, default_values):
#         agent_spec = assistant_agent_missing_optional_values["spec"]
#         missing_value = assistant_agent_missing_optional_values["missing"]

#         default_value = default_values.get(missing_value, None)

#         assistant_agent = AssistantAgent(
#             **agent_spec
#             )

#         for key in agent_spec:
#             if key == missing_value:
#                 assert getattr(assistant_agent, key) == default_value
#             if key == "config":
#                 assert getattr(assistant_agent, key) == AssistantAgentConfig(**agent_spec.get(key))
#             else:
#                 assert getattr(assistant_agent, key) == agent_spec.get(key)

#     def test_assistant_agent_missing_required_params(self, assistant_agent_missing_required_values):
#         agent_spec = assistant_agent_missing_required_values["spec"]

#         with pytest.raises(ValidationError) as e:
#             _ = AssistantAgent(**agent_spec)

# class TestExternalAgentString:
#     def test_assistant_agent_to_string(self, valid_assistant_agent_sample, capsys):
#         assistant_spec_definition = valid_assistant_agent_sample

#         assistant_agent = AssistantAgent(
#             spec_version = assistant_spec_definition["spec_version"],
#             kind = assistant_spec_definition["kind"],
#             name = assistant_spec_definition["name"],
#             title = assistant_spec_definition["title"],
#             description = assistant_spec_definition["description"],
#             tags = assistant_spec_definition["tags"],
#             config = assistant_spec_definition["config"],
#             nickname = assistant_spec_definition["nickname"],
#             app_id = assistant_spec_definition["app_id"]
#             )
        
#         print(assistant_agent)

#         captured = capsys.readouterr()

#         assert f"AssistantAgent(name='{assistant_spec_definition["name"]}', description='{assistant_spec_definition["description"]}')" in captured.out

# class TestExternalAgentFromSpec:
#     def test_assistant_agent_from_spec_yaml(self, valid_assistant_agent_sample):
#         with patch("ibm_watsonx_orchestrate.agent_builder.agents.assistant_agent.yaml_safe_load") as mock_loader, \
#             patch("builtins.open", mock_open()) as mock_file:
#             assistant_spec_definition = valid_assistant_agent_sample
#             mock_loader.return_value = assistant_spec_definition
            
#             assistant_agent = AssistantAgent.from_spec("test_file.yml")

#             mock_file.assert_called_with("test_file.yml", "r")
#             mock_loader.assert_called_once()

#             assert assistant_agent.spec_version == assistant_spec_definition["spec_version"]
#             assert assistant_agent.kind == assistant_spec_definition["kind"]
#             assert assistant_agent.name == assistant_spec_definition["name"]
#             assert assistant_agent.title == assistant_spec_definition["title"]
#             assert assistant_agent.description == assistant_spec_definition["description"]
#             assert assistant_agent.tags == assistant_spec_definition["tags"]
#             assert assistant_agent.config == AssistantAgentConfig(**assistant_spec_definition["config"])
#             assert assistant_agent.nickname == assistant_spec_definition["nickname"]
#             assert assistant_agent.app_id == assistant_spec_definition["app_id"]
        
#     def test_assistant_agent_from_spec_json(self, valid_assistant_agent_sample):
#         with patch("ibm_watsonx_orchestrate.agent_builder.agents.assistant_agent.json.load") as mock_loader, \
#             patch("builtins.open", mock_open()) as mock_file:
#             assistant_spec_definition = valid_assistant_agent_sample
#             mock_loader.return_value = assistant_spec_definition
            
#             assistant_agent = AssistantAgent.from_spec("test_file.json")

#             mock_file.assert_called_with("test_file.json", "r")
#             mock_loader.assert_called_once()

#             assert assistant_agent.spec_version == assistant_spec_definition["spec_version"]
#             assert assistant_agent.kind == assistant_spec_definition["kind"]
#             assert assistant_agent.name == assistant_spec_definition["name"]
#             assert assistant_agent.title == assistant_spec_definition["title"]
#             assert assistant_agent.description == assistant_spec_definition["description"]
#             assert assistant_agent.tags == assistant_spec_definition["tags"]
#             assert assistant_agent.config == AssistantAgentConfig(**assistant_spec_definition["config"])
#             assert assistant_agent.nickname == assistant_spec_definition["nickname"]
#             assert assistant_agent.app_id == assistant_spec_definition["app_id"]

#     def test_assistant_agent_from_spec_invalid_file_extentionl(self):
#        with patch("builtins.open", mock_open()) as mock_file:
#            with pytest.raises(ValueError) as e:
#                 AssistantAgent.from_spec("test_file.test")

#                 assert "file must end in .json, .yaml, or .yml" in str(e)

#     def test_assistant_agent_from_spec_no_spec_version(self, valid_assistant_agent_sample):
#         with patch("ibm_watsonx_orchestrate.agent_builder.agents.assistant_agent.yaml_safe_load") as mock_loader, \
#             patch("builtins.open", mock_open()) as mock_file:
#             assistant_spec_definition = valid_assistant_agent_sample
#             assistant_spec_definition.pop("spec_version", None)
#             mock_loader.return_value = assistant_spec_definition
            
#             with pytest.raises(ValueError) as e:
#                 AssistantAgent.from_spec("test_file.yml")

#                 mock_file.assert_called_with("test_file.yml", "r")
#                 mock_loader.assert_called_once()

#                 assert "Field 'spec_version' not provided. Please ensure provided spec conforms to a valid spec format" in str(e)

