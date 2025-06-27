import pytest
from unittest.mock import patch
from ibm_watsonx_orchestrate.client import utils
from ibm_watsonx_orchestrate.client.utils import is_local_dev, check_token_validity, instantiate_client
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient
# from ibm_watsonx_orchestrate.client.agents.external_agent_client import ExternalAgentClient
# from ibm_watsonx_orchestrate.client.agents.assistant_agent_client import AssistantAgentClient
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.connections.connections_client import ConnectionsClient

class TestIsLocalDev:
    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost:1234",
            "http://127.0.0.1:1234",
            "http://[::1]:1234",
            "http://0.0.0.0:1234"
        ],
    )
    def test_local_urls(self, url):
        assert is_local_dev(url)
    
    @pytest.mark.parametrize(
        "url",
        [
            "http://www.testing.com",
            "https://127.0.0.1:1234",
            "http://www.testing.com/test"
        ],
    )
    def test_remote_urls(self, url):
        assert not is_local_dev(url)

class TestCheckTokenValidity:

    tokens = {
        "valid_token_w_expiry": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjk5OTk5OTk5OTl9.Vg30C57s3l90JNap_VgMhKZjfc-p7SoBXaSAy8c28HA",
        "valid_token_wo_expiry": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "invalid_token_expired": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjEwMDAwMDAwMDB9.9oF3tWEwFMK-0ut1pNLF0tOfZ-onpT5upqOCX58xlko",
        "invalid_token": "not a real token",
    }

    @pytest.mark.parametrize(
        "token",
        [
            tokens["valid_token_w_expiry"],
            tokens["valid_token_wo_expiry"],
        ],
    )
    def test_valid_tokens(self, token):
        assert check_token_validity(token)
    
    @pytest.mark.parametrize(
        "token",
        [
            tokens["invalid_token_expired"],
            tokens["invalid_token"],
        ],
    )
    def test_invalid_tokens(self, token):
        assert not check_token_validity(token)

class TestInstantiateClient:

    def mock_yaml_safe_loader_no_active_env(self, file):
        return {}
    
    def mock_yaml_safe_loader_no_url(self, file):
        if utils.DEFAULT_CONFIG_FILE in file.name:
            return {
                "context": {
                    "active_environment": "testing"
                },
            }
        return {}

    def mock_yaml_safe_loader_missing_token(self, file):
        if utils.DEFAULT_CONFIG_FILE in file.name:
            return {
                "context": {
                    "active_environment": "testing"
                },
                "environments": {
                    "testing": {"wxo_url": "testing url"}
                }
            }
        return {}

    def mock_yaml_safe_loader_invalid_token(self, file):
        if utils.DEFAULT_CONFIG_FILE in file.name:
            return {
                "context": {
                    "active_environment": "testing"
                },
                "environments": {
                    "testing": {"wxo_url": "testing url"}
                }
            }
        return {
            "auth": {
                "testing": {
                    "wxo_mcsp_token": None
                }
            }
        }

    utils.DEFAULT_CONFIG_FILE_FOLDER = "tests/client/resources/"
    utils.DEFAULT_CONFIG_FILE = "config.yaml"
    utils.AUTH_CONFIG_FILE_FOLDER = "tests/client/resources/"
    utils.AUTH_CONFIG_FILE = "credentials.yaml"

    @pytest.mark.parametrize(
        "client",
        [
            ToolClient,
            AgentClient,
            # ExternalAgentClient,
            # AssistantAgentClient,
            ConnectionsClient
        ],
    )
    def test_instantiate_all_client_types(self, client):
        instantiated_client = instantiate_client(client)
        assert instantiated_client

    @pytest.mark.parametrize(
        "client",
        [
            ToolClient,
            AgentClient,
            # ExternalAgentClient,
            # AssistantAgentClient,
            ConnectionsClient
        ],
    )
    def test_no_active_environment(self, client, caplog):
        with patch("ibm_watsonx_orchestrate.client.utils.yaml_safe_load") as mock:
            mock.side_effect = self.mock_yaml_safe_loader_no_active_env
            with pytest.raises(SystemExit) as e:
                instantiate_client(client)
            assert e.type == SystemExit
            assert e.value.code == 1

            captured = caplog.text
            assert "No active environment set" in captured
    
    @pytest.mark.parametrize(
        "client",
        [
            ToolClient,
            AgentClient,
            # ExternalAgentClient,
            # AssistantAgentClient,
            ConnectionsClient
        ],
    )
    def test_no_url_in_environment(self, client, caplog):
        with patch("ibm_watsonx_orchestrate.client.utils.yaml_safe_load") as mock:
            mock.side_effect = self.mock_yaml_safe_loader_no_url
            with pytest.raises(SystemExit) as e:
                instantiate_client(client)
            assert e.type == SystemExit
            assert e.value.code == 1

            captured = caplog.text
            assert "No URL found for environment 'testing'" in captured
    

    @pytest.mark.parametrize(
        "client",
        [
            ToolClient,
            AgentClient,
            # ExternalAgentClient,
            # AssistantAgentClient,
            ConnectionsClient
        ],
    )
    def test_missing_token(self, client, caplog):
        with patch("ibm_watsonx_orchestrate.client.utils.yaml_safe_load") as mock:
            mock.side_effect = self.mock_yaml_safe_loader_missing_token
            with pytest.raises(SystemExit) as e:
                instantiate_client(client)
            assert e.type == SystemExit
            assert e.value.code == 1

            captured = caplog.text
            assert "No credentials found for active env 'testing'. Use `orchestrate env activate testing` to refresh your credentials" in captured

    @pytest.mark.parametrize(
        "client",
        [
            ToolClient,
            AgentClient,
            # ExternalAgentClient,
            # AssistantAgentClient,
            ConnectionsClient
        ],
    )
    def test_invalid_token(self, client, caplog):
        with patch("ibm_watsonx_orchestrate.client.utils.yaml_safe_load") as mock:
            mock.side_effect = self.mock_yaml_safe_loader_invalid_token
            with pytest.raises(SystemExit) as e:
                instantiate_client(client)
            assert e.type == SystemExit
            assert e.value.code == 1

            captured = caplog.text
            assert "The token found for environment 'testing' is missing or expired" in captured
