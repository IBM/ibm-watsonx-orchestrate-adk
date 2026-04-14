"""LangChain embeddings wrapper for IBM watsonx Orchestrate AI Gateway."""

from typing import Any, Dict, List, Optional

from ibm_cloud_sdk_core.authenticators import Authenticator
from ibm_watsonx_orchestrate_clients.common.utils import is_local_dev
from ibm_watsonx_orchestrate_sdk.client import Client
from ibm_watsonx_orchestrate_sdk.common.session import AgenticSession, ExecutionContext
from langchain_openai import OpenAIEmbeddings


class WxOEmbeddings(OpenAIEmbeddings):
    """
    IBM watsonx Orchestrate Embeddings Wrapper.
    
    Routes embedding calls through the ai-gateway via wxo-server's passthrough endpoint
    for enhanced security and centralized model management. Supports multiple
    initialization modes via the agentic-sdk Client.
    
    Supported OpenAIEmbeddings Features:
        - ✅ embed_query / aembed_query - Single text embedding
        - ✅ embed_documents / aembed_documents - Batch text embeddings
        - ✅ All model parameters (model, dimensions, chunk_size, etc.)
        - ✅ Request configuration (max_retries, request_timeout)
        - ✅ Custom headers and model_kwargs
    
    Initialization Methods:
    
    1. **from_runnable_config** (Recommended for LangGraph agents in WxO runtime):
        ```python
        from ibm_watsonx_orchestrate_sdk.langchain import WxOEmbeddings
        
        def create_agent(config: RunnableConfig):
            embeddings = WxOEmbeddings.from_runnable_config(
                config,
                model="openai/text-embedding-3-small"
            )
            return embeddings
        ```
    
    2. **from_instance_credentials** (For standalone usage with API key):
        ```python
        embeddings = WxOEmbeddings.from_instance_credentials(
            model="openai/text-embedding-3-small",
            instance_url="https://your-instance.cloud.ibm.com",
            api_key="your-api-key"
        )
        ```
    
    3. **from_execution_context** (For runs-on mode with ExecutionContext):
        ```python
        embeddings = WxOEmbeddings.from_execution_context(
            model="openai/text-embedding-3-small",
            execution_context=execution_context
        )
        ```
    
    4. **from_session** (For pre-configured AgenticSession):
        ```python
        embeddings = WxOEmbeddings.from_session(
            model="openai/text-embedding-3-small",
            session=session
        )
        ```
    
    5. **Direct initialization** (For advanced use cases):
        ```python
        embeddings = WxOEmbeddings(
            model="openai/text-embedding-3-small",
            api_key="your-api-key",
            instance_url="https://your-instance.cloud.ibm.com"
        )
        ```

    Usage Examples:
    
    Single query:
        ```python
        vector = embeddings.embed_query("Hello world")
        print(f"Embedding dimension: {len(vector)}")
        ```
    
    Multiple documents:
        ```python
        vectors = embeddings.embed_documents(["Hello", "World"])
        print(f"Generated {len(vectors)} embeddings")
        ```
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        instance_url: Optional[str] = None,
        iam_url: Optional[str] = None,
        auth_type: Optional[str] = None,
        verify: Optional[str | bool] = None,
        authenticator: Optional[Authenticator] = None,
        local: bool = False,
        *,
        execution_context: Optional[ExecutionContext | Dict[str, Any]] = None,
        session: Optional[AgenticSession] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize WxOEmbeddings wrapper.
        
        Args:
            model: Model ID in format "provider/model-name" (e.g., "openai/text-embedding-3-small")
            api_key: WxO API key (optional for local, required for SaaS standalone)
            instance_url: WxO instance base URL (required unless using execution_context or session)
            iam_url: IAM authentication URL (optional)
            auth_type: Authentication type (optional)
            verify: Certificate verification (optional)
            authenticator: IBM Cloud SDK authenticator (optional)
            local: Whether to use local mode (default: False, auto-detected from instance_url)
            execution_context: ExecutionContext for runs-on mode (optional)
            session: Pre-configured AgenticSession (optional)
            **kwargs: Additional arguments passed to OpenAIEmbeddings
        
        Raises:
            ValueError: If required parameters are missing or session has no authentication
        """
        if not local and is_local_dev(instance_url):
            local = True

        # Create Client instance using agentic-sdk
        client_instance = Client(
            api_key=api_key,
            instance_url=instance_url,
            iam_url=iam_url,
            auth_type=auth_type,
            verify=verify,
            authenticator=authenticator,
            local=local,
            execution_context=execution_context,
            session=session
        )
        
        # Get session from client
        agentic_session = client_instance.session
        
        # Extract authentication token
        if agentic_session.access_token:
            auth_key = agentic_session.access_token
        elif agentic_session.authenticator:
            # For runs-elsewhere mode, we need to get token from authenticator
            # This will be handled by the authenticator during requests
            auth_key = "placeholder"  # Will be replaced by authenticator
        else:
            raise ValueError(
                "No authentication method available in session. "
                "Session must have either access_token or authenticator."
            )
        
        # Extract identity information if available
        user_id_value = None
        tenant_id_value = None
        if agentic_session.identity:
            user_id_value = agentic_session.identity.user_id
            tenant_id_value = agentic_session.identity.tenant_id
        
        # Configure headers for ai-gateway via wxo-server passthrough endpoint
        headers: Dict[str, str] = {"Authorization": f"Bearer {auth_key}"}
        if user_id_value:
            headers["X-User-ID"] = user_id_value
        if tenant_id_value:
            headers["X-Tenant-ID"] = tenant_id_value
        
        # Construct API base URL for gateway passthrough
        # Session base_url format by mode:
        # - local: {instance_url}/api/v1 -> need to add /orchestrate
        # - runs-elsewhere: {instance_url}/v1/orchestrate
        # - runs-on: api_proxy_url (already includes path)
        api_base_url = f"{agentic_session.base_url}"
        if agentic_session.mode == "local":
            api_base_url += "/orchestrate"
        api_base_url += "/gateway/model"

        super().__init__(
            api_key="dummy",  # Ignored by gateway
            base_url=api_base_url,
            model=model,
            default_headers=headers,
            check_embedding_ctx_length=False,  # Disable tokenization - gateway expects raw text
            **kwargs,
        )

        # Set instance attributes AFTER super().__init__() for Pydantic v2 compatibility
        self._client = client_instance
        self._session = agentic_session
        self._user_id = user_id_value
        self._tenant_id = tenant_id_value

    def _get_current_token(self) -> str:
        """
        Get current token, refreshing if necessary when using authenticator.
        
        Returns:
            str: Current valid authentication token
        
        Note:
            - For runs-elsewhere mode: Token is managed by the authenticator
            - For runs-on and local modes: Token is from the session's access_token
        """
        # For runs-elsewhere mode with authenticator, get fresh token
        if self._session.authenticator:
            token = self._session.authenticator.token_manager.get_token()
            return token
        # For runs-on and local modes, use access_token from session
        elif self._session.access_token:
            return self._session.access_token
        else:
            # Fallback: extract from headers
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
    def from_instance_credentials(
        cls,
        *,
        model: str,
        api_key: str,
        instance_url: str,
        iam_url: Optional[str] = None,
        auth_type: Optional[str] = None,
        verify: Optional[bool] = None,
        authenticator: Optional[Authenticator] = None,
        **kwargs: Any,
    ) -> "WxOEmbeddings":
        """
        Create WxOEmbeddings for runs-elsewhere mode using instance credentials.
        
        This method is for standalone applications that connect to a WxO instance
        using API key authentication.
        
        Args:
            model: Model identifier (e.g., "ibm/slate-30m-english-rtrvr")
            api_key: WxO API key for authentication
            instance_url: Base URL of the WxO instance
            iam_url: IAM URL for token management
            auth_type: Authentication type
            verify: Whether to verify SSL certificates
            authenticator: Custom authenticator instance
            **kwargs: Additional arguments passed to WxOEmbeddings constructor
            
        Returns:
            WxOEmbeddings: Configured embeddings instance
            
        Example:
            ```python
            embeddings = WxOEmbeddings.from_instance_credentials(
                model="ibm/slate-30m-english-rtrvr",
                api_key="your-api-key",
                instance_url="https://your-instance.com"
            )
            ```
        """
        return cls(
            model=model,
            api_key=api_key,
            instance_url=instance_url,
            iam_url=iam_url,
            auth_type=auth_type,
            verify=verify,
            authenticator=authenticator,
            **kwargs
        )
    
    @classmethod
    def from_execution_context(
        cls,
        *,
        model: str,
        execution_context: Optional[ExecutionContext] = None,
        verify: Optional[bool] = None,
        **kwargs: Any,
    ) -> "WxOEmbeddings":
        """
        Create WxOEmbeddings for runs-on mode using execution context.
        
        This method is for agents running within the WxO runtime environment.
        The execution context is typically provided by the runtime.
        
        Args:
            model: Model identifier (e.g., "ibm/slate-30m-english-rtrvr")
            execution_context: Runtime execution context with access token and URLs
            verify: Whether to use certificate verification
            **kwargs: Additional arguments passed to WxOEmbeddings constructor
            
        Returns:
            WxOEmbeddings: Configured embeddings instance
            
        Example:
            ```python
            # In agent code running within WxO runtime
            embeddings = WxOEmbeddings.from_execution_context(
                model="ibm/slate-30m-english-rtrvr",
                execution_context=context  # Provided by runtime
            )
            ```
        """
        return cls(
            model=model,
            execution_context=execution_context,
            verify=verify,
            **kwargs
        )


    @classmethod
    def from_session(
        cls,
        *,
        model: str,
        session: AgenticSession,
        **kwargs: Any,
    ) -> "WxOEmbeddings":
        """
        Create WxOEmbeddings from a pre-configured AgenticSession.
        
        This method is useful when you already have a session object and want
        to create an embeddings instance with it.
        
        Args:
            model: Model identifier (e.g., "ibm/slate-30m-english-rtrvr")
            session: Pre-configured AgenticSession object
            **kwargs: Additional arguments passed to WxOEmbeddings constructor
            
        Returns:
            WxOEmbeddings: Configured embeddings instance
            
        Example:
            ```python
            # Using an existing session
            embeddings = WxOEmbeddings.from_session(
                model="ibm/slate-30m-english-rtrvr",
                session=my_session
            )
            ```
        """
        return cls(model=model, session=session, **kwargs)
    
    @classmethod
    def from_runnable_config(
        cls,
        *,
        model: str,
        config: Optional[Dict[str, Any]] = None,
        verify: Optional[bool] = None,
        **kwargs: Any,
    ) -> "WxOEmbeddings":
        """
        Create WxOEmbeddings from LangGraph RunnableConfig.
        
        This method extracts the execution context from LangGraph's configuration
        and creates an embeddings instance. It's designed for use within LangGraph
        agents where the config is passed through the graph execution.
        
        Args:
            model: Model identifier (e.g., "ibm/slate-30m-english-rtrvr")
            config: LangGraph RunnableConfig containing execution context
            verify: Whether to use certificate verification
            **kwargs: Additional arguments passed to WxOEmbeddings constructor
            
        Returns:
            WxOEmbeddings: Configured embeddings instance
            
        Example:
            ```python
            # In a LangGraph node function
            def my_node(state: State, config: RunnableConfig):
                embeddings = WxOEmbeddings.from_runnable_config(
                    model="ibm/slate-30m-english-rtrvr",
                    config=config
                )
                # Use embeddings...
            ```
        """
        client = Client.from_runnable_config(config, verify=verify)
        return cls(model=model, session=client.session, **kwargs)
