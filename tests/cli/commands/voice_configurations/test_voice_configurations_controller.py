from unittest.mock import patch
from pydantic import BaseModel
from ibm_watsonx_orchestrate.agent_builder.voice_configurations import VoiceConfiguration
from ibm_watsonx_orchestrate.cli.commands.voice_configurations.voice_configurations_controller import VoiceConfigurationsController


def voice_configuration_dict(
    expected_name="default_name",
    expected_stt_provider="default_stt",
    expected_tts_provider="default_tts",
    expected_id="default_id" 
) -> dict:
  return {
    "name": expected_name,
    "speech_to_text": { "provider" : expected_stt_provider },
    "text_to_speech": { "provider" : expected_tts_provider },
    "voice_configuration_id": expected_id
  }

class VoiceProviderMock:
  provider: str

class  VoiceConfigMock:
  name: str
  speech_to_text: VoiceProviderMock
  text_to_speech: VoiceProviderMock
  voice_configuration_id: str

def voice_configuration_class(
    expected_name="default_name",
    expected_stt_provider="default_stt",
    expected_tts_provider="default_tts",
    expected_id="default_id" 
) -> BaseModel :
  config = VoiceConfigMock()
  config.name = expected_name

  stt = VoiceProviderMock()
  stt.provider = expected_stt_provider
  config.speech_to_text = stt
  
  tts = VoiceProviderMock()
  tts.provider = expected_tts_provider
  config.text_to_speech = tts

  config.voice_configuration_id = expected_id

  return config

class TestGetVoiceConfiguration:
  
  def test_get(self):
    with patch("ibm_watsonx_orchestrate.client.voice_configurations.voice_configurations_client.VoiceConfigurationsClient.get") as get_mock:
      expected_id = "test_id"
      VoiceConfigurationsController().get_voice_config(voice_config_id=expected_id)
      get_mock.assert_called_once_with(expected_id)

  def test_get_by_name(self):
    with patch("ibm_watsonx_orchestrate.client.voice_configurations.voice_configurations_client.VoiceConfigurationsClient.get_by_name") as get_mock:
      expected_id = "test_id"
      expected_name = "test_name"
      get_mock.return_value = [voice_configuration_dict(expected_name=expected_name, expected_id=expected_id)]

      VoiceConfigurationsController().get_voice_config_by_name(voice_config_name=expected_name)
      get_mock.assert_called_once()

  def test_fetch(self):
    with patch("ibm_watsonx_orchestrate.client.voice_configurations.voice_configurations_client.VoiceConfigurationsClient.list") as list_mock:
      VoiceConfigurationsController().fetch_voice_configs()
      list_mock.assert_called_once()



class TestCreateVoiceConfiguration:
  
  def test_create(self):
    with patch("ibm_watsonx_orchestrate.client.voice_configurations.voice_configurations_client.VoiceConfigurationsClient.create") as create_mock:
      expected_id = "new_id"
      create_mock.return_value = {"id": expected_id }
      mock_config = voice_configuration_dict(expected_id=expected_id)
      id = VoiceConfigurationsController().create_voice_config(
        voice_config=mock_config
      )

      create_mock.assert_called_once_with(mock_config)
      assert id == expected_id
    


class TestUpdateVoiceConfiguration:
  
  def test_update_by_id(self):
    with patch("ibm_watsonx_orchestrate.client.voice_configurations.voice_configurations_client.VoiceConfigurationsClient.update") as update_mock:
      expected_id = "new_id"
      update_mock.return_value = {"id": expected_id }
      mock_config = voice_configuration_dict(expected_id=expected_id)
      id = VoiceConfigurationsController().update_voice_config_by_id(
        voice_config_id=expected_id,
        voice_config=mock_config
      )

      update_mock.assert_called_once_with(expected_id, mock_config)
      assert id == expected_id

  def test_update_by_name(self):
    with patch("ibm_watsonx_orchestrate.client.voice_configurations.voice_configurations_client.VoiceConfigurationsClient.update") as update_mock, \
      patch("ibm_watsonx_orchestrate.client.voice_configurations.voice_configurations_client.VoiceConfigurationsClient.get_by_name") as get_mock:
      
      expected_id = "new_id"
      update_mock.return_value = {"id": expected_id }
      expected_name = "test_name"
      mock_config = voice_configuration_class(
        expected_id=expected_id,
        expected_name=expected_name
      )
      get_mock.return_value = [mock_config]

      id = VoiceConfigurationsController().update_voice_config_by_name(
        voice_config_name=expected_name,
        voice_config=mock_config
      )

      get_mock.assert_called_once()
      update_mock.assert_called_once_with(expected_id, mock_config)
      assert id == expected_id


class TestRemoveVoiceConfiguration:
  
  def test_remove_by_id(self):
    with patch("ibm_watsonx_orchestrate.client.voice_configurations.voice_configurations_client.VoiceConfigurationsClient.delete") as delete_mock:
      expected_id = "test_id"
      VoiceConfigurationsController().remove_voice_config_by_id(voice_config_id=expected_id)

      delete_mock.assert_called_once_with(expected_id)

  def test_remove_by_name(self):
    with patch("ibm_watsonx_orchestrate.client.voice_configurations.voice_configurations_client.VoiceConfigurationsClient.delete") as delete_mock, \
      patch("ibm_watsonx_orchestrate.client.voice_configurations.voice_configurations_client.VoiceConfigurationsClient.get_by_name") as get_mock:
      expected_id = "test_id"
      expected_name = "test_name"
      mock_config = voice_configuration_class(
        expected_id=expected_id,
        expected_name=expected_name
      )
      get_mock.return_value = [mock_config]

      VoiceConfigurationsController().remove_voice_config_by_name(voice_config_name=expected_name)

      get_mock.assert_called_once()
      delete_mock.assert_called_once_with(expected_id)