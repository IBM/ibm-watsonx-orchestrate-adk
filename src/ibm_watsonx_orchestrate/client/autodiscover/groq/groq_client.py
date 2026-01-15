

from typing import Optional

from pydantic import BaseModel
from ibm_watsonx_orchestrate.cli.config import Config
from ibm_watsonx_orchestrate.client.autodiscover import BaseInferenceClient
from ibm_watsonx_orchestrate.utils.environment import EnvService
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest


GROQ_DEFAULT_MODEL = "openai/gpt-oss-120b"
GROQ_APIKEY_ENV_KEY = "GROQ_API_KEY"
GROQ_BASE_URL = "https://api.groq.com"

class GroqRequestBody(BaseModel):
  model: str
  messages: list


class GroqClient(BaseInferenceClient):

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
      api_key: Optional[str] = None,
      verify: Optional[str] = None,
      cfg: Optional[Config] = None,
      env: Optional[dict] = None,
      model: Optional[str] = None,
      is_local: Optional[bool] = None,
      **kwargs):
    self.__cfg = cfg
    self.__env = env 
    if is_local is None:
      is_local = self.is_local_dev()
    
    if not api_key:
      api_key = self._fetch_from_env(GROQ_APIKEY_ENV_KEY, required=True)
    
    self.model = model if model else GROQ_DEFAULT_MODEL
    super().__init__(base_url="", api_key=api_key, is_local=False, verify=verify)
    self.base_url = GROQ_BASE_URL

  def generate_response(self, input: str, model: Optional[str] = None, **kwargs):
    messages = self.create_message_format_request(instructions=kwargs.get("instructions", None), input=input)
    request = GroqRequestBody(
      model=model if model else self.model,
      messages=messages
    )

    response = self._post(
      path="/openai/v1/chat/completions",
      data=request.model_dump(exclude_none=True)
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
      raise ValueError(f"Unable to connect to Groq: '{key}' not found in env")
    return val