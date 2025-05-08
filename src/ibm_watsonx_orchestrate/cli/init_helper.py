import importlib.metadata
from importlib import resources
from typing import Optional
from rich import print as pprint
from dotenv import dotenv_values
import typer

from ibm_watsonx_orchestrate.cli.config import Config, PYTHON_REGISTRY_HEADER, \
    PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT


def version_callback(checkVersion: bool=True):
    if checkVersion:
        __version__ = importlib.metadata.version('ibm-watsonx-orchestrate')
        default_env = dotenv_values(resources.files("ibm_watsonx_orchestrate.docker").joinpath("default.env"))
        cfg = Config()
        pypi_override = cfg.read(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT)

        adk_version_str = f"[bold]ADK Version[/bold]: {__version__}"
        if pypi_override is not None:
            adk_version_str += f" [red bold](override: {pypi_override})[/red bold]"
        pprint(adk_version_str)


        pprint("[bold]Developer Edition Image Tags[/bold] [italic](if not overridden in env file)[/italic]")
        for key, value in default_env.items():
            if key.endswith('_TAG') or key == 'DBTAG':
                pprint(f"  [bold]{key}[/bold]: {value}")

        raise typer.Exit()

    

def init_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
      None, 
      "--version",
      help="Show the installed version of the ADK and Developer Edition Tags",
      callback=version_callback
    )
):
    pass
