import logging
import typer
from typing_extensions import Annotated

# REMOVE THIS FILE AFTER ONE MAJOR UPDATE
logger = logging.getLogger(__name__)

login_app = typer.Typer(no_args_is_help=True)

@login_app.command(name="login", add_help_option=False, hidden=True)
def login(
    local: Annotated[bool, typer.Option("--local", help="local login ")] = False):

    if local:
        logger.error("The command `orchestrate login --local` has been deprecated. Please use `orchestrate env activate local` instead") 
    else:
        logger.error("The command `orchestrate login` has been deprecated. Please use `orchestrate env activate <env>` instead")
