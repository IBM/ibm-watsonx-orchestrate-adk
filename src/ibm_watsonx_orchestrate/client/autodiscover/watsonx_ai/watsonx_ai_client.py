
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from ibm_watsonx_orchestrate.cli.commands.server.types import _create_wxai_authenticator
from ibm_watsonx_orchestrate.cli.config import Config
from ibm_watsonx_orchestrate.client.autodiscover import BaseInferenceClient
from ibm_watsonx_orchestrate.utils.environment import EnvService
from ibm_cloud_sdk_core.authenticators import Authenticator,IAMAuthenticator

from ibm_watsonx_orchestrate.utils.exceptions import BadRequest


WATSONX_AI_DEFAULT_MODEL = "meta-llama/llama-3-3-70b-instruct"

WATSONX_AI_URL_ENV_KEY = "WATSONX_URL"
WATSONX_AI_SPACE_ID_ENV_KEY = "WATSONX_SPACE_ID"
WATSONX_AI_APIKEY_ENV_KEY = "WATSONX_APIKEY"

WATSONX_AUTHORIZATION_URL_ENV_KEY = "WATSONX_AUTHORIZATION_URL"

DEFAULT_WATSONX_URL = "https://api.us-south.ml.cloud.ibm.com"

class WatsonxAIRequestBody(BaseModel):
  messages: list
  space_id: str
  model_id: Optional[str] = None

class WatsonxAIClient(BaseInferenceClient):
  
  @property
  def cfg(self):
    if not self.__cfg:
      self.__cfg = Config()
    return self.__cfg

  @property
  def env(self):
    if not self.__env:
      env_svc = EnvService(self.cfg)
      default_env = env_svc.get_default_env_file()
      self.__env = EnvService.merge_env(default_env_path=default_env, user_env_path=None) 
    return self.__env
  
  def __init__( self, 
      base_url: Optional[str] = None,
      api_key: Optional[str] = None,
      space_id: Optional[str] = None,
      is_local: Optional[bool] = None,
      verify: Optional[str] = None,
      cfg: Optional[Config] = None,
      env: Optional[dict] = None,
      model: Optional[str] = None,
      authenticator: Optional[Authenticator] = None,
      **kwargs
    ):
    self.__cfg = cfg
    self.__env = env 
    if not base_url:
      base_url = self._fetch_from_env(WATSONX_AI_URL_ENV_KEY, DEFAULT_WATSONX_URL)
    if not authenticator:
      if not api_key:
        api_key = self._fetch_from_env(WATSONX_AI_APIKEY_ENV_KEY, required=True)
      auth_url = self._fetch_from_env(WATSONX_AUTHORIZATION_URL_ENV_KEY)
      authenticator = _create_wxai_authenticator(api_key=api_key, wxai_url=base_url, auth_url=auth_url)
    
    self.space_id = self._fetch_from_env(WATSONX_AI_SPACE_ID_ENV_KEY, required=True) if space_id is None else space_id
    
    self.model = model if model else WATSONX_AI_DEFAULT_MODEL
    super().__init__(base_url="", authenticator=authenticator, is_local=is_local, verify=verify)
    self.base_url = base_url + "/ml/v1"


  def generate_response( self, 
      input: str, 
      model: Optional[str] = None, 
      **kwargs
    ):
    
    messages = self.create_message_format_request(instructions=kwargs.get("instructions", None), input=input)

    request = WatsonxAIRequestBody(
      messages=messages,
      space_id=self.space_id,
      model_id=model if model else self.model
    )
    response = self._post(
        path="/text/chat?version=2023-10-25",
        data=request.model_dump()
      )
    return response
  
  def extract_message_from_response(self, response: dict) -> str:
    messages = [ choice.get("message",{}) for choice in response.get("choices", []) ]
    for item in messages:
      if item.get("role", "") != "assistant":
        continue
      response = item.get("content", "")

      return response
    
    raise BadRequest(f"No message found in llm response")

  
  def _fetch_from_env(self, key: str, default = None, required: bool = False):
    val = self.env.get(key, default)
    if required and not val:
      raise ValueError(f"Unable to connect to WatsonxAI: '{key}' not found in env")
    return val