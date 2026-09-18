
import logging
import os
import requests

from ibm_watsonx_orchestrate_clients.common.base_client import BaseAPIClient

logger = logging.getLogger(__name__)

LANGFLOW_BASE_URL = "http://localhost:7861"
LANGFLOW_SUPERUSER_ENV = "LANGFLOW_SUPERUSER"
LANGFLOW_SUPERUSER_PASSWORD_ENV = "LANGFLOW_SUPERUSER_PASSWORD"


def _acquire_langflow_token(base_url: str, username: str | None = None, password: str | None = None) -> str | None:
    """Acquire a Langflow API token.

    If username/password are provided, authenticates via POST /api/v1/login.
    Otherwise attempts the auto-login endpoint (GET /api/v1/auto_login),
    which works when LANGFLOW_AUTO_LOGIN=true is set on the server.
    Returns None if neither method succeeds.
    """
    if username and password:
        try:
            resp = requests.post(
                f"{base_url}/api/v1/login",
                data={"username": username, "password": password},
            )
            resp.raise_for_status()
            return resp.json()["access_token"]
        except Exception as e:
            raise RuntimeError(f"Langflow authentication failed: {e}") from e

    # No credentials provided — fall back to auto-login
    logger.debug("No Langflow credentials provided, falling back to auto-login endpoint")
    resp = requests.get(f"{base_url}/api/v1/auto_login")
    if resp.status_code == 200:
        return resp.json().get("access_token")

    return None


class BaseLangflowClient(BaseAPIClient):

  def __init__(self, api_key: str | None = None, verify: str | None = None, authenticator = None):
    if api_key is None:
      username = os.environ.get(LANGFLOW_SUPERUSER_ENV)
      password = os.environ.get(LANGFLOW_SUPERUSER_PASSWORD_ENV)
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


