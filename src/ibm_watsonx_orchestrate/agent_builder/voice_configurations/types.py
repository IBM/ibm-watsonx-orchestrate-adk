import json
from enum import Enum
from typing import Annotated, Optional, List, Dict
from pydantic import BaseModel, Field, model_validator, ConfigDict

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

class DeepgramSTTConfig(BaseModel):
  api_url: Annotated[str, Field(min_length=1, max_length=2048)]
  api_key: Optional[Annotated[str, Field(min_length=1, max_length=2048)]] = None
  model: Annotated[str, Field(min_length=1, max_length=256)]
  language: Optional[str] = None
  numerals: Optional[bool] = None
  mip_opt_out: Optional[bool] = None


class SpeechToTextConfig(BaseModel):
  provider: Annotated[str, Field(min_length=1,max_length=128)]
  watson_stt_config: Optional[WatsonSTTConfig] = None
  emotech_stt_config: Optional[EmotechSTTConfig] = None
  deepgram_stt_config: Optional[DeepgramSTTConfig] = None

  @model_validator(mode='after')
  def validate_providers(self):
    _validate_exactly_one_of_fields(self,'SpeechToTextConfig',['watson_stt_config','emotech_stt_config','deepgram_stt_config'])
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

class ElevenLabsVoiceSettings(BaseModel):
  speed: Optional[float] = 1.0
  stability: Optional[float] = 0.5
  style: Optional[float] = 0.0
  similarity_boost: Optional[float] = 0.75
  use_speaker_boost: Optional[bool] = True

class ElevenLabsTTSConfig(BaseModel):
  api_key: Optional[Annotated[str, Field(min_length=1, max_length=2048)]] = None
  model_id: Annotated[str, Field(min_length=1, max_length=128)]
  voice_id: Annotated[str, Field(min_length=1, max_length=128)]
  language_code: Optional[Annotated[str, Field(min_length=2, max_length=16)]] = None
  apply_text_normalization: Optional[str] = None
  voice_settings: Optional[ElevenLabsVoiceSettings] = None

class DeepgramTTSConfig(BaseModel):
  api_key: Optional[Annotated[str, Field(min_length=1, max_length=2048)]] = None
  language: Optional[Annotated[str, Field(min_length=1, max_length=128)]] = None
  voice: Optional[Annotated[str, Field(min_length=1, max_length=128)]] = None
  mip_opt_out: Optional[bool] = None

class TextToSpeechConfig(BaseModel):
  provider: Annotated[str, Field(min_length=1,max_length=128)]
  watson_tts_config: Optional[WatsonTTSConfig] = None
  emotech_tts_config: Optional[EmotechTTSConfig] = None
  elevenlabs_tts_config: Optional[ElevenLabsTTSConfig] = None
  deepgram_tts_config: Optional[DeepgramTTSConfig] = None

  @model_validator(mode='after')
  def validate_providers(self):
    _validate_exactly_one_of_fields(self,'TextToSpeechConfig',['watson_tts_config','emotech_tts_config','elevenlabs_tts_config','deepgram_tts_config'])
    return self

class AdditionalProperties(BaseModel):
  speech_to_text: Optional[SpeechToTextConfig] = None
  text_to_speech: Optional[TextToSpeechConfig] = None

class DTMFInput(BaseModel):
  inter_digit_timeout_ms: Optional[int] = Field(default=2500, description="The amount of time (ms) to wait for a new DTMF digit")
  termination_key: Optional[str] = Field(default=None, description="The DTMF termination key that signals the end of DTMF input")
  maximum_count: Optional[int] = Field(default=None, description="Maximum number of digits a user can enter")
  ignore_speech: Optional[bool] = Field(default=True, description="Disable speech recognition during collection of DTMF digits")

class SileroVADConfig(BaseModel):
  confidence: Optional[float] = Field(default=0.7, description="The confidence threshold for speech detection (between 0.0 and 1.0)")
  start_seconds: Optional[float] = Field(default=0.2, description="The time in seconds speech must be detected before transitioning to SPEAKING state")
  stop_seconds: Optional[float] = Field(default=0.8, description="The time in seconds silence must be detected before transitioning to QUIET state")
  min_volume: Optional[float] = Field(default=0.6, description="The minimum audio volume threshold for speech detection (between 0.0 and 1.0)")

class VADConfig(BaseModel):
  enabled: Optional[bool] = Field(default=True, description="Enable Voice Activity Detection")
  provider: Optional[str] = Field(default="silero_vad", min_length=1, max_length=128)
  silero_vad_config: Optional[SileroVADConfig] = None

  @model_validator(mode='after')
  def set_default_silero_config(self):
    """Ensure silero_vad_config is set with default values when provider is silero_vad"""
    if self.provider == "silero_vad" and self.silero_vad_config is None:
      self.silero_vad_config = SileroVADConfig()
    return self

class UserIdleHandlerConfig(BaseModel):
  enabled: Optional[bool] = Field(default=False, description="Enable idle handling")
  idle_timeout: Optional[int] = Field(default=7, description="Idle timeout in seconds before triggering the handler")
  idle_max_reprompts: Optional[int] = Field(default=2, description="How many times to replay before ending the session")
  idle_timeout_message: Optional[str] = Field(default="", description="Message to play on idle")

class AudioClips(Enum):
  guitar_1 = "guitar_1"
  listen_1 = "listen_1"

class AgentIdleHandlerMessages(BaseModel):
  pre_hold_message: Optional[str] = Field(default="We're taking a little extra time but we'll be with you shortly. Thanks for your patience!", max_length=250, description="The text to play for the user before playing on-hold audio")
  hold_message: Optional[str] = Field(default="Your request is in progress. It might take a little time, but we assure you that the result will be worth the wait.", max_length=250, description="The text to play to the user periodically while on hold")

class AgentIdleHandler(AgentIdleHandlerMessages):
  model_config = ConfigDict(use_enum_values=True)

  typing_enabled: Optional[bool] = Field(default=True, description="Enable typing indicator")
  typing_duration_seconds: Optional[int] = Field(default=5, ge=0, le=30, description="Typing indicator duration in seconds")
  audio_clip_id: Optional[AudioClips] = Field(default=AudioClips.guitar_1, description="Audio clip to play during hold")
  hold_audio_seconds: Optional[int] = Field(default=15, ge=0, le=120, description="Duration of hold audio in seconds")

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
  vad: Optional[VADConfig] = None
  user_idle_handler: Optional[UserIdleHandlerConfig] = None
  agent_idle_handler: Optional[AgentIdleHandler] = None
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

class VoiceConfigurationListEntry(BaseModel):
    name: str = Field(description="Name of the voice configuration.")
    id: str = Field(default=None, description="A unique identifier for the voice configuration.")
    speech_to_text_provider: Optional[str] = Field("The speech to text service provider.")
    text_to_speech_provider: Optional[str] = Field("The text to speech service provider.")
    attached_agents: Optional[List[str]] = Field("A list of agent names that use the voice configuration.")

    def get_row_details(self):
        attached_agents = ", ".join(self.attached_agents) if self.attached_agents else ""
        return [self.name, self.id, self.speech_to_text_provider, self.text_to_speech_provider, attached_agents]


