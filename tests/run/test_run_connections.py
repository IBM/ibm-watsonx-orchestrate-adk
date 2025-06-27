from ibm_watsonx_orchestrate.run.connections import(
    basic_auth,
    bearer_token,
    api_key_auth,
    # oauth2_auth_code,
    # oauth2_implicit,
    # oauth2_password,
    # oauth2_client_creds,
    oauth2_on_behalf_of,
    key_value,
    connection_type
)
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType
from unittest.mock import patch


class TestBasicAuth:
    def test_basic_auth(self):
        with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
            basic_auth("test")
            mock.assert_called_with(ConnectionType.BASIC_AUTH, app_id="test")

class TestBearerToken:
    def test_bearer_token(self):
        with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
            bearer_token("test")
            mock.assert_called_with(ConnectionType.BEARER_TOKEN, app_id="test")

class TestApiKeyAuth:
    def test_api_key_auth(self):
        with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
            api_key_auth("test")
            mock.assert_called_with(ConnectionType.API_KEY_AUTH, app_id="test")

# class TestOauth2AuthCode:
#     def test_oauth2_auth_code(self):
#         with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
#             oauth2_auth_code("test")
#             mock.assert_called_with(ConnectionType.OAUTH2_AUTH_CODE, app_id="test")

# class TestOauth2Implicit:
#     def test_oauth2_implicit(self):
#         with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
#             oauth2_implicit("test")
#             mock.assert_called_with(ConnectionType.OAUTH2_IMPLICIT, app_id="test")

# class TestOauth2Password:
#     def test_oauth2_password(self):
#         with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
#             oauth2_password("test")
#             mock.assert_called_with(ConnectionType.OAUTH2_PASSWORD, app_id="test")

# class TestOauth2ClientCreds:
#     def test_oauth2_client_creds(self):
#         with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
#             oauth2_client_creds("test")
#             mock.assert_called_with(ConnectionType.OAUTH2_CLIENT_CREDS, app_id="test")

class TestOauth2OnBehalfOf:
    def test_oauth2_on_behalf_of(self):
        with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
            oauth2_on_behalf_of("test")
            mock.assert_called_with(ConnectionType.OAUTH_ON_BEHALF_OF_FLOW, app_id="test")

class TestKeyValue:
    def test_key_value(self):
        with patch("ibm_watsonx_orchestrate.run.connections.get_application_connection_credentials") as mock:
            key_value("test")
            mock.assert_called_with(ConnectionType.KEY_VALUE, app_id="test")

class TestConnectionType:
    def test_connection_type(self):
        with patch("ibm_watsonx_orchestrate.run.connections.get_connection_type") as mock:
            connection_type("test")
            mock.assert_called_with(app_id="test")