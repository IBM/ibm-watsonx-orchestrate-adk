import pytest
from pydantic_core import ValidationError
from ibm_watsonx_orchestrate.agent_builder.channels import SlackChannel
from ibm_watsonx_orchestrate.agent_builder.agents.types import SpecVersion
from ibm_watsonx_orchestrate.agent_builder.channels.types import ChannelKind


@pytest.fixture()
def valid_slack_channel():
    return {
        "channel": "byo_slack",
        "name": "test_slack_channel",
        "description": "Test Slack channel",
        "client_id": "123456789012.123456789012",
        "client_secret": "abcdef1234567890abcdef1234567890",
        "signing_secret": "abcdef1234567890abcdef1234567890",
        "teams": [
            {
                "id": "T09E6APUJBG",
                "bot_access_token": "xoxb-test-token"
            }
        ]
    }


@pytest.fixture()
def minimal_slack_channel():
    return {
        "channel": "byo_slack",
        "name": "test_channel",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "signing_secret": "test_signing_secret",
        "teams": [
            {
                "id": "T12345678",
                "bot_access_token": "xoxb-minimal-token"
            }
        ]
    }


class TestSlackChannel:
    """Tests for SlackChannel validation."""

    def test_valid_channel_creation(self, valid_slack_channel):
        """Test creating a valid Slack channel."""
        channel = SlackChannel(**valid_slack_channel)

        assert channel.channel == "byo_slack"
        assert channel.name == "test_slack_channel"
        assert channel.description == "Test Slack channel"
        assert channel.client_id == "123456789012.123456789012"
        assert channel.client_secret == "abcdef1234567890abcdef1234567890"
        assert channel.signing_secret == "abcdef1234567890abcdef1234567890"

    def test_minimal_channel_creation(self, minimal_slack_channel):
        """Test creating a channel with only required fields."""
        channel = SlackChannel(**minimal_slack_channel)

        assert channel.channel == "byo_slack"
        assert channel.name == "test_channel"
        assert channel.description is None
        assert channel.client_id == "test_client_id"
        assert channel.client_secret == "test_client_secret"
        assert channel.signing_secret == "test_signing_secret"

    def test_default_values(self, minimal_slack_channel):
        """Test that default values are set correctly."""
        channel = SlackChannel(**minimal_slack_channel)

        assert channel.spec_version == SpecVersion.V1
        assert channel.kind == ChannelKind.CHANNEL

    def test_missing_client_id(self):
        """Test that missing client_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            SlackChannel(
                channel="byo_slack",
                name="test_channel",
                client_secret="test_secret",
                signing_secret="test_signing_secret"
            )

        assert "client_id" in str(exc_info.value)

    def test_missing_client_secret(self):
        """Test that missing client_secret raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            SlackChannel(
                channel="byo_slack",
                name="test_channel",
                client_id="test_client_id",
                signing_secret="test_signing_secret"
            )

        assert "client_secret" in str(exc_info.value)

    def test_missing_signing_secret(self):
        """Test that missing signing_secret raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            SlackChannel(
                channel="byo_slack",
                name="test_channel",
                client_id="test_client_id",
                client_secret="test_secret"
            )

        assert "signing_secret" in str(exc_info.value)

    def test_empty_client_id(self):
        """Test that empty client_id fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            SlackChannel(
                channel="byo_slack",
                name="test_channel",
                client_id="",
                client_secret="test_secret",
                signing_secret="test_signing_secret"
            )

        assert "client_id" in str(exc_info.value)

    def test_empty_client_secret(self):
        """Test that empty client_secret fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            SlackChannel(
                channel="byo_slack",
                name="test_channel",
                client_id="test_client_id",
                client_secret="",
                signing_secret="test_signing_secret"
            )

        assert "client_secret" in str(exc_info.value)

    def test_empty_signing_secret(self):
        """Test that empty signing_secret fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            SlackChannel(
                channel="byo_slack",
                name="test_channel",
                client_id="test_client_id",
                client_secret="test_secret",
                signing_secret=""
            )

        assert "signing_secret" in str(exc_info.value)

    def test_name_max_length(self):
        """Test that name exceeding max length fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            SlackChannel(
                channel="byo_slack",
                name="a" * 65,  # Max is 64
                client_id="test_client_id",
                client_secret="test_secret",
                signing_secret="test_signing_secret"
            )

        assert "name" in str(exc_info.value)

    def test_description_max_length(self):
        """Test that description exceeding max length fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            SlackChannel(
                channel="byo_slack",
                name="test_channel",
                description="a" * 1025,  # Max is 1024
                client_id="test_client_id",
                client_secret="test_secret",
                signing_secret="test_signing_secret"
            )

        assert "description" in str(exc_info.value)

    def test_channel_type_locked(self):
        """Test that channel type is always byo_slack."""
        channel = SlackChannel(
            channel="byo_slack",
            name="test_channel",
            client_id="test_client_id",
            client_secret="test_secret",
            signing_secret="test_signing_secret",
            teams=[{"id": "T12345", "bot_access_token": "xoxb-test"}]
        )

        assert channel.channel == "byo_slack"

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            SlackChannel(
                channel="byo_slack",
                name="test_channel",
                client_id="test_client_id",
                client_secret="test_secret",
                signing_secret="test_signing_secret",
                unknown_field="value"
            )

        assert "unknown_field" in str(exc_info.value).lower() or "extra" in str(exc_info.value).lower()

    def test_dumps_spec(self, valid_slack_channel):
        """Test dumps_spec method excludes response-only fields."""
        channel = SlackChannel(**valid_slack_channel)

        # Manually set response-only fields (simulating API response)
        channel.channel_id = "ch-123"
        channel.tenant_id = "tenant-456"

        spec_json = channel.dumps_spec()

        # Response-only fields should be excluded
        assert "channel_id" not in spec_json
        assert "tenant_id" not in spec_json
        assert "agent_id" not in spec_json

        # User-editable fields should be included
        assert "byo_slack" in spec_json
        assert "test_slack_channel" in spec_json

    def test_dumps_spec_exclude_none(self, minimal_slack_channel):
        """Test dumps_spec with exclude_none option."""
        channel = SlackChannel(**minimal_slack_channel)

        spec_json = channel.dumps_spec(exclude_none=True)

        # None fields should be excluded
        assert "description" not in spec_json

        # Required fields should be included
        assert "name" in spec_json
        assert "client_id" in spec_json
        assert "client_secret" in spec_json
        assert "signing_secret" in spec_json

    def test_whitespace_stripped_from_fields(self):
        """Test that whitespace is stripped from string fields."""
        channel = SlackChannel(
            channel="byo_slack",
            name="  test_channel  ",
            client_id="  test_client_id  ",
            client_secret="  test_secret  ",
            signing_secret="  test_signing_secret  ",
            teams=[{"id": "  T12345  ", "bot_access_token": "  xoxb-test  "}]
        )

        assert channel.name == "test_channel"
        assert channel.client_id == "test_client_id"
        assert channel.client_secret == "test_secret"
        assert channel.signing_secret == "test_signing_secret"
        assert channel.teams[0].id == "T12345"
        assert channel.teams[0].bot_access_token == "xoxb-test"

    def test_realistic_slack_credentials(self):
        """Test with realistic-looking Slack credentials."""
        channel = SlackChannel(
            channel="byo_slack",
            name="production_slack",
            description="Production Slack integration",
            client_id="123456789012.987654321098",
            client_secret="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
            signing_secret="1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
            teams=[{"id": "T09E6APUJBG", "bot_access_token": "xoxb-123456789012-987654321098-abcdefghijklmnopqrstuvwx"}]
        )

        assert channel.client_id == "123456789012.987654321098"
        assert len(channel.client_secret) == 32
        assert len(channel.signing_secret) == 32
        assert channel.teams[0].id == "T09E6APUJBG"
        assert channel.teams[0].bot_access_token.startswith("xoxb-")

    def test_model_dump_excludes_serialization_fields(self, valid_slack_channel):
        """Test that model_dump with SERIALIZATION_EXCLUDE works correctly."""
        channel = SlackChannel(**valid_slack_channel)

        # Set response-only fields
        channel.channel_id = "ch-123"
        channel.tenant_id = "tenant-456"
        channel.agent_id = "agent-789"

        # Dump with exclusions
        data = channel.model_dump(exclude=channel.SERIALIZATION_EXCLUDE)

        # Response-only fields should be excluded
        assert "channel_id" not in data
        assert "tenant_id" not in data
        assert "agent_id" not in data

        # User fields should be present
        assert "channel" in data
        assert "client_id" in data
        assert "client_secret" in data
        assert "signing_secret" in data

    def test_missing_teams(self):
        """Test that missing teams raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            SlackChannel(
                channel="byo_slack",
                name="test_channel",
                client_id="test_client_id",
                client_secret="test_secret",
                signing_secret="test_signing_secret"
            )

        assert "team" in str(exc_info.value).lower()

    def test_empty_teams_list(self):
        """Test that empty teams list raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            SlackChannel(
                channel="byo_slack",
                name="test_channel",
                client_id="test_client_id",
                client_secret="test_secret",
                signing_secret="test_signing_secret",
                teams=[]
            )

        assert "team" in str(exc_info.value).lower()

    def test_teams_validation(self, minimal_slack_channel):
        """Test that teams are properly validated."""
        channel = SlackChannel(**minimal_slack_channel)

        assert len(channel.teams) == 1
        assert channel.teams[0].id == "T12345678"
        assert channel.teams[0].bot_access_token == "xoxb-minimal-token"
