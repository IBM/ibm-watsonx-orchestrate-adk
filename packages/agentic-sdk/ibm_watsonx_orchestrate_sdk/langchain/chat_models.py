"""LangChain chat model wrapper for IBM watsonx Orchestrate AI Gateway."""

from typing import Any, Dict

from ibm_watsonx_orchestrate_clients.common.client import Client
from ibm_watsonx_orchestrate_clients.common.credentials import Credentials
from ibm_watsonx_orchestrate_clients.common.utils import is_local_dev
from langchain_openai import ChatOpenAI


class ChatWxO(ChatOpenAI):
    """
    
    Routes LLM calls through the ai-gateway via wxo-server's passthrough endpoint
    for enhanced security and centralized model management. Automatically handles
    authentication and model routing with support for both service-level credentials
    (in WxO runtime) and API key-based authentication (standalone usage) with
    automatic token generation and refresh.
    
    Supported ChatOpenAI Features:
        - ✅ invoke / ainvoke - Standard chat completions
        - ✅ stream / astream - Streaming responses
        - ✅ batch / abatch - Batch processing
        - ✅ bind_tools - Tool/function calling
        - ✅ with_structured_output - Structured outputs
        - ✅ All model parameters (temperature, top_p, max_tokens, etc.)
        - ✅ Response metadata (token usage, finish_reason, etc.)
        - ✅ Logprobs support
    
    Usage in LangGraph agents (Runtime Mode):
        ```python
        from ibm_watsonx_orchestrate_sdk.langchain import ChatWxO
        from langgraph.graph.state import RunnableConfig
        
        def create_agent(config: RunnableConfig):
            llm = ChatWxO.from_config(
                config=config,
                model="virtual-model/watsonx/meta-llama/llama-3-2-90b-vision-instruct",
                temperature=0.2
            )
            # Use llm in your LangGraph agent as normal
            return llm
        ```
    
    Standalone usage with API key:
        ```python
        from ibm_watsonx_orchestrate_sdk.langchain import ChatWxO
        
        llm = ChatWxO(
            model="virtual-model/watsonx/meta-llama/llama-3-2-90b-vision-instruct",
            api_key="your-wxo-api-key",
            wxo_base_url="https://your-instance.cloud.ibm.com"
        )
        
        response = llm.invoke("Hello!")
        print(response.content)
        ```
    
    Streaming example:
        ```python
        for chunk in llm.stream("Tell me a story"):
            print(chunk.content, end="", flush=True)
        ```
    
    Tool calling example:
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
        agent_api_key: str | None = None,
        user_id: str | None = None,
        tenant_id: str | None = None,
        api_key: str | None = None,
        wxo_base_url: str | None = None,
        iam_url: str | None = None,
        auth_type: str | None = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize ChatWxO wrapper.
        
        Args:
            model: Model ID in format "virtual-model/provider/model-name"
                  Example: "virtual-model/watsonx/meta-llama/llama-3-2-90b-vision-instruct"
            agent_api_key: Service-level API key (optional)
                          - In WxO runtime: Automatically provided
                          - Standalone: Not used
            user_id: User identifier for request context (optional)
                    - In WxO runtime: Automatically provided
                    - Standalone: Not required
            tenant_id: Tenant identifier for request context (optional)
                      - In WxO runtime: Automatically provided
                      - Standalone: Not required
            api_key: WxO API key (optional for local, required for SaaS standalone)
                    - Local: Not required (uses default local credentials)
                      Note: Configure any desired LLM provider API keys in the .env file
                      used when starting the local ADK server
                    - SaaS standalone: Provide your WxO API key for automatic token management
                    - WxO Runtime: Not used (agent_api_key is used instead)
            wxo_base_url: WxO instance base URL (REQUIRED)
                         - In WxO runtime: Automatically provided
                         - Local: "http://localhost:4321" (or your local instance URL)
                         - SaaS standalone: Your WxO instance URL (e.g., "https://your-instance.cloud.ibm.com")
            iam_url: IAM authentication URL (optional)
                    - For staging/test environments: "https://iam.platform.test.saas.ibm.com"
                    - If not provided, will be auto-detected based on environment
            auth_type: Authentication type (optional)
                      - Options: "ibm_iam" (SaaS), "mcsp", "mcsp_v1", "mcsp_v2" (AWS), "cpd" (on-prem)
                      - If not provided, will be auto-detected based on environment
            **kwargs: Additional arguments passed to ChatOpenAI (temperature, max_tokens, etc.)
        
        Raises:
            ValueError: If neither agent_api_key nor api_key is provided, or if wxo_base_url is missing
        
        Note:
            - In WxO runtime: agent_api_key, user_id, and tenant_id are automatically provided
            - Standalone: Use api_key for authentication with automatic token management
        
        Example (Runtime):
            ```python
            # Credentials automatically injected by runtime
            llm = ChatWxO.from_config(config, model="virtual-model/...")
            ```
        
        Example (Local):
            ```python
            # Local development - no api_key needed
            llm = ChatWxO(
                model="virtual-model/watsonx/...",
                wxo_base_url="http://localhost:4321",
                temperature=0.7
            )
            ```
        
        Example (SaaS Standalone):
            ```python
            # SaaS - api_key required
            llm = ChatWxO(
                model="watsonx/...",
                api_key="your-api-key",
                wxo_base_url="https://your-instance.cloud.ibm.com",
                temperature=0.7
            )
            ```
        """
        if wxo_base_url is None:
            raise TypeError("ChatWxO() missing required argument: 'wxo_base_url'")
        
        if not wxo_base_url:
            raise ValueError("No URL Provided")
        
        if not wxo_base_url.startswith("https://"):
            if not is_local_dev(wxo_base_url):
                raise ValueError("Invalid URL Format. URL must start with 'https://'")
        
        if wxo_base_url[-1] == "/":
            wxo_base_url = wxo_base_url.rstrip("/")
        
        # Use local variables before super().__init__() to avoid Pydantic conflicts
        client_instance = None
        user_id_value = None
        tenant_id_value = None
        
        # Determine authentication method
        is_local = is_local_dev(wxo_base_url)
        
        if agent_api_key:
            # Runtime mode - use service-level credentials
            auth_key = agent_api_key
            user_id_value = user_id
            tenant_id_value = tenant_id
        elif api_key or is_local:
            # Standalone mode - use API key with automatic token management
            # For local dev: api_key is optional, LocalServiceInstance will use default credentials
            credentials = Credentials(
                url=wxo_base_url,
                api_key=api_key,  # Can be None for local
                iam_url=iam_url,
                auth_type=auth_type
            )
            client_instance = Client(credentials=credentials)
            # Both ServiceInstance and LocalServiceInstance set client.token during initialization
            auth_key = client_instance.token
        else:
            raise ValueError(
                "api_key is required for SaaS standalone usage. "
                "In WxO runtime: Credentials are automatically provided via agent_api_key. "
                "Local: api_key is optional and should not be provided (uses default local credentials). "
                "SaaS standalone: Pass your WxO API key as api_key parameter."
            )
        
        # Configure for ai-gateway via wxo-server passthrough endpoint
        headers = {"Authorization": f"Bearer {auth_key}"}
        if user_id_value:
            headers["X-User-ID"] = user_id_value
        if tenant_id_value:
            headers["X-Tenant-ID"] = tenant_id_value
        
        # Construct base URL - add /api prefix only for local development
        if is_local_dev(wxo_base_url):
            api_base_url = f"{wxo_base_url}/api/v1/orchestrate/gateway/model"
        else:
            # For SaaS/production, no /api prefix
            api_base_url = f"{wxo_base_url}/v1/orchestrate/gateway/model"
        
        # Initialize parent ChatOpenAI with passthrough configuration
        super().__init__(
            api_key="dummy",  # Ignored by gateway - real auth is in headers
            base_url=api_base_url,
            model=model,
            default_headers=headers,
            **kwargs
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
            - In API key mode: Automatically checks token expiry and refreshes if needed
            - In runtime mode: Returns the service-level credential (no refresh needed)
        """
        if self._client:
            # Using API key - get token from client
            # For ServiceInstance: use _get_token() for automatic refresh
            # For LocalServiceInstance: use client.token directly (no refresh needed)
            if hasattr(self._client.service_instance, '_get_token'):
                return self._client.service_instance._get_token()
            else:
                return self._client.token
        else:
            # Using service credentials - extract from headers
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
    def from_config(
        cls,
        config: Dict[str, Any],
        model: str,
        **kwargs: Any
    ) -> "ChatWxO":
        """
        Convenience method to create ChatWxO from RunnableConfig.
        
        Extracts authentication credentials and configuration from the config dictionary
        provided by LangGraph runtime. Supports both runtime mode (agent_api_key) and
        standalone mode (api_key).
        
        Args:
            config: RunnableConfig dictionary from create_agent, containing:
                   - configurable.wxo_base_url: WxO instance URL (required)
                   - configurable.api_key: WxO API key (standalone mode)
                   - configurable.agent_api_key: Service-level API key (runtime mode)
                   - configurable.user_id: User identifier (runtime mode)
                   - configurable.tenant_id: Tenant identifier (runtime mode)
            model: Model ID in format "virtual-model/provider/model-name"
            **kwargs: Additional arguments passed to ChatWxO.__init__()
        
        Returns:
            ChatWxO: Configured instance
        
        Raises:
            ValueError: If neither agent_api_key nor api_key found in config.configurable,
                       or if wxo_base_url is missing
        
        Example (Runtime):
            ```python
            def create_agent(config: RunnableConfig):
                llm = ChatWxO.from_config(
                    config=config,
                    model="virtual-model/watsonx/meta-llama/llama-3-2-90b-vision-instruct",
                    temperature=0.2,
                    max_tokens=1000
                )
                return llm
            ```
        
        Example (Standalone with config dict):
            ```python
            config = {
                "configurable": {
                    "api_key": "your-api-key",
                    "wxo_base_url": "https://your-instance.cloud.ibm.com"
                }
            }
            llm = ChatWxO.from_config(config, model="virtual-model/...")
            ```
        """
        configurable = config.get("configurable", {})
        
        agent_api_key = configurable.get("agent_api_key")
        user_id = configurable.get("user_id")
        tenant_id = configurable.get("tenant_id")
        api_key = configurable.get("api_key")
        wxo_base_url = configurable.get("wxo_base_url")
        
        if not wxo_base_url:
            raise ValueError(
                "wxo_base_url not found in config.configurable. "
                "Ensure base URL is provided in the agent configuration."
            )
        
        if not agent_api_key and not api_key:
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
            **kwargs
        )
