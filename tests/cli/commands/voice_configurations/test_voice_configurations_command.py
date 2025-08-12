from unittest.mock import patch
from unittest import TestCase
from ibm_watsonx_orchestrate.cli.commands.voice_configurations import voice_configurations_command

class TestVoiceConfigurationImport:

  def test_import(self):
    with patch("ibm_watsonx_orchestrate.cli.commands.voice_configurations.voice_configurations_controller.VoiceConfigurationsController.import_voice_config") as import_mock,\
      patch("ibm_watsonx_orchestrate.cli.commands.voice_configurations.voice_configurations_controller.VoiceConfigurationsController.publish_or_update_voice_config") as publish_or_update_mock:
      voice_configurations_command.import_voice_config(file="test.yaml")
      import_mock.assert_called_once_with("test.yaml")
      publish_or_update_mock.assert_called_once_with(import_mock())

  def test_import_invalid(self):
    TestCase().assertRaises(TypeError, voice_configurations_command.import_voice_config)


class TestVoiceConfigurationRemove:

  def test_remove_by_name(self):
    with patch("ibm_watsonx_orchestrate.cli.commands.voice_configurations.voice_configurations_controller.VoiceConfigurationsController.remove_voice_config_by_name") as remove_mock:
      voice_configurations_command.remove_voice_config(voice_config_name="test_name")
      remove_mock.assert_called_once_with("test_name")

  def test_remove_invalid(self):
    TestCase().assertRaises(TypeError, voice_configurations_command.remove_voice_config)


class TestVoiceConfigurationList:
  
  def test_list(self):
    with patch("ibm_watsonx_orchestrate.cli.commands.voice_configurations.voice_configurations_controller.VoiceConfigurationsController.list_voice_configs") as list_mock:
      voice_configurations_command.list_voice_configs()
      list_mock.assert_called_once_with(False)

  def test_list_verbose(self):
    with patch("ibm_watsonx_orchestrate.cli.commands.voice_configurations.voice_configurations_controller.VoiceConfigurationsController.list_voice_configs") as list_mock:
      voice_configurations_command.list_voice_configs(verbose=True)
      list_mock.assert_called_once_with(True)