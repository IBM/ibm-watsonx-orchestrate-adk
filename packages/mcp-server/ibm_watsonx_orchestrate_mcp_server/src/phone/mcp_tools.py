from typing import List, Dict, Any
from ibm_watsonx_orchestrate.cli.commands.phone.phone_controller import PhoneController
from ibm_watsonx_orchestrate.agent_builder.phone.types import PhoneChannelType
from ibm_watsonx_orchestrate.cli.common import ListFormats
from ibm_watsonx_orchestrate_mcp_server.utils.common import silent_call
from ibm_watsonx_orchestrate_mcp_server.utils.files.files import get_working_directory_path
from ibm_watsonx_orchestrate_mcp_server.src.phone.types import (
    ListPhoneConfigsOptions,
    CreatePhoneConfigOptions,
    GetPhoneConfigOptions,
    DeletePhoneConfigOptions,
    ImportPhoneConfigOptions,
    ExportPhoneConfigOptions,
    AttachAgentOptions,
    DetachAgentOptions,
    ListAttachmentsOptions,
    AddPhoneNumberOptions,
    ListPhoneNumbersOptions,
    UpdatePhoneNumberOptions,
    DeletePhoneNumberOptions
)


def list_phone_channel_types() -> List[str]:
    """
    List all supported phone channel types available in WatsonX Orchestrate.

    Supported types:
    - genesys_audio_connector: Genesys Audio Connector integration
    - sip_trunk: SIP trunk integration (supports phone number management)

    Returns:
        List of phone channel type strings (e.g., ["genesys_audio_connector", "sip_trunk"])
    """
    return [channel.value for channel in PhoneChannelType.__members__.values()]


def list_phone_configs(options: ListPhoneConfigsOptions) -> List[Dict[str, Any]]:
    """
    List all phone configs with optional filtering.

    Args:
        options: Configuration for listing phone configs including optional
                 channel_type filter and verbose flag

    Returns:
        List of phone config dictionaries containing id, name, type, description,
        and attached_environments. If verbose=True, returns full raw specifications.
    """
    controller = PhoneController()

    format_option = ListFormats.JSON if not options.verbose else None
    configs = silent_call(
        fn=controller.list_phone_configs,
        channel_type=options.channel_type,
        verbose=options.verbose,
        format=format_option
    )

    return configs if configs else []


def create_or_update_phone_config(options: CreatePhoneConfigOptions) -> str:
    """
    Create a new phone config or update an existing one by name.
    If a phone config with the same name exists, it will be updated.
    Otherwise, a new phone config will be created.

    For Genesys Audio Connector configs, missing credentials (api_key and/or
    client_secret) will be auto-generated. The generated credentials will be
    included in the response and should be saved for configuration in Genesys.

    For SIP trunk configs, the SIP connection information (SIP URI with tenant ID)
    will be included in the response for configuring your SIP trunk provider.

    Args:
        options: Phone config configuration including name, channel_type,
                 description, and channel_config with type-specific settings

    Returns:
        Success message with the phone config ID. For SIP trunk configs, also
        includes the SIP connection information (SIP URI and Tenant ID).

    Example:
        For Genesys Audio Connector (credentials are optional and will be auto-generated):
        {
            "name": "My Phone Config",
            "channel_type": "genesys_audio_connector",
            "description": "Production phone integration",
            "channel_config": {
                "security": {
                    "api_key": "your-api-key",      # Optional - will be auto-generated
                    "client_secret": "your-secret"   # Optional - will be auto-generated
                }
            }
        }

        For SIP Trunk:
        {
            "name": "My SIP Config",
            "channel_type": "sip_trunk",
            "description": "SIP trunk integration",
            "channel_config": {}
        }
    """
    controller = PhoneController()

    channel = silent_call(
        fn=controller.create_phone_config_from_args,
        channel_type=options.channel_type,
        name=options.name,
        description=options.description,
        **options.channel_config
    )

    config_id = silent_call(
        fn=controller.create_or_update_phone_config,
        channel=channel
    )

    message = f"Phone config '{options.name}' successfully created/updated. ID: {config_id}"

    # For Genesys Audio Connector configs, append generated credentials if present
    if options.channel_type == PhoneChannelType.GENESYS_AUDIO_CONNECTOR:
        if hasattr(channel, 'security') and channel.security:
            api_key = channel.security.get('api_key')
            client_secret = channel.security.get('client_secret')

            if api_key or client_secret:
                message += f"\nGENERATED CREDENTIALS - SAVE THESE!"
                message += f"\n\nPlease configure these credentials in:"
                message += f"\n  Genesys Audio Connector > Integration Settings > Credentials tab"
                message += f"\n"
                if api_key:
                    message += f"\n  API Key: {api_key}"
                if client_secret:
                    message += f"\n  Client Secret: {client_secret}"

    # For SIP configs, append SIP connection information
    if options.channel_type == PhoneChannelType.SIP:
        # Get the phone client to access base_url
        phone_client = controller.get_phone_client()
        base_url = phone_client.base_url

        # Get tenant_id
        tenant_id = None
        if '/instances/' in base_url:
            instance_id = base_url.split('/instances/')[1].split('/')[0]
            subscription_id = phone_client.get_subscription_id()
            if subscription_id:
                tenant_id = f"{subscription_id}_{instance_id}"
            else:
                tenant_id = instance_id

        # Get SIP URI using controller's method
        sip_uri_base = silent_call(
            fn=controller._get_sip_uri,
            base_url=base_url
        )

        # Build full SIP URI
        if tenant_id and sip_uri_base:
            full_sip_uri = f"sips:{sip_uri_base}?x-tenant-id={tenant_id}"
            message += f"\n\nSIP Connection Information:"
            message += f"\n  Full SIP URI: {full_sip_uri}"
            message += f"\n\nConfigure this SIP URI in your SIP trunk provider settings."

    return message


def import_phone_config(options: ImportPhoneConfigOptions) -> str:
    """
    Import phone config(s) from a YAML, JSON, or Python file.
    If a phone config with the same name already exists, it will be updated.

    For Genesys Audio Connector configs, missing credentials (api_key and/or
    client_secret) will be auto-generated. The generated credentials will be
    displayed and should be saved for configuration in Genesys.

    For SIP trunk configs, the SIP connection information (SIP URI with tenant ID)
    will be included in the response for configuring your SIP trunk provider.

    Args:
        options: Import configuration including file_path

    Returns:
        Success message with the name of imported phone config. For SIP trunk configs,
        also includes the SIP connection information (SIP URI and Tenant ID).
    """
    controller = PhoneController()

    working_directory_path = get_working_directory_path(options.file_path)

    channel = silent_call(
        fn=controller.import_phone_config,
        file=working_directory_path
    )

    config_id = silent_call(
        fn=controller.create_or_update_phone_config,
        channel=channel
    )

    message = f"Successfully imported phone config '{channel.name}'. ID: {config_id}"

    # For Genesys Audio Connector configs, append generated credentials if present
    if hasattr(channel, 'service_provider') and channel.service_provider == PhoneChannelType.GENESYS_AUDIO_CONNECTOR.value:
        if hasattr(channel, 'security') and channel.security:
            api_key = channel.security.get('api_key')
            client_secret = channel.security.get('client_secret')

            if api_key or client_secret:
                message += f"\nGENERATED CREDENTIALS - SAVE THESE!"
                message += f"\n\nPlease configure these credentials in:"
                message += f"\n  Genesys Audio Connector > Integration Settings > Credentials tab"
                message += f"\n"
                if api_key:
                    message += f"\n  API Key: {api_key}"
                if client_secret:
                    message += f"\n  Client Secret: {client_secret}"

    # For SIP configs, append SIP connection information
    if hasattr(channel, 'service_provider') and channel.service_provider == PhoneChannelType.SIP.value:
        # Get the phone client to access base_url
        phone_client = controller.get_phone_client()
        base_url = phone_client.base_url

        # Get tenant_id
        tenant_id = None
        if '/instances/' in base_url:
            instance_id = base_url.split('/instances/')[1].split('/')[0]
            subscription_id = phone_client.get_subscription_id()
            if subscription_id:
                tenant_id = f"{subscription_id}_{instance_id}"
            else:
                tenant_id = instance_id

        # Get SIP URI using controller's method
        sip_uri_base = silent_call(
            fn=controller._get_sip_uri,
            base_url=base_url
        )

        # Build full SIP URI
        if tenant_id and sip_uri_base:
            full_sip_uri = f"sips:{sip_uri_base}?x-tenant-id={tenant_id}"
            message += f"\n\nSIP Connection Information:"
            message += f"\n  Full SIP URI: {full_sip_uri}"
            message += f"\n\nConfigure this SIP URI in your SIP trunk provider settings."

    return message


def export_phone_config(options: ExportPhoneConfigOptions) -> str:
    """
    Export a phone config to a YAML file.

    Args:
        options: Export configuration including config identifier (either id or name must be provided)
                 and output_path

    Returns:
        Success message with the output file path
    """
    controller = PhoneController()

    resolved_id = silent_call(
        fn=controller.resolve_config_id,
        config_id=options.config_id,
        config_name=options.config_name
    )

    working_directory_output_path = get_working_directory_path(options.output_path)

    silent_call(
        fn=controller.export_phone_config,
        config_id=resolved_id,
        output_path=working_directory_output_path
    )

    return f"Phone config successfully exported to '{options.output_path}'"


def get_phone_config(options: GetPhoneConfigOptions) -> Dict[str, Any]:
    """
    Get details of a specific phone config.

    Args:
        options: Get configuration including config identifier (either id or name must be provided)
                 and verbose flag

    Returns:
        Dictionary containing full phone config details including id, name, type,
        configuration, attached_environments, and metadata
    """
    controller = PhoneController()

    resolved_id = silent_call(
        fn=controller.resolve_config_id,
        config_id=options.config_id,
        config_name=options.config_name
    )

    config = silent_call(
        fn=controller.get_phone_config,
        config_id=resolved_id,
        verbose=options.verbose
    )

    return config


def delete_phone_config(options: DeletePhoneConfigOptions) -> str:
    """
    Delete a phone config.

    Args:
        options: Delete configuration including config identifier (either id or name must be provided)

    Returns:
        Success message confirming deletion
    """
    controller = PhoneController()

    resolved_id = silent_call(
        fn=controller.resolve_config_id,
        config_id=options.config_id,
        config_name=options.config_name
    )

    silent_call(
        fn=controller.delete_phone_config,
        config_id=resolved_id
    )

    identifier = options.config_name if options.config_name else resolved_id
    return f"Phone config '{identifier}' successfully deleted"


def attach_agent_to_phone_config(options: AttachAgentOptions) -> str:
    """
    Attach an agent/environment to a phone config. 

    Only for Genesys Audio Connector.
    This operation is not supported for SIP trunk.

    Multiple agents can be attached to the same phone config.
    After attachment, webhook configuration will be provided for integration.

    Args:
        options: Attachment configuration including config identifier (either id or name must be provided),
                 agent_name, and environment

    Returns:
        Success message with webhook configuration details
    """
    controller = PhoneController()

    resolved_config_id = silent_call(
        fn=controller.resolve_config_id,
        config_id=options.config_id,
        config_name=options.config_name
    )

    agent_id = silent_call(
        fn=controller.get_agent_id_by_name,
        agent_name=options.agent_name
    )

    environment_id = silent_call(
        fn=controller.get_environment_id,
        agent_name=options.agent_name,
        env=options.environment
    )

    silent_call(
        fn=controller.attach_agent_to_config,
        config_id=resolved_config_id,
        agent_id=agent_id,
        environment_id=environment_id,
        agent_name=options.agent_name,
        env_name=options.environment
    )

    config = silent_call(
        fn=controller.get_phone_config,
        config_id=resolved_config_id,
        verbose=False
    )

    channel_type = config.get('service_provider', 'genesys_audio_connector')
    webhook_url = controller.get_phone_webhook_url(
        agent_id, environment_id, channel_type, resolved_config_id
    )

    if isinstance(webhook_url, dict):
        return (
            f"Successfully attached agent '{options.agent_name}' / environment '{options.environment}' "
            f"to phone config.\n\n"
            f"Webhook Configuration:\n"
            f"  Genesys Audio Connect URI: {webhook_url['audio_connect_uri']}\n"
            f"  Connector ID: {webhook_url['connector_id']}"
        )
    else:
        return (
            f"Successfully attached agent '{options.agent_name}' / environment '{options.environment}' "
            f"to phone config.\n\n"
            f"Webhook URL: {webhook_url}"
        )


def detach_agent_from_phone_config(options: DetachAgentOptions) -> str:
    """
    Detach an agent/environment from a phone config.

    Only for Genesys Audio Connector.
    This operation is not supported for SIP trunk.

    Args:
        options: Detachment configuration including config identifier (either id or name must be provided),
                 agent_name, and environment

    Returns:
        Success message confirming detachment
    """
    controller = PhoneController()

    resolved_config_id = silent_call(
        fn=controller.resolve_config_id,
        config_id=options.config_id,
        config_name=options.config_name
    )

    agent_id = silent_call(
        fn=controller.get_agent_id_by_name,
        agent_name=options.agent_name
    )

    environment_id = silent_call(
        fn=controller.get_environment_id,
        agent_name=options.agent_name,
        env=options.environment
    )

    silent_call(
        fn=controller.detach_agent_from_config,
        config_id=resolved_config_id,
        agent_id=agent_id,
        environment_id=environment_id,
        agent_name=options.agent_name,
        env_name=options.environment
    )

    return f"Successfully detached agent '{options.agent_name}' / environment '{options.environment}' from phone config"


def list_phone_config_attachments(options: ListAttachmentsOptions) -> List[Dict[str, Any]]:
    """
    List all agent/environment attachments for a phone config.

    Only for Genesys Audio Connector.
    This operation is not supported for SIP trunk.

    Args:
        options: List configuration including config identifier (either id or name must be provided)

    Returns:
        List of attachment dictionaries containing agent_id, agent_name,
        environment_id, and environment_name
    """
    controller = PhoneController()

    resolved_config_id = silent_call(
        fn=controller.resolve_config_id,
        config_id=options.config_id,
        config_name=options.config_name
    )

    attachments = silent_call(
        fn=controller.list_attachments,
        config_id=resolved_config_id,
        format=ListFormats.JSON
    )

    return attachments if attachments else []


def add_phone_number(options: AddPhoneNumberOptions) -> str:
    """
    Add a phone number to a SIP trunk phone config.

    Phone numbers can only be added to SIP trunk phone configs.
    This operation is not supported for Genesys Audio Connector configs.

    Args:
        options: Configuration including config identifier (either id or name must be provided),
                 phone number, optional description, and optional agent/environment association

    Returns:
        Success message confirming the phone number was added

    Example:
        {
            "config_name": "My SIP Trunk",
            "number": "+14155551234",
            "description": "Main office line",
            "agent_name": "CustomerService",
            "environment": "live"
        }
    """
    controller = PhoneController()

    resolved_config_id = silent_call(
        fn=controller.resolve_config_id,
        config_id=options.config_id,
        config_name=options.config_name
    )

    # Resolve agent and environment if provided
    agent_id = None
    environment_id = None
    if options.agent_name and options.environment:
        agent_id = silent_call(
            fn=controller.get_agent_id_by_name,
            agent_name=options.agent_name
        )
        environment_id = silent_call(
            fn=controller.get_environment_id,
            agent_name=options.agent_name,
            env=options.environment
        )

    silent_call(
        fn=controller.add_phone_number,
        config_id=resolved_config_id,
        number=options.number,
        description=options.description,
        agent_id=agent_id,
        environment_id=environment_id
    )

    message = f"Phone number '{options.number}' successfully added to phone config"
    if options.description:
        message += f"\nDescription: {options.description}"
    if options.agent_name and options.environment:
        message += f"\nAssociated with agent '{options.agent_name}' / environment '{options.environment}'"

    return message


def list_phone_numbers(options: ListPhoneNumbersOptions) -> List[Dict[str, Any]]:
    """
    List all phone numbers for a SIP trunk phone config.

    Phone numbers can only be managed for SIP trunk phone configs.
    This operation is not supported for Genesys Audio Connector configs.

    Args:
        options: Configuration including config identifier (either id or name must be provided)

    Returns:
        List of phone number dictionaries containing phone_number, description,
        and optional agent_id/environment_id associations
    """
    controller = PhoneController()

    resolved_config_id = silent_call(
        fn=controller.resolve_config_id,
        config_id=options.config_id,
        config_name=options.config_name
    )

    numbers = silent_call(
        fn=controller.list_phone_numbers,
        config_id=resolved_config_id,
        format=ListFormats.JSON
    )

    return numbers if numbers else []


def update_phone_number(options: UpdatePhoneNumberOptions) -> str:
    """
    Update a phone number's details in a SIP trunk phone config.

    Phone numbers can only be managed for SIP trunk phone configs.
    This operation is not supported for Genesys Audio Connector configs.

    Args:
        options: Configuration including config identifier (either id or name must be provided),
                 current phone number, optional new number, optional new description,
                 and optional agent/environment association

    Returns:
        Success message confirming the phone number was updated

    Example:
        {
            "config_name": "My SIP Trunk",
            "number": "+14155551234",
            "new_number": "+14155555678",
            "description": "Updated office line",
            "agent_name": "Sales",
            "environment": "live"
        }
    """
    controller = PhoneController()

    resolved_config_id = silent_call(
        fn=controller.resolve_config_id,
        config_id=options.config_id,
        config_name=options.config_name
    )

    # Resolve agent and environment if provided
    agent_id = None
    environment_id = None
    if options.agent_name and options.environment:
        agent_id = silent_call(
            fn=controller.get_agent_id_by_name,
            agent_name=options.agent_name
        )
        environment_id = silent_call(
            fn=controller.get_environment_id,
            agent_name=options.agent_name,
            env=options.environment
        )

    silent_call(
        fn=controller.update_phone_number,
        config_id=resolved_config_id,
        number=options.number,
        new_number=options.new_number,
        description=options.description,
        agent_id=agent_id,
        environment_id=environment_id
    )

    message = f"Phone number '{options.number}' successfully updated"
    if options.new_number:
        message += f"\nNew number: {options.new_number}"
    if options.description is not None:
        message += f"\nDescription: {options.description}"
    if options.agent_name and options.environment:
        message += f"\nAssociated with agent '{options.agent_name}' / environment '{options.environment}'"

    return message


def delete_phone_number(options: DeletePhoneNumberOptions) -> str:
    """
    Delete a phone number from a SIP trunk phone config.

    Phone numbers can only be managed for SIP trunk phone configs.
    This operation is not supported for Genesys Audio Connector configs.

    Args:
        options: Configuration including config identifier (either id or name must be provided)
                 and phone number to delete

    Returns:
        Success message confirming the phone number was deleted
    """
    controller = PhoneController()

    resolved_config_id = silent_call(
        fn=controller.resolve_config_id,
        config_id=options.config_id,
        config_name=options.config_name
    )

    silent_call(
        fn=controller.delete_phone_number,
        config_id=resolved_config_id,
        number=options.number
    )

    return f"Phone number '{options.number}' successfully deleted from phone config"


__tools__ = [
    list_phone_channel_types,
    list_phone_configs,
    create_or_update_phone_config,
    import_phone_config,
    export_phone_config,
    get_phone_config,
    delete_phone_config,
    attach_agent_to_phone_config,
    detach_agent_from_phone_config,
    list_phone_config_attachments,
    add_phone_number,
    list_phone_numbers,
    update_phone_number,
    delete_phone_number
]
