from ibm_watsonx_orchestrate.client.base_service_instance import BaseServiceInstance
import logging
import requests
from ibm_watsonx_orchestrate.client.credentials import Credentials
import json
import base64
from requests.exceptions import ConnectionError, Timeout, SSLError, HTTPError
import sys
from ibm_watsonx_orchestrate.client.utils import handle_error

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
        try:
            resp = requests.post(
                DEFAULT_LOCAL_AUTH_ENDPOINT,
                data=DEFAULT_USER,
            )
            resp.raise_for_status()

            return resp.json()["access_token"]

        except Timeout as e:
            handle_error(
                "Auth service did not respond in time.",
                e
            )

        except ConnectionError as e:
            handle_error(
                "Could not connect to the auth service. "
                "Please make sure that all services are up and running.",
                e
            )

        except SSLError as e:
            handle_error(
                "TLS error while connecting to the auth service.",
                e
            )

        except HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            handle_error(
                f"Auth service returned HTTP {status}. "
                "Check credentials or service logs.",
                e
            )

        except Exception as e:
            handle_error(
                "Failed to fetch access token. "
                "Check credentials or service logs.",
                e
            )

    def _get_tenant_token(self, tenant_id: str):
        try:
            resp = requests.post(
                DEFAULT_LOCAL_TENANT_AUTH_ENDPOINT.format(
                    DEFAULT_LOCAL_SERVICE_URL,
                    tenant_id,
                ),
                data=DEFAULT_USER,
            )
            resp.raise_for_status()

            return resp.json()["access_token"]

        except Timeout as e:
            handle_error(
                "Tenant auth service did not respond in time.",
                e
            )

        except ConnectionError as e:
            handle_error(
                "Could not connect to the tenant auth service. "
                "Please make sure all services are up and running.",
                e
            )

        except SSLError as e:
            handle_error(
                "TLS error while connecting to the tenant auth service.",
                e
            )

        except HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            handle_error(
                f"Tenant auth service returned HTTP {status}.",
                e
            )

        except Exception as e:
            handle_error(
                "Failed to fetch tenant access token. "
                "Check credentials or service logs.",
                e
            )

    def _create_token(self) -> str:

        return self._get_tenant_token(self.tenant_id)
