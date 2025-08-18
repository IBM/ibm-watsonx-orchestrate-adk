from unittest import TestCase
from pydantic import ValidationError
import pytest

from ibm_watsonx_orchestrate.agent_builder.voice_configurations import VoiceConfiguration

def unset_dict_node_by_path(dict_root,path):
  pathnodes = path.split(".")
  curr = dict_root
  for n in pathnodes[:-1]:
    if type(curr) is list:
      curr=curr[int(n)]
    elif type(curr) is dict:
      curr=curr[n]
    else:
      raise ValueError
  curr[pathnodes[-1]] = None
  return dict_root

@pytest.fixture
def complete_voice_config():
  return{
    "name": "test_name",
    "speech_to_text":{
      "provider": "test_stt_provider",
      "watson_stt_config": {
        "api_url": "test_api_url",
        "api_key": "test_api_key",
        "model": "test_model"
      }
    },
    "text_to_speech": {
      "provider": "test_tts_provider",
      "watson_tts_config":{
        "api_url": "test_api_url",
        "api_key": "test_api_key",
        "voice": "test_voice",
        "rate_percentage": 100,
        "pitch_percentage": 100,
        "language": "test_language"
      }
    },
    "voice_configuration_id": "test_voice_configuration_id",
    "attached_agents": [
      {
        "id": "test_agent_id",
        "name": "test_agent_name",
        "display_name": "test_agent_display_name"
      }
    ]
  }

@pytest.fixture
def minimum_voice_config():
  return{
    "name": "test_name",
    "speech_to_text":{
      "provider": "test_stt_provider",
      "watson_stt_config":{
        "api_url": "example.url/stt",
        "api_key": "example stt key",
        "model": "example model"
      }
    },
    "text_to_speech": {
      "provider": "test_tts_provider",
      "watson_tts_config": {
        "api_url": "example.url/tts",
        "api_key": "example tts key",
        "voice": "example voice"
      }
    }
  }

@pytest.fixture(params=[
  "name",
  "speech_to_text.provider",
  "speech_to_text.watson_stt_config.api_url",
  "speech_to_text.watson_stt_config.model",
  "text_to_speech.provider",
  "text_to_speech.watson_tts_config.api_url",
  "text_to_speech.watson_tts_config.voice",
  "attached_agents.0.id"
])
def invalid_voice_config(request,complete_voice_config):
  return unset_dict_node_by_path(complete_voice_config,request.param)

class TestVoiceConfigurationInit:

  def test_complete_config(self,complete_voice_config):
    config_data = complete_voice_config
    config = VoiceConfiguration.model_validate(config_data)

    assert config.name == config_data['name']
    assert config.speech_to_text.provider == config_data['speech_to_text']['provider']
    assert config.speech_to_text.watson_stt_config.api_url == config_data['speech_to_text']['watson_stt_config']['api_url']
    assert config.speech_to_text.watson_stt_config.model == config_data['speech_to_text']['watson_stt_config']['model']
    assert config.text_to_speech.provider == config_data['text_to_speech']['provider']
    assert config.text_to_speech.watson_tts_config.api_url == config_data['text_to_speech']['watson_tts_config']['api_url']
    assert config.text_to_speech.watson_tts_config.voice == config_data['text_to_speech']['watson_tts_config']['voice']

  def test_minimum_valid_config(self,minimum_voice_config):
    config_data = minimum_voice_config
    config = VoiceConfiguration.model_validate(config_data)

    assert config.name == config_data['name']
    assert config.speech_to_text.provider == config_data['speech_to_text']['provider']
    assert config.text_to_speech.provider == config_data['text_to_speech']['provider']

  def test_invalid_config(self,invalid_voice_config):
    TestCase().assertRaises(ValidationError,VoiceConfiguration.model_validate,invalid_voice_config)
    
