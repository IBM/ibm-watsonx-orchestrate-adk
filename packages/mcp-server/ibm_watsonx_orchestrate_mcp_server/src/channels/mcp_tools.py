from typing import List, Dict, Any
from ibm_watsonx_orchestrate.cli.commands.channels.channels_controller import ChannelsController
from ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller import ChannelsWebchatController
from ibm_watsonx_orchestrate.agent_builder.channels import ChannelLoader
from ibm_watsonx_orchestrate.agent_builder.channels.types import ChannelType
from ibm_watsonx_orchestrate.cli.common import ListFormats
from ibm_watsonx_orchestrate_mcp_server.utils.common import silent_call
from ibm_watsonx_orchestrate_mcp_server.utils.files.files import get_working_directory_path
from ibm_watsonx_orchestrate_mcp_server.src.channels.types import (
    ListChannelsOptions,
    CreateChannelOptions,
    GetChannelOptions,
    DeleteChannelOptions,
    ExportChannelOptions,
    ImportChannelOptions,
    WebchatEmbedOptions
)


def list_channels(options: ListChannelsOptions) -> List[Dict[str, Any]]:
    """
    List all channels for an agent in a specific environment.

    Args:
        options: Configuration for listing channels including agent_name, environment,
                 optional channel_type filter, and verbose flag

    Returns:
        List of channel dictionaries containing id, name, type, and created_on fields.
        If verbose=True, returns full raw channel specifications.
    """
    controller = ChannelsController()

    agent_id = controller.get_agent_id_by_name(options.agent_name)
    environment_id = controller.get_environment_id(options.agent_name, options.environment)

    format_option = ListFormats.JSON if not options.verbose else None
    channels = silent_call(
        fn=controller.list_channels_agent,
        agent_id=agent_id,
        environment_id=environment_id,
        channel_type=options.channel_type,
        verbose=options.verbose,
        format=format_option
    )

    return channels if channels else []


def create_or_update_channel(options: CreateChannelOptions) -> str:
    """
    Create a new channel or update an existing one by name.
    If a channel with the same name exists, it will be updated.
    Otherwise, a new channel will be created.

    Note: Webchat channels cannot be created via this tool as they are
    automatically available for all agents. Use generate_webchat_embed() instead.

    Args:
        options: Channel configuration including agent_name, environment, channel_type,
                 name, description, and channel_config with type-specific settings

    Returns:
        Success message with the event URL for the channel
    """
    controller = ChannelsController()

    agent_id = controller.get_agent_id_by_name(options.agent_name)
    environment_id = controller.get_environment_id(options.agent_name, options.environment)

    channel = silent_call(
        fn=controller.create_channel_from_args,
        channel_type=options.channel_type,
        name=options.name,
        description=options.description,
        **options.channel_config
    )

    event_url = silent_call(
        fn=controller.publish_or_update_channel,
        agent_id=agent_id,
        environment_id=environment_id,
        channel=channel
    )

    return f"Channel '{options.name}' successfully created/updated. Event URL: {event_url}"


def import_channel(options: ImportChannelOptions) -> str:
    """
    Import channel(s) from a YAML, JSON, or Python file.
    If a channel with the same name already exists, it will be updated.

    Args:
        options: Import configuration including agent_name, environment, and file_path

    Returns:
        Success message with the names and event URLs of imported channels
    """
    controller = ChannelsController()

    agent_id = controller.get_agent_id_by_name(options.agent_name)
    environment_id = controller.get_environment_id(options.agent_name, options.environment)

    working_directory_path = get_working_directory_path(options.file_path)

    channels = silent_call(
        fn=controller.import_channel,
        file=working_directory_path
    )

    channel_info = []
    for channel in channels:
        event_url = silent_call(
            fn=controller.publish_or_update_channel,
            agent_id=agent_id,
            environment_id=environment_id,
            channel=channel
        )
        channel_name = channel.name or "<unnamed>"
        channel_info.append(f"{channel_name} (Event URL: {event_url})")

    channels_str = ", ".join(channel_info)
    return f"Successfully imported {len(channels)} channel(s): {channels_str}"


def export_channel(options: ExportChannelOptions) -> str:
    """
    Export a channel to a YAML file.

    Args:
        options: Export configuration including agent_name, environment, channel_type,
                 channel identifier (id or name), and output_path

    Returns:
        Success message with the output file path
    """
    controller = ChannelsController()

    agent_id = controller.get_agent_id_by_name(options.agent_name)
    environment_id = controller.get_environment_id(options.agent_name, options.environment)

    channel_id = silent_call(
        fn=controller.resolve_channel_id,
        agent_id=agent_id,
        environment_id=environment_id,
        channel_type=options.channel_type,
        channel_id=options.channel_id,
        channel_name=options.channel_name
    )

    working_directory_output_path = get_working_directory_path(options.output_path)

    silent_call(
        fn=controller.export_channel,
        agent_id=agent_id,
        environment_id=environment_id,
        channel_type=options.channel_type,
        channel_id=channel_id,
        output_path=working_directory_output_path
    )

    return f"Channel successfully exported to '{options.output_path}'"


def delete_channel(options: DeleteChannelOptions) -> str:
    """
    Delete a channel from an agent environment.

    Args:
        options: Delete configuration including agent_name, environment, channel_type,
                 and channel identifier (id or name)

    Returns:
        Success message confirming deletion
    """
    controller = ChannelsController()

    agent_id = controller.get_agent_id_by_name(options.agent_name)
    environment_id = controller.get_environment_id(options.agent_name, options.environment)

    channel_id = silent_call(
        fn=controller.resolve_channel_id,
        agent_id=agent_id,
        environment_id=environment_id,
        channel_type=options.channel_type,
        channel_id=options.channel_id,
        channel_name=options.channel_name
    )

    silent_call(
        fn=controller.delete_channel,
        agent_id=agent_id,
        environment_id=environment_id,
        channel_type=options.channel_type,
        channel_id=channel_id
    )

    return f"Channel '{options.channel_name or channel_id}' successfully deleted"


def get_channel(options: GetChannelOptions) -> Dict[str, Any]:
    """
    Get details of a specific channel.

    Args:
        options: Get configuration including agent_name, environment, channel_type,
                 channel identifier (id or name), and verbose flag

    Returns:
        Dictionary containing full channel details including id, name, type,
        configuration, and metadata
    """
    controller = ChannelsController()

    agent_id = controller.get_agent_id_by_name(options.agent_name)
    environment_id = controller.get_environment_id(options.agent_name, options.environment)

    channel_id = silent_call(
        fn=controller.resolve_channel_id,
        agent_id=agent_id,
        environment_id=environment_id,
        channel_type=options.channel_type,
        channel_id=options.channel_id,
        channel_name=options.channel_name
    )

    channel = silent_call(
        fn=controller.get_channel,
        agent_id=agent_id,
        environment_id=environment_id,
        channel_type=options.channel_type,
        channel_id=channel_id,
        verbose=options.verbose
    )

    return channel


def generate_webchat_embed(options: WebchatEmbedOptions) -> str:
    """
    Generate HTML embed code for the webchat channel.
    
    Webchat is automatically available for all agents and does not require 
    explicit creation. This tool generates the HTML/JavaScript code needed 
    to embed the webchat widget in a web page.
    
    Args:
        options: Webchat configuration including agent_name and environment
    
    Returns:
        HTML/JavaScript embed code as a string
    """
    controller = ChannelsWebchatController(
        agent_name=options.agent_name,
        env=options.environment
    )
    
    embed_code = silent_call(fn=controller.create_webchat_embed_code)
    
    return embed_code


def list_channel_types() -> List[str]:
    """
    List all supported channel types available in WatsonX Orchestrate.

    Returns:
        List of channel type strings (e.g., ["webchat", "twilio_whatsapp", "twilio_sms", "byo_slack", "genesys_bot_connector"])
    """
    return [channel.value for channel in ChannelType.__members__.values()]


__tools__ = [
    list_channel_types,
    list_channels,
    create_or_update_channel,
    import_channel,
    export_channel,
    delete_channel,
    get_channel,
    generate_webchat_embed
]
