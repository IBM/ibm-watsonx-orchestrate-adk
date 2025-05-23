import json
from pathlib import Path
import logging
import pytest
import re
import requests
from unittest.mock import patch

from ibm_watsonx_orchestrate.cli.commands.models import models_command
from ibm_watsonx_orchestrate.client.model_policies.model_policies_client import ModelPoliciesClient
from ibm_watsonx_orchestrate.client.models.models_client import ModelsClient
from ibm_watsonx_orchestrate.client.models.types import CreateVirtualModel

class MockModelsClient():
    def __init__(self, list_response=[]):
        self.list_response = list_response

    def list(self):
        return self.list_response
    
    def create(self, model):
        assert isinstance(model, CreateVirtualModel)
    
    def delete(self, model_id):
        pass

class MockModelPoliciesClient():
    def __init__(self, list_response=[]):
        self.list_response = list_response

    def list(self):
        return self.list_response

class MockModel():
    name=""
    description=""
    id=""
    def __init__(self, name = "", description= "", id = ""):
        self.name = name
        self.description = description
        self.id = id
   
class DummyResponse:
    def __init__(self, status_code, json_data, content=b""):
        self.status_code = status_code
        self._json_data = json_data
        self.content = content

    def json(self):
        return self._json_data


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

class TestModelList:
    def test_model_list(self, monkeypatch, caplog):
        fake_env = {"WATSONX_URL": "http://dummy"}
        monkeypatch.setattr(models_command, "merge_env", lambda default, user: fake_env)
        monkeypatch.setattr(models_command, "get_default_env_file", lambda: Path("dummy.env"))
        monkeypatch.setattr(requests, "get", dummy_requests_get)

        mock_models_client = MockModelsClient(list_response=[MockModel])
        mock_policies_client = MockModelPoliciesClient(list_response=[MockModel])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_command.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client, mock_policies_client=mock_policies_client)

            models_command.model_list()
        
        captured = caplog.text

        assert "Retrieving virtual-model models list..." in captured
        assert "Retrieving virtual-policies models list..." in captured
        assert "Retrieving watsonx.ai models list..." in captured
        assert "No models found." not in captured
    
    def test_model_list_print_raw(self, monkeypatch, caplog):
        fake_env = {"WATSONX_URL": "http://dummy"}
        monkeypatch.setattr(models_command, "merge_env", lambda default, user: fake_env)
        monkeypatch.setattr(models_command, "get_default_env_file", lambda: Path("dummy.env"))
        monkeypatch.setattr(requests, "get", dummy_requests_get)

        mock_models_client = MockModelsClient(list_response=[MockModel])
        mock_policies_client = MockModelPoliciesClient(list_response=[MockModel])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_command.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client, mock_policies_client=mock_policies_client)

            models_command.model_list(print_raw=True)
        
        captured = caplog.text

        assert "Retrieving virtual-model models list..." in captured
        assert "Retrieving virtual-policies models list..." in captured
        assert "Retrieving watsonx.ai models list..." in captured
        assert "No models found." not in captured
    
    def test_model_list_missing_watsonx_url(self, monkeypatch, caplog):
        fake_env = {}
        monkeypatch.setattr(models_command, "merge_env", lambda default, user: fake_env)
        monkeypatch.setattr(models_command, "get_default_env_file", lambda: Path("dummy.env"))
        monkeypatch.setattr(requests, "get", dummy_requests_get)

        mock_models_client = MockModelsClient(list_response=[MockModel])
        mock_policies_client = MockModelPoliciesClient(list_response=[MockModel])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_command.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client, mock_policies_client=mock_policies_client)

            with pytest.raises(SystemExit):
                models_command.model_list()
            
            captured = caplog.text

            assert "Error: WATSONX_URL is required in the environment." in captured
    
    def test_model_list_no_models(self, monkeypatch, caplog):
        fake_env = {"WATSONX_URL": "http://dummy"}
        monkeypatch.setattr(models_command, "merge_env", lambda default, user: fake_env)
        monkeypatch.setattr(models_command, "get_default_env_file", lambda: Path("dummy.env"))
        monkeypatch.setattr(requests, "get", empty_dummy_requests_get)

        mock_models_client = MockModelsClient(list_response=[MockModel])
        mock_policies_client = MockModelPoliciesClient(list_response=[MockModel])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_command.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client, mock_policies_client=mock_policies_client)

            models_command.model_list()
        
        captured = caplog.text

        assert "Retrieving virtual-model models list..." in captured
        assert "Retrieving virtual-policies models list..." in captured
        assert "Retrieving watsonx.ai models list..." in captured
        assert "No models found." in captured
    
    def test_model_list_incompatible_models(self, monkeypatch, caplog):
        fake_env = {"WATSONX_URL": "http://dummy", "INCOMPATIBLE_MODELS": "1234"}
        monkeypatch.setattr(models_command, "merge_env", lambda default, user: fake_env)
        monkeypatch.setattr(models_command, "get_default_env_file", lambda: Path("dummy.env"))
        monkeypatch.setattr(requests, "get", dummy_requests_get)

        mock_models_client = MockModelsClient(list_response=[MockModel])
        mock_policies_client = MockModelPoliciesClient(list_response=[MockModel])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_command.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client, mock_policies_client=mock_policies_client)

            models_command.model_list()
        
        captured = caplog.text

        assert "Retrieving virtual-model models list..." in captured
        assert "Retrieving virtual-policies models list..." in captured
        assert "Retrieving watsonx.ai models list..." in captured
        assert "No models found." not in captured

class TestModelsAdd:
    mock_model_name = "test_model"
    mock_env_file = "test_env_file"
    mock_description = "test_description"
    mock_display_name = "test_display_name"
    mock_env = {
        "OPENAI_API_KEY": "test_key",
        "ANTHROPIC_API_KEY": "test_key",
        "GOOGLE_API_KEY": "test_key",
        "WATSONX_API_KEY": "test_key",
        "MISTRAL_API_KEY": "test_key",
        "OLLAMA_API_KEY": "test_key",
        "OPENROUTER_API_KEY": "test_key",
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
    def test_models_add(self, caplog, provider):
        mock_models_client = MockModelsClient(list_response=[MockModel])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_command.instantiate_client") as instantiate_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.models.env_file_model_provider_mapper.dotenv_values") as mock_dotenv_values:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client)
            mock_dotenv_values.return_value = self.mock_env

            models_command.models_add(
                name=f"{provider}/{self.mock_model_name}",
                env_file=self.mock_env_file, 
                description=self.mock_description, 
                display_name=self.mock_display_name 
            )

        captured = caplog.text

        assert f"Successfully added the model 'virtual-model/{provider}/{self.mock_model_name}'" in captured

class TestModelsRemove:
    mock_model_name = "test_model"
    mock_model_id = "test_model_id"

    def test_models_remove(self, caplog):
        mock_models_client = MockModelsClient(list_response=[MockModel(name=self.mock_model_name, id=self.mock_model_id)])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_command.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client)

            models_command.models_remove(name=self.mock_model_name)

        captured = caplog.text

        assert f"Successfully removed the model '{self.mock_model_name}'" in captured
    
    def test_models_remove_model_not_found(self, caplog):
        mock_models_client = MockModelsClient(list_response=[MockModel(name=self.mock_model_name, id=self.mock_model_id)])

        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_command.instantiate_client") as instantiate_client_mock:
            instantiate_client_mock.side_effect = lambda x: mock_instantiate_client(x, mock_models_client=mock_models_client)

            with pytest.raises(SystemExit):
                models_command.models_remove(name="dummy_name")

        captured = caplog.text

        assert f"Successfully removed the model '{self.mock_model_name}'" not in captured
        assert "Successfully removed the model 'dummy_name'" not in captured
        assert "No model found with the name 'dummy_name'" in captured