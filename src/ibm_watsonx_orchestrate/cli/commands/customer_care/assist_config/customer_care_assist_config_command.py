import typer
from typing_extensions import Annotated

from ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config.customer_care_assist_config_controller import (
    list_assist_config,
    set_assist_config,
    remove_assist_config,
    reset_assist_config,
)

customer_care_assist_config = typer.Typer(no_args_is_help=True)


@customer_care_assist_config.command(
    name="list",
    help="List current agent-assist configuration overrides",
)
def list_assist_config_command() -> None:
    list_assist_config()


@customer_care_assist_config.command(
    name="set",
    help="Set an agent-assist configuration property",
)
def set_assist_config_command(
    property_name: Annotated[
        str,
        typer.Option("--property", "-p", help="The configuration property to set"),
    ],
    value: Annotated[
        str,
        typer.Option("--value", "-v", help="The value to assign to the property"),
    ],
) -> None:
    set_assist_config(property_name=property_name, value=value)


@customer_care_assist_config.command(
    name="remove",
    help="Remove a single agent-assist configuration property override",
)
def remove_assist_config_command(
    property_name: Annotated[
        str,
        typer.Option("--property", "-p", help="The configuration property to remove"),
    ],
) -> None:
    remove_assist_config(property_name=property_name)


@customer_care_assist_config.command(
    name="reset",
    help="Remove all agent-assist configuration overrides",
)
def reset_assist_config_command() -> None:
    reset_assist_config()
