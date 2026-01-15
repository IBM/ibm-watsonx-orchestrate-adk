#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from __future__ import annotations

from ibm_cloud_sdk_core.authenticators import (
    Authenticator,
    MCSPAuthenticator,
    MCSPV2Authenticator,
    IAMAuthenticator,
    CloudPakForDataAuthenticator
) 

from ibm_watsonx_orchestrate.client.utils import check_token_validity, is_cpd_env, is_ibm_cloud_platform
from ibm_watsonx_orchestrate.client.base_service_instance import BaseServiceInstance
from ibm_watsonx_orchestrate.cli.commands.environment.types import EnvironmentAuthType

from ibm_watsonx_orchestrate.client.client_errors import (
    ClientError,
)

import logging
logger = logging.getLogger(__name__)

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
    
    def _infer_auth_type(self) -> EnvironmentAuthType:
        if is_ibm_cloud_platform(self._credentials.url):
            return EnvironmentAuthType.IBM_CLOUD_IAM
        elif is_cpd_env(self._credentials.url):
            return EnvironmentAuthType.CPD
        else:
            return EnvironmentAuthType.MCSP
    
    def _get_authenticator(self, auth_type: str | EnvironmentAuthType) -> Authenticator:
        match auth_type:
            case EnvironmentAuthType.MCSP | EnvironmentAuthType.MCSP_V1:
                url = self._credentials.iam_url if self._credentials.iam_url is not None else "https://iam.platform.saas.ibm.com"
                return MCSPAuthenticator(apikey=self._credentials.api_key, url=url)
            case EnvironmentAuthType.MCSP_V2:
                url = self._credentials.iam_url if self._credentials.iam_url is not None else "https://account-iam.platform.saas.ibm.com"
                wxo_url = self._credentials.url
                instance_id = wxo_url.split("instances/")[1]
                return MCSPV2Authenticator(
                    apikey=self._credentials.api_key, 
                    url=url, 
                    scope_collection_type="services", 
                    scope_id=instance_id
                )
            case EnvironmentAuthType.IBM_CLOUD_IAM:
                return IAMAuthenticator(apikey=self._credentials.api_key, url=self._credentials.iam_url)
            case EnvironmentAuthType.CPD:
                url = ""
                if self._credentials.iam_url is not None: 
                    url = self._credentials.iam_url
                else: 
                    base_url = self._credentials.url.split("/orchestrate")[0]
                    url = f"{base_url}/icp4d-api"

                password = self._credentials.password if self._credentials.password is not None else None
                api_key = self._credentials.api_key if self._credentials.api_key is not None else None
                cpd_password=password if password else None
                cpd_apikey=api_key if api_key else None
                return CloudPakForDataAuthenticator(
                    username=self._credentials.username, 
                    password=cpd_password, 
                    apikey=cpd_apikey, 
                    url=url, 
                    disable_ssl_verification=True
                )
            case _:
                raise ClientError(f"Unsupported authentication type: {auth_type}")
    
    def _create_token(self) -> str:
        inferred_auth_type = self._infer_auth_type()
        
        if self._credentials.auth_type:
            if self._credentials.auth_type != inferred_auth_type:
                logger.warning(f"Overriding the default authentication type '{inferred_auth_type}' for url '{self._credentials.url}' with '{self._credentials.auth_type.lower()}'")
            auth_type = self._credentials.auth_type.lower()
        else:
            inferred_type_options = [t for t in EnvironmentAuthType if t != inferred_auth_type]
            logger.warning(f"Using '{inferred_auth_type}' Auth Type. If this is incorrect please use the '--type' flag to explicitly choose one of {', '.join(inferred_type_options[:-1])} or {inferred_type_options[-1]}")
            auth_type = inferred_auth_type
        
        if auth_type == "mcsp":
            try:
                return self._authenticate(EnvironmentAuthType.MCSP_V1)
            except:
                return self._authenticate(EnvironmentAuthType.MCSP_V2)
        else:
            return self._authenticate(auth_type)

    def _authenticate(self, auth_type: str) -> str:
        """Handles authentication based on the auth_type."""
        try:
            authenticator = self._get_authenticator(auth_type)
            return authenticator.token_manager.get_token()

        except Exception as e:
            raise ClientError(f"Error getting {auth_type.upper()} Token", logg_messages=False)


    
    def _is_token_refresh_possible(self) -> bool:
        if self._credentials.api_key:
            return True
        return False
    
    def _check_token_expiry(self):
        token = self._client.token

        return not check_token_validity(token)
