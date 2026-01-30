
import typer
import sys

from ibm_watsonx_orchestrate.cli.commands.connections.connections_command import connections_app
from ibm_watsonx_orchestrate.cli.commands.login.login_command import login_app
from ibm_watsonx_orchestrate.cli.commands.settings.settings_command import settings_app
from ibm_watsonx_orchestrate.cli.commands.tools.tools_command import tools_app
from ibm_watsonx_orchestrate.cli.commands.agents.agents_command import agents_app
from ibm_watsonx_orchestrate.cli.commands.server.server_command import server_app
from ibm_watsonx_orchestrate.cli.commands.chat.chat_command import chat_app
from ibm_watsonx_orchestrate.cli.commands.models.models_command import models_app
from ibm_watsonx_orchestrate.cli.commands.environment.environment_command import environment_app
from ibm_watsonx_orchestrate.cli.commands.partners.partners_command import partners_app
from ibm_watsonx_orchestrate.cli.commands.channels.channels_command import channel_app
from ibm_watsonx_orchestrate.cli.commands.phone.phone_command import phone_app
from ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_command import knowledge_bases_app
from ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_command import toolkits_app
from ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_command import evaluation_app
from ibm_watsonx_orchestrate.cli.commands.voice_configurations.voice_configurations_command import voice_configurations_app
from ibm_watsonx_orchestrate.cli.init_helper import init_callback

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    callback=init_callback
)

app.add_typer(login_app)
app.add_typer(environment_app, name="env", help='Add, remove, or select the activate env other commands will interact with (either your local server or a production instance)')
app.add_typer(agents_app, name="agents", help='Interact with the agents in your active env')
app.add_typer(tools_app, name="tools", help='Interact with the tools in your active env')
app.add_typer(toolkits_app, name="toolkits", help="Interact with the toolkits in your active env")
app.add_typer(knowledge_bases_app, name="knowledge-bases", help="Upload knowledge your agents can search through to your active env")
app.add_typer(connections_app, name="connections", help='Interact with the agents in your active env')
app.add_typer(voice_configurations_app, name="voice-configs", help="Configure voice providers to enable voice interaction with your agents")
app.add_typer(server_app, name="server", help='Manipulate your local Orchestrate Developer Edition server [requires entitlement]')
app.add_typer(chat_app, name="chat", help='Launch the chat ui and CLI chat interface for your local Developer Edition server [requires entitlement]')
app.add_typer(models_app, name="models", help='List the available large language models (llms) that can be used in your agent definitions')
app.add_typer(channel_app, name="channels", help="Configure channels where your agent can exist on (such as embedded webchat, whatsapp, etc.)")
app.add_typer(phone_app, name="phone", help="Manage phone configurations (global resources that can be attached to multiple agents)")
app.add_typer(evaluation_app, name="evaluations", help='Evaluate the performance of your agents in your active env')
app.add_typer(settings_app, name="settings", help='Configure the settings for your active env')
app.add_typer(partners_app, name="partners", help='Generate a well-structured, submission-ready agent artifact package for partner-built agents')

if __name__ == "__main__":
    app()
