from enum import Enum
from typing import Optional, Union, TypeVar, List

from pydantic import BaseModel, Field, AliasChoices

from ibm_watsonx_orchestrate_core.types.connections.configuration import ConnectionType, ConnectionSecurityScheme

class ConnectionSendVia(str,Enum):
    HEADER = 'header'
    BODY = 'body'

    def __str__(self):
        return self.value
    
    def __repr__(self):
        return repr(self.value)


class ConnectionCredentialsEntryLocation(str, Enum):
    BODY = 'body'
    HEADER = 'header',
    QUERY = 'query'

    def __str__(self):
        return self.value

class KeyValueEntry(BaseModel):
    key: str = Field(description="The key of the entry.")
    value: str = Field(description="The value of the entry.")

    def __str__(self):
        return f"<KeyValueEntry: {self.key}={self.value}>"

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

class BaseRuntimeCredentials(BaseModel):
    url: Optional[str] = None
    custom_configuration: Optional[dict] = None

class BasicAuthCredentials(BaseRuntimeCredentials):
    username: str
    password: str
    server_cert: Optional[str] = None

class BearerTokenAuthCredentials(BaseRuntimeCredentials):
    token: str

class APIKeyAuthCredentials(BaseRuntimeCredentials):
    api_key: str
    name: Optional[str] = None  # Custom API key header

class OAuth2TokenCredentials(BaseRuntimeCredentials):
    access_token: str

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

class OAuth2JwtBearerCredentials(BaseOAuthCredentials):
    token_url: str
    grant_type: str = "urn:ietf:params:oauth:grant-type:jwt-bearer"
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    iss: Optional[str] = None
    aud: Optional[str] = None
    exp: Optional[str] = None
    include_jti: Optional[bool] = None
    custom_claims: Optional[dict] = None
    alg: str = "RS256"
    private_key: str
    kid: Optional[str] = None
    private_key_password: Optional[str] = None

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)

        jwt_payload = {}
        for key in ["iss", "aud", "exp", "include_jti"]:
            value = data.pop(key, None)
            if value is not None:
                jwt_payload[key] = value
        custom_claims = data.pop("custom_claims", None)
        if custom_claims:
            # custom_claims is intentionally kept nested under jwt_payload as a single key.
            # The connections manager service reads jwt_payload.custom_claims as an object,
            # validates it, and then spreads its key/value pairs into the signed JWT
            # assertion at runtime (see generateJWTAssertion.js:buildJWTPayload).
            # Do NOT flatten these claims directly into jwt_payload here.
            jwt_payload["custom_claims"] = custom_claims
        if jwt_payload:
            data["jwt_payload"] = jwt_payload

        jwt_signature = {}
        for key in ["alg", "kid", "private_key", "private_key_password"]:
            value = data.pop(key, None)
            if value is not None:
                jwt_signature[key] = value
        if jwt_signature:
            data["jwt_signature"] = jwt_signature

        return data

# KeyValue is just an alias of dictionary
class KeyValueConnectionCredentials(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def model_dump(self, *args, **kwargs):
        return self

CONNECTION_TYPE_CREDENTIAL_MAPPING = {
    ConnectionSecurityScheme.BASIC_AUTH: BasicAuthCredentials,
    ConnectionSecurityScheme.BEARER_TOKEN: BearerTokenAuthCredentials,
    ConnectionSecurityScheme.API_KEY_AUTH: APIKeyAuthCredentials,
    ConnectionSecurityScheme.OAUTH2: OAuth2TokenCredentials,
    ConnectionSecurityScheme.KEY_VALUE: KeyValueConnectionCredentials,
}

CREDENTIALS_SET = Union[
    BasicAuthCredentials,
    BearerTokenAuthCredentials,
    APIKeyAuthCredentials,
    OAuth2AuthCodeCredentials,
    # OAuth2ImplicitCredentials,
    OAuth2PasswordCredentials,
    OAuth2ClientCredentials,
    OAuthOnBehalfOfCredentials,
    OAuth2JwtBearerCredentials,
    KeyValueConnectionCredentials
]

CREDENTIALS = TypeVar("CREDENTIALS", bound=CREDENTIALS_SET)

class IdentityProviderCredentials(BaseOAuthCredentials):
    idp_url: str = Field(validation_alias=AliasChoices('idp_url', 'url'), serialization_alias='idp_url')
    client_id: str
    client_secret: str
    scope: str
    grant_type: str

class ExpectedCredentials(BaseModel):
    app_id: str
    type: ConnectionType | List[ConnectionType]