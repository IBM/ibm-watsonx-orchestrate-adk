import typer
from ibm_watsonx_orchestrate.cli.commands.connections.application.connections_application_command import connections_application_app

connections_app = typer.Typer(no_args_is_help=True)
connections_app.add_typer(
    connections_application_app,
    name="application",
    help="Creates or deletes a connection (credential binding) to an external application for use in, for example, an openapi tool"
)