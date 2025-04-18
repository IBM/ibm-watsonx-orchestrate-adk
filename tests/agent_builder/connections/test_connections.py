from ibm_watsonx_orchestrate.agent_builder.connections.connections import _clean_env_vars, _build_credentials_model, _validate_schema_type, _get_credentials_model, get_application_connection_credentials
from unittest.mock import patch
import os
import pytest
from ibm_watsonx_orchestrate.client.connections import (
    BasicAuthCredentials,
    BearerTokenAuthCredentials,
    APIKeyAuthCredentials,
    OAuth2AuthCodeCredentials,
    OAuth2ImplicitCredentials,
    OAuth2PasswordCredentials,
    OAuth2ClientCredentials,
    KeyValueConnectionCredentials,
    ConnectionType
)
from ibm_watsonx_orchestrate.utils.request import BadRequest

TEST_APP_ID = "testing"
TEST_VAR_PREFIX = f"WXO_CONNECTION_{TEST_APP_ID}_"

ALL_CONNECTION_TYPES = [
        ConnectionType.BASIC_AUTH,
        ConnectionType.BEARER_TOKEN,
        ConnectionType.API_KEY_AUTH,
        ConnectionType.OAUTH2_AUTH_CODE,
        ConnectionType.OAUTH2_IMPLICIT,
        ConnectionType.OAUTH2_PASSWORD,
        ConnectionType.OAUTH2_CLIENT_CREDS,
        ConnectionType.OAUTH2_IMPLICIT,
        ]

@pytest.fixture()
def connection_env_vars():
    return {
        f"{TEST_VAR_PREFIX}username": "Test Username",
        f"{TEST_VAR_PREFIX}password": "Test Password",
        f"{TEST_VAR_PREFIX}token": "Test Token",
        f"{TEST_VAR_PREFIX}api_key": "Test API Key",
        f"{TEST_VAR_PREFIX}client_id": "Test Client ID",
        f"{TEST_VAR_PREFIX}client_secret": "Test Client Secret",
        f"{TEST_VAR_PREFIX}well_known_url": "Test Well Known URL",
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
                (["username", "password"], ["Test Username", "Test Password"]),
                (["token"], ["Test Token"]),
                ([],[])
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
        
        with pytest.raises(BadRequest) as e:
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
                (BasicAuthCredentials(**{"username": "Test Username", "password": "Test Password"}), TEST_APP_ID),
                (BearerTokenAuthCredentials(**{"token": "Test Token"}), TEST_APP_ID),
                (APIKeyAuthCredentials(**{"api_key": "Test API Key"}), TEST_APP_ID),
                (OAuth2AuthCodeCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL"}), TEST_APP_ID),
                (OAuth2ImplicitCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL"}), TEST_APP_ID),
                (OAuth2PasswordCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL", "username": "Test Username", "password": "Test Password"}), TEST_APP_ID),
                (OAuth2ClientCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL"}), TEST_APP_ID),
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
                (BasicAuthCredentials, ConnectionType.BASIC_AUTH),
                (BearerTokenAuthCredentials, ConnectionType.BEARER_TOKEN),
                (APIKeyAuthCredentials, ConnectionType.API_KEY_AUTH),
                (OAuth2AuthCodeCredentials, ConnectionType.OAUTH2_AUTH_CODE),
                (OAuth2ImplicitCredentials, ConnectionType.OAUTH2_IMPLICIT),
                (OAuth2PasswordCredentials, ConnectionType.OAUTH2_PASSWORD),
                (OAuth2ClientCredentials, ConnectionType.OAUTH2_CLIENT_CREDS),
                (KeyValueConnectionCredentials, ConnectionType.KEY_VALUE),
            ]
    )
    def test_validate_schema_type(self, requested_type, expected_type):
        assert _validate_schema_type(requested_type=requested_type, expected_type=expected_type)
    
    @pytest.mark.parametrize(
            ("requested_type", "expected_types"),
            [
                (BasicAuthCredentials, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.BASIC_AUTH]),
                (BearerTokenAuthCredentials, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.BEARER_TOKEN]),
                (APIKeyAuthCredentials, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.API_KEY_AUTH]),
                (OAuth2ImplicitCredentials, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH2_IMPLICIT]),
                (OAuth2PasswordCredentials, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH2_PASSWORD]),
                (OAuth2ClientCredentials, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH2_CLIENT_CREDS]),
                (KeyValueConnectionCredentials, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.KEY_VALUE]),
            ]
    )
    def test_validate_schema_type_invalid(self, requested_type, expected_types):
        for expected_type in expected_types:
            assert not _validate_schema_type(requested_type=requested_type, expected_type=expected_type)

class TestGetCredentialsModel:

    @pytest.mark.parametrize(
            ("expected_connection", "app_id"),
            [
                (BasicAuthCredentials(**{"username": "Test Username", "password": "Test Password"}), TEST_APP_ID),
                (BearerTokenAuthCredentials(**{"token": "Test Token"}), TEST_APP_ID),
                (APIKeyAuthCredentials(**{"api_key": "Test API Key"}), TEST_APP_ID),
                (OAuth2AuthCodeCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL"}), TEST_APP_ID),
                (OAuth2ImplicitCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL"}), TEST_APP_ID),
                (OAuth2PasswordCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL", "username": "Test Username", "password": "Test Password"}), TEST_APP_ID),
                (OAuth2ClientCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL"}), TEST_APP_ID),
                (KeyValueConnectionCredentials({"Foo": "Test Foo", "bar": "Test bar"}), f"{TEST_APP_ID}_kv"),
            ]
    )
    def test_get_credentials_model(self, expected_connection, app_id, mock_env):
        conn = _get_credentials_model(credentials_type=type(expected_connection), app_id=app_id)
        assert conn == expected_connection

class TestGetApplicationConnectionCredentials:
    @pytest.mark.parametrize(
            ("expected_connection", "app_id", "conn_type"),
            [
                (BasicAuthCredentials(**{"username": "Test Username", "password": "Test Password"}), TEST_APP_ID, ConnectionType.BASIC_AUTH),
                (BearerTokenAuthCredentials(**{"token": "Test Token"}), TEST_APP_ID, ConnectionType.BEARER_TOKEN),
                (APIKeyAuthCredentials(**{"api_key": "Test API Key"}), TEST_APP_ID, ConnectionType.API_KEY_AUTH),
                (OAuth2AuthCodeCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL"}), TEST_APP_ID, ConnectionType.OAUTH2_AUTH_CODE),
                (OAuth2ImplicitCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL"}), TEST_APP_ID, ConnectionType.OAUTH2_IMPLICIT),
                (OAuth2PasswordCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL", "username": "Test Username", "password": "Test Password"}), TEST_APP_ID, ConnectionType.OAUTH2_PASSWORD),
                (OAuth2ClientCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL"}), TEST_APP_ID, ConnectionType.OAUTH2_CLIENT_CREDS),
                (KeyValueConnectionCredentials({"Foo": "Test Foo", "bar": "Test bar"}), f"{TEST_APP_ID}_kv", ConnectionType.KEY_VALUE),
            ]
    )
    def test_get_application_connection_credentials(self, expected_connection, app_id, conn_type, mock_env, monkeypatch):
        monkeypatch.setenv(f"WXO_SECURITY_SCHEMA_{app_id}", conn_type)
        conn = get_application_connection_credentials(type=type(expected_connection), app_id=app_id)
        assert conn == expected_connection
    
    def test_get_application_connection_credentials_no_credentials(self, mock_env, caplog):
        with pytest.raises(BadRequest) as e:
            conn = get_application_connection_credentials(type=BasicAuthCredentials, app_id="not_real")
        
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
                (OAuth2AuthCodeCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL"}), TEST_APP_ID, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH2_AUTH_CODE]),
                (OAuth2ImplicitCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL"}), TEST_APP_ID, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH2_IMPLICIT]),
                (OAuth2PasswordCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL", "username": "Test Username", "password": "Test Password"}), TEST_APP_ID, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH2_PASSWORD]),
                (OAuth2ClientCredentials(**{"client_id": "Test Client ID", "client_secret": "Test Client Secret", "well_known_url": "Test Well Known URL"}), TEST_APP_ID, [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.OAUTH2_CLIENT_CREDS]),
                (KeyValueConnectionCredentials({"Foo": "Test Foo", "bar": "Test bar"}), f"{TEST_APP_ID}_kv", [conn for conn in ALL_CONNECTION_TYPES if conn != ConnectionType.KEY_VALUE]),
            ]
    )
    def test_get_application_connection_credentials_invalid_type(self, expected_connection, app_id, conn_types, mock_env, monkeypatch, caplog):
        for conn_type in conn_types:
            monkeypatch.setenv(f"WXO_SECURITY_SCHEMA_{app_id}", conn_type)
            with pytest.raises(BadRequest) as e:
                conn = get_application_connection_credentials(type=type(expected_connection), app_id=app_id)
            
            message = f"The requested type '{type(expected_connection).__name__}' does not match the type '{conn_type}' for the connection '{app_id}'"
            captured = caplog.text
            assert message in str(e)
            assert message in captured