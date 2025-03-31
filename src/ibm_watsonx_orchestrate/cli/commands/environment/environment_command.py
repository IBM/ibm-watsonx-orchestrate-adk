import logging
import typer
from typing_extensions import Annotated
from ibm_watsonx_orchestrate.cli.commands.environment import environment_controller
from ibm_watsonx_orchestrate.cli.commands.environment.types import EnvironmentAuthType
from ibm_watsonx_orchestrate.cli.commands.tools.types import RegistryType
from ibm_watsonx_orchestrate.client.utils import is_local_dev

logger = logging.getLogger(__name__)

environment_app = typer.Typer(no_args_is_help=True)


@environment_app.command(name="activate")
def activate_env(
        name: Annotated[
            str,
            typer.Argument(),
        ],
        apikey: Annotated[
            str,
            typer.Option(
                "--apikey", "-a", help="WXO API Key. Leave Blank if developing locally"
            ),
        ] = None,
        registry: Annotated[
            RegistryType,
            typer.Option("--registry", help="Which registry to use when importing python tools", hidden=True),
        ] = None,
        test_package_version_override: Annotated[
            str,
            typer.Option("--test-package-version-override", help="Which prereleased package version to reference when using --registry testpypi", hidden=True),
        ] = None
):
    environment_controller.activate(name=name, apikey=apikey, registry=registry, test_package_version_override=test_package_version_override)


@environment_app.command(name="add")
def add_env(
        name: Annotated[
            str,
            typer.Option("--name", "-n", help="Name of the environment you wish to create"),
        ],
        url: Annotated[
            str,
            typer.Option("--url", "-u", help="URL for the watsonX Orchestrate instance"),
        ],
        activate: Annotated[
            bool,
            typer.Option("--activate", "-a", help="Activate the newly created environment"),
        ] = False,
        iam_url: Annotated[
            str,
            typer.Option(
                "--iam-url", "-i", help="The URL for the IAM token authentication", hidden=True
            ),
        ] = None,
        type: Annotated[
            EnvironmentAuthType,
            typer.Option("--type", "-t", help="The type of auth you wish to use"),
        ] = None
):
    environment_controller.add(name=name, url=url, should_activate=activate, iam_url=iam_url, type=type)


@environment_app.command(name="remove")
def remove_env(
        name: Annotated[
            str,
            typer.Option("--name", "-n", help="Name of the environment you wish to create"),
        ],
):
    environment_controller.remove(name=name)


@environment_app.command(name="list")
def list_envs():
    environment_controller.list_envs()
