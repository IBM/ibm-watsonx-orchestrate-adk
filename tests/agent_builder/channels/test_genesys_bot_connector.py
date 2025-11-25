import pytest
from pydantic_core import ValidationError
from ibm_watsonx_orchestrate.agent_builder.channels import GenesysBotConnectorChannel
from ibm_watsonx_orchestrate.agent_builder.agents.types import SpecVersion
from ibm_watsonx_orchestrate.agent_builder.channels.types import ChannelKind


@pytest.fixture()
def valid_genesys_channel():
    return {
        "channel": "genesys_bot_connector",
        "name": "test_genesys_channel",
        "description": "Test Genesys Bot Connector channel",
        "client_id": "863973e1-06ea-4f33-93e3-abc4fe1234ab",
        "client_secret": "aaB1CABCDE2R7SO12bcd3rE-4Ab5cD60EfGHI2LSvAk",
        "verification_token": "test",
        "bot_connector_id": "654321ee-6554-4fd9-bd1c-55555a1b1111",
        "api_url": "https://api.mypurecloud.com"
    }


@pytest.fixture()
def minimal_genesys_channel():
    return {
        "channel": "genesys_bot_connector",
        "name": "test_channel",
        "client_id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
        "client_secret": "test_secret_123",
        "verification_token": "token",
        "bot_connector_id": "f6e5d4c3-b2a1-4f5e-8d9c-3b4c5d6e7f8a",
        "api_url": "https://api.example.com"
    }


class TestGenesysBotConnectorChannel:
    """Tests for GenesysBotConnectorChannel validation."""

    def test_valid_channel_creation(self, valid_genesys_channel):
        """Test creating a valid Genesys Bot Connector channel."""
        channel = GenesysBotConnectorChannel(**valid_genesys_channel)

        assert channel.channel == "genesys_bot_connector"
        assert channel.name == "test_genesys_channel"
        assert channel.description == "Test Genesys Bot Connector channel"
        assert channel.client_id == "863973e1-06ea-4f33-93e3-abc4fe1234ab"
        assert channel.client_secret == "aaB1CABCDE2R7SO12bcd3rE-4Ab5cD60EfGHI2LSvAk"
        assert channel.verification_token == "test"
        assert channel.bot_connector_id == "654321ee-6554-4fd9-bd1c-55555a1b1111"
        assert channel.api_url == "https://api.mypurecloud.com"

    def test_minimal_channel_creation(self, minimal_genesys_channel):
        """Test creating a channel with only required fields."""
        channel = GenesysBotConnectorChannel(**minimal_genesys_channel)

        assert channel.channel == "genesys_bot_connector"
        assert channel.name == "test_channel"
        assert channel.description is None
        assert channel.client_id == "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d"

    def test_default_values(self, minimal_genesys_channel):
        """Test that default values are set correctly."""
        channel = GenesysBotConnectorChannel(**minimal_genesys_channel)

        assert channel.spec_version == SpecVersion.V1
        assert channel.kind == ChannelKind.CHANNEL

    def test_missing_client_id(self):
        """Test that missing client_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysBotConnectorChannel(
                channel="genesys_bot_connector",
                name="test_channel",
                client_secret="test_secret_123",
                verification_token="token",
                bot_connector_id="654321ee-6554-4fd9-bd1c-55555a1b1111",
                api_url="https://api.example.com"
            )

        assert "client_id" in str(exc_info.value)

    def test_missing_client_secret(self):
        """Test that missing client_secret raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysBotConnectorChannel(
                channel="genesys_bot_connector",
                name="test_channel",
                client_id="863973e1-06ea-4f33-93e3-abc4fe1234ab",
                verification_token="token",
                bot_connector_id="654321ee-6554-4fd9-bd1c-55555a1b1111",
                api_url="https://api.example.com"
            )

        assert "client_secret" in str(exc_info.value)

    def test_missing_verification_token(self):
        """Test that missing verification_token raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysBotConnectorChannel(
                channel="genesys_bot_connector",
                name="test_channel",
                client_id="863973e1-06ea-4f33-93e3-abc4fe1234ab",
                client_secret="test_secret_123",
                bot_connector_id="654321ee-6554-4fd9-bd1c-55555a1b1111",
                api_url="https://api.example.com"
            )

        assert "verification_token" in str(exc_info.value)

    def test_missing_bot_connector_id(self):
        """Test that missing bot_connector_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysBotConnectorChannel(
                channel="genesys_bot_connector",
                name="test_channel",
                client_id="863973e1-06ea-4f33-93e3-abc4fe1234ab",
                client_secret="test_secret_123",
                verification_token="token",
                api_url="https://api.example.com"
            )

        assert "bot_connector_id" in str(exc_info.value)

    def test_missing_api_url(self):
        """Test that missing api_url raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysBotConnectorChannel(
                channel="genesys_bot_connector",
                name="test_channel",
                client_id="863973e1-06ea-4f33-93e3-abc4fe1234ab",
                client_secret="test_secret_123",
                verification_token="token",
                bot_connector_id="654321ee-6554-4fd9-bd1c-55555a1b1111"
            )

        assert "api_url" in str(exc_info.value)

    def test_invalid_client_id_not_uuid(self):
        """Test that client_id not in UUID format fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysBotConnectorChannel(
                channel="genesys_bot_connector",
                name="test_channel",
                client_id="not-a-valid-uuid",
                client_secret="test_secret_123",
                verification_token="token",
                bot_connector_id="654321ee-6554-4fd9-bd1c-55555a1b1111",
                api_url="https://api.example.com"
            )

        assert "client_id" in str(exc_info.value)

    def test_invalid_bot_connector_id_not_uuid(self):
        """Test that bot_connector_id not in UUID format fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysBotConnectorChannel(
                channel="genesys_bot_connector",
                name="test_channel",
                client_id="863973e1-06ea-4f33-93e3-abc4fe1234ab",
                client_secret="test_secret_123",
                verification_token="token",
                bot_connector_id="invalid-bot-id",
                api_url="https://api.example.com"
            )

        assert "bot_connector_id" in str(exc_info.value)

    def test_invalid_api_url(self):
        """Test that api_url not in URL format fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysBotConnectorChannel(
                channel="genesys_bot_connector",
                name="test_channel",
                client_id="863973e1-06ea-4f33-93e3-abc4fe1234ab",
                client_secret="test_secret_123",
                verification_token="token",
                bot_connector_id="654321ee-6554-4fd9-bd1c-55555a1b1111",
                api_url="not-a-valid-url"
            )

        assert "api_url" in str(exc_info.value)

    def test_invalid_api_url_wrong_protocol(self):
        """Test that api_url with wrong protocol fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysBotConnectorChannel(
                channel="genesys_bot_connector",
                name="test_channel",
                client_id="863973e1-06ea-4f33-93e3-abc4fe1234ab",
                client_secret="test_secret_123",
                verification_token="token",
                bot_connector_id="654321ee-6554-4fd9-bd1c-55555a1b1111",
                api_url="ftp://api.example.com"  # Must be http or https
            )

        assert "api_url" in str(exc_info.value)

    def test_client_secret(self):
        """Test that client_secret accepts minimum length of 1."""
        # Note: min_length is 1 to allow any non-empty secret
        channel = GenesysBotConnectorChannel(
            channel="genesys_bot_connector",
            name="test_channel",
            client_id="863973e1-06ea-4f33-93e3-abc4fe1234ab",
            client_secret="a",  # Minimum 1 character
            verification_token="token",
            bot_connector_id="654321ee-6554-4fd9-bd1c-55555a1b1111",
            api_url="https://api.example.com"
        )

        assert channel.client_secret == "a"

    def test_channel_type_locked(self):
        """Test that channel type is always genesys_bot_connector."""
        channel = GenesysBotConnectorChannel(
            channel="genesys_bot_connector",
            name="test_channel",
            client_id="863973e1-06ea-4f33-93e3-abc4fe1234ab",
            client_secret="test_secret_123",
            verification_token="token",
            bot_connector_id="654321ee-6554-4fd9-bd1c-55555a1b1111",
            api_url="https://api.example.com"
        )

        assert channel.channel == "genesys_bot_connector"

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysBotConnectorChannel(
                channel="genesys_bot_connector",
                name="test_channel",
                client_id="863973e1-06ea-4f33-93e3-abc4fe1234ab",
                client_secret="test_secret_123",
                verification_token="token",
                bot_connector_id="654321ee-6554-4fd9-bd1c-55555a1b1111",
                api_url="https://api.example.com",
                unknown_field="value"
            )

        assert "unknown_field" in str(exc_info.value).lower() or "extra" in str(exc_info.value).lower()

    def test_dumps_spec(self, valid_genesys_channel):
        """Test dumps_spec method excludes response-only fields."""
        channel = GenesysBotConnectorChannel(**valid_genesys_channel)

        # Manually set response-only fields (simulating API response)
        channel.channel_id = "ch-123"
        channel.tenant_id = "tenant-456"
        channel.agent_id = "agent-789"

        spec_json = channel.dumps_spec()

        # Response-only fields should be excluded
        assert "channel_id" not in spec_json
        assert "tenant_id" not in spec_json
        assert "agent_id" not in spec_json
        assert "created_on" not in spec_json
        assert "updated_at" not in spec_json

        # User-editable fields should be included
        assert "genesys_bot_connector" in spec_json
        assert "test_genesys_channel" in spec_json
        assert "863973e1-06ea-4f33-93e3-abc4fe1234ab" in spec_json
        assert "654321ee-6554-4fd9-bd1c-55555a1b1111" in spec_json

    def test_dumps_spec_exclude_none(self, minimal_genesys_channel):
        """Test dumps_spec with exclude_none option."""
        channel = GenesysBotConnectorChannel(**minimal_genesys_channel)

        spec_json = channel.dumps_spec(exclude_none=True)

        # None fields should be excluded
        assert "description" not in spec_json

        # Required fields should be included
        assert "name" in spec_json
        assert "client_id" in spec_json
        assert "client_secret" in spec_json
        assert "verification_token" in spec_json
        assert "bot_connector_id" in spec_json
        assert "api_url" in spec_json

    def test_whitespace_stripped_from_fields(self):
        """Test that whitespace is stripped from string fields."""
        channel = GenesysBotConnectorChannel(
            channel="genesys_bot_connector",
            name="  test_channel  ",
            client_id="863973e1-06ea-4f33-93e3-abc4fe1234ab",
            client_secret="  test_secret_123  ",
            verification_token="  token  ",
            bot_connector_id="654321ee-6554-4fd9-bd1c-55555a1b1111",
            api_url="https://api.example.com"
        )

        assert channel.name == "test_channel"
        assert channel.client_secret == "test_secret_123"
        assert channel.verification_token == "token"

    def test_realistic_genesys_credentials(self):
        """Test with realistic Genesys credentials."""
        channel = GenesysBotConnectorChannel(
            channel="genesys_bot_connector",
            name="Production Bot Connector",
            description="Main customer support bot",
            client_id="987654e1-06ea-4f33-93e3-abc4fe1234ab",
            client_secret="aaB1CABCDE2R7SO12bcd3rE-4Ab5cD60EfGHI2LSvAk",
            verification_token="test",
            bot_connector_id="654321ee-6554-4fd9-bd1c-55555a1b1111",
            api_url="https://api.mypurecloud.com"
        )

        assert channel.client_id == "987654e1-06ea-4f33-93e3-abc4fe1234ab"
        assert channel.bot_connector_id == "654321ee-6554-4fd9-bd1c-55555a1b1111"
        assert channel.api_url == "https://api.mypurecloud.com"

    def test_model_dump_excludes_serialization_fields(self, valid_genesys_channel):
        """Test that model_dump with exclude parameter works correctly."""
        channel = GenesysBotConnectorChannel(**valid_genesys_channel)
        channel.channel_id = "ch-123"
        channel.tenant_id = "tenant-456"

        # Dump excluding the response-only fields
        data = channel.model_dump(exclude=channel.SERIALIZATION_EXCLUDE)

        assert "channel_id" not in data
        assert "tenant_id" not in data
        assert "agent_id" not in data
        assert "client_id" in data
        assert "bot_connector_id" in data

    def test_various_valid_url_formats(self):
        """Test that various valid URL formats are accepted."""
        valid_urls = [
            "https://api.mypurecloud.com",
            "https://api.mypurecloud.com/",
            "https://api.mypurecloud.com/v2",
            "http://localhost:4321",
            "http://localhost:4321/api/v1",
            "https://127.0.0.1:8080",
        ]

        for url in valid_urls:
            channel = GenesysBotConnectorChannel(
                channel="genesys_bot_connector",
                name="test_channel",
                client_id="863973e1-06ea-4f33-93e3-abc4fe1234ab",
                client_secret="test_secret_123",
                verification_token="token",
                bot_connector_id="654321ee-6554-4fd9-bd1c-55555a1b1111",
                api_url=url
            )
            assert channel.api_url == url

    def test_uppercase_uuid_accepted(self):
        """Test that UUIDs with uppercase letters are accepted."""
        channel = GenesysBotConnectorChannel(
            channel="genesys_bot_connector",
            name="test_channel",
            client_id="863973E1-06EA-4F33-93E3-abc4fe1234ab",  # Uppercase
            client_secret="test_secret_123",
            verification_token="token",
            bot_connector_id="654321EE-6554-4FD9-BD1C-55555a1b1111",  # Uppercase
            api_url="https://api.example.com"
        )

        assert channel.client_id == "863973E1-06EA-4F33-93E3-abc4fe1234ab"
        assert channel.bot_connector_id == "654321EE-6554-4FD9-BD1C-55555a1b1111"

    def test_api_url_exceeds_max_length(self):
        """Test that api_url exceeding max length fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysBotConnectorChannel(
                channel="genesys_bot_connector",
                name="test_channel",
                client_id="863973e1-06ea-4f33-93e3-abc4fe1234ab",
                client_secret="test_secret_123",
                verification_token="token",
                bot_connector_id="654321gg-6554-4fd9-bd1c-55555a1b1111",
                api_url="https://api.example.com/" + "a" * 50
            )

        assert "api_url" in str(exc_info.value)

    def test_empty_verification_token_fails(self):
        """Test that empty verification_token fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysBotConnectorChannel(
                channel="genesys_bot_connector",
                name="test_channel",
                client_id="863973e1-06ea-4f33-93e3-abc4fe1234ab",
                client_secret="test_secret_123",
                verification_token="",  # Empty string
                bot_connector_id="654321gg-6554-4fd9-bd1c-55555a1b1111",
                api_url="https://api.example.com"
            )

        assert "verification_token" in str(exc_info.value)

    def test_empty_client_secret_fails(self):
        """Test that empty client_secret fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysBotConnectorChannel(
                channel="genesys_bot_connector",
                name="test_channel",
                client_id="863973e1-06ea-4f33-93e3-abc4fe1234ab",
                client_secret="",  # Empty string
                verification_token="token",
                bot_connector_id="654321gg-6554-4fd9-bd1c-55555a1b1111",
                api_url="https://api.example.com"
            )

        assert "client_secret" in str(exc_info.value)
