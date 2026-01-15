import json
import logging
import sys
from pathlib import Path
from typing import Optional, List, Any, Dict

import rich
import yaml
from pydantic import ValidationError

from ibm_watsonx_orchestrate.agent_builder.channels import TwilioWhatsappChannel, TwilioSMSChannel, SlackChannel, \
    BaseChannel, ChannelLoader, GenesysBotConnectorChannel, FacebookChannel, TeamsChannel
from ibm_watsonx_orchestrate.agent_builder.channels.types import ChannelType
from ibm_watsonx_orchestrate.cli.common import ListFormats
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient
from ibm_watsonx_orchestrate.client.channels.channels_client import ChannelsClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client, is_local_dev, is_saas_env
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.cli.commands.channels.channels_common import (
    block_local_dev,
    check_local_dev_block,
    get_agent_id_by_name as common_get_agent_id_by_name,
    get_environment_id as common_get_environment_id,
    build_local_webhook_url,
    build_saas_webhook_url,
)

logger = logging.getLogger(__name__)


class ChannelsController:
    """Unified controller for all channel operations (CRUD, utilities, and webchat)."""

    def __init__(self):
        self.channels_client = None
        self.agent_client = None

    def _check_local_dev_block(self, enable_developer_mode: bool = False) -> None:
        """Check if channel operations should be blocked in local dev."""
        check_local_dev_block(enable_developer_mode, "Channel")

    def get_channels_client(self) -> ChannelsClient:
        """Get or create the channels client instance."""
        if not self.channels_client:
            self.channels_client = instantiate_client(ChannelsClient)
        return self.channels_client

    def get_agent_client(self) -> AgentClient:
        """Get or create the agent client instance."""
        if not self.agent_client:
            self.agent_client = instantiate_client(AgentClient)
        return self.agent_client

    # Alias for backward compatibility
    def get_native_client(self):
        """Alias for get_agent_client() for backward compatibility."""
        return self.get_agent_client()

    def get_channel_api_path(self, channel_type: str) -> str:
        """Convert channel type to API path.
        Some channel types have different API paths than their type name.

        Args:
            channel_type: Channel type (e.g., 'byo_slack')

        Returns:
            API path for the channel type
        """
        # Mapping for channel types that differ from their API paths
        channel_type_to_api_path = {
            'byo_slack': 'slack',
        }
        return channel_type_to_api_path.get(channel_type, channel_type)

    def get_agent_id_by_name(self, agent_name: str) -> str:
        """Look up agent ID by agent name."""
        client = self.get_agent_client()
        return common_get_agent_id_by_name(client, agent_name)

    def get_environment_id(self, agent_name: str, env: str):
        """Get environment ID by agent name and environment name (draft/live)."""
        agent_client = self.get_agent_client()
        return common_get_environment_id(agent_client, agent_name, env)

    def import_channel(self, file: str) -> List[BaseChannel]:
        """Import channel configuration(s) from YAML, JSON, or Python file.

        Args:
            file: Path to the channel configuration file (.yaml, .yml, .json, or .py)

        Returns:
            List of Channel objects (TwilioWhatsappChannel, WebchatChannel, etc.)
            For spec files (YAML/JSON), returns a list with a single channel.
            For Python files, returns all Channel instances found in the file.
        """
        file_path = Path(file)

        if not file_path.exists():
            logger.error(f"File not found: {file}")
            sys.exit(1)

        try:
            # Handle Python files with from_python, spec files with from_spec
            if file.endswith('.py'):
                channels = ChannelLoader.from_python(file)
                if not channels:
                    logger.error("Python file must define at least one BaseChannel instance.")
                    sys.exit(1)
                return channels
            else:
                # Spec files return single channel, wrap in list for consistency
                return [ChannelLoader.from_spec(file)]
        except BadRequest as e:
            logger.error(f"Failed to load channel: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to validate channel configuration: {e}")
            sys.exit(1)

    def create_channel_from_args(
        self,
        channel_type: ChannelType,
        name: str,
        description: Optional[str] = None,
        output_file: Optional[str] = None,
        **channel_fields
    ) -> BaseChannel:
        """Create a channel from CLI arguments.

        Args:
            channel_type: Type of channel
            name: Channel name
            description: Optional channel description
            output_file: If provided, write spec to this file instead of creating
            **channel_fields: Channel-specific fields (e.g., account_sid, auth_token for Twilio)

        Returns:
            Channel object

        Raises:
            SystemExit if validation fails or required fields missing
        """

        # Webchat channels work differently - they don't require explicit creation
        if channel_type == ChannelType.WEBCHAT:
            logger.error(
                "Webchat channels cannot be created using the 'create' command.\n"
                "Webchat is automatically available for all agents.\n"
                "To generate webchat embed code, use:\n"
                "  orchestrate channels webchat embed --agent-name <agent_name> --env <draft|live>"
            )
            sys.exit(1)

        channel_class_map = {
            ChannelType.TWILIO_WHATSAPP: TwilioWhatsappChannel,
            ChannelType.TWILIO_SMS: TwilioSMSChannel,
            ChannelType.SLACK: SlackChannel,
            ChannelType.GENESYS_BOT_CONNECTOR: GenesysBotConnectorChannel,
            ChannelType.FACEBOOK: FacebookChannel,
            ChannelType.TEAMS: TeamsChannel,
        }

        try:
            channel_class = channel_class_map.get(channel_type)

            if not channel_class:
                logger.error(f"Unsupported channel type for CLI creation: '{channel_type}'. Use 'import' command with a file for this channel type.")
                sys.exit(1)

            # Create channel instance with all provided fields
            channel = channel_class(
                name=name,
                description=description,
                **channel_fields
            )

            # If output file specified, write to file
            if output_file:
                output_path = Path(output_file)
                if output_path.suffix not in ['.yaml', '.yml']:
                    logger.error(f"Output file must have .yaml or .yml extension, got: {output_path.suffix}")
                    sys.exit(1)

                with safe_open(output_file, 'w') as f:
                    yaml.dump(
                        channel.model_dump(
                            exclude_none=True,
                            exclude=channel.SERIALIZATION_EXCLUDE
                        ),
                        f,
                        sort_keys=False,
                        default_flow_style=False,
                        allow_unicode=True
                    )
                logger.info(f"Channel specification written to '{output_file}'")

            return channel

        except ValidationError as e:
            # Handle Pydantic validation errors
            logger.error("Validation failed:")
            for error in e.errors():
                field = '.'.join(str(loc) for loc in error['loc'])
                msg = error['msg']
                logger.error(f"  {field}: {msg}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to create channel from arguments: {e}")
            sys.exit(1)

    @block_local_dev()
    def list_channels_agent(
        self,
        agent_id: str,
        environment_id: str,
        channel_type: Optional[ChannelType] = None,
        verbose: bool = False,
        format: Optional[ListFormats] = None,
        agent_name: str = None,
    ) -> List[Dict[str, Any]] | str | None:
        """List channels for an agent environment.

        Args:
            agent_id: Agent identifier (UUID)
            environment_id: Environment identifier (UUID)
            channel_type: Optional filter by channel type
            verbose: If True, show full JSON output
            format: Output format (table, json)
            agent_name: Optional agent name for display purposes
            env: Optional environment name for display purposes

        Returns:
            List of channel dictionaries or formatted output
        """
        # Check if trying to list webchat channels specifically
        if channel_type == ChannelType.WEBCHAT:
            logger.error(
                "Webchat channels cannot be listed via the channels API.\n"
                "Webchat is automatically available for all agents.\n"
                "To generate webchat embed code, use:\n"
                "  orchestrate channels webchat embed --agent-name <agent_name> --env <draft|live>"
            )
            sys.exit(1)

        client = self.get_channels_client()

        # Convert channel type to API path if provided
        api_path = self.get_channel_api_path(channel_type) if channel_type else None

        try:
            channels = client.list(agent_id, environment_id, api_path)
        except Exception as e:
            logger.error(f"Failed to list channels: {e}")
            sys.exit(1)

        if not channels:
            logger.info("No channels found")
            return []

        if verbose:
            rich.print_json(json.dumps(channels, indent=2))
            return channels

        table = rich.table.Table(
            show_header=True,
            header_style="bold white",
            title=f"Channels for Agent '{agent_name}' (id: {agent_id})",
            show_lines=True
        )

        columns = {
            "Name": {"overflow": "fold"},
            "Type": {},
            "ID": {"overflow": "fold"},
            "Created": {"overflow": "fold"},
        }

        for column in columns:
            table.add_column(column, **columns[column])

        for channel in channels:
            table.add_row(
                channel.get('name', '<no name>'),
                channel.get('channel', ''),
                str(channel.get('id', '')),
                channel.get('created_on', '')
            )

        if format == ListFormats.JSON:
            return channels

        console = rich.console.Console()
        console.print(table)
        return channels

    def resolve_channel_id(
        self,
        agent_id: str,
        environment_id: str,
        channel_type: ChannelType,
        channel_id: Optional[str] = None,
        channel_name: Optional[str] = None
    ) -> str:
        """Resolve channel ID from either ID or name, or validate both match.

        Args:
            agent_id: Agent identifier
            environment_id: Environment identifier
            channel_type: Channel type
            channel_id: Optional channel ID
            channel_name: Optional channel name

        Returns:
            Resolved channel ID
        """
        if not channel_id and not channel_name:
            logger.error("Either --id or --name must be provided")
            sys.exit(1)

        client = self.get_channels_client()

        # Convert channel type to API path
        api_path = self.get_channel_api_path(channel_type)

        # If both provided, validate they match
        if channel_id and channel_name:
            try:
                channel = client.get(agent_id, environment_id, api_path, channel_id)
                if not channel:
                    logger.error(f"Channel with ID '{channel_id}' not found")
                    sys.exit(1)

                actual_name = channel.get('name')
                if actual_name != channel_name:
                    logger.error(f"Channel ID '{channel_id}' has name '{actual_name}', not '{channel_name}'")
                    sys.exit(1)

                return channel_id

            except Exception as e:
                logger.error(f"Failed to validate channel: {e}")
                sys.exit(1)

        if channel_id:
            return channel_id

        # Resolve by channel name
        try:
            channels = client.list(agent_id, environment_id, api_path)
            matching_channels = [ch for ch in channels if ch.get('name') == channel_name]

            if not matching_channels:
                logger.error(f"Channel with name '{channel_name}' not found")
                sys.exit(1)

            if len(matching_channels) > 1:
                logger.error(f"Multiple channels with name '{channel_name}' found. Use --id to specify which one.")
                sys.exit(1)

            return matching_channels[0]['id']

        except Exception as e:
            logger.error(f"Failed to resolve channel: {e}")
            sys.exit(1)

    @block_local_dev()
    def get_channel(
        self,
        agent_id: str,
        environment_id: str,
        channel_type: ChannelType,
        channel_id: str,
        verbose: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a specific channel by ID.

        Args:
            agent_id: Agent identifier
            environment_id: Environment identifier
            channel_type: Channel type
            channel_id: Channel identifier
            verbose: If True, show full JSON output

        Returns:
            Channel dictionary or None if not found
        """
        # Check if trying to get a webchat channel
        if channel_type == ChannelType.WEBCHAT:
            logger.error(
                "Webchat channels cannot be retrieved via the channels API.\n"
                "Webchat is automatically available for all agents.\n"
                "To generate webchat embed code, use:\n"
                "  orchestrate channels webchat embed --agent-name <agent_name> --env <draft|live>"
            )
            sys.exit(1)

        client = self.get_channels_client()

        # Convert channel type to API path
        api_path = self.get_channel_api_path(channel_type)

        try:
            channel = client.get(agent_id, environment_id, api_path, channel_id)
        except Exception as e:
            logger.error(f"Failed to get channel: {e}")
            sys.exit(1)

        if not channel:
            logger.error(f"Channel not found: {channel_id}")
            sys.exit(1)

        if verbose:
            rich.print_json(json.dumps(channel, indent=2))
        else:
            rich.print(f"Channel: {channel.get('name', channel_id)}")
            rich.print(f"  Type: {channel.get('channel')}")
            rich.print(f"  ID: {channel.get('id')}")
            if channel.get('description'):
                rich.print(f"  Description: {channel.get('description')}")

        return channel

    def create_channel(
        self,
        agent_id: str,
        environment_id: str,
        channel: BaseChannel
    ) -> str:
        """Create a new channel.

        Args:
            agent_id: Agent identifier
            environment_id: Environment identifier
            channel: Channel configuration object

        Returns:
            Created channel ID

        Raises:
            SystemExit if a channel of the same type already exists in the same environment
        """
        client = self.get_channels_client()

        try:
            # Check if a channel of this type already exists in this environment
            # Convert channel type to API path for the list call
            api_path = self.get_channel_api_path(channel.channel)
            existing_channels = client.list(agent_id, environment_id, api_path)
            if existing_channels:
                logger.error(
                    f"A channel of type '{channel.channel}' already exists in this environment. "
                    f"Only one channel per type is allowed per environment. "
                    f"To use multiple channels of the same type, create them in different environments (draft/live)."
                )
                sys.exit(1)
        except Exception:
            # If list fails (e.g., 404 for unopened endpoint), continue with creation, WILL support these endpoints soon
            pass

        try:
            result = client.create(agent_id, environment_id, channel)
            channel_id = result.get('id')

            logger.info(f"Successfully created channel '{channel.name or '<unnamed>'}'. id: '{channel_id}'")

            return channel_id

        except Exception as e:
            logger.error(f"Failed to create channel: {e}")
            sys.exit(1)

    def update_channel(
        self,
        agent_id: str,
        environment_id: str,
        channel_id: str,
        channel: BaseChannel,
        partial: bool = True
    ) -> Dict[str, Any]:
        """Update an existing channel.

        Args:
            agent_id: Agent identifier
            environment_id: Environment identifier
            channel_id: Channel identifier to update
            channel: Channel configuration with updates
            partial: If True, only update explicitly set fields

        Returns:
            Updated channel dictionary
        """
        client = self.get_channels_client()

        try:
            result = client.update(agent_id, environment_id, channel_id, channel, partial)

            logger.info(f"Successfully updated channel '{result.get('name', '<unnamed>')}'. id: '{channel_id}'")

            return result

        except Exception as e:
            logger.error(f"Failed to update channel: {e}")
            sys.exit(1)

    def _build_local_event_url(
        self,
        agent_id: str,
        environment_id: str,
        channel_api_path: str,
        channel_id: str
    ) -> str:
        """Build event URL for local development environment.

        Args:
            agent_id: Agent identifier
            environment_id: Environment identifier
            channel_api_path: Channel API path
            channel_id: Channel identifier

        Returns:
            Local event URL path
        """
        return build_local_webhook_url(agent_id, environment_id, channel_api_path, channel_id, "runs")

    def _build_saas_event_url(
        self,
        client,
        agent_id: str,
        environment_id: str,
        channel_api_path: str,
        channel_id: str
    ) -> str:
        """Build event URL for SaaS environment.

        Args:
            client: ChannelsClient instance
            agent_id: Agent identifier
            environment_id: Environment identifier
            channel_api_path: Channel API path
            channel_id: Channel identifier

        Returns:
            Full SaaS event URL
        """
        return build_saas_webhook_url(
            client.base_url,
            client.get_subscription_id(),
            agent_id,
            environment_id,
            channel_api_path,
            channel_id,
            "events"
        )

    def get_channel_event_url(
        self,
        agent_id: str,
        environment_id: str,
        channel_api_path: str,
        channel_id: str
    ) -> str:
        """Generate the full event URL for a channel.

        Args:
            agent_id: Agent identifier
            environment_id: Environment identifier
            channel_api_path: Channel API path (e.g., 'slack', 'twilio_whatsapp')
            channel_id: Channel identifier

        Returns:
            Full event URL in the format:
            - SaaS: https://channels.{environment}/tenants/{subscription_id}_{instance_id}/agents/{agent_id}/environments/{environment_id}/channels/{channel_api_path}/{channel_id}/events
            - Local: /v1/agents/{agent_id}/environments/{environment_id}/channels/{channel_api_path}/{channel_id}/runs
        """
        client = self.get_channels_client()

        # Check if this is a local environment
        if is_local_dev(client.base_url):
            return self._build_local_event_url(agent_id, environment_id, channel_api_path, channel_id)

        # Build SaaS environment URL
        return self._build_saas_event_url(client, agent_id, environment_id, channel_api_path, channel_id)

    @block_local_dev()
    def publish_or_update_channel(
        self,
        agent_id: str,
        environment_id: str,
        channel: BaseChannel
    ) -> str:
        """Create or update a channel.

        If a channel with the same name exists, update it.
        Otherwise, create a new channel.

        Args:
            agent_id: Agent identifier
            environment_id: Environment identifier
            channel: Channel configuration

        Returns:
            Event URL for the channel
        """
        # Webchat channels work differently - they don't require explicit creation
        if channel.channel == ChannelType.WEBCHAT:
            logger.warning(
                "Webchat channels cannot be created or updated via the channels API.\n"
                "Webchat is automatically available for all agents.\n"
                "To generate webchat embed code, use:\n"
                "  orchestrate channels webchat embed --agent-name <agent_name> --env <draft|live>"
            )
            # Return a placeholder URL since webchat doesn't have a traditional event URL
            return f"Webchat is available for agent {agent_id} in environment {environment_id}"

        client = self.get_channels_client()

        # Try to find existing channel by name
        existing_channel = None
        if channel.name:
            try:
                # Convert channel type to API path for the list call
                api_path = self.get_channel_api_path(channel.channel)
                channels = client.list(agent_id, environment_id, api_path)
                for ch in channels:
                    if ch.get('name') == channel.name:
                        existing_channel = ch
                        break
            except Exception as e:
                logger.warning(f"Could not list existing channels: {e}")

        if existing_channel:
            logger.info(f"Found existing channel '{channel.name}', updating...")
            self.update_channel(
                agent_id,
                environment_id,
                existing_channel['id'],
                channel,
                partial=True
            )
            channel_id = existing_channel['id']
        else:
            logger.info(f"Creating new channel '{channel.name or '<unnamed>'}'...")
            channel_id = self.create_channel(agent_id, environment_id, channel)

        # Generate and log the event URL
        event_url = self.get_channel_event_url(agent_id, environment_id, channel.get_api_path(), channel_id)
        logger.info(f"Event URL: {event_url}")

        return event_url

    @block_local_dev()
    def export_channel(
        self,
        agent_id: str,
        environment_id: str,
        channel_type: ChannelType,
        channel_id: str,
        output_path: str,
        zip_file_out: Optional[Any] = None
    ) -> None:
        """Export a channel to a YAML file or zip.

        Args:
            agent_id: Agent identifier
            environment_id: Environment identifier
            channel_type: Channel type
            channel_id: Channel identifier to export
            output_path: Path where the YAML file should be saved (or path within zip)
            zip_file_out: Optional ZipFile object for recursive export
        """
        from pathlib import Path
        from io import BytesIO

        output_file = Path(output_path)
        output_file_extension = output_file.suffix

        # Validate file extension
        if output_file_extension not in [".yaml", ".yml"]:
            logger.error(f"Output file must end with '.yaml' or '.yml'. Provided file '{output_path}' ends with '{output_file_extension}'")
            sys.exit(1)

        # Get the channel
        client = self.get_channels_client()

        # Convert channel type to API path
        api_path = self.get_channel_api_path(channel_type)

        try:
            channel = client.get(agent_id, environment_id, api_path, channel_id)
        except Exception as e:
            if zip_file_out:
                logger.warning(f"Failed to get channel: {e}")
                return
            logger.error(f"Failed to get channel: {e}")
            sys.exit(1)

        if not channel:
            if zip_file_out:
                logger.warning(f"Channel not found: {channel_id}")
                return
            logger.error(f"Channel not found: {channel_id}")
            sys.exit(1)

        # Remove response-only fields before exporting
        # 'id' is also excluded as it's an API response field
        export_data = {k: v for k, v in channel.items() if k not in BaseChannel.SERIALIZATION_EXCLUDE and k != 'id'}

        # Write to YAML file or zip
        try:
            if zip_file_out:
                # Export to zip (for recursive agent export)
                channel_yaml = yaml.dump(export_data, sort_keys=False, default_flow_style=False, allow_unicode=True)
                channel_yaml_bytes = channel_yaml.encode("utf-8")
                channel_yaml_file = BytesIO(channel_yaml_bytes)
                zip_file_out.writestr(output_path, channel_yaml_file.getvalue())
            else:
                # Export to standalone file
                with safe_open(output_path, 'w') as outfile:
                    yaml.dump(export_data, outfile, sort_keys=False, default_flow_style=False, allow_unicode=True)

            logger.info(f"Exported channel '{channel.get('name', channel_id)}' to '{output_path}'")

        except Exception as e:
            if zip_file_out:
                logger.warning(f"Failed to write export file: {e}")
                return
            logger.error(f"Failed to write export file: {e}")
            sys.exit(1)

    @block_local_dev()
    def delete_channel(
        self,
        agent_id: str,
        environment_id: str,
        channel_type: ChannelType,
        channel_id: str
    ) -> None:
        """Delete a channel.

        Args:
            agent_id: Agent identifier
            environment_id: Environment identifier
            channel_type: Channel type
            channel_id: Channel identifier to delete
        """
        client = self.get_channels_client()

        # Convert channel type to API path
        api_path = self.get_channel_api_path(channel_type)

        try:
            client.delete(agent_id, environment_id, api_path, channel_id)

            logger.info(f"Successfully deleted channel '{channel_id}'")

        except Exception as e:
            logger.error(f"Failed to delete channel: {e}")
            sys.exit(1)
            
    def list_channels(self):
        """List all supported channel types (enum values)."""
        table = rich.table.Table(show_header=True, header_style="bold white", show_lines=True)
        columns = ["Channel"]
        for col in columns:
            table.add_column(col)

        for channel in ChannelType.__members__.values():
            table.add_row(channel.value)

        console = rich.console.Console()
        console.print(table)
