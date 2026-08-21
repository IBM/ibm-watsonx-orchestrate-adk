import base64
import pytest
from unittest.mock import MagicMock, patch
from ibm_watsonx_orchestrate_clients.common.service_instance.service_instance import ServiceInstance, _ScopelessMCSPV2TokenManager
from ibm_watsonx_orchestrate_core.types.environment import EnvironmentAuthType


def _make_mcsp_key(version: str) -> str:
    """Return a base64-encoded fake MCSP key for the given version prefix ('k1:' or 'k2:')."""
    return base64.b64encode(f"{version}some-uuid:token-data".encode()).decode()


def _make_service_instance(wxo_url, api_key="test-iam-token", auth_type=None):  # pragma: allowlist secret
    """Build a ServiceInstance with a fake client, bypassing token acquisition."""
    credentials = MagicMock()
    credentials.url = wxo_url
    credentials.api_key = api_key
    credentials.auth_type = auth_type

    client = MagicMock()
    client.credentials = credentials
    client.token = "existing-token"

    # Patch _get_token so __init__ doesn't try to acquire a real token
    with patch.object(ServiceInstance, "_get_token", return_value="existing-token"):
        instance = ServiceInstance(client)

    return instance


class TestInferAuthType:
    def test_ibm_cloud_iam(self):
        """IBM Cloud URL always routes to IAM regardless of key type."""
        si = _make_service_instance("https://us-south.ml.cloud.ibm.com/instances/abc")
        assert si._infer_auth_type() == EnvironmentAuthType.IBM_CLOUD_IAM

    def test_cpd(self):
        """CPD URL always routes to CPD regardless of key type."""
        si = _make_service_instance("https://cpd.example.com/orchestrate/abc")
        assert si._infer_auth_type() == EnvironmentAuthType.CPD

    def test_mcsp_v2_k2_key(self):
        """k2 API key (MCSP v2) should infer MCSP_V2 directly — no IAM URL needed."""
        si = _make_service_instance(
            wxo_url="https://api.germanywestcentral.watson-orchestrate.ibm.com/instances/abc",
            api_key=_make_mcsp_key("k2:"),
        )
        assert si._infer_auth_type() == EnvironmentAuthType.MCSP_V2

    def test_mcsp_v1_k1_key(self):
        """k1 API key (MCSP v1) should infer MCSP."""
        si = _make_service_instance(
            wxo_url="https://api.us-east-1.watson-orchestrate.ibm.com/instances/abc",
            api_key=_make_mcsp_key("k1:"),
        )
        assert si._infer_auth_type() == EnvironmentAuthType.MCSP

    def test_non_mcsp_key_fallback(self):
        """A non-MCSP key (plain IAM key) should fall back to generic MCSP."""
        si = _make_service_instance(
            wxo_url="https://api.us-east-1.watson-orchestrate.ibm.com/instances/abc",
            api_key="some-plain-iam-api-key",  # pragma: allowlist secret
        )
        assert si._infer_auth_type() == EnvironmentAuthType.MCSP

    def test_no_api_key_fallback(self):
        """No API key should fall back to generic MCSP."""
        si = _make_service_instance(
            wxo_url="https://api.germanywestcentral.watson-orchestrate.ibm.com/instances/abc",
            api_key=None,
        )
        assert si._infer_auth_type() == EnvironmentAuthType.MCSP


class TestGetAuthenticatorMcspV2:
    def test_mcsp_v2_uses_scopeless_token_manager(self):
        """MCSP v2 authenticator must use the scopeless token manager (no scope in URL path)."""
        si = _make_service_instance(
            wxo_url="https://api.germanywestcentral.watson-orchestrate.ibm.com/instances/abc",
            api_key=_make_mcsp_key("k2:"),
        )
        si._credentials.iam_url = None
        authenticator = si._get_authenticator(EnvironmentAuthType.MCSP_V2)
        assert isinstance(authenticator.token_manager, _ScopelessMCSPV2TokenManager)

    def test_mcsp_v2_token_url_is_scopeless(self):
        """The token request URL must be /api/2.0/apikeys/token with no scope path segments."""
        si = _make_service_instance(
            wxo_url="https://api.germanywestcentral.watson-orchestrate.ibm.com/instances/abc",
            api_key=_make_mcsp_key("k2:"),
        )
        si._credentials.iam_url = "https://account-iam.azure.westus3.platform.saas.ibm.com"
        authenticator = si._get_authenticator(EnvironmentAuthType.MCSP_V2)
        tm = authenticator.token_manager
        expected_url = "https://account-iam.azure.westus3.platform.saas.ibm.com/api/2.0/apikeys/token"
        assert tm.url + tm.OPERATION_PATH == expected_url

    def test_mcsp_v2_infers_azure_iam_url_from_wxo_url(self):
        """When no iam_url is set, the IAM URL is inferred from the WXO hostname."""
        si = _make_service_instance(
            wxo_url="https://api.germanywestcentral.watson-orchestrate.ibm.com/instances/abc",
            api_key=_make_mcsp_key("k2:"),
        )
        si._credentials.iam_url = None
        authenticator = si._get_authenticator(EnvironmentAuthType.MCSP_V2)
        tm = authenticator.token_manager
        assert tm.url == "https://account-iam.azure.westus3.platform.saas.ibm.com"
        assert tm.OPERATION_PATH == "/api/2.0/apikeys/token"

    def test_mcsp_v2_unknown_region_falls_back_to_global_default(self):
        """An unrecognised WXO region falls back to the global MCSP v2 IAM URL."""
        si = _make_service_instance(
            wxo_url="https://api.someunknownregion.watson-orchestrate.ibm.com/instances/abc",
            api_key=_make_mcsp_key("k2:"),
        )
        si._credentials.iam_url = None
        authenticator = si._get_authenticator(EnvironmentAuthType.MCSP_V2)
        tm = authenticator.token_manager
        assert tm.url == "https://account-iam.platform.saas.ibm.com"
        assert tm.OPERATION_PATH == "/api/2.0/apikeys/token"
