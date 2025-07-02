from pydantic import BaseModel, Field, AliasChoices, model_validator
from typing import Optional, Union, TypeVar, List
from enum import Enum

class ConnectionKind(str, Enum):
    basic = 'basic'
    bearer = 'bearer'
    api_key = 'api_key'
    oauth_auth_code_flow = 'oauth_auth_code_flow'
    # oauth_auth_implicit_flow = 'oauth_auth_implicit_flow'
    # oauth_auth_password_flow = 'oauth_auth_password_flow'
    oauth_auth_client_credentials_flow = 'oauth_auth_client_credentials_flow'
    oauth_auth_on_behalf_of_flow = 'oauth_auth_on_behalf_of_flow'
    key_value = 'key_value'
    kv = 'kv'

    def __str__(self):
        return self.value

class ConnectionEnvironment(str, Enum):
    DRAFT = 'draft'
    LIVE = 'live'

    def __str__(self):
        return self.value

class ConnectionPreference(str, Enum):
    MEMBER = 'member'
    TEAM = 'team'

    def __str__(self):
        return self.value

class ConnectionAuthType(str, Enum):
    OAUTH2_AUTH_CODE = 'oauth2_auth_code'
    # OAUTH2_IMPLICIT = 'oauth2_implicit'
    # OAUTH2_PASSWORD = 'oauth2_password'
    OAUTH2_CLIENT_CREDS = 'oauth2_client_creds'
    OAUTH_ON_BEHALF_OF_FLOW = 'oauth_on_behalf_of_flow'

    def __str__(self):
        return self.value 

    def __repr__(self):
        return repr(self.value)

class ConnectionSecurityScheme(str, Enum):
    BASIC_AUTH = 'basic_auth'
    BEARER_TOKEN = 'bearer_token'
    API_KEY_AUTH = 'api_key_auth'
    OAUTH2 = 'oauth2'
    KEY_VALUE = 'key_value_creds'
    
    def __str__(self):
        return self.value 

    def __repr__(self):
        return repr(self.value)

# Values for python tool expected credentials
# Line up with what the Security_Schema env var is
class ConnectionType(str, Enum):
    BASIC_AUTH = ConnectionSecurityScheme.BASIC_AUTH.value
    BEARER_TOKEN = ConnectionSecurityScheme.BEARER_TOKEN.value
    API_KEY_AUTH = ConnectionSecurityScheme.API_KEY_AUTH.value
    OAUTH2_AUTH_CODE = ConnectionAuthType.OAUTH2_AUTH_CODE.value
    # OAUTH2_IMPLICIT = ConnectionAuthType.OAUTH2_IMPLICIT.value
    # OAUTH2_PASSWORD = ConnectionAuthType.OAUTH2_PASSWORD.value
    OAUTH2_CLIENT_CREDS = ConnectionAuthType.OAUTH2_CLIENT_CREDS.value
    OAUTH_ON_BEHALF_OF_FLOW = ConnectionAuthType.OAUTH_ON_BEHALF_OF_FLOW.value
    KEY_VALUE = ConnectionSecurityScheme.KEY_VALUE.value

    def __str__(self):
        return self.value 

    def __repr__(self):
        return repr(self.value)

OAUTH_CONNECTION_TYPES = {
    ConnectionType.OAUTH2_AUTH_CODE,
    ConnectionType.OAUTH2_CLIENT_CREDS,
    # ConnectionType.OAUTH2_IMPLICIT,
    # ConnectionType.OAUTH2_PASSWORD,
    ConnectionType.OAUTH_ON_BEHALF_OF_FLOW,
}

class IdpConfigDataBody(BaseModel):
    requested_token_use: str
    requested_token_type: str

class IdpConfigData(BaseModel):
    header: Optional[dict] = None
    body: IdpConfigDataBody

    @model_validator(mode="after")
    def set_default_values(self):
        self.header = self.header or {
            "content-type": "application/x-www-form-urlencoded"
        }
        return self

class AppConfigData(BaseModel):
    header: Optional[dict] = None
    
    @model_validator(mode="after")
    def set_default_values(self):
        self.header = self.header or {
            "content-type": "application/x-www-form-urlencoded"
        }
        return self


class ConnectionConfiguration(BaseModel):
    app_id: str
    environment: ConnectionEnvironment
    preference: ConnectionPreference = Field(validation_alias=AliasChoices('preference', 'type'), serialization_alias='preference')
    security_scheme: ConnectionSecurityScheme
    auth_type: Optional[ConnectionAuthType] = None
    sso: bool = False
    server_url: str | None = None
    idp_config_data: Optional[IdpConfigData] = Field(None, validation_alias=AliasChoices('idp_config_data', 'idp_config'), serialization_alias='idp_config_data')
    app_config_data: Optional[AppConfigData] = Field(None, validation_alias=AliasChoices('app_config_data', 'app_config'), serialization_alias='app_config_data')
    config_id: str = None
    tenant_id: str = None

    def __init__(self, *args, **kwargs):
        kind = kwargs.get("kind")

        if kind:
            if not kwargs.get("auth_type"):
                kwargs["auth_type"] = CONNECTION_KIND_OAUTH_TYPE_MAPPING.get(kind)
        
            if not kwargs.get("security_scheme"):
                kwargs["security_scheme"] = CONNECTION_KIND_SCHEME_MAPPING.get(kind)
        
        super().__init__(*args, **kwargs)

    @model_validator(mode="after")
    def validate_config(self):
        conn_type = None
        if self.security_scheme == ConnectionSecurityScheme.OAUTH2:
            conn_type = self.auth_type
        else:
            conn_type = self.security_scheme
        if self.sso and conn_type != ConnectionAuthType.OAUTH_ON_BEHALF_OF_FLOW:
            raise ValueError(f"SSO not supported for auth scheme '{conn_type}'. SSO can only be used with OAuth auth types")
        if not self.sso and conn_type == ConnectionAuthType.OAUTH_ON_BEHALF_OF_FLOW:
            raise ValueError(f"SSO required for '{conn_type}'. Please enable SSO.")
        if self.sso:
            if not self.idp_config_data:
                raise ValueError("For SSO auth 'idp_config_data' is a required field")
            if not self.app_config_data:
                self.app_config_data = AppConfigData()
        if self.security_scheme == ConnectionSecurityScheme.KEY_VALUE and self.preference == ConnectionPreference.MEMBER:
            raise ValueError("Connection of type 'key_value' cannot be configured at the 'member' level. Key value connections must be of type 'team'")
        return self

class BasicAuthCredentials(BaseModel):
    username: str
    password: str
    url: Optional[str] = None

class BearerTokenAuthCredentials(BaseModel):
    token: str
    url: Optional[str] = None

class APIKeyAuthCredentials(BaseModel):
    api_key: str
    url: Optional[str] = None

class OAuth2TokenCredentials(BaseModel):
    access_token: str
    url: Optional[str] = None

class OAuth2AuthCodeCredentials(BaseModel):
    client_id: str
    client_secret: str
    token_url: str
    authorization_url: str
    scopes : Optional[List[str]] = None

# class OAuth2ImplicitCredentials(BaseModel):
#     client_id: str
#     authorization_url: str

# class OAuth2PasswordCredentials(BaseModel):
#     client_id: str
#     client_secret: str
#     token_url: str
#     authorization_url: str

class OAuth2ClientCredentials(BaseModel):
    client_id: str
    client_secret: str
    token_url: str
    scopes : Optional[List[str]] = None

class OAuthOnBehalfOfCredentials(BaseModel):
    client_id: str
    access_token_url: str
    grant_type: str

# KeyValue is just an alias of dictionary
class KeyValueConnectionCredentials(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def model_dump(self, *args, **kwargs):
        return self

CREDENTIALS_SET = Union[
    BasicAuthCredentials,
    BearerTokenAuthCredentials,
    APIKeyAuthCredentials,
    OAuth2AuthCodeCredentials,
    # OAuth2ImplicitCredentials,
    # OAuth2PasswordCredentials,
    OAuth2ClientCredentials,
    OAuthOnBehalfOfCredentials,
    KeyValueConnectionCredentials
]

CREDENTIALS = TypeVar("CREDENTIALS", bound=CREDENTIALS_SET)

CONNECTION_KIND_SCHEME_MAPPING = {
    ConnectionKind.basic: ConnectionSecurityScheme.BASIC_AUTH,
    ConnectionKind.bearer: ConnectionSecurityScheme.BEARER_TOKEN,
    ConnectionKind.api_key: ConnectionSecurityScheme.API_KEY_AUTH,
    ConnectionKind.oauth_auth_code_flow: ConnectionSecurityScheme.OAUTH2,
    # ConnectionKind.oauth_auth_implicit_flow: ConnectionSecurityScheme.OAUTH2,
    # ConnectionKind.oauth_auth_password_flow: ConnectionSecurityScheme.OAUTH2,
    ConnectionKind.oauth_auth_client_credentials_flow: ConnectionSecurityScheme.OAUTH2,
    ConnectionKind.oauth_auth_on_behalf_of_flow: ConnectionSecurityScheme.OAUTH2,
    ConnectionKind.key_value: ConnectionSecurityScheme.KEY_VALUE,
    ConnectionKind.kv: ConnectionSecurityScheme.KEY_VALUE,
}

CONNECTION_KIND_OAUTH_TYPE_MAPPING = {
    ConnectionKind.oauth_auth_code_flow: ConnectionAuthType.OAUTH2_AUTH_CODE,
    # ConnectionKind.oauth_auth_implicit_flow: ConnectionAuthType.OAUTH2_IMPLICIT,
    # ConnectionKind.oauth_auth_password_flow: ConnectionAuthType.OAUTH2_PASSWORD,
    ConnectionKind.oauth_auth_client_credentials_flow: ConnectionAuthType.OAUTH2_CLIENT_CREDS,
    ConnectionKind.oauth_auth_on_behalf_of_flow: ConnectionAuthType.OAUTH_ON_BEHALF_OF_FLOW,
}

CONNECTION_TYPE_CREDENTIAL_MAPPING = {
    ConnectionSecurityScheme.BASIC_AUTH: BasicAuthCredentials,
    ConnectionSecurityScheme.BEARER_TOKEN: BearerTokenAuthCredentials,
    ConnectionSecurityScheme.API_KEY_AUTH: APIKeyAuthCredentials,
    ConnectionSecurityScheme.OAUTH2: OAuth2TokenCredentials,
    ConnectionSecurityScheme.KEY_VALUE: KeyValueConnectionCredentials,
}

class IdentityProviderCredentials(BaseModel):
    idp_url: str = Field(validation_alias=AliasChoices('idp_url', 'url'), serialization_alias='idp_url')
    client_id: str
    client_secret: str
    scope: str
    grant_type: str

class ExpectedCredentials(BaseModel):
    app_id: str
    type: ConnectionType | List[ConnectionType]