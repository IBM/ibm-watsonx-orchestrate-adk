from pydantic import ValidationError
from ibm_watsonx_orchestrate.agent_builder.voice_configurations import VoiceConfiguration
from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient, ClientAPIException
from ibm_watsonx_orchestrate.client.client_errors import MissingArgument

import logging
logger = logging.getLogger(__name__)

class VoiceConfigurationsClient(BaseWXOClient):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # Voice configurations endpoint is at /v1/voice_configurations
    if self.base_url.endswith("/v1/orchestrate"):
      self.base_url = self.base_url.replace("/v1/orchestrate", "/v1")

  def create(self, voice_config: VoiceConfiguration) -> dict:
    return self._post("/voice_configurations", data=voice_config.model_dump(exclude_none=True))


  def update(self, voice_config_id: str, voice_config: VoiceConfiguration) -> dict:    
    if voice_config_id in [None,""]:
      raise MissingArgument("voice_config_id")
    return self._patch(f"/voice_configurations/{voice_config_id}", data=voice_config.model_dump(exclude_none=True))


  def get_by_id(self, voice_config_id: str) -> dict | None:
    if voice_config_id in [None,""]:
      raise MissingArgument("voice_config_id")
    
    try:
      response = self._get(f"/voice_configurations/{voice_config_id}")
      return VoiceConfiguration.model_validate(response)
    
    except ClientAPIException as e:
      if e.response.status_code == 404:
        return None
      raise e
    
    except ValidationError as e:
      logger.error("Recieved unexpected response from server")
      raise e
    
  def get_by_name(self, name: str) -> list[VoiceConfiguration]:
    return self.get_by_names([name])

  def get_by_names(self, names: list[str]) -> list[VoiceConfiguration]:
    # server will implement query by name, below can be uncommented then
    # formatted_config_names = [f"names={n}" for n in names]
    # return self._get(f"/voice_configurations?{"&".join(formatted_config_names)}")
    config_list = self.list()
    filtered_list = [cfg for cfg in config_list if cfg.name in names]

    try:
      return [ VoiceConfiguration.model_validate(cfg) for cfg in filtered_list ]
    except ValidationError as e:
      logger.error("Recieved unexpected response from server")
      raise e




  def delete(self, voice_config_id: str) -> None:
    if voice_config_id in [None,""]:
      raise MissingArgument("voice_config_id")
    self._delete(f"/voice_configurations/{voice_config_id}")


  def list(self) -> list[dict]:
    try:
      response = self._get("/voice_configurations")
      return [VoiceConfiguration.model_validate(x) for x in response.get('voice_configurations',[])]
    
    except ClientAPIException as e:
      if e.response.status_code == 404:
        return []
      raise e
    
    except ValidationError as e:
      logger.error("Recieved unexpected response from server")
      raise e
