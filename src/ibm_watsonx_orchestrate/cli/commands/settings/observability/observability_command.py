import typer

from ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command import \
    settings_observability_langfuse_app

settings_observability_app = typer.Typer(no_args_is_help=True)
settings_observability_app.add_typer(
    settings_observability_langfuse_app,
    name="langfuse",
    help="Fetch or configure a langfuse integration"
)