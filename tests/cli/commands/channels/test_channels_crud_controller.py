import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
from ibm_watsonx_orchestrate.cli.commands.channels.channels_controller import ChannelsController
from ibm_watsonx_orchestrate.agent_builder.channels import TwilioWhatsappChannel, SlackChannel
from ibm_watsonx_orchestrate.agent_builder.channels.types import ChannelType, SlackTeam
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest


@pytest.fixture
def controller():
    """Create a ChannelsController instance."""
    return ChannelsController()


@pytest.fixture
def mock_channels_client():
    """Create a mock channels client."""
    client = Mock()
    client.list = Mock(return_value=[])
    client.get = Mock(return_value=None)
    client.create = Mock(return_value={"id": "new-ch-id"})
    client.update = Mock(return_value={"id": "ch-123", "name": "updated"})
    client.delete = Mock()
    return client


@pytest.fixture
def mock_agent_client():
    """Create a mock agent client."""
    client = Mock()
    client.get_draft_by_name = Mock(return_value=[{"id": "agent-123", "name": "test_agent"}])
    return client


@pytest.fixture
def sample_channel():
    """Create a sample channel."""
    return TwilioWhatsappChannel(
        channel="twilio_whatsapp",
        name="test_channel",
        account_sid="AC" + "1" * 32,
        twilio_authentication_token="test_token"
    )


class TestGetAgentIdByName:
    """Tests for get_agent_id_by_name() method."""

    def test_get_agent_id_success(self, controller, mock_agent_client):
        """Test successful agent ID lookup by name."""
        with patch.object(controller, 'get_agent_client', return_value=mock_agent_client):
            agent_id = controller.get_agent_id_by_name("test_agent")

            assert agent_id == "agent-123"
            mock_agent_client.get_draft_by_name.assert_called_once_with("test_agent")

    def test_get_agent_id_not_found(self, controller, mock_agent_client):
        """Test agent not found raises SystemExit."""
        mock_agent_client.get_draft_by_name.return_value = []

        with patch.object(controller, 'get_agent_client', return_value=mock_agent_client):
            with pytest.raises(SystemExit):
                controller.get_agent_id_by_name("nonexistent_agent")

    def test_get_agent_id_multiple_found(self, controller, mock_agent_client):
        """Test multiple agents with same name raises SystemExit."""
        mock_agent_client.get_draft_by_name.return_value = [
            {"id": "agent-1", "name": "test_agent"},
            {"id": "agent-2", "name": "test_agent"}
        ]

        with patch.object(controller, 'get_agent_client', return_value=mock_agent_client):
            with pytest.raises(SystemExit):
                controller.get_agent_id_by_name("test_agent")


class TestImportChannel:
    """Tests for import_channel() method."""

    def test_import_from_yaml(self, controller):
        """Test importing channel from YAML file."""
        yaml_content = """
channel: twilio_whatsapp
name: imported_channel
account_sid: AC12345678901234567890123456789012
twilio_authentication_token: test_token
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            channels = controller.import_channel(temp_path)

            assert len(channels) == 1
            assert isinstance(channels[0], TwilioWhatsappChannel)
            assert channels[0].name == "imported_channel"
        finally:
            os.unlink(temp_path)

    def test_import_from_json(self, controller):
        """Test importing channel from JSON file."""
        json_content = """{
    "channel": "twilio_whatsapp",
    "name": "json_channel",
    "account_sid": "AC12345678901234567890123456789012",
    "twilio_authentication_token": "token"
}"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json_content)
            temp_path = f.name

        try:
            channels = controller.import_channel(temp_path)

            assert len(channels) == 1
            assert isinstance(channels[0], TwilioWhatsappChannel)
            assert channels[0].name == "json_channel"
        finally:
            os.unlink(temp_path)

    def test_import_file_not_found(self, controller):
        """Test importing non-existent file raises SystemExit."""
        with pytest.raises(SystemExit):
            controller.import_channel("/nonexistent/file.yaml")

    def test_import_invalid_channel(self, controller):
        """Test importing invalid channel raises SystemExit."""
        yaml_content = """
channel: invalid_channel_type
name: test
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            with pytest.raises(SystemExit):
                controller.import_channel(temp_path)
        finally:
            os.unlink(temp_path)

    def test_import_from_python_multiple_channels(self, controller):
        """Test importing multiple channels from Python file."""
        whatsapp_channel = TwilioWhatsappChannel(
            channel="twilio_whatsapp",
            name="whatsapp_channel",
            account_sid="AC12345678901234567890123456789012",
            twilio_authentication_token="token1"
        )

        another_whatsapp = TwilioWhatsappChannel(
            channel="twilio_whatsapp",
            name="another_channel",
            account_sid="AC98765432109876543210987654321098",
            twilio_authentication_token="token2"
        )

        with patch("ibm_watsonx_orchestrate.agent_builder.channels.channel.inspect.getmembers") as getmembers_mock, \
            patch("ibm_watsonx_orchestrate.agent_builder.channels.channel.importlib.import_module") as import_module_mock, \
            patch.object(Path, "exists", return_value=True):

            getmembers_mock.return_value = [
                ("whatsapp_channel", whatsapp_channel),
                ("another_whatsapp", another_whatsapp),
            ]

            channels = controller.import_channel("test.py")

            assert len(channels) == 2
            channel_names = [ch.name for ch in channels]
            assert "whatsapp_channel" in channel_names
            assert "another_channel" in channel_names


class TestCreateChannelFromArgs:
    """Tests for create_channel_from_args() method."""

    def test_create_webchat_blocked(self, controller):
        """Test creating webchat channel is blocked with helpful message."""
        with pytest.raises(SystemExit):
            controller.create_channel_from_args(
                channel_type=ChannelType.WEBCHAT,
                name="webchat_channel",
                description="This should fail"
            )

    def test_create_twilio_whatsapp_success(self, controller):
        """Test creating Twilio WhatsApp channel from CLI args."""
        channel = controller.create_channel_from_args(
            channel_type=ChannelType.TWILIO_WHATSAPP,
            name="cli_channel",
            description="Created from CLI",
            account_sid="AC" + "1" * 32,
            twilio_authentication_token="cli_token"
        )

        assert isinstance(channel, TwilioWhatsappChannel)
        assert channel.name == "cli_channel"
        assert channel.description == "Created from CLI"
        assert channel.account_sid == "AC" + "1" * 32

    def test_create_missing_account_sid(self, controller):
        """Test creating without account_sid raises SystemExit."""
        with pytest.raises(SystemExit):
            controller.create_channel_from_args(
                channel_type=ChannelType.TWILIO_WHATSAPP,
                name="test",
                twilio_authentication_token="token"
            )

    def test_create_missing_auth_token(self, controller):
        """Test creating without auth token raises SystemExit."""
        with pytest.raises(SystemExit):
            controller.create_channel_from_args(
                channel_type=ChannelType.TWILIO_WHATSAPP,
                name="test",
                account_sid="AC" + "1" * 32
            )

    def test_create_slack_missing_required_fields(self, controller):
        """Test creating Slack channel without required fields raises SystemExit."""
        with pytest.raises(SystemExit):
            controller.create_channel_from_args(
                channel_type=ChannelType.SLACK,
                name="test",
                client_id="test_id"  # Missing client_secret, signing_secret, and teams
            )

    def test_create_slack_success(self, controller):
        """Test creating Slack channel with all required fields using **kwargs."""
        channel = controller.create_channel_from_args(
            channel_type=ChannelType.SLACK,
            name="slack_channel",
            description="Slack integration",
            client_id="slack_client_id",
            client_secret="slack_client_secret",
            signing_secret="slack_signing_secret",
            teams=[{"id": "T12345", "bot_access_token": "xoxb-token"}]
        )

        assert isinstance(channel, SlackChannel)
        assert channel.name == "slack_channel"
        assert channel.client_id == "slack_client_id"
        assert channel.client_secret == "slack_client_secret"
        assert channel.signing_secret == "slack_signing_secret"
        assert len(channel.teams) == 1
        assert channel.teams[0].id == "T12345"

    def test_create_with_output_file(self, controller):
        """Test creating channel and saving to output file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name

        try:
            channel = controller.create_channel_from_args(
                channel_type=ChannelType.TWILIO_WHATSAPP,
                name="output_test",
                account_sid="AC" + "1" * 32,
                twilio_authentication_token="token",
                output_file=temp_path
            )

            assert isinstance(channel, TwilioWhatsappChannel)
            assert os.path.exists(temp_path)

            # Verify file content
            with open(temp_path, 'r') as f:
                content = f.read()
                assert "twilio_whatsapp" in content
                assert "output_test" in content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_create_invalid_output_extension(self, controller):
        """Test creating with invalid output file extension raises SystemExit."""
        with pytest.raises(SystemExit):
            controller.create_channel_from_args(
                channel_type=ChannelType.TWILIO_WHATSAPP,
                name="test",
                account_sid="AC" + "1" * 32,
                twilio_authentication_token="token",
                output_file="output.txt"  # Invalid extension
            )


@patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev', return_value=False)
class TestListChannels:
    """Tests for list_channels() method."""

    def test_list_webchat_channels_blocked(self, mock_is_local_dev, controller):
        """Test listing webchat channels is blocked with helpful message."""
        with pytest.raises(SystemExit):
            controller.list_channels_agent("agent-123", "draft", channel_type=ChannelType.WEBCHAT)

    def test_list_channels_success(self, mock_is_local_dev, controller, mock_channels_client):
        """Test listing channels successfully."""
        mock_channels_client.list.return_value = [
            {"id": "ch1", "name": "channel1", "channel": "twilio_whatsapp", "created_on": "2024-01-01"},
            {"id": "ch2", "name": "channel2", "channel": "slack", "created_on": "2024-01-02"}
        ]

        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            with patch('rich.console.Console.print'):  # Mock console output
                result = controller.list_channels_agent("agent-123", "draft")

                assert len(result) == 2
                mock_channels_client.list.assert_called_once_with("agent-123", "draft", None)

    def test_list_channels_with_type_filter(self, mock_is_local_dev, controller, mock_channels_client):
        """Test listing channels filtered by type."""
        mock_channels_client.list.return_value = [
            {"id": "ch1", "name": "channel1", "channel": "twilio_whatsapp", "created_on": "2024-01-01"}
        ]

        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            with patch('rich.console.Console.print'):
                controller.list_channels_agent("agent-123", "draft", channel_type=ChannelType.TWILIO_WHATSAPP)

                mock_channels_client.list.assert_called_once_with("agent-123", "draft", "twilio_whatsapp")

    def test_list_channels_empty(self, mock_is_local_dev, controller, mock_channels_client):
        """Test listing when no channels exist."""
        mock_channels_client.list.return_value = []

        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            result = controller.list_channels_agent("agent-123", "draft")

            assert result == []

    def test_list_channels_verbose(self, mock_is_local_dev, controller, mock_channels_client):
        """Test listing channels in verbose mode (JSON output)."""
        mock_channels_client.list.return_value = [
            {"id": "ch1", "name": "channel1"}
        ]

        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            with patch('rich.print_json') as mock_print_json:
                controller.list_channels_agent("agent-123", "draft", verbose=True)

                mock_print_json.assert_called_once()


@patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev', return_value=False)
class TestGetChannel:
    """Tests for get_channel() method."""

    def test_get_webchat_channel_blocked(self, mock_is_local_dev, controller):
        """Test getting webchat channel is blocked with helpful message."""
        with pytest.raises(SystemExit):
            controller.get_channel("agent-123", "draft", ChannelType.WEBCHAT, "ch1")

    def test_get_channel_success(self, mock_is_local_dev, controller, mock_channels_client):
        """Test getting a channel successfully."""
        mock_channels_client.get.return_value = {
            "id": "ch1",
            "name": "test_channel",
            "channel": "twilio_whatsapp",
            "description": "Test channel"
        }

        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            with patch('rich.print'):
                result = controller.get_channel("agent-123", "draft", "twilio_whatsapp", "ch1")

                assert result["id"] == "ch1"
                mock_channels_client.get.assert_called_once_with("agent-123", "draft", "twilio_whatsapp", "ch1")

    def test_get_channel_not_found(self, mock_is_local_dev, controller, mock_channels_client):
        """Test getting non-existent channel raises SystemExit."""
        mock_channels_client.get.return_value = None

        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            with pytest.raises(SystemExit):
                controller.get_channel("agent-123", "draft", "twilio_whatsapp", "nonexistent")


@patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev', return_value=False)
class TestCreateChannel:
    """Tests for create_channel() method."""

    def test_create_channel_success(self, mock_is_local_dev, controller, mock_channels_client, sample_channel):
        """Test creating a channel successfully."""
        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            channel_id = controller.create_channel("agent-123", "draft", sample_channel)

            assert channel_id == "new-ch-id"
            mock_channels_client.list.assert_called_once_with("agent-123", "draft", "twilio_whatsapp")
            mock_channels_client.create.assert_called_once_with("agent-123", "draft", sample_channel)

    def test_create_channel_failure(self, mock_is_local_dev, controller, mock_channels_client, sample_channel):
        """Test creating channel with API error raises SystemExit."""
        mock_channels_client.create.side_effect = Exception("API Error")

        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            with pytest.raises(SystemExit):
                controller.create_channel("agent-123", "draft", sample_channel)

    def test_create_channel_duplicate_type_same_environment(self, mock_is_local_dev, controller, mock_channels_client, sample_channel):
        """Test creating a duplicate channel type in the same environment raises SystemExit."""

        mock_channels_client.list.return_value = [
            {"id": "existing-ch-id", "name": "existing_channel", "channel": "twilio_whatsapp"}
        ]

        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            with pytest.raises(SystemExit):
                controller.create_channel("agent-123", "draft", sample_channel)

            mock_channels_client.list.assert_called_once_with("agent-123", "draft", "twilio_whatsapp")
            mock_channels_client.create.assert_not_called()

    def test_create_channel_same_type_different_environment(self, mock_is_local_dev, controller, mock_channels_client):
        """Test creating same channel type in different environments is allowed."""
        channel_draft = TwilioWhatsappChannel(
            channel="twilio_whatsapp",
            name="draft_channel",
            account_sid="AC" + "1" * 32,
            twilio_authentication_token="test_token"
        )
        channel_live = TwilioWhatsappChannel(
            channel="twilio_whatsapp",
            name="live_channel",
            account_sid="AC" + "2" * 32,
            twilio_authentication_token="test_token2"
        )

        mock_channels_client.list.return_value = []
        mock_channels_client.create.side_effect = [
            {"id": "draft-ch-id"},
            {"id": "live-ch-id"}
        ]

        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            draft_id = controller.create_channel("agent-123", "draft", channel_draft)
            assert draft_id == "draft-ch-id"

            live_id = controller.create_channel("agent-123", "live", channel_live)
            assert live_id == "live-ch-id"

            assert mock_channels_client.create.call_count == 2

    def test_create_channel_after_deletion(self, mock_is_local_dev, controller, mock_channels_client, sample_channel):
        """Test creating a channel of same type after deleting the previous one is allowed."""
        new_channel = TwilioWhatsappChannel(
            channel="twilio_whatsapp",
            name="new_channel",
            account_sid="AC" + "2" * 32,
            twilio_authentication_token="new_token"
        )

        mock_channels_client.list.side_effect = [
            [{"id": "old-ch-id", "name": "old_channel", "channel": "twilio_whatsapp"}],
            []
        ]
        mock_channels_client.create.return_value = {"id": "new-ch-id"}

        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            # fail - channel exists
            with pytest.raises(SystemExit):
                controller.create_channel("agent-123", "draft", sample_channel)

            # Delete the existing channel
            controller.delete_channel("agent-123", "draft", "twilio_whatsapp", "old-ch-id")

            # succeed - no existing channels
            new_id = controller.create_channel("agent-123", "draft", new_channel)
            assert new_id == "new-ch-id"
            mock_channels_client.create.assert_called_once_with("agent-123", "draft", new_channel)


@patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev', return_value=False)
class TestUpdateChannel:
    """Tests for update_channel() method."""

    def test_update_channel_partial(self, mock_is_local_dev, controller, mock_channels_client, sample_channel):
        """Test partial update of a channel."""
        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            result = controller.update_channel("agent-123", "draft", "ch-123", sample_channel, partial=True)

            assert result["id"] == "ch-123"
            mock_channels_client.update.assert_called_once_with("agent-123", "draft", "ch-123", sample_channel, True)

    def test_update_channel_full(self, mock_is_local_dev, controller, mock_channels_client, sample_channel):
        """Test full update of a channel."""
        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            controller.update_channel("agent-123", "draft", "ch-123", sample_channel, partial=False)

            mock_channels_client.update.assert_called_once_with("agent-123", "draft", "ch-123", sample_channel, False)


@patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev', return_value=False)
class TestPublishOrUpdateChannel:
    """Tests for publish_or_update_channel() method."""

    def test_publish_webchat_channel_warning(self, mock_is_local_dev, controller):
        """Test publishing webchat channel shows warning and doesn't create."""
        from ibm_watsonx_orchestrate.agent_builder.channels import WebchatChannel

        webchat_channel = WebchatChannel(
            channel="webchat",
            name="test_webchat"
        )

        with patch.object(controller, 'get_channels_client') as mock_get_client:
            result = controller.publish_or_update_channel("agent-123", "draft", webchat_channel)

            # Should return a message instead of trying to create
            assert "Webchat is available" in result
            assert "agent-123" in result
            assert "draft" in result
            # Should not attempt to get the client or create channel
            mock_get_client.assert_not_called()

    def test_publish_new_channel(self, mock_is_local_dev, controller, mock_channels_client, sample_channel):
        """Test publishing a new channel (no existing channel)."""
        mock_channels_client.list.return_value = []
        mock_channels_client.base_url = "https://example.com/v1/orchestrate"

        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            with patch.object(controller, 'create_channel', return_value="new-id") as mock_create:
                # Mock is_local_dev to return False for decorator and get_channel_event_url
                with patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev') as mock_local:
                    mock_local.return_value = False
                    event_url = controller.publish_or_update_channel("agent-123", "draft", sample_channel)

                # Refactored code returns /events for SaaS (non-/instances/ URLs fall back to default format)
                assert event_url == "https://example.com/agents/agent-123/environments/draft/channels/twilio_whatsapp/new-id/events"
                mock_create.assert_called_once()

    def test_update_existing_channel(self, mock_is_local_dev, controller, mock_channels_client, sample_channel):
        """Test updating an existing channel by name."""
        mock_channels_client.list.return_value = [
            {"id": "existing-id", "name": "test_channel", "channel": "twilio_whatsapp"}
        ]
        mock_channels_client.base_url = "https://example.com/v1/orchestrate"

        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            with patch.object(controller, 'update_channel') as mock_update:
                # Mock is_local_dev to return False for decorator and get_channel_event_url
                with patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev') as mock_local:
                    mock_local.return_value = False
                    event_url = controller.publish_or_update_channel("agent-123", "draft", sample_channel)

                # Refactored code returns /events for SaaS (non-/instances/ URLs fall back to default format)
                assert event_url == "https://example.com/agents/agent-123/environments/draft/channels/twilio_whatsapp/existing-id/events"
                mock_update.assert_called_once_with("agent-123", "draft", "existing-id", sample_channel, partial=True)

    def test_publish_with_new_name(self, mock_is_local_dev, controller, mock_channels_client):
        """Test publishing channel with name that doesn't exist creates new channel."""
        channel = TwilioWhatsappChannel(
            name="new_channel",
            channel="twilio_whatsapp",
            account_sid="AC" + "1" * 32,
            twilio_authentication_token="token"
        )
        mock_channels_client.base_url = "https://example.com/v1/orchestrate"
        mock_channels_client.list.return_value = []  # No existing channels with this name

        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            with patch.object(controller, 'create_channel', return_value="new-id") as mock_create:
                # Mock is_local_dev to return False for decorator and get_channel_event_url
                with patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev') as mock_local:
                    mock_local.return_value = False
                    event_url = controller.publish_or_update_channel("agent-123", "draft", channel)

                # Refactored code returns /events for SaaS (non-/instances/ URLs fall back to default format)
                assert event_url == "https://example.com/agents/agent-123/environments/draft/channels/twilio_whatsapp/new-id/events"
                mock_create.assert_called_once()


class TestGetChannelEventUrl:
    """Tests for get_channel_event_url() and helper methods."""

    def test_build_local_event_url(self, controller):
        """Test building event URL for local environment."""
        result = controller._build_local_event_url(
            agent_id="agent-123",
            environment_id="env-456",
            channel_api_path="slack",
            channel_id="ch-789"
        )
        
        assert result == "/v1/agents/agent-123/environments/env-456/channels/slack/ch-789/runs"

    def test_build_saas_event_url_with_subscription(self, controller, mock_channels_client):
        """Test building SaaS event URL with subscription ID."""
        mock_channels_client.base_url = "https://api.example.com/instances/inst-456/v1/orchestrate"
        mock_channels_client.get_subscription_id = Mock(return_value="sub-12345")

        result = controller._build_saas_event_url(
            client=mock_channels_client,
            agent_id="agent-123",
            environment_id="env-789",
            channel_api_path="twilio_whatsapp",
            channel_id="ch-abc"
        )

        expected = "https://channels.example.com/tenants/sub-12345_inst-456/agents/agent-123/environments/env-789/channels/twilio_whatsapp/ch-abc/events"
        assert result == expected

    def test_build_saas_event_url_without_subscription(self, controller, mock_channels_client):
        """Test building SaaS event URL without subscription ID (fallback)."""
        mock_channels_client.base_url = "https://api.example.com/instances/inst-456/v1/orchestrate"
        mock_channels_client.get_subscription_id = Mock(return_value=None)

        result = controller._build_saas_event_url(
            client=mock_channels_client,
            agent_id="agent-123",
            environment_id="env-789",
            channel_api_path="slack",
            channel_id="ch-xyz"
        )

        expected = "https://channels.example.com/tenants/inst-456/agents/agent-123/environments/env-789/channels/slack/ch-xyz/events"
        assert result == expected

    def test_build_saas_event_url_no_instances_path(self, controller, mock_channels_client):
        """Test building SaaS event URL when /instances/ is not in URL (fallback)."""
        mock_channels_client.base_url = "https://api.example.com/v1/orchestrate"
        mock_channels_client.get_subscription_id = Mock(return_value="sub-12345")

        result = controller._build_saas_event_url(
            client=mock_channels_client,
            agent_id="agent-123",
            environment_id="env-789",
            channel_api_path="webchat",
            channel_id="ch-def"
        )

        expected = "https://api.example.com/agents/agent-123/environments/env-789/channels/webchat/ch-def/events"
        assert result == expected

    def test_get_channel_event_url_local(self, controller, mock_channels_client):
        """Test get_channel_event_url for local environment."""
        mock_channels_client.base_url = "http://localhost:4321/v1/orchestrate"
        
        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            result = controller.get_channel_event_url(
                agent_id="agent-123",
                environment_id="env-456",
                channel_api_path="slack",
                channel_id="ch-789"
            )
            
            assert result == "/v1/agents/agent-123/environments/env-456/channels/slack/ch-789/runs"

    def test_get_channel_event_url_saas(self, controller, mock_channels_client):
        """Test get_channel_event_url for SaaS environment."""
        mock_channels_client.base_url = "https://api.example.com/instances/inst-456/v1/orchestrate"
        mock_channels_client.get_subscription_id = Mock(return_value="sub-12345")

        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            result = controller.get_channel_event_url(
                agent_id="agent-123",
                environment_id="env-789",
                channel_api_path="twilio_whatsapp",
                channel_id="ch-abc"
            )

            expected = "https://channels.example.com/tenants/sub-12345_inst-456/agents/agent-123/environments/env-789/channels/twilio_whatsapp/ch-abc/events"
            assert result == expected

    def test_get_channel_event_url_127_0_0_1(self, controller, mock_channels_client):
        """Test get_channel_event_url recognizes 127.0.0.1 as local."""
        mock_channels_client.base_url = "http://127.0.0.1:4321/v1/orchestrate"
        
        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            result = controller.get_channel_event_url(
                agent_id="agent-123",
                environment_id="env-456",
                channel_api_path="webchat",
                channel_id="ch-999"
            )
            
            assert result == "/v1/agents/agent-123/environments/env-456/channels/webchat/ch-999/runs"


@patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev', return_value=False)
class TestExportChannel:
    """Tests for export_channel() method."""

    def test_export_channel_to_file(self, mock_is_local_dev, controller, mock_channels_client):
        """Test exporting a channel to YAML file."""
        mock_channels_client.get.return_value = {
            "id": "ch1",
            "name": "export_test",
            "channel": "twilio_whatsapp",
            "account_sid": "AC" + "1" * 32,
            "twilio_authentication_token": "token",
            "tenant_id": "tenant-123"  # Should be excluded
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name

        try:
            with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
                controller.export_channel("agent-123", "draft", "twilio_whatsapp", "ch1", temp_path)

                assert os.path.exists(temp_path)

                # Verify exported content
                with open(temp_path, 'r') as f:
                    content = f.read()
                    assert "export_test" in content
                    assert "twilio_whatsapp" in content
                    assert "tenant_id" not in content  # Response-only field excluded
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_channel_invalid_extension(self, mock_is_local_dev, controller, mock_channels_client):
        """Test exporting with invalid file extension raises SystemExit."""
        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            with pytest.raises(SystemExit):
                controller.export_channel("agent-123", "draft", "twilio_whatsapp", "ch1", "output.txt")


@patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev', return_value=False)
class TestDeleteChannel:
    """Tests for delete_channel() method."""

    def test_delete_channel_success(self, mock_is_local_dev, controller, mock_channels_client):
        """Test deleting a channel successfully."""
        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            controller.delete_channel("agent-123", "draft", "twilio_whatsapp", "ch-123")

            mock_channels_client.delete.assert_called_once_with("agent-123", "draft", "twilio_whatsapp", "ch-123")

    def test_delete_channel_failure(self, mock_is_local_dev, controller, mock_channels_client):
        """Test deleting channel with API error raises SystemExit."""
        mock_channels_client.delete.side_effect = Exception("Delete failed")

        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            with pytest.raises(SystemExit):
                controller.delete_channel("agent-123", "draft", "twilio_whatsapp", "ch-123")


class TestLocalDevBlock:
    """Tests for local dev blocking functionality."""

    @patch("ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev")
    def test_block_when_local_dev_without_developer_mode(self, mock_is_local_dev, controller):
        """Test that operations are blocked in local dev without developer mode."""
        mock_is_local_dev.return_value = True

        with pytest.raises(SystemExit) as exc_info:
            controller._check_local_dev_block(enable_developer_mode=False)

        assert exc_info.value.code == 1

    @patch("ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev")
    @patch("ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.logger")
    def test_allow_when_local_dev_with_developer_mode(self, mock_logger, mock_is_local_dev, controller):
        """Test that operations are allowed in local dev with developer mode enabled."""
        mock_is_local_dev.return_value = True

        # Should not raise
        controller._check_local_dev_block(enable_developer_mode=True)

        # Verify warning messages were shown
        assert mock_logger.warning.call_count == 3
        warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
        assert "DEVELOPER MODE ENABLED - Proceed at your own risk! No official support will be provided." in warning_calls
        assert "Channel operations in local development may cause unexpected behavior." in warning_calls
        assert "This environment is not validated for production use." in warning_calls

    @patch("ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev")
    def test_allow_when_not_local_dev(self, mock_is_local_dev, controller):
        """Test that operations are allowed when not in local dev."""
        mock_is_local_dev.return_value = False

        controller._check_local_dev_block(enable_developer_mode=False)

    @patch("ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev")
    def test_allow_when_not_local_dev_with_developer_mode(self, mock_is_local_dev, controller):
        """Test that operations are allowed when not in local dev with developer mode."""
        mock_is_local_dev.return_value = False

        controller._check_local_dev_block(enable_developer_mode=True)

    @patch("ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev")
    @patch("ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.logger")
    def test_error_message_when_blocked(self, mock_logger, mock_is_local_dev, controller):
        """Test that correct error messages are shown when blocked."""
        mock_is_local_dev.return_value = True

        with pytest.raises(SystemExit):
            controller._check_local_dev_block(enable_developer_mode=False)

        assert mock_logger.error.call_count == 1
        mock_logger.warning.assert_not_called()

        mock_logger.error.assert_called_once_with("Channel authoring is not available in local development environment.")


class TestDecoratorBlocksInLocalDev:
    """Tests that verify the @block_local_dev decorator blocks controller methods in local dev."""

    @patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev', return_value=True)
    def test_list_channels_blocked_in_local_dev(self, mock_is_local_dev, controller):
        """Test list_channels_agent is blocked in local dev without developer mode."""
        with pytest.raises(SystemExit) as exc_info:
            controller.list_channels_agent("agent-123", "env-456")

        assert exc_info.value.code == 1

    @patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev', return_value=True)
    def test_get_channel_blocked_in_local_dev(self, mock_is_local_dev, controller):
        """Test get_channel is blocked in local dev without developer mode."""
        with pytest.raises(SystemExit) as exc_info:
            controller.get_channel("agent-123", "env-456", ChannelType.TWILIO_WHATSAPP, "ch-789")

        assert exc_info.value.code == 1

    @patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev', return_value=True)
    def test_publish_or_update_channel_blocked_in_local_dev(self, mock_is_local_dev, controller, sample_channel):
        """Test publish_or_update_channel is blocked in local dev without developer mode."""
        with pytest.raises(SystemExit) as exc_info:
            controller.publish_or_update_channel("agent-123", "env-456", sample_channel)

        assert exc_info.value.code == 1

    @patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev', return_value=True)
    def test_export_channel_blocked_in_local_dev(self, mock_is_local_dev, controller):
        """Test export_channel is blocked in local dev without developer mode."""
        with pytest.raises(SystemExit) as exc_info:
            controller.export_channel("agent-123", "env-456", ChannelType.TWILIO_WHATSAPP, "ch-789", "/tmp/output.yaml")

        assert exc_info.value.code == 1

    @patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev', return_value=True)
    def test_delete_channel_blocked_in_local_dev(self, mock_is_local_dev, controller):
        """Test delete_channel is blocked in local dev without developer mode."""
        with pytest.raises(SystemExit) as exc_info:
            controller.delete_channel("agent-123", "env-456", ChannelType.TWILIO_WHATSAPP, "ch-789")

        assert exc_info.value.code == 1

    @patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev', return_value=False)
    def test_methods_not_blocked_when_not_local_dev(self, mock_is_local_dev, controller, mock_channels_client):
        """Test that decorated methods work normally when not in local dev."""
        # This should NOT raise SystemExit
        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            with patch('rich.console.Console.print'):
                result = controller.list_channels_agent("agent-123", "env-456")
                # Should return empty list from mock
                assert result == []

    @patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.is_local_dev', return_value=True)
    @patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.logger')
    def test_methods_allowed_with_enable_developer_mode(self, mock_logger, mock_is_local_dev, controller, mock_channels_client):
        """Test that methods work in local dev when enable_developer_mode=True is passed as kwarg."""
        # This should NOT raise SystemExit when enable_developer_mode=True
        with patch.object(controller, 'get_channels_client', return_value=mock_channels_client):
            with patch('rich.console.Console.print'):
                result = controller.list_channels_agent("agent-123", "env-456", enable_developer_mode=True)
                assert result == []
                assert mock_logger.warning.call_count == 3
                warning_messages = [call[0][0] for call in mock_logger.warning.call_args_list]
                assert "DEVELOPER MODE ENABLED" in warning_messages[0]
