from typing import Optional
from ibm_watsonx_orchestrate.cli.commands.server.types import _create_wo_authenticator
from ibm_watsonx_orchestrate.cli.config import Config
from ibm_watsonx_orchestrate.client.autodiscover import WatsonxAIClient
from ibm_cloud_sdk_core.authenticators import Authenticator,MCSPAuthenticator

from ibm_watsonx_orchestrate.utils.environment import EnvService

WXO_URL_ENV_KEY = "WO_INSTANCE"
WXO_APIKEY_ENV_KEY = "WO_API_KEY"
WXO_AUTH_URL_ENV_KEY = "AUTHORIZATION_URL"

WXAI_APIKEY_ENV_KEY = "WATSONX_APIKEY"
WXAI_SPACE_ID_ENV_KEY = "WATSONX_SPACE_ID"
WXAI_SPACE_ID_PLACEHOLDER = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"

class MLProxyClient(WatsonxAIClient):

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
      authenticator: Optional[Authenticator] = None,
      **kwargs
    ):
    self.__cfg = cfg
    self.__env = env 
    if not base_url:
      base_url = self._fetch_from_env(WXO_URL_ENV_KEY, required= not authenticator)
    if not api_key:
      api_key = self._fetch_from_env(WXO_APIKEY_ENV_KEY, required= not authenticator)
    if not space_id:
      space_id = self._fetch_from_env(WXAI_SPACE_ID_ENV_KEY, WXAI_SPACE_ID_PLACEHOLDER)
    if not authenticator:
      auth_url = self._fetch_from_env(WXO_AUTH_URL_ENV_KEY)
      authenticator = _create_wo_authenticator(api_key=api_key,instance_url=base_url,auth_url=auth_url)
    super().__init__(
      base_url=base_url,
      authenticator=authenticator,
      space_id=space_id,
      is_local=is_local,
      verify=verify,
      env=env,
      **kwargs
    )
