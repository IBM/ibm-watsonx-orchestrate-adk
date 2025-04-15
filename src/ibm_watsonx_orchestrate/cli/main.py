import typer
import logging
import sys

from ibm_watsonx_orchestrate.cli.commands.connections.connections_command import connections_app
from ibm_watsonx_orchestrate.cli.commands.login.login_command import login_app
from ibm_watsonx_orchestrate.cli.commands.tools.tools_command import tools_app
from ibm_watsonx_orchestrate.cli.commands.agents.agents_command import agents_app
from ibm_watsonx_orchestrate.cli.commands.server.server_command import server_app
from ibm_watsonx_orchestrate.cli.commands.chat.chat_command import chat_app
from ibm_watsonx_orchestrate.cli.commands.models.models_command import models_app
from ibm_watsonx_orchestrate.cli.commands.environment.environment_command import environment_app

logger = logging.getLogger(__name__)

app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=False
)

# Global callback to handle --debug flag
@app.callback()
def global_flags(debug: bool = False):
    """This callback adds a global --debug flag."""
    if debug:
        sys.tracebacklimit = 40
    else:
        sys.tracebacklimit = 0

app.add_typer(login_app)
app.add_typer(tools_app, name="tools")
app.add_typer(agents_app, name="agents")
app.add_typer(server_app, name="server")
app.add_typer(chat_app, name="chat")
app.add_typer(connections_app, name="connections")
app.add_typer(models_app, name="models")
app.add_typer(environment_app, name="env")

if __name__ == "__main__":
    app()
