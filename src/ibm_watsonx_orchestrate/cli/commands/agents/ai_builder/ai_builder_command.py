import typer
from typing_extensions import Annotated
from pathlib import Path
from ibm_watsonx_orchestrate.cli.commands.agents.ai_builder.ai_builder_controller import prompt_tune, create_agent, \
    submit_refine_agent_with_chats

ai_builder_app = typer.Typer(no_args_is_help=True)

@ai_builder_app.command(name="create", help='Create an agent from scratch with the help of the AI Builder.')
def create_command(
    output_file: Annotated[
        Path,
        typer.Option("--output-file", "-o", help="Optional output file to save the agent spec"),
    ] = None,
    dry_run_flag: Annotated[
        bool,
        typer.Option("--dry-run", help="Dry run will prevent the tuned content being saved to a file and output the results to console"),
    ] = False,
    llm: Annotated[
        str,
        typer.Option("--llm", help="Select the agent LLM"),
    ] = None,
    chat_llm: Annotated[
        str,
        typer.Option("--chat-llm", help="Select the underlying model for the AI Builder. Currently only llama-3-3-70b-instruct and gpt-oss-120b are supported"),
    ] = None,
    agent_description: Annotated[
        str,
        typer.Option("--agent_description", "-d", help="A clear and comprehensive description enables the Agent Builder to better understand the agent’s intended functionality. If not provided the Agent Builder will ask for it"),
    ] = None
):
    create_agent(
        chat_llm=chat_llm,
        llm=llm,
        output_file=output_file,
        dry_run_flag=dry_run_flag,
        description=agent_description
    )

@ai_builder_app.command(name="prompt-tune", help='Tune the instructions of an Agent using IBM Conversational Prompt Engineering (CPE) to improve agent performance')
def prompt_tune_command(
    file: Annotated[
        Path,
        typer.Option("--file", "-f", help="Path to agent spec file"),
    ],
    output_file: Annotated[
        Path,
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
    chat_llm: Annotated[
        str,
        typer.Option("--chat-llm", help="Select the underlying model for the AI Builder. Currently only llama-3-3-70b-instruct and gpt-oss-120b are supported"),
    ] = None,
):
    prompt_tune(
        chat_llm=chat_llm,
        llm=llm,
        agent_spec=file,
        output_file=output_file,
        dry_run_flag=dry_run_flag,
    )

@ai_builder_app.command(name="autotune", help="Autotune the agent's instructions by incorporating insights from chat interactions and user feedback")
def agent_refine(
    agent_name: Annotated[
        str,
        typer.Option("--agent-name", "-n", help="The name of the agent to tune"),
    ],
    output_file: Annotated[
        Path,
        typer.Option("--output-file", "-o", help="Optional output file to avoid overwriting existing agent spec"),
    ] = None,
    use_last_chat: Annotated[
        bool,
        typer.Option("--use-last-chat", "-l", help="Tuning by using the last conversation with the agent instead of prompting the user to choose chats"),
    ] = False,
    dry_run_flag: Annotated[
        bool,
        typer.Option("--dry-run",
                     help="Dry run will prevent the tuned content being saved and output the results to console"),
    ] = False,
    chat_llm: Annotated[
        str,
        typer.Option("--chat-llm", help="Select the underlying model for the AI Builder. Currently only llama-3-3-70b-instruct is supported."),
    ] = None,

):
    submit_refine_agent_with_chats(agent_name=agent_name, chat_llm=chat_llm, output_file=output_file, use_last_chat=use_last_chat, dry_run_flag=dry_run_flag)