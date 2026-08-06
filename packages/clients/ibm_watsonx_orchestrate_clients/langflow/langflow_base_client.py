
import os
import requests

from ibm_watsonx_orchestrate_clients.common.base_client import BaseAPIClient

LANGFLOW_BASE_URL = "http://localhost:7861"
LANGFLOW_SUPERUSER_ENV = "LANGFLOW_SUPERUSER"
LANGFLOW_SUPERUSER_PASSWORD_ENV = "LANGFLOW_SUPERUSER_PASSWORD"


def _acquire_langflow_token(base_url: str, username: str, password: str) -> str:
    """POST to Langflow's login endpoint and return the access token."""
    resp = requests.post(
        f"{base_url}/api/v1/login",
        data={"username": username, "password": password},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


class BaseLangflowClient(BaseAPIClient):

  def __init__(self, api_key: str | None = None, verify: str | None = None, authenticator = None):
    username = os.environ.get(LANGFLOW_SUPERUSER_ENV)
    password = os.environ.get(LANGFLOW_SUPERUSER_PASSWORD_ENV)

    if api_key is None and username and password:
      api_key = _acquire_langflow_token(LANGFLOW_BASE_URL, username, password)

    super().__init__(base_url=LANGFLOW_BASE_URL, api_key=api_key, verify=verify, authenticator=authenticator)
    self.base_url += "/api"


class LangflowClient(BaseLangflowClient):

  def version(self):
    return self._get("/v1/version").get('version')
  
  def main_version(self):
    return self._get("/v1/version").get('main_version')
  
  def package(self):
    return self._get("/v1/version").get('package')


