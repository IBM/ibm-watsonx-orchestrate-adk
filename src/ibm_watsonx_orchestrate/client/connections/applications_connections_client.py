from enum import Enum
from typing import Union, Any

from pydantic import BaseModel

from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient


class ConnectionType(str, Enum):
    BASIC_AUTH = 'basic_auth'
    BEARER_TOKEN = 'bearer_token'
    API_KEY_AUTH = 'api_key_auth'
    OAUTH2_AUTH_CODE = 'oauth2_auth_code'
    OAUTH2_IMPLICIT = 'oauth2_implicit'
    OAUTH2_PASSWORD = 'oauth2_password'
    OAUTH2_CLIENT_CREDS = 'oauth2_client_creds'

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value


class BasicAuthCredentials(BaseModel):
    username: str
    password: str


class BearerTokenAuthCredentials(BaseModel):
    token: str


class APIKeyAuthCredentials(BaseModel):
    api_key: str


class OAuth2AuthCodeCredentials(BaseModel):
    client_id: str
    client_secret: str
    scope: str | None = None
    well_known_url: str


class OAuth2ImplicitCredentials(BaseModel):
    client_id: str
    client_secret: str
    scope: str | None = None
    well_known_url: str


class OAuth2PasswordCredentials(BaseModel):
    client_id: str
    client_secret: str
    scope: str | None = None
    username: str
    password: str
    well_known_url: str


class OAuth2ClientCredentials(BaseModel):
    client_id: str
    client_secret: str
    scope: str | None = None
    well_known_url: str


class CreateConnection(BaseModel):
    appid: str
    connection_type: ConnectionType
    credentials: Any
    shared: bool


class CreateBasicAuthConnection(CreateConnection):
    connection_type: ConnectionType = ConnectionType.BASIC_AUTH
    credentials: BasicAuthCredentials


class CreateBearerTokenAuthConnection(CreateConnection):
    connection_type: ConnectionType = ConnectionType.BEARER_TOKEN
    credentials: BearerTokenAuthCredentials


class CreateAPIKeyAuthConnection(CreateConnection):
    connection_type: ConnectionType = ConnectionType.API_KEY_AUTH
    credentials: APIKeyAuthCredentials


class CreateOAuth2AuthCodeConnection(CreateConnection):
    connection_type: ConnectionType = ConnectionType.OAUTH2_AUTH_CODE
    credentials: OAuth2AuthCodeCredentials


class CreateOAuth2ImplicitConnection(CreateConnection):
    connection_type: ConnectionType = ConnectionType.OAUTH2_IMPLICIT
    credentials: OAuth2ImplicitCredentials


class CreateOAuth2PasswordConnection(CreateConnection):
    connection_type: ConnectionType = ConnectionType.OAUTH2_PASSWORD
    credentials: OAuth2PasswordCredentials


class CreateOAuth2ClientCredentialsConnection(CreateConnection):
    connection_type: ConnectionType = ConnectionType.OAUTH2_CLIENT_CREDS
    credentials: OAuth2ClientCredentials


CREATE_CONNECTION = Union[
    CreateBasicAuthConnection,
    CreateBearerTokenAuthConnection,
    CreateAPIKeyAuthConnection,
    CreateOAuth2AuthCodeConnection,
    CreateOAuth2ImplicitConnection,
    CreateOAuth2PasswordConnection,
    CreateOAuth2ClientCredentialsConnection,
]


class CreateConnectionResponse(BaseModel):
    status: str = None
    message: str = None
    connection_id: str = None
    detail: str = None
    authorization_url: str = None


class DeleteConnectionResponse(BaseModel):
    status: str = None
    message: str = None
    connection_id: str = None
    detail: str = None


class ApplicationConnectionsClient(BaseAPIClient):
    """
    Client to handle CRUD operations for Orchestrator Agent endpoint
    """

    def create(self, connection: CREATE_CONNECTION) -> CreateConnectionResponse:
        return CreateConnectionResponse.model_validate(self._post("/api/v1/connections/applications", data=connection.model_dump()))

    def get(self) -> dict:
        raise RuntimeError('unimplemented')

    def update(self, agent_id: str, data: dict) -> dict:
        raise RuntimeError('unimplemented')

    def delete(self, app_id: str) -> DeleteConnectionResponse:
        return DeleteConnectionResponse.model_validate(self._delete(f"/api/v1/connections/applications/{app_id}"))