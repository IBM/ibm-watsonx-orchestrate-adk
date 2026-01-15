import platform
from pathlib import Path
import re

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
from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from ibm_watsonx_orchestrate.cli.commands.channels.types import RuntimeEnvironmentType
import logging
from typing import List, TypeVar
import os
import jwt
import time
import sys

logger = logging.getLogger(__name__)
LOCK = Lock()
T = TypeVar("T", bound=BaseWXOClient)

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

    if ".cloud.ibm.com" in url:
        return True
    return False

def is_cpd_env(url: str | None = None) -> bool:
    if url is None:
        url = get_current_env_url()

    if url.lower().startswith("https://cpd"):
        return True
    return False

def get_cpd_instance_id_from_url(url: str | None = None) -> str:
    if url is None:
        url = get_current_env_url()

    if not is_cpd_env(url):
        logger.error(f"The host {url} is not a CPD instance")
        sys.exit(1)

    url_fragments = url.split('/')
    return url_fragments[-1] if url_fragments[-1] else url_fragments[-2]




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
            else:
                client_instance = client(base_url=url, api_key=token, is_local=is_local_dev(url))

        return client_instance
    except FileNotFoundError as e:
        message = "No active environment found. Please run `orchestrate env activate` to activate an environment"
        logger.error(message)
        raise FileNotFoundError(message)


def get_arm_architectures () -> list[str]:
    # NOTE: intentionally omitting 32 bit arm architectures.
    return ["aarch64", "arm64", "arm", "aarch64_be", "armv8b", "armv8l"]


def get_architecture () -> str:
    arch = platform.machine().lower()
    if arch in ("amd64", "x86_64"):
        return "amd64"
    elif arch in get_arm_architectures():
        return arch

    else:
        raise Exception("Unsupported architecture %s" % arch)


def is_arm_architecture () -> bool:
    return platform.machine().lower() in get_arm_architectures()


def get_linux_distribution () -> str:
    system_release = platform.freedesktop_os_release()
    release_short_name = system_release.get('ID','').lower()
    
    return release_short_name
    

def get_linux_package_manager () -> str:
    linux_distro = get_linux_distribution()
    match linux_distro:
        case "ubuntu" | "debian":
            return "apt"
        case "rhel":
            return "dnf"
        case _:
            raise Exception(f"Managed installation is not supported for the current linux distribution '{linux_distro}'")


def get_os_type () -> str:
    system_details = platform.uname()
    system = system_details.system.lower()
    match(system):
        case "darwin" | "windows":
            return system
        case "linux":
            release = system_details.release.lower()
            if "wsl" in release:
                return "wsl"
            else: 
                return system
        case _:
            raise Exception(f"Unsupported operating system {system}")


def path_for_vm(path: str | Path) -> str:
    system = get_os_type()

    if system == "windows":
        # On Windows, we need to be careful with paths that look like WSL paths
        # but might be resolved to a Windows format by Path.resolve().
        # First, ensure forward slashes for consistency.
        temp_path_str = str(path).replace("\\", "/")

        # Special handling for paths that already look like /mnt/c/ on input
        # or C:/mnt/c/ after some initial resolution
        if temp_path_str.startswith("/mnt/") :
            return temp_path_str
        elif temp_path_str.lower().startswith("c:/mnt/c/"): # Check for C:/mnt/c/ specifically
            # This is the problematic case where Path.resolve() might have prefixed 'C:/'
            # We want to remove the leading 'C:' and ensure it starts with /mnt/c/
            wsl_path = temp_path_str[2:]
            return wsl_path


        # If it's a standard Windows path, then proceed with the normal conversion
        p = Path(path).expanduser().resolve()
        resolved_path_str = str(p).replace("\\", "/") # Ensure forward slashes after resolve

        m = re.match(r"^([A-Za-z]):/(.*)$", resolved_path_str)
        if m:
            drive, rest = m.groups()
            wsl_path = f"/mnt/{drive.lower()}/{rest}"
            return wsl_path
        else:
            logger.warning(f"Could not convert recognized Windows path to WSL path. Returning as-is: {resolved_path_str}")
            return resolved_path_str
    else:
        # If not on a Windows system, assume the path is already correct or requires no conversion
        # Just resolve and normalize slashes
        resolved_path_str = str(Path(path).expanduser().resolve()).replace("\\", "/")
        return resolved_path_str
    
def concat_bin_files(target_bin_file: str, source_files: list[str], read_chunk_size: int = None,
                     delete_source_files_post: bool = True) -> None:
    if read_chunk_size is None:
        # default read chunk size is 100 MB.
        read_chunk_size = 100 * 1024 * 1024

    with open(target_bin_file, "wb") as target:
        for source_file in source_files:
            with open(source_file, "rb") as source:
                while True:
                    source_chunk = source.read(read_chunk_size)

                    if source_chunk:
                        target.write(source_chunk)

                    else:
                        break

            if delete_source_files_post is True:
                os.remove(source_file)

def command_to_list(command: str | List[str]):
    return command.split() if isinstance(command,str) else command
