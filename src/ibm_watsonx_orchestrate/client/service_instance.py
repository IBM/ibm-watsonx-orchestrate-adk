#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from __future__ import annotations

from ibm_cloud_sdk_core.authenticators import MCSPAuthenticator 
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core.authenticators import CloudPakForDataAuthenticator

from ibm_watsonx_orchestrate.client.utils import check_token_validity, is_cpd_env
from ibm_watsonx_orchestrate.client.base_service_instance import BaseServiceInstance
from ibm_watsonx_orchestrate.cli.commands.environment.types import EnvironmentAuthType

from ibm_watsonx_orchestrate.client.client_errors import (
    ClientError,
)

import logging
logger = logging.getLogger(__name__)

from ibm_watsonx_orchestrate.cli.config import (
    Config,
    CONTEXT_SECTION_HEADER,
    CONTEXT_ACTIVE_ENV_OPT,
    ENVIRONMENTS_SECTION_HEADER,
    ENV_WXO_URL_OPT
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
                logger.warning("Using IBM IAM Auth Type. If this is incorrect please use the '--type' flag to explicitly choose one of 'ibm_iam' or 'mcsp' or 'cpd")
                return self._authenticate(EnvironmentAuthType.IBM_CLOUD_IAM)
            elif is_cpd_env(self._credentials.url):
                logger.warning("Using CPD Auth Type. If this is incorrect please use the '--type' flag to explicitly choose one of 'ibm_iam' or 'mcsp' or 'cpd")
                return self._authenticate(EnvironmentAuthType.CPD)
            else:
                logger.warning("Using MCSP Auth Type. If this is incorrect please use the '--type' flag to explicitly choose one of 'ibm_iam' or 'mcsp' or 'cpd' ")
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
                case EnvironmentAuthType.CPD:
                    url = ""
                    if self._credentials.iam_url is not None: 
                        url = self._credentials.iam_url
                    else: 
                        cfg = Config()
                        env_cfg = cfg.get(ENVIRONMENTS_SECTION_HEADER)
                        matching_wxo_url = next(
                            (env_config['wxo_url'] for env_config in env_cfg.values() if 'bypass_ssl' in env_config and 'verify' in env_config),
                            None
                        )
                        base_url = matching_wxo_url.split("/orchestrate")[0]
                        url = f"{base_url}/icp4d-api"

                    password = self._credentials.password if self._credentials.password is not None else None
                    api_key = self._credentials.api_key if self._credentials.api_key is not None else None
                    cpd_password=password if password else None
                    cpd_apikey=api_key if api_key else None
                    authenticator = CloudPakForDataAuthenticator(
                        username=self._credentials.username, 
                        password=cpd_password, 
                        apikey=cpd_apikey, 
                        url=url, 
                        disable_ssl_verification=True
                    )
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
