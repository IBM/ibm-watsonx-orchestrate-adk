#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from __future__ import annotations

from ibm_cloud_sdk_core.authenticators import MCSPAuthenticator 
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

from ibm_watsonx_orchestrate.client.utils import check_token_validity
from ibm_watsonx_orchestrate.client.base_service_instance import BaseServiceInstance
from ibm_watsonx_orchestrate.cli.commands.environment.types import EnvironmentAuthType

from ibm_watsonx_orchestrate.client.client_errors import (
    ClientError,
)


class ServiceInstance(BaseServiceInstance):
    """Connect, get details, and check usage of a Watson Machine Learning service instance."""

    def __init__(self, client) -> None:
        super().__init__()
        self._client = client
        self._credentials = client.credentials
        self._client.token = self._get_token()

    def _get_token(self) -> str:
        # If no token is set
        if self._client.token is None:
            return self._create_token()

        # Refresh is possible and token is expired
        if self._is_token_refresh_possible() and self._check_token_expiry():
            return self._create_token()

        return self._client.token
    
    def _create_token(self) -> str:
        if not self._credentials.auth_type:
            if ".cloud.ibm.com" in self._credentials.url:
                return self._authenticate(EnvironmentAuthType.IBM_CLOUD_IAM)
            else:
                return self._authenticate(EnvironmentAuthType.MCSP)
        else:
            return self._authenticate(self._credentials.auth_type)

    def _authenticate(self, auth_type: str) -> str:
        """Handles authentication based on the auth_type."""
        try:
            match auth_type:
                case EnvironmentAuthType.MCSP:
                    url = self._credentials.iam_url if self._credentials.iam_url is not None else "https://iam.platform.saas.ibm.com"
                    authenticator = MCSPAuthenticator(apikey=self._credentials.api_key, url=url)
                case EnvironmentAuthType.IBM_CLOUD_IAM:
                    authenticator = IAMAuthenticator(apikey=self._credentials.api_key, url=self._credentials.iam_url)
                case _:
                    raise ClientError(f"Unsupported authentication type: {auth_type}")

            return authenticator.token_manager.get_token()
        except Exception as e:
            raise ClientError(f"Error getting {auth_type.upper()} Token", e)

    
    def _is_token_refresh_possible(self) -> bool:
        if self._credentials.api_key:
            return True
        return False
    
    def _check_token_expiry(self):
        token = self._client.token

        return not check_token_validity(token)
