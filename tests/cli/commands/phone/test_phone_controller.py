import pytest
import json
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path

from ibm_watsonx_orchestrate.cli.commands.phone.phone_controller import PhoneController
from ibm_watsonx_orchestrate.cli.commands.phone.types import PhoneChannelType
from ibm_watsonx_orchestrate.agent_builder.phone import GenesysAudioConnectorChannel
from ibm_watsonx_orchestrate.cli.common import ListFormats
from pydantic import ValidationError


@pytest.fixture
def phone_controller():
    """Create a PhoneController instance."""
    return PhoneController()


@pytest.fixture
def mock_phone_client():
    """Create a mock phone client."""
    client = Mock()
    client.base_url = "https://api.example.com/v1/orchestrate"
    client.get_subscription_id = Mock(return_value="sub-123")
    return client


@pytest.fixture
def mock_agent_client():
    """Create a mock agent client."""
    return Mock()


@pytest.fixture
def sample_genesys_config():
    """Sample Genesys Audio Connector config data."""
    return {
        "name": "test_phone_config",
        "description": "Test phone configuration",
        "service_provider": "genesys_audio_connector",
        "security": {
            "api_key": "test_api_key",
            "client_secret": "test_client_secret"
        }
    }


@pytest.fixture
def sample_phone_config_response():
    """Sample phone config API response."""
    return {
        "id": "phone-123",
        "name": "test_phone_config",
        "description": "Test phone configuration",
        "service_provider": "genesys_audio_connector",
        "security": {
            "api_key": "test_api_key",
            "client_secret": "test_client_secret"
        },
        "attached_environments": [],
        "phone_numbers": [],
        "tenant_id": "tenant-456",
        "created_on": "2024-01-01T00:00:00Z"
    }


class TestPhoneControllerClients:
    """Tests for client getter methods."""

    def test_get_phone_client(self, phone_controller):
        """Test getting phone client instance."""
        with patch('ibm_watsonx_orchestrate.cli.commands.phone.phone_controller.instantiate_client') as mock_instantiate:
            mock_client = Mock()
            mock_instantiate.return_value = mock_client

            client = phone_controller.get_phone_client()

            assert client == mock_client
            assert phone_controller.phone_client == mock_client

    def test_get_phone_client_cached(self, phone_controller):
        """Test that phone client is cached after first call."""
        with patch('ibm_watsonx_orchestrate.cli.commands.phone.phone_controller.instantiate_client') as mock_instantiate:
            mock_client = Mock()
            mock_instantiate.return_value = mock_client

            client1 = phone_controller.get_phone_client()
            client2 = phone_controller.get_phone_client()

            assert client1 == client2
            mock_instantiate.assert_called_once()

    def test_get_agent_client(self, phone_controller):
        """Test getting agent client instance."""
        with patch('ibm_watsonx_orchestrate.cli.commands.phone.phone_controller.instantiate_client') as mock_instantiate:
            mock_client = Mock()
            mock_instantiate.return_value = mock_client

            client = phone_controller.get_agent_client()

            assert client == mock_client
            assert phone_controller.agent_client == mock_client


class TestPhoneControllerListTypes:
    """Tests for listing phone channel types."""

    def test_list_phone_channel_types(self, phone_controller, capsys):
        """Test listing all phone channel types."""
        phone_controller.list_phone_channel_types()

        captured = capsys.readouterr()
        assert "genesys_audio_connector" in captured.out


class TestPhoneControllerResolveConfigId:
    """Tests for config ID resolution."""

    def test_resolve_config_id_with_id_only(self, phone_controller, mock_phone_client):
        """Test resolving with ID only."""
        phone_controller.phone_client = mock_phone_client

        result = phone_controller.resolve_config_id(config_id="config-123")

        assert result == "config-123"

    def test_resolve_config_id_with_name_only(self, phone_controller, mock_phone_client):
        """Test resolving with name only."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.list_phone_channels.return_value = [
            {"id": "config-123", "name": "test_config"}
        ]

        result = phone_controller.resolve_config_id(config_name="test_config")

        assert result == "config-123"

    def test_resolve_config_id_with_both_matching(self, phone_controller, mock_phone_client):
        """Test resolving with both ID and name that match."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.get_phone_channel.return_value = {
            "id": "config-123",
            "name": "test_config"
        }

        result = phone_controller.resolve_config_id(config_id="config-123", config_name="test_config")

        assert result == "config-123"

    def test_resolve_config_id_with_both_not_matching(self, phone_controller, mock_phone_client, caplog):
        """Test resolving with ID and name that don't match."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.get_phone_channel.return_value = {
            "id": "config-123",
            "name": "different_name"
        }

        with pytest.raises(SystemExit):
            phone_controller.resolve_config_id(config_id="config-123", config_name="test_config")

        assert "has name 'different_name', not 'test_config'" in caplog.text

    def test_resolve_config_id_name_not_found(self, phone_controller, mock_phone_client, caplog):
        """Test resolving with non-existent name."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.list_phone_channels.return_value = []

        with pytest.raises(SystemExit):
            phone_controller.resolve_config_id(config_name="nonexistent")

        assert "not found" in caplog.text

    def test_resolve_config_id_multiple_names(self, phone_controller, mock_phone_client, caplog):
        """Test resolving with multiple configs having same name."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.list_phone_channels.return_value = [
            {"id": "config-123", "name": "test_config"},
            {"id": "config-456", "name": "test_config"}
        ]

        with pytest.raises(SystemExit):
            phone_controller.resolve_config_id(config_name="test_config")

        assert "Multiple phone configs" in caplog.text

    def test_resolve_config_id_neither_provided(self, phone_controller, caplog):
        """Test resolving with neither ID nor name."""
        with pytest.raises(SystemExit):
            phone_controller.resolve_config_id()

        assert "Either --id or --name must be provided" in caplog.text


class TestPhoneControllerCreateConfig:
    """Tests for creating phone configs."""

    def test_create_phone_config_from_args_genesys(self, phone_controller):
        """Test creating Genesys config from CLI args."""
        channel = phone_controller.create_phone_config_from_args(
            channel_type=PhoneChannelType.GENESYS_AUDIO_CONNECTOR,
            name="test_config",
            description="Test description",
            security={"api_key": "key123", "client_secret": "secret456"}
        )

        assert isinstance(channel, GenesysAudioConnectorChannel)
        assert channel.name == "test_config"
        assert channel.description == "Test description"
        assert channel.security["api_key"] == "key123"

    def test_create_phone_config_from_args_with_output_file(self, phone_controller):
        """Test creating config with output file."""
        with patch('ibm_watsonx_orchestrate.cli.commands.phone.phone_controller.safe_open', mock_open()) as mock_file, \
             patch('ibm_watsonx_orchestrate.cli.commands.phone.phone_controller.yaml.dump') as mock_yaml:

            channel = phone_controller.create_phone_config_from_args(
                channel_type=PhoneChannelType.GENESYS_AUDIO_CONNECTOR,
                name="test_config",
                output_file="output.yaml",
                security={"api_key": "key123", "client_secret": "secret456"}
            )

            mock_file.assert_called_once_with("output.yaml", 'w')
            mock_yaml.assert_called_once()

    def test_create_phone_config_from_args_invalid_output_extension(self, phone_controller, caplog):
        """Test creating config with invalid output file extension."""
        with pytest.raises(SystemExit):
            phone_controller.create_phone_config_from_args(
                channel_type=PhoneChannelType.GENESYS_AUDIO_CONNECTOR,
                name="test_config",
                output_file="output.txt",
                security={"api_key": "key123", "client_secret": "secret456"}
            )

        assert "must have .yaml or .yml extension" in caplog.text

    def test_create_phone_config_from_args_validation_error(self, phone_controller, caplog):
        """Test creating config with validation error."""
        with pytest.raises(SystemExit):
            phone_controller.create_phone_config_from_args(
                channel_type=PhoneChannelType.GENESYS_AUDIO_CONNECTOR,
                name="test_config",
                # Missing required security field
            )

        assert "Validation failed" in caplog.text

    @patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_common.is_local_dev', return_value=False)
    def test_create_phone_config(self, mock_is_local_dev, phone_controller, mock_phone_client, sample_genesys_config, caplog):
        """Test creating a phone config via API."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.create_phone_channel.return_value = {"id": "phone-123"}

        channel = GenesysAudioConnectorChannel(**sample_genesys_config)
        config_id = phone_controller.create_phone_config(channel)

        assert config_id == "phone-123"
        assert "Successfully created" in caplog.text

    @patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_common.is_local_dev', return_value=False)
    def test_create_or_update_phone_config_create(self, mock_is_local_dev, phone_controller, mock_phone_client, sample_genesys_config, caplog):
        """Test create_or_update when config doesn't exist."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.create_or_update_phone_channel.return_value = ({"id": "phone-123"}, True)

        channel = GenesysAudioConnectorChannel(**sample_genesys_config)
        config_id = phone_controller.create_or_update_phone_config(channel)

        assert config_id == "phone-123"
        assert "created" in caplog.text

    @patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_common.is_local_dev', return_value=False)
    def test_create_or_update_phone_config_update(self, mock_is_local_dev, phone_controller, mock_phone_client, sample_genesys_config, caplog):
        """Test create_or_update when config exists."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.create_or_update_phone_channel.return_value = ({"id": "phone-123"}, False)

        channel = GenesysAudioConnectorChannel(**sample_genesys_config)
        config_id = phone_controller.create_or_update_phone_config(channel)

        assert config_id == "phone-123"
        assert "updated" in caplog.text


@patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_common.is_local_dev', return_value=False)
class TestPhoneControllerListConfigs:
    """Tests for listing phone configs."""

    def test_list_phone_configs(self, mock_is_local_dev, phone_controller, mock_phone_client):
        """Test listing all phone configs."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.list_phone_channels.return_value = [
            {"id": "phone-1", "name": "config1", "service_provider": "genesys_audio_connector"},
            {"id": "phone-2", "name": "config2", "service_provider": "genesys_audio_connector"}
        ]

        configs = phone_controller.list_phone_configs()

        assert len(configs) == 2

    def test_list_phone_configs_filtered(self, mock_is_local_dev, phone_controller, mock_phone_client):
        """Test listing phone configs filtered by type."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.list_phone_channels.return_value = [
            {"id": "phone-1", "name": "config1", "service_provider": "genesys_audio_connector"},
            {"id": "phone-2", "name": "config2", "service_provider": "other_type"}
        ]

        configs = phone_controller.list_phone_configs(channel_type=PhoneChannelType.GENESYS_AUDIO_CONNECTOR)

        assert len(configs) == 1
        assert configs[0]["service_provider"] == "genesys_audio_connector"

    def test_list_phone_configs_empty(self, mock_is_local_dev, phone_controller, mock_phone_client, caplog):
        """Test listing when no configs exist."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.list_phone_channels.return_value = []

        configs = phone_controller.list_phone_configs()

        assert len(configs) == 0
        assert "No phone configs found" in caplog.text

    def test_list_phone_configs_verbose(self, mock_is_local_dev, phone_controller, mock_phone_client):
        """Test listing with verbose output."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.list_phone_channels.return_value = [
            {"id": "phone-1", "name": "config1"}
        ]

        with patch('ibm_watsonx_orchestrate.cli.commands.phone.phone_controller.rich.print_json') as mock_print:
            configs = phone_controller.list_phone_configs(verbose=True)

            mock_print.assert_called_once()


@patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_common.is_local_dev', return_value=False)
class TestPhoneControllerGetConfig:
    """Tests for getting phone config details."""

    def test_get_phone_config(self, mock_is_local_dev, phone_controller, mock_phone_client, sample_phone_config_response):
        """Test getting a phone config."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.get_phone_channel.return_value = sample_phone_config_response

        config = phone_controller.get_phone_config("phone-123", verbose=False)

        assert config["id"] == "phone-123"
        mock_phone_client.get_phone_channel.assert_called_once_with("phone-123")

    def test_get_phone_config_not_found(self, mock_is_local_dev, phone_controller, mock_phone_client, caplog):
        """Test getting non-existent config."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.get_phone_channel.return_value = None

        with pytest.raises(SystemExit):
            phone_controller.get_phone_config("nonexistent")

        assert "not found" in caplog.text

    def test_get_phone_config_verbose(self, mock_is_local_dev, phone_controller, mock_phone_client, sample_phone_config_response):
        """Test getting config with verbose output."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.get_phone_channel.return_value = sample_phone_config_response

        with patch('ibm_watsonx_orchestrate.cli.commands.phone.phone_controller.rich.print_json') as mock_print:
            phone_controller.get_phone_config("phone-123", verbose=True)

            mock_print.assert_called_once()


@patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_common.is_local_dev', return_value=False)
class TestPhoneControllerDeleteConfig:
    """Tests for deleting phone configs."""

    def test_delete_phone_config(self, mock_is_local_dev, phone_controller, mock_phone_client, caplog):
        """Test deleting a phone config."""
        phone_controller.phone_client = mock_phone_client

        phone_controller.delete_phone_config("phone-123")

        mock_phone_client.delete_phone_channel.assert_called_once_with("phone-123")
        assert "Successfully deleted" in caplog.text


@patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_common.is_local_dev', return_value=False)
class TestPhoneControllerImportExport:
    """Tests for import/export operations."""

    def test_import_phone_config_yaml(self, mock_is_local_dev, phone_controller, sample_genesys_config):
        """Test importing phone config from YAML."""
        with patch('ibm_watsonx_orchestrate.cli.commands.phone.phone_controller.Path') as mock_path, \
             patch('ibm_watsonx_orchestrate.cli.commands.phone.phone_controller.PhoneChannelLoader.from_spec') as mock_loader:
            mock_channel = GenesysAudioConnectorChannel(**sample_genesys_config)
            mock_loader.return_value = mock_channel
            mock_path.return_value.exists.return_value = True

            channel = phone_controller.import_phone_config("config.yaml")

            assert channel == mock_channel
            mock_loader.assert_called_once_with("config.yaml")

    def test_import_phone_config_python(self, mock_is_local_dev, phone_controller, sample_genesys_config):
        """Test importing phone config from Python file."""
        with patch('ibm_watsonx_orchestrate.cli.commands.phone.phone_controller.Path') as mock_path, \
             patch('ibm_watsonx_orchestrate.cli.commands.phone.phone_controller.PhoneChannelLoader.from_python') as mock_loader:
            mock_channel = GenesysAudioConnectorChannel(**sample_genesys_config)
            mock_loader.return_value = [mock_channel]
            mock_path.return_value.exists.return_value = True

            channel = phone_controller.import_phone_config("config.py")

            assert channel == mock_channel
            mock_loader.assert_called_once_with("config.py")

    def test_import_phone_config_file_not_found(self, mock_is_local_dev, phone_controller, caplog):
        """Test importing non-existent file."""
        with pytest.raises(SystemExit):
            phone_controller.import_phone_config("nonexistent.yaml")

        assert "File not found" in caplog.text

    def test_export_phone_config(self, mock_is_local_dev, phone_controller, mock_phone_client, sample_phone_config_response):
        """Test exporting phone config to YAML."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.get_phone_channel.return_value = sample_phone_config_response

        with patch('ibm_watsonx_orchestrate.cli.commands.phone.phone_controller.safe_open', mock_open()) as mock_file, \
             patch('ibm_watsonx_orchestrate.cli.commands.phone.phone_controller.yaml.dump') as mock_yaml:

            phone_controller.export_phone_config("phone-123", "output.yaml")

            mock_file.assert_called_once_with("output.yaml", 'w')
            mock_yaml.assert_called_once()

    def test_export_phone_config_invalid_extension(self, mock_is_local_dev, phone_controller, caplog):
        """Test exporting with invalid file extension."""
        with pytest.raises(SystemExit):
            phone_controller.export_phone_config("phone-123", "output.txt")

        assert "must end with '.yaml' or '.yml'" in caplog.text


@patch('ibm_watsonx_orchestrate.cli.commands.channels.channels_common.is_local_dev', return_value=False)
class TestPhoneControllerAttachments:
    """Tests for agent attachment operations."""

    def test_attach_agent_to_config(self, mock_is_local_dev, phone_controller, mock_phone_client, mock_agent_client, sample_phone_config_response, caplog):
        """Test attaching an agent to a phone config."""
        phone_controller.phone_client = mock_phone_client
        phone_controller.agent_client = mock_agent_client
        mock_phone_client.get_phone_channel.return_value = sample_phone_config_response
        mock_agent_client.get_draft_by_id.return_value = {
            "id": "agent-456",
            "name": "test_agent",
            "voice_configuration_id": "voice-config-123"
        }

        phone_controller.attach_agent_to_config(
            "phone-123", "agent-456", "env-789", "test_agent", "draft"
        )

        mock_phone_client.attach_agents_to_phone_channel.assert_called_once()
        mock_agent_client.get_draft_by_id.assert_called_once_with("agent-456")
        assert "Successfully attached" in caplog.text

    def test_attach_agent_already_attached(self, mock_is_local_dev, phone_controller, mock_phone_client, mock_agent_client, caplog):
        """Test attaching an agent that's already attached."""
        phone_controller.phone_client = mock_phone_client
        phone_controller.agent_client = mock_agent_client
        mock_phone_client.get_phone_channel.return_value = {
            "id": "phone-123",
            "name": "test_config",
            "attached_environments": [
                {"agent_id": "agent-456", "environment_id": "env-789"}
            ]
        }
        mock_agent_client.get_draft_by_id.return_value = {
            "id": "agent-456",
            "name": "test_agent",
            "voice_configuration_id": "voice-config-123"
        }

        with pytest.raises(SystemExit):
            phone_controller.attach_agent_to_config(
                "phone-123", "agent-456", "env-789", "test_agent", "draft"
            )

        assert "already attached" in caplog.text

    def test_attach_agent_without_voice_config(self, mock_is_local_dev, phone_controller, mock_phone_client, mock_agent_client, sample_phone_config_response, caplog):
        """Test attaching an agent without voice configuration shows warning."""
        phone_controller.phone_client = mock_phone_client
        phone_controller.agent_client = mock_agent_client
        mock_phone_client.get_phone_channel.return_value = sample_phone_config_response
        mock_agent_client.get_draft_by_id.return_value = {
            "id": "agent-456",
            "name": "test_agent",
            "voice_configuration_id": None
        }

        phone_controller.attach_agent_to_config(
            "phone-123", "agent-456", "env-789", "test_agent", "draft"
        )

        mock_phone_client.attach_agents_to_phone_channel.assert_called_once()
        assert "does not have voice configuration set up" in caplog.text
        assert "Successfully attached" in caplog.text

    def test_detach_agent_from_config(self, mock_is_local_dev, phone_controller, mock_phone_client, caplog):
        """Test detaching an agent from a phone config."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.get_phone_channel.return_value = {
            "id": "phone-123",
            "name": "test_config",
            "attached_environments": [
                {"agent_id": "agent-456", "environment_id": "env-789"}
            ]
        }

        phone_controller.detach_agent_from_config(
            "phone-123", "agent-456", "env-789", "test_agent", "draft"
        )

        mock_phone_client.attach_agents_to_phone_channel.assert_called_once()
        assert "Successfully detached" in caplog.text

    def test_detach_agent_not_attached(self, mock_is_local_dev, phone_controller, mock_phone_client, caplog):
        """Test detaching an agent that's not attached."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.get_phone_channel.return_value = {
            "id": "phone-123",
            "name": "test_config",
            "attached_environments": []
        }

        with pytest.raises(SystemExit):
            phone_controller.detach_agent_from_config(
                "phone-123", "agent-456", "env-789", "test_agent", "draft"
            )

        assert "is not attached" in caplog.text

    def test_list_attachments(self, mock_is_local_dev, phone_controller, mock_phone_client, mock_agent_client):
        """Test listing attachments for a phone config with agent names and environment names."""
        phone_controller.phone_client = mock_phone_client
        phone_controller.agent_client = mock_agent_client

        mock_phone_client.get_phone_channel.return_value = {
            "id": "phone-123",
            "name": "test_config",
            "attached_environments": [
                {"agent_id": "agent-456", "environment_id": "env-789"}
            ]
        }

        mock_agent_client.get_draft_by_id.return_value = {
            "name": "chat_core",
            "environments": [
                {"id": "env-789", "name": "draft"}
            ]
        }

        attachments = phone_controller.list_attachments("phone-123")

        assert len(attachments) == 1
        mock_agent_client.get_draft_by_id.assert_called_once_with("agent-456")

    def test_list_attachments_empty(self, mock_is_local_dev, phone_controller, mock_phone_client, caplog):
        """Test listing attachments when none exist."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.get_phone_channel.return_value = {
            "id": "phone-123",
            "name": "test_config",
            "attached_environments": []
        }

        attachments = phone_controller.list_attachments("phone-123")

        assert len(attachments) == 0
        assert "No agents attached" in caplog.text


class TestPhoneControllerWebhookURL:
    """Tests for webhook URL generation."""

    def test_get_phone_webhook_url_local(self, phone_controller, mock_phone_client):
        """Test webhook URL generation for local environment."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.base_url = "http://localhost:3000"

        with patch('ibm_watsonx_orchestrate.cli.commands.phone.phone_controller.is_local_dev', return_value=True):
            url = phone_controller.get_phone_webhook_url(
                "agent-123", "env-456", "genesys_audio_connector", "config-789"
            )

            assert isinstance(url, str)
            assert "/v1/agents/agent-123/environments/env-456/channels/genesys_audio_connector/config-789/connect" in url

    def test_get_phone_webhook_url_saas(self, phone_controller, mock_phone_client):
        """Test webhook URL generation for SaaS environment."""
        phone_controller.phone_client = mock_phone_client
        mock_phone_client.base_url = "https://api.example.com/instances/inst-123/v1/orchestrate"
        mock_phone_client.get_subscription_id.return_value = "sub-456"

        with patch('ibm_watsonx_orchestrate.cli.commands.phone.phone_controller.is_local_dev', return_value=False):
            url = phone_controller.get_phone_webhook_url(
                "agent-123", "env-456", "genesys_audio_connector", "config-789"
            )

            assert isinstance(url, dict)
            assert "audio_connect_uri" in url
            assert "connector_id" in url
            assert "wss://channels" in url["audio_connect_uri"]
