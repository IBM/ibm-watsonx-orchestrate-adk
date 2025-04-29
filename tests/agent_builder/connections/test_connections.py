from ibm_watsonx_orchestrate.agent_builder.connections.connections import _clean_env_vars, _build_credentials_model, _validate_schema_type, _get_credentials_model, get_application_connection_credentials, get_connection_type
from unittest.mock import patch
import os
import pytest
from ibm_watsonx_orchestrate.agent_builder.connections.types import (
    BasicAuthCredentials,
    BearerTokenAuthCredentials,
    APIKeyAuthCredentials,
    OAuth2TokenCredentials,
    # OAuth2AuthCodeCredentials,
    # OAuth2ImplicitCredentials,
    # OAuth2PasswordCredentials,
    # OAuth2ClientCredentials,
    OAuthOnBehalfOfCredentials,
    KeyValueConnectionCredentials,
    ConnectionType
)

TEST_APP_ID = "testing"
TEST_VAR_PREFIX = f"WXO_CONNECTION_{TEST_APP_ID}_"

ALL_CONNECTION_TYPES = [
        ConnectionType.BASIC_AUTH,
        ConnectionType.BEARER_TOKEN,
        ConnectionType.API_KEY_AUTH,
        # ConnectionType.OAUTH2_AUTH_CODE,
        # ConnectionType.OAUTH2_IMPLICIT,
        # ConnectionType.OAUTH2_PASSWORD,
        # ConnectionType.OAUTH2_CLIENT_CREDS,
        ConnectionType.OAUTH_ON_BEHALF_OF_FLOW,
        ]

@pytest.fixture()
def connection_env_vars():
    return {
        f"{TEST_VAR_PREFIX}username": "Test Username",
        f"{TEST_VAR_PREFIX}password": "Test Password",
        f"{TEST_VAR_PREFIX}token": "Test Token",
        f"{TEST_VAR_PREFIX}access_token": "Test Token",
        f"{TEST_VAR_PREFIX}api_key": "Test API Key",
        f"{TEST_VAR_PREFIX}url": "Test URL",
        f"WXO_CONNECTION_{TEST_APP_ID}_kv_Foo": "Test Foo",
        f"WXO_CONNECTION_{TEST_APP_ID}_kv_bar": "Test bar",
    }

@pytest.fixture()
def mock_env(monkeypatch, connection_env_vars):
    with patch.dict(os.environ, clear=True):
        envvars = connection_env_vars
        for k, v in envvars.items():
            monkeypatch.setenv(k, v)
        yield

class TestCleanEnvVars:

    @pytest.mark.parametrize(
            ("requirements", "expected_values"),
            [
                (["username", "password", "url"], ["Test Username", "Test Password", "Test URL"]),
                (["token", "url"], ["Test Token", "Test URL"]),
                (["api_key", "url"], ["Test API Key", "Test URL"]),
                (["url"],["Test URL"])
            ]
    )
    def test_clean_env_vars(self, requirements, expected_values, connection_env_vars):
        cleaned_dict = _clean_env_vars(vars=connection_env_vars, requirements=requirements, app_id=TEST_APP_ID)
        assert len(list(cleaned_dict.keys())) == len(requirements)

        for requirement in requirements:
            assert f"{TEST_VAR_PREFIX}{requirement}" in list(cleaned_dict.keys())
        
        assert list(cleaned_dict.values()) == expected_values
    
    @pytest.mark.parametrize(
            ("requirements"),
            [
                ["TEST1", "TEST2"],
                ["TOKEN", "TEST1"],
            ]
    )
    def test_clean_env_vars_missing_requirements(self, requirements, connection_env_vars, caplog):
        expected_missing_requirements = []
        for requirement in requirements:
            if f"{TEST_VAR_PREFIX}{requirement}" not in connection_env_vars:
                expected_missing_requirements.append(f"{TEST_VAR_PREFIX}{requirement}")
        
        with pytest.raises(ValueError) as e:
            cleaned_dict = _clean_env_vars(vars=connection_env_vars, requirements=requirements, app_id=TEST_APP_ID)

        expected_missing_requirements_str = ", ".join(expected_missing_requirements)
        message = f"Missing requirement environment variables '{expected_missing_requirements_str}' for connection '{TEST_APP_ID}'"
        assert message in str(e)

        captured = caplog.text
        assert message in captured

class TestBuildCredentialsModel:

    @pytest.mark.parametrize(
            ("expected_connection", "app_id"),
            [
                (BasicAuthCredentials(**{"username": "Test Username", "password": "Test Password", "url": "Test URL"}), TEST_APP_ID),
                (BearerTokenAuthCredentials(**{"token": "Test Token", "url": "Test URL"}), TEST_APP_ID),
                (APIKeyAuthCredentials(**{"api_key": "Test API Key", "url": "Test URL"}), TEST_APP_ID),
                (KeyValueConnectionCredentials({"Foo": "Test Foo", "bar": "Test bar"}), f"{TEST_APP_ID}_kv"),
            ]
    )
    def test_build_credentials_model(self, expected_connection, app_id, connection_env_vars):
        base_prefix = f"WXO_CONNECTION_{app_id}_"
        env_vars = {}
        for key in connection_env_vars:
            if key.startswith(base_prefix):
                env_vars[key] = connection_env_vars[key]

        conn = _build_credentials_model(type(expected_connection), env_vars, base_prefix)
        
        assert conn == expected_connection

class TestValidateSchemaType:
    @pytest.mark.parametrize(
            ("requested_type", "expected_type"),
            [
                (ConnectionType.BASIC_AUTH, ConnectionType.BASIC_AUTH),
                (ConnectionType.BEARER_TOKEN, ConnectionType.BEARER_TOKEN),
                (ConnectionType.API_KEY_AUTH, ConnectionType.API_KEY_AUTH),
                # (ConnectionType.OAUTH2_AUTH_CODE, ConnectionType.OAUTH2_AUTH_CODE),
                # (ConnectionType.OAUTH2_IMPLICIT, ConnectionType.OAUTH2_IMPLICIT),
                # (ConnectionType.OAUTH2_PASSWORD, ConnectionType.OAUTH2_PASSWORD),
                # (ConnectionType.OAUTH2_CLIENT_CREDS, ConnectionType.OAUTH2_CLIENT_CREDS),
                (ConnectionType.OAUTH_ON_BEHALF_OF_FLOW, ConnectionType.OAUTH_ON_BEHALF_OF_FLOW),
                (ConnectionType.KEY_VALUE, ConnectionType.KEY_VALUE),
            ]
    )
    def test_validate_schema_type(self, requested_type, expected_type):
        assert _validate_schema_type(requested_type=requested_type, expected_type=expected_type)
    
    @pytest.mark.parametrize(
            ("requested_type", "expected_types"),
            [
                (ConnectionType.BASIC_AUTH, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.BASIC_AUTH]),
                (ConnectionType.BEARER_TOKEN, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.BEARER_TOKEN]),
                (ConnectionType.API_KEY_AUTH, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.API_KEY_AUTH]),
                # (ConnectionType.OAUTH2_AUTH_CODE, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH2_AUTH_CODE]),
                # (ConnectionType.OAUTH2_IMPLICIT, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH2_IMPLICIT]),
                # (ConnectionType.OAUTH2_PASSWORD, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH2_PASSWORD]),
                # (ConnectionType.OAUTH2_CLIENT_CREDS, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH2_CLIENT_CREDS]),
                (ConnectionType.OAUTH_ON_BEHALF_OF_FLOW, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH_ON_BEHALF_OF_FLOW]),
                (ConnectionType.KEY_VALUE, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.KEY_VALUE]),
            ]
    )
    def test_validate_schema_type_invalid(self, requested_type, expected_types):
        for expected_type in expected_types:
            assert not _validate_schema_type(requested_type=requested_type, expected_type=expected_type)

class TestGetCredentialsModel:

    @pytest.mark.parametrize(
            ("expected_connection", "connection_type", "app_id"),
            [
                (BasicAuthCredentials(**{"username": "Test Username", "password": "Test Password", "url": "Test URL"}), ConnectionType.BASIC_AUTH, TEST_APP_ID),
                (BearerTokenAuthCredentials(**{"token": "Test Token", "url": "Test URL"}), ConnectionType.BEARER_TOKEN, TEST_APP_ID),
                (APIKeyAuthCredentials(**{"api_key": "Test API Key", "url": "Test URL"}), ConnectionType.API_KEY_AUTH, TEST_APP_ID),
                # (BearerTokenAuthCredentials(**{"token": "Test Token", "url": "Test URL"}), ConnectionType.OAUTH2_AUTH_CODE, TEST_APP_ID),
                # (BearerTokenAuthCredentials(**{"token": "Test Token", "url": "Test URL"}), ConnectionType.OAUTH2_IMPLICIT, TEST_APP_ID),
                # (BearerTokenAuthCredentials(**{"token": "Test Token", "url": "Test URL"}), ConnectionType.OAUTH2_PASSWORD, TEST_APP_ID),
                # (BearerTokenAuthCredentials(**{"token": "Test Token", "url": "Test URL"}), ConnectionType.OAUTH2_CLIENT_CREDS, TEST_APP_ID),
                (OAuth2TokenCredentials(**{"access_token": "Test Token", "url": "Test URL"}), ConnectionType.OAUTH_ON_BEHALF_OF_FLOW, TEST_APP_ID),
                (KeyValueConnectionCredentials({"Foo": "Test Foo", "bar": "Test bar"}), ConnectionType.KEY_VALUE, f"{TEST_APP_ID}_kv"),
            ]
    )
    def test_get_credentials_model(self, expected_connection, connection_type, app_id, mock_env):
        conn = _get_credentials_model(connection_type=connection_type, app_id=app_id)
        assert conn == expected_connection

class TestGetConnectionType:

    @pytest.mark.parametrize(
            ("connection_type"),
            [
                (ConnectionType.BASIC_AUTH),
                (ConnectionType.BEARER_TOKEN),
                (ConnectionType.API_KEY_AUTH),
                # (ConnectionType.OAUTH2_AUTH_CODE),
                # (ConnectionType.OAUTH2_IMPLICIT),
                # (ConnectionType.OAUTH2_PASSWORD),
                # (ConnectionType.OAUTH2_CLIENT_CREDS),
                (ConnectionType.OAUTH_ON_BEHALF_OF_FLOW),
                (ConnectionType.KEY_VALUE),

            ]
    )
    def test_get_connection_type(self, monkeypatch, connection_type):
        with patch.dict(os.environ, clear=True):
            monkeypatch.setenv(f"WXO_SECURITY_SCHEMA_{TEST_APP_ID}", connection_type.value)

            returned_connection_type = get_connection_type(TEST_APP_ID)
            assert connection_type == returned_connection_type
    
    def test_get_connection_type_missing_credentials(self, caplog):
        with pytest.raises(ValueError) as e:
            get_connection_type("fake_app_id")
        
        message = "No credentials found for connections 'fake_app_id'"
        captured = caplog.text
        assert message in str(e)
        assert message in captured
    
    @pytest.mark.parametrize(
            ("connection_type"),
            [
                "fake",
                " ",
                "None",
                "False"
            ]
    )
    def test_get_connection_type_invalid_credentials_type(self, monkeypatch, connection_type, caplog):
        with patch.dict(os.environ, clear=True):
            monkeypatch.setenv(f"WXO_SECURITY_SCHEMA_{TEST_APP_ID}", connection_type)

            with pytest.raises(ValueError) as e:
                get_connection_type(TEST_APP_ID)
            
        message = f"The expected type '{connection_type}' cannot be resolved into a valid connection auth type"
        captured = caplog.text
        assert message in str(e)
        assert message in captured

class TestGetApplicationConnectionCredentials:
    @pytest.mark.parametrize(
            ("expected_connection", "connection_type", "app_id"),
            [
                (BasicAuthCredentials(**{"username": "Test Username", "password": "Test Password", "url": "Test URL"}), ConnectionType.BASIC_AUTH, TEST_APP_ID),
                (BearerTokenAuthCredentials(**{"token": "Test Token", "url": "Test URL"}), ConnectionType.BEARER_TOKEN, TEST_APP_ID),
                (APIKeyAuthCredentials(**{"api_key": "Test API Key", "url": "Test URL"}), ConnectionType.API_KEY_AUTH, TEST_APP_ID),
                # (BearerTokenAuthCredentials(**{"token": "Test Token", "url": "Test URL"}), ConnectionType.OAUTH2_AUTH_CODE, TEST_APP_ID),
                # (BearerTokenAuthCredentials(**{"token": "Test Token", "url": "Test URL"}), ConnectionType.OAUTH2_IMPLICIT, TEST_APP_ID),
                # (BearerTokenAuthCredentials(**{"token": "Test Token", "url": "Test URL"}), ConnectionType.OAUTH2_PASSWORD, TEST_APP_ID),
                # (BearerTokenAuthCredentials(**{"token": "Test Token", "url": "Test URL"}), ConnectionType.OAUTH2_CLIENT_CREDS, TEST_APP_ID),
                (OAuth2TokenCredentials(**{"access_token": "Test Token", "url": "Test URL"}), ConnectionType.OAUTH_ON_BEHALF_OF_FLOW, TEST_APP_ID),
                (KeyValueConnectionCredentials({"Foo": "Test Foo", "bar": "Test bar"}), ConnectionType.KEY_VALUE, f"{TEST_APP_ID}_kv"),
            ]
    )
    def test_get_application_connection_credentials(self, expected_connection, app_id, connection_type, mock_env, monkeypatch):
        monkeypatch.setenv(f"WXO_SECURITY_SCHEMA_{app_id}", connection_type)
        conn = get_application_connection_credentials(type=connection_type, app_id=app_id)
        assert conn == expected_connection
    
    def test_get_application_connection_credentials_no_credentials(self, mock_env, caplog):
        with pytest.raises(ValueError) as e:
            conn = get_application_connection_credentials(type=ConnectionType.BASIC_AUTH, app_id="not_real")
        
        message = f"No credentials found for connections 'not_real'"
        captured = caplog.text
        assert message in str(e)
        assert message in captured
    
    @pytest.mark.parametrize(
            ("expected_connection", "app_id", "conn_types"),
            [
                (BasicAuthCredentials(**{"username": "Test Username", "password": "Test Password"}), TEST_APP_ID, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.BASIC_AUTH]),
                (BearerTokenAuthCredentials(**{"token": "Test Token"}), TEST_APP_ID, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.BEARER_TOKEN]),
                (APIKeyAuthCredentials(**{"api_key": "Test API Key"}), TEST_APP_ID, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.API_KEY_AUTH]),
                # (OAuth2AuthCodeCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "token_url": "Token URL", "authorization_url": "Auth URL"}), TEST_APP_ID, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH2_AUTH_CODE]),
                # (OAuth2ImplicitCredentials(**{"client_id": "Test Client ID", "authorization_url": "Auth URL"}), TEST_APP_ID, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH2_IMPLICIT]),
                # (OAuth2PasswordCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "token_url": "Token URL", "authorization_url": "Auth URL"}), TEST_APP_ID, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH2_PASSWORD]),
                # (OAuth2ClientCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "token_url": "Token URL"}), TEST_APP_ID, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH2_CLIENT_CREDS]),
                (OAuthOnBehalfOfCredentials(**{"client_id": "Test Client ID", "access_token_url": "Token URL", "grant_type": "Grant Type"}), TEST_APP_ID, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH_ON_BEHALF_OF_FLOW]),
                (KeyValueConnectionCredentials({"Foo": "Test Foo", "bar": "Test bar"}), f"{TEST_APP_ID}_kv", [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.KEY_VALUE]),
            ]
    )
    def test_get_application_connection_credentials_invalid_type(self, expected_connection, app_id, conn_types, mock_env, monkeypatch, caplog):
        for conn_type in conn_types:
            monkeypatch.setenv(f"WXO_SECURITY_SCHEMA_{app_id}", conn_type)
            with pytest.raises(ValueError) as e:
                conn = get_application_connection_credentials(type=type(expected_connection), app_id=app_id)
            
            message = f"The requested type '{type(expected_connection).__name__}' does not match the type '{conn_type.value}' for the connection '{app_id}'"
            captured = caplog.text
            assert message in str(e)
            assert message in captured