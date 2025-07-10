import logging
import sys
from pathlib import Path
import subprocess
import time
import requests
from ibm_watsonx_orchestrate.cli.commands.server.server_command import (
    get_compose_file,
    ensure_docker_compose_installed,
    _prepare_clean_env,
    ensure_docker_installed,
    read_env_file,
    get_default_env_file,
    get_persisted_user_env,
    get_dev_edition_source,
    get_default_registry_env_vars_by_dev_edition_source,
    docker_login_by_dev_edition_source,
    write_merged_env_file,
)

logger = logging.getLogger(__name__)

def _verify_env_contents(env: dict) -> None:
    if not env.get("WATSONX_APIKEY") or not env.get("WATSONX_SPACE_ID"):
        logger.error("The Copilot feature requires wx.ai credentials to passed through the provided env file. Please set 'WATSONX_SPACE_ID' and 'WATSONX_APIKEY'")
        sys.exit(1)

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

    _verify_env_contents(merged_env_dict)

    try:
        docker_login_by_dev_edition_source(merged_env_dict, dev_edition_source)
    except ValueError as ignored:
        # do nothing, as the docker login here is not mandatory
        pass

    final_env_file = write_merged_env_file(merged_env_dict)

    command = compose_command + [
        "-f", str(compose_path),
        "--env-file", str(final_env_file),
        "up",
        "cpe",
        "-d",
        "--remove-orphans"
    ]

    logger.info(f"Starting docker-compose Copilot service...")
    result = subprocess.run(command, capture_output=False)

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
    compose_path = get_compose_file()
    compose_command = ensure_docker_compose_installed()
    ensure_docker_installed()

    default_env = read_env_file(get_default_env_file())
    final_env_file = write_merged_env_file(default_env)

    command = compose_command + [
        "-f", str(compose_path),
        "--env-file", final_env_file,
        "down",
        "cpe"
    ]

    if is_reset:
        command.append("--volumes")
        logger.info("Stopping docker-compose Copilot service and resetting volumes...")
    else:
        logger.info("Stopping docker-compose Copilot service...")

    result = subprocess.run(command, capture_output=False)

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