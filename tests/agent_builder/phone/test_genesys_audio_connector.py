import pytest
import json
from pydantic_core import ValidationError
from ibm_watsonx_orchestrate.agent_builder.phone import GenesysAudioConnectorChannel
from ibm_watsonx_orchestrate.agent_builder.agents.types import SpecVersion
from ibm_watsonx_orchestrate.agent_builder.phone.types import PhoneChannelKind


@pytest.fixture()
def valid_genesys_channel():
    """Valid Genesys Audio Connector channel configuration."""
    return {
        "name": "test_genesys_channel",
        "description": "Test Genesys Audio Connector channel",
        "service_provider": "genesys_audio_connector",
        "security": {
            "api_key": "test_api_key_123",
            "client_secret": "test_client_secret_456"
        }
    }


@pytest.fixture()
def minimal_genesys_channel():
    """Minimal Genesys Audio Connector channel with only required fields."""
    return {
        "name": "test_channel",
        "service_provider": "genesys_audio_connector",
        "security": {
            "api_key": "api_key",
            "client_secret": "client_secret"
        }
    }


class TestGenesysAudioConnectorChannel:
    """Tests for GenesysAudioConnectorChannel validation."""

    def test_valid_channel_creation(self, valid_genesys_channel):
        """Test creating a valid Genesys Audio Connector channel."""
        channel = GenesysAudioConnectorChannel(**valid_genesys_channel)

        assert channel.name == "test_genesys_channel"
        assert channel.description == "Test Genesys Audio Connector channel"
        assert channel.service_provider == "genesys_audio_connector"
        assert channel.security["api_key"] == "test_api_key_123"
        assert channel.security["client_secret"] == "test_client_secret_456"

    def test_minimal_channel_creation(self, minimal_genesys_channel):
        """Test creating a channel with only required fields."""
        channel = GenesysAudioConnectorChannel(**minimal_genesys_channel)

        assert channel.name == "test_channel"
        assert channel.description is None
        assert channel.service_provider == "genesys_audio_connector"
        assert channel.security["api_key"] == "api_key"
        assert channel.security["client_secret"] == "client_secret"

    def test_default_values(self, minimal_genesys_channel):
        """Test that default values are set correctly."""
        channel = GenesysAudioConnectorChannel(**minimal_genesys_channel)

        assert channel.spec_version == SpecVersion.V1
        assert channel.kind == PhoneChannelKind.PHONE
        assert channel.service_provider == "genesys_audio_connector"

    def test_missing_name(self):
        """Test that missing name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysAudioConnectorChannel(
                service_provider="genesys_audio_connector",
                security={"api_key": "key", "client_secret": "secret"}
            )

        assert "name" in str(exc_info.value)

    def test_missing_security(self):
        """Test that missing security raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysAudioConnectorChannel(
                name="test_channel",
                service_provider="genesys_audio_connector"
            )

        assert "security is required" in str(exc_info.value)

    def test_missing_api_key(self):
        """Test that missing api_key in security raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysAudioConnectorChannel(
                name="test_channel",
                service_provider="genesys_audio_connector",
                security={"client_secret": "secret"}
            )

        assert "api_key" in str(exc_info.value)

    def test_missing_client_secret(self):
        """Test that missing client_secret in security raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysAudioConnectorChannel(
                name="test_channel",
                service_provider="genesys_audio_connector",
                security={"api_key": "key"}
            )

        assert "client_secret" in str(exc_info.value)

    def test_empty_api_key(self):
        """Test that empty api_key raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysAudioConnectorChannel(
                name="test_channel",
                service_provider="genesys_audio_connector",
                security={"api_key": "", "client_secret": "secret"}
            )

        assert "api_key" in str(exc_info.value)

    def test_empty_client_secret(self):
        """Test that empty client_secret raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysAudioConnectorChannel(
                name="test_channel",
                service_provider="genesys_audio_connector",
                security={"api_key": "key", "client_secret": ""}
            )

        assert "client_secret" in str(exc_info.value)

    def test_security_not_dict(self):
        """Test that security must be a dictionary."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysAudioConnectorChannel(
                name="test_channel",
                service_provider="genesys_audio_connector",
                security="not_a_dict"
            )

        assert "Input should be a valid dictionary" in str(exc_info.value)

    def test_name_max_length(self):
        """Test that name exceeding max length fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysAudioConnectorChannel(
                name="a" * 65,  # Max is 64
                service_provider="genesys_audio_connector",
                security={"api_key": "key", "client_secret": "secret"}
            )

        assert "name" in str(exc_info.value)

    def test_description_max_length(self):
        """Test that description exceeding max length fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysAudioConnectorChannel(
                name="test_channel",
                description="a" * 1025,  # Max is 1024
                service_provider="genesys_audio_connector",
                security={"api_key": "key", "client_secret": "secret"}
            )

        assert "description" in str(exc_info.value)

    def test_service_provider_locked(self):
        """Test that service_provider is always genesys_audio_connector."""
        channel = GenesysAudioConnectorChannel(
            name="test_channel",
            service_provider="genesys_audio_connector",
            security={"api_key": "key", "client_secret": "secret"}
        )

        assert channel.service_provider == "genesys_audio_connector"

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysAudioConnectorChannel(
                name="test_channel",
                service_provider="genesys_audio_connector",
                security={"api_key": "key", "client_secret": "secret"},
                unknown_field="value"
            )

        assert "unknown_field" in str(exc_info.value).lower() or "extra" in str(exc_info.value).lower()

    def test_dumps_spec(self, valid_genesys_channel):
        """Test dumps_spec method excludes response-only fields."""
        channel = GenesysAudioConnectorChannel(**valid_genesys_channel)

        # Manually set response-only fields (simulating API response)
        channel.id = "phone-123"
        channel.tenant_id = "tenant-456"
        channel.attached_environments = [{"agent_id": "agent-1", "environment_id": "env-1"}]
        channel.phone_numbers = [{"number": "+15551234567"}]

        spec_json = channel.dumps_spec()

        # Response-only fields should be excluded
        assert '"id"' not in spec_json
        assert '"tenant_id"' not in spec_json
        assert '"attached_environments"' not in spec_json
        assert '"phone_numbers"' not in spec_json
        assert '"created_on"' not in spec_json
        assert '"updated_at"' not in spec_json

        # User-editable fields should be included
        assert "test_genesys_channel" in spec_json
        assert "genesys_audio_connector" in spec_json
        assert "test_api_key_123" in spec_json

    def test_dumps_spec_exclude_none(self, minimal_genesys_channel):
        """Test dumps_spec with exclude_none option."""
        channel = GenesysAudioConnectorChannel(**minimal_genesys_channel)

        spec_json = channel.dumps_spec(exclude_none=True)

        # None fields should be excluded
        assert "description" not in spec_json

        # Required fields should be included
        assert "name" in spec_json
        assert "service_provider" in spec_json
        assert "security" in spec_json

    def test_get_api_path(self, minimal_genesys_channel):
        """Test get_api_path method returns correct path."""
        channel = GenesysAudioConnectorChannel(**minimal_genesys_channel)

        api_path = channel.get_api_path()

        assert api_path == "phone"

    def test_response_only_fields_optional(self, minimal_genesys_channel):
        """Test that response-only fields are optional and can be set."""
        channel = GenesysAudioConnectorChannel(**minimal_genesys_channel)

        # These should be None by default
        assert channel.id is None
        assert channel.tenant_id is None
        assert channel.attached_environments is None
        assert channel.phone_numbers is None
        assert channel.created_on is None
        assert channel.created_by is None
        assert channel.updated_at is None
        assert channel.updated_by is None

        # Should be able to set them (simulating API response)
        channel.id = "phone-123"
        channel.tenant_id = "tenant-456"
        channel.attached_environments = [{"agent_id": "agent-1", "environment_id": "env-1"}]
        channel.phone_numbers = [{"number": "+15551234567", "description": "Main line"}]

        assert channel.id == "phone-123"
        assert channel.tenant_id == "tenant-456"
        assert len(channel.attached_environments) == 1
        assert len(channel.phone_numbers) == 1

    def test_whitespace_stripping(self):
        """Test that whitespace is stripped from string fields."""
        channel = GenesysAudioConnectorChannel(
            name="  test_channel  ",
            description="  Test description  ",
            service_provider="genesys_audio_connector",
            security={"api_key": "key", "client_secret": "secret"}
        )

        assert channel.name == "test_channel"
        assert channel.description == "Test description"

    def test_model_dump_excludes_response_fields(self, valid_genesys_channel):
        """Test that model_dump with exclude parameter works correctly."""
        channel = GenesysAudioConnectorChannel(**valid_genesys_channel)
        channel.id = "phone-123"
        channel.tenant_id = "tenant-456"

        # Dump with exclusions
        data = channel.model_dump(
            exclude_none=True,
            exclude=channel.SERIALIZATION_EXCLUDE
        )

        # Response-only fields should be excluded
        assert "id" not in data
        assert "tenant_id" not in data

        # User-editable fields should be included
        assert "name" in data
        assert "security" in data

    def test_serialization_exclude_constant(self):
        """Test that SERIALIZATION_EXCLUDE contains expected fields."""
        expected_fields = {
            "id", "tenant_id", "attached_environments", "phone_numbers",
            "created_on", "created_by", "updated_at", "updated_by"
        }

        assert GenesysAudioConnectorChannel.SERIALIZATION_EXCLUDE == expected_fields

    def test_channel_with_all_optional_fields(self):
        """Test creating channel with all optional fields set."""
        channel = GenesysAudioConnectorChannel(
            name="test_channel",
            description="Full description",
            service_provider="genesys_audio_connector",
            security={"api_key": "key", "client_secret": "secret"},
            # Response-only fields
            id="phone-123",
            tenant_id="tenant-456",
            attached_environments=[{"agent_id": "agent-1", "environment_id": "env-1"}],
            phone_numbers=[{"number": "+15551234567"}],
            created_on="2024-01-01T00:00:00Z",
            created_by="user-123",
            updated_at="2024-01-02T00:00:00Z",
            updated_by="user-456"
        )

        assert channel.name == "test_channel"
        assert channel.description == "Full description"
        assert channel.id == "phone-123"
        assert channel.tenant_id == "tenant-456"
        assert len(channel.attached_environments) == 1
        assert len(channel.phone_numbers) == 1
        assert channel.created_on == "2024-01-01T00:00:00Z"
        assert channel.created_by == "user-123"
        assert channel.updated_at == "2024-01-02T00:00:00Z"
        assert channel.updated_by == "user-456"

    def test_invalid_service_provider(self):
        """Test that invalid service_provider raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenesysAudioConnectorChannel(
                name="test_channel",
                service_provider="wrong_provider",
                security={"api_key": "key", "client_secret": "secret"}
            )

        assert "service_provider" in str(exc_info.value).lower()

    def test_roundtrip_serialization(self, valid_genesys_channel):
        """Test that dumps_spec can be loaded back to recreate the channel."""
        # Create original channel
        channel1 = GenesysAudioConnectorChannel(**valid_genesys_channel)

        # Serialize to JSON
        spec_json = channel1.dumps_spec()

        # Deserialize back to dict and create new channel
        data = json.loads(spec_json)
        channel2 = GenesysAudioConnectorChannel(**data)

        # Verify fields match
        assert channel1.name == channel2.name
        assert channel1.description == channel2.description
        assert channel1.service_provider == channel2.service_provider
        assert channel1.security == channel2.security
        assert channel1.spec_version == channel2.spec_version
        assert channel1.kind == channel2.kind
