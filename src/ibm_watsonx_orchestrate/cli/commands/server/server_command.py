import importlib.resources as resources
import logging
import os
import platform
import subprocess
import sys
import shutil
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import re
import jwt
import requests
import typer
from dotenv import dotenv_values

from ibm_watsonx_orchestrate.client.utils import instantiate_client

from ibm_watsonx_orchestrate.cli.commands.server.types import WatsonXAIEnvConfig, ModelGatewayEnvConfig

from ibm_watsonx_orchestrate.cli.commands.environment.environment_controller import _login

from ibm_watsonx_orchestrate.cli.config import LICENSE_HEADER, \
    ENV_ACCEPT_LICENSE

from ibm_watsonx_orchestrate.cli.config import PROTECTED_ENV_NAME, clear_protected_env_credentials_token, Config, \
    AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE, AUTH_MCSP_TOKEN_OPT, AUTH_SECTION_HEADER, USER_ENV_CACHE_HEADER, LICENSE_HEADER, \
    ENV_ACCEPT_LICENSE
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient

logger = logging.getLogger(__name__)

server_app = typer.Typer(no_args_is_help=True)

_EXPORT_FILE_TYPES: set[str] = {
    'py',
    'yaml',
    'yml',
    'json',
    'env'
}

_ALWAYS_UNSET: set[str] = {
    "WO_API_KEY",
    "WO_INSTANCE",
    "DOCKER_IAM_KEY",
    "WO_DEVELOPER_EDITION_SOURCE",
    "WATSONX_SPACE_ID",
    "WATSONX_APIKEY",
    "WO_USERNAME",
    "WO_PASSWORD",
}

NON_SECRET_ENV_ITEMS: set[str] = {
    "WO_DEVELOPER_EDITION_SOURCE",
    "WO_INSTANCE",
    "USE_SAAS_ML_TOOLS_RUNTIME",
    "AUTHORIZATION_URL",
    "OPENSOURCE_REGISTRY_PROXY",
    "SAAS_WDU_RUNTIME",
    "LATEST_ENV_FILE",
}
  
def define_saas_wdu_runtime(value: str = "none") -> None:
    cfg = Config()
    cfg.write(USER_ENV_CACHE_HEADER,"SAAS_WDU_RUNTIME",value)

def set_compose_file_path_in_env(path: str = None) -> None:
    Config().save(
        {
            USER_ENV_CACHE_HEADER: {
                "DOCKER_COMPOSE_FILE_PATH" : path
            }
        }
    )

def get_compose_file_path_from_env() -> str:
    return Config().read(USER_ENV_CACHE_HEADER,"DOCKER_COMPOSE_FILE_PATH")


def ensure_docker_installed() -> None:
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        logger.error("Unable to find an installed docker")
        sys.exit(1)

def ensure_docker_compose_installed() -> list:
    try:
        subprocess.run(["docker", "compose", "version"], check=True, capture_output=True)
        return ["docker", "compose"]
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    try:
        subprocess.run(["docker-compose", "version"], check=True, capture_output=True)
        return ["docker-compose"]
    except (FileNotFoundError, subprocess.CalledProcessError):
        typer.echo("Unable to find an installed docker-compose or docker compose")
        sys.exit(1)

def docker_login(api_key: str, registry_url: str, username:str = "iamapikey") -> None:
    logger.info(f"Logging into Docker registry: {registry_url} ...")
    result = subprocess.run(
        ["docker", "login", "-u", username, "--password-stdin", registry_url],
        input=api_key.encode("utf-8"),
        capture_output=True,
    )
    if result.returncode != 0:
        logger.error(f"Error logging into Docker:\n{result.stderr.decode('utf-8')}")
        sys.exit(1)
    logger.info("Successfully logged in to Docker.")

def docker_login_by_dev_edition_source(env_dict: dict, source: str) -> None:
    if env_dict.get('WO_DEVELOPER_EDITION_SKIP_LOGIN', None) == 'true':
        logger.info('WO_DEVELOPER_EDITION_SKIP_LOGIN is set to true, skipping login.')
        logger.warning('If the developer edition images are not already pulled this call will fail without first setting WO_DEVELOPER_EDITION_SKIP_LOGIN=false')
    else:
        if not env_dict.get("REGISTRY_URL"):
            raise ValueError("REGISTRY_URL is not set.")
        registry_url = env_dict["REGISTRY_URL"].split("/")[0]
        if source == "internal":
            iam_api_key = env_dict.get("DOCKER_IAM_KEY")
            if not iam_api_key:
                raise ValueError("DOCKER_IAM_KEY is required in the environment file if WO_DEVELOPER_EDITION_SOURCE is set to 'internal'.")
            docker_login(iam_api_key, registry_url, "iamapikey")
        elif source == "myibm":
            wo_entitlement_key = env_dict.get("WO_ENTITLEMENT_KEY")
            if not wo_entitlement_key:
                raise ValueError("WO_ENTITLEMENT_KEY is required in the environment file.")
            docker_login(wo_entitlement_key, registry_url, "cp")
        elif source == "orchestrate":
            wo_auth_type = env_dict.get("WO_AUTH_TYPE")
            api_key, username = get_docker_cred_by_wo_auth_type(env_dict, wo_auth_type)
            docker_login(api_key, registry_url, username)


def get_compose_file() -> Path:
    custom_compose_path = get_compose_file_path_from_env()
    return Path(custom_compose_path) if custom_compose_path else get_default_compose_file()


def get_default_compose_file() -> Path:
    with resources.as_file(
        resources.files("ibm_watsonx_orchestrate.docker").joinpath("compose-lite.yml")
    ) as compose_file:
        return compose_file


def get_default_env_file() -> Path:
    with resources.as_file(
        resources.files("ibm_watsonx_orchestrate.docker").joinpath("default.env")
    ) as env_file:
        return env_file


def read_env_file(env_path: Path|str) -> dict:
    return dotenv_values(str(env_path))

def merge_env(
    default_env_path: Path,
    user_env_path: Path | None
) -> dict:

    merged = dotenv_values(str(default_env_path))

    if user_env_path is not None:
        user_env = dotenv_values(str(user_env_path))
        merged.update(user_env)

    return merged

def get_default_registry_env_vars_by_dev_edition_source(default_env: dict, user_env:dict, source: str) -> dict[str,str]:
    component_registry_var_names = {key for key in default_env if key.endswith("_REGISTRY")} | {'REGISTRY_URL'}

    registry_url = user_env.get("REGISTRY_URL", None)
    if not registry_url:
        if source == "internal":
            registry_url = "us.icr.io/watson-orchestrate-private"
        elif source == "myibm":
            registry_url = "cp.icr.io/cp/wxo-lite"
        elif source == "orchestrate":
            # extract the hostname from the WO_INSTANCE URL, and replace the "api." prefix with "registry." to construct the registry URL per region
            wo_url = user_env.get("WO_INSTANCE")
            
            if not wo_url:
                raise ValueError("WO_INSTANCE is required in the environment file if the developer edition source is set to 'orchestrate'.")
            
            parsed = urlparse(wo_url)
            hostname = parsed.hostname
            
            registry_url = f"registry.{hostname[4:]}/cp/wxo-lite"
        else:
            raise ValueError(f"Unknown value for developer edition source: {source}. Must be one of ['internal', 'myibm', 'orchestrate'].")
    
    result = {name: registry_url for name in component_registry_var_names}
    return result

def get_dev_edition_source(env_dict: dict | None) -> str:
    if not env_dict:
        return "myibm"
    
    source = env_dict.get("WO_DEVELOPER_EDITION_SOURCE")

    if source:
        return source
    if env_dict.get("WO_INSTANCE"):
        return "orchestrate"
    return "myibm"

def get_docker_cred_by_wo_auth_type(env_dict: dict, auth_type: str | None) -> tuple[str, str]:
    # Try infer the auth type if not provided
    if not auth_type:
        instance_url = env_dict.get("WO_INSTANCE")
        if instance_url:
            if ".cloud.ibm.com" in instance_url:
                auth_type = "ibm_iam"
            elif ".ibm.com" in instance_url:
                auth_type = "mcsp"
            elif "https://cpd" in instance_url:
                auth_type = "cpd"
    
    if auth_type in {"mcsp", "ibm_iam"}:
        wo_api_key = env_dict.get("WO_API_KEY")
        if not wo_api_key:
            raise ValueError("WO_API_KEY is required in the environment file if the WO_AUTH_TYPE is set to 'mcsp' or 'ibm_iam'.")
        instance_url = env_dict.get("WO_INSTANCE")
        if not instance_url:
            raise ValueError("WO_INSTANCE is required in the environment file if the WO_AUTH_TYPE is set to 'mcsp' or 'ibm_iam'.")
        path = urlparse(instance_url).path
        if not path or '/' not in path:
            raise ValueError(f"Invalid WO_INSTANCE URL: '{instance_url}'. It should contain the instance (tenant) id.")
        tenant_id = path.split('/')[-1]
        return wo_api_key, f"wxouser-{tenant_id}"
    elif auth_type == "cpd":
        wo_api_key = env_dict.get("WO_API_KEY")
        wo_password = env_dict.get("WO_PASSWORD")
        if not wo_api_key and not wo_password:
            raise ValueError("WO_API_KEY or WO_PASSWORD is required in the environment file if the WO_AUTH_TYPE is set to 'cpd'.")
        wo_username = env_dict.get("WO_USERNAME")
        if not wo_username:
            raise ValueError("WO_USERNAME is required in the environment file if the WO_AUTH_TYPE is set to 'cpd'.")
        return wo_api_key or wo_password, wo_username  # type: ignore[return-value]
    else:
        raise ValueError(f"Unknown value for WO_AUTH_TYPE: '{auth_type}'. Must be one of ['mcsp', 'ibm_iam', 'cpd'].")
    
def apply_server_env_dict_defaults(provided_env_dict: dict) -> dict:

    env_dict = provided_env_dict.copy()

    env_dict['DBTAG'] = get_dbtag_from_architecture(merged_env_dict=env_dict)

    model_config = None
    try:
        use_model_proxy = env_dict.get("USE_SAAS_ML_TOOLS_RUNTIME")
        if not use_model_proxy or use_model_proxy.lower() != 'true':
            model_config = WatsonXAIEnvConfig.model_validate(env_dict)
    except ValueError:
        pass
    
    # If no watsonx ai detials are found, try build model gateway config
    if not model_config:
        try:
            model_config = ModelGatewayEnvConfig.model_validate(env_dict)
        except ValueError as e :
            pass
    
    if not model_config:
        logger.error("Missing required model access environment variables. Please set Watson Orchestrate credentials 'WO_INSTANCE' and 'WO_API_KEY'. For CPD, set 'WO_INSTANCE', 'WO_USERNAME' and either 'WO_API_KEY' or 'WO_PASSWORD'. Alternatively, you can set WatsonX AI credentials directly using 'WATSONX_SPACE_ID' and 'WATSONX_APIKEY'")
        sys.exit(1)

    env_dict.update(model_config.model_dump(exclude_none=True))

    return env_dict

def apply_llm_api_key_defaults(env_dict: dict) -> None:
    llm_value = env_dict.get("WATSONX_APIKEY")
    if llm_value:
        env_dict.setdefault("ASSISTANT_LLM_API_KEY", llm_value)
        env_dict.setdefault("ASSISTANT_EMBEDDINGS_API_KEY", llm_value)
        env_dict.setdefault("ROUTING_LLM_API_KEY", llm_value)
        env_dict.setdefault("BAM_API_KEY", llm_value)
        env_dict.setdefault("WXAI_API_KEY", llm_value)
    space_value = env_dict.get("WATSONX_SPACE_ID")
    if space_value:
        env_dict.setdefault("ASSISTANT_LLM_SPACE_ID", space_value)
        env_dict.setdefault("ASSISTANT_EMBEDDINGS_SPACE_ID", space_value)
        env_dict.setdefault("ROUTING_LLM_SPACE_ID", space_value)

def _is_docker_container_running(container_name):
    ensure_docker_installed()
    command = [ "docker",
                "ps",
                "-f",
                f"name={container_name}"
            ]
    result = subprocess.run(command, env=os.environ, capture_output=True)
    if container_name in str(result.stdout):
        return True
    return False

def _check_exclusive_observibility(langfuse_enabled: bool, ibm_tele_enabled: bool):
    if langfuse_enabled and ibm_tele_enabled:
        return False
    if langfuse_enabled and _is_docker_container_running("docker-frontend-server-1"):
        return False
    if ibm_tele_enabled and _is_docker_container_running("docker-langfuse-web-1"):
        return False
    return True

def _prepare_clean_env(env_file: Path) -> None:
    """Remove env vars so terminal definitions don't override"""
    keys_from_file = set(dotenv_values(str(env_file)).keys())
    keys_to_unset = keys_from_file | _ALWAYS_UNSET
    for key in keys_to_unset:
        os.environ.pop(key, None)

def write_merged_env_file(merged_env: dict, target_path: str = None) -> Path:

    if target_path:
        file = open(target_path,"w")
    else:
        file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env")

    with file:
        for key, val in merged_env.items():
            file.write(f"{key}={val}\n")
    return Path(file.name)

def get_dbtag_from_architecture(merged_env_dict: dict) -> str:
    """Detects system architecture and returns the corresponding DBTAG."""
    arch = platform.machine()

    arm64_tag = merged_env_dict.get("ARM64DBTAG")
    amd_tag = merged_env_dict.get("AMDDBTAG")

    if arch in ["aarch64", "arm64"]:
        return arm64_tag
    else:
        return amd_tag

def refresh_local_credentials() -> None:
    """
    Refresh the local credentials
    """
    clear_protected_env_credentials_token()
    _login(name=PROTECTED_ENV_NAME, apikey=None)

def persist_user_env(env: dict, include_secrets: bool = False) -> None:
    if include_secrets:
        persistable_env = env
    else:
        persistable_env = {k:env[k] for k in NON_SECRET_ENV_ITEMS if k in env}

    cfg = Config()
    cfg.save(
        {
            USER_ENV_CACHE_HEADER: persistable_env
        }
    )

def get_persisted_user_env() -> dict | None:
    cfg = Config()
    user_env = cfg.get(USER_ENV_CACHE_HEADER) if cfg.get(USER_ENV_CACHE_HEADER) else None
    return user_env

def run_compose_lite(
        final_env_file: Path, 
        experimental_with_langfuse=False, 
        experimental_with_ibm_telemetry=False, 
        with_doc_processing=False,
        with_voice=False,
        experimental_with_langflow=False,
    ) -> None:
    compose_path = get_compose_file()

    compose_command = ensure_docker_compose_installed()
    _prepare_clean_env(final_env_file)  
    db_tag = read_env_file(final_env_file).get('DBTAG', None)
    logger.info(f"Detected architecture: {platform.machine()}, using DBTAG: {db_tag}")

    # Step 1: Start only the DB container
    db_command = compose_command + [
        "-f", str(compose_path),
        "--env-file", str(final_env_file),
        "up",
        "-d",
        "--remove-orphans",
        "wxo-server-db"
    ]

    logger.info("Starting database container...")
    result = subprocess.run(db_command, env=os.environ, capture_output=False)

    if result.returncode != 0:
        logger.error(f"Error starting DB container: {result.stderr}")
        sys.exit(1)

    logger.info("Database container started successfully. Now starting other services...")


    # Step 2: Create Langflow DB (if enabled)
    if experimental_with_langflow:
        create_langflow_db()

    # Step 3: Start all remaining services (except DB)
    profiles = []
    if experimental_with_langfuse:
        profiles.append("langfuse")
    if experimental_with_ibm_telemetry:
        profiles.append("ibm-telemetry")
    if with_doc_processing:
        profiles.append("docproc")
    if with_voice:
        profiles.append("voice")
    if experimental_with_langflow:
        profiles.append("langflow")

    command = compose_command[:]
    for profile in profiles:
        command += ["--profile", profile]

    command += [
        "-f", str(compose_path),
        "--env-file", str(final_env_file),
        "up",
        "--scale",
        "ui=0",
        "--scale",
        "cpe=0",
        "-d",
        "--remove-orphans",
    ]

    logger.info("Starting docker-compose services...")
    result = subprocess.run(command, capture_output=False)

    if result.returncode == 0:
        logger.info("Services started successfully.")
        # Remove the temp file if successful
        if final_env_file.exists():
            final_env_file.unlink()
    else:
        error_message = result.stderr.decode('utf-8') if result.stderr else "Error occurred."
        logger.error(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n{error_message}"
        )
        sys.exit(1)

def wait_for_wxo_server_health_check(timeout_seconds=90, interval_seconds=2):
    url = "http://localhost:4321/api/v1/health/ready"

    start_time = time.time()
    errormsg = None
    while time.time() - start_time <= timeout_seconds:
        try:
            response = requests.get(url)
            if 200 <= response.status_code < 300:
                return True
            else:
                logger.debug(f"Response code from healthcheck {response.status_code}")
        except requests.RequestException as e:
            errormsg = e
            #print(f"Request failed: {e}")

        time.sleep(interval_seconds)
    if errormsg:
        logger.error(f"Health check request failed: {errormsg}")
    return False

def wait_for_wxo_ui_health_check(timeout_seconds=45, interval_seconds=2):
    url = "http://localhost:3000/chat-lite"
    logger.info("Waiting for UI component to be initialized...")
    start_time = time.time()
    while time.time() - start_time <= timeout_seconds:
        try:
            response = requests.get(url)
            if 200 <= response.status_code < 300:
                return True
            else:
                pass
                #print(f"Response code from UI healthcheck {response.status_code}")
        except requests.RequestException as e:
            pass
            #print(f"Request failed for UI: {e}")

        time.sleep(interval_seconds)
    logger.info("UI component is initialized")
    return False

def run_compose_lite_ui(user_env_file: Path) -> bool:
    compose_path = get_compose_file()
    compose_command = ensure_docker_compose_installed()
    _prepare_clean_env(user_env_file)  
    ensure_docker_installed()

    default_env = read_env_file(get_default_env_file())
    user_env = read_env_file(user_env_file) if user_env_file else {}
    if not user_env:
        user_env = get_persisted_user_env() or {}

    dev_edition_source = get_dev_edition_source(user_env)
    default_registry_vars = get_default_registry_env_vars_by_dev_edition_source(default_env, user_env, source=dev_edition_source)

    # Update the default environment with the default registry variables only if they are not already set
    for key in default_registry_vars:
        if key not in default_env or not default_env[key]:
            default_env[key] = default_registry_vars[key]

    # Merge the default environment with the user environment
    merged_env_dict = {
        **default_env,
        **user_env,
    }

    _login(name=PROTECTED_ENV_NAME)
    auth_cfg = Config(AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE)
    existing_auth_config = auth_cfg.get(AUTH_SECTION_HEADER).get(PROTECTED_ENV_NAME, {})
    existing_token = existing_auth_config.get(AUTH_MCSP_TOKEN_OPT) if existing_auth_config else None
    token = jwt.decode(existing_token, options={"verify_signature": False})
    tenant_id = token.get('woTenantId', None)
    merged_env_dict['REACT_APP_TENANT_ID'] = tenant_id

    agent_client = instantiate_client(AgentClient)
    agents = agent_client.get()
    if not agents:
        logger.error("No agents found for the current environment. Please create an agent before starting the chat.")
        sys.exit(1)

    try:
        docker_login_by_dev_edition_source(merged_env_dict, dev_edition_source)
    except ValueError as ignored:
        # do nothing, as the docker login here is not mandatory
        pass

    # Auto-configure callback IP for async tools
    merged_env_dict = auto_configure_callback_ip(merged_env_dict)

    #These are to removed warning and not used in UI component
    if not 'WATSONX_SPACE_ID' in merged_env_dict:
        merged_env_dict['WATSONX_SPACE_ID']='X'
    if not 'WATSONX_APIKEY' in merged_env_dict:
        merged_env_dict['WATSONX_APIKEY']='X'
    apply_llm_api_key_defaults(merged_env_dict)

    final_env_file = write_merged_env_file(merged_env_dict)

    logger.info("Waiting for orchestrate server to be fully started and ready...")

    health_check_timeout = int(merged_env_dict["HEALTH_TIMEOUT"]) if "HEALTH_TIMEOUT" in merged_env_dict else 120
    is_successful_server_healthcheck = wait_for_wxo_server_health_check(timeout_seconds=health_check_timeout)
    if not is_successful_server_healthcheck:
        logger.error("Healthcheck failed orchestrate server.  Make sure you start the server components with `orchestrate server start` before trying to start the chat UI")
        return False

    command = compose_command + [
        "-f", str(compose_path),
        "--env-file", str(final_env_file),
        "up",
        "ui",
        "-d",
        "--remove-orphans"
    ]

    logger.info(f"Starting docker-compose UI service...")
    result = subprocess.run(command, capture_output=False)

    if result.returncode == 0:
        logger.info("Chat UI Service started successfully.")
        # Remove the temp file if successful
        if final_env_file.exists():
            final_env_file.unlink()
    else:
        error_message = result.stderr.decode('utf-8') if result.stderr else "Error occurred."
        logger.error(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n{error_message}"
        )
        return False
    
    is_successful_ui_healthcheck = wait_for_wxo_ui_health_check()
    if not is_successful_ui_healthcheck:
        logger.error("The Chat UI service did not initialize within the expected time.  Check the logs for any errors.")

    return True

def run_compose_lite_down_ui(user_env_file: Path, is_reset: bool = False) -> None:
    compose_path = get_compose_file()
    compose_command = ensure_docker_compose_installed()
    _prepare_clean_env(user_env_file)  


    ensure_docker_installed()
    default_env_path = get_default_env_file()
    merged_env_dict = merge_env(
        default_env_path,
        user_env_file
    )
    merged_env_dict['WATSONX_SPACE_ID']='X'
    merged_env_dict['WATSONX_APIKEY']='X'
    apply_llm_api_key_defaults(merged_env_dict)
    final_env_file = write_merged_env_file(merged_env_dict)

    command = compose_command + [
        "-f", str(compose_path),
        "--env-file", str(final_env_file),
        "down",
        "ui"
    ]

    if is_reset:
        command.append("--volumes")
        logger.info("Stopping docker-compose UI service and resetting volumes...")
    else:
        logger.info("Stopping docker-compose UI service...")

    result = subprocess.run(command, capture_output=False)

    if result.returncode == 0:
        logger.info("UI service stopped successfully.")
        # Remove the temp file if successful
        if final_env_file.exists():
            final_env_file.unlink()
    else:
        error_message = result.stderr.decode('utf-8') if result.stderr else "Error occurred."
        logger.error(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n{error_message}"
        )
        sys.exit(1)

def run_compose_lite_down(final_env_file: Path, is_reset: bool = False) -> None:
    compose_path = get_compose_file()
    compose_command = ensure_docker_compose_installed()
    _prepare_clean_env(final_env_file)  

    command = compose_command + [
        '--profile', '*',
        "-f", str(compose_path),
        "--env-file", str(final_env_file),
        "down"
    ]

    if is_reset:
        command.append("--volumes")
        logger.info("Stopping docker-compose services and resetting volumes...")
    else:
        logger.info("Stopping docker-compose services...")

    result = subprocess.run(command, capture_output=False)

    if result.returncode == 0:
        logger.info("Services stopped successfully.")
        # Remove the temp file if successful
        if final_env_file.exists():
            final_env_file.unlink()
    else:
        error_message = result.stderr.decode('utf-8') if result.stderr else "Error occurred."
        logger.error(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n{error_message}"
        )
        sys.exit(1)

def run_compose_lite_logs(final_env_file: Path, is_reset: bool = False) -> None:
    compose_path = get_compose_file()
    compose_command = ensure_docker_compose_installed()
    _prepare_clean_env(final_env_file)  

    command = compose_command + [
        "-f", str(compose_path),
        "--env-file", str(final_env_file),
        "--profile",
        "*",
        "logs",
        "-f"
    ]

    logger.info("Docker Logs...")

    result = subprocess.run(command, capture_output=False)

    if result.returncode == 0:
        logger.info("End of docker logs")
        # Remove the temp file if successful
        if final_env_file.exists():
            final_env_file.unlink()
    else:
        error_message = result.stderr.decode('utf-8') if result.stderr else "Error occurred."
        logger.error(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n{error_message}"
        )
        sys.exit(1)

def confirm_accepts_license_agreement(accepts_by_argument: bool):
    cfg = Config()
    accepts_license = cfg.read(LICENSE_HEADER, ENV_ACCEPT_LICENSE)
    if accepts_license != True:
        logger.warning(('''
            By running the following command your machine will install IBM watsonx Orchestrate Developer Edition, which is governed by the following IBM license agreement:
            - * https://www.ibm.com/support/customer/csol/terms/?id=L-YRMZ-PB6MHM&lc=en
            Additionally, the following prerequisite open source programs will be obtained from Docker Hub and will be installed on your machine. Each of the below programs are Separately Licensed Code, and are governed by the separate license agreements identified below, and not by the IBM license agreement:
            * redis (7.2)               - https://github.com/redis/redis/blob/7.2.7/COPYING
            * minio                     - https://github.com/minio/minio/blob/master/LICENSE
            * milvus-io                 - https://github.com/milvus-io/milvus/blob/master/LICENSE
            * etcd                      - https://github.com/etcd-io/etcd/blob/main/LICENSE
            * clickhouse-server         - https://github.com/ClickHouse/ClickHouse/blob/master/LICENSE
            * langfuse                  - https://github.com/langfuse/langfuse/blob/main/LICENSE
            After installation, you are solely responsible for obtaining and installing updates and fixes, including security patches, for the above prerequisite open source programs. To update images the customer will run `orchestrate server reset && orchestrate server start -e .env`.
        ''').strip())
        if not accepts_by_argument:
            result = input('\nTo accept the terms and conditions of the IBM license agreement and the Separately Licensed Code licenses above please enter "I accept": ')
        else:
            result = None
        if result == 'I accept' or accepts_by_argument:
            cfg.write(LICENSE_HEADER, ENV_ACCEPT_LICENSE, True)
        else:
            logger.error('The terms and conditions were not accepted, exiting.')
            exit(1)

def auto_configure_callback_ip(merged_env_dict: dict) -> dict:
    """
    Automatically detect and configure CALLBACK_HOST_URL if it's empty.

    Args:
        merged_env_dict: The merged environment dictionary

    Returns:
        Updated environment dictionary with CALLBACK_HOST_URL set
    """
    callback_url = merged_env_dict.get('CALLBACK_HOST_URL', '').strip()

    # Only auto-configure if CALLBACK_HOST_URL is empty
    if not callback_url:
        logger.info("Auto-detecting local IP address for async tool callbacks...")

        system = platform.system()
        ip = None

        try:
            if system in ("Linux", "Darwin"):
                result = subprocess.run(["ifconfig"], capture_output=True, text=True, check=True)
                lines = result.stdout.splitlines()

                for line in lines:
                    line = line.strip()
                    # Unix ifconfig output format: "inet 192.168.1.100 netmask 0xffffff00 broadcast 192.168.1.255"
                    if line.startswith("inet ") and "127.0.0.1" not in line:
                        candidate_ip = line.split()[1]
                        # Validate IP is not loopback or link-local
                        if (candidate_ip and
                            not candidate_ip.startswith("127.") and
                            not candidate_ip.startswith("169.254")):
                            ip = candidate_ip
                            break

            elif system == "Windows":
                result = subprocess.run(["ipconfig"], capture_output=True, text=True, check=True)
                lines = result.stdout.splitlines()

                for line in lines:
                    line = line.strip()
                    # Windows ipconfig output format: "   IPv4 Address. . . . . . . . . . . : 192.168.1.100"
                    if "IPv4 Address" in line and ":" in line:
                        candidate_ip = line.split(":")[-1].strip()
                        # Validate IP is not loopback or link-local
                        if (candidate_ip and
                            not candidate_ip.startswith("127.") and
                            not candidate_ip.startswith("169.254")):
                            ip = candidate_ip
                            break

            else:
                logger.warning(f"Unsupported platform: {system}")
                ip = None

        except Exception as e:
            logger.debug(f"IP detection failed on {system}: {e}")
            ip = None

        if ip:
            callback_url = f"http://{ip}:4321"
            merged_env_dict['CALLBACK_HOST_URL'] = callback_url
            logger.info(f"Auto-configured CALLBACK_HOST_URL to: {callback_url}")
        else:
            # Fallback for localhost
            callback_url = "http://host.docker.internal:4321"
            merged_env_dict['CALLBACK_HOST_URL'] = callback_url
            logger.info(f"Using Docker internal URL: {callback_url}")
            logger.info("For external tools, consider using ngrok or similar tunneling service.")
    else:
        logger.info(f"Using existing CALLBACK_HOST_URL: {callback_url}")

    return merged_env_dict

def prepare_server_env_vars(user_env: dict = {}):
    
    default_env = read_env_file(get_default_env_file())
    dev_edition_source = get_dev_edition_source(user_env)
    default_registry_vars = get_default_registry_env_vars_by_dev_edition_source(default_env, user_env, source=dev_edition_source)
    
    # Update the default environment with the default registry variables only if they are not already set
    for key in default_registry_vars:
        if key not in default_env or not default_env[key]:
            default_env[key] = default_registry_vars[key]

    # Merge the default environment with the user environment
    merged_env_dict = {
        **default_env,
        **user_env,
    }

    merged_env_dict = apply_server_env_dict_defaults(merged_env_dict)

    # Auto-configure callback IP for async tools
    merged_env_dict = auto_configure_callback_ip(merged_env_dict)

    apply_llm_api_key_defaults(merged_env_dict)

    return merged_env_dict

@server_app.command(name="start")
def server_start(
    user_env_file: str = typer.Option(
        None,
        "--env-file", '-e',
        help="Path to a .env file that overrides default.env. Then environment variables override both."
    ),
    experimental_with_langfuse: bool = typer.Option(
        False,
        '--with-langfuse', '-l',
        help='Option to enable Langfuse support.'
    ),
    experimental_with_ibm_telemetry: bool = typer.Option(
        False,
        '--with-ibm-telemetry', '-i',
        help=''
    ),
    persist_env_secrets: bool = typer.Option(
        False,
        '--persist-env-secrets', '-p',
        help='Option to store secret values from the provided env file in the config file (~/.config/orchestrate/config.yaml)',
        hidden=True
    ),
    accept_terms_and_conditions: bool = typer.Option(
        False,
        "--accept-terms-and-conditions",
        help="By providing this flag you accept the terms and conditions outlined in the logs on server start."
    ),
    with_doc_processing: bool = typer.Option(
        False,
        '--with-doc-processing', '-d',
        help='Enable IBM Document Processing to extract information from your business documents. Enabling this activates the Watson Document Understanding service.'
    ),
    custom_compose_file: str = typer.Option(
        None,
        '--compose-file', '-f',
        help='Provide the path to a custom docker-compose file to use instead of the default compose file'
    ),  
    with_voice: bool = typer.Option(
        False,
        '--with-voice', '-v',
        help='Enable voice controller to interact with the chat via voice channels'
    ),
    experimental_with_langflow: bool = typer.Option(
        False,
        '--experimental-with-langflow',
        help='(Experimental) Enable Langflow UI, available at http://localhost:7861',
        hidden=True
    ),
):
    confirm_accepts_license_agreement(accept_terms_and_conditions)

    define_saas_wdu_runtime()
    
    ensure_docker_installed()

    if user_env_file and not Path(user_env_file).exists():
        logger.error(f"The specified environment file '{user_env_file}' does not exist.")
        sys.exit(1)

    if custom_compose_file:
        if Path(custom_compose_file).exists():
            logger.warning("You are using a custom docker compose file, official support will not be available for this configuration")
        else:
            logger.error(f"The specified docker-compose file '{custom_compose_file}' does not exist.")
            sys.exit(1)
    
    #Run regardless, to allow this to set compose as 'None' when not in use 
    set_compose_file_path_in_env(custom_compose_file)

    user_env = read_env_file(user_env_file) if user_env_file else {}
    persist_user_env(user_env, include_secrets=persist_env_secrets)
    
    merged_env_dict = prepare_server_env_vars(user_env)  

    if not _check_exclusive_observibility(experimental_with_langfuse, experimental_with_ibm_telemetry):
        logger.error("Please select either langfuse or ibm telemetry for observability not both")
        sys.exit(1)

    # Add LANGFUSE_ENABLED and DOCPROC_ENABLED into the merged_env_dict, for tempus to pick up.
    if experimental_with_langfuse:
        merged_env_dict['LANGFUSE_ENABLED'] = 'true'

    if with_doc_processing:
        merged_env_dict['DOCPROC_ENABLED'] = 'true'
        define_saas_wdu_runtime("local")

    if experimental_with_ibm_telemetry:
        merged_env_dict['USE_IBM_TELEMETRY'] = 'true'

    if experimental_with_langflow:
        merged_env_dict['LANGFLOW_ENABLED'] = 'true'
    

    try:
        dev_edition_source = get_dev_edition_source(merged_env_dict)
        docker_login_by_dev_edition_source(merged_env_dict, dev_edition_source)
    except ValueError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

    final_env_file = write_merged_env_file(merged_env_dict)

    run_compose_lite(final_env_file=final_env_file,
                     experimental_with_langfuse=experimental_with_langfuse,
                     experimental_with_ibm_telemetry=experimental_with_ibm_telemetry,
                     with_doc_processing=with_doc_processing,
                     with_voice=with_voice,
                     experimental_with_langflow=experimental_with_langflow)
    
    run_db_migration()

    logger.info("Waiting for orchestrate server to be fully initialized and ready...")

    health_check_timeout = int(merged_env_dict["HEALTH_TIMEOUT"]) if "HEALTH_TIMEOUT" in merged_env_dict else (7 * 60)
    is_successful_server_healthcheck = wait_for_wxo_server_health_check(timeout_seconds=health_check_timeout)
    if is_successful_server_healthcheck:
        logger.info("Orchestrate services initialized successfully")
    else:
        logger.error(
            "The server did not successfully start within the given timeout. This is either an indication that something "
            f"went wrong, or that the server simply did not start within {health_check_timeout} seconds. Please check the logs with "
            "`orchestrate server logs`, or consider increasing the timeout by adding `HEALTH_TIMEOUT=number-of-seconds` "
            "to your env file."
        )
        exit(1)

    try:
        refresh_local_credentials()
    except:
        logger.warning("Failed to refresh local credentials, please run `orchestrate env activate local`")

    logger.info(f"You can run `orchestrate env activate local` to set your environment or `orchestrate chat start` to start the UI service and begin chatting.")

    if experimental_with_langfuse:
        logger.info(f"You can access the observability platform Langfuse at http://localhost:3010, username: orchestrate@ibm.com, password: orchestrate")
    if with_doc_processing:
        logger.info(f"Document processing in Flows (Public Preview) has been enabled.")
    if experimental_with_langflow:
        logger.info("Langflow has been enabled, the Langflow UI is available at http://localhost:7861")

@server_app.command(name="stop")
def server_stop(
    user_env_file: str = typer.Option(
        None,
        "--env-file", '-e',
        help="Path to a .env file that overrides default.env. Then environment variables override both."
    )
):

    ensure_docker_installed()
    default_env_path = get_default_env_file()
    merged_env_dict = merge_env(
        default_env_path,
        Path(user_env_file) if user_env_file else None
    )
    merged_env_dict['WATSONX_SPACE_ID']='X'
    merged_env_dict['WATSONX_APIKEY']='X'
    apply_llm_api_key_defaults(merged_env_dict)
    final_env_file = write_merged_env_file(merged_env_dict)
    run_compose_lite_down(final_env_file=final_env_file)

@server_app.command(name="reset")
def server_reset(
    user_env_file: str = typer.Option(
        None,
        "--env-file", '-e',
        help="Path to a .env file that overrides default.env. Then environment variables override both."
    )
):
    
    ensure_docker_installed()
    default_env_path = get_default_env_file()
    merged_env_dict = merge_env(
        default_env_path,
        Path(user_env_file) if user_env_file else None
    )
    merged_env_dict['WATSONX_SPACE_ID']='X'
    merged_env_dict['WATSONX_APIKEY']='X'
    apply_llm_api_key_defaults(merged_env_dict)
    final_env_file = write_merged_env_file(merged_env_dict)
    run_compose_lite_down(final_env_file=final_env_file, is_reset=True)

@server_app.command(name="logs")
def server_logs(
    user_env_file: str = typer.Option(
        None,
        "--env-file", '-e',
        help="Path to a .env file that overrides default.env. Then environment variables override both."
    )
):
    ensure_docker_installed()
    default_env_path = get_default_env_file()
    merged_env_dict = merge_env(
        default_env_path,
        Path(user_env_file) if user_env_file else None
    )
    merged_env_dict['WATSONX_SPACE_ID']='X'
    merged_env_dict['WATSONX_APIKEY']='X'
    apply_llm_api_key_defaults(merged_env_dict)
    final_env_file = write_merged_env_file(merged_env_dict)
    run_compose_lite_logs(final_env_file=final_env_file)

def run_db_migration() -> None:
    compose_path = get_compose_file()
    compose_command = ensure_docker_compose_installed()
    default_env_path = get_default_env_file()
    merged_env_dict = merge_env(default_env_path, user_env_path=None)
    merged_env_dict['WATSONX_SPACE_ID']='X'
    merged_env_dict['WATSONX_APIKEY']='X'
    merged_env_dict['WXAI_API_KEY'] = ''
    merged_env_dict['ASSISTANT_EMBEDDINGS_API_KEY'] = ''
    merged_env_dict['ASSISTANT_LLM_SPACE_ID'] = ''
    merged_env_dict['ROUTING_LLM_SPACE_ID'] = ''
    merged_env_dict['USE_SAAS_ML_TOOLS_RUNTIME'] = ''
    merged_env_dict['BAM_API_KEY'] = ''
    merged_env_dict['ASSISTANT_EMBEDDINGS_SPACE_ID'] = ''
    merged_env_dict['ROUTING_LLM_API_KEY'] = ''
    merged_env_dict['ASSISTANT_LLM_API_KEY'] = ''
    final_env_file = write_merged_env_file(merged_env_dict)
    

    pg_user = merged_env_dict.get("POSTGRES_USER","postgres")

    migration_command = f'''
        APPLIED_MIGRATIONS_FILE="/var/lib/postgresql/applied_migrations/applied_migrations.txt"
        touch "$APPLIED_MIGRATIONS_FILE"

        for file in /docker-entrypoint-initdb.d/*.sql; do
            filename=$(basename "$file")

            if grep -Fxq "$filename" "$APPLIED_MIGRATIONS_FILE"; then
                echo "Skipping already applied migration: $filename"
            else
                echo "Applying migration: $filename"
                if psql -U {pg_user} -d postgres -q -f "$file" > /dev/null 2>&1; then
                    echo "$filename" >> "$APPLIED_MIGRATIONS_FILE"
                else
                    echo "Error applying $filename. Stopping migrations."
                    exit 1
                fi
            fi
        done
        '''

    command = compose_command + [
        "-f", str(compose_path),
        "--env-file", str(final_env_file),
        "exec",
        "wxo-server-db",
        "bash",
        "-c",
        migration_command
    ]

    logger.info("Running Database Migration...")
    result = subprocess.run(command, capture_output=False)

    if result.returncode == 0:
        logger.info("Migration ran successfully.")
    else:
        error_message = result.stderr.decode('utf-8') if result.stderr else "Error occurred."
        logger.error(
            f"Error running database migration):\n{error_message}"
        )
        sys.exit(1)

def create_langflow_db() -> None:
    compose_path = get_compose_file()
    compose_command = ensure_docker_compose_installed()
    default_env_path = get_default_env_file()
    merged_env_dict = merge_env(default_env_path, user_env_path=None)
    merged_env_dict['WATSONX_SPACE_ID']='X'
    merged_env_dict['WATSONX_APIKEY']='X'
    merged_env_dict['WXAI_API_KEY'] = ''
    merged_env_dict['ASSISTANT_EMBEDDINGS_API_KEY'] = ''
    merged_env_dict['ASSISTANT_LLM_SPACE_ID'] = ''
    merged_env_dict['ROUTING_LLM_SPACE_ID'] = ''
    merged_env_dict['USE_SAAS_ML_TOOLS_RUNTIME'] = ''
    merged_env_dict['BAM_API_KEY'] = ''
    merged_env_dict['ASSISTANT_EMBEDDINGS_SPACE_ID'] = ''
    merged_env_dict['ROUTING_LLM_API_KEY'] = ''
    merged_env_dict['ASSISTANT_LLM_API_KEY'] = ''
    final_env_file = write_merged_env_file(merged_env_dict)

    pg_timeout = merged_env_dict.get('POSTGRES_READY_TIMEOUT','10')

    pg_user = merged_env_dict.get("POSTGRES_USER","postgres")

    creation_command = f"""
    echo 'Waiting for pg to initialize...'

    timeout={pg_timeout}
    while [[ -z `pg_isready | grep 'accepting connections'` ]] && (( timeout > 0 )); do
      ((timeout-=1)) && sleep 1;
    done

    if psql -U {pg_user} -lqt | cut -d \\| -f 1 | grep -qw langflow; then
        echo 'Existing Langflow DB found'
    else
        echo 'Creating Langflow DB'
        createdb -U "{pg_user}" -O "{pg_user}" langflow;
        psql -U {pg_user} -q -d postgres -c "GRANT CONNECT ON DATABASE langflow TO {pg_user}";
    fi
    """
    command = compose_command + [
        "-f", str(compose_path),
        "--env-file", str(final_env_file),
        "exec",
        "wxo-server-db",
        "bash",
        "-c",
        creation_command
    ]

    logger.info("Preparing Langflow resources...")
    result = subprocess.run(command, capture_output=False)

    if result.returncode == 0:
        logger.info("Langflow resources sucessfully created")
    else:
        error_message = result.stderr.decode('utf-8') if result.stderr else "Error occurred."
        logger.error(
            f"Failed to create Langflow resources\n{error_message}"
        )
        sys.exit(1)

def bump_file_iteration(filename: str) -> str:
    regex = re.compile(f"^(?P<name>[^\\(\\s\\.\\)]+)(\\((?P<num>\\d+)\\))?(?P<type>\\.(?:{'|'.join(_EXPORT_FILE_TYPES)}))?$")
    _m = regex.match(filename)
    iter = int(_m['num']) + 1 if (_m and _m['num']) else 1
    return f"{_m['name']}({iter}){_m['type'] or ''}"

def get_next_free_file_iteration(filename: str) -> str:
    while Path(filename).exists():
        filename = bump_file_iteration(filename)
    return filename

@server_app.command(name="eject", help="output the docker-compose file and associated env file used to run the server")
def server_eject(
    user_env_file: str = typer.Option(
        None,
        "--env-file",
        "-e",
        help="Path to a .env file that overrides default.env. Then environment variables override both."
    )
):
    
    if not user_env_file:
        logger.error(f"To use 'server eject' you need to specify an env file with '--env-file' or '-e'")
        sys.exit(1)

    if not Path(user_env_file).exists():
        logger.error(f"The specified environment file '{user_env_file}' does not exist.")
        sys.exit(1)

    logger.warning("Changes to your docker compose file are not supported")
    
    compose_file_path = get_compose_file()

    compose_output_file = get_next_free_file_iteration('docker-compose.yml')
    logger.info(f"Exporting docker compose file to '{compose_output_file}'")

    shutil.copyfile(compose_file_path,compose_output_file)


    user_env = read_env_file(user_env_file)
    merged_env_dict = prepare_server_env_vars(user_env)
    
    env_output_file = get_next_free_file_iteration('server.env')
    logger.info(f"Exporting env file to '{env_output_file}'")

    write_merged_env_file(merged_env=merged_env_dict,target_path=env_output_file)

    logger.info(f"To make use of the exported configuration file run \"orchestrate server start -e {env_output_file} -f {compose_output_file}\"")

if __name__ == "__main__":
    server_app()
