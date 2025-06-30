import logging
import typer
import webbrowser
from pathlib import Path

chat_app = typer.Typer(no_args_is_help=True)
from ibm_watsonx_orchestrate.cli.commands.server.server_command import run_compose_lite_ui, run_compose_lite_down_ui

logger = logging.getLogger(__name__)

@chat_app.command(name="start")
def chat_start(
    user_env_file: str = typer.Option(
        None,
        "--env-file", "-e",
        help="Path to a .env file that overrides default.env. Then environment variables override both."
    )
):
    user_env_file_path = Path(user_env_file) if user_env_file else None

    is_ui_service_started = run_compose_lite_ui(user_env_file=user_env_file_path)

    if is_ui_service_started:
        url = "http://localhost:3000/chat-lite"
        webbrowser.open(url)
        logger.info(f"Opening chat interface at {url}")
        # TODO: Remove when connections UI is added
        logger.warning("When using local chat, requests that the user 'Connect Apps' must be resolved by running `orchestrate connections set-credentials`")
    else:
        logger.error("Unable to start orchestrate UI chat service.  Please check error messages and logs")

@chat_app.command(name="stop")
def chat_stop(
    user_env_file: str = typer.Option(
        None,
        "--env-file", "-e",
        help="Path to a .env file that overrides default.env. Then environment variables override both."
    )
):
    user_env_file_path = Path(user_env_file) if user_env_file else None
    run_compose_lite_down_ui(user_env_file=user_env_file_path)


if __name__ == "__main__":
    chat_app()