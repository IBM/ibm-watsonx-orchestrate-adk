import typer

from ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_command import customer_care_platform
from ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config.customer_care_assist_config_command import customer_care_assist_config

customer_care_app = typer.Typer(no_args_is_help=True)

customer_care_app.add_typer(
    typer_instance=customer_care_platform,
    name="platform",
    help="Manage connections to customer care platforms (e.g. Genesys)"
)

customer_care_app.add_typer(
    typer_instance=customer_care_assist_config,
    name="assist-config",
    help="Manage agent-assist configuration overrides",
    hidden=True,
)
