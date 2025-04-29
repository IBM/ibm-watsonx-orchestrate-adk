import typer

from ibm_watsonx_orchestrate.cli.commands.settings.observability.observability_command import settings_observability_app

settings_app = typer.Typer(no_args_is_help=True)
settings_app.add_typer(
    settings_observability_app,
    name="observability",
    help="Configures an external observability platform (such as langfuse)"
)