import typer
from typing_extensions import Annotated
from ibm_watsonx_orchestrate.cli.commands.channels.types import EnvironmentType
from ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller import ChannelsWebchatController


channel_webchat = typer.Typer(no_args_is_help=True)

@channel_webchat.command(
    name="embed",
    help="Creates an embedded webchat code snippet with the command 'orchestrate channel webchat embed --agent-name=some_agent --env=live"
)
def create_webchat_embed_code(
    agent_name: Annotated[
        str,
        typer.Option(
            '--agent-name',
            '-a',
            help='The name of the agent you wish to have embedded'
        )
    ],
    env: Annotated[
        EnvironmentType,
        typer.Option(
            '--env',
            '-e',
            help='The environment in which your agent resides. This will default to live if no environment is provided'
        )
    ] = EnvironmentType.LIVE,
):
    controller = ChannelsWebchatController(agent_name=agent_name, env=env)
    controller.create_webchat_embed_code()
