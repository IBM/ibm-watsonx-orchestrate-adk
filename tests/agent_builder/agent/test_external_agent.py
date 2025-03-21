# import pytest
# from pydantic_core import ValidationError
# from unittest.mock import patch, mock_open
# from ibm_watsonx_orchestrate.agent_builder.agents import ExternalAgent, SpecVersion, AgentKind, ExternalAgentConfig

# @pytest.fixture()
# def valid_external_agent_sample():
#     return {
#         "spec_version": SpecVersion.V1,
#         "kind": AgentKind.EXTERNAL,
#         "name": "test_external_agent",
#         "title": "Test External",
#         "description": "Test Object for external agent",
#         "tags": [
#             "tag1",
#             "tag2"
#         ],
#         "api_url": "test",
#         "chat_params": {
#             "stream": True
#         },
#         "config":{
#             "hidden": False,
#             "enable_cot": False
#         },
#         "nickname": "test_agent",
#         "app_id": "123"
#     }

# @pytest.fixture()
# def default_values():
#     return {
#     }

# @pytest.fixture(params=['kind', 'spec_version', 'tags', 'chat_params', 'config', 'nickname', 'app_id'])
# def external_agent_missing_optional_values(request, valid_external_agent_sample):
#     external_spec_definition = valid_external_agent_sample
#     external_spec_definition.pop(request.param, None)

#     return {
#         "missing" : request.param,
#         "spec" : external_spec_definition
#     }

# @pytest.fixture(params=['name', 'description', 'title', 'api_url'])
# def external_agent_missing_required_values(request, valid_external_agent_sample):
#     external_spec_definition = valid_external_agent_sample
#     external_spec_definition.pop(request.param, None)

#     return {
#         "missing" : request.param,
#         "spec" : external_spec_definition
#     }

# class TestExternalAgentInit:
#     def test_valid_external_agent(self, valid_external_agent_sample):
#         external_spec_definition = valid_external_agent_sample

#         external_agent = ExternalAgent(
#             spec_version = external_spec_definition["spec_version"],
#             kind = external_spec_definition["kind"],
#             name = external_spec_definition["name"],
#             title = external_spec_definition["title"],
#             description = external_spec_definition["description"],
#             tags = external_spec_definition["tags"],
#             api_url = external_spec_definition["api_url"],
#             chat_params = external_spec_definition["chat_params"],
#             config = external_spec_definition["config"],
#             nickname = external_spec_definition["nickname"],
#             app_id = external_spec_definition["app_id"]
#             )
        
#         assert external_agent.spec_version == external_spec_definition["spec_version"]
#         assert external_agent.kind == external_spec_definition["kind"]
#         assert external_agent.name == external_spec_definition["name"]
#         assert external_agent.title == external_spec_definition["title"]
#         assert external_agent.description == external_spec_definition["description"]
#         assert external_agent.tags == external_spec_definition["tags"]
#         assert external_agent.api_url == external_spec_definition["api_url"]
#         assert external_agent.chat_params == external_spec_definition["chat_params"]
#         assert external_agent.config == ExternalAgentConfig(**external_spec_definition["config"])
#         assert external_agent.nickname == external_spec_definition["nickname"]
#         assert external_agent.app_id == external_spec_definition["app_id"]
        


#     def test_external_agent_missing_optional_params(self, external_agent_missing_optional_values, default_values):
#         agent_spec = external_agent_missing_optional_values["spec"]
#         missing_value = external_agent_missing_optional_values["missing"]

#         default_value = default_values.get(missing_value, None)

#         external_agent = ExternalAgent(
#             **agent_spec
#             )

#         for key in agent_spec:
#             if key == missing_value:
#                 assert getattr(external_agent, key) == default_value
#             if key == "config":
#                 assert getattr(external_agent, key) == ExternalAgentConfig(**agent_spec.get(key))
#             else:
#                 assert getattr(external_agent, key) == agent_spec.get(key)

#     def test_external_agent_missing_required_params(self, external_agent_missing_required_values):
#         agent_spec = external_agent_missing_required_values["spec"]

#         with pytest.raises(ValidationError) as e:
#             _ = ExternalAgent(**agent_spec)

# class TestExternalAgentString:
#     def test_external_agent_to_string(self, valid_external_agent_sample, capsys):
#         external_spec_definition = valid_external_agent_sample

#         external_agent = ExternalAgent(
#             spec_version = external_spec_definition["spec_version"],
#             kind = external_spec_definition["kind"],
#             name = external_spec_definition["name"],
#             title = external_spec_definition["title"],
#             description = external_spec_definition["description"],
#             tags = external_spec_definition["tags"],
#             api_url = external_spec_definition["api_url"],
#             chat_params = external_spec_definition["chat_params"],
#             config = external_spec_definition["config"],
#             nickname = external_spec_definition["nickname"],
#             app_id = external_spec_definition["app_id"]
#             )
        
#         print(external_agent)

#         captured = capsys.readouterr()

#         assert f"ExternalAgent(name='{external_spec_definition["name"]}', description='{external_spec_definition["description"]}')" in captured.out

# class TestExternalAgentFromSpec:
#     def test_external_agent_from_spec_yaml(self, valid_external_agent_sample):
#         with patch("ibm_watsonx_orchestrate.agent_builder.agents.external_agent.yaml_safe_load") as mock_loader, \
#             patch("builtins.open", mock_open()) as mock_file:
#             external_spec_definition = valid_external_agent_sample
#             mock_loader.return_value = external_spec_definition
            
#             external_agent = ExternalAgent.from_spec("test_file.yml")

#             mock_file.assert_called_with("test_file.yml", "r")
#             mock_loader.assert_called_once()

#             assert external_agent.spec_version == external_spec_definition["spec_version"]
#             assert external_agent.kind == external_spec_definition["kind"]
#             assert external_agent.name == external_spec_definition["name"]
#             assert external_agent.title == external_spec_definition["title"]
#             assert external_agent.description == external_spec_definition["description"]
#             assert external_agent.tags == external_spec_definition["tags"]
#             assert external_agent.api_url == external_spec_definition["api_url"]
#             assert external_agent.chat_params == external_spec_definition["chat_params"]
#             assert external_agent.config == ExternalAgentConfig(**external_spec_definition["config"])
#             assert external_agent.nickname == external_spec_definition["nickname"]
#             assert external_agent.app_id == external_spec_definition["app_id"]
        
#     def test_external_agent_from_spec_json(self, valid_external_agent_sample):
#         with patch("ibm_watsonx_orchestrate.agent_builder.agents.external_agent.json.load") as mock_loader, \
#             patch("builtins.open", mock_open()) as mock_file:
#             external_spec_definition = valid_external_agent_sample
#             mock_loader.return_value = external_spec_definition
            
#             external_agent = ExternalAgent.from_spec("test_file.json")

#             mock_file.assert_called_with("test_file.json", "r")
#             mock_loader.assert_called_once()

#             assert external_agent.spec_version == external_spec_definition["spec_version"]
#             assert external_agent.kind == external_spec_definition["kind"]
#             assert external_agent.name == external_spec_definition["name"]
#             assert external_agent.title == external_spec_definition["title"]
#             assert external_agent.description == external_spec_definition["description"]
#             assert external_agent.tags == external_spec_definition["tags"]
#             assert external_agent.api_url == external_spec_definition["api_url"]
#             assert external_agent.chat_params == external_spec_definition["chat_params"]
#             assert external_agent.config == ExternalAgentConfig(**external_spec_definition["config"])
#             assert external_agent.nickname == external_spec_definition["nickname"]
#             assert external_agent.app_id == external_spec_definition["app_id"]

#     def test_external_agent_from_spec_invalid_file_extentionl(self):
#        with patch("builtins.open", mock_open()) as mock_file:
#            with pytest.raises(ValueError) as e:
#                 ExternalAgent.from_spec("test_file.test")

#                 assert "file must end in .json, .yaml, or .yml" in str(e)

#     def test_external_agent_from_spec_no_spec_version(self, valid_external_agent_sample):
#         with patch("ibm_watsonx_orchestrate.agent_builder.agents.external_agent.yaml_safe_load") as mock_loader, \
#             patch("builtins.open", mock_open()) as mock_file:
#             external_spec_definition = valid_external_agent_sample
#             external_spec_definition.pop("spec_version", None)
#             mock_loader.return_value = external_spec_definition
            
#             with pytest.raises(ValueError) as e:
#                 ExternalAgent.from_spec("test_file.yml")

#                 mock_file.assert_called_with("test_file.yml", "r")
#                 mock_loader.assert_called_once()

#                 assert "Field 'spec_version' not provided. Please ensure provided spec conforms to a valid spec format" in str(e)

