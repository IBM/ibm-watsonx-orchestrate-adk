from ibm_watsonx_orchestrate.cli.commands.channels import channels_command
from unittest.mock import patch

class TestAgentList:
    def test_channel_list_channel_non_verbose(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.channels.channels_controller.list_channels"
        ) as mock:
            channels_command.list_channel()

            mock.assert_called_once_with()