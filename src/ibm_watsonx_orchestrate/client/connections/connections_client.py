from typing import List

from ibm_cloud_sdk_core.authenticators import MCSPAuthenticator
from pydantic import BaseModel, ValidationError, Field, AliasChoices
from typing import Optional, Annotated

from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient, ClientAPIException
from ibm_watsonx_orchestrate.agent_builder.connections.types import ConnectionEnvironment, ConnectionPreference, ConnectionConfiguration, ConnectionAuthType, ConnectionSecurityScheme, IdpConfigData, AppConfigData, ConnectionType
from ibm_watsonx_orchestrate.client.utils import is_cpd_env, is_local_dev

import logging
logger = logging.getLogger(__name__)

class ListConfigsResponse(BaseModel):
    connection_id: str = None,
    app_id: str = None
    name: str = None
    security_scheme: ConnectionSecurityScheme | None = None,
    auth_type: str | None = None,
    environment:  ConnectionEnvironment | None = None,
    preference: ConnectionPreference | None = None,
    credentials_entered: bool | None = False

class GetConfigResponse(BaseModel):
    config_id: str = None
    tenant_id: str = None
    app_id: str = None
    environment: ConnectionEnvironment = None
    preference: ConnectionPreference = None
    auth_type: str | None = None
    sso: bool = None
    security_scheme: ConnectionSecurityScheme = None
    server_url: str | None = None
    idp_config_data: Annotated[Optional[IdpConfigData], Field(validation_alias=AliasChoices('idp_config_data', 'idp_config'), serialization_alias='idp_config_data')] = None
    app_config_data: Annotated[Optional[AppConfigData], Field(validation_alias=AliasChoices('app_config_data', 'app_config'), serialization_alias='app_config_data')] = None

    def as_config(self):
        return ConnectionConfiguration.model_validate(dict(self), context="export")

class GetConnectionResponse(BaseModel):
    connection_id: str = None
    app_id: str = None
    tenant_id: Optional[str] = None



class ConnectionsClient(BaseWXOClient):
    def __init__(self, base_url: str, api_key: str = None, is_local: bool = False, verify: str = None, authenticator: MCSPAuthenticator = None):
        super(ConnectionsClient, self).__init__(base_url, api_key, is_local, verify, authenticator)
        if is_local_dev(base_url):
            self.base_url = f"{base_url.rstrip('/')}/api/v1/orchestrate"
        else:
            self.base_url = f"{base_url.rstrip('/')}/v1/orchestrate"
    """
    Client to handle CRUD operations for Connections endpoint
    """
    # POST api/v1/connections/applications
    def create(self, payload: dict) -> None:
        self._post("/connections/applications", data=payload)

    # DELETE api/v1/connections/applications/{app_id}
    def delete(self, app_id: str) -> dict:
        return self._delete(f"/connections/applications/{app_id}")

    # GET /api/v1/connections/applications/{app_id}
    def get(self, app_id: str) -> GetConnectionResponse | None:
        try:
            return GetConnectionResponse.model_validate(self._get(f"/connections/applications?app_id={app_id}"))
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return None
            raise e


    # GET api/v1/connections/applications
    def list(self) -> List[ListConfigsResponse]:
        try:
            res = self._get(f"/connections/applications?include_details=true")
            import json
            json.dumps(res)
            return [ListConfigsResponse.model_validate(conn) for conn in res.get("applications", [])]
        except ValidationError as e:
            logger.error("Recieved unexpected response from server")
            raise e
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return []
            raise e


    # POST /api/v1/connections/applications/{app_id}/configurations
    def create_config(self, app_id: str, payload: dict) -> None:
        self._post(f"/connections/applications/{app_id}/configurations", data=payload)

    # PATCH /api/v1/connections/applications/{app_id}/configurations/{env}
    def update_config(self, app_id: str, env: ConnectionEnvironment, payload: dict) -> None:
        self._patch(f"/connections/applications/{app_id}/configurations/{env}", data=payload)

    # `GET /api/v1/connections/applications/{app_id}/configurations/{env}'
    def get_config(self, app_id: str, env: ConnectionEnvironment) -> GetConfigResponse:
        try:
            res = self._get(f"/connections/applications/{app_id}/configurations/{env}")
            return GetConfigResponse.model_validate(res)
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return None
            raise e

    # POST /api/v1/connections/applications/{app_id}/configs/{env}/credentials
    # POST /api/v1/connections/applications/{app_id}/configs/{env}/runtime_credentials
    def create_credentials(self, app_id: str, env: ConnectionEnvironment, payload: dict, use_app_credentials: bool) -> None:
        if use_app_credentials:
            self._post(f"/connections/applications/{app_id}/configs/{env}/credentials", data=payload)
        else:
            self._post(f"/connections/applications/{app_id}/configs/{env}/runtime_credentials", data=payload)

    # PATCH /api/v1/connections/applications/{app_id}/configs/{env}/credentials
    # PATCH /api/v1/connections/applications/{app_id}/configs/{env}/runtime_credentials
    def update_credentials(self, app_id: str, env: ConnectionEnvironment, payload: dict, use_app_credentials: bool) -> None:
        if use_app_credentials:
            self._patch(f"/connections/applications/{app_id}/configs/{env}/credentials", data=payload)
        else:
            self._patch(f"/connections/applications/{app_id}/configs/{env}/runtime_credentials", data=payload)

    # GET /api/v1/connections/applications/{app_id}/configs/credentials?env={env}
    # GET /api/v1/connections/applications/{app_id}/configs/runtime_credentials?env={env}
    def get_credentials(self, app_id: str, env: ConnectionEnvironment, use_app_credentials: bool) -> dict:
        try:
            if use_app_credentials:
                return self._get(f"/connections/applications/{app_id}/credentials/{env}")
            else:
                return self._get(f"/connections/applications/runtime_credentials?app_id={app_id}&env={env}")
        except ClientAPIException as e:
            # Returns 400 when app creds exist but runtime cred don't yet exist
            if e.response.status_code == 404 or e.response.status_code == 400:
                return None
            raise e

    # DELETE /api/v1/connections/applications/{app_id}/configs/{env}/credentials
    # DELETE /api/v1/connections/applications/{app_id}/configs/{env}/runtime_credentials
    def delete_credentials(self, app_id: str, env: ConnectionEnvironment, use_app_credentials: bool) -> None:
        if use_app_credentials:
            self._delete(f"/connections/applications/{app_id}/configs/{env}/credentials")
        else:
            self._delete(f"/connections/applications/{app_id}/configs/{env}/runtime_credentials")

    def get_draft_by_app_id(self, app_id: str) -> GetConnectionResponse:
        return self.get(app_id=app_id)

    def get_draft_by_app_ids(self, app_ids: List[str]) -> List[GetConnectionResponse]:
        connections = []
        for app_id in app_ids:
            connection = self.get_draft_by_app_id(app_id)
            if connection:
                connections += connection
        return connections

    def get_draft_by_id(self, conn_id) -> str:
        """Retrieve the app ID for a given connection ID."""
        if conn_id is None:
            return ""
        try:
            app_details = self._get(f"/connections/applications?connection_id={conn_id}")
            return app_details.get("app_id")
        except ClientAPIException as e:
            if e.response.status_code == 404:
                logger.warning(f"Connections not found. Returning connection ID: {conn_id}")
                return conn_id
            raise e

    def get_drafts_by_ids(self, conn_ids) -> List[ListConfigsResponse]:
        if not conn_ids:
            return []
        try:
            res = self._get(f"/connections/applications?include_details=true&connectionIds={','.join(conn_ids)}")
            import json
            json.dumps(res)
            return [ListConfigsResponse.model_validate(conn) for conn in res.get("applications", [])]
        except ValidationError as e:
            logger.error("Recieved unexpected response from server")
            raise e
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return []
            raise e