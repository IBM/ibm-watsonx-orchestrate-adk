import logging
import typer
import webbrowser

from pathlib import Path
from typing_extensions import Annotated

from ibm_watsonx_orchestrate.cli.commands.server.server_command import run_compose_lite_ui, run_compose_lite_down_ui
from ibm_watsonx_orchestrate.cli.commands.chat.chat_controller import chat_ask_interactive

logger = logging.getLogger(__name__)
chat_app = typer.Typer(no_args_is_help=True)

@chat_app.command(name="start")
def chat_start(
    user_env_file: Annotated[
        str,
        typer.Option(
            "--env-file", "-e",
            help="Path to a .env file that overrides default.env. Then environment variables override both."
        )
    ] = None,
    skip_open: Annotated[
        bool,
        typer.Option(
            "--skip-open", help="Do not open the chat UI in a web browser."
        )
    ] = False,
):
    """Start the web-based chat UI service for your local Developer Edition server.
    """
    user_env_file_path = Path(user_env_file) if user_env_file else None

    is_ui_service_started = run_compose_lite_ui(user_env_file=user_env_file_path)

    if is_ui_service_started:
        url = "http://localhost:3000/chat-lite"
        if skip_open is None or not skip_open:
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
    """Stop the web-based chat UI service.
    """
    user_env_file_path = Path(user_env_file) if user_env_file else None
    run_compose_lite_down_ui(user_env_file=user_env_file_path)

@chat_app.command(name="ask")
def chat_ask(
    agent_name: Annotated[
        str,
        typer.Option("--agent-name", "-n", help="Agent Name to chat with")
    ],
    message: Annotated[
        str,
        typer.Argument(help="Single message to send")
    ] = None,
    include_reasoning: Annotated[
        bool,
        typer.Option("--include-reasoning", "-r", help="Show reasoning trace from the agent")
    ] = False,
):
    """Chat with an agent: interactive mode or start chat by asking a question.
    
    Examples:
    
    \b
    orchestrate chat ask --agent-name <my-agent-name> "What is the weather?"
    orchestrate chat ask --agent-name <my-agent-name> "What is the weather?" --include-reasoning
    orchestrate chat ask --agent-name <my-agent-name>
    orchestrate chat ask --agent-name <my-agent-name> --include-reasoning
    
    """

    chat_ask_interactive(agent_name, include_reasoning=include_reasoning, initial_message=message)

if __name__ == "__main__":
    chat_app()