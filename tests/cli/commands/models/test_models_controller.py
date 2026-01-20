import json
from pathlib import Path
import logging
import pytest
import re
import requests
import yaml
import traceback
from unittest.mock import patch, mock_open, MagicMock

from ibm_watsonx_orchestrate.cli.commands.models import models_controller
from ibm_watsonx_orchestrate.cli.commands.models.models_controller import ModelsController, create_model_from_spec, create_policy_from_spec, import_python_model, import_python_policy, parse_model_file, parse_policy_file, extract_model_names_from_policy_inner, get_model_names_from_policy
from ibm_watsonx_orchestrate.client.model_policies.model_policies_client import ModelPoliciesClient
from ibm_watsonx_orchestrate.client.models.models_client import ModelsClient
from ibm_watsonx_orchestrate.agent_builder.models.types import VirtualModel, ModelType, ProviderConfig
from ibm_watsonx_orchestrate.agent_builder.model_policies.types import ModelPolicyInner, ModelPolicyStrategyMode, ModelPolicy, ModelPolicyStrategy, ModelPolicyRetry, ModelPolicyTarget
from ibm_watsonx_orchestrate.utils.environment import EnvService


class MockModelsClient():
    def __init__(self, list_response=[], get_draft_by_name_response=[]):
        self.list_response = list_response
        self.get_draft_by_name_response = get_draft_by_name_response
        self.base_url = 'http://localhost:4321'

    def list(self):
        return self.list_response
    
    def create(self, model):
        assert isinstance(model, VirtualModel)
    
    def update(self, model_id, model):
        assert isinstance(model, VirtualModel)
    
    def delete(self, model_id):
        pass

    def get_draft_by_name(self, model_name):
        return self.get_draft_by_name_response

class MockModelPoliciesClient():
    def __init__(self, list_response=[], get_draft_by_name_response=[]):
        self.list_response = list_response
        self.get_draft_by_name_response = get_draft_by_name_response

    def list(self):
        return self.list_response

    def create(self, policy):
        assert isinstance(policy, ModelPolicy)
    
    def update(self, policy_id, policy):
        assert isinstance(policy, ModelPolicy)
    
    def delete(self, model_policy_id):
        pass

    def get_draft_by_name(self, policy_name):
        return self.get_draft_by_name_response

class MockModel():
    name=""
    description=""
    id=""
    spec={}

    def __init__(self, name = "", description= "", id = "", spec= {}):
        self.name = name
        self.description = description
        self.id = id
        self.spec = spec
    
    def model_dump(self, mode, exclude_none):
        return self.spec

class DummyResponse:
    def __init__(self, status_code, json_data, content=b""):
        self.status_code = status_code
        self._json_data = json_data
        self.content = content

    def json(self):
        return self._json_data

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

def mock_instantiate_client(client: ModelsClient | ModelPoliciesClient, mock_models_client: MockModelsClient=None, mock_policies_client: MockModelPoliciesClient=None) -> MockModelsClient | MockModelPoliciesClient:
    if client == ModelsClient:
        if mock_models_client:
             return mock_models_client
        return MockModelsClient()
    if client == ModelPoliciesClient:
        if mock_policies_client:
            return mock_policies_client
        return MockModelPoliciesClient()
    
def dummy_requests_get(url):
        return DummyResponse(200, {"resources": [
            {
                "model_id": "1234",
                "short_description": "test"
            },
            {
                "model_id": "test",
                "short_description": "1234"
            }
        ]})

def empty_dummy_requests_get(url):
        return DummyResponse(200, {"resources": []})

class TestCreateModelFromSpec:
    mock_model_spec = {
        "spec_version": "v1",
        "name": "test_name",
        "display_name": "test_display_name",
        "description": "test_description",
        "config": {"abc": 123},
        "provider_config": {"provider": "test_provider"},
        "tags": ["test_tag_1"],
        "model_type": ModelType.CHAT,
        "connection_id": "test_connection_id"
    }
    def test_create_model_from_spec(self):
        model = create_model_from_spec(self.mock_model_spec)

        assert model.name == self.mock_model_spec.get("name")
        assert model.display_name == self.mock_model_spec.get("display_name")
        assert model.description == self.mock_model_spec.get("description")
        assert model.config == self.mock_model_spec.get("config")
        assert model.provider_config == ProviderConfig.model_validate(self.mock_model_spec.get("provider_config"))
        assert model.tags == self.mock_model_spec.get("tags")
        assert model.model_type == self.mock_model_spec.get("model_type")
        assert model.connection_id == self.mock_model_spec.get("connection_id")

class TestCreatePolicyFromSpec:
    mock_policy_spec = {
        "spec_version": "v1",
        "name": "test_name",
        "display_name": "test_display_name",
        "description": "test_description",
        "policy": {
            "strategy": {
                "mode": ModelPolicyStrategyMode.FALL_BACK,
                "on_status_codes": [500]
            },
            "retry": {
                "attempts": 1,
                "on_status_codes": [500]
            },
            "targets": []
        }
    }
    def test_create_policy_from_spec(self):
        policy = create_policy_from_spec(self.mock_policy_spec)

        assert policy.name == self.mock_policy_spec.get("name")
        assert policy.display_name == self.mock_policy_spec.get("display_name")
        assert policy.description == self.mock_policy_spec.get("description")
        assert policy.policy == ModelPolicyInner.model_validate(self.mock_policy_spec.get("policy"))

class TestImportPythonModel:
    mock_model_spec = {
        "spec_version": "v1",
        "name": "test_name",
        "display_name": "test_display_name",
        "description": "test_description",
        "config": {"abc": 123},
        "provider_config": {"provider": "test_provider"},
        "tags": ["test_tag_1"],
        "model_type": ModelType.CHAT,
        "connection_id": "test_connection_id"
    }
    def test_import_python_model(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.inspect.getmembers") as getmembers_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.importlib.import_module") as import_module_mock:
            
            mock_model = VirtualModel(**self.mock_model_spec)
            # sample_external_agent = ExternalAgent(**external_agent_content)
            # sample_assitant_agent = AssistantAgent(**assistant_agent_content)

            getmembers_mock.return_value = [(None, mock_model)]

            models = import_python_model("test.py")

            import_module_mock.assert_called_with("test")
            getmembers_mock.assert_called()

            assert len(models) == 1

class TestImportPythonPolicy:
    mock_policy_spec = {
        "spec_version": "v1",
        "name": "test_name",
        "display_name": "test_display_name",
        "description": "test_description",
        "policy": {
            "strategy": {
                "mode": ModelPolicyStrategyMode.FALL_BACK,
                "on_status_codes": [500]
            },
            "retry": {
                "attempts": 1,
                "on_status_codes": [500]
            },
            "targets": []
        }
    }
    def test_import_python_policy(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.inspect.getmembers") as getmembers_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.importlib.import_module") as import_module_mock:
            
            mock_policy = ModelPolicy(**self.mock_policy_spec)
            # sample_external_agent = ExternalAgent(**external_agent_content)
            # sample_assitant_agent = AssistantAgent(**assistant_agent_content)

            getmembers_mock.return_value = [(None, mock_policy)]

            policies = import_python_policy("test.py")

            import_module_mock.assert_called_with("test")
            getmembers_mock.assert_called()

            assert len(policies) == 1

class TestParseModelFile:
    mock_model_spec = {
        "spec_version": "v1",
        "name": "test_name",
        "display_name": "test_display_name",
        "description": "test_description",
        "config": {"abc": 123},
        "provider_config": {"provider": "test_provider"},
        "tags": ["test_tag_1"],
        "model_type": ModelType.CHAT,
        "connection_id": "test_connection_id"
    }
    def test_parse_model_file_yaml(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.safe_open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.yaml.load") as mock_loader:
            
            mock_loader.return_value = self.mock_model_spec

            parse_model_file("test.yaml")

            mock_file.assert_called_once_with("test.yaml", "r")
            mock_loader.assert_called_once()
    
    def test_parse_model_file_json(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.safe_open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.json.load") as mock_loader:
            
            mock_loader.return_value = self.mock_model_spec

            parse_model_file("test.json")

            mock_file.assert_called_once_with("test.json", "r")
            mock_loader.assert_called_once()
    
    def test_parse_model_file_py(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.inspect.getmembers") as getmembers_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.importlib.import_module") as import_module_mock:

            getmembers_mock.return_value = []
            models = parse_model_file("test.py")

            import_module_mock.assert_called_with("test")
            getmembers_mock.assert_called()

            assert len(models) == 0
    
    def test_parse_model_file_invalid(self):
        with pytest.raises(ValueError) as e:
            parse_model_file("test.test")
            assert "file must end in .json, .yaml, .yml or .py" in str(e)

class TestParsePolicyFile:
    mock_policy_spec = {
        "spec_version": "v1",
        "name": "test_name",
        "display_name": "test_display_name",
        "description": "test_description",
        "policy": {
            "strategy": {
                "mode": ModelPolicyStrategyMode.FALL_BACK,
                "on_status_codes": [500]
            },
            "retry": {
                "attempts": 1,
                "on_status_codes": [500]
            },
            "targets": []
        }
    }
    def test_parse_policy_file_yaml(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.safe_open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.yaml.load") as mock_loader:
            
            mock_loader.return_value = self.mock_policy_spec

            parse_policy_file("test.yaml")

            mock_file.assert_called_once_with("test.yaml", "r")
            mock_loader.assert_called_once()
    
    def test_parse_policy_file_json(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.safe_open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.json.load") as mock_loader:
            
            mock_loader.return_value = self.mock_policy_spec

            parse_policy_file("test.json")

            mock_file.assert_called_once_with("test.json", "r")
            mock_loader.assert_called_once()
    
    def test_parse_policy_file_py(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.inspect.getmembers") as getmembers_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.importlib.import_module") as import_module_mock:

            getmembers_mock.return_value = []
            models = parse_policy_file("test.py")

            import_module_mock.assert_called_with("test")
            getmembers_mock.assert_called()

            assert len(models) == 0
    
    def test_parse_policy_file_invalid(self):
        with pytest.raises(ValueError) as e:
            parse_policy_file("test.test")
            assert "file must end in .json, .yaml, .yml or .py" in str(e)

class TestExtractModelNamesFromPolicyInner:
    test_policy_strategy = ModelPolicyStrategy(mode=ModelPolicyStrategyMode.FALL_BACK, on_status_codes=[500])
    test_policy_retry = ModelPolicyRetry(attempts=1, on_status_codes=[400])
    test_policy_targets = [
        ModelPolicyTarget(model_name="test_model_name_1", weight=0.8),
        ModelPolicyInner(
            strategy = test_policy_strategy,
            retry = test_policy_retry,
            targets=[ModelPolicyTarget(model_name="test_model_name_2", weight=0.2)]
        )
    ]
    test_policy_inner = ModelPolicyInner(
        strategy = test_policy_strategy,
        retry = test_policy_retry,
        targets=test_policy_targets
    )
    def test_extract_model_names_from_policy_inner(self):
        model_names = extract_model_names_from_policy_inner(self.test_policy_inner)

        assert "test_model_name_1" in model_names
        assert "test_model_name_2" in model_names

class TestGetModelNamesFromPolicy:
    test_policy_strategy = ModelPolicyStrategy(mode=ModelPolicyStrategyMode.FALL_BACK, on_status_codes=[500])
    test_policy_retry = ModelPolicyRetry(attempts=1, on_status_codes=[400])
    test_policy_targets = [
        ModelPolicyTarget(model_name="test_model_name_1", weight=1),
        ModelPolicyInner(
            strategy = test_policy_strategy,
            retry = test_policy_retry,
            targets=[ModelPolicyTarget(model_name="test_model_name_2", weight=1)]
        )
    ]

    test_policy_inner = ModelPolicyInner(
        strategy = test_policy_strategy,
        retry = test_policy_retry,
        targets=test_policy_targets
    )

    test_policy = ModelPolicy(
        name="test_name",
        description="test_description",
        display_name="test_display_name",
        policy = test_policy_inner
    )
    def test_get_model_names_from_policy(self):
        model_names = get_model_names_from_policy(self.test_policy)

        assert "test_model_name_1" in model_names
        assert "test_model_name_2" in model_names

class TestListModels:
    def test_list_models(self, monkeypatch, caplog):
        fake_env = {"WATSONX_URL": "http://dummy", 'LLM_HAS_WATSONX_APIKEY': True, 'LLM_HAS_WO_INSTANCE': True, 'LLM_HAS_GROQ_API_KEY': True}
        monkeypatch.setattr(EnvService, "merge_env", lambda default, user: fake_env)
        monkeypatch.setattr(EnvService, "get_default_env_file", lambda: Path("dummy.env"))
        monkeypatch.setattr(EnvService, 'get_user_env', lambda self, fallback_to_persisted_env: {})
        monkeypatch.setattr(requests, "get", dummy_requests_get)

        mock_models_client = MockModelsClient(list_response=[MockModel])
        mock_policies_client = MockModelPoliciesClient(list_response=[MockModel])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock, \
                patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.is_local_dev") as is_local_dev_mock, \
                patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.is_saas_env") as is_saas_env_mock:
            is_local_dev_mock.return_value = True
            is_saas_env_mock.return_value = False
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client, mock_policies_client=mock_policies_client)

            mc = ModelsController()
            mc.list_models()
        
        captured = caplog.text

        assert "Retrieving virtual-model models list..." in captured
        assert "Retrieving virtual-policies models list..." in captured
        assert "Retrieving watsonx.ai models list..." in captured
    
    def test_list_models_print_raw(self, monkeypatch, caplog):
        fake_env = {"WATSONX_URL": "http://dummy", 'LLM_HAS_WATSONX_APIKEY': True, 'LLM_HAS_WO_INSTANCE': True, 'LLM_HAS_GROQ_API_KEY': True}
        monkeypatch.setattr(EnvService, "merge_env", lambda default, user: fake_env)
        monkeypatch.setattr(EnvService, "get_default_env_file", lambda: Path("dummy.env"))
        monkeypatch.setattr(EnvService, 'get_user_env', lambda self, fallback_to_persisted_env: {})
        monkeypatch.setattr(requests, "get", dummy_requests_get)

        mock_models_client = MockModelsClient(list_response=[MockModel])
        mock_policies_client = MockModelPoliciesClient(list_response=[MockModel])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock, \
                patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.is_local_dev") as is_local_dev_mock, \
                patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.is_saas_env") as is_saas_env_mock:
            is_local_dev_mock.return_value = True
            is_saas_env_mock.return_value = False
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client, mock_policies_client=mock_policies_client)

            mc = ModelsController()
            mc.list_models(print_raw=True)
        
        captured = caplog.text

        assert "Retrieving virtual-model models list..." in captured
        assert "Retrieving virtual-policies models list..." in captured
        assert "Retrieving watsonx.ai models list..." in captured
    
    def test_list_models_missing_watsonx_url(self, monkeypatch, caplog):
        fake_env = {'LLM_HAS_WATSONX_APIKEY': True, 'LLM_HAS_WO_INSTANCE': True, 'LLM_HAS_GROQ_API_KEY': True}
        monkeypatch.setattr(EnvService, "merge_env", lambda default, user: fake_env)
        monkeypatch.setattr(EnvService, "get_default_env_file", lambda: Path("dummy.env"))
        monkeypatch.setattr(EnvService, 'get_user_env', lambda self, fallback_to_persisted_env: {})
        monkeypatch.setattr(requests, "get", dummy_requests_get)

        mock_models_client = MockModelsClient(list_response=[MockModel])
        mock_policies_client = MockModelPoliciesClient(list_response=[MockModel])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock, \
                patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.is_local_dev") as is_local_dev_mock, \
                patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.is_saas_env") as is_saas_env_mock:
            is_local_dev_mock.return_value = True
            is_saas_env_mock.return_value = False
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client, mock_policies_client=mock_policies_client)

            with pytest.raises(SystemExit):
                mc = ModelsController()
                mc.list_models()
            
            captured = caplog.text

            assert "Error: WATSONX_URL is required in the environment." in captured
    
    def test_list_models_no_models(self, monkeypatch, caplog):
        fake_env = {"WATSONX_URL": "http://dummy", 'LLM_HAS_WATSONX_APIKEY': True, 'LLM_HAS_WO_INSTANCE': True, 'LLM_HAS_GROQ_API_KEY': True}
        monkeypatch.setattr(EnvService, "merge_env", lambda default, user: fake_env)
        monkeypatch.setattr(EnvService, "get_default_env_file", lambda: Path("dummy.env"))
        monkeypatch.setattr(EnvService, 'get_user_env', lambda self, fallback_to_persisted_env: {})
        monkeypatch.setattr(requests, "get", empty_dummy_requests_get)

        mock_models_client = MockModelsClient(list_response=[MockModel])
        mock_policies_client = MockModelPoliciesClient(list_response=[MockModel])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock, \
                patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.is_local_dev") as is_local_dev_mock, \
                patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.is_saas_env") as is_saas_env_mock:
            is_local_dev_mock.return_value = True
            is_saas_env_mock.return_value = False
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client, mock_policies_client=mock_policies_client)

            mc = ModelsController()
            mc.list_models()
        
        captured = caplog.text

        assert "Retrieving virtual-model models list..." in captured
        assert "Retrieving virtual-policies models list..." in captured
        assert "Retrieving watsonx.ai models list..." in captured
    
    def test_list_models_incompatible_models(self, monkeypatch, caplog):
        fake_env = {"WATSONX_URL": "http://dummy", 'LLM_HAS_WATSONX_APIKEY': True, 'LLM_HAS_WO_INSTANCE': True, 'LLM_HAS_GROQ_API_KEY': True, "INCOMPATIBLE_MODELS": "1234"}
        monkeypatch.setattr(EnvService, "merge_env", lambda default, user: fake_env)
        monkeypatch.setattr(EnvService, "get_default_env_file", lambda: Path("dummy.env"))
        monkeypatch.setattr(EnvService, 'get_user_env', lambda self, fallback_to_persisted_env: {})
        monkeypatch.setattr(requests, "get", dummy_requests_get)

        mock_models_client = MockModelsClient(list_response=[MockModel])
        mock_policies_client = MockModelPoliciesClient(list_response=[MockModel])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.is_local_dev") as is_local_dev_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.is_saas_env") as is_saas_env_mock:
            is_local_dev_mock.return_value = True
            is_saas_env_mock.return_value = False
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client, mock_policies_client=mock_policies_client)

            mc = ModelsController()
            mc.list_models()
        
        captured = caplog.text

        assert "Retrieving virtual-model models list..." in captured
        assert "Retrieving virtual-policies models list..." in captured
        assert "Retrieving watsonx.ai models list..." in captured

class TestImportModel:
    mock_filename = "mock_file"
    mock_app_id = "mock_app_id"
    mock_connection_id = "mock_conn_id"
    mock_model_spec = {
        "spec_version": "v1",
        "name": "test_name",
        "display_name": "test_display_name",
        "description": "test_description",
        "config": {"abc": 123},
        "provider_config": {"provider": "test_provider"},
        "tags": ["test_tag_1"],
        "model_type": ModelType.CHAT,
    }

    @pytest.mark.parametrize(
            ("provider"),
            [
               "openai",
               "anthropic",
               "google",
               "watsonx",
               "mistral-ai",
               "ollama",
               "openrouter"
            ]
    )
    def test_import_model_file(self, provider):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.safe_open", mock_open()) as mock_file, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.yaml.load") as mock_loader, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.get_connection_id") as get_connection_id_mock:
            
            mock_file_content = self.mock_model_spec.copy()
            mock_file_content["name"] = f"{provider}/{mock_file_content['name']}"
            get_connection_id_mock.return_value = self.mock_connection_id
            mock_loader.return_value = mock_file_content

            mc = ModelsController()
            models = mc.import_model(
                file = f"{self.mock_filename}.yaml",
                app_id=self.mock_app_id
            )

            mock_file.assert_called_once_with(f"{self.mock_filename}.yaml", "r")
            mock_loader.assert_called_once()

            assert len(models) == 1

            model = models[0]

            assert model.name == f"virtual-model/{mock_file_content['name']}"
            assert model.provider_config.provider == provider
            assert model.connection_id == self.mock_connection_id

    @pytest.mark.parametrize(
            ("provider"),
            [
               "openai",
               "anthropic",
               "google",
               "watsonx",
               "mistral-ai",
               "ollama",
               "openrouter"
            ]
    )
    def test_import_model_file_no_provider(self, provider):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.safe_open", mock_open()) as mock_file, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.yaml.load") as mock_loader, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.get_connection_id") as get_connection_id_mock:
            
            mock_file_content = self.mock_model_spec.copy()
            mock_file_content["name"] = f"{provider}/{mock_file_content['name']}"
            mock_file_content["provider_config"] = None
            get_connection_id_mock.return_value = self.mock_connection_id
            mock_loader.return_value = mock_file_content

            mc = ModelsController()
            models = mc.import_model(
                file = f"{self.mock_filename}.yaml",
                app_id=self.mock_app_id
            )

            mock_file.assert_called_once_with(f"{self.mock_filename}.yaml", "r")
            mock_loader.assert_called_once()

            assert len(models) == 1

            model = models[0]

            assert model.name == f"virtual-model/{mock_file_content['name']}"
            assert model.provider_config.provider == provider
            assert model.connection_id == self.mock_connection_id
    
    @pytest.mark.parametrize(
            ("provider"),
            [
               "openai",
               "anthropic",
               "google",
               "watsonx",
               "mistral-ai",
               "ollama",
               "openrouter"
            ]
    )
    def test_import_model_file_no_config(self, provider):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.safe_open", mock_open()) as mock_file, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.yaml.load") as mock_loader, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.get_connection_id") as get_connection_id_mock:
            
            mock_file_content = self.mock_model_spec.copy()
            mock_file_content["name"] = f"{provider}/{mock_file_content['name']}"
            mock_file_content["config"] = None
            get_connection_id_mock.return_value = self.mock_connection_id
            mock_loader.return_value = mock_file_content

            mc = ModelsController()
            models = mc.import_model(
                file = f"{self.mock_filename}.yaml",
                app_id=self.mock_app_id
            )

            mock_file.assert_called_once_with(f"{self.mock_filename}.yaml", "r")
            mock_loader.assert_called_once()

            assert len(models) == 1

            model = models[0]

            assert model.name == f"virtual-model/{mock_file_content['name']}"
            assert model.provider_config.provider == provider
            assert model.connection_id == self.mock_connection_id

class TestExportModel:
    mock_model_spec = {
        "spec_version": "v1",
        "name": "test_name",
        "display_name": "test_display_name",
        "description": "test_description",
        "config": {"abc": 123},
        "provider_config": {"provider": "test_provider"},
        "tags": ["test_tag_1"],
        "model_type": ModelType.CHAT,
        "connection_id": "test_connection_id"
    }
    mock_model_name = "test_model"
    mock_output_path = "test_output.zip"

    def test_export_model(self, caplog):
        mock_models_client = MockModelsClient(get_draft_by_name_response=[MockModel(name=self.mock_model_name, spec=self.mock_model_spec)])
        mock_connection_client = MockConnectionClient(
            get_draft_by_id_response="testing"
        )

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.yaml.dump", wraps = yaml.dump) as yaml_dump_spy, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.zipfile.ZipFile") as mock_zipfile, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.get_app_id_from_conn_id") as mock_get_app_id, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.export_connection") as mock_export_connection:
            instantiate_client_mock.return_value = mock_models_client
            mock_get_app_id.return_value = "test_app_id"

            mc = ModelsController()
            mc.export_model(name=self.mock_model_name, output_path=self.mock_output_path)

        captured = caplog.text
        yaml_dump_spy.assert_called_once()

        assert "Exporting model" in captured
        assert f"Successfully exported model" in captured
        mock_export_connection.assert_called_once()
        mock_export_connection.assert_called_once()

class TestCreateModel:
    mock_model_name = "test_model"
    mock_env_file = "test_env_file"
    mock_description = "test_description"
    mock_display_name = "test_display_name"
    mock_app_id = "test_app_id"
    mock_connection_id = "test_connection_id"

    @pytest.mark.parametrize(
            ("provider"),
            [
               "openai",
               "anthropic",
               "google",
               "watsonx",
               "mistral-ai",
               "ollama",
               "openrouter"
            ]
    )
    def test_create_model(self, provider):
        mock_models_client = MockModelsClient(list_response=[MockModel])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.get_connection_id") as get_connection_id_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client)
            get_connection_id_mock.return_value = self.mock_connection_id
        
            mc = ModelsController()
            model = mc.create_model(
                name=f"{provider}/{self.mock_model_name}",
                description=self.mock_description, 
                display_name=self.mock_display_name,
                app_id=self.mock_app_id
            )

        assert model.name == f"virtual-model/{provider}/{self.mock_model_name}"
        assert model.description == self.mock_description
        assert model.display_name == self.mock_display_name
        assert model.connection_id == self.mock_connection_id

    @pytest.mark.parametrize(
            ("provider", "provider_config_dict"),
            [
               ("openai", {"api_key": "test_api_key"}),
               ("anthropic", {"api_key": "test_api_key"}),
               ("google", {"api_key": "test_api_key"}),
               ("watsonx", {"api_key": "test_api_key", "watsonx_space_id": "test_space_id"}),
               ("mistral-ai", {"api_key": "test_api_key"}),
               ("ollama", {"api_key": "test_api_key", "custom_host": "test_custom_host"}),
               ("openrouter", {"api_key": "test_api_key"})
            ]
    )
    def test_create_model_with_provider_config(self, provider, provider_config_dict):
        mock_models_client = MockModelsClient(list_response=[MockModel])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.get_connection_id") as get_connection_id_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client)
            get_connection_id_mock.return_value = self.mock_connection_id
        
            mc = ModelsController()
            model = mc.create_model(
                name=f"{provider}/{self.mock_model_name}",
                description=self.mock_description, 
                display_name=self.mock_display_name,
                provider_config_dict=provider_config_dict
            )

        assert model.name == f"virtual-model/{provider}/{self.mock_model_name}"
        assert model.description == self.mock_description
        assert model.display_name == self.mock_display_name
        assert model.connection_id == self.mock_connection_id

class TestPublishOrUpdateModels:
    mock_model_name = "test_name"
    mock_model = VirtualModel(
        name=mock_model_name, 
    )

    def test_publish_or_update_models_publish(self, caplog):
        mock_models_client = MockModelsClient(get_draft_by_name_response=[])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client)

            mc = ModelsController()

            mc.publish_or_update_models(model = self.mock_model)
        
        captured = caplog.text

        assert f"Successfully added the model '{self.mock_model.name}'" in captured
    
    def test_publish_or_update_models_update(self, caplog):
        mock_models_client = MockModelsClient(get_draft_by_name_response=[
            MockModel(id="")
        ])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client)

            mc = ModelsController()

            mc.publish_or_update_models(model = self.mock_model)
        
        captured = caplog.text

        assert f"Existing model '{self.mock_model.name}' found. Updating..." in captured
        assert f"Model '{self.mock_model.name}' updated successfully" in captured
    
    def test_publish_or_update_models_multiple_models_found(self, caplog):
        mock_models_client = MockModelsClient(get_draft_by_name_response=[
            MockModel(id=""),
            MockModel(id=""),
        ])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client)

            mc = ModelsController()

            with pytest.raises(SystemExit):
                mc.publish_or_update_models(model = self.mock_model)
        
        captured = caplog.text

        assert f"Multiple models with the name '{self.mock_model.name}' found. Failed to update model" in captured


class TestRemoveModel:
    mock_model_name = "test_model"
    mock_model_id = "test_model_id"

    def test_remove_model(self, caplog):
        mock_models_client = MockModelsClient(get_draft_by_name_response=[MockModel(name=self.mock_model_name, id=self.mock_model_id)])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client)
            
            mc = ModelsController()
            mc.remove_model(name=self.mock_model_name)

        captured = caplog.text

        assert f"Successfully removed the model '{self.mock_model_name}'" in captured
    
    def test_models_remove_model_not_found(self, caplog):
        mock_models_client = MockModelsClient(get_draft_by_name_response=[])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client)

            mc = ModelsController()
            with pytest.raises(SystemExit):
                mc.remove_model(name=self.mock_model_name)

        captured = caplog.text

        assert f"Successfully removed the model '{self.mock_model_name}'" not in captured
        assert f"No model found with the name '{self.mock_model_name}'" in captured
    
    def test_models_remove_model_multiple_found(self, caplog):
        mock_models_client = MockModelsClient(get_draft_by_name_response=[MockModel(), MockModel()])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client)

            mc = ModelsController()
            with pytest.raises(SystemExit):
                mc.remove_model(name=self.mock_model_name)

        captured = caplog.text

        assert f"Successfully removed the model '{self.mock_model_name}'" not in captured
        assert f"Multiple models with the name '{self.mock_model_name}' found. Failed to remove model" in captured

class TestImportModelPolicy:
    mock_filename = "mock_file"
    mock_model_name = "test_model"
    mock_policy_name = "test_name"
    mock_policy_spec = {
        "spec_version": "v1",
        "name": mock_policy_name,
        "display_name": "test_display_name",
        "description": "test_description",
        "policy": {
            "strategy": {
                "mode": ModelPolicyStrategyMode.FALL_BACK,
                "on_status_codes": [500]
            },
            "retry": {
                "attempts": 1,
                "on_status_codes": [500]
            },
            "targets": [
                {
                    "model_name": mock_model_name,
                    "weight": 1
                }
            ]
        }
    }

    def test_import_model_policy(self):

        mock_models_client = MockModelsClient(list_response=[MockModel(name=self.mock_model_name)])
        mock_policies_client = MockModelPoliciesClient(list_response=[])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.safe_open", mock_open()) as mock_file, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.yaml.load") as mock_loader, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client, mock_policies_client=mock_policies_client)
            mock_loader.return_value = self.mock_policy_spec

            mc = ModelsController()
            policies = mc.import_model_policy(
                file = f"{self.mock_filename}.yaml",
            )

            mock_file.assert_called_once_with(f"{self.mock_filename}.yaml", "r")
            mock_loader.assert_called_once()

            assert len(policies) == 1

            policy = policies[0]

            assert policy.name == f"virtual-policy/{self.mock_policy_name}"
            assert len(policy.policy.targets) == 1

            target = policy.policy.targets[0]
            assert target.model_name == self.mock_model_name
    
    def test_import_model_policy_model_not_found(self, caplog):

        mock_models_client = MockModelsClient(list_response=[])
        mock_policies_client = MockModelPoliciesClient(list_response=[])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.safe_open", mock_open()) as mock_file, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.yaml.load") as mock_loader, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client, mock_policies_client=mock_policies_client)
            mock_loader.return_value = self.mock_policy_spec

            mc = ModelsController()

            with pytest.raises(SystemExit):
                mc.import_model_policy(
                    file = f"{self.mock_filename}.yaml",
                )

            mock_file.assert_called_once_with(f"{self.mock_filename}.yaml", "r")
            mock_loader.assert_called_once()

        captured = caplog.text
        assert f"No model found with the name '{self.mock_model_name}'" in captured           

class TestCreateModelPolicy:
    mock_model_name = "test_model"
    mock_policy_name = "test_name"
    mock_policy_strategy = ModelPolicyStrategyMode.FALL_BACK

    def test_create_model_policy(self):
        mock_models_client = MockModelsClient(list_response=[MockModel(name=self.mock_model_name)])
        mock_policies_client = MockModelPoliciesClient(list_response=[])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client, mock_policies_client=mock_policies_client)

            mc = ModelsController()
            policy = mc.create_model_policy(
                name=self.mock_policy_name,
                models=[self.mock_model_name],
                strategy=self.mock_policy_strategy,
                strategy_on_code=[500],
                retry_on_code=[503],
                retry_attempts=1,
            )

            assert policy.name == f"virtual-policy/{self.mock_policy_name}"
            assert len(policy.policy.targets) == 1

            target = policy.policy.targets[0]
            assert target.model_name == self.mock_model_name
    
    def test_create_model_policy_model_not_found(self, caplog):
        mock_models_client = MockModelsClient(list_response=[])
        mock_policies_client = MockModelPoliciesClient(list_response=[])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client, mock_policies_client=mock_policies_client)

            mc = ModelsController()
            with pytest.raises(SystemExit):
                mc.create_model_policy(
                    name=self.mock_policy_name,
                    models=[self.mock_model_name],
                    strategy=self.mock_policy_strategy,
                    strategy_on_code=[500],
                    retry_on_code=[503],
                    retry_attempts=1,
                )

        captured = caplog.text

        assert f"No model found with the name '{self.mock_model_name}'" in captured

class TestExportModelPolicy:
    mock_model_spec = {
        "spec_version": "v1",
        "name": "test_name",
        "display_name": "test_display_name",
        "description": "test_description",
        "policy": {
            "strategy": {
                "mode": "fallback"
            },
            "retry": {
                "attempts": 1,
                "on_status_codes": [503]
            },
            "targets": [
                {
                    "model_name": "virtual-model/openai/o4-mini"
                }
            ]
        },
    }

    mock_model_spec_no_policy = {
        "spec_version": "v1",
        "name": "test_name_2",
        "display_name": "test_display_name",
        "description": "test_description",
        "policy": {
            "strategy": {
                "mode": "fallback"
            },
            "retry": {
                "attempts": 1,
                "on_status_codes": [503]
            },
            "targets": []
        }
    }

    mock_model_name = "test_model"
    mock_output_path = "test_output.zip"
    def test_export_model_policy(self, caplog):
        mock_models_client = MockModelsClient(get_draft_by_name_response=[MockModel(name=self.mock_model_name, spec=self.mock_model_spec)])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.yaml.dump", wraps = yaml.dump) as yaml_dump_spy, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.zipfile.ZipFile") as mock_zipfile, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.export_model") as mock_export_model:
            instantiate_client_mock.return_value = mock_models_client

            mc = ModelsController()
            mc.export_model_policy(name=self.mock_model_name, output_path=self.mock_output_path)

        captured = caplog.text
        assert yaml_dump_spy.call_count == 1

        assert "Exporting model policy" in captured
        assert f"Successfully exported model policy" in captured
        mock_export_model.assert_called_once()

    def test_export_model_policy_only(self, caplog):
        mock_models_client = MockModelsClient(get_draft_by_name_response=[MockModel(name=self.mock_model_name, spec=self.mock_model_spec_no_policy)])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.yaml.dump", wraps = yaml.dump) as yaml_dump_spy, \
            patch("ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.zipfile.ZipFile") as mock_zipfile, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.export_model") as mock_export_model:

            instantiate_client_mock.return_value = mock_models_client

            mc = ModelsController()
            mc.export_model_policy(name=self.mock_model_name, output_path=self.mock_output_path)

        captured = caplog.text
        assert yaml_dump_spy.call_count == 1

        assert "Exporting model policy" in captured
        assert f"Successfully exported model policy" in captured

class TestPublishOrUpdateModelPoliciess:
    mock_policy_name = "test_name"
    mock_display_name = "test_display_name"
    mock_description = "test_description"
    mock_policy_strategy = ModelPolicyStrategy(
        mode = ModelPolicyStrategyMode.FALL_BACK,
        on_status_codes=[500]
    )
    mock_policy_retry = ModelPolicyRetry(
        attempts=1,
        on_status_codes=[503]
    )
    mock_policy_inner = ModelPolicyInner(
        strategy=mock_policy_strategy,
        retry=mock_policy_retry,
        targets=[]
    )
    mock_policy = ModelPolicy(
        name = mock_policy_name,
        description=mock_description,
        display_name=mock_display_name,
        policy=mock_policy_inner
    )
    def test_publish_or_update_model_policies_publish(self, caplog):
        mock_policies_client = MockModelPoliciesClient(get_draft_by_name_response=[])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_policies_client=mock_policies_client)

            mc = ModelsController()
            mc.publish_or_update_model_policies(
                self.mock_policy
            )

        
        captured = caplog.text

        assert f"Successfully added the model policy '{self.mock_policy_name}'" in captured
    
    def test_publish_or_update_model_policies_update(self, caplog):
        mock_policies_client = MockModelPoliciesClient(get_draft_by_name_response=[MockModel(name=self.mock_policy_name)])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_policies_client=mock_policies_client)

            mc = ModelsController()
            mc.publish_or_update_model_policies(
                self.mock_policy
            )

        
        captured = caplog.text

        assert f"Existing model policy '{self.mock_policy_name}' found. Updating..." in captured
        assert f"Existing model policy '{self.mock_policy_name}' found. Updating..." in captured
    
    def test_publish_or_update_model_policies_publish_not_found(self, caplog):
        mock_policies_client = MockModelPoliciesClient(get_draft_by_name_response=[MockModel(), MockModel()])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_policies_client=mock_policies_client)

            mc = ModelsController()
            with pytest.raises(SystemExit):
                mc.publish_or_update_model_policies(
                    self.mock_policy
                )

        
        captured = caplog.text

        assert f"Successfully added the model policy '{self.mock_policy_name}'"  not in captured
        assert f"Existing model policy '{self.mock_policy_name}' found. Updating..." not in captured
        assert f"Existing model policy '{self.mock_policy_name}' found. Updating..." not in captured
        assert f"Multiple model policies with the name '{self.mock_policy_name}' found. Failed to update model policy" in captured

class TestRemovePolicy:
    mock_policy_name = "test_policy"
    mock_policy_id = "test_policy_id"

    def test_remove_policy(self, caplog):
        mock_policies_client = MockModelPoliciesClient(get_draft_by_name_response=[MockModel(name=self.mock_policy_name, id=self.mock_policy_id)])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_policies_client=mock_policies_client)
            
            mc = ModelsController()
            mc.remove_policy(name=self.mock_policy_name)

        captured = caplog.text

        assert f"Successfully removed the policy '{self.mock_policy_name}'" in captured
    
    def test_remove_policy_not_found(self, caplog):
        mock_policies_client = MockModelPoliciesClient(get_draft_by_name_response=[])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_policies_client=mock_policies_client)
            
            mc = ModelsController()
            with pytest.raises(SystemExit):
                mc.remove_policy(name=self.mock_policy_name)

        captured = caplog.text

        assert f"Successfully removed the policy '{self.mock_policy_name}'" not in captured
        assert f"No model policy found with the name '{self.mock_policy_name}'" in captured
    
    def test_remove_policy_multiple_found(self, caplog):
        mock_policies_client = MockModelPoliciesClient(get_draft_by_name_response=[MockModel(), MockModel()])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_policies_client=mock_policies_client)
            
            mc = ModelsController()
            with pytest.raises(SystemExit):
                mc.remove_policy(name=self.mock_policy_name)

        captured = caplog.text

        assert f"Successfully removed the policy '{self.mock_policy_name}'" not in captured
        assert f"Multiple model policies with the name '{self.mock_policy_name}' found. Failed to remove model policy" in captured