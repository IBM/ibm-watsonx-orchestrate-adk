import typer
from typing_extensions import Annotated
from ibm_watsonx_orchestrate.cli.commands.login import login_controller
from ibm_watsonx_orchestrate.client.utils import is_local_dev
import logging

logger = logging.getLogger(__name__)

login_app = typer.Typer(no_args_is_help=True)

DEFAULT_LOCAL_SERVICE_URL = "http://localhost:4321"


@login_app.command(name="login")
def login(
    apikey: Annotated[
        str,
        typer.Option(
            "--apikey", "-a", help="WXO API Key. Leave Blank if developing locally"
        ),
    ] = None,
    url: Annotated[
        str,
        typer.Option("--url", "-u", help="URL of the WXO instance you wish to access"),
    ] = None,
    local: Annotated[bool, typer.Option("--local", help="local login ")] = False):

    is_local = False

    if local:
        logger.warning(f"For local development environment, default to url: {DEFAULT_LOCAL_SERVICE_URL}")
        url = DEFAULT_LOCAL_SERVICE_URL
        is_local = True

    if url and is_local_dev(url):
        logger.warning("Local development url found. Default to local setup")
        is_local = True

    login_controller.login(apikey=apikey, url=url, is_local=is_local)
