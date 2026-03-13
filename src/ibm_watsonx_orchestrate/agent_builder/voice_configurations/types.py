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
  background_audio_suppression: Optional[Annotated[float, Field(ge=0.0, le=1.0)]] = None
  language_customization_id: Optional[Annotated[str, Field(min_length=1, max_length=256)]] = Field(
    default=None,
    description="Language customization ID"
  )
  inactivity_timeout: Optional[Annotated[int, Field(ge=-1)]] = Field(
    default=None,
    description="Seconds of inactivity before the service stops listening. Default 30"
  )
  profanity_filter: Optional[bool] = None
  smart_formatting: Optional[bool] = None
  speaker_labels: Optional[bool] = Field(
    default=None,
    description="Enable speaker labels (beta). Default false"
  )
  redaction: Optional[bool] = None
  low_latency: Optional[bool] = None
  learning_opt_out: Optional[bool] = None
  watson_metadata: Optional[Annotated[str, Field(min_length=1, max_length=512)]] = Field(
    default=None,
    description="Value for x-watson-metadata header."
  )
  smart_formatting_version: Optional[Annotated[int, Field(ge=0)]] = Field(
    default=None,
    description="Version of smart formatting to use."
  )
  customization_weight: Optional[Annotated[float, Field(ge=0.0, le=1.0)]] = Field(
    default=None,
    description="Weight for custom language model (0.0 to 1.0). Default 0.5"
  )
  character_insertion_bias: Optional[Annotated[float, Field(ge=-1.0, le=1.0)]] = Field(
    default=None,
    description="Bias for character insertion (-1.0 to 1.0). Default 0.0"
  )
  end_of_phrase_silence_time: Optional[Annotated[float, Field(ge=0.0, le=120.0)]] = None

class EmotechSTTConfig(BaseModel):
  api_url: Annotated[str, Field(min_length=1, max_length=2048)]
  api_key: Optional[Annotated[str, Field(min_length=1, max_length=2048)]] = None
  positive_speech_threshold: Optional[float] = Field(default=0.25, description="Confidence threshold above which audio is classified as speech, default is 0.25")
  negative_speech_threshold: Optional[float] = Field(default=0.25, description="Confidence threshold below which audio is classified as non-speech, default is 0.25")
  partial_interval: Optional[int] = Field(default=500, description="Time interval (in ms) between partial transcription results, default is 500 ms.")
  silence_threshold: Optional[int] = Field(default=500, description="Silence duration (in ms) after speech used to determine end of utterance, default is 1500 ms.")

class DeepgramSTTConfig(BaseModel):
  api_url: Annotated[str, Field(min_length=1, max_length=2048)]
  api_key: Optional[Annotated[str, Field(min_length=1, max_length=2048)]] = None
  model: Annotated[str, Field(min_length=1, max_length=256)]
  keyterm: Optional[list[str]] = None
  mip_opt_out: Optional[bool] = None
  # v1/listen endpoint parameters
  channels: Optional[int] = Field(default=None, description="Number of audio channels")
  diarize: Optional[bool] = Field(default=None, description="Enable speaker diarization")
  dictation: Optional[bool] = Field(default=None, description="Enable dictation mode")
  endpointing: Optional[int] = Field(default=None, description="Endpointing silence duration in seconds, or false to disable")
  extra: Optional[List[str]] = Field(default=None, description="Extra parameters to pass to Deepgram")
  interim_results: Optional[bool] = Field(default=None, description="Enable interim results")
  keywords: Optional[List[str]] = Field(default=None, description="Keywords to detect")
  language: Optional[str] = None
  multichannel: Optional[bool] = Field(default=None, description="Transcribe each audio channel independently")
  numerals: Optional[bool] = None
  profanity_filter: Optional[bool] = Field(default=None, description="Filter profanity")
  punctuate: Optional[bool] = Field(default=None, description="Add punctuation and capitalization")
  redact: Optional[str] = Field(default=None, description="Redact sensitive information")
  replace: Optional[List[str]] = Field(default=None, description="Replace specified terms")
  search: Optional[List[str]] = Field(default=None, description="Search for specific terms")
  smart_format: Optional[bool] = Field(default=None, description="Apply smart formatting to the transcript")
  tag: Optional[List[str]] = Field(default=None, description="Tag for the request")
  utterance_end_ms: Optional[int] = Field(default=None, description="How long Deepgram will wait to send UtteranceEnd message after word has been transcribed")
  vad_events: Optional[bool] = Field(default=None, description="Enable Deepgram's voice activity detection events")
  version: Optional[str] = Field(default=None, description="API version")
  # v2/listen endpoint parameters
  eager_eot_threshold: Optional[float] = Field(
    default=None,
    ge=0.3,
    le=0.9,
    description="End-of-turn confidence required to fire an eager EOT event, between (0.3 - 0.9)"
  )
  eot_threshold: Optional[float] = Field(
    default=None,
    ge=0.5,
    le=0.9,
    description="End-of-turn confidence required to finish a turn, between (0.5 - 0.9)"
  )
  eot_timeout_ms: Optional[int] = Field(default=None, description="A turn will be finished when this much time (ms) has passed after speech, regardless of EOT confidence")


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
  rate_percentage: Optional[int] = Field(default=0, description="Rate percentage for speech synthesis, default is 0")
  pitch_percentage: Optional[int] = Field(default=0, description="Pitch percentage for speech synthesis, default is 0")
  language: Optional[Annotated[str, Field(min_length=2, max_length=16)]] = Field(default=None, description="Language code for the voice, e.g., 'en-US'")
  customization_id: Optional[Annotated[str, Field(min_length=1, max_length=256)]] = Field(default=None, description="Custom ID for the Watson TTS service")
  meta_id: Optional[Annotated[str, Field(min_length=1, max_length=256)]] = Field(default=None, description="Meta ID for the Watson TTS service")
  learning_opt_out: Optional[bool] = Field(default=None, description="Set to true to opt out of data collection for learning purposes")

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

class ElevenLabsPronounciationDict(BaseModel):
  pronunciation_dictionary_id: str = Field(..., description="ID of the pronunciation dictionary")
  version_id: str = Field(..., description="Version ID of the pronunciation dictionary")

class ElevenLabsTTSConfig(BaseModel):
  api_url: Optional[str] = Field(default=None, min_length=1, max_length=2048, description="ElevenLabs API URL")
  api_key: Optional[Annotated[str, Field(min_length=1, max_length=2048)]] = None
  model_id: Annotated[str, Field(min_length=1, max_length=128)]
  voice_id: Annotated[str, Field(min_length=1, max_length=128)]
  language_code: Optional[Annotated[str, Field(min_length=2, max_length=16)]] = None
  apply_text_normalization: Optional[str] = None
  optimize_streaming_latency: Optional[int] = Field(default=None, description="Optimize streaming latency (0-4)")
  apply_language_text_normalization: Optional[bool] = Field(default=None, description="Whether to apply language-specific text normalization")
  pronunciation_dictionary_locators: Optional[List[ElevenLabsPronounciationDict]] = Field(default=None, description="List of pronunciation dictionary locators")
  seed: Optional[int] = Field(default=None, description="Seed for deterministic audio generation")
  previous_text: Optional[str] = Field(default=None, description="Previous text for context")
  next_text: Optional[str] = Field(default=None, description="Next text for context")
  voice_settings: Optional[ElevenLabsVoiceSettings] = None

class DeepgramTTSConfig(BaseModel):
  api_key: Optional[Annotated[str, Field(min_length=1, max_length=2048)]] = None
  api_url: Optional[Annotated[str, Field(min_length=1, max_length=2048)]] = None
  language: Optional[Annotated[str, Field(min_length=1, max_length=128)]] = None
  model: Optional[Annotated[str, Field(min_length=1, max_length=128)]] = None
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
  idle_hangup_message: Optional[str] = Field(default="", description="Message to play before hanging up")

class UserIdleHandlerLangConfig(BaseModel):
  idle_timeout_message: Optional[str] = Field(
    default="",
    description="Localized idle message for this language."
  )
  idle_hangup_message: Optional[str] = Field(
    default="",
    description="Localized final hangup message for this language."
  )

class AudioClips(Enum):
  guitar_1 = "guitar_1"
  listen_1 = "listen_1"

class AgentIdleHandlerMessages(BaseModel):
  pre_hold_message: Optional[str] = Field(default="We're taking a little extra time but we'll be with you shortly. Thanks for your patience!", min_length=0, max_length=250, description="The text to play for the user before playing on-hold audio")
  hold_message: Optional[str] = Field(default="Your request is in progress. It might take a little time, but we assure you that the result will be worth the wait.", min_length=0, max_length=250, description="The text to play to the user periodically while on hold")

class AgentIdleHandler(AgentIdleHandlerMessages):
  model_config = ConfigDict(use_enum_values=True)

  typing_enabled: bool = Field(default=True, description="Enable typing indicator")
  typing_duration_seconds: int = Field(default=5, ge=0, le=30, description="Typing indicator duration in seconds")
  audio_clip_id: AudioClips = Field(default=AudioClips.guitar_1, description="Audio clip to play during hold")
  hold_audio_seconds: int = Field(default=15, ge=0, le=120, description="Duration of hold audio in seconds")

class LanguageVoiceConfig(BaseModel):
  """Voice configuration for a specific language"""
  text_to_speech: Optional[TextToSpeechConfig] = None
  speech_to_text: Optional[SpeechToTextConfig] = None
  user_idle_handler: Optional[UserIdleHandlerLangConfig] = None
  agent_idle_handler: Optional[AgentIdleHandlerMessages] = None

class AttachedAgent(BaseModel):
  id: str
  name: Optional[str] = None
  display_name: Optional[str] = None

class VoiceConfiguration(BaseModel):
  name: Annotated[str, Field(min_length=1,max_length=128)]
  llm_aggregation_timeout_seconds: Optional[float] = Field(
    default=0.8,
    description="Maximum time to wait for additional transcription content before pushing aggregated result."
  )
  speech_to_text: SpeechToTextConfig
  text_to_speech: TextToSpeechConfig
  language: Optional[Annotated[str,Field(min_length=2,max_length=16)]] = Field(
    default="en-us",
    description="Default language code, e.g., 'en-us'"
  )
  additional_languages: Optional[Dict[str, LanguageVoiceConfig]] = Field(
    default_factory=dict,
    description="Additional language configurations keyed by language code"
  )
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
    id: Optional[str] = Field(default=None, description="A unique identifier for the voice configuration.")
    speech_to_text_provider: Optional[str] = Field(default=None, description="The speech to text service provider.")
    text_to_speech_provider: Optional[str] = Field(default=None, description="The text to speech service provider.")
    attached_agents: Optional[List[str]] = Field(default=None, description="A list of agent names that use the voice configuration.")

    def get_row_details(self):
        attached_agents = ", ".join(self.attached_agents) if self.attached_agents else ""
        return [self.name, self.id, self.speech_to_text_provider, self.text_to_speech_provider, attached_agents]


