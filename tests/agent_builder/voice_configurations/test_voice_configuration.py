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

@pytest.fixture
def deepgram_stt_config():
  return{
    "name": "deepgram_stt_test",
    "speech_to_text":{
      "provider": "deepgram",
      "deepgram_stt_config":{
        "api_url": "https://api.deepgram.com",
        "api_key": "test_deepgram_key",
        "model": "nova-2"
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

@pytest.fixture
def emotech_stt_config():
  return{
    "name": "emotech_stt_test",
    "speech_to_text":{
      "provider": "emotech",
      "emotech_stt_config":{
        "api_url": "https://api.emotech.com",
        "api_key": "test_emotech_key"
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

@pytest.fixture
def elevenlabs_tts_config():
  return{
    "name": "elevenlabs_tts_test",
    "speech_to_text":{
      "provider": "test_stt_provider",
      "watson_stt_config":{
        "api_url": "example.url/stt",
        "api_key": "example stt key",
        "model": "example model"
      }
    },
    "text_to_speech": {
      "provider": "elevenlabs",
      "elevenlabs_tts_config": {
        "model_id": "eleven_turbo_v2_5",
        "voice_id": "test_voice_id"
      }
    }
  }

@pytest.fixture
def deepgram_tts_config():
  return{
    "name": "deepgram_tts_test",
    "speech_to_text":{
      "provider": "test_stt_provider",
      "watson_stt_config":{
        "api_url": "example.url/stt",
        "api_key": "example stt key",
        "model": "example model"
      }
    },
    "text_to_speech": {
      "provider": "deepgram",
      "deepgram_tts_config": {
        "voice": "aura-asteria-en"
      }
    }
  }

@pytest.fixture
def emotech_tts_config():
  return{
    "name": "emotech_tts_test",
    "speech_to_text":{
      "provider": "test_stt_provider",
      "watson_stt_config":{
        "api_url": "example.url/stt",
        "api_key": "example stt key",
        "model": "example model"
      }
    },
    "text_to_speech": {
      "provider": "emotech",
      "emotech_tts_config": {
        "api_url": "https://api.emotech.com",
        "api_key": "test_emotech_key",
        "voice": "test_voice"
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

  def test_deepgram_stt_config(self,deepgram_stt_config):
    config_data = deepgram_stt_config
    config = VoiceConfiguration.model_validate(config_data)

    assert config.name == config_data['name']
    assert config.speech_to_text.provider == "deepgram"
    assert config.speech_to_text.deepgram_stt_config.api_url == config_data['speech_to_text']['deepgram_stt_config']['api_url']
    assert config.speech_to_text.deepgram_stt_config.model == config_data['speech_to_text']['deepgram_stt_config']['model']

  def test_emotech_stt_config(self,emotech_stt_config):
    config_data = emotech_stt_config
    config = VoiceConfiguration.model_validate(config_data)

    assert config.name == config_data['name']
    assert config.speech_to_text.provider == "emotech"
    assert config.speech_to_text.emotech_stt_config.api_url == config_data['speech_to_text']['emotech_stt_config']['api_url']
    assert config.speech_to_text.emotech_stt_config.api_key == config_data['speech_to_text']['emotech_stt_config']['api_key']

  def test_elevenlabs_tts_config(self,elevenlabs_tts_config):
    config_data = elevenlabs_tts_config
    config = VoiceConfiguration.model_validate(config_data)

    assert config.name == config_data['name']
    assert config.text_to_speech.provider == "elevenlabs"
    assert config.text_to_speech.elevenlabs_tts_config.model_id == config_data['text_to_speech']['elevenlabs_tts_config']['model_id']
    assert config.text_to_speech.elevenlabs_tts_config.voice_id == config_data['text_to_speech']['elevenlabs_tts_config']['voice_id']

  def test_deepgram_tts_config(self,deepgram_tts_config):
    config_data = deepgram_tts_config
    config = VoiceConfiguration.model_validate(config_data)

    assert config.name == config_data['name']
    assert config.text_to_speech.provider == "deepgram"
    assert config.text_to_speech.deepgram_tts_config.voice == config_data['text_to_speech']['deepgram_tts_config']['voice']

  def test_emotech_tts_config(self,emotech_tts_config):
    config_data = emotech_tts_config
    config = VoiceConfiguration.model_validate(config_data)

    assert config.name == config_data['name']
    assert config.text_to_speech.provider == "emotech"
    assert config.text_to_speech.emotech_tts_config.api_url == config_data['text_to_speech']['emotech_tts_config']['api_url']
    assert config.text_to_speech.emotech_tts_config.api_key == config_data['text_to_speech']['emotech_tts_config']['api_key']
    assert config.text_to_speech.emotech_tts_config.voice == config_data['text_to_speech']['emotech_tts_config']['voice']

