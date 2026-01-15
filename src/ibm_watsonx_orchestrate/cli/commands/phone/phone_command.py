import typer
from typing import Optional
from ibm_watsonx_orchestrate.cli.commands.phone.phone_controller import PhoneController
from ibm_watsonx_orchestrate.cli.commands.phone.types import PhoneChannelType, EnvironmentType
from ibm_watsonx_orchestrate.cli.commands.channels.channels_common import parse_field
from ibm_watsonx_orchestrate.cli.common import ListFormats

phone_app = typer.Typer(no_args_is_help=True)

controller = PhoneController()

@phone_app.command(name="list", help="List supported phone channel types")
def list_phone_types():
    """List all supported phone channel types."""
    controller.list_phone_channel_types()


@phone_app.command(name="create", help="Create a new phone config using CLI arguments")
def create_phone_config(
    name: str = typer.Option(..., "--name", "-n", help="Phone config name"),
    channel_type: PhoneChannelType = typer.Option(..., "--type", "-t", help="Phone channel type (e.g., genesys_audio_connector)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Phone config description"),
    field: Optional[list[str]] = typer.Option(None, "--field", "-f", help="Config-specific field in key=value format (can be used multiple times)."),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Write the config spec to a file instead of creating it"),
    enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """Create a new phone config using CLI arguments."""
    # Parse field arguments
    # For Genesys Audio Connector: nest api_key and client_secret under 'security'
    # For SIP Trunk: security and other complex fields are passed as JSON
    try:
        if channel_type == PhoneChannelType.GENESYS_AUDIO_CONNECTOR:
            config_fields = parse_field(field, nested_fields=['api_key', 'client_secret'])
        else:
            config_fields = parse_field(field)
    except ValueError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)

    channel = controller.create_phone_config_from_args(
        channel_type=channel_type,
        name=name,
        description=description,
        output_file=output_file,
        **config_fields
    )

    if not output_file:
        controller.create_or_update_phone_config(channel, enable_developer_mode=enable_developer_mode)


@phone_app.command(name="list-configs", help="List all phone configs")
def list_phone_configs(
    channel_type: Optional[PhoneChannelType] = typer.Option(None, "--type", "-t", help="Filter by phone channel type"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full JSON output"),
    format: Optional[ListFormats] = typer.Option(None, "--format", "-f", help="Output format (table, json)"),
    enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """List all phone configs."""
    controller.list_phone_configs(channel_type, verbose, format, enable_developer_mode=enable_developer_mode)


@phone_app.command(name="get", help="Get details of a specific phone config by ID or name")
def get_phone_config(
    config_id: Optional[str] = typer.Option(None, "--id", "-i", help="Phone config ID (either --id or --name required)"),
    config_name: Optional[str] = typer.Option(None, "--name", "-n", help="Phone config name (either --id or --name required)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full JSON output"),
    enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """Get a specific phone config by ID or name."""
    resolved_id = controller.resolve_config_id(config_id, config_name)
    controller.get_phone_config(resolved_id, verbose, enable_developer_mode=enable_developer_mode)


@phone_app.command(name="delete", help="Delete a phone config by ID or name")
def delete_phone_config(
    config_id: Optional[str] = typer.Option(None, "--id", "-i", help="Phone config ID to delete (either --id or --name required)"),
    config_name: Optional[str] = typer.Option(None, "--name", "-n", help="Phone config name to delete (either --id or --name required)"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """Delete a phone config by ID or name."""
    resolved_id = controller.resolve_config_id(config_id, config_name)

    identifier = config_name if config_name else resolved_id
    if not confirm:
        response = typer.confirm(f"Are you sure you want to delete phone config '{identifier}'?")
        if not response:
            typer.echo("Deletion cancelled")
            return

    controller.delete_phone_config(resolved_id, enable_developer_mode=enable_developer_mode)


@phone_app.command(name="import", help="Import a phone config from a file")
def import_phone_config(
    file: str = typer.Option(..., "--file", "-f", help="Path to phone config file (YAML, JSON, or Python)"),
    enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """Import phone config from a configuration file (creates or updates by name)."""
    channel = controller.import_phone_config(file)
    controller.create_or_update_phone_config(channel, enable_developer_mode=enable_developer_mode)


@phone_app.command(name="export", help="Export a phone config to a YAML file by ID or name")
def export_phone_config(
    config_id: Optional[str] = typer.Option(None, "--id", "-i", help="Phone config ID to export"),
    config_name: Optional[str] = typer.Option(None, "--name", "-n", help="Phone config name to export"),
    output: str = typer.Option(..., "--output", "-o", help="Path where the YAML file should be saved"),
    enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """Export a phone config to a YAML file."""
    resolved_id = controller.resolve_config_id(config_id, config_name)
    controller.export_phone_config(resolved_id, output, enable_developer_mode=enable_developer_mode)


@phone_app.command(name="attach", help="Attach an agent/environment to a phone config")
def attach_agent(
    config_id: Optional[str] = typer.Option(None, "--id", "-i", help="Phone config ID (either --id or --name required)"),
    config_name: Optional[str] = typer.Option(None, "--name", "-n", help="Phone config name (either --id or --name required)"),
    agent_name: str = typer.Option(..., "--agent-name", help="Agent name to attach"),
    env: EnvironmentType = typer.Option(..., "--env", "-e", help="Environment name (draft or live)"),
    enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """Attach an agent/environment to an existing phone config.

    Multiple agents can be attached to the same config.

    Examples:
        orchestrate phone attach --name "Phone Support" --agent-name my_agent --env draft
    """
    resolved_config_id = controller.resolve_config_id(config_id, config_name)
    agent_id = controller.get_agent_id_by_name(agent_name)
    environment_id = controller.get_environment_id(agent_name, env)

    # Type assertions to ensure non-None values
    assert agent_id is not None, f"Agent '{agent_name}' not found"
    assert environment_id is not None, f"Environment '{env}' not found for agent '{agent_name}'"

    controller.attach_agent_to_config(
        resolved_config_id,
        agent_id,
        environment_id,
        agent_name,
        env,
        enable_developer_mode=enable_developer_mode
    )


@phone_app.command(name="detach", help="Detach an agent/environment from a phone config")
def detach_agent(
    config_id: Optional[str] = typer.Option(None, "--id", "-i", help="Phone config ID (either --id or --name required)"),
    config_name: Optional[str] = typer.Option(None, "--name", "-n", help="Phone config name (either --id or --name required)"),
    agent_name: str = typer.Option(..., "--agent-name", help="Agent name to detach"),
    env: EnvironmentType = typer.Option(..., "--env", "-e", help="Environment name (draft or live)"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """Detach an agent/environment from a phone config.

    Examples:
        orchestrate phone detach --name "Phone Support" --agent-name my_agent --env draft
    """
    resolved_config_id = controller.resolve_config_id(config_id, config_name)
    agent_id = controller.get_agent_id_by_name(agent_name)
    environment_id = controller.get_environment_id(agent_name, env)

    # Type assertions to ensure non-None values
    assert agent_id is not None, f"Agent '{agent_name}' not found"
    assert environment_id is not None, f"Environment '{env}' not found for agent '{agent_name}'"

    if not confirm:
        response = typer.confirm(f"Are you sure you want to detach agent '{agent_name}' / environment '{env}' from this phone config?")
        if not response:
            typer.echo("Detach cancelled")
            return

    controller.detach_agent_from_config(
        resolved_config_id,
        agent_id,
        environment_id,
        agent_name,
        env,
        enable_developer_mode=enable_developer_mode
    )


@phone_app.command(name="list-attachments", help="List all agent/environment attachments for a phone config")
def list_attachments(
    config_id: Optional[str] = typer.Option(None, "--id", "-i", help="Phone config ID (either --id or --name required)"),
    config_name: Optional[str] = typer.Option(None, "--name", "-n", help="Phone config name (either --id or --name required)"),
    format: Optional[ListFormats] = typer.Option(None, "--format", "-f", help="Output format (table, json)"),
    enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """List all agent/environment pairs attached to a specific phone config."""
    resolved_config_id = controller.resolve_config_id(config_id, config_name)
    controller.list_attachments(resolved_config_id, format, enable_developer_mode=enable_developer_mode)


@phone_app.command(name="add-number", help="Add a phone number to a phone config")
def add_phone_number(
    config_id: Optional[str] = typer.Option(None, "--id", "-i", help="Phone config ID (either --id or --name required)"),
    config_name: Optional[str] = typer.Option(None, "--name", "-n", help="Phone config name (either --id or --name required)"),
    number: str = typer.Option(..., "--number", help="Phone number (E.164 format recommended, e.g., +15551234567)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description for the phone number"),
    agent_name: Optional[str] = typer.Option(None, "--agent-name", help="Agent name to associate with this phone number"),
    env: Optional[EnvironmentType] = typer.Option(None, "--env", "-e", help="Environment (draft or live) to associate with this phone number"),
    enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """Add a phone number to a phone config (SIP channels only)."""
    resolved_config_id = controller.resolve_config_id(config_id, config_name)
    agent_id, environment_id = controller.resolve_agent_and_environment(agent_name, env)
    controller.add_phone_number(resolved_config_id, number, description, agent_id, environment_id, enable_developer_mode=enable_developer_mode)


@phone_app.command(name="list-numbers", help="List all phone numbers for a phone config")
def list_phone_numbers(
    config_id: Optional[str] = typer.Option(None, "--id", "-i", help="Phone config ID (either --id or --name required)"),
    config_name: Optional[str] = typer.Option(None, "--name", "-n", help="Phone config name (either --id or --name required)"),
    format: Optional[ListFormats] = typer.Option(None, "--format", "-f", help="Output format (table, json)"),
    enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """List all phone numbers associated with a phone config (SIP channels only)."""
    resolved_config_id = controller.resolve_config_id(config_id, config_name)
    controller.list_phone_numbers(resolved_config_id, format, enable_developer_mode=enable_developer_mode)


@phone_app.command(name="update-number", help="Update a phone number's details")
def update_phone_number(
    config_id: Optional[str] = typer.Option(None, "--id", "-i", help="Phone config ID (either --id or --name required)"),
    config_name: Optional[str] = typer.Option(None, "--name", "-n", help="Phone config name (either --id or --name required)"),
    number: str = typer.Option(..., "--number", help="Phone number to update"),
    new_number: Optional[str] = typer.Option(None, "--new-number", help="New phone number"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    agent_name: Optional[str] = typer.Option(None, "--agent-name", help="Agent name to associate with this phone number"),
    env: Optional[EnvironmentType] = typer.Option(None, "--env", "-e", help="Environment (draft or live) to associate with this phone number"),
    enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """Update a phone number's details (SIP channels only)."""
    resolved_config_id = controller.resolve_config_id(config_id, config_name)
    agent_id, environment_id = controller.resolve_agent_and_environment(agent_name, env)
    controller.update_phone_number(resolved_config_id, number, new_number, description, agent_id, environment_id, enable_developer_mode=enable_developer_mode)


@phone_app.command(name="delete-number", help="Delete a phone number from a phone config")
def delete_phone_number(
    config_id: Optional[str] = typer.Option(None, "--id", "-i", help="Phone config ID (either --id or --name required)"),
    config_name: Optional[str] = typer.Option(None, "--name", "-n", help="Phone config name (either --id or --name required)"),
    number: str = typer.Option(..., "--number", help="Phone number to delete"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    enable_developer_mode: bool = typer.Option(False, "--enable-developer-mode", hidden=True)
):
    """Remove a phone number from a phone config (SIP channels only)."""
    resolved_config_id = controller.resolve_config_id(config_id, config_name)

    if not confirm:
        response = typer.confirm(f"Are you sure you want to delete phone number '{number}'?")
        if not response:
            typer.echo("Deletion cancelled")
            return

    controller.delete_phone_number(resolved_config_id, number, enable_developer_mode=enable_developer_mode)
