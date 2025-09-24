import logging
import sys
from pathlib import Path
import time
import requests
from urllib.parse import urlparse

from ibm_watsonx_orchestrate.cli.config import Config
from ibm_watsonx_orchestrate.utils.docker_utils import DockerLoginService, DockerComposeCore, DockerUtils
from ibm_watsonx_orchestrate.utils.environment import EnvService

logger = logging.getLogger(__name__)

def wait_for_wxo_cpe_health_check(timeout_seconds=45, interval_seconds=2):
    url = "http://localhost:8081/version"
    logger.info("Waiting for Copilot component to be initialized...")
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
    return False

def run_compose_lite_cpe(user_env_file: Path) -> bool:
    DockerUtils.ensure_docker_installed()

    cli_config = Config()
    env_service = EnvService(cli_config)
    env_service.prepare_clean_env(user_env_file)
    user_env = env_service.get_user_env(user_env_file)
    merged_env_dict = env_service.prepare_server_env_vars(user_env=user_env, should_drop_auth_routes=True)

    try:
        DockerLoginService(env_service=env_service).login_by_dev_edition_source(merged_env_dict)
    except ValueError as ignored:
        # do nothing, as the docker login here is not mandatory
        pass

    final_env_file = env_service.write_merged_env_file(merged_env_dict)

    compose_core = DockerComposeCore(env_service)

    result = compose_core.service_up(service_name="cpe", friendly_name="Copilot", final_env_file=final_env_file)

    if result.returncode == 0:
        logger.info("Copilot Service started successfully.")
        # Remove the temp file if successful
        if final_env_file.exists():
            final_env_file.unlink()
    else:
        error_message = result.stderr.decode('utf-8') if result.stderr else "Error occurred."
        logger.error(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n{error_message}"
        )
        return False
    
    is_successful_cpe_healthcheck = wait_for_wxo_cpe_health_check()
    if not is_successful_cpe_healthcheck:
        logger.error("The Copilot service did not initialize within the expected time.  Check the logs for any errors.")

    return True

def run_compose_lite_cpe_down(is_reset: bool = False) -> None:
    DockerUtils.ensure_docker_installed()

    default_env = EnvService.read_env_file(EnvService.get_default_env_file())
    final_env_file = EnvService.write_merged_env_file(default_env)

    cli_config = Config()
    env_service = EnvService(cli_config)
    compose_core = DockerComposeCore(env_service)

    result = compose_core.service_down(service_name="cpe", friendly_name="Copilot", final_env_file=final_env_file, is_reset=is_reset)

    if result.returncode == 0:
        logger.info("Copilot service stopped successfully.")
        # Remove the temp file if successful
        if final_env_file.exists():
            final_env_file.unlink()
    else:
        error_message = result.stderr.decode('utf-8') if result.stderr else "Error occurred."
        logger.error(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n{error_message}"
        )
        sys.exit(1)

def start_server(user_env_file_path: Path) -> None:
    is_server_started = run_compose_lite_cpe(user_env_file=user_env_file_path)

    if is_server_started:
        logger.info("Copilot service successfully started")
    else:
        logger.error("Unable to start orchestrate Copilot service.  Please check error messages and logs")

def stop_server() -> None:
    run_compose_lite_cpe_down()