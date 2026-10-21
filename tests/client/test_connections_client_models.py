import pytest

from ibm_watsonx_orchestrate_clients.connections.connections_client import ListConfigsResponse
from ibm_watsonx_orchestrate_core.types.connections import ConnectionSecurityScheme, ConnectionType, ConnectionAuthType
from ibm_watsonx_orchestrate.client.connections.utils import get_connection_type


class TestListConfigsResponseSecurityScheme:
    @pytest.mark.parametrize("scheme", [e.value for e in ConnectionSecurityScheme])
    def test_known_schemes_resolve_to_enum(self, scheme):
        res = ListConfigsResponse.model_validate({"app_id": "app", "security_scheme": scheme})
        assert res.security_scheme == ConnectionSecurityScheme(scheme)
        assert isinstance(res.security_scheme, ConnectionSecurityScheme)

    def test_custom_schema_is_known(self):
        res = ListConfigsResponse.model_validate({"app_id": "app", "security_scheme": "custom_schema"})
        assert res.security_scheme == ConnectionSecurityScheme.CUSTOM

    def test_unknown_scheme_does_not_raise(self):
        res = ListConfigsResponse.model_validate({"app_id": "app", "security_scheme": "some_future_scheme"})
        assert res.security_scheme == "some_future_scheme"

    def test_missing_scheme_defaults_to_none(self):
        res = ListConfigsResponse.model_validate({"app_id": "app"})
        assert res.security_scheme is None
        assert res.connection_id is None
        assert res.environment is None


class TestGetConnectionType:
    def test_returns_none_for_custom_schema(self):
        assert get_connection_type(ConnectionSecurityScheme.CUSTOM, None) is None

    def test_returns_none_for_unknown_scheme(self):
        assert get_connection_type("some_future_scheme", None) is None

    def test_known_scheme_still_resolves(self):
        assert get_connection_type(ConnectionSecurityScheme.BASIC_AUTH, None) == ConnectionType.BASIC_AUTH

    def test_oauth2_resolves_via_auth_type(self):
        assert get_connection_type(ConnectionSecurityScheme.OAUTH2, ConnectionAuthType.OAUTH2_AUTH_CODE) == ConnectionType.OAUTH2_AUTH_CODE

    def test_both_none_returns_none(self):
        assert get_connection_type(None, None) is None
