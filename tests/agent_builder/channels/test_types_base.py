import pytest
from ibm_watsonx_orchestrate.agent_builder.channels import ChannelType
from ibm_watsonx_orchestrate.agent_builder.channels.types import ChannelKind


class TestChannelType:
    """Tests for ChannelType enum."""

    def test_channel_type_values(self):
        """Test that all expected channel types exist."""
        assert ChannelType.WEBCHAT.value == "webchat"
        assert ChannelType.TWILIO_WHATSAPP.value == "twilio_whatsapp"
        assert ChannelType.TWILIO_SMS.value == "twilio_sms"
        assert ChannelType.SLACK.value == "byo_slack"
        assert ChannelType.GENESYS_BOT_CONNECTOR.value == "genesys_bot_connector"
        assert ChannelType.FACEBOOK.value == "facebook"
        assert ChannelType.TEAMS.value == "teams"

    def test_channel_type_string_representation(self):
        """Test that channel type converts to string correctly."""
        assert str(ChannelType.WEBCHAT) == "webchat"
        assert str(ChannelType.TWILIO_WHATSAPP) == "twilio_whatsapp"
        assert str(ChannelType.TWILIO_SMS) == "twilio_sms"
        assert str(ChannelType.SLACK) == "byo_slack"
        assert str(ChannelType.GENESYS_BOT_CONNECTOR) == "genesys_bot_connector"
        assert str(ChannelType.FACEBOOK) == "facebook"
        assert str(ChannelType.TEAMS) == "teams"


class TestChannelKind:
    """Tests for ChannelKind enum."""

    def test_channel_kind_value(self):
        """Test that channel kind has correct value."""
        assert ChannelKind.CHANNEL.value == "channel"

    def test_channel_kind_string_representation(self):
        """Test that channel kind converts to string correctly."""
        assert str(ChannelKind.CHANNEL) == "channel"
