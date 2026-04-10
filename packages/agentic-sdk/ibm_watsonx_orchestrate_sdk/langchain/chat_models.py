"""LangChain chat model wrapper for IBM watsonx Orchestrate AI Gateway."""

from typing import Any, Dict, Optional

from ibm_cloud_sdk_core.authenticators import Authenticator
from ibm_watsonx_orchestrate_clients.common.utils import is_local_dev
from ibm_watsonx_orchestrate_sdk.client import Client
from ibm_watsonx_orchestrate_sdk.common.session import AgenticSession, ExecutionContext
from langchain_openai import ChatOpenAI


class ChatWxO(ChatOpenAI):
    """
    IBM watsonx Orchestrate Chat Model Wrapper.
    
    Routes LLM calls through the ai-gateway via wxo-server's passthrough endpoint
    for enhanced security and centralized model management. Supports multiple
    initialization modes via the agentic-sdk Client.
    
    Supported ChatOpenAI Features:
        - ✅ invoke / ainvoke - Standard chat completions
        - ✅ stream / astream - Streaming responses
        - ✅ batch / abatch - Batch processing
        - ✅ bind_tools - Tool/function calling
        - ✅ with_structured_output - Structured outputs
        - ✅ All model parameters (temperature, top_p, max_tokens, etc.)
        - ✅ Response metadata (token usage, finish_reason, etc.)
        - ✅ Logprobs support
    
    Initialization Methods:
    
    1. **from_runnable_config** (Recommended for LangGraph agents in WxO runtime):
        ```python
        from ibm_watsonx_orchestrate_sdk.langchain import ChatWxO
        
        def create_agent(config: RunnableConfig):
            llm = ChatWxO.from_runnable_config(
                config,
                model="watsonx/meta-llama/llama-3-2-90b-vision-instruct",
                temperature=0.2
            )
            return llm
        ```
    
    2. **from_instance_credentials** (For standalone usage with API key):
        ```python
        llm = ChatWxO.from_instance_credentials(
            model="virtual-model/watsonx/...",
            instance_url="https://your-instance.cloud.ibm.com",
            api_key="your-api-key",
            temperature=0.7
        )
        ```
    
    3. **from_execution_context** (For runs-on mode with ExecutionContext):
        ```python
        llm = ChatWxO.from_execution_context(
            model="virtual-model/...",
            execution_context=execution_context,
            temperature=0.7
        )
        ```
    
    4. **from_session** (For pre-configured AgenticSession):
        ```python
        llm = ChatWxO.from_session(
            model="virtual-model/...",
            session=session,
            temperature=0.7
        )
        ```
    
    5. **Direct initialization** (For advanced use cases):
        ```python
        llm = ChatWxO(
            model="virtual-model/...",
            api_key="your-api-key",
            instance_url="https://your-instance.cloud.ibm.com",
            temperature=0.7
        )
        ```
    
    Usage Examples:
    
    Streaming:
        ```python
        for chunk in llm.stream("Tell me a story"):
            print(chunk.content, end="", flush=True)
        ```
    
    Tool calling:
        ```python
        from pydantic import BaseModel, Field
        
        class GetWeather(BaseModel):
            '''Get weather for a location'''
            location: str = Field(description="City and state")
        
        llm_with_tools = llm.bind_tools([GetWeather])
        response = llm_with_tools.invoke("What's the weather in NYC?")
        print(response.tool_calls)
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
        **kwargs: Any
    ) -> None:
        """
        Initialize ChatWxO wrapper.
        
        Args:
            model: Model ID in format "virtual-model/provider/model-name"
                  Example: "virtual-model/watsonx/meta-llama/llama-3-2-90b-vision-instruct"
            api_key: WxO API key (optional for local, required for SaaS standalone)
                    - Local: Not required (uses default local credentials)
                    - SaaS standalone: Provide your WxO API key for automatic token management
            instance_url: WxO instance base URL (required unless using execution_context or session)
                         - Local: "http://localhost:4321" (or your local instance URL)
                         - SaaS standalone: Your WxO instance URL (e.g., "https://your-instance.cloud.ibm.com")
            iam_url: IAM authentication URL (optional)
                    - For staging/test environments: "https://iam.platform.test.saas.ibm.com"
                    - If not provided, will be auto-detected based on environment
            auth_type: Authentication type (optional)
                      - Options: "ibm_iam" (SaaS), "mcsp", "mcsp_v1", "mcsp_v2" (AWS), "cpd" (on-prem)
                      - If not provided, will be auto-detected based on environment
            verify: Certificate verification (optional)
            authenticator: IBM Cloud SDK authenticator (optional)
            local: Whether to use local mode (default: False, auto-detected from instance_url)
            execution_context: ExecutionContext for runs-on mode (optional)
            session: Pre-configured AgenticSession (optional)
            **kwargs: Additional arguments passed to ChatOpenAI (temperature, max_tokens, etc.)
        
        Raises:
            ValueError: If required parameters are missing or session has no authentication
        
        Example (Local):
            ```python
            llm = ChatWxO(
                model="virtual-model/watsonx/...",
                instance_url="http://localhost:4321",
                temperature=0.7
            )
            ```
        
        Example (SaaS Standalone):
            ```python
            llm = ChatWxO(
                model="watsonx/...",
                api_key="your-api-key",
                instance_url="https://your-instance.cloud.ibm.com",
                temperature=0.7
            )
            ```
        
        Example (Runtime with ExecutionContext):
            ```python
            llm = ChatWxO(
                model="virtual-model/...",
                execution_context=execution_context
            )
            ```
        """
        if not local and is_local_dev(instance_url):
            local = True

        # Create Client instance using agentic-sdk
        client_instance = Client(
            api_key=api_key,
            instance_url=instance_url,
            # iam_url=iam_url,
            # auth_type=auth_type,
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
        headers = {"Authorization": f"Bearer {auth_key}"}
        if user_id_value:
            headers["X-User-ID"] = user_id_value
        if tenant_id_value:
            headers["X-Tenant-ID"] = tenant_id_value
        
        # Construct API base URL for gateway passthrough
        # Session base_url already includes  prefix /api/v1 for local, /v1/orchestrate for others
        api_base_url = f"{agentic_session.base_url}"
        if local:
            api_base_url += "/orchestrate"
        api_base_url += "/gateway/model"
        
        # Initialize parent ChatOpenAI with passthrough configuration
        super().__init__(
            api_key="dummy",  # Ignored by gateway - real auth is in headers
            base_url=api_base_url,
            model=model,
            default_headers=headers,
            **kwargs
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
    
    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        """
        Invoke the chat model with automatic token refresh.
        
        Overrides the parent invoke() to refresh authentication token before making
        the request when using API key authentication. This ensures long-running
        agents don't fail due to expired tokens.
        
        Args:
            *args: Positional arguments passed to ChatOpenAI.invoke()
            **kwargs: Keyword arguments passed to ChatOpenAI.invoke()
        
        Returns:
            AIMessage: Response from the model
        
        Example:
            ```python
            response = llm.invoke("What is the capital of France?")
            print(response.content)  # "The capital of France is Paris."
            ```
        """
        if self._client:
            # Refresh token in headers before making request
            current_token = self._get_current_token()
            self.default_headers["Authorization"] = f"Bearer {current_token}"
        return super().invoke(*args, **kwargs)
    
    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        """
        Async invoke the chat model with automatic token refresh.
        
        Overrides the parent ainvoke() to refresh authentication token before making
        the async request when using API key authentication.
        
        Args:
            *args: Positional arguments passed to ChatOpenAI.ainvoke()
            **kwargs: Keyword arguments passed to ChatOpenAI.ainvoke()
        
        Returns:
            AIMessage: Response from the model
        
        Example:
            ```python
            response = await llm.ainvoke("What is the capital of France?")
            print(response.content)
            ```
        """
        if self._client:
            # Refresh token in headers before making request
            current_token = self._get_current_token()
            self.default_headers["Authorization"] = f"Bearer {current_token}"
        return await super().ainvoke(*args, **kwargs)
    
    @classmethod
    def from_instance_credentials(
        cls,
        *,
        model: str,
        instance_url: str,
        api_key: str,
        iam_url: Optional[str] = None,
        auth_type: Optional[str] = None,
        verify: Optional[str | bool] = None,
        authenticator: Optional[Authenticator] = None,
        **kwargs: Any
    ) -> "ChatWxO":
        """
        Create ChatWxO from instance credentials (runs-elsewhere mode).
        
        Args:
            model: Model ID in format "virtual-model/provider/model-name"
            instance_url: WxO instance URL
            api_key: WxO API key
            iam_url: IAM authentication URL (optional)
            auth_type: Authentication type (optional)
            verify: Certificate verification (optional)
            authenticator: IBM Cloud SDK authenticator (optional)
            **kwargs: Additional arguments passed to ChatOpenAI
        
        Returns:
            ChatWxO: Configured instance
        
        Example:
            ```python
            llm = ChatWxO.from_instance_credentials(
                model="virtual-model/watsonx/...",
                instance_url="https://your-instance.cloud.ibm.com",
                api_key="your-api-key",
                temperature=0.7
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
        execution_context: ExecutionContext | Dict[str, Any],
        verify: Optional[str | bool] = None,
        **kwargs: Any
    ) -> "ChatWxO":
        """
        Create ChatWxO from execution context (runs-on mode).
        
        Args:
            model: Model ID in format "virtual-model/provider/model-name"
            execution_context: ExecutionContext with access_token, api_proxy_url, etc.
            verify: Certificate verification (optional)
            **kwargs: Additional arguments passed to ChatOpenAI
        
        Returns:
            ChatWxO: Configured instance
        
        Example:
            ```python
            llm = ChatWxO.from_execution_context(
                model="virtual-model/...",
                execution_context=execution_context,
                temperature=0.7
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
        **kwargs: Any
    ) -> "ChatWxO":
        """
        Create ChatWxO from a pre-configured AgenticSession.
        
        Args:
            model: Model ID in format "virtual-model/provider/model-name"
            session: Pre-configured AgenticSession
            **kwargs: Additional arguments passed to ChatOpenAI
        
        Returns:
            ChatWxO: Configured instance
        
        Example:
            ```python
            session = build_local_session(
                instance_url="http://localhost:4321",
                access_token="token"
            )
            llm = ChatWxO.from_session(
                model="virtual-model/...",
                session=session,
                temperature=0.7
            )
            ```
        """
        return cls(
            model=model,
            session=session,
            **kwargs
        )
    
    @classmethod
    def from_runnable_config(
        cls,
        config: Any,
        *,
        model: str,
        verify: Optional[str | bool] = None,
        **kwargs: Any
    ) -> "ChatWxO":
        """
        Create ChatWxO from LangGraph RunnableConfig (runs-on mode).
        
        Extracts execution_context from config.configurable and creates a ChatWxO instance.
        This is the recommended way to initialize ChatWxO in LangGraph agents running
        in WxO runtime.
        
        Args:
            config: RunnableConfig from LangGraph
            model: Model ID in format "virtual-model/provider/model-name"
            verify: Certificate verification (optional)
            **kwargs: Additional arguments passed to ChatOpenAI
        
        Returns:
            ChatWxO: Configured instance
        
        Raises:
            ValueError: If execution_context is missing from config.configurable
        
        Example:
            ```python
            def create_agent(config: RunnableConfig):
                llm = ChatWxO.from_runnable_config(
                    config,
                    model="virtual-model/watsonx/meta-llama/llama-3-2-90b-vision-instruct",
                    temperature=0.2
                )
                return llm
            ```
        """
        # Use Client's from_runnable_config to create client
        client_instance = Client.from_runnable_config(config, verify=verify)
        
        return cls(
            model=model,
            session=client_instance.session,
            verify=verify,
            **kwargs
        )
