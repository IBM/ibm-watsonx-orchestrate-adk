import os
import sys
import subprocess
import tempfile
from pathlib import Path
import requests
import time

import typer
import importlib.resources as resources
from dotenv import dotenv_values

server_app = typer.Typer(no_args_is_help=True)


def ensure_docker_installed() -> None:
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Unable to find an installed docker")
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

def docker_login(iam_api_key: str, registry_url: str) -> None:
    print(f"Logging into Docker registry: {registry_url} ...")
    result = subprocess.run(
        ["docker", "login", "-u", "iamapikey", "--password-stdin", registry_url],
        input=iam_api_key.encode("utf-8"),
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"Error logging into Docker:\n{result.stderr.decode('utf-8')}")
        sys.exit(1)
    print("Successfully logged in to Docker.")


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


def merge_env(
    default_env_path: Path,
    user_env_path: Path | None
) -> dict:
    #Default values in docker/default.env and overrides in user .env or environment
    merged = dotenv_values(str(default_env_path))

    if user_env_path is not None:
        user_env = dotenv_values(str(user_env_path))
        merged.update(user_env)

    for key, val in os.environ.items():
        merged[key] = val

    return merged


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



def run_compose_lite(final_env_file: Path) -> None:
    compose_path = get_compose_file()
    compose_command = ensure_docker_compose_installed()

    command = compose_command + [
        "-f", str(compose_path),
        "--env-file", str(final_env_file),
        "up",
        "--scale",
        "ui=0",
        "-d",
        "--remove-orphans"
    ]

    print("Starting docker-compose services...")
    result = subprocess.run(command, capture_output=False)

    if result.returncode == 0:
        print("Services started successfully.")
        # Remove the temp file if successful
        if final_env_file.exists():
            final_env_file.unlink()
    else:
        error_message = result.stderr.decode('utf-8') if result.stderr else "Error occurred."
        print(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n"
            f"{error_message}"
        )
        sys.exit(1)

def wait_for_wxo_server_health_check(health_user, health_pass, timeout_seconds=45, interval_seconds=2):
    url = "http://localhost:4321/api/v1/auth/token"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'username': health_user,
        'password': health_pass
    }

    start_time = time.time()
    while time.time() - start_time <= timeout_seconds:
        try:
            response = requests.get(url)
            if 200 <= response.status_code < 300:
                return True
            else:
                print(f"Response code from healthcheck {response.status_code}")
        except requests.RequestException as e:
            pass
            #print(f"Request failed: {e}")

        time.sleep(interval_seconds)

    return False

def run_compose_lite_ui(user_env_file: Path, agent_name: str) -> bool:
    compose_path = get_compose_file()
    compose_command = ensure_docker_compose_installed()
    ensure_docker_installed()
    default_env_path = get_default_env_file()
    print(f"user env file: {user_env_file}")
    merged_env_dict = merge_env(
        default_env_path,
        user_env_file if user_env_file else None
    )

    registry_url = merged_env_dict.get("REGISTRY_URL")
    if not registry_url:
        print("Error: REGISTRY_URL is required but not set in the environment.")
        sys.exit(1)

    iam_api_key = merged_env_dict.get("DOCKER_IAM_KEY")
    if iam_api_key:
        docker_login(iam_api_key, registry_url)

    #These are to removed warning and not used in UI component
    if not 'WATSONX_SPACE_ID' in merged_env_dict:
        merged_env_dict['WATSONX_SPACE_ID']='X'
    if not 'WATSONX_APIKEY' in merged_env_dict:
        merged_env_dict['WATSONX_APIKEY']='X'
    apply_llm_api_key_defaults(merged_env_dict)

    if agent_name:
        merged_env_dict['ORCHESTRATOR_AGENT_NAME'] = agent_name

    final_env_file = write_merged_env_file(merged_env_dict)



    print("Waiting for ochestrate server to be fully started and ready...")
    wxo_user = merged_env_dict['WXO_USER']
    is_successful_server_healthcheck = wait_for_wxo_server_health_check(merged_env_dict['WXO_USER'], merged_env_dict['WXO_PASS'])
    if not is_successful_server_healthcheck:
        print("Healthcheck failed orchestrate server.  Make sure you start the server components with `orchestrate server start` before trying to start the chat UI")
        return False

    command = compose_command + [
        "-f", str(compose_path),
        "--env-file", str(final_env_file),
        "up",
        "ui",
        "-d",
        "--remove-orphans"
    ]

    print(f"Starting docker-compose UI service with orchestrator agent name {merged_env_dict['ORCHESTRATOR_AGENT_NAME']}...")
    result = subprocess.run(command, capture_output=False)

    if result.returncode == 0:
        print("Chat UI Service started successfully.")
        # Remove the temp file if successful
        if final_env_file.exists():
            final_env_file.unlink()
    else:
        error_message = result.stderr.decode('utf-8') if result.stderr else "Error occurred."
        print(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n"
            f"{error_message}"
        )
        return False
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
        print("Stopping docker-compose UI service and resetting volumes...")
    else:
        print("Stopping docker-compose UI service...")

    result = subprocess.run(command, capture_output=False)

    if result.returncode == 0:
        print("UI service stopped successfully.")
        # Remove the temp file if successful
        if final_env_file.exists():
            final_env_file.unlink()
    else:
        error_message = result.stderr.decode('utf-8') if result.stderr else "Error occurred."
        print(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n"
            f"{error_message}"
        )
        sys.exit(1)

def run_compose_lite_down(final_env_file: Path, is_reset: bool = False) -> None:
    compose_path = get_compose_file()
    compose_command = ensure_docker_compose_installed()

    command = compose_command + [
        "-f", str(compose_path),
        "--env-file", str(final_env_file),
        "down"
    ]

    if is_reset:
        command.append("--volumes")
        print("Stopping docker-compose services and resetting volumes...")
    else:
        print("Stopping docker-compose services...")

    result = subprocess.run(command, capture_output=False)

    if result.returncode == 0:
        print("Services stopped successfully.")
        # Remove the temp file if successful
        if final_env_file.exists():
            final_env_file.unlink()
    else:
        error_message = result.stderr.decode('utf-8') if result.stderr else "Error occurred."
        print(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n"
            f"{error_message}"
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

    print("Docker Logs...")

    result = subprocess.run(command, capture_output=False)

    if result.returncode == 0:
        print("End of docker logs")
        # Remove the temp file if successful
        if final_env_file.exists():
            final_env_file.unlink()
    else:
        error_message = result.stderr.decode('utf-8') if result.stderr else "Error occurred."
        print(
            f"Error running docker-compose (temporary env file left at {final_env_file}):\n"
            f"{error_message}"
        )
        sys.exit(1)

@server_app.command(name="start")
def server_start(
    user_env_file: str = typer.Option(
        None,
        "--env-file",
        help="Path to a .env file that overrides default.env. Then environment variables override both."
    )
):
    
    ensure_docker_installed()

    default_env_path = get_default_env_file()

    merged_env_dict = merge_env(
        default_env_path,
        Path(user_env_file) if user_env_file else None
    )

    iam_api_key = merged_env_dict.get("DOCKER_IAM_KEY")
    if not iam_api_key:
        print("Error: DOCKER_IAM_KEY is required but not set in the environment.")
        sys.exit(1)

    registry_url = merged_env_dict.get("REGISTRY_URL")
    if not registry_url:
        print("Error: REGISTRY_URL is required but not set in the environment.")
        sys.exit(1)

    docker_login(iam_api_key, registry_url)

    apply_llm_api_key_defaults(merged_env_dict)

    final_env_file = write_merged_env_file(merged_env_dict)
    run_compose_lite(final_env_file=final_env_file)

    print(f"You can run `orchestrate chat start` to start the UI service and begin chatting.")

@server_app.command(name="stop")
def server_stop(
    user_env_file: str = typer.Option(
        None,
        "--env-file",
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
        "--env-file",
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
        "--env-file",
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

if __name__ == "__main__":
    server_app()