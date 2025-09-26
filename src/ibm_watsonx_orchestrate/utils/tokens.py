from datetime import timezone, datetime
from urllib.parse import urlparse

import jwt

from ibm_watsonx_orchestrate.cli.commands.environment.types import EnvironmentAuthType
from ibm_watsonx_orchestrate.client.client import Client
from ibm_watsonx_orchestrate.client.client_errors import ClientError
from ibm_watsonx_orchestrate.client.credentials import Credentials
from ibm_watsonx_orchestrate.utils.environment import EnvSettingsService


class CpdWxOTokenService:

    def __init__ (self, env_settings: EnvSettingsService):
        self.__token = None
        self.__token_exp_at = None
        self.__env_settings = env_settings

    def get_token (self) -> str:
        if self.__token is None or self.__has_token_expired():
            self.__refresh_token()

        return self.__token

    def __has_token_expired (self) -> bool:
        return self.__token is None or self.__token_exp_at is None or datetime.now(
            timezone.utc).timestamp() >= self.__token_exp_at

    def __refresh_token (self) -> None:
        try:
            self.__token = None
            self.__token_exp_at = None

            creds = Credentials(
                url=self.__env_settings.get_wo_instance_url(),
                api_key=self.__env_settings.get_wo_api_key(),
                username=self.__env_settings.get_wo_username(),
                password=self.__env_settings.get_wo_password(),
                iam_url=None,
                auth_type=EnvironmentAuthType.CPD
            )

            client = Client(creds)
            self.__token = client.token

            decoded_token = jwt.decode(self.__token, options={"verify_signature": False})
            self.__token_exp_at = decoded_token.get("exp")

        except ClientError as ex:
            raise ClientError(ex)
