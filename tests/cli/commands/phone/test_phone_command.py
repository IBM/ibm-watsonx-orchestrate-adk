from ibm_watsonx_orchestrate.cli.commands.phone import phone_command
from ibm_watsonx_orchestrate.cli.commands.phone.types import PhoneChannelType, EnvironmentType
from unittest.mock import patch, Mock
import pytest
import typer


class TestPhoneCommands:
    """Tests for phone CLI commands."""

    def test_list_phone_types(self):
        """Test list command calls controller.list_phone_channel_types function."""
        mock_controller = Mock()

        with patch.object(phone_command, 'controller', mock_controller):
            phone_command.list_phone_types()
            mock_controller.list_phone_channel_types.assert_called_once_with()

    def test_create_phone_config_basic(self):
        """Test create command with basic required fields."""
        mock_controller = Mock()
        mock_channel = Mock()
        mock_controller.create_phone_config_from_args.return_value = mock_channel

        with patch.object(phone_command, 'controller', mock_controller):
            phone_command.create_phone_config(
                name="test_phone",
                channel_type=PhoneChannelType.GENESYS_AUDIO_CONNECTOR,
                description="Test phone config",
                field=None,
                output_file=None,
                enable_developer_mode=False
            )

            mock_controller.create_phone_config_from_args.assert_called_once()
            mock_controller.create_or_update_phone_config.assert_called_once_with(mock_channel)

    def test_create_phone_config_with_fields(self):
        """Test create command with config-specific fields."""
        mock_controller = Mock()
        mock_channel = Mock()
        mock_controller.create_phone_config_from_args.return_value = mock_channel

        with patch.object(phone_command, 'controller', mock_controller):
            phone_command.create_phone_config(
                name="test_phone",
                channel_type=PhoneChannelType.GENESYS_AUDIO_CONNECTOR,
                description="Test phone config",
                field=["api_key=test_key", "client_secret=test_secret"],
                output_file=None,
                enable_developer_mode=False
            )

            # Verify the call was made with security fields nested
            call_args = mock_controller.create_phone_config_from_args.call_args
            assert call_args[1]['security']['api_key'] == 'test_key'
            assert call_args[1]['security']['client_secret'] == 'test_secret'

    def test_create_phone_config_with_output_file(self):
        """Test create command with output file (no API call)."""
        mock_controller = Mock()
        mock_channel = Mock()
        mock_controller.create_phone_config_from_args.return_value = mock_channel

        with patch.object(phone_command, 'controller', mock_controller):
            phone_command.create_phone_config(
                name="test_phone",
                channel_type=PhoneChannelType.GENESYS_AUDIO_CONNECTOR,
                description=None,
                field=None,
                output_file="test_output.yaml",
                enable_developer_mode=False
            )

            mock_controller.create_phone_config_from_args.assert_called_once()
            # Should NOT call create_or_update when output_file is specified
            mock_controller.create_or_update_phone_config.assert_not_called()

    def test_create_phone_config_invalid_field_format(self):
        """Test create command with invalid field format."""
        mock_controller = Mock()

        with patch.object(phone_command, 'controller', mock_controller):
            with pytest.raises(typer.Exit):
                phone_command.create_phone_config(
                    name="test_phone",
                    channel_type=PhoneChannelType.GENESYS_AUDIO_CONNECTOR,
                    description=None,
                    field=["invalid_field_without_equals"],
                    output_file=None,
                    enable_developer_mode=False
                )

    def test_list_phone_configs(self):
        """Test list-configs command."""
        mock_controller = Mock()

        with patch.object(phone_command, 'controller', mock_controller):
            phone_command.list_phone_configs(
                channel_type=PhoneChannelType.GENESYS_AUDIO_CONNECTOR,
                verbose=False,
                format=None,
                enable_developer_mode=False
            )

            mock_controller.list_phone_configs.assert_called_once_with(
                PhoneChannelType.GENESYS_AUDIO_CONNECTOR, False, None
            )

    def test_get_phone_config_by_id(self):
        """Test get command with config ID."""
        mock_controller = Mock()
        mock_controller.resolve_config_id.return_value = "config-123"

        with patch.object(phone_command, 'controller', mock_controller):
            phone_command.get_phone_config(
                config_id="config-123",
                config_name=None,
                verbose=False,
                enable_developer_mode=False
            )

            mock_controller.resolve_config_id.assert_called_once_with("config-123", None)
            mock_controller.get_phone_config.assert_called_once_with("config-123", False)

    def test_get_phone_config_by_name(self):
        """Test get command with config name."""
        mock_controller = Mock()
        mock_controller.resolve_config_id.return_value = "config-123"

        with patch.object(phone_command, 'controller', mock_controller):
            phone_command.get_phone_config(
                config_id=None,
                config_name="test_config",
                verbose=False,
                enable_developer_mode=False
            )

            mock_controller.resolve_config_id.assert_called_once_with(None, "test_config")
            mock_controller.get_phone_config.assert_called_once_with("config-123", False)

    def test_delete_phone_config_with_confirmation(self):
        """Test delete command with confirmation flag."""
        mock_controller = Mock()
        mock_controller.resolve_config_id.return_value = "config-123"

        with patch.object(phone_command, 'controller', mock_controller):
            phone_command.delete_phone_config(
                config_id="config-123",
                config_name=None,
                confirm=True,
                enable_developer_mode=False
            )

            mock_controller.resolve_config_id.assert_called_once_with("config-123", None)
            mock_controller.delete_phone_config.assert_called_once_with("config-123")

    def test_import_phone_config(self):
        """Test import command."""
        mock_controller = Mock()
        mock_channel = Mock()
        mock_controller.import_phone_config.return_value = mock_channel

        with patch.object(phone_command, 'controller', mock_controller):
            phone_command.import_phone_config(
                file="test_config.yaml",
                enable_developer_mode=False
            )

            mock_controller.import_phone_config.assert_called_once_with("test_config.yaml")
            mock_controller.create_or_update_phone_config.assert_called_once_with(mock_channel)

    def test_export_phone_config(self):
        """Test export command."""
        mock_controller = Mock()
        mock_controller.resolve_config_id.return_value = "config-123"

        with patch.object(phone_command, 'controller', mock_controller):
            phone_command.export_phone_config(
                config_id="config-123",
                config_name=None,
                output="output.yaml",
                enable_developer_mode=False
            )

            mock_controller.resolve_config_id.assert_called_once_with("config-123", None)
            mock_controller.export_phone_config.assert_called_once_with("config-123", "output.yaml")

    def test_attach_agent(self):
        """Test attach command."""
        mock_controller = Mock()
        mock_controller.resolve_config_id.return_value = "config-123"
        mock_controller.get_agent_id_by_name.return_value = "agent-456"
        mock_controller.get_environment_id.return_value = "env-789"

        with patch.object(phone_command, 'controller', mock_controller):
            phone_command.attach_agent(
                config_id="config-123",
                config_name=None,
                agent_name="test_agent",
                env=EnvironmentType.DRAFT,
                enable_developer_mode=False
            )

            mock_controller.resolve_config_id.assert_called_once_with("config-123", None)
            mock_controller.get_agent_id_by_name.assert_called_once_with("test_agent")
            mock_controller.get_environment_id.assert_called_once_with("test_agent", EnvironmentType.DRAFT)
            mock_controller.attach_agent_to_config.assert_called_once_with(
                "config-123", "agent-456", "env-789", "test_agent", EnvironmentType.DRAFT
            )

    def test_detach_agent_with_confirmation(self):
        """Test detach command with confirmation flag."""
        mock_controller = Mock()
        mock_controller.resolve_config_id.return_value = "config-123"
        mock_controller.get_agent_id_by_name.return_value = "agent-456"
        mock_controller.get_environment_id.return_value = "env-789"

        with patch.object(phone_command, 'controller', mock_controller):
            phone_command.detach_agent(
                config_id="config-123",
                config_name=None,
                agent_name="test_agent",
                env=EnvironmentType.DRAFT,
                confirm=True,
                enable_developer_mode=False
            )

            mock_controller.detach_agent_from_config.assert_called_once_with(
                "config-123", "agent-456", "env-789", "test_agent", EnvironmentType.DRAFT
            )

    def test_list_attachments(self):
        """Test list-attachments command."""
        mock_controller = Mock()
        mock_controller.resolve_config_id.return_value = "config-123"

        with patch.object(phone_command, 'controller', mock_controller):
            phone_command.list_attachments(
                config_id="config-123",
                config_name=None,
                format=None,
                enable_developer_mode=False
            )

            mock_controller.resolve_config_id.assert_called_once_with("config-123", None)
            mock_controller.list_attachments.assert_called_once_with("config-123", None)
