from ibm_watsonx_orchestrate.client.base_service_instance import BaseServiceInstance
import logging
import requests
from ibm_watsonx_orchestrate.client.credentials import Credentials
import json
import base64

logger = logging.getLogger(__name__)

DEFAULT_TENANT = {
    "name": "wxo-dev",
    "title": "WatsonX Orchestrate Development",
    "tags": ["test"]
}

DEFAULT_USER = json.loads(base64.b64decode('eyJ1c2VybmFtZSI6ICJ3eG8uYXJjaGVyQGlibS5jb20iLCJwYXNzd29yZCI6ICJ3YXRzb254In0='))
DEFAULT_LOCAL_SERVICE_URL = "http://localhost:4321"
DEFAULT_LOCAL_AUTH_ENDPOINT = f"{DEFAULT_LOCAL_SERVICE_URL}/api/v1/auth/token"
DEFAULT_LOCAL_TENANT_URL = f"{DEFAULT_LOCAL_SERVICE_URL}/api/v1/tenants"
DEFAULT_LOCAL_TENANT_AUTH_ENDPOINT = "{}/api/v1/auth/token?tenant_id={}"


class LocalServiceInstance(BaseServiceInstance):
    """lite service instance for local development"""

    def __init__(self, client) -> None:

        self._logger = logging.getLogger(__name__)
        self._client = client
        self._credentials: Credentials = client.credentials
        self._credentials.local_global_token = self._get_user_auth_token()

        self.tenant_id = self._create_default_tenant_if_not_exist()
        self.tenant_access_token = self._get_tenant_token(self.tenant_id)
        # the local token does not have exp claim.
        self._client.token = self.tenant_access_token
        super().__init__()

    @staticmethod
    def get_default_tenant(apikey):
        headers = {"Authorization": f"Bearer {apikey}",
                   "Content-Type": "application/json"}
        resp = requests.get(DEFAULT_LOCAL_TENANT_URL, headers=headers)
        if resp.status_code == 200:
            tenant_config = resp.json()
            for tenant in tenant_config:
                if tenant["name"] == DEFAULT_TENANT["name"]:
                    return tenant
            return {}
        else:
            resp.raise_for_status()

    @staticmethod
    def create_default_tenant(apikey):
        headers = {"Authorization": f"Bearer {apikey}",
                   "Content-Type": "application/json"}
        resp = requests.post(DEFAULT_LOCAL_TENANT_URL, headers=headers, json=DEFAULT_TENANT)
        if resp.status_code == 201:
            return True
        else:
            resp.raise_for_status()

    def _create_default_tenant_if_not_exist(self) -> str:
        user_auth_token = self._credentials.local_global_token
        default_tenant = self.get_default_tenant(user_auth_token)

        if not default_tenant:
            logger.info("no local tenant found. A default tenant is created")
            self.create_default_tenant(user_auth_token)
            default_tenant = self.get_default_tenant(user_auth_token)
        else:
            logger.info("local tenant found")
        tenant_id = default_tenant["id"]
        return tenant_id

    def _get_user_auth_token(self):
        resp = requests.post(DEFAULT_LOCAL_AUTH_ENDPOINT, data=DEFAULT_USER)
        if resp.status_code == 200:
            return resp.json()["access_token"]
        else:
            resp.raise_for_status()

    def _get_tenant_token(self, tenant_id: str):
        resp = requests.post(DEFAULT_LOCAL_TENANT_AUTH_ENDPOINT.format(DEFAULT_LOCAL_SERVICE_URL, tenant_id),
                             data=DEFAULT_USER)
        if resp.status_code == 200:
            return resp.json()["access_token"]
        else:
            resp.raise_for_status()

    def _create_token(self) -> str:

        return self._get_tenant_token(self.tenant_id)
