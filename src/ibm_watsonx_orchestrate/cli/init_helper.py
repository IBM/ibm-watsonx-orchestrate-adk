import importlib.metadata
from importlib import resources
from typing import Optional
from rich import print as pprint
from dotenv import dotenv_values
import typer
import sys

from ibm_watsonx_orchestrate.cli.commands.langflow.utils import is_langflow_container_running
from ibm_watsonx_orchestrate.cli.config import Config, PYTHON_REGISTRY_HEADER, \
    PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT


def version_callback(checkVersion: bool=True):
    if checkVersion:
        __version__ = importlib.metadata.version('ibm-watsonx-orchestrate')
        default_env = dotenv_values(resources.files("ibm_watsonx_orchestrate.developer_edition.resources.docker").joinpath("default.env"))
        cfg = Config()
        pypi_override = cfg.read(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT)

        adk_version_str = f"[bold]ADK Version[/bold]: {__version__}"
        if pypi_override is not None:
            adk_version_str += f" [red bold](override: {pypi_override})[/red bold]"
        pprint(adk_version_str)

        langflow_version = default_env.get("LANGFLOW_TAG")
        langflow_version_string = f"[bold]Langflow Version[/bold]: {langflow_version}"
        langflow_image = default_env.get("LANGFLOW_IMAGE")
        if langflow_image:
            langflow_version_string += f" ({langflow_image})"
        pprint(langflow_version_string)

        pprint("[bold]Developer Edition Image Tags[/bold] [italic](if not overridden in env file)[/italic]")
        for key, value in default_env.items():
            if key.endswith('_TAG') or key == 'DBTAG' or key == 'UITAG':
                pprint(f"  [bold]{key}[/bold]: {value}")

        raise typer.Exit()


def init_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
      None, 
      "--version",
      help="Show the installed version of the ADK and Developer Edition Tags",
      callback=version_callback
    ),
    debug: Optional[bool] = typer.Option(
        False,
        "--debug",
        help="Enable debug mode"
    )
):
    if debug:
        sys.tracebacklimit = 40
    else:
        sys.tracebacklimit = 0
    pass
