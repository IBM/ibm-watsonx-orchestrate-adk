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
    ENV_WXO_URL_OPT,
    BYPASS_SSL,
    VERIFY
)
from threading import Lock
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from ibm_watsonx_orchestrate.cli.commands.channels.types import RuntimeEnvironmentType
import logging
from typing import TypeVar
import os
import jwt
import time
import sys

logger = logging.getLogger(__name__)
LOCK = Lock()
T = TypeVar("T", bound=BaseAPIClient)


def get_current_env_url() -> str:
    cfg = Config()
    active_env = cfg.read(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
    return cfg.get(ENVIRONMENTS_SECTION_HEADER, active_env, ENV_WXO_URL_OPT)

def is_local_dev(url: str | None = None) -> bool:
    if url is None:
        url = get_current_env_url()

    if url.startswith("http://localhost"):
        return True

    if url.startswith("http://127.0.0.1"):
        return True

    if url.startswith("http://[::1]"):
        return True

    if url.startswith("http://0.0.0.0"):
        return True

    return False

def is_ga_platform(url: str | None = None) -> bool:
    if url is None:
        url = get_current_env_url()
        
    if url.__contains__("orchestrate.ibm.com"):
        return True
    return False

def is_saas_env():
    return is_ga_platform() or is_ibm_cloud_platform()

def is_ibm_cloud_platform(url:str | None = None) -> bool:
    if url is None:
        url = get_current_env_url()

    if url.__contains__("cloud.ibm.com"):
        return True
    return False

def is_cpd_env(url: str | None = None) -> bool:
    if url is None:
        url = get_current_env_url()

    if url.lower().startswith("https://cpd"):
        return True
    return False

def get_environment() -> str:
    if is_local_dev():
        return RuntimeEnvironmentType.LOCAL
    if is_cpd_env():
        return RuntimeEnvironmentType.CPD
    if is_ibm_cloud_platform():
        return RuntimeEnvironmentType.IBM_CLOUD
    if is_ga_platform():
        return RuntimeEnvironmentType.AWS
    return None

def get_cpd_instance_id_from_url(url: str | None = None) -> str:
    if url is None:
        url = get_current_env_url()

    if not is_cpd_env(url):
        logger.error(f"The host {url} is not a CPD instance")
        sys.exit(1)

    url_fragments = url.split('/')
    return url_fragments[-1] if url_fragments[-1] else url_fragments[-2]

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
            bypass_ssl = (
                config.get(ENVIRONMENTS_SECTION_HEADER, {})
                    .get(active_env, {})
                    .get(BYPASS_SSL, None)
            )

            verify = (
                config.get(ENVIRONMENTS_SECTION_HEADER, {})
                    .get(active_env, {})
                    .get(VERIFY, None)
            )

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
            is_cpd = is_cpd_env(url)
            if is_cpd:
                if bypass_ssl is True:
                    client_instance = client(base_url=url, api_key=token, is_local=is_local_dev(url), verify=False)
                elif verify is not None:
                    client_instance = client(base_url=url, api_key=token, is_local=is_local_dev(url), verify=verify)
            else:
                client_instance = client(base_url=url, api_key=token, is_local=is_local_dev(url))

        return client_instance
    except FileNotFoundError as e:
        message = "No active environment found. Please run `orchestrate env activate` to activate an environment"
        logger.error(message)
        raise FileNotFoundError(message)