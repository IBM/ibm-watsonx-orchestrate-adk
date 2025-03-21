from ibm_watsonx_orchestrate.agent_builder.connections import (
    get_application_connection_credentials,
    BasicAuthCredentials,
    BearerTokenAuthCredentials,
    APIKeyAuthCredentials,
    OAuth2AuthCodeCredentials,
    OAuth2ImplicitCredentials,
    OAuth2PasswordCredentials,
    OAuth2ClientCredentials,
    KeyValueConnectionCredentials
    )

def basic_auth(app_id:str) -> BasicAuthCredentials:
    return get_application_connection_credentials(BasicAuthCredentials, app_id=app_id)

def bearer_token(app_id:str) -> BearerTokenAuthCredentials:
    return get_application_connection_credentials(BearerTokenAuthCredentials, app_id=app_id)

def api_key_auth(app_id:str) -> APIKeyAuthCredentials:
    return get_application_connection_credentials(APIKeyAuthCredentials, app_id=app_id)

def oauth2_auth_code(app_id:str) -> OAuth2AuthCodeCredentials:
    return get_application_connection_credentials(OAuth2AuthCodeCredentials, app_id=app_id)

def oauth2_implicit(app_id:str) -> OAuth2ImplicitCredentials:
    return get_application_connection_credentials(OAuth2ImplicitCredentials, app_id=app_id)

def oauth2_password(app_id:str) -> OAuth2PasswordCredentials:
    return get_application_connection_credentials(OAuth2PasswordCredentials, app_id=app_id)

def oauth2_client_creds(app_id:str) -> OAuth2ClientCredentials:
    return get_application_connection_credentials(OAuth2ClientCredentials, app_id=app_id)

def key_value(app_id:str) -> KeyValueConnectionCredentials:
    return get_application_connection_credentials(KeyValueConnectionCredentials, app_id=app_id)