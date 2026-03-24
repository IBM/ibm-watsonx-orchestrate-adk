from typing import Any, Optional, Dict
import asyncio
from urllib.parse import urlparse

from pygments.lexer import include
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
            Raw MCP tool call response. Callers should access result.structuredContent
            or result.content as needed.
        """
        session = await self._ensure_session()
        result = await session.call_tool(tool_name, arguments)
        return result
    
    async def run_flow(
        self,
        flow_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a flow synchronously and wait for completion or interruption.
        
        This method calls the MCP tool `run_flow__<flow_name>` to execute a flow
        synchronously. The flow will run until it completes, fails, or is interrupted
        (e.g., waiting for user input).
        
        Args:
            flow_name: The name of the flow to execute (without version suffix)
            arguments: Flow-specific input parameters matching the flow's input schema
            context: Optional context parameters for flow execution:
                - thread_id: The thread id of the agent initiating the tool
                - environment_id: The environment id ("draft" or "live", default: "draft")
                - channel_id: The channel id of the request channel
                - channel_capabilities: Array of channel capabilities (e.g., ['form', 'form-table', 'file'])
                - agent_id: The agent id initiating the flow
                - agent_version: The caller agent version
        
        Returns:
            Dictionary with the following structure:
            - output (optional): Flow-specific output (only present when flow completes successfully with output)
            - status (required): Status information containing:
                - instance_id: The instance ID of the flow run
                - name: The flow name
                - state: Current state ("working", "input_required", "completed", "failed")
                - created_at: Creation timestamp (ISO 8601)
                - updated_at: Last update timestamp (ISO 8601)
        
        Behavior:
            - Executes flow to completion or until interrupted (e.g., user node)
            - Always returns a wrapper object with 'status' field
            - 'output' field only included when flow completes successfully with output
            - User interventions handled via MCP elicitation automatically
            - When state is "input_required", flow is paused waiting for user intervention
            - When state is "completed" and output is present, flow succeeded with results
            - When state is "failed", represents actual execution errors
        
        Example:
            >>> async with FlowMCPClient(base_url, api_key) as client:
            ...     result = await client.run_flow(
            ...         "purchase_approval",
            ...         {"item": "Laptop", "amount": 1500},
            ...         context={"thread_id": "thread-123", "environment_id": "draft"}
            ...     )
            ...     if result["status"]["state"] == "completed":
            ...         print(f"Flow completed: {result.get('output')}")
            ...     elif result["status"]["state"] == "input_required":
            ...         print(f"Flow waiting for input: {result['status']['instance_id']}")
        """
        # Merge context into arguments if provided
        if context:
            arguments = {**arguments, "_context": context}
        
        # _call_tool already returns structured data from structuredContent
        return await self._call_tool(f"run_flow__{flow_name}", arguments)

    async def arun_flow(
        self,
        flow_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Start a flow asynchronously and return immediately with instance ID.
        
        This method calls the MCP tool `run_flow_async__<flow_name>` to start a flow
        execution in the background. It returns immediately with an instance_id that
        can be used to query the flow status later.
        
        Args:
            flow_name: The name of the flow to execute (without version suffix)
            arguments: Flow-specific input parameters matching the flow's input schema
            context: Optional context parameters for flow execution (same as run_flow)
        
        Returns:
            Dictionary containing:
            - instance_id: The instance ID of the started flow (claim-check pattern)
        
        Behavior:
            - Starts flow execution in background
            - Returns instance_id immediately
            - Flow continues executing asynchronously
            - User interventions handled via MCP elicitation
            - Client should poll using query_flow or list_flows to check status
        
        Example:
            >>> async with FlowMCPClient(base_url, api_key) as client:
            ...     result = await client.arun_flow(
            ...         "purchase_approval",
            ...         {"item": "Laptop", "amount": 1500}
            ...     )
            ...     instance_id = result["instance_id"]
            ...     # Later, query the flow status
            ...     flows = await client.list_flows(instance_id=instance_id)
        """
        # Merge context into arguments if provided
        if context:
            arguments = {**arguments, "_context": context}
        
        # _call_tool already returns structured data from structuredContent
        return await self._call_tool(f"run_flow_async__{flow_name}", arguments)
        
    async def query_flow(self, flow_name: str, instance_id: str) -> Dict[str, Any]:
        """
        Query the status and output of a specific flow instance.
        
        This method calls the MCP tool `query_flow__<flow_name>` to retrieve the current
        state and output (if completed) of a flow run.
        
        Args:
            flow_name: The name of the flow model (without version suffix)
            instance_id: The instance ID of the flow run to query
        
        Returns:
            Dictionary with the following structure:
            - output (optional): Flow-specific output (only present when flow completes successfully with output)
            - status (required): Status information containing:
                - instance_id: The instance ID of the flow run
                - name: The flow name
                - state: Current state ("working", "input_required", "completed", "failed")
                - created_at: Creation timestamp (ISO 8601)
                - updated_at: Last update timestamp (ISO 8601)
        
        Authorization:
            User must have access to the flow (only returns data for flows initiated by the requesting user)
        
        Behavior:
            - Queries database for flow instance by instance_id
            - Validates that instance belongs to the expected flow model
            - Returns current state and output (if completed)
            - Only returns data for flows initiated by the requesting user
        
        Example:
            >>> async with FlowMCPClient(base_url, api_key) as client:
            ...     # Start a flow asynchronously
            ...     result = await client.arun_flow("purchase_approval", {"item": "Laptop", "amount": 1500})
            ...     instance_id = result["instance_id"]
            ...     
            ...     # Query the flow status
            ...     status = await client.query_flow("purchase_approval", instance_id)
            ...     print(f"Flow state: {status['status']['state']}")
            ...     if status['status']['state'] == 'completed' and 'output' in status:
            ...         print(f"Flow output: {status['output']}")
        """
        if not flow_name:
            raise ValueError("flow_name is required")
        if not instance_id:
            raise ValueError("instance_id is required")
        
        arguments = {"instance_id": instance_id}
        # _call_tool already returns structured data from structuredContent
        return await self._call_tool(f"query_flow__{flow_name}", arguments)

    async def cancel_flow(self, instance_id: str) -> Any:
        """
        Interrupt and stop a running flow instance.
        
        This method calls the MCP tool `cancel_flow` to abort a flow execution.
        The flow will be stopped and its state will be updated accordingly.
        
        Args:
            instance_id: The unique instance ID of the flow run to cancel
        
        Returns:
            Success message if flow was aborted, or error message if flow not found
            or user not authorized
        
        Authorization:
            User must have access to the flow (regular users can only cancel flows
            they initiated; administrators can cancel any flow in the tenant)
        
        Raises:
            May raise exceptions if the flow is not found or user lacks authorization
        
        Example:
            >>> async with FlowMCPClient(base_url, api_key) as client:
            ...     # Start a flow
            ...     result = await client.arun_flow("purchase_approval", {"item": "Laptop", "amount": 1500})
            ...     instance_id = result["instance_id"]
            ...     
            ...     # Cancel the flow
            ...     cancel_result = await client.cancel_flow(instance_id)
            ...     print(cancel_result)
        """
        if not instance_id:
            raise ValueError("instance_id is required")
        
        arguments = {"instance_id": instance_id}
        # _call_tool already returns structured data from structuredContent
        return await self._call_tool("cancel_flow", arguments)

    async def replay_flow_pending_elicitation(self, instance_id: str) -> Dict[str, Any]:
        """
        Replay pending elicitation requests for a flow instance after reconnection.
        
        This tool returns immediately with the count of pending elicitations, then replays
        them asynchronously in the background. This non-blocking design allows the tool to
        be called multiple times safely, even if the client disconnects during replay.
        
        Args:
            instance_id: The unique instance ID of the flow run
        
        Returns:
            Dictionary containing:
            - pending_count: Number of pending elicitations found (will be replayed asynchronously)
            - message: Status message describing the result
        
        Requirements:
            - Client must be actively subscribed to the flow (use subscribe_flow first)
            - Only the subscribed session can replay elicitations
            - User must have access to the flow
        
        Behavior:
            1. Verifies client is subscribed to the flow instance
            2. Queries Redis stream for all events related to the flow
            3. Identifies ON_TASK_WAIT events without corresponding ON_TASK_RESUME or ON_TASK_CALLBACK
            4. Returns immediately with count of pending elicitations
            5. Asynchronously regenerates and sends elicitation requests for each pending task
            6. Tracks sent elicitations to prevent duplicates to the same session
            7. Client receives elicitations and can respond normally
        
        Key Features:
            - Non-Blocking: Returns immediately, doesn't wait for replay to complete
            - Idempotent: Can be called multiple times safely (deterministic elicitation IDs prevent duplicates)
            - Duplicate Prevention: Tracks which elicitations have been sent to each session
            - Resilient: If client disconnects during replay, can call again to retry
            - Background Processing: Replay happens asynchronously without blocking the caller
        
        Use Cases:
            1. After Reconnection: Client disconnected and missed elicitation requests
            2. Server Restart: Flow server restarted while flow was waiting for user input
            3. Session Recovery: Recover from network interruptions without losing flow state
            4. Retry on Failure: If client disconnects during replay, call again after reconnecting
        
        Example:
            >>> async with FlowMCPClient(base_url, api_key) as client:
            ...     # After reconnection
            ...     await client.subscribe_flow(instance_id)
            ...     result = await client.replay_flow_pending_elicitation(instance_id)
            ...     print(f"Replaying {result['pending_count']} elicitation(s)")
            ...     # Client will receive elicitations asynchronously
        
        Reconnection Workflow:
            1. Client disconnects (loses elicitation)
            2. Flow continues running, waiting at user node
            3. Client reconnects
            4. Client calls: subscribe_flow(instance_id)
            5. Client calls: replay_flow_pending_elicitation(instance_id)
            6. Client receives missed elicitation(s) asynchronously
            7. Client responds normally
            8. Flow continues execution
        """
        if not instance_id:
            raise ValueError("instance_id is required")
        
        arguments = {"instance_id": instance_id}
        # _call_tool already returns structured data from structuredContent
        return await self._call_tool("replay_flow_pending_elicitation", arguments)

    async def submit_flow_elicitation(
        self,
        instance_id: str,
        elicitation_id: str,
        response: Dict[str, Any]
    ) -> Any:
        """
        Submit an elicitation response offline when the client was disconnected during an elicitation request.
        
        When a client disconnects during an active elicitation, they can reconnect and submit
        the response later using this tool. The tool looks up the original ON_TASK_WAIT event
        from the Redis stream and posts the response to the callback queue to resume the flow.
        
        Args:
            instance_id: The unique instance ID of the flow run
            elicitation_id: The elicitation ID from the original elicitation request (this is the task_id)
            response: The elicitation response with the following structure:
                - action (required): One of "accept", "decline", or "cancel"
                - content (optional): The form data content (required for "accept" action)
        
        Returns:
            Success message with elicitation ID and action taken, or error message if:
            - Flow instance not found
            - User not authorized
            - Flow already completed or failed
            - Elicitation not found or already resolved
        
        Authorization:
            User must have access to the flow
        
        Response Handling:
            | Response Type | Action         | Behavior |
            |--------------|----------------|----------|
            | Form         | Accept         | Posts form data with form_operation: 'submit'. Flow resumes. |
            | Form         | Cancel/Decline | Posts form_operation: 'cancel' with empty form_data. Flow handles cancellation. |
            | Non-Form     | Accept         | Posts callback content items. Flow resumes. |
            | Non-Form     | Cancel/Decline | Elicitation remains open - no callback posted. Returns can_retry: true. |
        
        Key Points:
            - Form cancellations are communicated to the flow engine via form_operation: 'cancel'
            - Non-form cancellations leave the elicitation open for retry
            - The tool validates that the elicitation is still pending before submission
        
        Example:
            >>> async with FlowMCPClient(base_url, api_key) as client:
            ...     # After reconnection and replay
            ...     response = {
            ...         "action": "accept",
            ...         "content": {
            ...             "name": "user_input",
            ...             "text": '{"movie":"Inception","time":"7:00 PM"}',
            ...             "form_data": {"movie": "Inception", "time": "7:00 PM"},
            ...             "response_type": "form_operation",
            ...             "form_operation": "submit"
            ...         }
            ...     }
            ...     result = await client.submit_flow_elicitation(
            ...         instance_id="flow-abc123",
            ...         elicitation_id="task-789",
            ...         response=response
            ...     )
        
        Workflow:
            1. Client disconnects during an active elicitation
            2. Client reconnects and calls subscribe_flow(instance_id)
            3. Client calls replay_flow_pending_elicitation(instance_id)
            4. Client submits response using submit_flow_elicitation
            5. Flow resumes processing with the submitted response
        """
        if not instance_id:
            raise ValueError("instance_id is required")
        if not elicitation_id:
            raise ValueError("elicitation_id is required")
        if not response:
            raise ValueError("response is required")
        if "action" not in response:
            raise ValueError("response must contain 'action' field")
        
        # Validate action value
        valid_actions = ["accept", "decline", "cancel"]
        if response["action"] not in valid_actions:
            raise ValueError(f"Invalid action '{response['action']}'. Must be one of: {', '.join(valid_actions)}")
        
        arguments = {
            "instance_id": instance_id,
            "elicitation_id": elicitation_id,
            "response": response
        }
        # _call_tool already returns structured data from structuredContent
        return await self._call_tool("submit_flow_elicitation", arguments)


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
        
    async def list_flows(
        self,
        instance_id: Optional[str] = None,
        name: Optional[str] = None,
        include_details: bool = False,
        state: Optional[str] = None,
        max_instances: Optional[int] = None,
        updated_at_start: Optional[str] = None,
        updated_at_end: Optional[str] = None
    ) -> list:
        """
        Query and retrieve information about flow instances with flexible filtering options.
        
        Authorization:
            - Regular users see only flows they initiated
            - Administrators (TODO) will see all flows across all users in the tenant
        
        Args:
            instance_id: The unique instance ID of the flow run
            name: The unique name of the flow model
            include_details: Include detailed information about each flow instance (default: False)
            state: Filter by flow run state. Values: "working", "input_required", "completed", "failed"
            max_instances: Maximum number of instances to return (positive integer)
            updated_at_start: Filter by updated_at >= this timestamp (ISO 8601 format)
            updated_at_end: Filter by updated_at <= this timestamp (ISO 8601 format)
        
        Returns:
            List of flow instances with the following structure:
            - instance_id: Unique instance ID
            - tenant_id: Tenant ID
            - name: Flow model display name
            - model_id: Flow model ID
            - model_version: Flow model version
            - state: Current state ("working", "input_required", "completed", "failed")
            - metadata: Additional metadata (LLM model, environment ID, agent info, trace settings)
            - input: Input data for the flow run
            - output: Output data from the flow run (if completed)
            - private: Private data for the flow run
            - execution_summary: Summary of the execution
            - sequence: Execution sequence information with steps
            - initiators: List of users who started this flow run
            - error: Error message if the flow failed
            - trace_context: Distributed tracing information (traceparent, duration)
            - children: Child flow runs (if any)
            - tasks: List of tasks executed in this flow run with detailed state
            - created_at: Creation timestamp (ISO 8601)
            - updated_at: Last update timestamp (ISO 8601)
        
        Example:
            >>> async with FlowMCPClient(base_url, api_key) as client:
            ...     flows = await client.list_flows(
            ...         name="purchase_approval_flow",
            ...         state="working",
            ...         include_details=True,
            ...         max_instances=10
            ...     )
        """
        # Build arguments dictionary, only including non-None values
        arguments: Dict[str, Any] = {}
        
        if instance_id is not None:
            arguments['instance_id'] = instance_id
        if name is not None:
            arguments['name'] = name
        if include_details is not None and include_details:
            arguments['include_details'] = include_details
        if state is not None:
            # Validate state value
            valid_states = ["working", "input_required", "completed", "failed"]
            if state not in valid_states:
                raise ValueError(f"Invalid state '{state}'. Must be one of: {', '.join(valid_states)}")
            arguments['state'] = state
        if max_instances is not None:
            if not isinstance(max_instances, int) or max_instances <= 0:
                raise ValueError("max_instances must be a positive integer")
            arguments['max_instances'] = max_instances
        if updated_at_start is not None:
            arguments['updated_at_start'] = updated_at_start
        if updated_at_end is not None:
            arguments['updated_at_end'] = updated_at_end

        # Call the list_flows tool via MCP
        result = await self._call_tool("list_flows", arguments)
        
        return result
    
    
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
        raise NotImplementedError("Create operation not supported via MCP client")
    
    def delete(self, *args, **kwargs):
        """Not implemented for MCP client."""
        raise NotImplementedError("Delete operation not supported via MCP client")
    
    def update(self, *args, **kwargs):
        """Not implemented for MCP client. Use create_update_flow_model instead."""
        raise NotImplementedError("Update operation not supported via MCP client")
    
    def get(self, *args, **kwargs):
        """Not implemented for MCP client. Use get_flow_model instead."""
        raise NotImplementedError("Get operation not supported via MCP client")
