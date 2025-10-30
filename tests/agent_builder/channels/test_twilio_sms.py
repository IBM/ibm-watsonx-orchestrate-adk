import pytest
from pydantic_core import ValidationError
from ibm_watsonx_orchestrate.agent_builder.channels import TwilioSMSChannel
from ibm_watsonx_orchestrate.agent_builder.agents.types import SpecVersion
from ibm_watsonx_orchestrate.agent_builder.channels.types import ChannelKind


@pytest.fixture()
def valid_twilio_sms_channel():
    return {
        "channel": "twilio_sms",
        "name": "test_sms_channel",
        "description": "Test sms channel",
        "account_sid": "AC" + "1" * 32,
        "twilio_authentication_token": "test_token_123",
        "phone_number": "+1234567890"
    }


@pytest.fixture()
def minimal_twilio_sms_channel():
    return {
        "channel": "twilio_sms",
        "name": "test_channel",
        "account_sid": "AC" + "a" * 32,
        "twilio_authentication_token": "token"
    }


class TestTwilioSMSChannel:
    """Tests for TwilioSMSChannel validation."""

    def test_valid_channel_creation(self, valid_twilio_sms_channel):
        """Test creating a valid Twilio SMS channel."""
        channel = TwilioSMSChannel(**valid_twilio_sms_channel)

        assert channel.channel == "twilio_sms"
        assert channel.name == "test_sms_channel"
        assert channel.description == "Test sms channel"
        assert channel.account_sid == "AC" + "1" * 32
        assert channel.twilio_authentication_token == "test_token_123"
        assert channel.phone_number == "+1234567890"

    def test_minimal_channel_creation(self, minimal_twilio_sms_channel):
        """Test creating a channel with only required fields."""
        channel = TwilioSMSChannel(**minimal_twilio_sms_channel)

        assert channel.channel == "twilio_sms"
        assert channel.name == "test_channel"
        assert channel.description is None
        assert channel.phone_number is None  # Optional field
        assert channel.account_sid == "AC" + "a" * 32

    def test_default_values(self, minimal_twilio_sms_channel):
        """Test that default values are set correctly."""
        channel = TwilioSMSChannel(**minimal_twilio_sms_channel)

        assert channel.spec_version == SpecVersion.V1
        assert channel.kind == ChannelKind.CHANNEL

    def test_missing_account_sid(self):
        """Test that missing account_sid raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioSMSChannel(
                channel="twilio_sms",
                name="test_channel",
                twilio_authentication_token="token"
            )

        assert "account_sid" in str(exc_info.value)

    def test_missing_auth_token(self):
        """Test that missing auth token raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioSMSChannel(
                channel="twilio_sms",
                name="test_channel",
                account_sid="AC" + "1" * 32
            )

        assert "twilio_authentication_token" in str(exc_info.value)

    def test_invalid_account_sid_length_short(self):
        """Test that account_sid with wrong length fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioSMSChannel(
                channel="twilio_sms",
                name="test_channel",
                account_sid="AC123",  # Too short
                twilio_authentication_token="token"
            )

        assert "account_sid" in str(exc_info.value)

    def test_invalid_account_sid_length_long(self):
        """Test that account_sid with wrong length fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioSMSChannel(
                channel="twilio_sms",
                name="test_channel",
                account_sid="AC" + "1" * 33,  # Too long
                twilio_authentication_token="token"
            )

        assert "account_sid" in str(exc_info.value)

    def test_invalid_account_sid_pattern(self):
        """Test that account_sid not starting with AC fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioSMSChannel(
                channel="twilio_sms",
                name="test_channel",
                account_sid="AB" + "1" * 32,  # Should start with AC
                twilio_authentication_token="token"
            )

        assert "account_sid" in str(exc_info.value)

    def test_name_max_length(self):
        """Test that name exceeding max length fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioSMSChannel(
                channel="twilio_sms",
                name="a" * 65,  # Max is 64
                account_sid="AC" + "1" * 32,
                twilio_authentication_token="token"
            )

        assert "name" in str(exc_info.value)

    def test_description_max_length(self):
        """Test that description exceeding max length fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioSMSChannel(
                channel="twilio_sms",
                name="test_channel",
                description="a" * 1025,  # Max is 1024
                account_sid="AC" + "1" * 32,
                twilio_authentication_token="token"
            )

        assert "description" in str(exc_info.value)

    def test_channel_type_locked(self):
        """Test that channel type is always twilio_sms."""
        channel = TwilioSMSChannel(
            channel="twilio_sms",
            name="test_channel",
            account_sid="AC" + "1" * 32,
            twilio_authentication_token="token"
        )

        assert channel.channel == "twilio_sms"

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            TwilioSMSChannel(
                channel="twilio_sms",
                name="test_channel",
                account_sid="AC" + "1" * 32,
                twilio_authentication_token="token",
                unknown_field="value"
            )

        assert "unknown_field" in str(exc_info.value).lower() or "extra" in str(exc_info.value).lower()

    def test_phone_number_optional(self):
        """Test that phone_number is optional."""
        # Without phone_number
        channel1 = TwilioSMSChannel(
            channel="twilio_sms",
            name="test_channel",
            account_sid="AC" + "1" * 32,
            twilio_authentication_token="token"
        )
        assert channel1.phone_number is None

        # With phone_number
        channel2 = TwilioSMSChannel(
            channel="twilio_sms",
            name="test_channel",
            account_sid="AC" + "1" * 32,
            twilio_authentication_token="token",
            phone_number="+1234567890"
        )
        assert channel2.phone_number == "+1234567890"

    def test_dumps_spec(self, valid_twilio_sms_channel):
        """Test dumps_spec method excludes response-only fields."""
        channel = TwilioSMSChannel(**valid_twilio_sms_channel)

        # Manually set response-only fields (simulating API response)
        channel.channel_id = "ch-123"
        channel.tenant_id = "tenant-456"

        spec_json = channel.dumps_spec()

        # Response-only fields should be excluded
        assert "channel_id" not in spec_json
        assert "tenant_id" not in spec_json
        assert "agent_id" not in spec_json

        # User-editable fields should be included
        assert "twilio_sms" in spec_json
        assert "test_sms_channel" in spec_json
        assert "+1234567890" in spec_json

    def test_dumps_spec_exclude_none(self, minimal_twilio_sms_channel):
        """Test dumps_spec with exclude_none option."""
        channel = TwilioSMSChannel(**minimal_twilio_sms_channel)

        spec_json = channel.dumps_spec(exclude_none=True)

        # None fields should be excluded
        assert "description" not in spec_json
        assert "phone_number" not in spec_json

        # Required fields should be included
        assert "name" in spec_json
        assert "account_sid" in spec_json
        assert "twilio_authentication_token" in spec_json

    def test_phone_number_various_formats(self):
        """Test that various phone number formats are accepted."""
        formats = [
            "+1234567890",
            "1234567890",
            "+1 (234) 567-8900",
            "+44 20 7946 0958",
        ]

        for phone in formats:
            channel = TwilioSMSChannel(
                channel="twilio_sms",
                name="test_channel",
                account_sid="AC" + "1" * 32,
                twilio_authentication_token="token",
                phone_number=phone
            )
            assert channel.phone_number == phone
