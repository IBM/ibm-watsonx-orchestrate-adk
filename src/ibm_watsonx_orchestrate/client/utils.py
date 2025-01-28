from ibm_watsonx_orchestrate.cli.config import DEFAULT_CONFIG_FILE_FOLDER, DEFAULT_CONFIG_FILE, AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE
from threading import Lock
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
import logging
from typing import TypeVar
import os

logger = logging.getLogger(__name__)
LOCK = Lock()
T = TypeVar("T", bound=BaseAPIClient)


def is_local_dev(url: str) -> bool:
    if url.startswith("http://localhost"):
        return True

    if url.startswith("http://127.0.0.1"):
        return True

    if url.startswith("http://[::1]"):
        return True

    if url.startswith("http://0.0.0.0"):
        return True

    return False


def instantiate_client(client: type(T)):
    with LOCK:
        with open(os.path.join(DEFAULT_CONFIG_FILE_FOLDER, DEFAULT_CONFIG_FILE), "r") as f:
            config = yaml_safe_load(f)
        url = config.get("app", {}).get("wxo_url", None)
        with open(os.path.join(AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE), "r") as f:
            auth_config = yaml_safe_load(f)
        token = auth_config.get("auth", {}).get("wxo_mcsp_token", {}).get("token")
        if not url or not token:
            raise ValueError("both url and token are required for the client. Please re-login")
        client_instance = client(base_url=url, api_key=token, is_local=is_local_dev(url))
    return client_instance