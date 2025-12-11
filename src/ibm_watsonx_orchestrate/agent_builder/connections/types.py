import logging
from pydantic import BaseModel, Field, AliasChoices, model_validator, ValidationInfo
from typing import Optional, Union, TypeVar, List
from enum import Enum


logger = logging.getLogger(__name__)

class ConnectionKind(str, Enum):
    basic = 'basic'
    bearer = 'bearer'
    api_key = 'api_key'
    oauth_auth_code_flow = 'oauth_auth_code_flow'
    # oauth_auth_implicit_flow = 'oauth_auth_implicit_flow'
    oauth_auth_password_flow = 'oauth_auth_password_flow'
    oauth_auth_client_credentials_flow = 'oauth_auth_client_credentials_flow'
    oauth_auth_on_behalf_of_flow = 'oauth_auth_on_behalf_of_flow'
    oauth_auth_token_exchange_flow = 'oauth_auth_token_exchange_flow'
    key_value = 'key_value'
    kv = 'kv'

    def __str__(self):
        return self.value

class ConnectionEnvironment(str, Enum):
    DRAFT = 'draft'
    LIVE = 'live'

    def __str__(self):
        return self.value
    
    def __repr__(self):
        return repr(self.value)

class ConnectionPreference(str, Enum):
    MEMBER = 'member'
    TEAM = 'team'

    def __str__(self):
        return self.value

class ConnectionAuthType(str, Enum):
    OAUTH2_AUTH_CODE = 'oauth2_auth_code'
    # OAUTH2_IMPLICIT = 'oauth2_implicit'
    OAUTH2_PASSWORD = 'oauth2_password'
    OAUTH2_CLIENT_CREDS = 'oauth2_client_creds'
    OAUTH_ON_BEHALF_OF_FLOW = 'oauth_on_behalf_of_flow'
    OAUTH2_TOKEN_EXCHANGE = 'oauth2_token_exchange'

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
    OAUTH2_PASSWORD = ConnectionAuthType.OAUTH2_PASSWORD.value
    OAUTH2_CLIENT_CREDS = ConnectionAuthType.OAUTH2_CLIENT_CREDS.value
    OAUTH_ON_BEHALF_OF_FLOW = ConnectionAuthType.OAUTH_ON_BEHALF_OF_FLOW.value
    OAUTH2_TOKEN_EXCHANGE = ConnectionAuthType.OAUTH2_TOKEN_EXCHANGE.value
    KEY_VALUE = ConnectionSecurityScheme.KEY_VALUE.value

    def __str__(self):
        return self.value 

    def __repr__(self):
        return repr(self.value)
    
class ConnectionSendVia(str,Enum):
    HEADER = 'header'
    BODY = 'body'

    def __str__(self):
        return self.value
    
    def __repr__(self):
        return repr(self.value)

OAUTH_CONNECTION_TYPES = {
    ConnectionType.OAUTH2_AUTH_CODE,
    ConnectionType.OAUTH2_CLIENT_CREDS,
    # ConnectionType.OAUTH2_IMPLICIT,
    ConnectionType.OAUTH2_PASSWORD,
    ConnectionType.OAUTH_ON_BEHALF_OF_FLOW,
    ConnectionType.OAUTH2_TOKEN_EXCHANGE
}

SSO_CONNECTION_TYPES = {
    ConnectionType.OAUTH_ON_BEHALF_OF_FLOW,
    ConnectionType.OAUTH2_TOKEN_EXCHANGE
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
    server_url: Optional[str] = None
    idp_config_data: Optional[IdpConfigData] = Field(None, validation_alias=AliasChoices('idp_config_data', 'idp_config'), serialization_alias='idp_config_data')
    app_config_data: Optional[AppConfigData] = Field(None, validation_alias=AliasChoices('app_config_data', 'app_config'), serialization_alias='app_config_data')
    config_id: Optional[str] = None
    tenant_id: Optional[str] = None
    
    def __get_import_aliases_mapping(self) -> dict:
        return {
            "security_scheme": "kind",
            "preference": "type",
            "auth_type": None,
            "idp_config_data": "idp_config",
            "app_config_data": "app_config"
        }
    
    def __get_kind(self, security_scheme: ConnectionSecurityScheme, auth_type: Optional[ConnectionAuthType]) -> str | None:
        def reverse_lookup(d: dict[str, str], value: str) -> str | None:
            for k, v in d.items():
                if v == value:
                    return k
            return None

        if auth_type or security_scheme == ConnectionSecurityScheme.OAUTH2:
            return reverse_lookup(CONNECTION_KIND_OAUTH_TYPE_MAPPING, auth_type)
        else:
            return reverse_lookup(CONNECTION_KIND_SCHEME_MAPPING, security_scheme)


    def model_dump(self, *args, use_import_aliases: bool = False, **kwargs):
            data = super().model_dump(*args, **kwargs)
            if use_import_aliases:
                kind = self.__get_kind(data.get("security_scheme"), data.get("auth_type"))
                if kwargs.get("mode") and kwargs.get("mode") == "json":
                    kind = str(kind) 

                key_aliases = self.__get_import_aliases_mapping()
                for k, v in key_aliases.items():
                    if v:
                        data[v] = data.pop(k)
                    else:
                        data.pop(k)
                data["kind"] = kind
            return data


    @model_validator(mode="before")
    def validate_auth_scheme(self):
        kind = self.get("kind")

        if kind:
            if not self.get("auth_type"):
                self["auth_type"] = CONNECTION_KIND_OAUTH_TYPE_MAPPING.get(kind)
        
            if not self.get("security_scheme"):
                self["security_scheme"] = CONNECTION_KIND_SCHEME_MAPPING.get(kind)

        if self.get('auth_type'):
            try:
                self['auth_type'] = ConnectionAuthType(self.get('auth_type'))
            except:
                logger.warning(f"Unsupported auth type '{self.get('auth_type')}' for connection '{self.get('app_id')}', this will be removed from the configuration data.")
                self['auth_type'] = None
        return self

    @model_validator(mode="after")
    def validate_config(self, info: ValidationInfo):
        context = getattr(info, "context", None)

        if context == "export":
            return self

        conn_type = None
        if self.security_scheme == ConnectionSecurityScheme.OAUTH2:
            conn_type = self.auth_type
        else:
            conn_type = self.security_scheme
        if self.sso and conn_type not in SSO_CONNECTION_TYPES:
            raise ValueError(f"SSO not supported for auth scheme '{conn_type}'. SSO can only be used with support auth types {SSO_CONNECTION_TYPES}")
        if not self.sso and conn_type in SSO_CONNECTION_TYPES:
            raise ValueError(f"SSO required for '{conn_type}'. Please enable SSO.")
        if self.sso:
            if not self.app_config_data:
                self.app_config_data = AppConfigData()
            if self.preference != ConnectionPreference.MEMBER:
                raise ValueError("For SSO auth 'type' must be set to member")
        if conn_type == ConnectionType.OAUTH_ON_BEHALF_OF_FLOW and not self.idp_config_data:
                raise ValueError("For SSO auth 'idp_config_data' is a required field")
        if self.security_scheme == ConnectionSecurityScheme.KEY_VALUE and self.preference == ConnectionPreference.MEMBER:
            raise ValueError("Connection of type 'key_value' cannot be configured at the 'member' level. Key value connections must be of type 'team'")
        return self

class ConnectionCredentialsEntryLocation(str, Enum):
    BODY = 'body'
    HEADER = 'header',
    QUERY = 'query'

    def __str__(self):
        return self.value

class ConnectionCredentialsEntry(BaseModel):
    key: str = Field(description="The key of the custom credential entry.")
    value: str = Field(description="The value of the custom credential entry.")
    location: ConnectionCredentialsEntryLocation = Field(description="How the custom credential should be sent to the server")

    def __str__(self):
        return f"<ConnectionCredentialsEntry: {self.location}:{self.key}={self.value}>"

class BaseOAuthCredentials(BaseModel):
    custom_token_query: Optional[dict] = None
    custom_token_header: Optional[dict] = None
    custom_token_body: Optional[dict] = None
    custom_auth_query: Optional[dict] = None

class ConnectionCredentialsCustomFields(BaseOAuthCredentials):
    def add_field(self, entry: ConnectionCredentialsEntry, is_token:bool=True) -> None:
        match entry.location:
            case ConnectionCredentialsEntryLocation.HEADER:
                if not is_token:
                    return
                attribute = "custom_token_header"
            case ConnectionCredentialsEntryLocation.BODY:
                if not is_token:
                    return
                attribute = "custom_token_body"
            case ConnectionCredentialsEntryLocation.QUERY:
                if is_token:
                     attribute = "custom_token_query"
                else:
                    attribute = "custom_auth_query"
            case _:
                return
        
        fields = getattr(self, attribute)
        if not fields:
            setattr(self, attribute, {})
            fields = getattr(self, attribute)
        fields[entry.key] = entry.value

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

class OAuth2AuthCodeCredentials(BaseOAuthCredentials):
    client_id: str
    client_secret: str
    token_url: str
    authorization_url: str
    scope : Optional[str] = None

# class OAuth2ImplicitCredentials(BaseModel):
#     client_id: str
#     authorization_url: str

class OAuth2PasswordCredentials(BaseOAuthCredentials):
    username: str
    password: str
    client_id: str
    client_secret: str
    token_url: str
    scope: Optional[str] = None
    grant_type: str = "password"
    

class OAuth2ClientCredentials(BaseOAuthCredentials):
    client_id: str
    client_secret: str
    token_url: str
    scope : Optional[str] = None
    send_via: ConnectionSendVia = ConnectionSendVia.HEADER
    grant_type: str = "client_credentials"

class OAuthOnBehalfOfCredentials(BaseOAuthCredentials):
    client_id: str
    access_token_url: str
    grant_type: str

class OAuth2TokenExchangeCredentials(BaseOAuthCredentials):
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
    OAuth2PasswordCredentials,
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
    ConnectionKind.oauth_auth_password_flow: ConnectionSecurityScheme.OAUTH2,
    ConnectionKind.oauth_auth_client_credentials_flow: ConnectionSecurityScheme.OAUTH2,
    ConnectionKind.oauth_auth_on_behalf_of_flow: ConnectionSecurityScheme.OAUTH2,
    ConnectionKind.oauth_auth_token_exchange_flow: ConnectionSecurityScheme.OAUTH2,
    ConnectionKind.key_value: ConnectionSecurityScheme.KEY_VALUE,
    ConnectionKind.kv: ConnectionSecurityScheme.KEY_VALUE,
}

CONNECTION_KIND_OAUTH_TYPE_MAPPING = {
    ConnectionKind.oauth_auth_code_flow: ConnectionAuthType.OAUTH2_AUTH_CODE,
    # ConnectionKind.oauth_auth_implicit_flow: ConnectionAuthType.OAUTH2_IMPLICIT,
    ConnectionKind.oauth_auth_password_flow: ConnectionAuthType.OAUTH2_PASSWORD,
    ConnectionKind.oauth_auth_client_credentials_flow: ConnectionAuthType.OAUTH2_CLIENT_CREDS,
    ConnectionKind.oauth_auth_on_behalf_of_flow: ConnectionAuthType.OAUTH_ON_BEHALF_OF_FLOW,
    ConnectionKind.oauth_auth_token_exchange_flow: ConnectionAuthType.OAUTH2_TOKEN_EXCHANGE
}

CONNECTION_TYPE_CREDENTIAL_MAPPING = {
    ConnectionSecurityScheme.BASIC_AUTH: BasicAuthCredentials,
    ConnectionSecurityScheme.BEARER_TOKEN: BearerTokenAuthCredentials,
    ConnectionSecurityScheme.API_KEY_AUTH: APIKeyAuthCredentials,
    ConnectionSecurityScheme.OAUTH2: OAuth2TokenCredentials,
    ConnectionSecurityScheme.KEY_VALUE: KeyValueConnectionCredentials,
}

class IdentityProviderCredentials(BaseOAuthCredentials):
    idp_url: str = Field(validation_alias=AliasChoices('idp_url', 'url'), serialization_alias='idp_url')
    client_id: str
    client_secret: str
    scope: str
    grant_type: str

class ExpectedCredentials(BaseModel):
    app_id: str
    type: ConnectionType | List[ConnectionType]

class ConnectionsListEntry(BaseModel):
    app_id: str = Field(description="A unique identifier for the connection.")
    auth_type: Optional[str] = Field(default=None, description="The kind of auth used by the connections")
    type: Optional[ConnectionPreference] = Field(default=None, description="The type of the connections. If set to 'team' the credentails will be shared by all users. If set to 'member' each user will have to provide their own credentials")
    credentials_set: bool = Field(default=False, description="Are the credentials set for the current user. If using OAuth connection types this value will be False unless there isn a stored token from runtime usage")

    def get_row_details(self):
        auth_type = self.auth_type if self.auth_type else "n/a"
        type = self.type if self.type else "n/a"
        credentials_set = "✅" if self.credentials_set else "❌"
        return [self.app_id, auth_type, type, credentials_set]

class ConnectionsListResponse(BaseModel):
    non_configured: Optional[List[dict] | str] = None
    draft: Optional[List[dict] | str] = None
    live: Optional[List[dict] | str] = None