from enum import Enum
from typing import Union, Any, List

from pydantic import BaseModel, ConfigDict

from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient, ClientAPIException

import logging
logger = logging.getLogger(__name__)


class ConnectionType(str, Enum):
    BASIC_AUTH = 'basic_auth'
    BEARER_TOKEN = 'bearer_token'
    API_KEY_AUTH = 'api_key_auth'
    OAUTH2_AUTH_CODE = 'oauth2_auth_code'
    OAUTH2_IMPLICIT = 'oauth2_implicit'
    OAUTH2_PASSWORD = 'oauth2_password'
    OAUTH2_CLIENT_CREDS = 'oauth2_client_creds'
    KEY_VALUE = 'key_value_creds'

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

# KeyValue is just an alias of dictionary
class KeyValueConnectionCredentials(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

class CreateKeyValueConnection(CreateConnection):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    connection_type: ConnectionType = ConnectionType.KEY_VALUE
    credentials: KeyValueConnectionCredentials


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

class ListConnectionResponse(BaseModel):
    appid: str = None
    shared: bool = None
    tenant_id: str = None
    is_connected: bool = None
    connection_type: str = None
    connection_id: str = None

class ApplicationConnectionsClient(BaseAPIClient):
    """
    Client to handle CRUD operations for Application Connections endpoint
    """

    def create(self, connection: CREATE_CONNECTION) -> CreateConnectionResponse:
        return CreateConnectionResponse.model_validate(self._post("/connections/applications", data=connection.model_dump()))

    def get(self) -> List[ListConnectionResponse]:
        try:
            response = self._get("/connections/applications")
        except ClientAPIException as e:
            if e.response.status_code == 404:
                response = []
            else:
                raise e
        connections = []
        for conn in response:
            connections.append(ListConnectionResponse.model_validate(conn))
        return connections

    def get_draft_by_app_id(self, app_id: str) -> List[ListConnectionResponse]:
        return self.get_draft_by_app_ids([app_id])

    def get_draft_by_app_ids(self, app_ids: List[str]) -> List[ListConnectionResponse]:
        response = self._get(f"/connections/applications/list?app_ids={','.join(app_ids)}")
        connections = []
        for conn in response:
            connections.append(ListConnectionResponse.model_validate(conn))
        return connections

    def update(self, agent_id: str, data: dict) -> dict:
        raise RuntimeError('unimplemented')

    def delete(self, connection_id: str) -> DeleteConnectionResponse:
        return DeleteConnectionResponse.model_validate(self._delete(f"/connections/applications/{connection_id}"))
    
    def get_draft_by_id(self, conn_id) -> str:
        """Retrieve the app ID for a given connection ID."""
        if conn_id is None:
            return ""
        try:
            connections = self.get()
        except ClientAPIException as e:
            if e.response.status_code == 404:
                logger.warning(f"Connections not found. Returning connection ID: {conn_id}")
                return conn_id 
            raise 
        appid = next((conn.appid for conn in connections if conn.connection_id == conn_id), None)

        if appid is None:
            logger.warning(f"Connection with ID {conn_id} not found. Returning connection ID.")
            return conn_id  
        return appid
