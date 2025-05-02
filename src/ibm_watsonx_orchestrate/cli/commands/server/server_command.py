import importlib.resources as resources
import logging
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import jwt
import requests
import typer
from dotenv import dotenv_values

from ibm_watsonx_orchestrate.client.utils import instantiate_client, check_token_validity, is_local_dev
from ibm_watsonx_orchestrate.cli.commands.environment.environment_controller import _login
from ibm_watsonx_orchestrate.cli.config import LICENSE_HEADER, \
    ENV_ACCEPT_LICENSE
from ibm_watsonx_orchestrate.cli.config import PROTECTED_ENV_NAME, clear_protected_env_credentials_token, Config, \
    AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE, AUTH_MCSP_TOKEN_OPT, AUTH_SECTION_HEADER, USER_ENV_CACHE_HEADER
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient

logger = logging.getLogger(__name__)

server_app = typer.Typer(no_args_is_help=True)


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
    registry_url = env_dict["REGISTRY_URL"]
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
        if not wo_auth_type:
            raise ValueError("WO_AUTH_TYPE is required in the environment file if WO_DEVELOPER_EDITION_SOURCE is set to 'orchestrate'.")
        api_key, username = get_docker_cred_by_wo_auth_type(env_dict, wo_auth_type)
        docker_login(api_key, registry_url, username)

def get_compose_file() -> Path:
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

def get_default_registry_env_vars_by_dev_edition_source(env_dict: dict, source: str) -> dict[str,str]:
    component_registry_var_names = {key for key in env_dict if key.endswith("_REGISTRY")}

    result = {}
    if source == "internal":
        result["REGISTRY_URL"] = "us.icr.io"
        for name in component_registry_var_names:
            result[name] = "us.icr.io/watson-orchestrate-private"
    elif source == "myibm":
        result["REGISTRY_URL"] = "cp.icr.io"
        for name in component_registry_var_names:
            result[name] = "cp.icr.io/cp/wxo-lite"
    elif source == "orchestrate":
        raise NotImplementedError("The 'orchestrate' source is not implemented yet.")
        # TODO: confirm with Tej about the registry url for orchestrate source
    return result

def get_dev_edition_source(env_dict: dict) -> str:
    source = env_dict.get("WO_DEVELOPER_EDITION_SOURCE")

    if source:
        return source
    if env_dict.get("WO_INSTANCE"):
        return "orchestrate"
    return "myibm"

def get_docker_cred_by_wo_auth_type(env_dict: dict, auth_type: str) -> tuple[str, str]:
    if auth_type in {"mcsp", "ibm_iam"}:
        wo_api_key = env_dict.get("WO_API_KEY")
        if not wo_api_key:
            raise ValueError("WO_API_KEY is required in the environment file if the WO_AUTH_TYPE is set to 'mcsp' or 'ibm_iam'.")
        return wo_api_key, "wouser"
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
        raise ValueError(f"Unknown value for WO_AUTH_TYPE: {auth_type}. Must be one of ['mcsp', 'ibm_iam', 'cpd'].")

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

def write_merged_env_file(merged_env: dict) -> Path:
    tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env")
    with tmp:
        for key, val in merged_env.items():
            tmp.write(f"{key}={val}\n")
    return Path(tmp.name)


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

NON_SECRET_ENV_ITEMS = {
    "WO_DEVELOPER_EDITION_SOURCE",
    "WO_INSTANCE",
    "USE_SAAS_ML_TOOLS_RUNTIME",
    "WXO_MCSP_EXCHANGE_URL",
    "OPENSOURCE_REGISTRY_PROXY"
}
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

def run_compose_lite(final_env_file: Path, experimental_with_langfuse=False, with_flow_runtime=False) -> None:
    compose_path = get_compose_file()
    compose_command = ensure_docker_compose_installed()
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


    # Step 2: Start all remaining services (except DB)
    if experimental_with_langfuse:
        command = compose_command + [
            '--profile',
            'langfuse'
        ]
    else:
        command = compose_command

    # Check if we start the server with tempus-runtime.
    if with_flow_runtime:
        command += ['--profile', 'with-tempus-runtime']

    command += [
        "-f", str(compose_path),
        "--env-file", str(final_env_file),
        "up",
        "--scale",
        "ui=0",
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

def wait_for_wxo_server_health_check(health_user, health_pass, timeout_seconds=90, interval_seconds=2):
    url = "http://localhost:4321/api/v1/auth/token"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'username': health_user,
        'password': health_pass
    }

    start_time = time.time()
    errormsg = None
    while time.time() - start_time <= timeout_seconds:
        try:
            response = requests.post(url, headers=headers, data=data)
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
    ensure_docker_installed()

    default_env = read_env_file(get_default_env_file())
    user_env = read_env_file(user_env_file) if user_env_file else {}
    if not user_env:
        user_env = get_persisted_user_env()

    dev_edition_source = get_dev_edition_source(user_env)
    default_registry_vars = get_default_registry_env_vars_by_dev_edition_source(default_env, source=dev_edition_source)

    merged_env_dict = {
        **default_env,
        **default_registry_vars,
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

    #These are to removed warning and not used in UI component
    if not 'WATSONX_SPACE_ID' in merged_env_dict:
        merged_env_dict['WATSONX_SPACE_ID']='X'
    if not 'WATSONX_APIKEY' in merged_env_dict:
        merged_env_dict['WATSONX_APIKEY']='X'
    apply_llm_api_key_defaults(merged_env_dict)

    final_env_file = write_merged_env_file(merged_env_dict)

    logger.info("Waiting for orchestrate server to be fully started and ready...")

    health_check_timeout = int(merged_env_dict["HEALTH_TIMEOUT"]) if "HEALTH_TIMEOUT" in merged_env_dict else 120
    is_successful_server_healthcheck = wait_for_wxo_server_health_check(merged_env_dict['WXO_USER'], merged_env_dict['WXO_PASS'], timeout_seconds=health_check_timeout)
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

    command = compose_command + [
        "-f", str(compose_path),
        "--env-file", str(final_env_file),
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
        help=''
    ),
    with_flow_runtime: bool = typer.Option(
        False,
        '--with-tempus-runtime', '-f',
        help='Option to start server with tempus-runtime.',
        hidden=True
    )
    ,
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
):
    confirm_accepts_license_agreement(accept_terms_and_conditions)

    if user_env_file and not Path(user_env_file).exists():
        logger.error(f"Error: The specified environment file '{user_env_file}' does not exist.")
        sys.exit(1)
    ensure_docker_installed()

    default_env = read_env_file(get_default_env_file())
    user_env = read_env_file(user_env_file) if user_env_file else {}
    persist_user_env(user_env, include_secrets=persist_env_secrets)
    dev_edition_source = get_dev_edition_source(user_env)
    default_registry_vars = get_default_registry_env_vars_by_dev_edition_source(default_env, source=dev_edition_source)

    merged_env_dict = {
        **default_env,
        **default_registry_vars,
        **user_env,
    }

    merged_env_dict['DBTAG'] = get_dbtag_from_architecture(merged_env_dict=merged_env_dict)

    try:
        docker_login_by_dev_edition_source(merged_env_dict, dev_edition_source)
    except ValueError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

    apply_llm_api_key_defaults(merged_env_dict)


    final_env_file = write_merged_env_file(merged_env_dict)
    run_compose_lite(final_env_file=final_env_file, experimental_with_langfuse=experimental_with_langfuse, with_flow_runtime=with_flow_runtime)

    run_db_migration()

    logger.info("Waiting for orchestrate server to be fully initialized and ready...")

    health_check_timeout = int(merged_env_dict["HEALTH_TIMEOUT"]) if "HEALTH_TIMEOUT" in merged_env_dict else (7 * 60)
    is_successful_server_healthcheck = wait_for_wxo_server_health_check(merged_env_dict['WXO_USER'], merged_env_dict['WXO_PASS'], timeout_seconds=health_check_timeout)
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

    if with_flow_runtime:
        logger.info(f"Starting with flow runtime")

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

    command = compose_command + [
        "-f", str(compose_path),
        "exec",
        "wxo-server-db",
        "bash",
        "-c",
        '''
        APPLIED_MIGRATIONS_FILE="/var/lib/postgresql/applied_migrations/applied_migrations.txt"
        touch "$APPLIED_MIGRATIONS_FILE"

        for file in /docker-entrypoint-initdb.d/*.sql; do
            filename=$(basename "$file")

            if grep -Fxq "$filename" "$APPLIED_MIGRATIONS_FILE"; then
                echo "Skipping already applied migration: $filename"
            else
                echo "Applying migration: $filename"
                if psql -U postgres -d postgres -q -f "$file" > /dev/null 2>&1; then
                    echo "$filename" >> "$APPLIED_MIGRATIONS_FILE"
                else
                    echo "Error applying $filename. Stopping migrations."
                    exit 1
                fi
            fi
        done
        '''
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

if __name__ == "__main__":
    server_app()
