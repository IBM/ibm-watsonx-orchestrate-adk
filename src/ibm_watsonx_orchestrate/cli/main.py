import typer

from ibm_watsonx_orchestrate.cli.commands.connections.connections_command import connections_app
from ibm_watsonx_orchestrate.cli.commands.login.login_command import login_app
from ibm_watsonx_orchestrate.cli.commands.settings.settings_command import settings_app
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
app.add_typer(environment_app, name="env", help='Add, remove, or select the activate env other commands will interact with (either your local server or a production instance)')
app.add_typer(agents_app, name="agents", help='Interact with the agents in your active env')
app.add_typer(tools_app, name="tools", help='Interact with the tools in your active env')
app.add_typer(knowledge_bases_app, name="knowledge-bases", help="Upload knowledge your agents can search through to your active env")
app.add_typer(connections_app, name="connections", help='Interact with the agents in your active env')
app.add_typer(server_app, name="server", help='Manipulate your local Orchestrate Developer Edition server [requires an Entitlement]')
app.add_typer(chat_app, name="chat", help='Launch the chat ui for your local Developer Edition server [requires docker pull credentials]')
app.add_typer(models_app, name="models", help='List the available large language models (llms) that can be used in your agent definitions')
app.add_typer(channel_app, name="channels", help="Configure channels where your agent can exist on (such as embedded webchat)")
app.add_typer(settings_app, name="settings", help='Configure the settings for your active env')

if __name__ == "__main__":
    app()
