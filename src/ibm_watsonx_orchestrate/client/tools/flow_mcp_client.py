from typing import Any, Optional, Dict
import asyncio
from urllib.parse import urlparse
from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient
from ibm_cloud_sdk_core.authenticators import Authenticator

try:
    from mcp import ClientSession  # type: ignore[import-not-found]
    from mcp.client.streamable_http import streamable_http_client  # type: ignore[import-not-found]
    import httpx  # type: ignore[import-not-found]
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    # Provide stub types when mcp is not installed
    ClientSession = Any  # type: ignore[misc,assignment]
    streamable_http_client = Any  # type: ignore[misc,assignment]
    httpx = Any  # type: ignore[misc,assignment]


class FlowMCPClient(BaseWXOClient):
    """
    Client to handle flow operations via MCP (Model Context Protocol) server.
    
    This client connects to an MCP server running at /flows/mcp context root
    and provides methods to interact with flow models and execute flows.
    
    Unlike TempusClient which uses REST, this client uses the Python MCP SDK
    to communicate with the MCP server via SSE (Server-Sent Events) transport.
    
    Note:
        Flow MCP server only supports streamable HTTP (SSE) transport.
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        is_local: bool = False,
        verify: Optional[str] = None,
        authenticator: Optional[Authenticator] = None,
        *args,
        **kwargs
    ):
        """
        Initialize the FlowMCPClient.
        
        Args:
            base_url: Base URL of the server
            api_key: API key for authentication
            is_local: Whether this is a local deployment
            verify: SSL verification setting
            authenticator: Authenticator instance for authentication
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
            
        Note:
            Flow MCP server only supports SSE (Server-Sent Events) transport over HTTP.
            Use instantiate_client() from ibm_watsonx_orchestrate.client.utils to create
            instances with proper authentication configuration.
        """
        super().__init__(base_url=base_url, api_key=api_key, is_local=is_local, verify=verify, authenticator=authenticator, *args, **kwargs)  # type: ignore[arg-type]
        
        if not HAS_MCP:
            raise ImportError(
                "MCP SDK is not installed. Please install it with: "
                "pip install ibm-watsonx-orchestrate[mcp]"
            )
        
        # Parse URL and construct MCP endpoint
        parsed_url = urlparse(self.base_url)
        
        # Construct the MCP endpoint URL
        # For local: port 9044, context root /mcp
        # For remote: /v1/orchestrate/flows/mcp
        if self.is_local:
            # Local MCP server runs on port 9044 with context root /mcp
            self.mcp_url = f"{parsed_url.scheme}://{parsed_url.hostname}:9044/mcp"
        else:
            self.mcp_url = f"{parsed_url.scheme}://{parsed_url.netloc}/v1/orchestrate/flows/mcp"
        
        self._session: Optional[ClientSession] = None  # type: ignore[valid-type]
        self._context_manager = None
        self._http_client: Optional[httpx.AsyncClient] = None  # type: ignore[valid-type]
        
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for MCP requests.
        Uses the parent class _get_headers method.
        
        Returns:
            Dictionary of headers including authorization
        """
        return self._get_headers()
    
    async def _ensure_session(self) -> ClientSession:  # type: ignore[valid-type]
        """
        Ensure an MCP session is established.
        
        Returns:
            Active ClientSession instance
        """
        if self._session is None:
            await self._connect()
        return self._session  # type: ignore[return-value]
    
    async def _connect(self):
        """
        Establish connection to the MCP server using streamable HTTP transport.
        Flow MCP server only supports streamable HTTP.
        """
        # Create httpx.AsyncClient with authentication headers
        # Note: We create the client but pass it to streamable_http_client
        # which will manage its lifecycle
        self._http_client = httpx.AsyncClient(  # type: ignore[misc]
            headers=self._get_auth_headers(),
            timeout=30.0
        )
        
        # Use streamable HTTP client with the configured http_client
        # The streamable_http_client will NOT close the http_client if we provide one
        self._context_manager = streamable_http_client(  # type: ignore[misc,call-arg]
            self.mcp_url,
            http_client=self._http_client,
            terminate_on_close=True
        )
        
        # Enter the context manager to get read stream, write stream, and session ID callback
        read_stream, write_stream, _get_session_id = await self._context_manager.__aenter__()
        
        # Create a session using the client streams
        self._session = ClientSession(read_stream, write_stream)  # type: ignore[misc]
        await self._session.__aenter__()  # type: ignore[union-attr]
        
        # Initialize the connection
        await self._session.initialize()  # type: ignore[union-attr]
    
    async def _disconnect(self):
        """
        Close the MCP session and cleanup resources.
        """
        if self._session:
            await self._session.__aexit__(None, None, None)
            self._session = None
        
        if self._context_manager:
            await self._context_manager.__aexit__(None, None, None)
            self._context_manager = None
        
        if self._http_client:
            await self._http_client.aclose()  # type: ignore[union-attr]
            self._http_client = None
    
    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call an MCP tool with the given arguments.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Dictionary of arguments to pass to the tool
            
        Returns:
            Result from the tool execution
        """
        session = await self._ensure_session()
        result = await session.call_tool(tool_name, arguments)
        
        # Extract content from result
        if hasattr(result, 'content') and result.content:
            # Return the first content item's text if available
            if len(result.content) > 0:
                content_item = result.content[0]
                if hasattr(content_item, 'text'):
                    return content_item.text
                return content_item
        
        return result
    
    def get_mcp_endpoint(self) -> str:
        """
        Returns the MCP endpoint URL.
        
        Returns:
            The MCP endpoint URL string
        """
        return self.mcp_url
    
    async def list_tools(self) -> list:
        """
        List available tools on the MCP server.
        
        Returns:
            List of available tools
        """
        session = await self._ensure_session()
        result = await session.list_tools()
        return result.tools if hasattr(result, 'tools') else []
    
    def __enter__(self):
        """
        Context manager entry - not supported for async client.
        Use async with instead.
        """
        raise RuntimeError(
            "FlowMCPClient requires async context manager. "
            "Use 'async with' instead of 'with'."
        )
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - not supported for async client."""
        pass
    
    async def __aenter__(self):
        """
        Async context manager entry.
        
        Returns:
            Self for use in async with statement
        """
        await self._connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        await self._disconnect()
    
    # Required abstract methods from BaseAPIClient
    def create(self, *args, **kwargs):
        """Not implemented for MCP client. Use create_update_flow_model instead."""
        raise NotImplementedError("Use create_update_flow_model for creating flow models")
    
    def delete(self, *args, **kwargs):
        """Not implemented for MCP client."""
        raise NotImplementedError("Delete operation not supported via MCP client")
    
    def update(self, *args, **kwargs):
        """Not implemented for MCP client. Use create_update_flow_model instead."""
        raise NotImplementedError("Use create_update_flow_model for updating flow models")
    
    def get(self, *args, **kwargs):
        """Not implemented for MCP client. Use get_flow_model instead."""
        raise NotImplementedError("Use get_flow_model for retrieving flow models")

# Made with Bob
