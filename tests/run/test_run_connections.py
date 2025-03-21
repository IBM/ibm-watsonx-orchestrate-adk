from ibm_watsonx_orchestrate.run.connections import(
    basic_auth,
    bearer_token,
    api_key_auth,
    oauth2_auth_code,
    oauth2_implicit,
    oauth2_password,
    oauth2_client_creds,
    key_value
)
from ibm_watsonx_orchestrate.agent_builder.connections import (
    BasicAuthCredentials,
    BearerTokenAuthCredentials,
    APIKeyAuthCredentials,
    OAuth2AuthCodeCredentials,
    OAuth2ImplicitCredentials,
    OAuth2PasswordCredentials,
    OAuth2ClientCredentials,
    KeyValueConnectionCredentials
    )
from unittest.mock import patch


class TestBasicAuth:
    def test_basic_auth(mock):
        with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
            basic_auth("test")
            mock.assert_called_with(BasicAuthCredentials, app_id="test")

class TestBearerToken:
    def test_bearer_token(mock):
        with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
            bearer_token("test")
            mock.assert_called_with(BearerTokenAuthCredentials, app_id="test")

class TestApiKeyAuth:
    def test_api_key_auth(mock):
        with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
            api_key_auth("test")
            mock.assert_called_with(APIKeyAuthCredentials, app_id="test")

class TestOauth2AuthCode:
    def test_oauth2_auth_code(mock):
        with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
            oauth2_auth_code("test")
            mock.assert_called_with(OAuth2AuthCodeCredentials, app_id="test")

class TestOauth2Implicit:
    def test_oauth2_implicit(mock):
        with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
            oauth2_implicit("test")
            mock.assert_called_with(OAuth2ImplicitCredentials, app_id="test")

class TestOauth2Password:
    def test_oauth2_password(mock):
        with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
            oauth2_password("test")
            mock.assert_called_with(OAuth2PasswordCredentials, app_id="test")

class TestOauth2ClientCreds:
    def test_oauth2_client_creds(mock):
        with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
            oauth2_client_creds("test")
            mock.assert_called_with(OAuth2ClientCredentials, app_id="test")

class TestKeyValue:
    def test_key_value(mock):
        with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
            key_value("test")
            mock.assert_called_with(KeyValueConnectionCredentials, app_id="test")