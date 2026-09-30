"""
Unit tests for BedrockDiscoveryService.

All HTTP is mocked — no real AWS credentials required.
Pattern mirrors tests/agent_builder/agent/test_vertex_discovery.py.
"""
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from ibm_watsonx_orchestrate.agent_builder.agents.external_agent import ExternalAgent
from ibm_watsonx_orchestrate.agent_builder.agents.bedrock_discovery import (
    BedrockDiscoveryService,
    _BEDROCK_AGENT_ENDPOINT,
    _BEDROCK_RUNTIME_ENDPOINT,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_REGION = "us-east-1"
FAKE_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"  # pragma: allowlist secret
FAKE_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"  # pragma: allowlist secret

FAKE_AGENT_1 = {
    "agentId": "ABCDEF1234",
    "agentName": "Customer Support",
    "description": "Handles customer queries",
    "agentStatus": "PREPARED",
}

FAKE_AGENT_2 = {
    "agentId": "XYZXYZ5678",
    "agentName": "Sales Assistant",
    "description": "",
    "agentStatus": "PREPARED",
}


def _make_prepared_request():
    """Return a minimal PreparedRequest stub."""
    r = requests.Request("GET", "https://example.com").prepare()
    return r


# ---------------------------------------------------------------------------
# A. Auth / SigV4 signing
# ---------------------------------------------------------------------------

class TestSignRequest:
    def test_sign_request_returns_prepared_request(self):
        """_sign_request() returns a PreparedRequest with Authorization header."""
        with BedrockDiscoveryService() as svc:
            prepared = svc._sign_request(
                method="GET",
                url=f"https://bedrock-agent.{FAKE_REGION}.amazonaws.com/agents/",
                region=FAKE_REGION,
                access_key_id=FAKE_ACCESS_KEY,
                secret_access_key=FAKE_SECRET_KEY,
            )
        assert isinstance(prepared, requests.PreparedRequest)
        assert "Authorization" in prepared.headers

    def test_sign_request_includes_amz_date_header(self):
        """SigV4 signing populates x-amz-date."""
        with BedrockDiscoveryService() as svc:
            prepared = svc._sign_request(
                method="GET",
                url=f"https://bedrock-agent.{FAKE_REGION}.amazonaws.com/agents/",
                region=FAKE_REGION,
                access_key_id=FAKE_ACCESS_KEY,
                secret_access_key=FAKE_SECRET_KEY,
            )
        assert "X-Amz-Date" in prepared.headers

    def test_sign_request_with_session_token_includes_security_token(self):
        """When session_token is provided, x-amz-security-token is set."""
        with BedrockDiscoveryService() as svc:
            prepared = svc._sign_request(
                method="GET",
                url=f"https://bedrock-agent.{FAKE_REGION}.amazonaws.com/agents/",
                region=FAKE_REGION,
                access_key_id=FAKE_ACCESS_KEY,
                secret_access_key=FAKE_SECRET_KEY,
                session_token="my-session-token",
            )
        assert "X-Amz-Security-Token" in prepared.headers

    def test_sign_request_authorization_contains_access_key(self):
        """Authorization header contains the access key ID."""
        with BedrockDiscoveryService() as svc:
            prepared = svc._sign_request(
                method="GET",
                url=f"https://bedrock-agent.{FAKE_REGION}.amazonaws.com/agents/",
                region=FAKE_REGION,
                access_key_id=FAKE_ACCESS_KEY,
                secret_access_key=FAKE_SECRET_KEY,
            )
        assert FAKE_ACCESS_KEY in prepared.headers["Authorization"]

    def test_sign_request_authorization_contains_region(self):
        """Authorization header contains the region string."""
        with BedrockDiscoveryService() as svc:
            prepared = svc._sign_request(
                method="GET",
                url=f"https://bedrock-agent.{FAKE_REGION}.amazonaws.com/agents/",
                region=FAKE_REGION,
                access_key_id=FAKE_ACCESS_KEY,
                secret_access_key=FAKE_SECRET_KEY,
            )
        assert FAKE_REGION in prepared.headers["Authorization"]

    def test_sign_request_params_baked_into_url_before_signing(self):
        """Query-string params must appear in the signed URL so the signature covers them.

        botocore.AWSRequest does NOT embed params into .url when passed via the
        ``params`` kwarg — the URL stays as the base URL and the signature is
        computed without the query string.  The fix builds the full URL with
        urlencode() before passing to AWSRequest, so both the signed canonical
        request and the sent PreparedRequest.url contain the query string.
        """
        params = {"nextToken": "tok123"}
        with BedrockDiscoveryService() as svc:
            prepared = svc._sign_request(
                method="GET",
                url=f"https://bedrock-agent.{FAKE_REGION}.amazonaws.com/agents/",
                region=FAKE_REGION,
                access_key_id=FAKE_ACCESS_KEY,
                secret_access_key=FAKE_SECRET_KEY,
                params=params,
            )
        # The sent URL must contain the query string
        assert "nextToken=tok123" in prepared.url
        # The Authorization credential scope must reference the correct service name
        assert "bedrock-agent" in prepared.headers["Authorization"]

    def test_sign_request_service_name_is_bedrock_agent(self):
        """Authorization credential scope must use service name 'bedrock-agent', not 'bedrock'."""
        with BedrockDiscoveryService() as svc:
            prepared = svc._sign_request(
                method="GET",
                url=f"https://bedrock-agent.{FAKE_REGION}.amazonaws.com/agents/",
                region=FAKE_REGION,
                access_key_id=FAKE_ACCESS_KEY,
                secret_access_key=FAKE_SECRET_KEY,
            )
        assert "bedrock-agent" in prepared.headers["Authorization"]


# ---------------------------------------------------------------------------
# B. Agent listing
# ---------------------------------------------------------------------------

class TestListAgents:
    @patch("ibm_watsonx_orchestrate.agent_builder.agents.bedrock_discovery.BedrockDiscoveryService._sign_request")
    def test_list_agents_success(self, mock_sign):
        """Returns list of agentSummary dicts on success."""
        mock_sign.return_value = _make_prepared_request()

        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {"agentSummaries": [FAKE_AGENT_1, FAKE_AGENT_2]}

        with BedrockDiscoveryService() as svc:
            svc.session.send = Mock(return_value=mock_resp)
            result = svc._list_agents(FAKE_REGION, FAKE_ACCESS_KEY, FAKE_SECRET_KEY)

        assert len(result) == 2
        assert result[0]["agentName"] == "Customer Support"

    @patch("ibm_watsonx_orchestrate.agent_builder.agents.bedrock_discovery.BedrockDiscoveryService._sign_request")
    def test_list_agents_empty_account(self, mock_sign):
        """Empty account returns [], no error."""
        mock_sign.return_value = _make_prepared_request()

        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.json.return_value = {}

        with BedrockDiscoveryService() as svc:
            svc.session.send = Mock(return_value=mock_resp)
            result = svc._list_agents(FAKE_REGION, FAKE_ACCESS_KEY, FAKE_SECRET_KEY)

        assert result == []

    @patch("ibm_watsonx_orchestrate.agent_builder.agents.bedrock_discovery.BedrockDiscoveryService._sign_request")
    def test_list_agents_403_fatal(self, mock_sign):
        """403 is not swallowed — raises HTTPError."""
        mock_sign.return_value = _make_prepared_request()

        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")

        with BedrockDiscoveryService() as svc:
            svc.session.send = Mock(return_value=mock_resp)
            with pytest.raises(requests.HTTPError):
                svc._list_agents(FAKE_REGION, FAKE_ACCESS_KEY, FAKE_SECRET_KEY)

    @patch("ibm_watsonx_orchestrate.agent_builder.agents.bedrock_discovery.BedrockDiscoveryService._sign_request")
    def test_list_agents_404_fatal(self, mock_sign):
        """404 (bad region) is not swallowed — raises HTTPError."""
        mock_sign.return_value = _make_prepared_request()

        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        with BedrockDiscoveryService() as svc:
            svc.session.send = Mock(return_value=mock_resp)
            with pytest.raises(requests.HTTPError):
                svc._list_agents("bad-region", FAKE_ACCESS_KEY, FAKE_SECRET_KEY)

    @patch("ibm_watsonx_orchestrate.agent_builder.agents.bedrock_discovery.BedrockDiscoveryService._sign_request")
    def test_list_agents_pagination(self, mock_sign):
        """Follows nextToken across multiple pages and returns full set."""
        mock_sign.return_value = _make_prepared_request()

        page1 = Mock()
        page1.raise_for_status = Mock()
        page1.json.return_value = {
            "agentSummaries": [FAKE_AGENT_1],
            "nextToken": "token_page2",
        }
        page2 = Mock()
        page2.raise_for_status = Mock()
        page2.json.return_value = {"agentSummaries": [FAKE_AGENT_2]}

        with BedrockDiscoveryService() as svc:
            svc.session.send = Mock(side_effect=[page1, page2])
            result = svc._list_agents(FAKE_REGION, FAKE_ACCESS_KEY, FAKE_SECRET_KEY)

        assert len(result) == 2
        # second call must include nextToken in params
        second_sign_call = mock_sign.call_args_list[1]
        assert second_sign_call[1]["params"]["nextToken"] == "token_page2"

    @patch("ibm_watsonx_orchestrate.agent_builder.agents.bedrock_discovery.BedrockDiscoveryService._list_agents")
    def test_list_agents_delegates_to_internal(self, mock_list_internal):
        """list_agents() delegates to _list_agents() with the same arguments."""
        mock_list_internal.return_value = [FAKE_AGENT_1]

        with BedrockDiscoveryService() as svc:
            result = svc.list_agents(FAKE_REGION, FAKE_ACCESS_KEY, FAKE_SECRET_KEY)

        mock_list_internal.assert_called_once_with(
            region=FAKE_REGION,
            access_key_id=FAKE_ACCESS_KEY,
            secret_access_key=FAKE_SECRET_KEY,
            session_token=None,
        )
        assert result == [FAKE_AGENT_1]


# ---------------------------------------------------------------------------
# C. Field conversion
# ---------------------------------------------------------------------------

class TestConvertToWxoExternalAgentDict:
    def test_convert_sets_provider_bedrock_agent(self):
        result = BedrockDiscoveryService.convert_to_wxo_external_agent_dict(
            FAKE_AGENT_1, FAKE_REGION
        )
        assert result["provider"] == "bedrock_agent"

    def test_convert_sets_api_url(self):
        result = BedrockDiscoveryService.convert_to_wxo_external_agent_dict(
            FAKE_AGENT_1, FAKE_REGION
        )
        assert result["api_url"] == (
            f"https://bedrock-agent-runtime.{FAKE_REGION}.amazonaws.com"
            f"/agents/ABCDEF1234/agentAliases/TSTALIASID/"
        )

    def test_convert_sets_display_name_sanitized(self):
        """name is agentName lowercased with spaces/dashes → underscores, max 64 chars."""
        agent = {**FAKE_AGENT_1, "agentName": "My Cool Agent-v2"}
        result = BedrockDiscoveryService.convert_to_wxo_external_agent_dict(
            agent, FAKE_REGION
        )
        assert result["name"] == "my_cool_agent_v2"

    def test_convert_no_description_uses_fallback(self):
        """Empty description falls back to 'AWS Bedrock agent: <agentName>'."""
        result = BedrockDiscoveryService.convert_to_wxo_external_agent_dict(
            FAKE_AGENT_2, FAKE_REGION
        )
        assert result["description"] == "AWS Bedrock agent: Sales Assistant"

    def test_convert_validates_as_external_agent(self):
        """Converted dict passes ExternalAgent.model_validate() without raising."""
        result = BedrockDiscoveryService.convert_to_wxo_external_agent_dict(
            FAKE_AGENT_1, FAKE_REGION
        )
        agent = ExternalAgent.model_validate(result)
        assert agent.name == "customer_support"
        assert agent.provider.value == "bedrock_agent"

    def test_convert_name_truncated_to_64_chars(self):
        """Names longer than 64 characters are truncated."""
        long_name = "a" * 100
        agent = {"agentId": "ID123", "agentName": long_name}
        result = BedrockDiscoveryService.convert_to_wxo_external_agent_dict(
            agent, FAKE_REGION
        )
        assert len(result["name"]) == 64


# ---------------------------------------------------------------------------
# D. Name filtering
# ---------------------------------------------------------------------------

class TestDiscoverAndConvert:
    def test_filter_by_name_match(self):
        """Returns only the matching agent."""
        with BedrockDiscoveryService() as svc:
            result = svc.discover_and_convert(
                [FAKE_AGENT_1, FAKE_AGENT_2],
                agents=["Customer Support"],
                region=FAKE_REGION,
            )
        assert len(result) == 1
        assert result[0]["name"] == "customer_support"

    def test_filter_matches_agent_name_case_insensitive(self):
        """Filter is case-insensitive against agentName."""
        with BedrockDiscoveryService() as svc:
            result = svc.discover_and_convert(
                [FAKE_AGENT_1],
                agents=["customer support"],
                region=FAKE_REGION,
            )
        assert len(result) == 1

    def test_filter_no_match_logs_warning(self, caplog):
        """Non-matching name returns [] and logs a warning."""
        import logging
        with caplog.at_level(logging.WARNING):
            with BedrockDiscoveryService() as svc:
                result = svc.discover_and_convert(
                    [FAKE_AGENT_1],
                    agents=["nonexistent agent"],
                    region=FAKE_REGION,
                )
        assert result == []
        assert "nonexistent agent" in caplog.text

    def test_filter_none_returns_all(self):
        """`agents=None` returns all converted agents."""
        with BedrockDiscoveryService() as svc:
            result = svc.discover_and_convert(
                [FAKE_AGENT_1, FAKE_AGENT_2],
                agents=None,
                region=FAKE_REGION,
            )
        assert len(result) == 2

    def test_empty_agent_name_falls_back_to_agent_id(self):
        """agentName='' produces name='bedrock_agent_<agentId>'."""
        agent = {"agentId": "ID999", "agentName": ""}
        with BedrockDiscoveryService() as svc:
            result = svc.discover_and_convert([agent], agents=None, region=FAKE_REGION)
        assert result[0]["name"] == "bedrock_agent_id999"

    def test_all_hyphen_agent_name_falls_back_to_agent_id(self):
        """agentName='---' → sanitized='___' → falls back to bedrock_agent_<agentId>."""
        agent = {"agentId": "ID888", "agentName": "---"}
        with BedrockDiscoveryService() as svc:
            result = svc.discover_and_convert([agent], agents=None, region=FAKE_REGION)
        assert result[0]["name"] == "bedrock_agent_id888"
