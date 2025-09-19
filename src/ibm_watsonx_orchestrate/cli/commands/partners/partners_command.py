import typer

from ibm_watsonx_orchestrate.cli.commands.partners import partners_controller
from ibm_watsonx_orchestrate.cli.commands.partners.offering.partners_offering_command import partners_offering

partners_app = typer.Typer(no_args_is_help=True)

partners_app.add_typer(
    partners_offering,
    name="offering",
    help="Tools for partners to create and package offerings"
)