import typer

from ibm_watsonx_orchestrate.cli.commands.connections.connections_command import connections_app
from ibm_watsonx_orchestrate.cli.commands.login.login_command import login_app
from ibm_watsonx_orchestrate.cli.commands.tools.tools_command import tools_app
from ibm_watsonx_orchestrate.cli.commands.agents.agents_command import agents_app
from ibm_watsonx_orchestrate.cli.commands.server.server_command import server_app
from ibm_watsonx_orchestrate.cli.commands.chat.chat_command import chat_app
import logging
import logging.config
import yaml


def setup_logging(config_file):

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    logging.config.dictConfig(config)


setup_logging("logging.yaml")

app = typer.Typer(no_args_is_help=True)
app.add_typer(login_app)
app.add_typer(tools_app, name="tools")
app.add_typer(agents_app, name="agents")
app.add_typer(server_app, name="server")
app.add_typer(chat_app, name="chat")
app.add_typer(connections_app, name="connections")

if __name__ == "__main__":
    app()
