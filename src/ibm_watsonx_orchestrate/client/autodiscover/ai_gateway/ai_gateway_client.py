
from typing import Annotated, Optional

from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.cli.commands.server.types import _create_wo_authenticator
from ibm_watsonx_orchestrate.cli.config import Config

from ibm_watsonx_orchestrate.client.autodiscover import BaseInferenceClient
from ibm_watsonx_orchestrate.utils.environment import EnvService
from ibm_cloud_sdk_core.authenticators import Authenticator

from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

AI_GATEWAY_URL_ENV_KEY = "AI_GATEWAY_BASE_URL"

WXO_URL_ENV_KEY = "WO_INSTANCE"
WXO_APIKEY_ENV_KEY = "WO_API_KEY"
WXO_AUTH_URL_ENV_KEY = "AUTHORIZATION_URL"

GATEWAY_ENABLED_ENV_KEY = "AI_GATEWAY_ENABLED"

AI_GATEWAY_DEFAULT_MODEL = "watsonx/meta-llama/llama-3-3-70b-instruct"

LOCAL_SERVER_URL = "http://localhost:4321"


class AIGatewayRequestBody(BaseModel):
  model: str 
  messages: list
  temperature: Optional[Annotated[float,Field(ge=0,le=2)]] = None
  top_p: Optional[Annotated[float,Field(ge=0,le=1)]] = None


class AIGatewayClient(BaseInferenceClient):

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
      is_local: Optional[bool] = None,
      verify: Optional[str] = None,
      cfg: Optional[Config] = None,
      env: Optional[dict] = None,
      model: Optional[str] = None,
      authenticator: Optional[Authenticator] = None
    ):
    self.__cfg = cfg
    self.__env = env
    if is_local is None:
      is_local = self.is_local_dev() and self.env.get(GATEWAY_ENABLED_ENV_KEY)

    if not base_url:

      if is_local:
        base_url = LOCAL_SERVER_URL
        api_key = self.get_instance_auth_token()

      else:
        base_url = self._fetch_from_env(WXO_URL_ENV_KEY, required=True)
        api_key = self._fetch_from_env(WXO_APIKEY_ENV_KEY, required=True)
        
        auth_url = self._fetch_from_env(WXO_AUTH_URL_ENV_KEY)
        authenticator = _create_wo_authenticator(api_key=api_key, instance_url=base_url, auth_url=auth_url)
        api_key = None # unset so that client uses authenticator

    self.model = model if model else AI_GATEWAY_DEFAULT_MODEL
    super().__init__(base_url=base_url, authenticator=authenticator, api_key=api_key, is_local=False, verify=verify)

  def generate_response(self, input: str, model: Optional[str] = None, **kwargs):
    messages = self.create_message_format_request(instructions=kwargs.get("instructions", None), input=input)
    request = AIGatewayRequestBody(
      model=model if model else self.model,
      messages=messages
    )
    
    response = self._post(
      path="/gateway/model/chat/completions",
      data=request.model_dump(exclude_none=True)
    )

    return response
  
  def extract_message_from_response(self, response: dict):
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
      raise ValueError(f"Unable to connect to AI Gateway: '{key}' not found in env")
    return val