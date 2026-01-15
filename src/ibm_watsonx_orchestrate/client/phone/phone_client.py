# Client for managing phone channels in watsonx Orchestrate.

from typing import Optional, Dict, Any
import logging
from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient
from ibm_watsonx_orchestrate.client.utils import is_local_dev

logger = logging.getLogger(__name__)


class PhoneClient(BaseWXOClient):
    """
    Client for CRUD operations on phone channels.
    
    Phone channels are global resources not scoped to specific agents/environments.
    Multiple agents can attach to the same phone config.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_endpoint = "/api/v1/channels" if is_local_dev(self.base_url) else "/channels"

    def create_phone_channel(self, channel) -> Dict[str, Any]:
        """Create a phone channel (global resource).

        Args:
            channel: Phone channel configuration object

        Returns:
            Dictionary with channel ID and details
        """
        endpoint = f"/../{self.base_endpoint}/phone"

        data = channel.model_dump(
            exclude_none=True,
            exclude=channel.SERIALIZATION_EXCLUDE
        )

        return self._post(endpoint, data=data)

    def attach_agents_to_phone_channel(
        self,
        config_id: str,
        attached_environments: list[dict[str, str]]
    ) -> Dict[str, Any]:
        """Attach agents to a phone channel.

        Args:
            config_id: Phone config identifier
            attached_environments: List of dicts with agent_id and environment_id
                Example: [
                    {"agent_id": "agent-123", "environment_id": "env-456"},
                    {"agent_id": "agent-123", "environment_id": "env-789"}
                ]

        Returns:
            Dictionary with updated channel details
        """
        endpoint = f"/../{self.base_endpoint}/phone/{config_id}"
        data = {"attached_environments": attached_environments}

        return self._patch(endpoint, data=data)

    def get_phone_channel(self, config_id: str) -> Optional[Dict[str, Any]]:
        """Get a phone channel by ID.

        Args:
            config_id: Phone config identifier

        Returns:
            Dictionary with channel details, or None if not found
        """
        endpoint = f"/../{self.base_endpoint}/phone/{config_id}"
        return self._get(endpoint)

    def list_phone_channels(self) -> list[dict[str, Any]]:
        """List all phone channels.

        Returns:
            List of channel dictionaries
        """
        endpoint = f"/../{self.base_endpoint}/phone"
        response = self._get(endpoint)
        return response.get("phones", []) if isinstance(response, dict) else []

    def delete_phone_channel(self, config_id: str) -> None:
        """Delete a phone channel.

        Args:
            config_id: Phone config identifier to delete
        """
        endpoint = f"/../{self.base_endpoint}/phone/{config_id}"
        self._delete(endpoint)

    def update_phone_channel(
        self,
        config_id: str,
        channel,
        partial: bool = True
    ) -> Dict[str, Any]:
        """Update a phone channel configuration.

        Args:
            config_id: Phone config identifier
            channel: Phone channel configuration object with updates
            partial: If True, only update explicitly set fields

        Returns:
            Dictionary with updated channel details
        """
        endpoint = f"/../{self.base_endpoint}/phone/{config_id}"

        # Exclude response-only fields and optionally unset fields
        data = channel.model_dump(
            exclude_none=True,
            exclude_unset=partial,
            exclude=channel.SERIALIZATION_EXCLUDE
        )

        return self._patch(endpoint, data=data)

    def create_or_update_phone_channel(self, channel) -> tuple[Dict[str, Any], bool]:
        """Create a phone channel or update if one with the same name exists.

        Args:
            channel: Phone channel configuration object

        Returns:
            Tuple of (channel_dict, was_created) where was_created is True if created, False if updated
        """
        # Check if a channel with this name already exists
        existing_channel = None
        if channel.name:
            try:
                channels = self.list_phone_channels()
                for ch in channels:
                    if ch.get('name') == channel.name:
                        existing_channel = ch
                        break
            except Exception as e:
                logger.warning(f"Could not list existing phone channels: {e}")

        if existing_channel:
            logger.info(f"Found existing phone config '{channel.name}', updating...")
            result = self.update_phone_channel(existing_channel['id'], channel, partial=True)
            return result, False
        else:
            logger.info(f"Creating new phone config '{channel.name or '<unnamed>'}'...")
            result = self.create_phone_channel(channel)
            return result, True

    def get_subscription_id(self) -> Optional[str]:
        """Extract subscription ID from the JWT token.

        Returns:
            Subscription ID if found, None otherwise
        """
        if not self.api_key:
            return None

        try:
            import jwt
            decoded = jwt.decode(self.api_key, options={"verify_signature": False})
            subscription_id = decoded.get('subscriptionId')

            if not subscription_id:
                account = decoded.get('account', {})
                subscription_id = account.get('bss')
            return subscription_id
            
        except Exception as e:
            logger.debug(f"Failed to extract subscription ID from token: {e}")
            return None

    def _check_phone_numbers_supported(self, config_id: str) -> None:
        """Verify the phone channel supports phone number management.
        Phone number management is only supported for SIP channels.

        Args:
            config_id: Phone config identifier
        """
        from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

        config = self.get_phone_channel(config_id)
        if not config:
            raise BadRequest(f"Phone config not found: {config_id}")

        service_provider = config.get('service_provider', '')

        # Only SIP channels support phone number management
        if service_provider != 'sip_trunk':
            raise NotImplementedError(
                f"Phone number management is not supported for {service_provider}."
                "This feature is only available for SIP phone channels."
            )

    def add_phone_number(
        self,
        config_id: str,
        number: str,
        description: Optional[str] = None,
        agent_id: Optional[str] = None,
        environment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a phone number to a phone channel.

        Args:
            config_id: Phone config identifier
            number: Phone number to add
            description: Optional description
            agent_id: Optional agent ID to associate with this phone number
            environment_id: Optional environment ID to associate with this phone number

        Returns:
            Dictionary with phone number details
        """
        self._check_phone_numbers_supported(config_id)
        endpoint = f"/../{self.base_endpoint}/phone/{config_id}/numbers"

        data = {"phone_number": number}
        if description:
            data["description"] = description
        if agent_id:
            data["agent_id"] = agent_id
        if environment_id:
            data["environment_id"] = environment_id

        return self._post(endpoint, data=data)

    def list_phone_numbers(self, config_id: str) -> list[dict[str, Any]]:
        """List all phone numbers for a phone channel.

        Args:
            config_id: Phone config identifier

        Returns:
            List of phone number dictionaries
        """
        self._check_phone_numbers_supported(config_id)
        config = self.get_phone_channel(config_id)
        return config.get("phone_numbers", []) if config else []

    def update_phone_number(
        self,
        config_id: str,
        number: str,
        new_number: Optional[str] = None,
        description: Optional[str] = None,
        agent_id: Optional[str] = None,
        environment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update a phone number's details.

        Args:
            config_id: Phone config identifier
            number: Phone number to update
            new_number: New phone number
            description: New description
            agent_id: Optional agent ID to associate with this phone number
            environment_id: Optional environment ID to associate with this phone number

        Returns:
            Dictionary with updated phone number details
        """
        self._check_phone_numbers_supported(config_id)
        endpoint = f"/../{self.base_endpoint}/phone/{config_id}/numbers/{number}"

        data = {"phone_number": new_number if new_number else number}
        if description is not None:
            data["description"] = description
        if agent_id:
            data["agent_id"] = agent_id
        if environment_id:
            data["environment_id"] = environment_id

        return self._patch(endpoint, data=data)

    def delete_phone_number(
        self,
        config_id: str,
        number: str
    ) -> None:
        """Delete a phone number from a phone channel.

        Args:
            config_id: Phone config identifier
            number: Phone number to delete
        """
        self._check_phone_numbers_supported(config_id)
        endpoint = f"/../{self.base_endpoint}/phone/{config_id}/numbers/{number}"
        self._delete(endpoint)
