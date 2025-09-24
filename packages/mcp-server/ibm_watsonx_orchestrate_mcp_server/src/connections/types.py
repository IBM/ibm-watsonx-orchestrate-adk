from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionEnvironment, ConnectionKind, ConnectionPreference
from ibm_watsonx_orchestrate.agent_builder.connections.types import ConnectionSendVia, ConnectionCredentialsEntry
from pydantic import BaseModel, Field
from typing import Optional, List

class BaseConnectionOptions(BaseModel):
    app_id: str = Field(
        description="The app id of the connection to configure"
    )
    environment: ConnectionEnvironment = Field(
        description="The environemnt you wish to configre the connection for."
    )

class ConfigureConnectionsOptions(BaseConnectionOptions):
    type: ConnectionPreference = Field(
        description="The type of connection you wish to configure. Setting type to 'team' will mean the connection's credentials are shared by all users. Setting 'member' will require each user to provide their own credentials for the connection"
    )
    kind: ConnectionKind = Field(
        description="The kind of connection you wish to configure."
    )
    server_url: Optional[str]=Field(
        default=None,
        description="The url the connections credentials will be used against."
    )
    sso: bool = Field(
        default=False,
        description="If true, the connection will be configured to use single sign on. Only supported when kind is 'oauth_auth_on_behalf_of_flow' and is required to be true in that case"
    )
    idp_token_use: Optional[str] = Field(
        default=None,
        description="The token use used by the identity provider when using single sign on. Only supported when sso is true"
    )
    idp_token_type: Optional[str] = Field(
        default=None,
        description="The token type used by the identity provider when using single sign on. Only supported when sso is true"
    )
    idp_token_header: Optional[List[str]] = Field(
        default=None,
        description="Header values for the identity provider token request. Defaults to using 'content-type: application/x-www-form-urlencoded'. Formatted as <header_key>: <header_value>. Only supported when sso is true"
    )
    app_token_header: Optional[List[str]] = Field(
        default=None,
        description="Header values for the application token request. Defaults to using 'content-type: application/x-www-form-urlencoded'. Formatted as <header_key>: <header_value>. Only supported when sso is true"
    )

class SetCredentialsConnectionOptions(BaseConnectionOptions):
    username: Optional[str] = Field(
        default=None,
        description="The username to login with. Required when connection kind is 'basic' or 'oauth_auth_password_flow'"
    )
    password: Optional[str] = Field(
        default=None,
        description="The password to login with. Required when connection kind is 'basic' or 'oauth_auth_password_flow'"
    )
    token: Optional[str] = Field(
        default=None,
        description="The bearer token to login with. Required when connection kind is 'bearer'"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="The api key to login with. Required when connection kind is 'api_key'"
    )
    client_id: Optional[str] = Field(
        default=None,
        description="The client id for the OAuth request. Required when connection kind is 'oauth_auth_code_flow', 'oauth_auth_client_credentials_flow', 'oauth_auth_password_flow' or 'oauth_auth_on_behalf_of_flow'"
    )
    client_secret: Optional[str] = Field(
        default=None,
        description="The client secret for the OAuth request. Required when connection kind is 'oauth_auth_code_flow', 'oauth_auth_client_credentials_flow' or 'oauth_auth_password_flow'"
    )
    send_via: Optional[ConnectionSendVia] = Field(
        default=None,
        description="The location where the token will be sent during the OAuth handshake. Used when connection kind is 'oauth_auth_client_credentials_flow'. Defaults to 'header'."
    )
    token_url: Optional[str] = Field(
        default=None,
        description="The url to request the token from. Required when connection kind is 'oauth_auth_code_flow', 'oauth_auth_client_credentials_flow', 'oauth_auth_password_flow' or 'oauth_auth_on_behalf_of_flow'"
    )
    auth_url: Optional[str] = Field(
        default=None,
        description="The url to request the authorization from. Required when connection kind is 'oauth_auth_code_flow'"
    )
    grant_type: Optional[str] = Field(
        default=None,
        description="The grant type of the token requested for the token server. Required when connections kind is 'oauth_auth_on_behalf_of_flow'. Defaults for 'oauth_auth_client_credentials_flow' to 'client_credentials' and for 'oauth_auth_password_flow' it defaults to 'password'"
    )
    scope: Optional[List[str]] = Field(
        default=None,
        description="An optional set of scopes. Used for 'oauth_auth_code_flow', 'oauth_auth_client_credentials_flow' and 'oauth_auth_password_flow'"
    )
    entries: Optional[dict] = Field(
        default=None,
        description="A dictionary containing arbitrary key value pairs to be used in the key_value connection. Required when kind is  'key_value'"
    )
    token_entries: Optional[List[ConnectionCredentialsEntry]] = Field(
        default=None,
        description="A list of optional custom fields to be passed with OAuth token requests. Supported when connection kind is 'oauth_auth_code_flow', 'oauth_auth_client_credentials_flow', 'oauth_auth_password_flow' or 'oauth_auth_on_behalf_of_flow'"
    )
    auth_entries: Optional[List[ConnectionCredentialsEntry]] = Field(
        default=None,
        description="A list of optional custom fields to be passed with OAuth authorization requests. Supported when connection kind is 'oauth_auth_code_flow'. Location must be 'query'."
    )

class SetIdentityProviderOptions(BaseConnectionOptions):
    url: str = Field(description="The URL of the identity provider service")
    client_id: str = Field(description="The client id used to authenticate with the identity provider")
    client_secret: str = Field(description="The client secret used to authenticate with the identity provider")
    scope: str = Field(description="The scope used to authenticate with the identity provider")
    grant_type: str = Field(description="The grant type requested from the identity provider")
    token_entries: Optional[List[ConnectionCredentialsEntry]] = Field(
        default=None,
        description="A list of optional custom fields to be passed with OAuth token requests. Supported when connection kind is 'oauth_auth_code_flow', 'oauth_auth_client_credentials_flow', 'oauth_auth_password_flow' or 'oauth_auth_on_behalf_of_flow'"
    )