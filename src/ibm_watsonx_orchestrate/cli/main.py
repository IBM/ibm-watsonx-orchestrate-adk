import typer

from ibm_watsonx_orchestrate.cli.commands.connections.connections_command import connections_app
from ibm_watsonx_orchestrate.cli.commands.login.login_command import login_app
from ibm_watsonx_orchestrate.cli.commands.tools.tools_command import tools_app
from ibm_watsonx_orchestrate.cli.commands.agents.agents_command import agents_app
from ibm_watsonx_orchestrate.cli.commands.server.server_command import server_app
from ibm_watsonx_orchestrate.cli.commands.chat.chat_command import chat_app
from ibm_watsonx_orchestrate.cli.commands.models.models_command import models_app
from ibm_watsonx_orchestrate.cli.commands.environment.environment_command import environment_app
from ibm_watsonx_orchestrate.cli.commands.channels.channels_command import channel_app
from ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_command import knowledge_bases_app

app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=False
)
app.add_typer(login_app)
app.add_typer(tools_app, name="tools")
app.add_typer(agents_app, name="agents")
app.add_typer(server_app, name="server")
app.add_typer(chat_app, name="chat")
app.add_typer(connections_app, name="connections")
app.add_typer(models_app, name="models")
app.add_typer(environment_app, name="env")
app.add_typer(channel_app, name="channels")
app.add_typer(knowledge_bases_app, name="knowledge-bases")

if __name__ == "__main__":
    app()
