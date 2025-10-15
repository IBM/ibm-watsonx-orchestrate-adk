import logging
import os
import platform
import re
import shutil
import sys
import time
from pathlib import Path

import jwt
import requests
import typer

from ibm_watsonx_orchestrate.cli.commands.environment.environment_controller import _login
from ibm_watsonx_orchestrate.cli.commands.server.images.images_command import images_app
from ibm_watsonx_orchestrate.cli.config import PROTECTED_ENV_NAME, clear_protected_env_credentials_token, Config, \
    AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE, AUTH_MCSP_TOKEN_OPT, AUTH_SECTION_HEADER, LICENSE_HEADER, \
    ENV_ACCEPT_LICENSE
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.docker_utils import DockerLoginService, DockerComposeCore, DockerUtils
from ibm_watsonx_orchestrate.utils.environment import EnvService
from ibm_watsonx_orchestrate.utils.utils import parse_string_safe


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

def run_compose_lite(
        final_env_file: Path,
        env_service: EnvService,
        experimental_with_langfuse=False, 
        experimental_with_ibm_telemetry=False, 
        with_doc_processing=False,
        with_voice=False,
        with_connections_ui=False,
        with_langflow=False,
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

    result = compose_core.services_up(profiles, final_env_file, ["--scale", "ui=0", "--scale", "cpe=0"])

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
    merged_env_dict['VOICE_ENABLED'] = DockerUtils.is_docker_container_running("docker-wxo-server-voice-1")

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

    logger.info("Waiting for orchestrate server to be fully started and ready...")

    health_check_timeout = int(merged_env_dict["HEALTH_TIMEOUT"]) if "HEALTH_TIMEOUT" in merged_env_dict else 120
    is_successful_server_healthcheck = wait_for_wxo_server_health_check(merged_env_dict['WXO_USER'], merged_env_dict['WXO_PASS'], timeout_seconds=health_check_timeout)
    if not is_successful_server_healthcheck:
        logger.error("Healthcheck failed orchestrate server.  Make sure you start the server components with `orchestrate server start` before trying to start the chat UI")
        return False

    compose_core = DockerComposeCore(env_service=env_service)

    result = compose_core.service_up(service_name="ui", friendly_name="UI", final_env_file=final_env_file)

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

    cli_config = Config()
    env_service = EnvService(cli_config)
    compose_core = DockerComposeCore(env_service=env_service)

    result = compose_core.service_down(service_name="ui", friendly_name="UI", final_env_file=final_env_file, is_reset=is_reset)

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
    EnvService.prepare_clean_env(final_env_file)

    cli_config = Config()
    env_service = EnvService(cli_config)
    compose_core = DockerComposeCore(env_service=env_service)

    result = compose_core.services_down(final_env_file=final_env_file, is_reset=is_reset)

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

def run_compose_lite_logs(final_env_file: Path) -> None:
    EnvService.prepare_clean_env(final_env_file)

    cli_config = Config()
    env_service = EnvService(cli_config)
    compose_core = DockerComposeCore(env_service=env_service)

    result = compose_core.services_logs(final_env_file=final_env_file, should_follow=True)

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
):
    cli_config = Config()
    confirm_accepts_license_agreement(accept_terms_and_conditions, cli_config)

    DockerUtils.ensure_docker_installed()

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

    env_service.define_saas_wdu_runtime()
    
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
        env_service.define_saas_wdu_runtime("local")

    if experimental_with_ibm_telemetry:
        merged_env_dict['USE_IBM_TELEMETRY'] = 'true'

    if with_langflow:
        merged_env_dict['LANGFLOW_ENABLED'] = 'true'
    
    if with_voice:
        merged_env_dict['VOICE_ENABLED'] = 'true'
    

    try:
        DockerLoginService(env_service=env_service).login_by_dev_edition_source(merged_env_dict)
    except ValueError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

    final_env_file = env_service.write_merged_env_file(merged_env_dict)

    run_compose_lite(final_env_file=final_env_file,
                     experimental_with_langfuse=experimental_with_langfuse,
                     experimental_with_ibm_telemetry=experimental_with_ibm_telemetry,
                     with_doc_processing=with_doc_processing,
                     with_voice=with_voice,
                     with_connections_ui=with_connections_ui,
                     with_langflow=with_langflow, env_service=env_service)
    
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

    refresh_local_credentials()

    logger.info(f"You can run `orchestrate env activate local` to set your environment or `orchestrate chat start` to start the UI service and begin chatting.")

    if experimental_with_langfuse:
        logger.info(f"You can access the observability platform Langfuse at http://localhost:3010, username: orchestrate@ibm.com, password: orchestrate")
    if with_doc_processing:
        logger.info(f"Document processing in Flows (Public Preview) has been enabled.")
    if with_connections_ui:
        logger.info("Connections UI can be found at http://localhost:3412/connectors")
    if with_langflow:
        logger.info("Langflow has been enabled, the Langflow UI is available at http://localhost:7861")
@server_app.command(name="stop")
def server_stop(
    user_env_file: str = typer.Option(
        None,
        "--env-file", '-e',
        help="Path to a .env file that overrides default.env. Then environment variables override both."
    )
):

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

@server_app.command(name="reset")
def server_reset(
        user_env_file: str = typer.Option(
            None,
            "--env-file", '-e',
            help="Path to a .env file that overrides default.env. Then environment variables override both."
        ),
):
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

@server_app.command(name="logs")
def server_logs(
    user_env_file: str = typer.Option(
        None,
        "--env-file", '-e',
        help="Path to a .env file that overrides default.env. Then environment variables override both."
    )
):
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

def run_db_migration() -> None:
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

        # Create wxo_observability database if it doesn't exist
        if psql -U {pg_user} -lqt | cut -d \\| -f 1 | grep -qw wxo_observability; then
            echo 'Existing wxo_observability DB found'
        else
            echo 'Creating wxo_observability DB'
            createdb -U "{pg_user}" -O "{pg_user}" wxo_observability;
            psql -U {pg_user} -q -d postgres -c "GRANT CONNECT ON DATABASE wxo_observability TO {pg_user}";
        fi

        # Run observability-specific migrations
        OBSERVABILITY_MIGRATIONS_FILE="/var/lib/postgresql/applied_migrations/observability_migrations.txt"
        touch "$OBSERVABILITY_MIGRATIONS_FILE"

        for file in /docker-entrypoint-initdb.d/observability/*.sql; do
            if [ -f "$file" ]; then
                filename=$(basename "$file")
                
                if grep -Fxq "$filename" "$OBSERVABILITY_MIGRATIONS_FILE"; then
                    echo "Skipping already applied observability migration: $filename"
                else
                    echo "Applying observability migration: $filename"
                    if psql -U {pg_user} -d wxo_observability -q -f "$file" > /dev/null 2>&1; then
                        echo "$filename" >> "$OBSERVABILITY_MIGRATIONS_FILE"
                    else
                        echo "Error applying observability migration: $filename. Stopping migrations."
                        exit 1
                    fi
                fi
            fi
        done
        '''

    cli_config = Config()
    env_service = EnvService(cli_config)
    compose_core = DockerComposeCore(env_service=env_service)

    result = compose_core.service_container_bash_exec(service_name="wxo-server-db",
                                                      log_message="Running Database Migration...",
                                                      final_env_file=final_env_file, bash_command=migration_command)

    if result.returncode == 0:
        logger.info("Migration ran successfully.")
    else:
        error_message = result.stderr.decode('utf-8') if result.stderr else "Error occurred."
        logger.error(
            f"Error running database migration):\n{error_message}"
        )
        sys.exit(1)

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

    cli_config = Config()
    env_service = EnvService(cli_config)
    compose_core = DockerComposeCore(env_service=env_service)

    result = compose_core.service_container_bash_exec(service_name="wxo-server-db",
                                                      log_message="Preparing Langflow resources...",
                                                      final_env_file=final_env_file, bash_command=creation_command)

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


if __name__ == "__main__":
    server_app()
