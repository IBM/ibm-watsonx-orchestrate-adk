import os
from typing import Optional
from ibm_cloud_sdk_core.authenticators import Authenticator

from ibm_watsonx_orchestrate_clients.common.credentials import Credentials
from ibm_watsonx_orchestrate_clients.common.service_instance.service_instance import ServiceInstance
from ibm_watsonx_orchestrate_clients.common.utils import is_local_dev
from ibm_watsonx_orchestrate_agentic_sdk.context.context_client import ContextClient
# from ibm_watsonx_orchestrate_agentic_sdk.memory.memory_client import MemoryClient


class _DummyClient:
    """Dummy client for ServiceInstance initialization"""
    def __init__(self, credentials: Credentials):
        self.credentials = credentials
        self.token = None


class AgenticSDK:
    """
    Main client for IBM watsonx Orchestrate Agentic SDK
    
    Supports multiple authentication modes:
    1. Local mode (JWT token): For local development servers
    2. Cloud mode (API key): Automatically detects platform and creates appropriate authenticator
    3. Explicit authenticator: For advanced use cases
    4. Environment variables: WXO_USER_TOKEN + WXO_AUTH_URL for local mode
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        instance_url: Optional[str] = None,
        verify: Optional[str] = None,
        authenticator: Optional[Authenticator] = None,
        local: bool = False
    ):
        """
        Initialize the Agentic SDK client
        
        Args:
            api_key: API key for cloud authentication, or JWT token for local authentication
            instance_url: Base URL of the watsonx instance
            verify: SSL verification setting
            authenticator: IBM Cloud SDK authenticator for advanced use cases
            local: Set to True for local development server authentication (uses JWT token)
        
        Authentication Modes:
            - Local mode (local=True): Uses api_key as JWT Bearer token directly
            - Cloud mode (local=False): Creates authenticator from api_key for platform-specific auth
              * IBM Cloud: Uses IAMAuthenticator
              * MCSP: Uses MCSPAuthenticator or MCSPV2Authenticator
              * CPD: Uses CloudPakForDataAuthenticator
            - Explicit authenticator: Pass authenticator object directly
            - Environment variables: Set WXO_USER_TOKEN and WXO_AUTH_URL (implies local=True)
        
        Raises:
            ValueError: If neither api_key nor authenticator is provided, or if instance_url is missing
        """
        use_env_auth = (api_key is None and instance_url is None and authenticator is None)
        
        if use_env_auth:
            env_token = os.environ.get("WXO_USER_TOKEN")
            env_url = os.environ.get("WXO_AUTH_URL")
            
            if env_token and env_url:
                api_key = env_token
                instance_url = env_url
                local = True  # Environment auth always uses local mode (JWT token)
            else:
                missing_vars = []
                if not env_token:
                    missing_vars.append("WXO_USER_TOKEN")
                if not env_url:
                    missing_vars.append("WXO_AUTH_URL")
                raise ValueError(
                    f"Environment variable authentication requires both WXO_USER_TOKEN and WXO_AUTH_URL. "
                    f"Missing: {', '.join(missing_vars)}"
                )
        
        if instance_url is None:
            raise ValueError("instance_url is required (provide explicitly or set WXO_AUTH_URL environment variable)")
        
        if api_key is None and authenticator is None:
            raise ValueError(
                "Either api_key or authenticator must be provided "
                "(provide explicitly or set WXO_USER_TOKEN environment variable)"
            )
        
        # Auto-detect local mode if not explicitly set
        if not local and api_key and not authenticator:
            local = is_local_dev(instance_url)
        
        self._base_url = instance_url
        self._verify = verify
        self._is_local = local
        
        # For local mode: use JWT token directly
        # For cloud mode: create authenticator from API key
        if local:
            # Local mode: JWT token passed directly as Bearer token
            self._credentials = Credentials(url=instance_url, token=api_key, verify=verify)
            self._api_key = api_key
            self._authenticator = None
        else:
            # Cloud mode: Create authenticator for platform-specific authentication
            if authenticator:
                # Explicit authenticator provided
                self._authenticator = authenticator
                self._api_key = None
                self._credentials = Credentials(url=instance_url, api_key=api_key, verify=verify)
            else:
                # Create authenticator from API key using ServiceInstance
                self._credentials = Credentials(url=instance_url, api_key=api_key, verify=verify)
                dummy_client = _DummyClient(self._credentials)
                service_instance = ServiceInstance(dummy_client)
                self._authenticator = service_instance._get_authenticator(service_instance._infer_auth_type())
                self._api_key = None
        
        self._context_client: Optional[ContextClient] = None
        # self._memory_client: Optional[MemoryClient] = None
    
    @property
    def context(self) -> ContextClient:
        """Access the Context service"""
        if self._context_client is None:
            # For local mode: pass api_key (JWT token)
            # For cloud mode: pass authenticator (None for api_key to avoid conflict)
            self._context_client = ContextClient(
                base_url=self._base_url,
                api_key=self._api_key if self._is_local else None,
                is_local=self._is_local,
                verify=self._verify,
                authenticator=self._authenticator
            )
        return self._context_client
    
    # @property
    # def memory(self) -> MemoryClient:
    #     """Access the Memory service"""
    #     if self._memory_client is None:
    #         self._memory_client = MemoryClient(
    #             base_url=self._base_url,
    #             api_key=self._api_key,
    #             is_local=self._is_local,
    #             verify=self._verify,
    #             authenticator=self._authenticator
    #         )
    #     return self._memory_client
