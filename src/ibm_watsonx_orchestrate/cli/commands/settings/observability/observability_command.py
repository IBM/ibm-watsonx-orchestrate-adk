import typer

from ibm_watsonx_orchestrate.cli.commands.settings.observability.langfuse.langfuse_command import \
    settings_observability_langfuse_app
from ibm_watsonx_orchestrate.cli.commands.settings.observability.openlayer.openlayer_command import \
    settings_observability_openlayer_app

settings_observability_app = typer.Typer(no_args_is_help=True)
settings_observability_app.add_typer(
    settings_observability_langfuse_app,
    name="langfuse",
    help="Fetch or configure a langfuse integration"
)
settings_observability_app.add_typer(
    settings_observability_openlayer_app,
    name="openlayer",
    help="Fetch or configure an openlayer integration"
)
