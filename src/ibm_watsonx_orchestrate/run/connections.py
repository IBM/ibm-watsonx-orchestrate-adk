from ibm_watsonx_orchestrate.agent_builder.connections import (
    get_application_connection_credentials,
    get_connection_type,
    BasicAuthCredentials,
    BearerTokenAuthCredentials,
    APIKeyAuthCredentials,
    OAuth2TokenCredentials,
    KeyValueConnectionCredentials,
    ConnectionType
    )

def basic_auth(app_id:str) -> BasicAuthCredentials:
    return get_application_connection_credentials(ConnectionType.BASIC_AUTH, app_id=app_id)

def bearer_token(app_id:str) -> BearerTokenAuthCredentials:
    return get_application_connection_credentials(ConnectionType.BEARER_TOKEN, app_id=app_id)

def api_key_auth(app_id:str) -> APIKeyAuthCredentials:
    return get_application_connection_credentials(ConnectionType.API_KEY_AUTH, app_id=app_id)

def oauth2_auth_code(app_id:str) -> OAuth2TokenCredentials:
    return get_application_connection_credentials(ConnectionType.OAUTH2_AUTH_CODE, app_id=app_id)

# def oauth2_implicit(app_id:str) -> BearerTokenAuthCredentials:
#     return get_application_connection_credentials(ConnectionType.OAUTH2_IMPLICIT, app_id=app_id)

def oauth2_password(app_id:str) -> OAuth2TokenCredentials:
    return get_application_connection_credentials(ConnectionType.OAUTH2_PASSWORD, app_id=app_id)

def oauth2_client_creds(app_id:str) -> OAuth2TokenCredentials:
    return get_application_connection_credentials(ConnectionType.OAUTH2_CLIENT_CREDS, app_id=app_id)

def oauth2_on_behalf_of(app_id:str) -> OAuth2TokenCredentials:
    return get_application_connection_credentials(ConnectionType.OAUTH_ON_BEHALF_OF_FLOW, app_id=app_id)

def oauth2_token_exchange(app_id:str) -> OAuth2TokenCredentials:
    return get_application_connection_credentials(ConnectionType.OAUTH2_TOKEN_EXCHANGE, app_id=app_id)

def key_value(app_id:str) -> KeyValueConnectionCredentials:
    return get_application_connection_credentials(ConnectionType.KEY_VALUE, app_id=app_id)

def connection_type(app_id:str) -> ConnectionType:
    return get_connection_type(app_id=app_id)