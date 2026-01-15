import json
import sys
import yaml
import logging
import secrets
import base64
from typing import Optional, List, Any, Dict
from pathlib import Path
from pydantic import ValidationError
from rich.table import Table
from rich.console import Console
from rich import print_json

from ibm_watsonx_orchestrate.agent_builder.phone import GenesysAudioConnectorChannel, SIPTrunkChannel, BasePhoneChannel, PhoneChannelLoader
from ibm_watsonx_orchestrate.agent_builder.phone.phone import PHONE_CHANNEL_CLASSES
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

    def _block_sip_in_local(
        self,
        config_id: Optional[str] = None,
        channel: Optional[BasePhoneChannel] = None,
        service_provider: Optional[str] = None,
        operation: str = "operation"
    ) -> None:
        """Block SIP operations in local development environment.

        This is a hard block with no developer mode bypass.
        Checks if the operation involves SIP and blocks it in local environments.

        Args:
            config_id: Phone config ID to check
            channel: Phone channel object to check
            service_provider: Service provider string to check
            operation: Description of the operation being blocked

        Raises:
            SystemExit: If in local dev and operation involves SIP
        """
        if not is_local_dev():
            return

        is_sip = False

        if service_provider:
            is_sip = service_provider == 'sip_trunk'
        elif channel:
            is_sip = channel.service_provider == PhoneChannelType.SIP.value
        elif config_id:
            try:
                client = self.get_phone_client()
                config = client.get_phone_channel(config_id)
                if config:
                    is_sip = config.get('service_provider') == 'sip_trunk'
            except Exception:
                pass

        if is_sip:
            logger.error(
                f"SIP trunk {operation} is not available in local development environment. "
                f"Only Genesys Audio Connector is supported for local development."
            )
            sys.exit(1)

    def _check_genesys_only(self, config: Dict[str, Any], operation: str) -> None:
        """Block operations that are only supported for Genesys Audio Connector channels."""
        if config.get('service_provider') != PhoneChannelType.GENESYS_AUDIO_CONNECTOR.value:
            logger.error(
                f"{operation} is only supported for Genesys Audio Connector channels. "
            )
            sys.exit(1)

    def _check_sip_only(self, config: Dict[str, Any], operation: str) -> None:
        """Block operations that are only supported for SIP trunk channels."""
        if config.get('service_provider') != PhoneChannelType.SIP.value:
            logger.error(
                f"{operation} is only supported for SIP trunk channels. "
            )
            sys.exit(1)

    def _generate_api_key(self, length: int = 16) -> str:
        """Generate a random API key.

        Args:
            length: Length of the API key in characters (default: 16)

        Returns:
            A randomly generated API key string
        """
        return secrets.token_urlsafe(length)

    def _generate_client_secret(self, length: int = 16) -> str:
        """Generate a random client secret that is base64-encoded.

        Args:
            length: Length of the random bytes to generate before encoding (default: 16)

        Returns:
            A base64-encoded client secret string
        """
        random_bytes = secrets.token_bytes(length)
        return base64.b64encode(random_bytes).decode('utf-8')

    def _generate_genesys_credentials(self) -> Dict[str, str]:
        """Generate both API key and client secret for Genesys Audio Connector.

        Returns:
            Dictionary with 'api_key' and 'client_secret' keys
        """
        return {
            'api_key': self._generate_api_key(),
            'client_secret': self._generate_client_secret()
        }

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

    def get_agent_id_by_name(self, agent_name: str) -> str | None:
        """Look up agent ID by agent name."""
        client = self.get_agent_client()
        return common_get_agent_id_by_name(client, agent_name)

    def get_agent_name_by_id(self, agent_id: str) -> str | None:
        """Look up agent ID by agent name."""
        client = self.get_agent_client()
        return common_get_agent_name_by_id(client, agent_id)

    def get_environment_id(self, agent_name: str, env: str) -> str:
        """Get environment ID by agent name and environment name (draft/live)."""
        agent_client = self.get_agent_client()
        return common_get_environment_id(agent_client, agent_name, env)

    def resolve_agent_and_environment(
        self,
        agent_name: Optional[str],
        env: Optional[str]
    ) -> tuple[Optional[str], Optional[str]]:
        """Resolve agent name and environment to their IDs.
        
        Args:
            agent_name: Optional agent name
            env: Optional environment type (draft/live)
            
        Returns:
            Tuple of (agent_id, environment_id) or (None, None)
            
        Raises:
            SystemExit: If only one of agent_name or env is provided
        """
        import typer
        
        if agent_name and env:
            agent_id = self.get_agent_id_by_name(agent_name)
            environment_id = self.get_environment_id(agent_name, env)
            return agent_id, environment_id
        elif agent_name or env:
            missing = "--env" if agent_name else "--agent-name"
            provided = "--agent-name" if agent_name else "--env"
            typer.echo(f"Error: {missing} is required when {provided} is specified")
            raise typer.Exit(1)
        return None, None

    def list_phone_channel_types(self):
        """List all supported phone channel types (enum values)."""
        table = Table(show_header=True, header_style="bold white", show_lines=True)
        table.add_column("Phone Channel Type")

        for channel_type in PhoneChannelType.__members__.values():
            # Hide SIP type in local environment
            if is_local_dev() and channel_type == PhoneChannelType.SIP:
                continue
            table.add_row(channel_type.value)

        console = Console()
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
        """Create a phone config from CLI arguments.

        If credentials are not provided for Genesys Audio Connector, they will be
        auto-generated and displayed to the user.
        """
        # Block SIP channel creation in local environment
        if is_local_dev() and channel_type == PhoneChannelType.SIP:
            logger.error(
                "SIP trunk channels are not supported in local development environment. "
                "Only Genesys Audio Connector is available for local development."
            )
            sys.exit(1)
        channel_class_map = {
            PhoneChannelType.GENESYS_AUDIO_CONNECTOR: GenesysAudioConnectorChannel,
            PhoneChannelType.SIP: SIPTrunkChannel,
        }

        try:
            channel_class = channel_class_map.get(channel_type)

            if not channel_class:
                logger.error(f"Unsupported phone channel type: '{channel_type}'")
                sys.exit(1)

            # Auto-generate credentials for Genesys Audio Connector if not provided
            generated_credentials = {}
            if channel_type == PhoneChannelType.GENESYS_AUDIO_CONNECTOR:
                security = channel_fields.get('security', {})

                # Check which credentials are missing and generate them
                needs_api_key = not security or not security.get('api_key')
                needs_client_secret = not security or not security.get('client_secret')

                if needs_api_key or needs_client_secret:
                    # Merge with any existing security fields
                    if not security:
                        security = {}

                    if needs_api_key:
                        generated_credentials['api_key'] = self._generate_api_key()
                        security['api_key'] = generated_credentials['api_key']

                    if needs_client_secret:
                        generated_credentials['client_secret'] = self._generate_client_secret()
                        security['client_secret'] = generated_credentials['client_secret']

                    channel_fields['security'] = security

                    # Display generated credentials to the user
                    logger.info("\n" + "="*20)
                    logger.info("GENERATED CREDENTIALS - SAVE THESE!")
                    logger.info("\nPlease paste these credentials in:")
                    logger.info("  Genesys Audio Connector > Integration Settings > Credentials tab")
                    logger.info("")
                    if needs_api_key:
                        logger.info(f"API Key: {generated_credentials['api_key']}")
                    if needs_client_secret:
                        logger.info(f"Client Secret: {generated_credentials['client_secret']}")
                    logger.info("")
                    logger.info("="*20 + "\n")

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
    def create_phone_config(self, channel: BasePhoneChannel) -> str | None:
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
    def create_or_update_phone_config(self, channel: BasePhoneChannel, enable_developer_mode: bool = False) -> str | None:
        """Create or update a phone config.
        
        If a phone config with the same name exists, update it.
        Otherwise, create a new phone config.
        
        Args:
            channel: Phone channel configuration object
            
        Returns:
            Phone config ID
        """
        # Block SIP operations in local environment
        self._block_sip_in_local(channel=channel, operation="creation/update")
        
        client = self.get_phone_client()

        try:
            result, was_created = client.create_or_update_phone_channel(channel)
            config_id = result.get('id')
            
            action = "created" if was_created else "updated"
            logger.info(f"Successfully {action} phone config '{channel.name or '<unnamed>'}'. id: '{config_id}'")
            
            # For SIP trunk configs, display SIP URI and Tenant ID
            if result.get('service_provider') == 'sip_trunk':
                self._display_sip_connection_info(result)
            
            return config_id

        except Exception as e:
            logger.error(f"Failed to create or update phone config: {e}")
            sys.exit(1)

    @block_local_dev()
    def list_phone_configs(
        self,
        channel_type: Optional[PhoneChannelType] = None,
        verbose: bool = False,
        format: Optional[ListFormats] = None,
        enable_developer_mode: bool = False
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

        # Filter out SIP configs in local environment
        if is_local_dev():
            configs = [c for c in configs if c.get('service_provider') != 'sip_trunk']

        # Filter by type if specified
        if channel_type:
            configs = [c for c in configs if c.get('service_provider') == channel_type.value]

        if verbose:
            print_json(json.dumps(configs, indent=2))
            return configs

        table = Table(
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

        console = Console()
        console.print(table)
        return configs

    @block_local_dev()
    def get_phone_config(
        self,
        config_id: str,
        verbose: bool = False,
        enable_developer_mode: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a specific phone config by ID."""
        # Block SIP config access in local environment
        self._block_sip_in_local(config_id=config_id, operation="access")
        
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
            print_json(json.dumps(config, indent=2))
        else:
            console = Console()
            console.print(f"Phone Config: {config.get('name', config_id)}")
            console.print(f"  Type: {config.get('service_provider')}")
            console.print(f"  ID: {config.get('id')}")
            if config.get('description'):
                console.print(f"  Description: {config.get('description')}")

            # Show SIP URI and Tenant ID for SIP channels
            if config.get('service_provider') == 'sip_trunk':

                client = self.get_phone_client()

                # Extract instance_id from base_url
                base_url = client.base_url

                tenant_id = None
                if '/instances/' in base_url:
                    instance_id = base_url.split('/instances/')[1].split('/')[0]
                    tenant_id = self._get_tenant_id(client, instance_id)
                else:
                    logger.warning("Could not determine instance ID from base URL")

                sip_uri_base = self._get_sip_uri(client.base_url)

                if tenant_id:
                    full_sip_uri = f"sips:{sip_uri_base}?x-tenant-id={tenant_id}"
                else:
                    full_sip_uri = f"sips:{sip_uri_base}"
                    logger.warning("Could not determine tenant ID")

                console.print(f"  SIP URI: {full_sip_uri}")

            # Show attached agents
            attached_envs = config.get('attached_environments', [])
            if attached_envs:
                console.print(f"  Attached Agents: {len(attached_envs)}")
                for env in attached_envs:
                    console.print(f"    - Agent: {env.get('agent_id')}, Env: {env.get('environment_id')}")
            else:
                console.print("  Attached Agents: None")

            # Show phone numbers for SIP channels
            if config.get('service_provider') == 'sip_trunk':
                phone_numbers = config.get('phone_numbers', [])
                if phone_numbers:
                    console.print(f"  Phone Numbers: {len(phone_numbers)}")
                    for num in phone_numbers:
                        desc = f" ({num.get('description')})" if num.get('description') else ""
                        console.print(f"    - {num.get('phone_number')}{desc}")
                else:
                    console.print("  Phone Numbers: None")

        return config

    @block_local_dev()
    def delete_phone_config(self, config_id: str, enable_developer_mode: bool = False) -> None:
        """Delete a phone config."""
        # Block SIP config deletion in local environment
        self._block_sip_in_local(config_id=config_id, operation="deletion")
        
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
    
    def _get_tenant_id(self, client, instance_id: str) -> str:
        """Construct tenant ID from subscription and instance IDs.

        Args:
            client: Phone client to extract subscription ID from
            instance_id: Instance ID from URL

        Returns:
            Combined tenant ID string
        """
        if not client:
            client = self.get_phone_client()

        subscription_id = client.get_subscription_id()
        
        if not subscription_id:
            logger.warning("Missing subscription ID in token. The generated Event URL may be invalid.")
            return instance_id

        return f"{subscription_id}_{instance_id}"

    @block_local_dev()
    def attach_agent_to_config(
        self,
        config_id: str,
        agent_id: str,
        environment_id: str,
        agent_name: Optional[str] = None,
        env_name: Optional[str] = None,
        enable_developer_mode: bool = False
    ) -> None:
        """Attach an agent/environment to a phone config (Genesys Audio Connector only)."""
        client = self.get_phone_client()

        try:
            # Get current config to check if it's SIP
            config = client.get_phone_channel(config_id)
            if not config:
                logger.error(f"Phone config not found: {config_id}")
                sys.exit(1)

            # Only allow for Genesys Audio Connector channels
            self._check_genesys_only(config, "Agent attachment")

            # Check if agent has voice configuration
            agent_client = self.get_agent_client()
            agent_spec = agent_client.get_draft_by_id(agent_id)

            if not agent_spec or not isinstance(agent_spec, dict):
                logger.error(f"Agent not found: {agent_name}")
                sys.exit(1)

            if not agent_spec.get('voice_configuration_id'):
                logger.warning(
                    f"Warning: Agent '{agent_name}' does not have voice configuration set up. "
                    f"Phone integration may not work properly without voice configuration."
                )

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
        env_name: Optional[str] = None,
        enable_developer_mode: bool = False
    ) -> None:
        """Detach an agent/environment from a phone config (Genesys Audio Connector only)."""
        client = self.get_phone_client()

        try:
            # Get current config
            config = client.get_phone_channel(config_id)
            if not config:
                logger.error(f"Phone config not found: {config_id}")
                sys.exit(1)

            # Only allow for Genesys Audio Connector channels
            self._check_genesys_only(config, "Agent detachment")

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
        format: Optional[ListFormats] = None,
        enable_developer_mode: bool = False
    ) -> List[Dict[str, Any]]:
        """List all agent/environment attachments for a phone config (Genesys Audio Connector only)."""
        client = self.get_phone_client()

        try:
            config = client.get_phone_channel(config_id)
            if not config:
                logger.error(f"Phone config not found: {config_id}")
                sys.exit(1)

            # Only allow for Genesys Audio Connector channels
            self._check_genesys_only(config, "Listing attachments")

            attached_envs = config.get('attached_environments', [])

            if not attached_envs:
                logger.info(f"No agents attached to phone config '{config.get('name')}'")
                return []

            if format == ListFormats.JSON:
                print_json(json.dumps(attached_envs, indent=2))
                return attached_envs

            agent_client = self.get_agent_client()

            table = Table(
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
                    if agent_spec and isinstance(agent_spec, dict):
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

            console = Console()
            console.print(table)
            return attached_envs

        except Exception as e:
            logger.error(f"Failed to list attachments: {e}")
            sys.exit(1)

    def import_phone_config(self, file: str) -> BasePhoneChannel:
        """Import phone config from YAML, JSON, or Python file.

        If credentials are not provided for Genesys Audio Connector, they will be
        auto-generated and displayed to the user.
        """
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
                channel = phone_channels[0]
            else:
                # Load the file content first
                from ibm_watsonx_orchestrate.utils.file_manager import safe_open
                from yaml import safe_load as yaml_safe_load
                import json as json_module

                with safe_open(file, 'r') as f:
                    if file.endswith('.yaml') or file.endswith('.yml'):
                        content = yaml_safe_load(f)
                    elif file.endswith('.json'):
                        content = json_module.load(f)
                    else:
                        raise BadRequest('file must end in .json, .yaml, or .yml')

                # Auto-generate credentials for Genesys Audio Connector if not provided
                if content.get('service_provider') == 'genesys_audio_connector':
                    security = content.get('security', {})
                    generated_credentials = {}

                    # Check which credentials are missing and generate them
                    needs_api_key = not security or not security.get('api_key')
                    needs_client_secret = not security or not security.get('client_secret')

                    if needs_api_key or needs_client_secret:
                        # Merge with any existing security fields
                        if not security:
                            security = {}

                        if needs_api_key:
                            generated_credentials['api_key'] = self._generate_api_key()
                            security['api_key'] = generated_credentials['api_key']

                        if needs_client_secret:
                            generated_credentials['client_secret'] = self._generate_client_secret()
                            security['client_secret'] = generated_credentials['client_secret']

                        content['security'] = security

                        # Display generated credentials to the user
                        logger.info("="*20)
                        logger.info("GENERATED CREDENTIALS - SAVE THESE!")
                        logger.info("Please paste these credentials in:")
                        logger.info("  Genesys Audio Connector > Integration Settings > Credentials tab")
                        logger.info("")
                        if needs_api_key:
                            logger.info(f"API Key: {generated_credentials['api_key']}")
                        if needs_client_secret:
                            logger.info(f"Client Secret: {generated_credentials['client_secret']}")
                        logger.info("")
                        logger.info("="*20 + "\n")

                # Now validate the content with credentials included
                channel_type = content.get('service_provider')
                channel_class = PHONE_CHANNEL_CLASSES.get(channel_type)

                if not channel_class:
                    supported = ', '.join(PHONE_CHANNEL_CLASSES.keys())
                    raise BadRequest(f"Unsupported phone channel type: '{channel_type}'. Supported types: {supported}")

                channel = channel_class.model_validate(content)

            # Block SIP config import in local environment
            self._block_sip_in_local(channel=channel, operation="import")

            return channel
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
        output_path: str,
        enable_developer_mode: bool = False
    ) -> None:
        """Export a phone config to a YAML file."""
        # Block SIP config export in local environment
        self._block_sip_in_local(config_id=config_id, operation="export")
        
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

    def _get_sip_uri(self, base_url: str) -> str:
        """Get SIP URI for the environment by parsing the API base URL.

        Args:
            base_url: API base URL

        Returns:
            SIP URI (FQDN) for the environment
        """
        from urllib.parse import urlparse
        
        parsed = urlparse(base_url)
        hostname = parsed.hostname or ""
        
        # Pattern matching for different environments
        
        # IBM Cloud - Test (Dallas)
        if "watson-orchestrate.test.cloud.ibm.com" in hostname:
            return "public.voip.us-south.watson-orchestrate.test.cloud.ibm.com"
        
        # IBM Cloud - Prod (Sao Paulo)
        if "br-sao" in hostname and "watson-orchestrate.cloud.ibm.com" in hostname:
            return "public.voip.br-sao.watson-orchestrate.cloud.ibm.com"
        
        # IBM Cloud - Prod (Dallas)
        if "watson-orchestrate.cloud.ibm.com" in hostname:
            return "public.voip.us-south.watson-orchestrate.cloud.ibm.com"
        
        # AWS - Dev
        if "dev-wa.watson-orchestrate.ibm.com" in hostname:
            return "public.voip.dev-wa.watson-orchestrate.ibm.com"
        
        # AWS - Dev Sandbox
        if "dev-sbsz2.watson-orchestrate.ibm.com" in hostname:
            return "public.voip.dev-sbsz2.watson-orchestrate.ibm.com"
        
        # AWS - Test (Staging)
        if "staging-wa.watson-orchestrate.ibm.com" in hostname:
            return "public.voip.staging-wa.watson-orchestrate.ibm.com"
        
        # AWS - Preprod
        if "preprod.dl.watson-orchestrate.ibm.com" in hostname:
            return "public.voip.preprod.dl.watson-orchestrate.ibm.com"
        
        # AWS - Prod (AP-South-1)
        if "ap-south-1.dl.watson-orchestrate.ibm.com" in hostname:
            return "public.voip.ap-south-1.dl.watson-orchestrate.ibm.com"
        
        # AWS - Prod (EU-Central-1)
        if "eu-central-1.dl.watson-orchestrate.ibm.com" in hostname:
            return "public.voip.eu-central-1.dl.watson-orchestrate.ibm.com"
        
        # AWS - Prod (US-East-1)
        if "dl.watson-orchestrate.ibm.com" in hostname:
            return "public.voip.dl.watson-orchestrate.ibm.com"
        
        # Default fallback to staging (test) environment
        logger.warning(f"Could not determine SIP URI from base URL '{base_url}', defaulting to base URL.")
        return "{base_url}"

    def _display_sip_connection_info(self, config: Dict[str, Any]) -> None:
        """Display SIP connection information for SIP trunk configs.

        Args:
            config: Phone config dictionary containing SIP trunk details
        """

        client = self.get_phone_client()

        # Get tenant_id from config, or compute it if not present
        tenant_id = None
        if not tenant_id:
            # Compute tenant_id client-side
            # Extract instance_id from base_url
            base_url = client.base_url
            if '/instances/' in base_url:
                instance_id = base_url.split('/instances/')[1].split('/')[0]
                tenant_id = self._get_tenant_id(client, instance_id)
            else:
                logger.warning("Could not determine instance ID from base URL")

        # Get SIP URI based on current environment
        sip_uri_base = self._get_sip_uri(client.base_url)

        # Build full SIP URI with tenant ID parameter
        if tenant_id:
            full_sip_uri = f"sips:{sip_uri_base}?x-tenant-id={tenant_id}"
        else:
            full_sip_uri = f"sips:{sip_uri_base}"

        console = Console()
        console.print("\n[bold yellow]Configure these values in your SIP trunk provider:[/bold yellow]")
        console.print(f"   Full SIP URI: '{full_sip_uri}'")
        console.print("")

    @block_local_dev()
    def add_phone_number(
        self,
        config_id: str,
        number: str,
        description: Optional[str] = None,
        agent_id: Optional[str] = None,
        environment_id: Optional[str] = None,
        enable_developer_mode: bool = False
    ) -> None:
        """Add a phone number to a phone config (SIP trunk only).

        Args:
            config_id: Phone config identifier
            number: Phone number to add (E.164 format recommended)
            description: Optional description for the phone number
            agent_id: Optional agent ID to associate with this phone number
            environment_id: Optional environment ID to associate with this phone number
        """
        client = self.get_phone_client()

        try:
            # Get config and verify it's SIP trunk
            config = client.get_phone_channel(config_id)
            if not config:
                logger.error(f"Phone config not found: {config_id}")
                sys.exit(1)

            # Only allow for SIP trunk channels
            self._check_sip_only(config, "Phone number management")

            result = client.add_phone_number(config_id, number, description, agent_id, environment_id)
            logger.info(f"Successfully added phone number '{number}' to phone config")
            if description:
                logger.info(f"  Description: {description}")
            if agent_id and environment_id:
                logger.info(f"  Associated with agent: {agent_id}, environment: {environment_id}")

        except Exception as e:
            logger.error(f"Failed to add phone number: {e}")
            sys.exit(1)

    @block_local_dev()
    def list_phone_numbers(
        self,
        config_id: str,
        format: Optional[ListFormats] = None,
        enable_developer_mode: bool = False
    ) -> List[Dict[str, Any]]:
        """List all phone numbers for a phone config (SIP trunk only).

        Args:
            config_id: Phone config identifier
            format: Output format (table, json)

        Returns:
            List of phone number dictionaries
        """
        client = self.get_phone_client()

        try:
            # Get config and verify it's SIP trunk
            config = client.get_phone_channel(config_id)
            if not config:
                logger.error(f"Phone config not found: {config_id}")
                sys.exit(1)

            # Only allow for SIP trunk channels
            self._check_sip_only(config, "Phone number management")

            numbers = client.list_phone_numbers(config_id)

            if not numbers:
                logger.info("No phone numbers found for this config")
                return []

            if format == ListFormats.JSON:
                print_json(json.dumps(numbers, indent=2))
                return numbers

            table = Table(
                show_header=True,
                header_style="bold white",
                title="Phone Numbers",
                show_lines=True
            )

            table.add_column("Number", overflow="fold")
            table.add_column("Description", overflow="fold")

            for num in numbers:
                table.add_row(
                    num.get('phone_number', ''),
                    num.get('description', '')
                )

            console = Console()
            console.print(table)
            return numbers

        except Exception as e:
            logger.error(f"Failed to list phone numbers: {e}")
            sys.exit(1)

    @block_local_dev()
    def update_phone_number(
        self,
        config_id: str,
        number: str,
        new_number: Optional[str] = None,
        description: Optional[str] = None,
        agent_id: Optional[str] = None,
        environment_id: Optional[str] = None,
        enable_developer_mode: bool = False
    ) -> None:
        """Update a phone number's details (SIP trunk only).

        Args:
            config_id: Phone config identifier
            number: Phone number to update
            new_number: New phone number (if changing the number itself)
            description: New description
            agent_id: Optional agent ID to associate with this phone number
            environment_id: Optional environment ID to associate with this phone number
        """
        client = self.get_phone_client()

        if not new_number and description is None and agent_id is None and environment_id is None:
            logger.warning("No updates specified (provide --new-number, --description, --agent-name, or --env)")
            return

        try:
            # Get config and verify it's SIP trunk
            config = client.get_phone_channel(config_id)
            if not config:
                logger.error(f"Phone config not found: {config_id}")
                sys.exit(1)

            # Only allow for SIP trunk channels
            self._check_sip_only(config, "Phone number management")

            result = client.update_phone_number(config_id, number, new_number, description, agent_id, environment_id)
            logger.info(f"Successfully updated phone number '{number}'")
            if new_number:
                logger.info(f"  New number: {new_number}")
            if description is not None:
                logger.info(f"  New description: {description}")
            if agent_id and environment_id:
                logger.info(f"  Associated with agent: {agent_id}, environment: {environment_id}")

        except Exception as e:
            logger.error(f"Failed to update phone number: {e}")
            sys.exit(1)

    @block_local_dev()
    def delete_phone_number(
        self,
        config_id: str,
        number: str,
        enable_developer_mode: bool = False
    ) -> None:
        """Delete a phone number from a phone config (SIP trunk only).

        Args:
            config_id: Phone config identifier
            number: Phone number to delete
        """
        client = self.get_phone_client()

        try:
            # Get config and verify it's SIP trunk
            config = client.get_phone_channel(config_id)
            if not config:
                logger.error(f"Phone config not found: {config_id}")
                sys.exit(1)

            # Only allow for SIP trunk channels
            self._check_sip_only(config, "Phone number management")

            client.delete_phone_number(config_id, number)
            logger.info(f"Successfully deleted phone number '{number}'")

        except Exception as e:
            logger.error(f"Failed to delete phone number: {e}")
            sys.exit(1)
