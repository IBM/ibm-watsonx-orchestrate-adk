

from abc import abstractmethod
import os
from typing import Optional
from ibm_watsonx_orchestrate.cli.config import AUTH_CONFIG_FILE, AUTH_CONFIG_FILE_FOLDER, AUTH_MCSP_TOKEN_OPT, AUTH_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT, CONTEXT_SECTION_HEADER, Config
from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient
from ibm_watsonx_orchestrate.utils.environment import EnvService
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load




class BaseInferenceClient(BaseWXOClient):

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

  @abstractmethod
  def generate_response(self):    
    raise NotImplementedError(f"Function 'generate_response' not implemented for '{self.__class__.__name__}'")

  @abstractmethod
  def extract_message_from_response(self):
    raise NotImplementedError(f"Function 'extract_multiline_string_from_response' not implemented for '{self.__class__.__name__}'")
  
  def get_active_env(self) -> str:
    return self.cfg.read(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
  
  def is_local_dev(self):
    active_env= self.get_active_env()
    return active_env.lower() == 'local'
  
  def get_instance_auth_token(self, env: Optional[str] = None):
    if not env:
      env = self.get_active_env()

    with open(os.path.join(AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE), "r") as f:
      auth_config = yaml_safe_load(f)
      
    auth_settings = auth_config.get(AUTH_SECTION_HEADER, {}).get(env, None)

    if not auth_settings:
      raise BadRequest(f"No auth configuration found for environment '{env}'")

    return auth_settings.get(AUTH_MCSP_TOKEN_OPT)

  def create_message_format_request(self, input: str, instructions: Optional[str] = None) -> list:
    
    messages = []
    
    if instructions:
      messages.append(
        {
          "role": "system",
          "content": instructions
        }
      )
    
    messages.append(
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": input

          }
        ]
      }
    )

    return messages
    
  