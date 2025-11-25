import json
import sys
import rich
import yaml
import logging
from typing import Optional, List, Any, Dict
from pathlib import Path
from pydantic import ValidationError

from ibm_watsonx_orchestrate.agent_builder.phone import GenesysAudioConnectorChannel, BasePhoneChannel, PhoneChannelLoader
from ibm_watsonx_orchestrate.cli.commands.phone.types import PhoneChannelType
from ibm_watsonx_orchestrate.client.utils import instantiate_client, is_local_dev
from ibm_watsonx_orchestrate.client.phone.phone_client import PhoneClient
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.cli.common import ListFormats
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.cli.commands.channels.channels_common import (
    block_local_dev,
    check_local_dev_block,
    get_agent_id_by_name as common_get_agent_id_by_name,
    get_environment_id as common_get_environment_id,
    get_agent_name_by_id as common_get_agent_name_by_id,
    build_local_webhook_url,
)

logger = logging.getLogger(__name__)


class PhoneController:
    """Controller for phone config operations (CRUD, attachments, phone numbers)."""

    def __init__(self):
        self.phone_client = None
        self.agent_client = None

    def _check_local_dev_block(self, enable_developer_mode: bool = False) -> None:
        """Check if phone operations should be blocked in local dev."""
        check_local_dev_block(enable_developer_mode, "Phone config")

    def get_phone_client(self) -> PhoneClient:
        """Get or create the phone client instance."""
        if not self.phone_client:
            self.phone_client = instantiate_client(PhoneClient)
        return self.phone_client

    def get_agent_client(self) -> AgentClient:
        """Get or create the agent client instance."""
        if not self.agent_client:
            self.agent_client = instantiate_client(AgentClient)
        return self.agent_client

    def get_agent_id_by_name(self, agent_name: str) -> str:
        """Look up agent ID by agent name."""
        client = self.get_agent_client()
        return common_get_agent_id_by_name(client, agent_name)

    def get_agent_name_by_id(self, agent_id: str) -> str:
        """Look up agent ID by agent name."""
        client = self.get_agent_client()
        return common_get_agent_name_by_id(client, agent_id)

    def get_environment_id(self, agent_name: str, env: str) -> str:
        """Get environment ID by agent name and environment name (draft/live)."""
        agent_client = self.get_agent_client()
        return common_get_environment_id(agent_client, agent_name, env)

    def list_phone_channel_types(self):
        """List all supported phone channel types (enum values)."""
        table = rich.table.Table(show_header=True, header_style="bold white", show_lines=True)
        table.add_column("Phone Channel Type")

        for channel_type in PhoneChannelType.__members__.values():
            table.add_row(channel_type.value)

        console = rich.console.Console()
        console.print(table)

    def resolve_config_id(
        self,
        config_id: Optional[str] = None,
        config_name: Optional[str] = None
    ) -> str:
        """Resolve config ID from either ID or name."""
        if not config_id and not config_name:
            logger.error("Either --id or --name must be provided")
            sys.exit(1)

        if config_id and config_name:
            # Validate they match
            client = self.get_phone_client()
            try:
                config = client.get_phone_channel(config_id)
                if not config:
                    logger.error(f"Phone config with ID '{config_id}' not found")
                    sys.exit(1)

                actual_name = config.get('name')
                if actual_name != config_name:
                    logger.error(f"Phone config ID '{config_id}' has name '{actual_name}', not '{config_name}'")
                    sys.exit(1)

                return config_id
            except Exception as e:
                logger.error(f"Failed to validate phone config: {e}")
                sys.exit(1)

        if config_id:
            return config_id

        # Resolve by name
        try:
            client = self.get_phone_client()
            configs = client.list_phone_channels()
            matching_configs = [c for c in configs if c.get('name') == config_name]

            if not matching_configs:
                logger.error(f"Phone config with name '{config_name}' not found")
                sys.exit(1)

            if len(matching_configs) > 1:
                logger.error(f"Multiple phone configs with name '{config_name}' found. Use --id to specify which one.")
                sys.exit(1)

            return matching_configs[0]['id']
        except Exception as e:
            logger.error(f"Failed to resolve phone config: {e}")
            sys.exit(1)

    def create_phone_config_from_args(
        self,
        channel_type: PhoneChannelType,
        name: str,
        description: Optional[str] = None,
        output_file: Optional[str] = None,
        **channel_fields
    ) -> BasePhoneChannel:
        """Create a phone config from CLI arguments."""
        channel_class_map = {
            PhoneChannelType.GENESYS_AUDIO_CONNECTOR: GenesysAudioConnectorChannel,
        }

        try:
            channel_class = channel_class_map.get(channel_type)

            if not channel_class:
                logger.error(f"Unsupported phone channel type: '{channel_type}'")
                sys.exit(1)

            # Create channel instance
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
                logger.info(f"Phone config specification written to '{output_file}'")

            return channel

        except ValidationError as e:
            logger.error("Validation failed:")
            for error in e.errors():
                field = '.'.join(str(loc) for loc in error['loc'])
                msg = error['msg']
                logger.error(f"  {field}: {msg}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to create phone config from arguments: {e}")
            sys.exit(1)

    @block_local_dev()
    def create_phone_config(self, channel: BasePhoneChannel) -> str:
        """Create a new phone config."""
        client = self.get_phone_client()

        try:
            result = client.create_phone_channel(channel)
            config_id = result.get('id')

            logger.info(f"Successfully created phone config '{channel.name or '<unnamed>'}'. id: '{config_id}'")
            return config_id

        except Exception as e:
            logger.error(f"Failed to create phone config: {e}")
            sys.exit(1)

    @block_local_dev()
    def create_or_update_phone_config(self, channel: BasePhoneChannel) -> str:
        """Create or update a phone config.
        
        If a phone config with the same name exists, update it.
        Otherwise, create a new phone config.
        
        Args:
            channel: Phone channel configuration object
            
        Returns:
            Phone config ID
        """
        client = self.get_phone_client()

        try:
            result, was_created = client.create_or_update_phone_channel(channel)
            config_id = result.get('id')
            
            action = "created" if was_created else "updated"
            logger.info(f"Successfully {action} phone config '{channel.name or '<unnamed>'}'. id: '{config_id}'")
            
            return config_id

        except Exception as e:
            logger.error(f"Failed to create or update phone config: {e}")
            sys.exit(1)

    @block_local_dev()
    def list_phone_configs(
        self,
        channel_type: Optional[PhoneChannelType] = None,
        verbose: bool = False,
        format: Optional[ListFormats] = None
    ) -> List[Dict[str, Any]]:
        """List all phone configs."""
        client = self.get_phone_client()

        try:
            configs = client.list_phone_channels()
        except Exception as e:
            logger.error(f"Failed to list phone configs: {e}")
            sys.exit(1)

        if not configs:
            logger.info("No phone configs found")
            return []

        # Filter by type if specified
        if channel_type:
            configs = [c for c in configs if c.get('service_provider') == channel_type.value]

        if verbose:
            rich.print_json(json.dumps(configs, indent=2))
            return configs

        table = rich.table.Table(
            show_header=True,
            header_style="bold white",
            title="Phone Configs",
            show_lines=True
        )

        columns = {
            "Name": {"overflow": "fold"},
            "Type": {},
            "ID": {"overflow": "fold"},
            "Attached Agents": {"overflow": "fold"},
        }

        for column in columns:
            table.add_column(column, **columns[column])

        for config in configs:
            # Format attached agents
            attached_envs = config.get('attached_environments', [])
            if attached_envs:
                # Group by agent_id
                agent_env_map = {}
                for env in attached_envs:
                    agent_id = env.get('agent_id', '')
                    env_id = env.get('environment_id', '')
                    if agent_id not in agent_env_map:
                        agent_env_map[agent_id] = []
                    agent_env_map[agent_id].append(env_id)
                
                attached_str = "\n".join([f"{agent_id[:8]}..." for agent_id in agent_env_map.keys()])
            else:
                attached_str = "None"

            table.add_row(
                config.get('name', '<no name>'),
                config.get('service_provider', ''),
                str(config.get('id', ''))[:16] + '...',
                attached_str
            )

        if format == ListFormats.JSON:
            return configs

        console = rich.console.Console()
        console.print(table)
        return configs

    @block_local_dev()
    def get_phone_config(
        self,
        config_id: str,
        verbose: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a specific phone config by ID."""
        client = self.get_phone_client()

        try:
            config = client.get_phone_channel(config_id)
        except Exception as e:
            logger.error(f"Failed to get phone config: {e}")
            sys.exit(1)

        if not config:
            logger.error(f"Phone config not found: {config_id}")
            sys.exit(1)

        if verbose:
            rich.print_json(json.dumps(config, indent=2))
        else:
            rich.print(f"Phone Config: {config.get('name', config_id)}")
            rich.print(f"  Type: {config.get('service_provider')}")
            rich.print(f"  ID: {config.get('id')}")
            if config.get('description'):
                rich.print(f"  Description: {config.get('description')}")
            
            # Show attached agents
            attached_envs = config.get('attached_environments', [])
            if attached_envs:
                rich.print(f"  Attached Agents: {len(attached_envs)}")
                for env in attached_envs:
                    rich.print(f"    - Agent: {env.get('agent_id')}, Env: {env.get('environment_id')}")
            else:
                rich.print("  Attached Agents: None")

        return config

    @block_local_dev()
    def delete_phone_config(self, config_id: str) -> None:
        """Delete a phone config."""
        client = self.get_phone_client()

        try:
            client.delete_phone_channel(config_id)
            logger.info(f"Successfully deleted phone config '{config_id}'")
        except Exception as e:
            logger.error(f"Failed to delete phone config: {e}")
            sys.exit(1)

    def _build_local_webhook_url(
        self,
        agent_id: str,
        environment_id: str,
        channel_type: str,
        config_id: str
    ) -> str:
        """Build webhook URL for local development environment."""
        return build_local_webhook_url(agent_id, environment_id, channel_type, config_id, "connect")

    def _build_saas_webhook_url(
        self,
        client,
        agent_id: str,
        environment_id: str,
        channel_type: str,
        config_id: str
    ) -> Dict[str, str]:
        """Build webhook URL for SaaS environment (Genesys Audio Connector).

        Args:
            client: PhoneClient instance
            agent_id: Agent identifier
            environment_id: Environment identifier
            channel_type: Phone channel type (e.g., 'genesys_audio_connector')
            config_id: Phone config identifier

        Returns:
            Dictionary with 'audio_connect_uri' and 'connector_id' keys
        """
        base_url = client.base_url

        # Clean up base URL by removing API version paths
        base_url_clean = base_url.replace('/v1/orchestrate', '').replace('/v1', '')

        # Parse URL to extract domain and instance ID
        if '/instances/' not in base_url_clean:
            logger.warning("Could not parse base_url to construct proper webhook URL")
            # Fallback to simple format
            return {
                "audio_connect_uri": f"{base_url_clean}/channels/phone",
                "connector_id": f"agents/{agent_id}/environments/{environment_id}/channels/{channel_type}/{config_id}/connect"
            }

        parts = base_url_clean.split('/instances/')
        domain = parts[0].replace('https://api.', 'wss://channels.')
        instance_id = parts[1].rstrip('/')

        # Get subscription ID and construct tenant ID
        subscription_id = client.get_subscription_id()
        tenant_id = f"{subscription_id}_{instance_id}" if subscription_id else instance_id

        if not subscription_id:
            logger.debug("Subscription ID not found in token, using instance_id as tenant_id")

        # For Genesys Audio Connector, split into two parts
        audio_connect_uri = f"{domain}/tenants/{tenant_id}/"
        connector_id = f"agents/{agent_id}/environments/{environment_id}/channels/{channel_type}/{config_id}/connect"

        return {
            "audio_connect_uri": audio_connect_uri,
            "connector_id": connector_id
        }

    def get_phone_webhook_url(
        self,
        agent_id: str,
        environment_id: str,
        channel_type: str,
        config_id: str
    ) -> str | Dict[str, str]:
        """Generate the webhook URL for a phone channel.

        Args:
            agent_id: Agent identifier
            environment_id: Environment identifier
            channel_type: Phone channel type (e.g., 'genesys_audio_connector')
            config_id: Phone config identifier

        Returns:
            For local dev: String with full path
            For SaaS: Dictionary with 'audio_connect_uri' and 'connector_id' keys
        """
        client = self.get_phone_client()

        # Check if this is a local environment
        if is_local_dev(client.base_url):
            return self._build_local_webhook_url(agent_id, environment_id, channel_type, config_id)

        # Build SaaS environment URL (split format for Genesys)
        return self._build_saas_webhook_url(client, agent_id, environment_id, channel_type, config_id)

    @block_local_dev()
    def attach_agent_to_config(
        self,
        config_id: str,
        agent_id: str,
        environment_id: str,
        agent_name: Optional[str] = None,
        env_name: Optional[str] = None
    ) -> None:
        """Attach an agent/environment to a phone config."""
        client = self.get_phone_client()

        try:
            # Check if agent has voice configuration
            agent_client = self.get_agent_client()
            agent_spec = agent_client.get_draft_by_id(agent_id)

            if not agent_spec:
                logger.error(f"Agent not found: {agent_name}")
                sys.exit(1)

            if not agent_spec.get('voice_configuration_id'):
                logger.warning(
                    f"Warning: Agent '{agent_name}' does not have voice configuration set up. "
                    f"Phone integration may not work properly without voice configuration."
                )

            # Get current config to check existing attachments
            config = client.get_phone_channel(config_id)
            if not config:
                logger.error(f"Phone config not found: {config_id}")
                sys.exit(1)

            attached_envs = config.get('attached_environments', [])

            # Check if already attached
            is_attached = any(
                e.get('agent_id') == agent_id and e.get('environment_id') == environment_id
                for e in attached_envs
            )

            if is_attached:
                agent_display = agent_name if agent_name else agent_id
                env_display = env_name if env_name else environment_id
                logger.error(
                    f"Agent '{agent_display}' / Environment '{env_display}' is already attached to phone config '{config.get('name')}'."
                )
                sys.exit(1)

            # Add new attachment
            attached_envs.append({
                "agent_id": agent_id,
                "environment_id": environment_id
            })

            # Update config
            client.attach_agents_to_phone_channel(config_id, attached_envs)

            agent_display = agent_name if agent_name else agent_id
            env_display = env_name if env_name else environment_id
            logger.info(f"Successfully attached agent '{agent_display}' / environment '{env_display}' to phone config '{config.get('name')}'")

            # Generate and display webhook URL
            channel_type = config.get('service_provider', 'genesys_audio_connector')
            webhook_url = self.get_phone_webhook_url(agent_id, environment_id, channel_type, config_id)
            
            if isinstance(webhook_url, dict):
                # SaaS format - split into two parts
                logger.info("\nWebhook Configuration:")
                logger.info(f"  Genesys Audio Connect URI: {webhook_url['audio_connect_uri']}")
                logger.info(f"  Connector ID: {webhook_url['connector_id']}")
            else:
                # Local dev format - single URL
                logger.info(f"\nWebhook URL: {webhook_url}")

        except Exception as e:
            logger.error(f"Failed to attach agent to phone config: {e}")
            sys.exit(1)

    @block_local_dev()
    def detach_agent_from_config(
        self,
        config_id: str,
        agent_id: str,
        environment_id: str,
        agent_name: Optional[str] = None,
        env_name: Optional[str] = None
    ) -> None:
        """Detach an agent/environment from a phone config."""
        client = self.get_phone_client()

        try:
            # Get current config
            config = client.get_phone_channel(config_id)
            if not config:
                logger.error(f"Phone config not found: {config_id}")
                sys.exit(1)

            attached_envs = config.get('attached_environments', [])

            # Remove the attachment
            new_attached_envs = [
                e for e in attached_envs
                if not (e.get('agent_id') == agent_id and e.get('environment_id') == environment_id)
            ]

            if len(new_attached_envs) == len(attached_envs):
                agent_display = agent_name if agent_name else agent_id
                env_display = env_name if env_name else environment_id
                logger.error(
                    f"Agent '{agent_display}' / Environment '{env_display}' is not attached to phone config '{config.get('name')}'."
                )
                sys.exit(1)

            # Update config
            client.attach_agents_to_phone_channel(config_id, new_attached_envs)

            agent_display = agent_name if agent_name else agent_id
            env_display = env_name if env_name else environment_id
            logger.info(f"Successfully detached agent '{agent_display}' / environment '{env_display}' from phone config '{config.get('name')}'")

        except Exception as e:
            logger.error(f"Failed to detach agent from phone config: {e}")
            sys.exit(1)

    @block_local_dev()
    def list_attachments(
        self,
        config_id: str,
        format: Optional[ListFormats] = None
    ) -> List[Dict[str, Any]]:
        """List all agent/environment attachments for a phone config."""
        client = self.get_phone_client()

        try:
            config = client.get_phone_channel(config_id)
            if not config:
                logger.error(f"Phone config not found: {config_id}")
                sys.exit(1)

            attached_envs = config.get('attached_environments', [])

            if not attached_envs:
                logger.info(f"No agents attached to phone config '{config.get('name')}'")
                return []

            if format == ListFormats.JSON:
                rich.print_json(json.dumps(attached_envs, indent=2))
                return attached_envs

            agent_client = self.get_agent_client()

            table = rich.table.Table(
                show_header=True,
                header_style="bold white",
                title=f"Attachments for Phone Config '{config.get('name')}'",
                show_lines=True
            )

            table.add_column("Agent Name", overflow="fold")
            table.add_column("Agent ID", overflow="fold")
            table.add_column("Environment", overflow="fold")
            table.add_column("Environment ID", overflow="fold")

            for env in attached_envs:
                agent_id = env.get('agent_id', '')
                environment_id = env.get('environment_id', '')

                # Look up agent name
                agent_name = '<unknown>'
                env_name = '<unknown>'
                try:
                    agent_spec = agent_client.get_draft_by_id(agent_id)
                    if agent_spec:
                        agent_name = agent_spec.get('name', '<unknown>')

                        # Look up environment name
                        agent_environments = agent_spec.get('environments', [])
                        for agent_env in agent_environments:
                            if agent_env.get('id') == environment_id:
                                env_name = agent_env.get('name', '<unknown>')
                                break
                except Exception as e:
                    logger.debug(f"Could not look up agent/environment details: {e}")

                table.add_row(
                    agent_name,
                    agent_id,
                    env_name,
                    environment_id
                )

            console = rich.console.Console()
            console.print(table)
            return attached_envs

        except Exception as e:
            logger.error(f"Failed to list attachments: {e}")
            sys.exit(1)

    def import_phone_config(self, file: str) -> BasePhoneChannel:
        """Import phone config from YAML, JSON, or Python file."""
        file_path = Path(file)

        if not file_path.exists():
            logger.error(f"File not found: {file}")
            sys.exit(1)

        try:
            if file.endswith('.py'):
                phone_channels = PhoneChannelLoader.from_python(file)
                if not phone_channels:
                    logger.error("Python file must define at least one BasePhoneChannel instance.")
                    sys.exit(1)
                # Return first phone channel found
                return phone_channels[0]
            else:
                phone_channel = PhoneChannelLoader.from_spec(file)
                return phone_channel
        except BadRequest as e:
            logger.error(f"Failed to load phone config: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to validate phone config: {e}")
            sys.exit(1)

    @block_local_dev()
    def export_phone_config(
        self,
        config_id: str,
        output_path: str
    ) -> None:
        """Export a phone config to a YAML file."""
        output_file = Path(output_path)
        output_file_extension = output_file.suffix

        if output_file_extension not in [".yaml", ".yml"]:
            logger.error(f"Output file must end with '.yaml' or '.yml'. Provided file '{output_path}' ends with '{output_file_extension}'")
            sys.exit(1)

        client = self.get_phone_client()

        try:
            config = client.get_phone_channel(config_id)
        except Exception as e:
            logger.error(f"Failed to get phone config: {e}")
            sys.exit(1)

        if not config:
            logger.error(f"Phone config not found: {config_id}")
            sys.exit(1)

        # Remove response-only fields before exporting
        export_data = {k: v for k, v in config.items() if k not in BasePhoneChannel.SERIALIZATION_EXCLUDE and k not in ['id', 'attached_environments', 'phone_numbers', 'created_on', 'updated_at', 'created_by', 'updated_by', 'tenant_id']}

        try:
            with safe_open(output_path, 'w') as outfile:
                yaml.dump(export_data, outfile, sort_keys=False, default_flow_style=False, allow_unicode=True)

            logger.info(f"Exported phone config '{config.get('name', config_id)}' to '{output_path}'")

        except Exception as e:
            logger.error(f"Failed to write export file: {e}")
            sys.exit(1)

    @block_local_dev()
    def update_phone_config(
        self,
        config_id: str,
        channel: BasePhoneChannel
    ) -> None:
        """Update a phone config.
        
        Args:
            config_id: Phone config identifier
            channel: Updated phone channel configuration object
        """
        client = self.get_phone_client()

        try:
            # Get current config to verify it exists
            existing_config = client.get_phone_channel(config_id)
            if not existing_config:
                logger.error(f"Phone config not found: {config_id}")
                sys.exit(1)

            # Update the config
            result = client.update_phone_channel(config_id, channel, partial=True)
            
            logger.info(f"Successfully updated phone config '{result.get('name', config_id)}'")

        except Exception as e:
            logger.error(f"Failed to update phone config: {e}")
            sys.exit(1)
