import pytest
import tempfile
import os
from unittest.mock import patch
from pathlib import Path
from ibm_watsonx_orchestrate.agent_builder.channels import ChannelLoader, TwilioWhatsappChannel, SlackChannel, WebchatChannel
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

        webchat_channel = WebchatChannel(
            channel="webchat",
            name="webchat_channel"
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
                ("webchat_channel", webchat_channel),
                ("another_whatsapp", another_whatsapp),
            ]

            channels = ChannelLoader.from_python("test.py")

        import_module_mock.assert_called_with("test")
        assert len(channels) == 3

        # Check that we got different channel types
        channel_names = [ch.name for ch in channels]
        assert "whatsapp_channel" in channel_names
        assert "webchat_channel" in channel_names
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
