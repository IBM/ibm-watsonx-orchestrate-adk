"""
Unit tests for AzureAIFoundryDiscoveryService.

All HTTP is mocked — no real Azure credentials required.
"""
from unittest.mock import Mock, patch

import pytest
import requests

from ibm_watsonx_orchestrate.agent_builder.agents.azure_ai_foundry_discovery import (
    AzureAIFoundryDiscoveryService,
    _AZURE_AI_SCOPE,
    _AZURE_TOKEN_URL,
)
from ibm_watsonx_orchestrate.agent_builder.agents.external_agent import ExternalAgent

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_TENANT_ID = "00000000-0000-0000-0000-000000000000"
FAKE_CLIENT_ID = "11111111-1111-1111-1111-111111111111"
FAKE_CLIENT_SECRET = "super-secret-key"  # pragma: allowlist secret
FAKE_ENDPOINT = "https://my-resource.services.ai.azure.com"
FAKE_PROJECT = "my-project"

FAKE_AGENT_1 = {
    "id": "agent-abc",
    "name": "Customer Support",
    "description": "Handles customer queries",
}

FAKE_AGENT_2 = {
    "id": "agent-xyz",
    "name": "Sales Assistant",
    "description": "",
}


# ---------------------------------------------------------------------------
# A. Token acquisition
# ---------------------------------------------------------------------------

class TestGetToken:
    @patch("requests.Session.post")
    def test_get_token_success(self, mock_post):
        """Returns access token from mocked token endpoint."""
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {"access_token": "tok_azure123"}  # pragma: allowlist secret
        mock_post.return_value = mock_resp

        with AzureAIFoundryDiscoveryService() as svc:
            token = svc._get_token(FAKE_TENANT_ID, FAKE_CLIENT_ID, FAKE_CLIENT_SECRET)

        assert token == "tok_azure123"  # pragma: allowlist secret
        mock_post.assert_called_once()
        expected_url = _AZURE_TOKEN_URL.format(tenant_id=FAKE_TENANT_ID)
        assert mock_post.call_args[0][0] == expected_url
        assert mock_post.call_args[1]["data"]["scope"] == _AZURE_AI_SCOPE

    @patch("requests.Session.post")
    def test_get_token_auth_failure_401(self, mock_post):
        """raise_for_status on 401 propagates — not swallowed."""
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")
        mock_post.return_value = mock_resp

        with AzureAIFoundryDiscoveryService() as svc:
            with pytest.raises(requests.HTTPError):
                svc._get_token(FAKE_TENANT_ID, FAKE_CLIENT_ID, FAKE_CLIENT_SECRET)


# ---------------------------------------------------------------------------
# B. Agent listing
# ---------------------------------------------------------------------------

class TestListAgents:
    @patch("requests.Session.get")
    def test_list_agents_success(self, mock_get):
        """Returns list of agent dicts on success."""
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {"value": [FAKE_AGENT_1, FAKE_AGENT_2]}
        mock_get.return_value = mock_resp

        with AzureAIFoundryDiscoveryService() as svc:
            result = svc._list_agents(FAKE_ENDPOINT, FAKE_PROJECT, "tok")

        assert len(result) == 2
        assert result[0]["name"] == "Customer Support"

    @patch("requests.Session.get")
    def test_list_agents_empty_project(self, mock_get):
        """Empty project returns [], no error."""
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {}
        mock_get.return_value = mock_resp

        with AzureAIFoundryDiscoveryService() as svc:
            result = svc._list_agents(FAKE_ENDPOINT, FAKE_PROJECT, "tok")

        assert result == []

    @patch("requests.Session.get")
    def test_list_agents_403_fatal(self, mock_get):
        """403 is not swallowed — raises HTTPError."""
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_get.return_value = mock_resp

        with AzureAIFoundryDiscoveryService() as svc:
            with pytest.raises(requests.HTTPError):
                svc._list_agents(FAKE_ENDPOINT, FAKE_PROJECT, "tok")

    @patch("requests.Session.get")
    def test_list_agents_pagination(self, mock_get):
        """Follows nextLink across multiple pages and passes api-version unconditionally."""
        page1 = Mock()
        page1.raise_for_status = Mock()
        page1.json.return_value = {
            "value": [FAKE_AGENT_1],
            "nextLink": f"{FAKE_ENDPOINT}/api/projects/{FAKE_PROJECT}/agents?skiptoken=1",
        }
        page2 = Mock()
        page2.raise_for_status = Mock()
        page2.json.return_value = {"value": [FAKE_AGENT_2]}
        mock_get.side_effect = [page1, page2]

        with AzureAIFoundryDiscoveryService() as svc:
            result = svc._list_agents(FAKE_ENDPOINT, FAKE_PROJECT, "tok")

        assert len(result) == 2
        assert mock_get.call_count == 2
        assert mock_get.call_args_list[0][1]["params"] == {"api-version": "2025-05-01"}
        assert mock_get.call_args_list[1][0][0] == f"{FAKE_ENDPOINT}/api/projects/{FAKE_PROJECT}/agents?skiptoken=1"
        assert mock_get.call_args_list[1][1]["params"] == {"api-version": "2025-05-01"}

    @patch("ibm_watsonx_orchestrate.agent_builder.agents.azure_ai_foundry_discovery.AzureAIFoundryDiscoveryService._list_agents")
    @patch("ibm_watsonx_orchestrate.agent_builder.agents.azure_ai_foundry_discovery.AzureAIFoundryDiscoveryService._get_token")
    def test_list_agents_orchestrates_token_and_listing(self, mock_get_token, mock_list_agents):
        """list_agents() calls _get_token then passes the token to _list_agents."""
        mock_get_token.return_value = "tok_from_aad"  # pragma: allowlist secret
        mock_list_agents.return_value = [FAKE_AGENT_1]

        with AzureAIFoundryDiscoveryService() as svc:
            result = svc.list_agents(FAKE_ENDPOINT, FAKE_PROJECT, FAKE_TENANT_ID, FAKE_CLIENT_ID, FAKE_CLIENT_SECRET)

        mock_get_token.assert_called_once_with(FAKE_TENANT_ID, FAKE_CLIENT_ID, FAKE_CLIENT_SECRET)
        mock_list_agents.assert_called_once_with(FAKE_ENDPOINT, FAKE_PROJECT, "tok_from_aad")  # pragma: allowlist secret
        assert result == [FAKE_AGENT_1]


# ---------------------------------------------------------------------------
# C. Field conversion
# ---------------------------------------------------------------------------

class TestConvertToWxoExternalAgentDict:
    def test_convert_sets_provider_azure_ai_foundry(self):
        result = AzureAIFoundryDiscoveryService.convert_to_wxo_external_agent_dict(
            FAKE_AGENT_1, FAKE_ENDPOINT, FAKE_PROJECT
        )
        assert result["provider"] == "azure_ai_foundry"

    def test_convert_sets_api_url(self):
        result = AzureAIFoundryDiscoveryService.convert_to_wxo_external_agent_dict(
            FAKE_AGENT_1, FAKE_ENDPOINT, FAKE_PROJECT
        )
        assert result["api_url"] == (
            f"{FAKE_ENDPOINT}/api/projects/{FAKE_PROJECT}/agents/agent-abc"
        )

    def test_convert_sets_api_url_with_full_resource_path(self):
        """Full ARM resource path id extracts only the final segment."""
        agent = {
            **FAKE_AGENT_1,
            "id": "/subscriptions/sub-123/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/acc/agents/asst_abc123",
        }
        result = AzureAIFoundryDiscoveryService.convert_to_wxo_external_agent_dict(
            agent, FAKE_ENDPOINT, FAKE_PROJECT
        )
        assert result["api_url"] == (
            f"{FAKE_ENDPOINT}/api/projects/{FAKE_PROJECT}/agents/asst_abc123"
        )

    def test_convert_sets_name_sanitized(self):
        """name is display name lowercased with spaces/dashes/special chars → underscores, max 64 chars."""
        agent = {**FAKE_AGENT_1, "name": "My Cool Agent v2.0 (prod)"}
        result = AzureAIFoundryDiscoveryService.convert_to_wxo_external_agent_dict(
            agent, FAKE_ENDPOINT, FAKE_PROJECT
        )
        assert result["name"] == "my_cool_agent_v2_0__prod_"

    def test_convert_no_description_uses_fallback(self):
        """Empty description falls back to 'Microsoft Azure AI Foundry agent: <name>'."""
        result = AzureAIFoundryDiscoveryService.convert_to_wxo_external_agent_dict(
            FAKE_AGENT_2, FAKE_ENDPOINT, FAKE_PROJECT
        )
        assert result["description"] == "Microsoft Azure AI Foundry agent: Sales Assistant"

    def test_convert_validates_as_external_agent(self):
        """Converted dict passes ExternalAgent.model_validate() without raising."""
        result = AzureAIFoundryDiscoveryService.convert_to_wxo_external_agent_dict(
            FAKE_AGENT_1, FAKE_ENDPOINT, FAKE_PROJECT
        )
        agent = ExternalAgent.model_validate(result)
        assert agent.name == "customer_support"
        assert agent.provider.value == "azure_ai_foundry"

    def test_convert_name_truncated_to_64_chars(self):
        """Names longer than 64 characters are truncated."""
        long_name = "a" * 100
        agent = {"id": "x", "name": long_name}
        result = AzureAIFoundryDiscoveryService.convert_to_wxo_external_agent_dict(
            agent, FAKE_ENDPOINT, FAKE_PROJECT
        )
        assert len(result["name"]) == 64

    def test_convert_empty_name_falls_back_to_id(self):
        """Empty name falls back to azure_agent_<id>."""
        agent = {"id": "1234", "name": ""}
        result = AzureAIFoundryDiscoveryService.convert_to_wxo_external_agent_dict(
            agent, FAKE_ENDPOINT, FAKE_PROJECT
        )
        assert result["name"] == "azure_agent_1234"


# ---------------------------------------------------------------------------
# D. Name filtering
# ---------------------------------------------------------------------------

class TestDiscoverAndConvert:
    def test_filter_by_name_match(self):
        """Returns only the matching agent."""
        with AzureAIFoundryDiscoveryService() as svc:
            result = svc.discover_and_convert(
                [FAKE_AGENT_1, FAKE_AGENT_2],
                agents=["Customer Support"],
                endpoint=FAKE_ENDPOINT,
                project_name=FAKE_PROJECT,
            )
        assert len(result) == 1
        assert result[0]["name"] == "customer_support"

    def test_filter_matches_name_case_insensitive(self):
        """Filter is case-insensitive against agent name."""
        with AzureAIFoundryDiscoveryService() as svc:
            result = svc.discover_and_convert(
                [FAKE_AGENT_1],
                agents=["customer support"],
                endpoint=FAKE_ENDPOINT,
                project_name=FAKE_PROJECT,
            )
        assert len(result) == 1

    def test_filter_no_match_logs_warning(self, caplog):
        """Non-matching name returns [] and logs a warning."""
        import logging
        with caplog.at_level(logging.WARNING):
            with AzureAIFoundryDiscoveryService() as svc:
                result = svc.discover_and_convert(
                    [FAKE_AGENT_1],
                    agents=["nonexistent agent"],
                    endpoint=FAKE_ENDPOINT,
                    project_name=FAKE_PROJECT,
                )
        assert result == []
        assert "nonexistent agent" in caplog.text

    def test_filter_none_returns_all(self):
        """`agents=None` returns all converted agents."""
        with AzureAIFoundryDiscoveryService() as svc:
            result = svc.discover_and_convert(
                [FAKE_AGENT_1, FAKE_AGENT_2],
                agents=None,
                endpoint=FAKE_ENDPOINT,
                project_name=FAKE_PROJECT,
            )
        assert len(result) == 2
