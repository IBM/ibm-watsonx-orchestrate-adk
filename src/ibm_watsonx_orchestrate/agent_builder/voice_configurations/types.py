import json
from typing import Annotated, Optional, List, Dict
from pydantic import BaseModel, Field, model_validator

def _validate_exactly_one_of_fields(object: BaseModel, object_name: str, fields: list[str]):
  present_fields = [getattr(object,field) for field in fields if getattr(object,field) is not None]

  if len(present_fields) != 1:
    raise ValueError(f"{object_name} requires exactly one of {','.join(fields)}")


def _validate_language_uniqueness(config: BaseModel):
  if hasattr(config,'language') and hasattr(config,'additional_languages'):
    if config.language and config.additional_languages and config.language in config.additional_languages:
      raise ValueError(f"Language '{config.language}' cannot be in both the default language and additional_languages")


class WatsonSTTConfig(BaseModel):
  api_url: Annotated[str, Field(min_length=1,max_length=2048)]
  api_key: Optional[Annotated[str, Field(min_length=1,max_length=2048)]] = None
  bearer_token: Optional[Annotated[str, Field(min_length=1,max_length=2048)]] = None
  model: Annotated[str, Field(min_length=1,max_length=256)]

class EmotechSTTConfig(BaseModel):
  api_key: Annotated[str,Field(min_length=1,max_length=2048)]
  api_url: Annotated[str,Field(min_length=1,max_length=2048)]


class SpeechToTextConfig(BaseModel):
  provider: Annotated[str, Field(min_length=1,max_length=128)]
  watson_stt_config: Optional[WatsonSTTConfig] = None
  emotech_stt_config: Optional[EmotechSTTConfig] = None

  @model_validator(mode='after')
  def validate_providers(self):
    _validate_exactly_one_of_fields(self,'SpeechToTextConfig',['watson_stt_config','emotech_stt_config'])
    return self

class WatsonTTSConfig(BaseModel):
  api_url: Annotated[str, Field(min_length=1,max_length=2048)]
  api_key: Optional[Annotated[str, Field(min_length=1,max_length=2048)]] = None
  bearer_token: Optional[Annotated[str, Field(min_length=1,max_length=2048)]] = None
  voice: Annotated[str, Field(min_length=1,max_length=128)]
  rate_percentage: Optional[int] = None
  pitch_percentage: Optional[int] = None
  language: Optional[str] = None

class EmotechTTSConfig(BaseModel):
  api_url: Annotated[str, Field(min_length=1,max_length=2048)]
  api_key: Annotated[str, Field(min_length=1,max_length=2048)]
  voice: Optional[Annotated[str, Field(min_length=1,max_length=128)]]

class TextToSpeechConfig(BaseModel):
  provider: Annotated[str, Field(min_length=1,max_length=128)]
  watson_tts_config: Optional[WatsonTTSConfig] = None
  emotech_tts_config: Optional[EmotechTTSConfig] = None

  @model_validator(mode='after')
  def validate_providers(self):
    _validate_exactly_one_of_fields(self,'TextToSpeechConfig',['watson_tts_config','emotech_tts_config'])
    return self

class AdditionalProperties(BaseModel):
  speech_to_text: Optional[SpeechToTextConfig] = None
  text_to_speech: Optional[TextToSpeechConfig] = None

class DTMFInput(BaseModel):
  inter_digit_timeout_ms: Optional[int] = None
  termination_key: Optional[str] = None
  maximum_count: Optional[int] = None
  ignore_speech: Optional[bool] = None

class AttachedAgent(BaseModel):
  id: str
  name: Optional[str] = None
  display_name: Optional[str] = None

class VoiceConfiguration(BaseModel):
  name: Annotated[str, Field(min_length=1,max_length=128)]
  speech_to_text: SpeechToTextConfig
  text_to_speech: TextToSpeechConfig
  language: Optional[Annotated[str,Field(min_length=2,max_length=16)]] = None
  additional_languages: Optional[dict[str,AdditionalProperties]] = None
  dtmf_input: Optional[DTMFInput] = None
  voice_configuration_id: Optional[str] = None
  tenant_id: Optional[Annotated[str, Field(min_length=1,max_length=128)]] = None
  attached_agents: Optional[list[AttachedAgent]] = None

  @model_validator(mode='after')
  def validate_language(self):
    _validate_language_uniqueness(self)
    return self

  def dumps_spec(self) -> str:
    dumped = self.model_dump(mode='json', exclude_none=True)
    return json.dumps(dumped, indent=2)


