import typer
from typing import Optional
from ibm_watsonx_orchestrate.cli.commands.channels.channels_controller import ChannelsController
from ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_command import channel_webchat
from ibm_watsonx_orchestrate.cli.commands.channels.types import EnvironmentType
from ibm_watsonx_orchestrate.cli.commands.channels.channels_common import parse_field
from ibm_watsonx_orchestrate.cli.common import ListFormats
from ibm_watsonx_orchestrate.agent_builder.channels.types import ChannelType

channel_app = typer.Typer(no_args_is_help=True)

channel_app.add_typer(
    channel_webchat,
    name="webchat",
    help="Generate webchat embed code snippets. Usage: 'orchestrate channels webchat embed --agent-name some_agent --env live'"
)

# Initialize controller
controller = ChannelsController()

@channel_app.command(name="list", help="List supported channel types")
def list_channel():
    controller.list_channels()


@channel_app.command(name="import", help="Import a channel configuration from a file")
def import_channel(
        agent_name: str = typer.Option(..., "--agent-name", help="Agent name"),
        env: EnvironmentType = typer.Option(..., "--env", "-e", help="Environment name (draft or live)"),
        file: str = typer.Option(..., "--file", "-f", help="Path to channel configuration file (YAML, JSON, or Python)"),
        enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """Import channel(s) from a configuration file (creates or updates by name)."""
    agent_id = controller.get_agent_id_by_name(agent_name)
    environment_id = controller.get_environment_id(agent_name, env)
    channels = controller.import_channel(file)

    # Import all channels from the file
    for channel in channels:
        controller.publish_or_update_channel(agent_id, environment_id, channel, enable_developer_mode=enable_developer_mode)



@channel_app.command(name="list-channels", help="List all channel instances configured for a specific agent and environment. (e.g. orchestrate channels list-channels --agent-name chat_core --env draft)")
def list_channels_command(
        agent_name: str = typer.Option(..., "--agent-name", help="Agent name"),
        env: EnvironmentType = typer.Option(..., "--env", "-e", help="Environment name (draft or live)"),
        channel_type: Optional[ChannelType] = typer.Option(None, "--type", "-t", help="Filter by channel type (e.g., twilio_whatsapp)"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full JSON output"),
        format: Optional[ListFormats] = typer.Option(None, "--format", "-f", help="Output format (table, json)"),
        enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """List channels for an agent environment."""
    agent_id = controller.get_agent_id_by_name(agent_name)
    environment_id = controller.get_environment_id(agent_name, env)
    controller.list_channels_agent(agent_id, environment_id, channel_type, verbose, format, agent_name=agent_name, enable_developer_mode=enable_developer_mode)


@channel_app.command(name="get", help="Get details of a specific channel by ID or name")
def get_channel(
        agent_name: str = typer.Option(..., "--agent-name", help="Agent name"),
        env: EnvironmentType = typer.Option(..., "--env", "-e", help="Environment name (draft or live)"),
        channel_type: ChannelType = typer.Option(..., "--type", "-t", help="Channel type (e.g., twilio_whatsapp)"),
        channel_id: Optional[str] = typer.Option(None, "--id", "-i", help="Channel ID (either --id or --name required)"),
        channel_name: Optional[str] = typer.Option(None, "--name", "-n", help="Channel name (either --id or --name required)"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full JSON output"),
        enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """Get a specific channel by ID or name."""
    agent_id = controller.get_agent_id_by_name(agent_name)
    environment_id = controller.get_environment_id(agent_name, env)
    resolved_id = controller.resolve_channel_id(agent_id, environment_id, channel_type, channel_id, channel_name)
    controller.get_channel(agent_id, environment_id, channel_type, resolved_id, verbose, enable_developer_mode=enable_developer_mode)


@channel_app.command(name="create", help="Create a new channel using CLI arguments")
def create_channel(
        agent_name: str = typer.Option(..., "--agent-name", help="Agent name"),
        env: EnvironmentType = typer.Option(..., "--env", "-e", help="Environment name (draft or live)"),
        channel_type: ChannelType = typer.Option(..., "--type", "-t", help="Channel type (e.g., twilio_whatsapp, webchat)"),
        name: str = typer.Option(..., "--name", "-n", help="Channel name"),
        description: Optional[str] = typer.Option(None, "--description", "-d", help="Channel description"),
        field: Optional[list[str]] = typer.Option(None, "--field", "-f", help="Channel-specific field in key=value format (can be used multiple times). Examples: --field account_sid=ACxxx --field twilio_authentication_token=xxx"),
        output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Write the channel spec to a file instead of creating it"),
        enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """Create a new channel using CLI arguments.

    Examples:
        # Create a Twilio WhatsApp channel
        orchestrate channels create --agent-name my_agent --env draft --type twilio_whatsapp --name "WhatsApp Channel" --field account_sid=ACxxx --field twilio_authentication_token=xxx

        # Create a Webchat channel
        orchestrate channels create --agent-name my_agent --env draft --type webchat --name "Web Chat"
    """
    agent_id = controller.get_agent_id_by_name(agent_name)

    # Parse field arguments into a dictionary
    try:
        channel_fields = parse_field(field)
    except ValueError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)

    channel = controller.create_channel_from_args(
        channel_type=channel_type,
        name=name,
        description=description,
        output_file=output_file,
        **channel_fields
    )

    if not output_file:
        environment_id = controller.get_environment_id(agent_name, env)
        controller.publish_or_update_channel(agent_id, environment_id, channel, enable_developer_mode=enable_developer_mode)


@channel_app.command(name="export", help="Export a channel to a YAML file by ID or name")
def export_channel(
        agent_name: str = typer.Option(..., "--agent-name", help="Agent name"),
        env: EnvironmentType = typer.Option(..., "--env", "-e", help="Environment name (draft or live)"),
        channel_type: ChannelType = typer.Option(..., "--type", "-t", help="Channel type (e.g., twilio_whatsapp, webchat)"),
        channel_id: Optional[str] = typer.Option(None, "--id", "-i", help="Channel ID to export"),
        channel_name: Optional[str] = typer.Option(None, "--name", "-n", help="Channel name to export"),
        output: str = typer.Option(..., "--output", "-o", help="Path where the YAML file should be saved"),
        enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """Export a channel configuration to a YAML file."""
    agent_id = controller.get_agent_id_by_name(agent_name)
    environment_id = controller.get_environment_id(agent_name, env)
    resolved_id = controller.resolve_channel_id(agent_id, environment_id, channel_type, channel_id, channel_name)
    controller.export_channel(agent_id, environment_id, channel_type, resolved_id, output, enable_developer_mode=enable_developer_mode)


@channel_app.command(name="delete", help="Delete a channel by ID or name")
def delete_channel(
        agent_name: str = typer.Option(..., "--agent-name", help="Agent name"),
        env: EnvironmentType = typer.Option(..., "--env", "-e", help="Environment name (draft or live)"),
        channel_type: ChannelType = typer.Option(..., "--type", "-t", help="Channel type"),
        channel_id: Optional[str] = typer.Option(None, "--id", "-i", help="Channel ID to delete"),
        channel_name: Optional[str] = typer.Option(None, "--name", "-n", help="Channel name to delete"),
        confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
        enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """Delete a channel by ID or name."""
    agent_id = controller.get_agent_id_by_name(agent_name)
    environment_id = controller.get_environment_id(agent_name, env)
    resolved_id = controller.resolve_channel_id(agent_id, environment_id, channel_type, channel_id, channel_name)

    identifier = channel_name if channel_name else resolved_id
    if not confirm:
        response = typer.confirm(f"Are you sure you want to delete channel '{identifier}'?")
        if not response:
            typer.echo("Deletion cancelled")
            return

    controller.delete_channel(agent_id, environment_id, channel_type, resolved_id, enable_developer_mode=enable_developer_mode)
