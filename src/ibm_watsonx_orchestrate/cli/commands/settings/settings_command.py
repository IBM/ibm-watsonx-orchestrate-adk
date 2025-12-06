import typer
from typing import Annotated
from ibm_watsonx_orchestrate.cli.commands.settings.observability.observability_command import settings_observability_app
from ibm_watsonx_orchestrate.cli.commands.settings.settings_controller import SettingsController
from ibm_watsonx_orchestrate.cli.commands.settings.docker import docker_settings_app

settings_app = typer.Typer(no_args_is_help=True)
settings_app.add_typer(
    settings_observability_app,
    name="observability",
    help="Configures an external observability platform (such as langfuse)"
)
settings_app.add_typer(
    docker_settings_app,
    name="docker",
    help="Configuration for the docker host used to run the developer edition"
)

@settings_app.command(name="set-encoding", help="Set the encoding type the ADK should use for file access. If unset the ADK will try detect the encoding of each file.")
def set_encoding(
    encoding: Annotated[
        str,
        typer.Argument(),
    ],
):
    settings_controller = SettingsController()
    settings_controller.set_encoding(encoding=encoding)

@settings_app.command(name="unset-encoding", help="Unset the encoding override setting an resort to default bahaviour where the ADK will try detect the encoding of each file.")
def unset_encoding():
    settings_controller = SettingsController()
    settings_controller.unset_encoding()
