from ibm_watsonx_orchestrate.cli.commands.channels import channels_command
from ibm_watsonx_orchestrate.agent_builder.channels.types import ChannelType
from unittest.mock import patch, Mock, MagicMock

class TestChannelCommands:
    def test_list_channel_types(self):
        """Test list command calls controller.list_channels function."""
        mock_controller = Mock()

        with patch.object(channels_command, 'controller', mock_controller):
            channels_command.list_channel()
            mock_controller.list_channels.assert_called_once_with()

    def test_import_channel_resolves_environment(self):
        """Test import command resolves env name to UUID."""
        mock_controller = Mock()
        mock_controller.get_agent_id_by_name.return_value = "agent-123"
        mock_controller.get_environment_id.return_value = "env-12345678"
        mock_channel = Mock()
        mock_controller.import_channel.return_value = [mock_channel]  # Return list of channels

        with patch.object(channels_command, 'controller', mock_controller):
            channels_command.import_channel(
                agent_name="test_agent",
                env="draft",
                file="test.yaml"
            )

            # Verify environment name was resolved to UUID
            mock_controller.get_environment_id.assert_called_once_with("test_agent", "draft")
            # Verify publish was called with resolved UUID
            mock_controller.publish_or_update_channel.assert_called_once()
            args = mock_controller.publish_or_update_channel.call_args[0]
            assert args[0] == "agent-123"
            assert args[1] == "env-12345678"

    def test_list_channels_resolves_environment(self):
        """Test list command resolves env name to UUID."""
        mock_controller = Mock()
        mock_controller.get_agent_id_by_name.return_value = "agent-123"
        mock_controller.get_environment_id.return_value = "env-12345678"

        with patch.object(channels_command, 'controller', mock_controller):
            channels_command.list_channels_command(
                agent_name="test_agent",
                env="live",
                channel_type=None,
                verbose=False,
                format=None
            )

            # Verify environment name was resolved to UUID
            mock_controller.get_environment_id.assert_called_once_with("test_agent", "live")
            # Verify list_channels_agent was called with resolved UUID
            mock_controller.list_channels_agent.assert_called_once_with(
                "agent-123", "env-12345678", None, False, None, agent_name="test_agent"
            )

    def test_create_channel_resolves_environment(self):
        """Test create command resolves env name to UUID."""
        mock_controller = Mock()
        mock_controller.get_agent_id_by_name.return_value = "agent-123"
        mock_controller.get_environment_id.return_value = "env-12345678"
        mock_controller.create_channel_from_args.return_value = Mock()

        with patch.object(channels_command, 'controller', mock_controller):
            channels_command.create_channel(
                agent_name="test_agent",
                env="draft",
                channel_type=ChannelType.WEBCHAT,
                name="test_channel",
                description=None,
                field=None,
                output_file=None
            )

            # Verify environment name was resolved to UUID
            mock_controller.get_environment_id.assert_called_once_with("test_agent", "draft")
            # Verify publish was called with resolved UUID
            mock_controller.publish_or_update_channel.assert_called_once()
            args = mock_controller.publish_or_update_channel.call_args[0]
            assert args[0] == "agent-123"
            assert args[1] == "env-12345678"

    def test_delete_channel_resolves_environment(self):
        """Test delete command resolves env name to UUID and channel ID."""
        mock_controller = Mock()
        mock_controller.get_agent_id_by_name.return_value = "agent-123"
        mock_controller.get_environment_id.return_value = "env-12345678"
        mock_controller.resolve_channel_id.return_value = "ch-789"

        with patch.object(channels_command, 'controller', mock_controller):
            channels_command.delete_channel(
                agent_name="test_agent",
                env="live",
                channel_type=ChannelType.WEBCHAT,
                channel_id="ch-789",
                channel_name=None,
                confirm=True  # Skip confirmation prompt
            )

            # Verify environment name was resolved to UUID
            mock_controller.get_environment_id.assert_called_once_with("test_agent", "live")
            # Verify resolve_channel_id was called
            mock_controller.resolve_channel_id.assert_called_once_with(
                "agent-123", "env-12345678", ChannelType.WEBCHAT, "ch-789", None
            )
            # Verify delete was called with resolved UUID and ID
            mock_controller.delete_channel.assert_called_once_with(
                "agent-123", "env-12345678", ChannelType.WEBCHAT, "ch-789"
            )