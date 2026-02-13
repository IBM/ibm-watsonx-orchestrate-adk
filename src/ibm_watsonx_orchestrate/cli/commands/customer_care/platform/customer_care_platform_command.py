import typer
from typing import Optional
from typing_extensions import Annotated

from ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_controller import (
    configure_platform_customer_care,
    list_platform_customer_care,
    remove_platform_customer_care
)
from ibm_watsonx_orchestrate.cli.commands.customer_care.platform.types import PlatformType

customer_care_platform = typer.Typer(no_args_is_help=True)

@customer_care_platform.command(name="configure", help="Configure a connection to a new contact center platform or update an existing one")
def configure_platform_customer_care_command(
    type: Annotated[
        PlatformType,
        typer.Option('--type', '-t', help="The type of platform to configure")
    ],
    name: Annotated[
        str,
        typer.Option('--name', '-n', help="The name of the contact center you wish to create. This value will be used to in conjunction with a platform-specific suffix to uniquely reference this connection")
    ],
    client_id: Annotated[
        Optional[str],
        typer.Option('--client-id', help="The client_id to authenticate with")
    ] = None,
    client_secret: Annotated[
        Optional[str],
        typer.Option('--client-secret', help="The client_secret to authenticate with")
    ] = None,
    client_secret_stdin: Annotated[
        Optional[str],
        typer.Option('--client-secret-stdin', help="The client_secret from stdin to authenticate with")
    ] = None,
    endpoint: Annotated[
        Optional[str],
        typer.Option('--endpoint', help="The endpoint to authenticate with")
    ] = None
) -> None:
    configure_platform_customer_care(
        type=type,
        name=name,
        client_id=client_id,
        client_secret=client_secret,
        client_secret_stdin=client_secret_stdin,
        endpoint=endpoint
    )

@customer_care_platform.command(name="list", help="List connections to contact center platforms for customer care")
def list_platform_customer_care_command(
   type: Annotated[
    Optional[PlatformType],
    typer.Option('--type', '-t', help="The type of platform to list")
   ] = None
) -> None:
    list_platform_customer_care(
        type=type
    )

@customer_care_platform.command(name="remove", help="Remove connections to contact center platforms for customer care")
def remove_platform_customer_care_command(
     name: Annotated[
        str,
        typer.Option('--name', '-n', help="The name of the contact center to remove. This can be the full id or the prefix")
    ],
    type: Annotated[
        Optional[PlatformType],
        typer.Option('--type', '-t', help="The type of platform to remove")
    ] = None
) -> None:
    remove_platform_customer_care(
        type=type,
        name=name
    )