import pytest
from pydantic_core import ValidationError
from ibm_watsonx_orchestrate.agent_builder.channels import TwilioWhatsappChannel
from ibm_watsonx_orchestrate.agent_builder.agents.types import SpecVersion
from ibm_watsonx_orchestrate.agent_builder.channels.types import ChannelKind


@pytest.fixture()
def valid_twilio_whatsapp_channel():
    return {
        "channel": "twilio_whatsapp",
        "name": "test_whatsapp_channel",
        "description": "Test WhatsApp channel",
        "account_sid": "AC" + "1" * 32,
        "twilio_authentication_token": "test_token_123"
    }


@pytest.fixture()
def minimal_twilio_whatsapp_channel():
    return {
        "channel": "twilio_whatsapp",
        "name": "test_channel",
        "account_sid": "AC" + "a" * 32,
        "twilio_authentication_token": "token"
    }


class TestTwilioWhatsappChannel:
    """Tests for TwilioWhatsappChannel validation."""

    def test_valid_channel_creation(self, valid_twilio_whatsapp_channel):
        """Test creating a valid Twilio WhatsApp channel."""
        channel = TwilioWhatsappChannel(**valid_twilio_whatsapp_channel)

        assert channel.channel == "twilio_whatsapp"
        assert channel.name == "test_whatsapp_channel"
        assert channel.description == "Test WhatsApp channel"
        assert channel.account_sid == "AC" + "1" * 32
        assert channel.twilio_authentication_token == "test_token_123"

    def test_minimal_channel_creation(self, minimal_twilio_whatsapp_channel):
        """Test creating a channel with only required fields."""
        channel = TwilioWhatsappChannel(**minimal_twilio_whatsapp_channel)

        assert channel.channel == "twilio_whatsapp"
        assert channel.name == "test_channel"
        assert channel.description is None
        assert channel.account_sid == "AC" + "a" * 32

    def test_default_values(self, minimal_twilio_whatsapp_channel):
        """Test that default values are set correctly."""
        channel = TwilioWhatsappChannel(**minimal_twilio_whatsapp_channel)

        assert channel.spec_version == SpecVersion.V1
        assert channel.kind == ChannelKind.CHANNEL

    def test_missing_account_sid(self):
        """Test that missing account_sid raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioWhatsappChannel(
                channel="twilio_whatsapp",
                name="test_channel",
                twilio_authentication_token="token"
            )

        assert "account_sid" in str(exc_info.value)

    def test_missing_auth_token(self):
        """Test that missing auth token raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioWhatsappChannel(
                channel="twilio_whatsapp",
                name="test_channel",
                account_sid="AC" + "1" * 32
            )

        assert "twilio_authentication_token" in str(exc_info.value)

    def test_invalid_account_sid_length_short(self):
        """Test that account_sid with wrong length fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioWhatsappChannel(
                channel="twilio_whatsapp",
                name="test_channel",
                account_sid="AC123",  # Too short
                twilio_authentication_token="token"
            )

        assert "account_sid" in str(exc_info.value)

    def test_invalid_account_sid_length_long(self):
        """Test that account_sid with wrong length fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioWhatsappChannel(
                channel="twilio_whatsapp",
                name="test_channel",
                account_sid="AC" + "1" * 33,  # Too long
                twilio_authentication_token="token"
            )

        assert "account_sid" in str(exc_info.value)

    def test_invalid_account_sid_pattern(self):
        """Test that account_sid not starting with AC fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioWhatsappChannel(
                channel="twilio_whatsapp",
                name="test_channel",
                account_sid="AB" + "1" * 32,  # Should start with AC
                twilio_authentication_token="token"
            )

        assert "account_sid" in str(exc_info.value)

    def test_name_max_length(self):
        """Test that name exceeding max length fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioWhatsappChannel(
                channel="twilio_whatsapp",
                name="a" * 65,  # Max is 64
                account_sid="AC" + "1" * 32,
                twilio_authentication_token="token"
            )

        assert "name" in str(exc_info.value)

    def test_description_max_length(self):
        """Test that description exceeding max length fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioWhatsappChannel(
                channel="twilio_whatsapp",
                name="test_channel",
                description="a" * 1025,  # Max is 1024
                account_sid="AC" + "1" * 32,
                twilio_authentication_token="token"
            )

        assert "description" in str(exc_info.value)

    def test_channel_type_locked(self):
        """Test that channel type is always twilio_whatsapp."""
        channel = TwilioWhatsappChannel(
            channel="twilio_whatsapp",
            name="test_channel",
            account_sid="AC" + "1" * 32,
            twilio_authentication_token="token"
        )

        assert channel.channel == "twilio_whatsapp"

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioWhatsappChannel(
                channel="twilio_whatsapp",
                name="test_channel",
                account_sid="AC" + "1" * 32,
                twilio_authentication_token="token",
                unknown_field="value"
            )

        assert "unknown_field" in str(exc_info.value).lower() or "extra" in str(exc_info.value).lower()

    def test_dumps_spec(self, valid_twilio_whatsapp_channel):
        """Test dumps_spec method excludes response-only fields."""
        channel = TwilioWhatsappChannel(**valid_twilio_whatsapp_channel)

        # Manually set response-only fields (simulating API response)
        channel.channel_id = "ch-123"
        channel.tenant_id = "tenant-456"

        spec_json = channel.dumps_spec()

        # Response-only fields should be excluded
        assert "channel_id" not in spec_json
        assert "tenant_id" not in spec_json
        assert "agent_id" not in spec_json

        # User-editable fields should be included
        assert "twilio_whatsapp" in spec_json
        assert "test_whatsapp_channel" in spec_json

    def test_dumps_spec_exclude_none(self, minimal_twilio_whatsapp_channel):
        """Test dumps_spec with exclude_none option."""
        channel = TwilioWhatsappChannel(**minimal_twilio_whatsapp_channel)

        spec_json = channel.dumps_spec(exclude_none=True)

        # None fields should be excluded
        assert "description" not in spec_json

        # Required fields should be included
        assert "name" in spec_json
        assert "account_sid" in spec_json
        assert "twilio_authentication_token" in spec_json
