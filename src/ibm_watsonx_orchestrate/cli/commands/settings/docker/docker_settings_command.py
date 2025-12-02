import typer
from typing import Annotated
from ibm_watsonx_orchestrate.cli.commands.settings.settings_controller import SettingsController

docker_settings_app = typer.Typer(no_args_is_help=True)


@docker_settings_app.command(name="host", help="Configure the docker host used to run the developer edition")
def set_docker_host(
    use_native_docker: Annotated[
        bool,
        typer.Option("--user-managed/--orchestrate")
    ]
):
    settings_controller = SettingsController()
    settings_controller.set_docker_host(native=use_native_docker)