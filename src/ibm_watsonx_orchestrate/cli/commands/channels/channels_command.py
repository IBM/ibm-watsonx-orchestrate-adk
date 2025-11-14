import typer
from ibm_watsonx_orchestrate.cli.commands.channels import channels_controller
from ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_command import channel_webchat

channel_app = typer.Typer(no_args_is_help=True)

channel_app.add_typer(
    channel_webchat,
    name="webchat",
    help="Integrate with the Webchat Channel, for example exporting an embeddable code snippet can be achieved with the command 'orchestrate channel webchat embed --agent-name=some_agent --env=live'."
)

@channel_app.command(name="list", help="Lists the current supported Channels. A Channel refers to the different platforms you can embed your assistant into, such as web chat: orchestrate channel webchat embed --agent-name=some_agent --env=live")
def list_channel():
    channels_controller.list_channels()
