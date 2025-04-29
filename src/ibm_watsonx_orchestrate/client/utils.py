from ibm_watsonx_orchestrate.cli.config import (
    Config,
    DEFAULT_CONFIG_FILE_FOLDER,
    DEFAULT_CONFIG_FILE,
    AUTH_CONFIG_FILE_FOLDER,
    AUTH_CONFIG_FILE,
    AUTH_SECTION_HEADER,
    AUTH_MCSP_TOKEN_OPT,
    CONTEXT_SECTION_HEADER,
    CONTEXT_ACTIVE_ENV_OPT,
    ENVIRONMENTS_SECTION_HEADER,
    ENV_WXO_URL_OPT
)
from threading import Lock
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
import logging
from typing import TypeVar
import os
import jwt
import time

logger = logging.getLogger(__name__)
LOCK = Lock()
T = TypeVar("T", bound=BaseAPIClient)


def is_local_dev(url: str | None = None) -> bool:
    if url is None:
        cfg = Config()
        active_env = cfg.read(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
        url = cfg.get(ENVIRONMENTS_SECTION_HEADER, active_env, ENV_WXO_URL_OPT)

    if url.startswith("http://localhost"):
        return True

    if url.startswith("http://127.0.0.1"):
        return True

    if url.startswith("http://[::1]"):
        return True

    if url.startswith("http://0.0.0.0"):
        return True

    return False

def check_token_validity(token: str) -> bool:
    try:
        token_claimset = jwt.decode(token, options={"verify_signature": False})
        expiry = token_claimset.get('exp')

        current_timestamp = int(time.time())
        # Check if the token is not expired (or will not be expired in 10 minutes)
        if not expiry or current_timestamp < expiry - 600:
            return True
        return False
    except:
        return False


def instantiate_client(client: type[T] , url: str | None=None) -> T:
    try:
        with LOCK:
            with open(os.path.join(DEFAULT_CONFIG_FILE_FOLDER, DEFAULT_CONFIG_FILE), "r") as f:
                config = yaml_safe_load(f)
            active_env = config.get(CONTEXT_SECTION_HEADER, {}).get(CONTEXT_ACTIVE_ENV_OPT)

            if not url:
                url = config.get(ENVIRONMENTS_SECTION_HEADER, {}).get(active_env, {}).get(ENV_WXO_URL_OPT)

            with open(os.path.join(AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE), "r") as f:
                auth_config = yaml_safe_load(f)
            auth_settings = auth_config.get(AUTH_SECTION_HEADER, {}).get(active_env, {})

            if not active_env:
                logger.error("No active environment set. Use `orchestrate env activate` to activate an environment")
                exit(1)
            if not url:
                logger.error(f"No URL found for environment '{active_env}'. Use `orchestrate env list` to view existing environments and `orchesrtate env add` to reset the URL")
                exit(1)
            if not auth_settings:
                logger.error(f"No credentials found for active env '{active_env}'. Use `orchestrate env activate {active_env}` to refresh your credentials")
                exit(1)
            token = auth_settings.get(AUTH_MCSP_TOKEN_OPT)
            if not check_token_validity(token):
                logger.error(f"The token found for environment '{active_env}' is missing or expired. Use `orchestrate env activate {active_env}` to fetch a new one")
                exit(1)
            client_instance = client(base_url=url, api_key=token, is_local=is_local_dev(url))

        return client_instance
    except FileNotFoundError as e:
        message = "No active environment found. Please run `orchestrate env activate` to activate an environment"
        logger.error(message)
        raise FileNotFoundError(message)