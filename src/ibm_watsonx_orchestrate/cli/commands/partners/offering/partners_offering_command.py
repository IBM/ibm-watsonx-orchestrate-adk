import typer
from typing_extensions import Annotated
from ibm_watsonx_orchestrate.cli.commands.partners.offering.partners_offering_controller import PartnersOfferingController
from typing_extensions import Annotated
from ibm_watsonx_orchestrate.cli.commands.partners.offering.types import AgentKind


partners_offering = typer.Typer(no_args_is_help=True)

@partners_offering.command(
        name="create",
        help="Export Items from your environment to create an offering"
    )
def create_offering(
    offering: Annotated[
        str,
        typer.Option("--offering", "-o", help="Name of the offering"),
    ],
    publisher_name: Annotated[
        str,
        typer.Option("--publisher", "-p", help="Publisher name"),
    ],
    type: Annotated[
        AgentKind,
        typer.Option("--type", "-t", help="Type of agent: native|external"),
    ],
    agent_name: Annotated[
        str,
        typer.Option("--agent-name", "-a", help="Agent name to create"),
    ],
):
    controller = PartnersOfferingController()
    controller.create(
        offering=offering,
        publisher_name=publisher_name,
        agent_type=type,
        agent_name=agent_name,
    )


@partners_offering.command(
        name="package",
        help="Validate your exported offering and package for upload"
    )
def package_offering(
    offering: Annotated[
        str,
        typer.Option("--offering", "-o", help="Name of the offering to package"),
    ],
    folder_path: Annotated[
        str,
        typer.Option("--folder", "-f", help="Path to folder containing the specified offering")
    ] = None
):
    controller = PartnersOfferingController()
    controller.package(offering=offering, folder_path=folder_path)