# Client for managing channels in watsonx Orchestrate.

from typing import Optional, Dict, Any
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient
from ibm_watsonx_orchestrate.agent_builder.channels.types import Channel


class ChannelsClient(BaseAPIClient):
    """
    Client for CRUD operations on channels.
    """

    def create(
        self,
        agent_id: str,
        environment_id: str,
        channel: Channel
    ) -> Dict[str, Any]:
        """
        Create a new channel for an agent environment.

        Args:
            agent_id: Agent identifier
            environment_id: Environment identifier (e.g., "draft" or "live")
            channel: Channel configuration object

        Returns:
            Dictionary with channel ID and details
        """
        endpoint = f"/orchestrate/agents/{agent_id}/environments/{environment_id}/channels/{channel.get_api_path()}"

        # Exclude response-only fields
        data = channel.model_dump(
            exclude_none=True,
            exclude=channel.SERIALIZATION_EXCLUDE
        )

        return self._post(endpoint, data=data)

    def update(
        self,
        agent_id: str,
        environment_id: str,
        channel_id: str,
        channel: Channel,
        partial: bool = True
    ) -> Dict[str, Any]:
        """Update an existing channel.

        Args:
            agent_id: Agent identifier (UUID)
            environment_id: Environment identifier (UUID)
            channel_id: Channel identifier to update
            channel: Channel configuration with updates
            partial: If True, only send explicitly set fields (default: True)

        Returns:
            Dictionary with updated channel details
        """
        endpoint = f"/orchestrate/agents/{agent_id}/environments/{environment_id}/channels/{channel.get_api_path()}/{channel_id}"

        # For partial updates, exclude unset fields
        # For full updates, include all fields
        data = channel.model_dump(
            exclude_none=True,
            exclude_unset=partial,
            exclude=channel.SERIALIZATION_EXCLUDE
        )

        return self._patch(endpoint, data=data)

    def get(
        self,
        agent_id: str,
        environment_id: str,
        channel_type: str,
        channel_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific channel by ID.

        Args:
            agent_id: Agent identifier (UUID)
            environment_id: Environment identifier (UUID)
            channel_type: Channel type (e.g., "twilio_whatsapp")
            channel_id: Channel identifier

        Returns:
            Dictionary with channel details, or None if not found
        """
        endpoint = f"/orchestrate/agents/{agent_id}/environments/{environment_id}/channels/{channel_type}/{channel_id}"
        return self._get(endpoint)

    def list(
        self,
        agent_id: str,
        environment_id: str,
        channel_type: Optional[str] = None
    ) -> list[Dict[str, Any]]:
        """List all channels for an agent environment.

        Args:
            agent_id: Agent identifier (UUID)
            environment_id: Environment identifier (UUID)
            channel_type: Optional filter by channel type

        Returns:
            List of channel dictionaries
        """
        if channel_type:
            endpoint = f"/orchestrate/agents/{agent_id}/environments/{environment_id}/channels/{channel_type}"
        else:
            endpoint = f"/orchestrate/agents/{agent_id}/environments/{environment_id}/channels"

        response = self._get(endpoint)
        return response.get("channels", []) if isinstance(response, dict) else []

    def delete(
        self,
        agent_id: str,
        environment_id: str,
        channel_type: str,
        channel_id: str
    ) -> None:
        """Delete a channel.

        Args:
            agent_id: Agent identifier (UUID)
            environment_id: Environment identifier (UUID)
            channel_type: Channel type
            channel_id: Channel identifier to delete
        """
        endpoint = f"/orchestrate/agents/{agent_id}/environments/{environment_id}/channels/{channel_type}/{channel_id}"
        self._delete(endpoint)
