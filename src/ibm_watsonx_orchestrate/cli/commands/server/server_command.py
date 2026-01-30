import logging
import os
import platform
import re
import shutil
import sys
import time
from pathlib import Path
import subprocess
import re
import jwt
import requests
import typer
import shlex
from typing import Optional

from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.developer_edition.vm_host.vm_manager import get_vm_manager

from ibm_watsonx_orchestrate.cli.commands.environment.environment_controller import _login
from ibm_watsonx_orchestrate.cli.commands.server.images.images_command import images_app
from ibm_watsonx_orchestrate.cli.config import PROTECTED_ENV_NAME, clear_protected_env_credentials_token, Config, \
    AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE, AUTH_MCSP_TOKEN_OPT, AUTH_SECTION_HEADER, LICENSE_HEADER, \
    ENV_ACCEPT_LICENSE
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.docker_utils import DockerLoginService, DockerComposeCore, DockerUtils
from ibm_watsonx_orchestrate.utils.environment import EnvService
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.utils.migration_manager import MigrationsManager
from ibm_watsonx_orchestrate.utils.utils import parse_string_safe


from ibm_watsonx_orchestrate.developer_edition.vm_host.lima import LimaLifecycleManager
from ibm_watsonx_orchestrate.client.utils import get_os_type, path_for_vm
import base64
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from ibm_watsonx_orchestrate.cli.config import (Config, PREVIOUS_DOCKER_CONTEXT, DOCKER_CONTEXT)

logger = logging.getLogger(__name__)

server_app = typer.Typer(no_args_is_help=True)
server_app.add_typer(images_app, name="images", help="Manage docker images pulled by app.")

_EXPORT_FILE_TYPES: set[str] = {
    'py',
    'yaml',
    'yml',
    'json',
    'env'
}

def refresh_local_credentials() -> None:
    """
    Refresh the local credentials
    """
    try:
        clear_protected_env_credentials_token()
        _login(name=PROTECTED_ENV_NAME, apikey=None)

    except:
        logger.warning("Failed to refresh local credentials, please run `orchestrate env activate local`")

def cleanup_orchestrate_cache():
        """
        Removes all temporary rendered image files under ~/.cache/orchestrate
        while preserving essential files like docker-compose.yml and credentials.yaml.
        """
        orchestrate_cache = Path.home() / ".cache" / "orchestrate"

        removed_files = []
        preserved_files = {"docker-compose.yml", "credentials.yaml", "layers"}

        for item in orchestrate_cache.iterdir():
            # Skip preserved items
            if item.name in preserved_files:
                continue

            if item.name.startswith("rendered-image-") or item.name.startswith("tmp"):
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    removed_files.append(item.name)
                except Exception as e:
                    print(f"[WARN] Could not remove {item}: {e}")


def run_compose_lite(
        final_env_file: Path,
        env_service: EnvService,
        experimental_with_langfuse=False,
        experimental_with_ibm_telemetry=False,
        with_doc_processing=False,
        with_voice=False,
        with_connections_ui=False,
        with_langflow=False,
        with_ai_builder=False,
    ) -> None:
    env_service.prepare_clean_env(final_env_file)
    db_tag = env_service.read_env_file(final_env_file).get('DBTAG', None)
    logger.info(f"Detected architecture: {platform.machine()}, using DBTAG: {db_tag}")

    compose_core = DockerComposeCore(env_service=env_service)

    # Step 1: Start only the DB container
    result = compose_core.service_up(service_name="wxo-server-db", friendly_name="WxO Server DB", final_env_file=final_env_file, compose_env=os.environ)

    if result.returncode != 0:
        logger.error(f"Error starting DB container: {result.stderr}")
        sys.exit(1)

    logger.info("Database container started successfully. Now starting other services...")


    # Step 2: Create Langflow DB (if enabled)
    if with_langflow:
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
    if with_connections_ui:
        profiles.append("connections-ui")
    if with_langflow:
        profiles.append("langflow")
    if with_ai_builder:
        profiles.append("agent-builder")

    result = compose_core.services_up(profiles, final_env_file, ["--scale", "ui=0"])

    if result.returncode == 0:
        logger.info("Services started successfully.")
        # Remove the temp file if successful
        if final_env_file.exists():
            final_env_file.unlink()
    else:
        stderr_decoded= result.stderr.decode('utf-8') if isinstance(result.stderr, bytes) else result.stderr
        error_message = stderr_decoded if stderr_decoded else "Error occurred."
        logger.error(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n{error_message}"
        )
        sys.exit(1)

def stop_virtual_machine(keep_vm: bool = False):
    if keep_vm:
        return
    
    vm = get_vm_manager()
    vm.stop_server()

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
        except requests.RequestException as e:
            pass

        time.sleep(interval_seconds)
    logger.info("UI component is initialized")
    return False

def run_compose_lite_ui(user_env_file: Path) -> bool:
    DockerUtils.ensure_docker_installed()

    cli_config = Config()
    env_service = EnvService(cli_config)
    env_service.prepare_clean_env(user_env_file)
    user_env = env_service.get_user_env(user_env_file)
    merged_env_dict = env_service.prepare_server_env_vars_minimal(user_env=user_env)

    _login(name=PROTECTED_ENV_NAME)
    auth_cfg = Config(AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE)
    existing_auth_config = auth_cfg.get(AUTH_SECTION_HEADER).get(PROTECTED_ENV_NAME, {})
    existing_token = existing_auth_config.get(AUTH_MCSP_TOKEN_OPT) if existing_auth_config else None
    token = jwt.decode(existing_token, options={"verify_signature": False})
    tenant_id = token.get('woTenantId', None)
    merged_env_dict['REACT_APP_TENANT_ID'] = tenant_id
    merged_env_dict['VOICE_ENABLED'] = DockerUtils.is_docker_container_running("dev-edition-wxo-server-voice-1")

    agent_client = instantiate_client(AgentClient)
    agents = agent_client.get()
    if not agents:
        logger.error("No agents found for the current environment. Please create an agent before starting the chat.")
        sys.exit(1)

    try:
        DockerLoginService(env_service=env_service).login_by_dev_edition_source(merged_env_dict)
    except ValueError as ignored:
        # do nothing, as the docker login here is not mandatory
        pass

    # Auto-configure callback IP for async tools
    merged_env_dict = env_service.auto_configure_callback_ip(merged_env_dict)

    #These are to removed warning and not used in UI component
    if not 'WATSONX_SPACE_ID' in merged_env_dict:
        merged_env_dict['WATSONX_SPACE_ID']='X'
    if not 'WATSONX_APIKEY' in merged_env_dict:
        merged_env_dict['WATSONX_APIKEY']='X'
    env_service.apply_llm_api_key_defaults(merged_env_dict)

    final_env_file = env_service.write_merged_env_file(merged_env_dict)

    # Make env file vm-visible and reuse existing env file if present
    vm_env_dir = Path.home() / ".cache/orchestrate"
    vm_env_dir.mkdir(parents=True, exist_ok=True)
    vm_env_file = vm_env_dir / final_env_file.name
    shutil.copy(final_env_file, vm_env_file)

    logger.info("Waiting for orchestrate server to be fully started and ready...")

    health_check_timeout = int(merged_env_dict["HEALTH_TIMEOUT"]) if "HEALTH_TIMEOUT" in merged_env_dict else 120
    is_successful_server_healthcheck = wait_for_wxo_server_health_check(merged_env_dict['WXO_USER'], merged_env_dict['WXO_PASS'], timeout_seconds=health_check_timeout)
    if not is_successful_server_healthcheck:
        logger.error("Healthcheck failed orchestrate server.  Make sure you start the server components with `orchestrate server start` before trying to start the chat UI")
        return False

    compose_core = DockerComposeCore(env_service=env_service)

    result = compose_core.service_up(service_name="ui", friendly_name="UI", final_env_file=vm_env_file)

    if result.returncode == 0:
        logger.info("Chat UI Service started successfully.")
        for f in [final_env_file, vm_env_file]:
            try:
                if f.exists():
                    f.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove temp file {f}: {e}")
    else:
        stderr_decoded = result.stderr.decode('utf-8') if isinstance(result.stderr, bytes) else result.stderr
        error_message = stderr_decoded if stderr_decoded else "Error occurred."
        logger.error(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n{error_message}"
        )
        return False
    
    is_successful_ui_healthcheck = wait_for_wxo_ui_health_check()
    if not is_successful_ui_healthcheck:
        logger.error("The Chat UI service did not initialize within the expected time.  Check the logs for any errors.")

    return True

def run_compose_lite_down_ui(user_env_file: Path, is_reset: bool = False) -> None:
    EnvService.prepare_clean_env(user_env_file)
    DockerUtils.ensure_docker_installed()
    default_env_path = EnvService.get_default_env_file()
    merged_env_dict = EnvService.merge_env(
        default_env_path,
        user_env_file
    )
    merged_env_dict['WATSONX_SPACE_ID']='X'
    merged_env_dict['WATSONX_APIKEY']='X'
    EnvService.apply_llm_api_key_defaults(merged_env_dict)
    final_env_file = EnvService.write_merged_env_file(merged_env_dict)

    # Make env file vm-visible and reuse existing env file if present
    vm_env_dir = Path.home() / ".cache/orchestrate"
    vm_env_dir.mkdir(parents=True, exist_ok=True)
    vm_env_file = vm_env_dir / final_env_file.name
    shutil.copy(final_env_file, vm_env_file)


    cli_config = Config()
    env_service = EnvService(cli_config)
    compose_core = DockerComposeCore(env_service=env_service)

    result = compose_core.service_down(service_name="ui", friendly_name="UI", final_env_file=vm_env_file, is_reset=is_reset)

    if result.returncode == 0:
        logger.info("UI service stopped successfully.")
        # Remove the temp file if successful
        if final_env_file.exists():
            final_env_file.unlink()
        if vm_env_file.exists():
            vm_env_file.unlink()
    else:
        stderr_decoded = result.stderr.decode('utf-8') if isinstance(result.stderr, bytes) else result.stderr
        error_message = stderr_decoded if stderr_decoded else "Error occurred."
        logger.error(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n{error_message}"
        )
        sys.exit(1)

def run_compose_lite_down(final_env_file: Path, is_reset: bool = False) -> None:
    """
    Stops all services via docker compose inside the Lima VM.
    If is_reset=True, also removes named volumes (resetting DB and state).
    """
    orchestrate_path = Path.home() / ".cache/orchestrate"
    orchestrate_path.mkdir(parents=True, exist_ok=True)

    # # Copy the env file into Lima-visible orchestrate dir
    lima_env_file = orchestrate_path / final_env_file.name
    shutil.copy(final_env_file, lima_env_file)

    EnvService.prepare_clean_env(lima_env_file)

    cli_config = Config()
    env_service = EnvService(cli_config)
    compose_core = DockerComposeCore(env_service=env_service)

    result = compose_core.services_down(final_env_file=lima_env_file, is_reset=is_reset)

    if result.returncode == 0:
        if is_reset:
            logger.info("Services and volumes reset successfully.")
        else:
            logger.info("Services stopped successfully.")

        # Cleanup temp env files
        if final_env_file.exists():
            final_env_file.unlink()
        if lima_env_file.exists():
            lima_env_file.unlink()
    else:
        stderr_decoded = result.stderr.decode('utf-8') if isinstance(result.stderr, bytes) else result.stderr
        error_message = stderr_decoded if stderr_decoded else "Error occurred."
        logger.error(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n{error_message}"
        )
        sys.exit(1)

def run_compose_lite_logs(final_env_file: Path) -> None:
    """
    Tail docker compose logs for orchestrate services (inside Lima, WSL, or native Docker).
    """
    orchestrate_path = Path.home() / ".cache/orchestrate"
    orchestrate_path.mkdir(parents=True, exist_ok=True)

    # Copy the env file into orchestrate dir (VM-visible if needed)
    vm_env_file = orchestrate_path / final_env_file.name
    shutil.copy(final_env_file, vm_env_file)

    compose_path = EnvService(Config()).get_compose_file()
    vm_resolved_compose = path_for_vm(compose_path)
    vm_resolved_file = path_for_vm(vm_env_file)

    command = [
        "compose",
        "-f", str(vm_resolved_compose),
        "--env-file", str(vm_resolved_file),
        "logs",
        "-f",
    ]

    vm = get_vm_manager()

    try:
        logger.info(f"Tailing docker-compose logs inside {vm.__class__.__name__}...")
        result = vm.run_docker_command(command, capture_output=False)
    except KeyboardInterrupt:
        result = subprocess.CompletedProcess(args=command, returncode=130)
    except subprocess.CalledProcessError as e:
        if e.returncode == 130:
            result = subprocess.CompletedProcess(args=e.cmd, returncode=130)
        else:
            logger.error(f"Docker compose logs failed: {e}")
    finally:
        # Always clean up
        if final_env_file.exists():
            final_env_file.unlink()
        if vm_env_file.exists():
            vm_env_file.unlink()

    # If user exited normally or with Ctrl+C, don't print any errors
    if result.returncode in (0, 130):
        logger.info("End of docker logs")
        return True

    # Any other error → print
    error_message = getattr(result, "stderr", None) or "Error occurred."
    logger.error(
        f"Error running docker-compose logs (temporary env file left at {vm_env_file}):\n{error_message}"
    )
    sys.exit(1)

def confirm_accepts_license_agreement(accepts_by_argument: bool, cfg: Config):
    accepts_license = cfg.read(LICENSE_HEADER, ENV_ACCEPT_LICENSE)
    if accepts_license != True:
        logger.warning(('''
            By running the following command your machine will install IBM watsonx Orchestrate Developer Edition, which is governed by the following IBM license agreement:
            - * https://www.ibm.com/support/customer/csol/terms/?id=L-GLQU-5KA4PY&lc=en
            Additionally, the following prerequisite open source programs will be obtained from Docker Hub and will be installed on your machine. Each of the below programs are Separately Licensed Code, and are governed by the separate license agreements identified below, and not by the IBM license agreement:
            * redis (7.2)               - https://github.com/redis/redis/blob/7.2.7/COPYING
            * minio                     - https://github.com/minio/minio/blob/master/LICENSE
            * milvus-io                 - https://github.com/milvus-io/milvus/blob/master/LICENSE
            * etcd                      - https://github.com/etcd-io/etcd/blob/main/LICENSE
            * clickhouse-server         - https://github.com/ClickHouse/ClickHouse/blob/master/LICENSE
            * langfuse                  - https://github.com/langfuse/langfuse/blob/main/LICENSE
            * langflow                  - https://github.com/langflow-ai/langflow/blob/main/LICENSE
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


def copy_files_to_cache(user_env_file: Path, env_service: EnvService) -> Path:
    """
    Prepare the compose + env files in a cache directory (~/.cache/orchestrate)
    and return the VM-visible Path to the .env file.
    Works for both macOS (Lima) and Windows (WSL).
    """

    staging_dir = Path.home() / ".cache" / "orchestrate"
    staging_dir.mkdir(parents=True, exist_ok=True)

    # Copy compose file
    compose_src = env_service.get_compose_file(ignore_cache=True)
    shutil.copy(compose_src, staging_dir / "docker-compose.yml")

    # Merge default + user env
    default_env = EnvService.get_default_env_file()
    merged_env = EnvService.merge_env(default_env, user_env_file)

    # Write merged env to a stable name
    merged_env_path = staging_dir / "merged.env"
    EnvService.write_merged_env_file(merged_env, target_path=merged_env_path)

    # Return the correct path for the VM to access
    system = platform.system().lower()

    if system == "windows":
        # When running in WSL, /home/orchestrate maps directly inside the WSL VM
        # vm_env_path = Path("/home/orchestrate/.cache/orchestrate/merged.env")
        vm_env_path = Path(path_for_vm(merged_env_path))
    else:
         vm_env_path = merged_env_path

    return vm_env_path

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
    with_connections_ui: bool = typer.Option(
        False,
        '--with-connections-ui', '-c',
        help='Enables connections ui to facilitate OAuth connections and credential management via a UI'),
    with_langflow: bool = typer.Option(
        False,
        '--with-langflow',
        help='Enable Langflow UI, available at http://localhost:7861'
    ),
    with_ai_builder: bool = typer.Option(
        False,
        '--with-ai-builder',
        help='Enable AI Builder features that allow for AI assisted agent creation and refinement'
    ),
):
    cli_config = Config()
    confirm_accepts_license_agreement(accept_terms_and_conditions, cli_config)

    if user_env_file and not Path(user_env_file).exists():
        logger.error(f"The specified environment file '{user_env_file}' does not exist.")
        sys.exit(1)

    if custom_compose_file:
        if Path(custom_compose_file).exists():
            logger.warning("You are using a custom docker compose file, official support will not be available for this configuration")
        else:
            logger.error(f"The specified docker-compose file '{custom_compose_file}' does not exist.")
            sys.exit(1)

    env_service = EnvService(cli_config)

    env_service.define_saas_wdu_runtime() # Set WDU_RUNTIME_SOURCE=none initially
    
    #Run regardless, to allow this to set compose as 'None' when not in use 
    env_service.set_compose_file_path_in_env(custom_compose_file)

    user_env = env_service.get_user_env(user_env_file=user_env_file, fallback_to_persisted_env=False)
    developer_edition_source = env_service.get_dev_edition_source_core(user_env)
    env_service.persist_user_env(user_env, include_secrets=persist_env_secrets, source=developer_edition_source)
    
    merged_env_dict = env_service.prepare_server_env_vars(user_env=user_env, should_drop_auth_routes=False)

    if not DockerUtils.check_exclusive_observability(experimental_with_langfuse, experimental_with_ibm_telemetry):
        logger.error("Please select either langfuse or ibm telemetry for observability not both")
        sys.exit(1)

    # Add LANGFUSE_ENABLED and DOCPROC_ENABLED into the merged_env_dict, for tempus to pick up.
    if experimental_with_langfuse:
        merged_env_dict['LANGFUSE_ENABLED'] = 'true'

    if with_doc_processing:
        merged_env_dict['DOCPROC_ENABLED'] = 'true'
        merged_env_dict["WDU_RUNTIME_SOURCE"] = "local" # Set WDU_RUNTIME_SOURCE=local to use local WDU service
    elif merged_env_dict.get("WO_INSTANCE") and merged_env_dict.get("WO_API_KEY"):
        merged_env_dict["WDU_RUNTIME_SOURCE"] = "remote" # Set WDU_RUNTIME_SOURCE=remote to use WDU proxy
    else:
        logger.warning("IBM Document Processing is not enabled. The following two features will be disabled: \n1. Agent Knowledge - Upload files \n2. Agent Workflow - Document Processing. \nTo enable these features, please use '--with-doc-processing' argument or provide WO_INSTANCE and WO_API_KEY in your env file to start the server.")

    if experimental_with_ibm_telemetry:
        merged_env_dict['USE_IBM_TELEMETRY'] = 'true'
        merged_env_dict['FLOW_TRACING_OTLP_ENDPOINT'] = merged_env_dict.get('FLOW_TRACING_OTLP_ENDPOINT') or 'http://jaeger:4318/v1/traces'
    else:
        merged_env_dict['FLOW_TRACING_OTLP_ENDPOINT'] = ''

    if with_langflow:
        merged_env_dict['LANGFLOW_ENABLED'] = 'true'

    if with_voice:
        merged_env_dict['VOICE_ENABLED'] = 'true'
    
    if with_ai_builder:
        merged_env_dict['AI_BUILDER_ENABLED'] = 'true'

    final_env_file = env_service.write_merged_env_file(merged_env_dict)

    vm_env_file_path = copy_files_to_cache(final_env_file, env_service)

    vm = get_vm_manager()
    
    if with_doc_processing:
        try:
            vm.check_and_ensure_memory_for_doc_processing(min_memory_gb=24)
        except Exception as e:
            logger.warning(f"Could not verify memory requirements: {e}")
            logger.warning("Continuing with server start...")

    vm.start_server()

    logger.info("Running docker compose-up...")
    
    
    try:
        DockerLoginService(env_service=env_service).login_by_dev_edition_source(merged_env_dict)
    except ValueError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


    run_compose_lite(final_env_file=vm_env_file_path,
                     experimental_with_langfuse=experimental_with_langfuse,
                     experimental_with_ibm_telemetry=experimental_with_ibm_telemetry,
                     with_doc_processing=with_doc_processing,
                     with_voice=with_voice,
                     with_connections_ui=with_connections_ui,
                     with_langflow=with_langflow,
                     with_ai_builder=with_ai_builder,
                     env_service=env_service)
    
    run_db_migration(with_ai_builder)

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

    refresh_local_credentials()

    logger.info(f"You can run `orchestrate env activate local` to set your environment or `orchestrate chat start` to start the UI service and begin chatting.")

    # clean up potential cpd files in cache
    cleanup_orchestrate_cache()

    if experimental_with_langfuse:
        # Local Development Service Credentials
        #------------------------------------------------
        # These credentials are for local development only.
        # They are default values and can be overridden by the user.
        # These do NOT provide access to any production or sensitive system
        # ------------------------------------------------
        logger.info(f"You can access the observability platform Langfuse at http://localhost:3010, username: orchestrate@ibm.com, password: orchestrate")
    if with_doc_processing:
        logger.info(f"Document processing in Flows (Public Preview) has been enabled.")
        

    if with_connections_ui:
        logger.info("Connections UI can be found at http://localhost:3412/connectors")
    if with_langflow:
        logger.info("Langflow has been enabled, the Langflow UI is available at http://localhost:7861")
    if with_ai_builder:
        logger.info("AI Builder feature has been enabled. You can now use AI assisted agent authoring features")

@server_app.command(name="stop")
def server_stop(
    user_env_file: str = typer.Option(
        None,
        "--env-file", '-e',
        help="Path to a .env file that overrides default.env. Then environment variables override both."
    ),
    keep_vm: bool = typer.Option(
        False,
        "--keep-vm",
        help="Don't stop the VM running the Developer Editon server."
    )
):
    vm = get_vm_manager()
    if not vm.is_server_running():
        logger.info("Server already stopped")
        return

    DockerUtils.ensure_docker_installed()
    default_env_path = EnvService.get_default_env_file()
    merged_env_dict = EnvService.merge_env(
        default_env_path,
        Path(user_env_file) if user_env_file else None
    )
    merged_env_dict['WATSONX_SPACE_ID']='X'
    merged_env_dict['WATSONX_APIKEY']='X'
    EnvService.apply_llm_api_key_defaults(merged_env_dict)
    final_env_file = EnvService.write_merged_env_file(merged_env_dict)
    run_compose_lite_down(final_env_file=final_env_file)
    stop_virtual_machine(keep_vm=keep_vm)

@server_app.command(name="reset")
def server_reset(
        user_env_file: str = typer.Option(
            None,
            "--env-file", '-e',
            help="Path to a .env file that overrides default.env. Then environment variables override both."
        ),
        keep_vm: bool = typer.Option(
            False,
            "--keep-vm",
            help="Don't stop the VM running the Developer Editon server."
        )
):
    vm = get_vm_manager()
    vm.start_server()

    DockerUtils.ensure_docker_installed()

    user_env_file = parse_string_safe(value=user_env_file, override_empty_to_none=True)
    if user_env_file is not None:
        user_env_file = Path(user_env_file)

        if not user_env_file.exists() or not user_env_file.is_file():
            logger.error(f"Provided .env file does not exist or cannot be accessed: {user_env_file}")
            sys.exit(1)

    cli_config = Config()
    env_service = EnvService(cli_config)

    if user_env_file is not None:
        user_env = env_service.get_user_env(user_env_file=user_env_file, fallback_to_persisted_env=False)
        merged_env_dict = env_service.prepare_server_env_vars(user_env=user_env, should_drop_auth_routes=False)

    else:
        default_env_path = EnvService.get_default_env_file()
        merged_env_dict = EnvService.merge_env(default_env_path, None)

    merged_env_dict['WATSONX_SPACE_ID']='X'
    merged_env_dict['WATSONX_APIKEY']='X'

    env_service.apply_llm_api_key_defaults(merged_env_dict)
    final_env_file = EnvService.write_merged_env_file(merged_env_dict)

    run_compose_lite_down(final_env_file=final_env_file, is_reset=True)
    stop_virtual_machine(keep_vm=keep_vm)

def run_db_migration(with_ai_builder: bool = False) -> None:
    default_env_path = EnvService.get_default_env_file()
    merged_env_dict = EnvService.merge_env(default_env_path, user_env_path=None)

    # Set required env keys
    merged_env_dict.update({
        'WATSONX_SPACE_ID': 'X',
        'WATSONX_APIKEY': 'X',
        'WXAI_API_KEY': '',
        'ASSISTANT_EMBEDDINGS_API_KEY': '',
        'ASSISTANT_LLM_SPACE_ID': '',
        'ROUTING_LLM_SPACE_ID': '',
        'USE_SAAS_ML_TOOLS_RUNTIME': '',
        'BAM_API_KEY': '',
        'ASSISTANT_EMBEDDINGS_SPACE_ID': '',
        'ROUTING_LLM_API_KEY': '',
        'ASSISTANT_LLM_API_KEY': '',
    })

    final_env_file = EnvService.write_merged_env_file(merged_env_dict)

    pg_user = merged_env_dict.get("POSTGRES_USER", "postgres")
    pg_timeout = merged_env_dict.get("POSTGRES_READY_TIMEOUT", 10)

    migration_manager = MigrationsManager(
        env_path=final_env_file,
        context={
            'PG_USER': pg_user,
            'PG_TIMEOUT': pg_timeout
        }
    )
    logger.info(f"Running DB migrations inside {migration_manager.vm_manager.__class__.__name__}...")

    system = get_os_type() # I noticed WSL having issues after Orchestrate server reset so addin this sleep here.
    if system == "windows":
        time.sleep(60)

    migration_manager.run_orchestrate_migrations()
    migration_manager.run_observability_migrations()
    migration_manager.run_mcp_gateway_migrations()

    if with_ai_builder:
        migration_manager.run_architect_migrations()



def create_langflow_db() -> None:
    default_env_path = EnvService.get_default_env_file()
    merged_env_dict = EnvService.merge_env(default_env_path, user_env_path=None)
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
    
    final_env_file = EnvService.write_merged_env_file(merged_env_dict)

    pg_timeout = merged_env_dict.get('POSTGRES_READY_TIMEOUT','10')
    pg_user = merged_env_dict.get("POSTGRES_USER","postgres")

    migration_manager = MigrationsManager(
        env_path=final_env_file,
        context={
            'PG_USER': pg_user,
            'PG_TIMEOUT': pg_timeout
        }
    )

    migration_manager.run_langflow_migrations()


    

def bump_file_iteration(filename: str) -> str:
    regex = re.compile(f"^(?P<name>[^\\(\\s\\.\\)]+)(\\((?P<num>\\d+)\\))?(?P<type>\\.(?:{'|'.join(_EXPORT_FILE_TYPES)}))?$")
    _m = regex.match(filename)
    iter = int(_m['num']) + 1 if (_m and _m['num']) else 1
    return f"{_m['name']}({iter}){_m['type'] or ''}"

def get_next_free_file_iteration(filename: str) -> str:
    while Path(filename).exists():
        filename = bump_file_iteration(filename)
    return filename

@server_app.command(name="eject", help="Output the docker-compose file and associated env file used to run the server")
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

    cli_config = Config()
    env_service = EnvService(cli_config)
    compose_file_path = env_service.get_compose_file()
    compose_output_file = get_next_free_file_iteration('docker-compose.yml')
    logger.info(f"Exporting docker compose file to '{compose_output_file}'")

    shutil.copyfile(compose_file_path,compose_output_file)

    user_env = env_service.get_user_env(user_env_file=user_env_file, fallback_to_persisted_env=False)
    merged_env_dict = env_service.prepare_server_env_vars(user_env=user_env, should_drop_auth_routes=False)
    
    env_output_file = get_next_free_file_iteration('server.env')
    logger.info(f"Exporting env file to '{env_output_file}'")

    env_service.write_merged_env_file(merged_env=merged_env_dict,target_path=env_output_file)

    logger.info(f"To make use of the exported configuration file run \"orchestrate server start -e {env_output_file} -f {compose_output_file}\"")


# orchestrate server purge - will delete the users underlying lima or wsl vm
@server_app.command(name="purge", help="Delete the underlying VM and all its data")
def server_purge():
    vm = get_vm_manager(ensure_installed=False)
    console = Console()
    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
            ) as progress:
                task = progress.add_task(description="Deleting the underlying VM and all its data", total=None)
                try:
                    success =  vm.delete_server()
                    if success:
                        progress.stop()
                        logger.info("VM and associated directories deleted successfully.")
                    else:
                        progress.stop()
                        logger.error("Failed to Delete VM.")
                        sys.exit(1)
                except Exception as e:
                    progress.stop()
                    raise BadRequest(str(e))


# orchestrate server edit - will allow the user to update their underlying vm cpu and memory settings
@server_app.command(name="edit", help="Edit the underlying VM CPU, memory, or disk settings")
def server_edit(
    cpus: Optional[int] = typer.Option(None, help="Number of CPU cores", min=1),
    memory: Optional[int] = typer.Option(None, help="Memory in GB", min=1),
    disk: Optional[int] = typer.Option(None, help="Disk space in GB", min=1)
):
    
    if cpus is None and memory is None and disk is None:
        logger.error("Please provide at least one option: --cpus, --memory, or --disk.")
        sys.exit(1)

    system = get_os_type()  
    if system == "windows":
        if disk: 
            logger.warning("Disk resizing is not supported automatically for WSL. Please resize manually if needed.")
    
    # Using Progress Spinner for OSX/Linux but using logger.info for wsl as it takes much longer and gives user better info.
    if system == "windows":
        vm = get_vm_manager()
        success =  vm.edit_server(cpus, memory, disk)
        if success:
            logger.info("VM updated successfully.")
        else:
            logger.error("Failed to Update VM.")
            sys.exit(1)
    else:
        vm = get_vm_manager()
        console = Console()
        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            progress.add_task(description="Editing the underlying VM settings...", total=None)
            try:
                success = vm.edit_server(cpus, memory, disk)
                if success:
                    progress.stop()
                    logger.info("VM updated successfully.")
                else:
                    progress.stop()
                    logger.error("Failed to Update VM.")
                    sys.exit(1)
            except Exception as e:
                progress.stop()
                raise BadRequest(str(e))


# orchestrate server attach-docker - switch the docker context to the ibm-watsonx-orchestrate context
@server_app.command(name="attach-docker", help="Attach Docker to the Orchestrate VM context")
def server_attach_docker():

    vm = get_vm_manager()
    success = vm.attach_docker_context()
    if success:
        logger.info("Docker context successfully switched to ibm-watsonx-orchestrate.")
    else:
        logger.error("Failed to switch Docker context.")
        sys.exit(1)

# orchestrate server release-docker - switch the docker context back to default
@server_app.command(name="release-docker", help="Switch the docker context back to default")
def server_release_docker():
    cfg = Config()
    previous_context = cfg.read(DOCKER_CONTEXT, PREVIOUS_DOCKER_CONTEXT, ) or "default"

    vm = get_vm_manager()
    success = vm.release_docker_context()
    if success:
        logger.info(f"Docker context successfully switched to {previous_context}.")
    else:
        logger.error("Failed to switch Docker context.")
        sys.exit(1)

# orchestrate server logs <container> - get the logs of a given container pod
@server_app.command(name="logs", help="Get the logs for all containers or a specific container")
def server_logs(
    container_id: Optional[str] = typer.Option(
        None, 
        "--id", 
        "-i", 
        help="Container ID of the container whose logs you want to view."
    ),
    container_name: Optional[str] = typer.Option(
        None, 
        "--name", 
        "-n", 
        help="Container Name of the container whose logs you want to view."
    ),
    user_env_file: str = typer.Option(
        None,
        "--env-file", '-e',
        help="Path to a .env file that overrides default.env. Then environment variables override both."
    )  
):
    if not container_id and not container_name:
        DockerUtils.ensure_docker_installed()
        default_env_path = EnvService.get_default_env_file()
        merged_env_dict = EnvService.merge_env(
            default_env_path,
            Path(user_env_file) if user_env_file else None
        )
        merged_env_dict['WATSONX_SPACE_ID']='X'
        merged_env_dict['WATSONX_APIKEY']='X'
        EnvService.apply_llm_api_key_defaults(merged_env_dict)
        final_env_file = EnvService.write_merged_env_file(merged_env_dict)
        run_compose_lite_logs(final_env_file=final_env_file)
    
    else:
        vm = get_vm_manager()
        vm.get_container_logs(container_id, container_name)


# orchestrate server ssh - ssh into the underlying vm
@server_app.command(name="ssh", help="SSH into the underlying VM")
def ssh():
    vm = get_vm_manager()
    vm.ssh()


if __name__ == "__main__":
    server_app()
