#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from __future__ import annotations

import json

from ibm_cloud_sdk_core.authenticators import (
    Authenticator,
    MCSPAuthenticator,
    MCSPV2Authenticator,
    IAMAuthenticator,
    CloudPakForDataAuthenticator
)
from ibm_cloud_sdk_core.token_managers.mcspv2_token_manager import MCSPV2TokenManager
from ibm_watsonx_orchestrate_core.types.environment import EnvironmentAuthType
from ibm_watsonx_orchestrate_clients.common.utils import check_token_validity, is_cpd_env, is_ibm_cloud_platform, detect_mcsp_key_type, infer_mcspv2_iam_url
from ibm_watsonx_orchestrate_clients.common.service_instance.base_service_instance import BaseServiceInstance

from ibm_watsonx_orchestrate_clients.common.errors import (
    ClientError,
)

import logging
logger = logging.getLogger(__name__)


class _ScopelessMCSPV2TokenManager(MCSPV2TokenManager):
    """MCSPV2TokenManager variant that uses the scopeless token endpoint.

    The standard MCSPV2TokenManager embeds scope_collection_type and scope_id
    into the path: /api/2.0/{scopeCollectionType}/{scopeId}/apikeys/token

    Some MCSP v2 deployments (e.g. Azure regional endpoints) only expose the
    scopeless path: /api/2.0/apikeys/token — which is also what wxo-docker-proxy
    uses. This subclass overrides OPERATION_PATH to use the scopeless variant
    and ignores the scope path parameters entirely.
    """

    OPERATION_PATH = '/api/2.0/apikeys/token'

    def request_token(self) -> dict:
        """Invoke POST /api/2.0/apikeys/token (scopeless variant)."""
        required_headers = {
            'User-Agent': self.user_agent,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        request_headers = {}
        if self.headers is not None and isinstance(self.headers, dict):
            request_headers.update(self.headers)
        request_headers.update(required_headers)

        request_url = self.url + self.OPERATION_PATH
        request_body = {'apikey': self.apikey}
        if self.caller_ext_claim is not None and isinstance(self.caller_ext_claim, dict):
            request_body['callerExtClaim'] = self.caller_ext_claim

        query_params = {
            'includeBuiltinActions': self.bool_to_string(self.include_builtin_actions),
            'includeCustomActions': self.bool_to_string(self.include_custom_actions),
            'includeRoles': self.bool_to_string(self.include_roles),
            'prefixRolesWithDefinitionScope': self.bool_to_string(self.prefix_roles),
        }

        logger.debug('Invoking scopeless MCSP v2 token service operation: %s', request_url)
        return self._request(
            method='POST',
            headers=request_headers,
            url=request_url,
            params=query_params,
            data=json.dumps(request_body),
            proxies=self.proxies,
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
    
    def _infer_auth_type(self) -> EnvironmentAuthType:
        if is_ibm_cloud_platform(self._credentials.url):
            return EnvironmentAuthType.IBM_CLOUD_IAM
        elif is_cpd_env(self._credentials.url, env_auth_type=self._credentials.auth_type):
            return EnvironmentAuthType(self._credentials.auth_type).canonical if self._credentials.auth_type else EnvironmentAuthType.CPD
        else:
            key_type = detect_mcsp_key_type(self._credentials.api_key)
            if key_type == "k2":
                return EnvironmentAuthType.MCSP_V2
            elif key_type == "k1":
                return EnvironmentAuthType.MCSP
            else:
                # Non-MCSP key (IAM key or unknown) — fall back to generic MCSP,
                # which will try v1 then v2. Explicit --type flag overrides this.
                return EnvironmentAuthType.MCSP
    
    def _get_authenticator(self, auth_type: str | EnvironmentAuthType) -> Authenticator:
        match auth_type:
            case EnvironmentAuthType.MCSP | EnvironmentAuthType.MCSP_V1:
                url = self._credentials.iam_url if self._credentials.iam_url is not None else "https://iam.platform.saas.ibm.com"
                return MCSPAuthenticator(apikey=self._credentials.api_key, url=url)
            case EnvironmentAuthType.MCSP_V2:
                url = (self._credentials.iam_url or infer_mcspv2_iam_url(self._credentials.url)).rstrip("/")
                # Use the scopeless token manager directly via BearerTokenAuthenticator.
                # The standard MCSPV2TokenManager embeds scope into the URL path
                # (/api/2.0/{type}/{id}/apikeys/token), but Azure regional MCSP v2
                # endpoints only expose the scopeless path (/api/2.0/apikeys/token).
                token_manager = _ScopelessMCSPV2TokenManager(
                    apikey=self._credentials.api_key,
                    url=url,
                    scope_collection_type="services",
                    scope_id="placeholder",
                )
                authenticator = MCSPV2Authenticator(
                    apikey=self._credentials.api_key,
                    url=url,
                    scope_collection_type="services",
                    scope_id="placeholder",
                )
                authenticator.token_manager = token_manager
                return authenticator
            case EnvironmentAuthType.IBM_CLOUD_IAM:
                return IAMAuthenticator(apikey=self._credentials.api_key, url=self._credentials.iam_url)
            case EnvironmentAuthType.CPD | EnvironmentAuthType.K8S:
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
            auth_type = EnvironmentAuthType(self._credentials.auth_type).canonical
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
