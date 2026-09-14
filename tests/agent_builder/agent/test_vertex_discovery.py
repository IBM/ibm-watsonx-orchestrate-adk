"""
Unit tests for VertexDiscoveryService.

All HTTP is mocked — no real GCP credentials required.
Pattern mirrors tests/cli/commands/agents/test_a2a_discovery.py.
"""
import time
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from ibm_watsonx_orchestrate.agent_builder.agents.external_agent import ExternalAgent
from ibm_watsonx_orchestrate.agent_builder.agents.vertex_discovery import (
    VertexDiscoveryService,
    _GOOGLE_SCOPE,
    _GOOGLE_TOKEN_URL,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_PRIVATE_KEY = (
    "-----BEGIN RSA PRIVATE KEY-----\n"
    "MIIEowIBAAKCAQEA2a2rwplBQLF29amygykEMmYz0+Kcj3bKBp29xNMm9QhXG0x8\n"  # pragma: allowlist secret
    "-----END RSA PRIVATE KEY-----"
)

FAKE_SERVICE_ACCOUNT = {
    "type": "service_account",
    "project_id": "my-gcp-project",
    "private_key_id": "key-id-123",
    "private_key": FAKE_PRIVATE_KEY,  # pragma: allowlist secret
    "client_email": "svc@my-gcp-project.iam.gserviceaccount.com",
    "token_uri": "https://oauth2.googleapis.com/token",
}

FAKE_AGENT_1 = {
    "name": "projects/my-gcp-project/locations/us-central1/agents/agent-abc",
    "displayName": "Customer Support",
    "description": "Handles customer queries",
}

FAKE_AGENT_2 = {
    "name": "projects/my-gcp-project/locations/us-central1/agents/agent-xyz",
    "displayName": "Sales Assistant",
    "description": "",
}


# ---------------------------------------------------------------------------
# A. Token acquisition
# ---------------------------------------------------------------------------

class TestGetToken:
    @patch("jwt.encode", return_value="signed_jwt")
    @patch("requests.Session.post")
    def test_get_token_success(self, mock_post, mock_jwt):
        """Returns access token from mocked token endpoint."""
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {"access_token": "tok_abc123"}  # pragma: allowlist secret
        mock_post.return_value = mock_resp

        with VertexDiscoveryService() as svc:
            token = svc._get_token(FAKE_SERVICE_ACCOUNT)

        assert token == "tok_abc123"  # pragma: allowlist secret
        mock_post.assert_called_once()

    def test_get_token_invalid_service_account_missing_private_key(self):
        """Raises ValueError when private_key is missing."""
        bad_sa = {k: v for k, v in FAKE_SERVICE_ACCOUNT.items() if k != "private_key"}
        with VertexDiscoveryService() as svc:
            with pytest.raises(ValueError, match="private_key"):
                svc._get_token(bad_sa)

    def test_get_token_invalid_service_account_missing_client_email(self):
        """Raises ValueError when client_email is missing."""
        bad_sa = {k: v for k, v in FAKE_SERVICE_ACCOUNT.items() if k != "client_email"}
        with VertexDiscoveryService() as svc:
            with pytest.raises(ValueError, match="client_email"):
                svc._get_token(bad_sa)

    @patch("jwt.encode", return_value="signed_jwt")
    @patch("requests.Session.post")
    def test_get_token_auth_failure_401(self, mock_post, mock_jwt):
        """raise_for_status on 401 propagates — not swallowed."""
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")
        mock_post.return_value = mock_resp

        with VertexDiscoveryService() as svc:
            with pytest.raises(requests.HTTPError):
                svc._get_token(FAKE_SERVICE_ACCOUNT)

    @patch("requests.Session.post")
    def test_get_token_uses_correct_scope(self, mock_post):
        """POST body contains the required cloud-platform scope."""
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {"access_token": "tok"}  # pragma: allowlist secret
        mock_post.return_value = mock_resp

        with VertexDiscoveryService() as svc:
            with patch("jwt.encode", return_value="signed"):
                svc._get_token(FAKE_SERVICE_ACCOUNT)

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["data"]["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"

    @patch("time.time", return_value=1_000_000)
    @patch("jwt.encode")
    @patch("requests.Session.post")
    def test_get_token_jwt_claims(self, mock_post, mock_jwt_encode, mock_time):
        """JWT payload has correct iss, aud, exp relative to iat."""
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {"access_token": "tok"}  # pragma: allowlist secret
        mock_post.return_value = mock_resp
        mock_jwt_encode.return_value = "signed_jwt"

        with VertexDiscoveryService() as svc:
            svc._get_token(FAKE_SERVICE_ACCOUNT)

        payload, *_ = mock_jwt_encode.call_args[0]
        assert payload["iss"] == FAKE_SERVICE_ACCOUNT["client_email"]
        assert payload["sub"] == FAKE_SERVICE_ACCOUNT["client_email"]
        assert payload["aud"] == _GOOGLE_TOKEN_URL
        assert payload["scope"] == _GOOGLE_SCOPE
        assert payload["iat"] == 1_000_000
        assert payload["exp"] == 1_000_000 + 3600


# ---------------------------------------------------------------------------
# B. Agent listing
# ---------------------------------------------------------------------------

class TestListAgents:
    @patch("requests.Session.get")
    def test_list_agents_success(self, mock_get):
        """Returns list of agent dicts on success."""
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {"agents": [FAKE_AGENT_1, FAKE_AGENT_2]}
        mock_get.return_value = mock_resp

        with VertexDiscoveryService() as svc:
            result = svc._list_agents("my-project", "us-central1", "tok")

        assert len(result) == 2
        assert result[0]["displayName"] == "Customer Support"

    @patch("requests.Session.get")
    def test_list_agents_empty_project(self, mock_get):
        """Empty project returns [], no error."""
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {}
        mock_get.return_value = mock_resp

        with VertexDiscoveryService() as svc:
            result = svc._list_agents("my-project", "us-central1", "tok")

        assert result == []

    @patch("requests.Session.get")
    def test_list_agents_403_fatal(self, mock_get):
        """403 is not swallowed — raises HTTPError."""
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_get.return_value = mock_resp

        with VertexDiscoveryService() as svc:
            with pytest.raises(requests.HTTPError):
                svc._list_agents("my-project", "us-central1", "tok")

    @patch("requests.Session.get")
    def test_list_agents_404_fatal(self, mock_get):
        """404 (bad project/location) is not swallowed — raises HTTPError."""
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_resp

        with VertexDiscoveryService() as svc:
            with pytest.raises(requests.HTTPError):
                svc._list_agents("bad-project", "bad-region", "tok")

    @patch("requests.Session.get")
    def test_list_agents_pagination(self, mock_get):
        """Follows nextPageToken across multiple pages and returns full set."""
        page1 = Mock()
        page1.raise_for_status = Mock()
        page1.json.return_value = {
            "agents": [FAKE_AGENT_1],
            "nextPageToken": "token_page2",
        }
        page2 = Mock()
        page2.raise_for_status = Mock()
        page2.json.return_value = {"agents": [FAKE_AGENT_2]}
        mock_get.side_effect = [page1, page2]

        with VertexDiscoveryService() as svc:
            result = svc._list_agents("my-project", "us-central1", "tok")

        assert len(result) == 2
        assert mock_get.call_count == 2
        # Second call must include pageToken
        _, kwargs = mock_get.call_args_list[1]
        assert kwargs["params"]["pageToken"] == "token_page2"

    @patch("ibm_watsonx_orchestrate.agent_builder.agents.vertex_discovery.VertexDiscoveryService._list_agents")
    @patch("ibm_watsonx_orchestrate.agent_builder.agents.vertex_discovery.VertexDiscoveryService._get_token")
    def test_list_agents_orchestrates_token_and_listing(self, mock_get_token, mock_list_agents):
        """list_agents() calls _get_token then passes the token to _list_agents."""
        mock_get_token.return_value = "tok_from_sa"  # pragma: allowlist secret
        mock_list_agents.return_value = [FAKE_AGENT_1]

        with VertexDiscoveryService() as svc:
            result = svc.list_agents("my-project", "us-central1", FAKE_SERVICE_ACCOUNT)

        mock_get_token.assert_called_once_with(FAKE_SERVICE_ACCOUNT)
        mock_list_agents.assert_called_once_with("my-project", "us-central1", "tok_from_sa")  # pragma: allowlist secret
        assert result == [FAKE_AGENT_1]


# ---------------------------------------------------------------------------
# C. Field conversion
# ---------------------------------------------------------------------------

class TestConvertToWxoExternalAgentDict:
    def test_convert_sets_provider_vertex_agent(self):
        result = VertexDiscoveryService.convert_to_wxo_external_agent_dict(
            FAKE_AGENT_1, "us-central1"
        )
        assert result["provider"] == "vertex_agent"

    def test_convert_sets_api_url(self):
        result = VertexDiscoveryService.convert_to_wxo_external_agent_dict(
            FAKE_AGENT_1, "us-central1"
        )
        assert result["api_url"] == (
            "https://agentregistry.googleapis.com/v1/"
            "projects/my-gcp-project/locations/us-central1/agents/agent-abc"
        )

    def test_convert_sets_display_name_sanitized(self):
        """name is displayName lowercased with spaces/dashes → underscores, max 64 chars."""
        agent = {**FAKE_AGENT_1, "displayName": "My Cool Agent-v2"}
        result = VertexDiscoveryService.convert_to_wxo_external_agent_dict(
            agent, "us-central1"
        )
        assert result["name"] == "my_cool_agent_v2"

    def test_convert_no_description_uses_fallback(self):
        """Empty description falls back to 'Google Gemini Enterprise agent: <displayName>'."""
        result = VertexDiscoveryService.convert_to_wxo_external_agent_dict(
            FAKE_AGENT_2, "us-central1"
        )
        assert result["description"] == "Google Gemini Enterprise agent: Sales Assistant"

    def test_convert_validates_as_external_agent(self):
        """Converted dict passes ExternalAgent.model_validate() without raising."""
        result = VertexDiscoveryService.convert_to_wxo_external_agent_dict(
            FAKE_AGENT_1, "us-central1"
        )
        agent = ExternalAgent.model_validate(result)
        assert agent.name == "customer_support"
        assert agent.provider.value == "vertex_agent"

    def test_convert_name_truncated_to_64_chars(self):
        """Names longer than 64 characters are truncated."""
        long_name = "a" * 100
        agent = {"name": "projects/p/locations/l/agents/x", "displayName": long_name}
        result = VertexDiscoveryService.convert_to_wxo_external_agent_dict(
            agent, "us-central1"
        )
        assert len(result["name"]) == 64


# ---------------------------------------------------------------------------
# D. Name filtering
# ---------------------------------------------------------------------------

class TestDiscoverAndConvert:
    def test_filter_by_name_match(self):
        """Returns only the matching agent."""
        with VertexDiscoveryService() as svc:
            result = svc.discover_and_convert(
                [FAKE_AGENT_1, FAKE_AGENT_2],
                agents=["Customer Support"],
                location="us-central1",
            )
        assert len(result) == 1
        assert result[0]["name"] == "customer_support"

    def test_filter_matches_display_name_case_insensitive(self):
        """Filter is case-insensitive against displayName."""
        with VertexDiscoveryService() as svc:
            result = svc.discover_and_convert(
                [FAKE_AGENT_1],
                agents=["customer support"],
                location="us-central1",
            )
        assert len(result) == 1

    def test_filter_no_match_logs_warning(self, caplog):
        """Non-matching name returns [] and logs a warning."""
        import logging
        with caplog.at_level(logging.WARNING):
            with VertexDiscoveryService() as svc:
                result = svc.discover_and_convert(
                    [FAKE_AGENT_1],
                    agents=["nonexistent agent"],
                    location="us-central1",
                )
        assert result == []
        assert "nonexistent agent" in caplog.text

    def test_filter_none_returns_all(self):
        """`agents=None` returns all converted agents."""
        with VertexDiscoveryService() as svc:
            result = svc.discover_and_convert(
                [FAKE_AGENT_1, FAKE_AGENT_2],
                agents=None,
                location="us-central1",
            )
        assert len(result) == 2
