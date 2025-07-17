import typer
from typing_extensions import Annotated
from pathlib import Path
from ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller import prompt_tune, create_agent
from ibm_watsonx_orchestrate.cli.commands.copilot.copilot_server_controller import start_server, stop_server

copilot_app = typer.Typer(no_args_is_help=True)

# Server Commands
@copilot_app.command(name="start", help='Start the copilot server')
def start_server_command(
    user_env_file: str = typer.Option(
        None,
        "--env-file", "-e",
        help="Path to a .env file that overrides default.env. Then environment variables override both."
    )
):
    user_env_file_path = Path(user_env_file) if user_env_file else None

    start_server(user_env_file_path=user_env_file_path)

@copilot_app.command(name="stop", help='Stop the copilot server')
def stop_server_command():
    stop_server()

# Functional Commands
@copilot_app.command(name="prompt-tune", help='Tune the instructions of an Agent using IBM Conversational Prompt Engineering (CPE) to improve agent performance')
def prompt_tume_command(
    file: Annotated[
        str,
        typer.Option("--file", "-f", help="Path to agent spec file"),
    ] = None,
    output_file: Annotated[
        str,
        typer.Option("--output-file", "-o", help="Optional output file to avoid overwriting existing agent spec"),
    ] = None,
    dry_run_flag: Annotated[
        bool,
        typer.Option("--dry-run", help="Dry run will prevent the tuned content being saved and output the results to console"),
    ] = False,
    llm: Annotated[
        str,
        typer.Option("--llm", help="Select the agent LLM"),
    ] = None,
    samples: Annotated[
        str,
        typer.Option("--samples", "-s", help="Path to utterances sample file (txt file where each line is a utterance, or csv file with a single \"input\" column)"),
    ] = None
):
    if file is None:
        # create agent yaml from scratch
        create_agent(
            llm=llm,
            output_file=output_file,
            samples_file=samples,
            dry_run_flag=dry_run_flag
        )
    else:
        # improve existing agent instruction
        prompt_tune(
            agent_spec=file,
            samples_file=samples,
            output_file=output_file,
            dry_run_flag=dry_run_flag,
        )