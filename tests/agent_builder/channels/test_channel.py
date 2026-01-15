import pytest
import tempfile
import os
from unittest.mock import patch
from pathlib import Path
from pydantic_core import ValidationError
from ibm_watsonx_orchestrate.agent_builder.channels import (
    ChannelLoader,
    TwilioWhatsappChannel,
    SlackChannel,
    WebchatChannel,
    GenesysBotConnectorChannel,
    FacebookChannel,
    TeamsChannel
)
from ibm_watsonx_orchestrate.agent_builder.agents.types import SpecVersion
from ibm_watsonx_orchestrate.agent_builder.channels.types import ChannelKind
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest


@pytest.fixture()
def valid_yaml_content():
    return """
channel: twilio_whatsapp
name: test_channel
account_sid: AC12345678901234567890123456789012
twilio_authentication_token: test_token
"""


@pytest.fixture()
def valid_json_content():
    return """{
    "channel": "twilio_whatsapp",
    "name": "test_channel",
    "account_sid": "AC12345678901234567890123456789012",
    "twilio_authentication_token": "test_token"
}"""


@pytest.fixture()
def minimal_yaml_content():
    return """
channel: twilio_whatsapp
name: minimal_channel
account_sid: AC12345678901234567890123456789012
twilio_authentication_token: test_token
"""


@pytest.fixture()
def slack_yaml_content():
    return """
channel: byo_slack
name: test_slack_channel
client_id: test_client_id
client_secret: test_client_secret
signing_secret: test_signing_secret
teams:
  - id: T12345
    bot_access_token: xoxb-test-token
"""


@pytest.fixture()
def slack_json_content():
    return """{
    "channel": "byo_slack",
    "name": "test_slack_channel",
    "client_id": "test_client_id",
    "client_secret": "test_client_secret",
    "signing_secret": "test_signing_secret",
    "teams": [
        {
            "id": "T12345",
            "bot_access_token": "xoxb-test-token"
        }
    ]
}"""


class TestChannelFromSpec:
    """Tests for ChannelLoader.from_spec() method."""

    def test_from_yaml_file(self, valid_yaml_content):
        """Test loading channel from YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(valid_yaml_content)
            temp_path = f.name

        try:
            channel = ChannelLoader.from_spec(temp_path)

            assert isinstance(channel, TwilioWhatsappChannel)
            assert channel.channel == "twilio_whatsapp"
            assert channel.name == "test_channel"
            assert channel.account_sid == "AC12345678901234567890123456789012"
            assert channel.twilio_authentication_token == "test_token"
        finally:
            os.unlink(temp_path)

    def test_from_yml_file(self, valid_yaml_content):
        """Test loading channel from .yml file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(valid_yaml_content)
            temp_path = f.name

        try:
            channel = ChannelLoader.from_spec(temp_path)

            assert isinstance(channel, TwilioWhatsappChannel)
            assert channel.channel == "twilio_whatsapp"
        finally:
            os.unlink(temp_path)

    def test_from_json_file(self, valid_json_content):
        """Test loading channel from JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(valid_json_content)
            temp_path = f.name

        try:
            channel = ChannelLoader.from_spec(temp_path)

            assert isinstance(channel, TwilioWhatsappChannel)
            assert channel.channel == "twilio_whatsapp"
            assert channel.name == "test_channel"
        finally:
            os.unlink(temp_path)

    def test_from_spec_with_python_file_raises_error(self):
        """Test that from_spec raises error for Python files."""
        python_content = """
from ibm_watsonx_orchestrate.agent_builder.channels import TwilioWhatsappChannel

channel = TwilioWhatsappChannel(
    channel="twilio_whatsapp",
    name="python_channel",
    account_sid="AC12345678901234567890123456789012",
    twilio_authentication_token="python_token"
)
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_content)
            temp_path = f.name

        try:
            with pytest.raises(BadRequest) as exc_info:
                ChannelLoader.from_spec(temp_path)

            error_msg = str(exc_info.value).lower()
            assert "from_python" in error_msg
        finally:
            os.unlink(temp_path)

    def test_missing_channel_field(self):
        """Test that missing 'channel' field raises error."""
        yaml_content = """
name: test_channel
account_sid: AC12345678901234567890123456789012
twilio_authentication_token: test_token
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            with pytest.raises(BadRequest) as exc_info:
                ChannelLoader.from_spec(temp_path)

            assert "channel" in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)

    def test_unsupported_channel_type(self):
        """Test that unsupported channel type raises error."""
        yaml_content = """
channel: unsupported_channel
name: test_channel
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            with pytest.raises(BadRequest) as exc_info:
                ChannelLoader.from_spec(temp_path)

            assert "unsupported" in str(exc_info.value).lower() or "supported" in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)

    def test_unsupported_file_extension(self):
        """Test that unsupported file extension raises error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("some content")
            temp_path = f.name

        try:
            with pytest.raises(BadRequest) as exc_info:
                ChannelLoader.from_spec(temp_path)

            error_msg = str(exc_info.value).lower()
            assert "json" in error_msg or "yaml" in error_msg or "yml" in error_msg
        finally:
            os.unlink(temp_path)

    def test_invalid_yaml_syntax(self):
        """Test that invalid YAML syntax raises error."""
        invalid_yaml = """
channel: twilio_whatsapp
name: test
  invalid: indentation
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name

        try:
            with pytest.raises(Exception):  # Could be BadRequest or YAMLError
                ChannelLoader.from_spec(temp_path)
        finally:
            os.unlink(temp_path)

    def test_invalid_json_syntax(self):
        """Test that invalid JSON syntax raises error."""
        invalid_json = """
{
    "channel": "twilio_whatsapp",
    "name": "test",
    invalid json
}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(invalid_json)
            temp_path = f.name

        try:
            with pytest.raises(Exception):  # Could be BadRequest or JSONDecodeError
                ChannelLoader.from_spec(temp_path)
        finally:
            os.unlink(temp_path)

    def test_validation_error_propagates(self):
        """Test that Pydantic validation errors are raised."""
        # Missing required field
        yaml_content = """
channel: twilio_whatsapp
account_sid: AC12345678901234567890123456789012
# Missing twilio_authentication_token
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            with pytest.raises(Exception):  # Validation error
                ChannelLoader.from_spec(temp_path)
        finally:
            os.unlink(temp_path)


    def test_minimal_valid_channel(self, minimal_yaml_content):
        """Test loading channel with only required fields."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(minimal_yaml_content)
            temp_path = f.name

        try:
            channel = ChannelLoader.from_spec(temp_path)

            assert isinstance(channel, TwilioWhatsappChannel)
            assert channel.name == "minimal_channel"
            assert channel.account_sid == "AC12345678901234567890123456789012"
        finally:
            os.unlink(temp_path)

    def test_slack_from_yaml_file(self, slack_yaml_content):
        """Test loading Slack channel from YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(slack_yaml_content)
            temp_path = f.name

        try:
            channel = ChannelLoader.from_spec(temp_path)

            assert isinstance(channel, SlackChannel)
            assert channel.channel == "byo_slack"
            assert channel.name == "test_slack_channel"
            assert channel.client_id == "test_client_id"
            assert channel.client_secret == "test_client_secret"
            assert channel.signing_secret == "test_signing_secret"
        finally:
            os.unlink(temp_path)

    def test_slack_from_json_file(self, slack_json_content):
        """Test loading Slack channel from JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(slack_json_content)
            temp_path = f.name

        try:
            channel = ChannelLoader.from_spec(temp_path)

            assert isinstance(channel, SlackChannel)
            assert channel.channel == "byo_slack"
            assert channel.name == "test_slack_channel"
            assert channel.client_id == "test_client_id"
        finally:
            os.unlink(temp_path)


class TestChannelFromPython:
    """Tests for ChannelLoader.from_python() method."""

    def test_from_python_single_channel(self):
        """Test loading single channel from Python file."""
        channel1 = TwilioWhatsappChannel(
            channel="twilio_whatsapp",
            name="python_channel",
            account_sid="AC12345678901234567890123456789012",
            twilio_authentication_token="python_token"
        )

        with patch("ibm_watsonx_orchestrate.agent_builder.channels.channel.inspect.getmembers") as getmembers_mock, \
             patch("ibm_watsonx_orchestrate.agent_builder.channels.channel.importlib.import_module") as import_module_mock:

            getmembers_mock.return_value = [
                ("channel1", channel1) 
            ]
            channels = ChannelLoader.from_python("test.py")

        import_module_mock.assert_called_with("test")
        assert len(channels) == 1
        assert isinstance(channels[0], TwilioWhatsappChannel)
        assert channels[0].name == "python_channel"
        assert channels[0].account_sid == "AC12345678901234567890123456789012"

    def test_from_python_multiple_channels(self):
        """Test loading multiple channels from Python file."""

        whatsapp_channel = TwilioWhatsappChannel(
            channel="twilio_whatsapp",
            name="whatsapp_channel",
            account_sid="AC12345678901234567890123456789012",
            twilio_authentication_token="token1"
        )

        slack_channel = SlackChannel(
            channel="byo_slack",
            name="slack_channel",
            client_id="test_client_id",
            client_secret="test_client_secret",
            signing_secret="test_signing_secret",
            teams=[{"id": "T12345", "bot_access_token": "xoxb-test"}]
        )

        another_whatsapp = TwilioWhatsappChannel(
            channel="twilio_whatsapp",
            name="another_channel",
            account_sid="AC98765432109876543210987654321098",
            twilio_authentication_token="token2"
        )

        with patch("ibm_watsonx_orchestrate.agent_builder.channels.channel.inspect.getmembers") as getmembers_mock, \
            patch("ibm_watsonx_orchestrate.agent_builder.channels.channel.importlib.import_module") as import_module_mock:

            getmembers_mock.return_value = [
                ("whatsapp_channel", whatsapp_channel),
                ("slack_channel", slack_channel),
                ("another_whatsapp", another_whatsapp),
            ]

            channels = ChannelLoader.from_python("test.py")

        import_module_mock.assert_called_with("test")
        assert len(channels) == 3

        # Check that we got different channel types
        channel_names = [ch.name for ch in channels]
        assert "whatsapp_channel" in channel_names
        assert "slack_channel" in channel_names
        assert "another_channel" in channel_names

    def test_from_python_no_channels(self):
        """Test loading from Python file with no channel instances."""
        with patch("ibm_watsonx_orchestrate.agent_builder.channels.channel.inspect.getmembers") as getmembers_mock, \
             patch("ibm_watsonx_orchestrate.agent_builder.channels.channel.importlib.import_module") as import_module_mock:

            getmembers_mock.return_value = [
                ("some_var", "not a channel")  # Should be filtered out
            ]

            channels = ChannelLoader.from_python("test.py")

        import_module_mock.assert_called_with("test")
        getmembers_mock.assert_called_once()
        assert len(channels) == 0

    def test_from_python_mocked(self):
        """Test from_python with mocked inspect.getmembers and importlib."""
        channel1 = TwilioWhatsappChannel(
            channel="twilio_whatsapp",
            name="channel1",
            account_sid="AC12345678901234567890123456789012",
            twilio_authentication_token="token"
        )

        channel2 = SlackChannel(
            channel="byo_slack",
            name="channel2",
            client_id="test_client_id",
            client_secret="test_client_secret",
            signing_secret="test_signing_secret",
            teams=[{"id": "T12345", "bot_access_token": "xoxb-test"}]
        )

        with patch("ibm_watsonx_orchestrate.agent_builder.channels.channel.inspect.getmembers") as getmembers_mock, \
             patch("ibm_watsonx_orchestrate.agent_builder.channels.channel.importlib.import_module") as import_module_mock:

            getmembers_mock.return_value = [
                ("channel1", channel1),
                ("channel2", channel2),
                ("some_var", "not a channel")  # Should be filtered out
            ]
            channels = ChannelLoader.from_python("test.py")

            import_module_mock.assert_called_with("test")
            getmembers_mock.assert_called_once()
            assert len(channels) == 2
            assert channels[0].name == "channel1"
            assert channels[1].name == "channel2"

    def test_slack_from_python_file(self):
        """Test loading Slack channel from Python file."""
        slack_channel = SlackChannel(
            channel="byo_slack",
            name="test_slack",
            client_id="test_client_id",
            client_secret="test_client_secret",
            signing_secret="test_signing_secret",
            teams=[{"id": "T12345", "bot_access_token": "xoxb-test"}]
        )

        with patch("ibm_watsonx_orchestrate.agent_builder.channels.channel.inspect.getmembers") as getmembers_mock, \
            patch("ibm_watsonx_orchestrate.agent_builder.channels.channel.importlib.import_module") as import_module_mock:

            getmembers_mock.return_value = [
                ("slack_channel", slack_channel)
            ]

            channels = ChannelLoader.from_python("test.py")

        import_module_mock.assert_called_with("test")
        assert len(channels) == 1
        assert isinstance(channels[0], SlackChannel)
        assert channels[0].name == "test_slack"
        assert channels[0].client_id == "test_client_id"
        assert channels[0].client_secret == "test_client_secret"
        assert channels[0].signing_secret == "test_signing_secret"


class TestGenesysBotConnectorChannel:
    """Tests for GenesysBotConnectorChannel validation."""

    @pytest.fixture()
    def valid_genesys_channel(self):
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
    def minimal_genesys_channel(self):
        return {
            "channel": "genesys_bot_connector",
            "name": "test_channel",
            "client_id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
            "client_secret": "test_secret_123",
            "verification_token": "token",
            "bot_connector_id": "f6e5d4c3-b2a1-4f5e-8d9c-3b4c5d6e7f8a",
            "api_url": "https://api.example.com"
        }

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

        # User-editable fields should be included
        assert "genesys_bot_connector" in spec_json
        assert "test_genesys_channel" in spec_json
        assert "863973e1-06ea-4f33-93e3-abc4fe1234ab" in spec_json


class TestFacebookChannel:
    """Tests for FacebookChannel validation."""

    @pytest.fixture()
    def valid_facebook_channel(self):
        return {
            "channel": "facebook",
            "name": "test_facebook_channel",
            "description": "Test Facebook Messenger channel",
            "application_secret": "abc123def456ghi789jkl012mno345pqr",
            "verification_token": "my_verification_token_123",
            "page_access_token": "EAABsbCS1iHgBO7ZCnqiZCJ9kqZABCDEF123456"
        }

    @pytest.fixture()
    def minimal_facebook_channel(self):
        return {
            "channel": "facebook",
            "name": "test_channel",
            "application_secret": "secret123",
            "verification_token": "verify123",
            "page_access_token": "token123"
        }

    def test_valid_channel_creation(self, valid_facebook_channel):
        """Test creating a valid Facebook channel."""
        channel = FacebookChannel(**valid_facebook_channel)

        assert channel.channel == "facebook"
        assert channel.name == "test_facebook_channel"
        assert channel.description == "Test Facebook Messenger channel"
        assert channel.application_secret == "abc123def456ghi789jkl012mno345pqr"
        assert channel.verification_token == "my_verification_token_123"
        assert channel.page_access_token == "EAABsbCS1iHgBO7ZCnqiZCJ9kqZABCDEF123456"

    def test_default_values(self, minimal_facebook_channel):
        """Test that default values are set correctly."""
        channel = FacebookChannel(**minimal_facebook_channel)

        assert channel.spec_version == SpecVersion.V1
        assert channel.kind == ChannelKind.CHANNEL

    def test_missing_application_secret(self):
        """Test that missing application_secret raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            FacebookChannel(
                channel="facebook",
                name="test_channel",
                verification_token="verify123",
                page_access_token="token123"
            )

        assert "application_secret" in str(exc_info.value)

    def test_missing_verification_token(self):
        """Test that missing verification_token raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            FacebookChannel(
                channel="facebook",
                name="test_channel",
                application_secret="secret123",
                page_access_token="token123"
            )

        assert "verification_token" in str(exc_info.value)

    def test_missing_page_access_token(self):
        """Test that missing page_access_token raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            FacebookChannel(
                channel="facebook",
                name="test_channel",
                application_secret="secret123",
                verification_token="verify123"
            )

        assert "page_access_token" in str(exc_info.value)

    def test_empty_application_secret_fails(self):
        """Test that empty application_secret fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            FacebookChannel(
                channel="facebook",
                name="test_channel",
                application_secret="",
                verification_token="verify123",
                page_access_token="token123"
            )

        assert "application_secret" in str(exc_info.value)

    def test_empty_verification_token_fails(self):
        """Test that empty verification_token fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            FacebookChannel(
                channel="facebook",
                name="test_channel",
                application_secret="secret123",
                verification_token="",
                page_access_token="token123"
            )

        assert "verification_token" in str(exc_info.value)

    def test_empty_page_access_token_fails(self):
        """Test that empty page_access_token fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            FacebookChannel(
                channel="facebook",
                name="test_channel",
                application_secret="secret123",
                verification_token="verify123",
                page_access_token=""
            )

        assert "page_access_token" in str(exc_info.value)

    def test_channel_type_locked(self):
        """Test that channel type is always facebook."""
        channel = FacebookChannel(
            channel="facebook",
            name="test_channel",
            application_secret="secret123",
            verification_token="verify123",
            page_access_token="token123"
        )

        assert channel.channel == "facebook"

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            FacebookChannel(
                channel="facebook",
                name="test_channel",
                application_secret="secret123",
                verification_token="verify123",
                page_access_token="token123",
                unknown_field="value"
            )

        assert "unknown_field" in str(exc_info.value).lower() or "extra" in str(exc_info.value).lower()

    def test_dumps_spec(self, valid_facebook_channel):
        """Test dumps_spec method excludes response-only fields."""
        channel = FacebookChannel(**valid_facebook_channel)

        # Manually set response-only fields (simulating API response)
        channel.channel_id = "ch-123"
        channel.tenant_id = "tenant-456"
        channel.agent_id = "agent-789"

        spec_json = channel.dumps_spec()

        # Response-only fields should be excluded
        assert "channel_id" not in spec_json
        assert "tenant_id" not in spec_json
        assert "agent_id" not in spec_json

        # User-editable fields should be included
        assert "facebook" in spec_json
        assert "test_facebook_channel" in spec_json
        assert "abc123def456ghi789jkl012mno345pqr" in spec_json

    def test_whitespace_stripped_from_fields(self):
        """Test that whitespace is stripped from string fields."""
        channel = FacebookChannel(
            channel="facebook",
            name="  test_channel  ",
            application_secret="  secret123  ",
            verification_token="  verify123  ",
            page_access_token="  token123  "
        )

        assert channel.name == "test_channel"
        assert channel.application_secret == "secret123"
        assert channel.verification_token == "verify123"
        assert channel.page_access_token == "token123"


class TestTeamsChannel:
    """Tests for TeamsChannel validation."""

    @pytest.fixture()
    def valid_teams_channel(self):
        return {
            "channel": "teams",
            "name": "test_teams_channel",
            "description": "Test Microsoft Teams channel",
            "app_password": "abc~123.def456-ghi789_jkl012",
            "app_id": "12345678-1234-1234-1234-123456789012",
            "teams_tenant_id": "87654321-4321-4321-4321-210987654321"
        }

    def test_valid_channel_creation(self, valid_teams_channel):
        """Test creating a valid Teams channel."""
        channel = TeamsChannel(**valid_teams_channel)

        assert channel.channel == "teams"
        assert channel.name == "test_teams_channel"
        assert channel.description == "Test Microsoft Teams channel"
        assert channel.app_password == "abc~123.def456-ghi789_jkl012"
        assert channel.app_id == "12345678-1234-1234-1234-123456789012"
        assert channel.teams_tenant_id == "87654321-4321-4321-4321-210987654321"

    def test_default_values(self):
        """Test that default values are set correctly."""
        channel = TeamsChannel(
            channel="teams",
            name="test_channel",
            app_password="password123",
            app_id="app123"
        )

        assert channel.spec_version == SpecVersion.V1
        assert channel.kind == ChannelKind.CHANNEL

    def test_missing_app_password(self):
        """Test that missing app_password raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TeamsChannel(
                channel="teams",
                name="test_channel",
                app_id="app123"
            )

        assert "app_password" in str(exc_info.value)

    def test_missing_app_id(self):
        """Test that missing app_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TeamsChannel(
                channel="teams",
                name="test_channel",
                app_password="password123"
            )

        assert "app_id" in str(exc_info.value)

    def test_empty_app_password_fails(self):
        """Test that empty app_password fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TeamsChannel(
                channel="teams",
                name="test_channel",
                app_password="",
                app_id="app123"
            )

        assert "app_password" in str(exc_info.value)

    def test_empty_app_id_fails(self):
        """Test that empty app_id fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TeamsChannel(
                channel="teams",
                name="test_channel",
                app_password="password123",
                app_id=""
            )

        assert "app_id" in str(exc_info.value)

    def test_teams_tenant_id_optional(self):
        """Test that teams_tenant_id is optional."""
        channel = TeamsChannel(
            channel="teams",
            name="test_channel",
            app_password="password123",
            app_id="app123"
        )

        assert channel.teams_tenant_id is None

    def test_channel_type_locked(self):
        """Test that channel type is always teams."""
        channel = TeamsChannel(
            channel="teams",
            name="test_channel",
            app_password="password123",
            app_id="app123"
        )

        assert channel.channel == "teams"

    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            TeamsChannel(
                channel="teams",
                name="test_channel",
                app_password="password123",
                app_id="app123",
                unknown_field="value"
            )

        assert "unknown_field" in str(exc_info.value).lower() or "extra" in str(exc_info.value).lower()

    def test_dumps_spec(self, valid_teams_channel):
        """Test dumps_spec method excludes response-only fields."""
        channel = TeamsChannel(**valid_teams_channel)

        # Manually set response-only fields (simulating API response)
        channel.channel_id = "ch-123"
        channel.tenant_id = "tenant-response-456"
        channel.agent_id = "agent-789"

        spec_json = channel.dumps_spec()

        # Response-only fields should be excluded
        assert "channel_id" not in spec_json
        assert "tenant-response-456" not in spec_json  # Response-only tenant_id
        assert "agent_id" not in spec_json

        # User-editable fields should be included
        assert "teams" in spec_json
        assert "test_teams_channel" in spec_json
        assert "abc~123.def456-ghi789_jkl012" in spec_json
        # User-editable teams_tenant_id should be included
        assert "87654321-4321-4321-4321-210987654321" in spec_json

    def test_whitespace_stripped_from_fields(self):
        """Test that whitespace is stripped from string fields."""
        channel = TeamsChannel(
            channel="teams",
            name="  test_channel  ",
            app_password="  password123  ",
            app_id="  app123  ",
            teams_tenant_id="  tenant123  "
        )

        assert channel.name == "test_channel"
        assert channel.app_password == "password123"
        assert channel.app_id == "app123"
        assert channel.teams_tenant_id == "tenant123"
