"""LangChain embeddings wrapper for IBM watsonx Orchestrate AI Gateway."""

from typing import Any, Dict, List, Optional

from ibm_watsonx_orchestrate_clients.common.client import Client
from ibm_watsonx_orchestrate_clients.common.credentials import Credentials
from ibm_watsonx_orchestrate_clients.common.utils import is_local_dev
from langchain_openai import OpenAIEmbeddings


class WxOEmbeddings(OpenAIEmbeddings):
    """
    IBM watsonx Orchestrate Embeddings Wrapper.
    
    Routes embedding calls through the ai-gateway via wxo-server's passthrough endpoint
    for enhanced security and centralized model management. Automatically handles
    authentication and model routing with support for both service-level credentials
    (in WxO runtime) and API key-based authentication (standalone usage) with
    automatic token generation and refresh.
    
    Supported OpenAIEmbeddings Features:
        - ✅ embed_query / aembed_query - Single text embedding
        - ✅ embed_documents / aembed_documents - Batch text embeddings
        - ✅ All model parameters (model, dimensions, chunk_size, etc.)
        - ✅ Request configuration (max_retries, request_timeout)
        - ✅ Custom headers and model_kwargs
    
    Initianlization in Runtime Mode (running in WxO):
        ```python
        from ibm_watsonx_orchestrate_sdk.langchain import WxOEmbeddings
        from langgraph.graph.state import RunnableConfig
        
        def create_agent(config: RunnableConfig):
            embeddings = WxOEmbeddings.from_config(
                config=config,
                model="openai/text-embedding-3-small"
            )
            # Use embeddings for RAG, vector stores, etc.
            return embeddings
        ```
    
    Standalone initialization with API key (SaaS):
        ```python
        from ibm_watsonx_orchestrate_sdk.langchain import WxOEmbeddings
        import os
        
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key=os.getenv("WXO_API_KEY"),
            wxo_base_url=os.getenv("WXO_BASE_URL"),
            iam_url=os.getenv("IAM_URL"),  # Optional
            auth_type=os.getenv("AUTH_TYPE")  # Optional
        )
        ```
    
    Standalone initialization (Local):
        ```python
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            wxo_base_url="http://localhost:4321"
            # api_key not required for local - uses default credentials
        )
        ```

    Usage examples:
        ```python
        # Single query
        vector = embeddings.embed_query("Hello world")
        print(f"Embedding dimension: {len(vector)}")
        
        # Multiple documents
        vectors = embeddings.embed_documents(["Hello", "World"])
        print(f"Generated {len(vectors)} embeddings")
        ```
    """

    def __init__(
        self,
        model: str,
        agent_api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        api_key: Optional[str] = None,
        wxo_base_url: Optional[str] = None,
        iam_url: Optional[str] = None,
        auth_type: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize WxOEmbeddings wrapper.
        
        Args:
            model: Model ID in format "provider/model-name" (e.g., "openai/text-embedding-3-small")
            agent_api_key: Service-level API key (optional)
                          - In WxO runtime: Automatically provided from K8s secret
            user_id: User identifier for request context (optional)
                    - In WxO runtime: Automatically provided from A2A request
            tenant_id: Tenant identifier for request context (optional)
                      - In WxO runtime: Automatically provided from A2A request
            api_key: WxO API key (optional for local, required for SaaS standalone)
                    - SaaS standalone: Provide your WxO API key for automatic token management
                    - Local: Optional - uses default credentials if not provided
            wxo_base_url: WxO instance base URL (REQUIRED)
                         - In WxO runtime: Automatically provided
                         - Standalone SaaS: Your WxO instance URL (e.g., "https://your-instance.cloud.ibm.com")
                         - Local: "http://localhost:4321"
            iam_url: IAM URL for authentication (optional, for staging/test SaaS environments)
            auth_type: Authentication type (optional, e.g., "mcsp" for AWS SaaS environments)
            **kwargs: Additional arguments passed to OpenAIEmbeddings
        
        Raises:
            ValueError: If api_key is missing for SaaS standalone, or if wxo_base_url is missing
        
        Note:
            - In WxO runtime: agent_api_key, user_id, and tenant_id are automatically provided
            - SaaS standalone: api_key is required
            - Local standalone: api_key is optional (uses default credentials)
        """
        if wxo_base_url is None:
            raise TypeError("WxOEmbeddings() missing required argument: 'wxo_base_url'")
        
        if not wxo_base_url:
            raise ValueError("No URL Provided")
        
        if not wxo_base_url.startswith("https://"):
            if not is_local_dev(wxo_base_url):
                raise ValueError("Invalid URL Format. URL must start with 'https://'")
        
        if wxo_base_url[-1] == "/":
            wxo_base_url = wxo_base_url.rstrip("/")

        # Use local variables before super().__init__() to avoid Pydantic conflicts
        client_instance = None
        user_id_value = user_id
        tenant_id_value = tenant_id

        # Check if local environment (allows operation without API key)
        is_local = is_local_dev(wxo_base_url)

        # Determine authentication method
        if agent_api_key:
            # Runtime mode - use service-level credentials
            auth_key = agent_api_key
        elif api_key or is_local:
            # Standalone mode - use API key with automatic token management
            # For local: api_key is optional (uses default credentials)
            credentials = Credentials(
                url=wxo_base_url,
                api_key=api_key,  # Can be None for local
                iam_url=iam_url,
                auth_type=auth_type,
            )
            client_instance = Client(credentials=credentials)
            # Both ServiceInstance and LocalServiceInstance set client.token during initialization
            auth_key = client_instance.token
            user_id_value = None
            tenant_id_value = None
        else:
            raise ValueError(
                "api_key is required for SaaS standalone usage. "
                "In WxO runtime: Credentials are automatically provided. "
                "For local development: api_key is optional (uses default credentials). "
                "For SaaS standalone: Pass your WxO API key as api_key parameter."
            )

        # Configure for ai-gateway via wxo-server passthrough endpoint
        headers: Dict[str, str] = {"Authorization": f"Bearer {auth_key}"}
        if user_id_value:
            headers["X-User-ID"] = user_id_value
        if tenant_id_value:
            headers["X-Tenant-ID"] = tenant_id_value
        
        # Construct base URL - add /api prefix only for local development
        if is_local:
            api_base_url = f"{wxo_base_url}/api/v1/orchestrate/gateway/model"
        else:
            # For SaaS/production, no /api prefix
            api_base_url = f"{wxo_base_url}/v1/orchestrate/gateway/model"

        super().__init__(
            api_key="dummy",  # Ignored by gateway
            base_url=api_base_url,
            model=model,
            default_headers=headers,
            check_embedding_ctx_length=False,  # Disable tokenization - gateway expects raw text
            **kwargs,
        )

        # Set instance attributes AFTER super().__init__() for Pydantic v2 compatibility
        self._wxo_base_url = wxo_base_url
        self._client = client_instance
        self._user_id = user_id_value
        self._tenant_id = tenant_id_value

    def _get_current_token(self) -> str:
        """
        Get current token, refreshing if necessary when using API key authentication.
        
        Returns:
            str: Current valid authentication token
        
        Note:
            - For ServiceInstance: Calls _get_token() for automatic token refresh
            - For LocalServiceInstance: Returns client.token directly (no refresh needed)
            - For runtime mode (agent_api_key): Extracts token from headers
        """
        if self._client:
            # Using API key - get token from client
            # For ServiceInstance: use _get_token() for automatic refresh
            # For LocalServiceInstance: use client.token directly (no refresh needed)
            if hasattr(self._client.service_instance, "_get_token"):
                return self._client.service_instance._get_token()
            else:
                return self._client.token
        else:
            # Using agent_api_key - extract from headers
            return self.default_headers.get("Authorization", "").replace("Bearer ", "")

    def embed_documents(self, texts: List[str], **kwargs: Any) -> List[List[float]]:
        """
        Embed search docs.
        
        Args:
            texts: List of texts to embed
            **kwargs: Additional arguments passed to OpenAIEmbeddings
        
        Returns:
            List of embeddings, one for each text
        """
        if self._client:
            # Refresh token in headers before making request
            current_token = self._get_current_token()
            self.default_headers["Authorization"] = f"Bearer {current_token}"
        return super().embed_documents(texts, **kwargs)

    def embed_query(self, text: str, **kwargs: Any) -> List[float]:
        """
        Embed query text.
        
        Args:
            text: Text to embed
            **kwargs: Additional arguments passed to OpenAIEmbeddings
        
        Returns:
            Embedding vector
        """
        if self._client:
            # Refresh token in headers before making request
            current_token = self._get_current_token()
            self.default_headers["Authorization"] = f"Bearer {current_token}"
        return super().embed_query(text, **kwargs)

    async def aembed_documents(self, texts: List[str], **kwargs: Any) -> List[List[float]]:
        """
        Asynchronously embed search docs.
        
        Args:
            texts: List of texts to embed
            **kwargs: Additional arguments passed to OpenAIEmbeddings
        
        Returns:
            List of embeddings, one for each text
        """
        if self._client:
            # Refresh token in headers before making request
            current_token = self._get_current_token()
            self.default_headers["Authorization"] = f"Bearer {current_token}"
        return await super().aembed_documents(texts, **kwargs)

    async def aembed_query(self, text: str, **kwargs: Any) -> List[float]:
        """
        Asynchronously embed query text.
        
        Args:
            text: Text to embed
            **kwargs: Additional arguments passed to OpenAIEmbeddings
        
        Returns:
            Embedding vector
        """
        if self._client:
            # Refresh token in headers before making request
            current_token = self._get_current_token()
            self.default_headers["Authorization"] = f"Bearer {current_token}"
        return await super().aembed_query(text, **kwargs)

    @classmethod
    def from_config(
        cls,
        config: Dict[str, Any],
        model: str,
        **kwargs: Any,
    ) -> "WxOEmbeddings":
        """
        Convenience method to create from RunnableConfig.
        
        Supports both runtime mode (agent_api_key) and standalone mode (api_key).
        
        Args:
            config: RunnableConfig dictionary from create_agent
            model: Model ID
            **kwargs: Additional arguments
        
        Returns:
            WxOEmbeddings instance
        
        Raises:
            ValueError: If neither agent_api_key nor api_key found in config.configurable,
                       or if wxo_base_url is missing
        """
        configurable = config.get("configurable", {})

        agent_api_key = configurable.get("agent_api_key")
        user_id = configurable.get("user_id")
        tenant_id = configurable.get("tenant_id")
        api_key = configurable.get("api_key")
        wxo_base_url = configurable.get("wxo_base_url")
        iam_url = configurable.get("iam_url")
        auth_type = configurable.get("auth_type")

        if not wxo_base_url:
            raise ValueError(
                "wxo_base_url not found in config.configurable. "
                "Ensure base URL is provided in the agent configuration."
            )

        # Check if local environment
        is_local = is_local_dev(wxo_base_url)

        if not agent_api_key and not api_key and not is_local:
            raise ValueError(
                "Neither agent_api_key nor api_key found in config.configurable. "
                "Ensure authentication credentials are provided in the agent configuration."
            )

        return cls(
            model=model,
            agent_api_key=agent_api_key,
            user_id=user_id,
            tenant_id=tenant_id,
            api_key=api_key,
            wxo_base_url=wxo_base_url,
            iam_url=iam_url,
            auth_type=auth_type,
            **kwargs,
        )
