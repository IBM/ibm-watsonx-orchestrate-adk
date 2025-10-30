import pytest
from unittest.mock import Mock, patch, MagicMock
from ibm_watsonx_orchestrate.client.channels.channels_client import ChannelsClient
from ibm_watsonx_orchestrate.agent_builder.channels import TwilioWhatsappChannel


@pytest.fixture
def channels_client():
    """Create a ChannelsClient instance with mocked HTTP methods."""
    client = ChannelsClient(base_url="https://test.example.com")
    # Mock the underlying HTTP methods
    client._get = Mock()
    client._post = Mock()
    client._patch = Mock()
    client._delete = Mock()
    return client


@pytest.fixture
def sample_channel():
    """Create a sample channel for testing."""
    return TwilioWhatsappChannel(
        channel="twilio_whatsapp",
        name="test_channel",
        account_sid="AC" + "1" * 32,
        twilio_authentication_token="test_token"
    )


class TestChannelsClientList:
    """Tests for list() method."""

    def test_list_all_channels(self, channels_client):
        """Test listing all channels for an agent environment."""
        channels_client._get.return_value = {
            "channels": [
                {"id": "ch1", "name": "channel1", "channel": "twilio_whatsapp"},
                {"id": "ch2", "name": "channel2", "channel": "slack"}
            ]
        }

        result = channels_client.list("agent-123", "draft")

        channels_client._get.assert_called_once_with("/orchestrate/agents/agent-123/environments/draft/channels")
        assert len(result) == 2
        assert result[0]["id"] == "ch1"

    def test_list_channels_by_type(self, channels_client):
        """Test listing channels filtered by type."""
        channels_client._get.return_value = {
            "channels": [
                {"id": "ch1", "name": "channel1", "channel": "twilio_whatsapp"}
            ]
        }

        result = channels_client.list("agent-123", "draft", "twilio_whatsapp")

        channels_client._get.assert_called_once_with("/orchestrate/agents/agent-123/environments/draft/channels/twilio_whatsapp")
        assert len(result) == 1

    def test_list_empty_channels(self, channels_client):
        """Test listing when no channels exist."""
        channels_client._get.return_value = {"channels": []}

        result = channels_client.list("agent-123", "draft")

        assert result == []


class TestChannelsClientGet:
    """Tests for get() method."""

    def test_get_channel_success(self, channels_client):
        """Test getting a specific channel."""
        channels_client._get.return_value = {
            "id": "ch1",
            "name": "test_channel",
            "channel": "twilio_whatsapp",
            "account_sid": "AC" + "1" * 32
        }

        result = channels_client.get("agent-123", "draft", "twilio_whatsapp", "ch1")

        channels_client._get.assert_called_once_with("/orchestrate/agents/agent-123/environments/draft/channels/twilio_whatsapp/ch1")
        assert result["id"] == "ch1"
        assert result["name"] == "test_channel"

    def test_get_channel_not_found(self, channels_client):
        """Test getting a non-existent channel."""
        channels_client._get.return_value = None

        result = channels_client.get("agent-123", "draft", "twilio_whatsapp", "nonexistent")

        assert result is None


class TestChannelsClientCreate:
    """Tests for create() method."""

    def test_create_channel_success(self, channels_client, sample_channel):
        """Test creating a new channel."""
        channels_client._post.return_value = {
            "id": "new-ch-id",
            "name": "test_channel",
            "channel": "twilio_whatsapp"
        }

        result = channels_client.create("agent-123", "draft", sample_channel)

        channels_client._post.assert_called_once()
        call_args = channels_client._post.call_args

        # Check endpoint
        assert call_args[0][0] == "/orchestrate/agents/agent-123/environments/draft/channels/twilio_whatsapp"

        # Check that data was passed
        data = call_args[1]["data"]
        assert "account_sid" in data
        assert "twilio_authentication_token" in data

        # Check result
        assert result["id"] == "new-ch-id"

    def test_create_channel_excludes_response_fields(self, channels_client, sample_channel):
        """Test that response-only fields are excluded from create request."""
        # Set response-only fields (simulating a channel from API)
        sample_channel.channel_id = "ch-123"
        sample_channel.tenant_id = "tenant-456"

        channels_client._post.return_value = {"id": "new-id"}

        channels_client.create("agent-123", "draft", sample_channel)

        call_args = channels_client._post.call_args
        data = call_args[1]["data"]

        # Response-only fields should not be in request
        assert "channel_id" not in data
        assert "tenant_id" not in data
        assert "agent_id" not in data


class TestChannelsClientUpdate:
    """Tests for update() method."""

    def test_update_channel_partial(self, channels_client, sample_channel):
        """Test partial update of a channel."""
        channels_client._patch.return_value = {
            "id": "ch-123",
            "name": "test_channel",
            "channel": "twilio_whatsapp"
        }

        result = channels_client.update(
            "agent-123",
            "draft",
            "ch-123",
            sample_channel,
            partial=True
        )

        channels_client._patch.assert_called_once()
        call_args = channels_client._patch.call_args

        # Check endpoint
        assert call_args[0][0] == "/orchestrate/agents/agent-123/environments/draft/channels/twilio_whatsapp/ch-123"

        # Check result
        assert result["id"] == "ch-123"

    def test_update_channel_full(self, channels_client, sample_channel):
        """Test full update of a channel."""
        channels_client._patch.return_value = {"id": "ch-123"}

        channels_client.update(
            "agent-123",
            "draft",
            "ch-123",
            sample_channel,
            partial=False
        )

        channels_client._patch.assert_called_once()

    def test_update_excludes_response_fields(self, channels_client, sample_channel):
        """Test that response-only fields are excluded from update request."""
        sample_channel.channel_id = "ch-123"
        sample_channel.created_on = "2024-01-01"

        channels_client._patch.return_value = {"id": "ch-123"}

        channels_client.update("agent-123", "draft", "ch-123", sample_channel)

        call_args = channels_client._patch.call_args
        data = call_args[1]["data"]

        # Response-only fields should not be in request
        assert "channel_id" not in data
        assert "created_on" not in data


class TestChannelsClientDelete:
    """Tests for delete() method."""

    def test_delete_channel_success(self, channels_client):
        """Test deleting a channel."""
        channels_client._delete.return_value = {}

        channels_client.delete("agent-123", "draft", "twilio_whatsapp", "ch-123")

        channels_client._delete.assert_called_once_with("/orchestrate/agents/agent-123/environments/draft/channels/twilio_whatsapp/ch-123")


class TestChannelsClientEndpointConstruction:
    """Tests for proper API endpoint construction."""

    def test_endpoint_with_special_characters(self, channels_client):
        """Test endpoint construction with special characters in IDs."""
        channels_client._get.return_value = {"channels": []}

        channels_client.list("agent-with-dash", "draft")

        call_args = channels_client._get.call_args
        assert "agent-with-dash" in call_args[0][0]

    def test_endpoint_live_environment(self, channels_client):
        """Test endpoint construction with live environment."""
        channels_client._get.return_value = {"channels": []}

        channels_client.list("agent-123", "live")

        call_args = channels_client._get.call_args
        assert "/environments/live/" in call_args[0][0]


class TestChannelsClientInstantiation:
    """Tests for client instantiation."""

    def test_client_instantiation(self):
        """Test that client can be instantiated."""
        client = ChannelsClient(base_url="https://test.example.com")
        assert client is not None
        assert client.base_url == "https://test.example.com/v1/orchestrate"
