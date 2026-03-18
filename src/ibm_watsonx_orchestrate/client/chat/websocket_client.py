import asyncio
import json
import logging
import jwt
import websocket
import threading

from typing import Optional, Callable, Dict, Any
from urllib.parse import urlparse, urlunparse

from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient
from ibm_watsonx_orchestrate.client.utils import is_local_dev

logger = logging.getLogger(__name__)


class WebSocketClient(BaseWXOClient):
    """
    WebSocket client for real-time chat message streaming using websocket-client.
    
    This client establishes a WebSocket connection to receive async messages
    and run completion events in real-time, eliminating the need for HTTP polling.
    Uses lightweight websocket-client library.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ws_connection: Optional[websocket.WebSocketApp] = None
        self._message_handlers: Dict[str, Callable] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def get_user_id(self) -> Optional[str]:
        """Extract user ID from the JWT token.
        
        Returns:
            User ID if found, None otherwise
        """
        if not self.api_key:
            return None
        
        try:
            decoded = jwt.decode(self.api_key, options={"verify_signature": False})
            user_id = decoded.get('sub') or decoded.get('userId') or decoded.get('user_id')
            return user_id
        except Exception as e:
            logger.warning(f"Could not extract user ID from token: {e}")
            return None
    
    def get_tenant_id(self) -> Optional[str]:
        """Extract tenant ID from the JWT token.
        
        Returns:
            Tenant ID if found, None otherwise
        """
        if not self.api_key:
            return None
        
        try:
            decoded = jwt.decode(self.api_key, options={"verify_signature": False})
            tenant_id = decoded.get('woTenantId') or decoded.get('tenantId') or decoded.get('tenant_id')
            return tenant_id
        except Exception as e:
            logger.warning(f"Could not extract tenant ID from token: {e}")
            return None
        
    def _build_websocket_url(
        self,
        agent_id: str,
        thread_id: str,
        run_id: Optional[str] = None
    ) -> str:
        """
        Build WebSocket URL for Socket.IO/Engine.IO async endpoint.
        
        Args:
            agent_id: Agent identifier (not used in URL, kept for compatibility)
            thread_id: Thread identifier (not used in URL, kept for compatibility)
            run_id: Optional run identifier (not used in URL, kept for compatibility)
            
        Returns:
            WebSocket URL (wss:// or ws://) with query parameters
        """
        parsed = urlparse(self.base_url)
        
        # Extract user_id and tenant_id from JWT token
        user_id = self.get_user_id()
        tenant_id = self.get_tenant_id()
        
        if not user_id or not tenant_id:
            logger.warning(f"Missing user_id or tenant_id from token. user_id={user_id}, tenant_id={tenant_id}")
        
        # Determine WebSocket protocol and host
        if is_local_dev(self.base_url):
            ws_scheme = "ws"
            host_parts = parsed.netloc.split(':')
            ws_host = f"{host_parts[0]}:4001"
        else:
            ws_scheme = "wss"
            ws_host = parsed.netloc
        
        # Build WebSocket path for Socket.IO/Engine.IO
        ws_path = "/api/async/"
        
        # Build query parameters
        query_params = []
        if user_id:
            query_params.append(f"userId={user_id}")
        if tenant_id:
            query_params.append(f"tenantId={tenant_id}")
        query_params.append("EIO=4")  # Engine.IO version 4
        query_params.append("transport=websocket")
        
        query_string = "&".join(query_params)
        
        ws_url = urlunparse((ws_scheme, ws_host, ws_path, '', query_string, ''))
        return ws_url
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            if not isinstance(message, str):
                return
            
            # Engine.IO protocol parsing
            if len(message) < 1:
                return
            
            # Get message type
            msg_type = message[0]
            
            if msg_type == '0':
                # OPEN - send CONNECT
                ws.send('40')
                return
            
            elif msg_type == '2':
                # PING - send PONG
                ws.send('3')
                return
            
            elif msg_type == '3':
                # PONG
                return
            
            elif message.startswith('42'):
                # EVENT
                json_str = message[2:]
                parsed = json.loads(json_str)
                
                if isinstance(parsed, list) and len(parsed) >= 2:
                    event_name = parsed[0]
                    event_data = parsed[1]
                    
                    if isinstance(event_data, dict):
                        event_type = event_data.get('event', 'unknown')
                        
                        # Call registered handler
                        if event_type in self._message_handlers:
                            handler = self._message_handlers[event_type]
                            if asyncio.iscoroutinefunction(handler):
                                # Schedule coroutine in the event loop
                                if self._loop:
                                    asyncio.run_coroutine_threadsafe(handler(event_data), self._loop)
                            else:
                                handler(event_data)
            
            elif message.startswith('40'):
                # CONNECT
                return
            
            elif message.startswith('41'):
                # DISCONNECT
                self._running = False
                return
            
            else:
                logger.warning(f"Received unknown Engine.IO message: {message[:50]}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Non-JSON message received: {message}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}", exc_info=True)
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors."""
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        self._running = False
    
    def _on_open(self, ws):
        """Handle WebSocket open."""
        logger.info("WebSocket connection established")
        self._running = True
    
    async def connect(
        self,
        agent_id: str,
        thread_id: str,
        run_id: Optional[str] = None
    ) -> None:
        """
        Establish WebSocket connection.
        
        Args:
            agent_id: Agent identifier
            thread_id: Thread identifier
            run_id: Optional run identifier
        """
        ws_url = self._build_websocket_url(agent_id, thread_id, run_id)
        
        # Get headers for authentication
        headers = self._get_headers()
        header_list = [f"{k}: {v}" for k, v in headers.items()]
        
        try:
            # Store the current event loop
            self._loop = asyncio.get_event_loop()
            
            # Create WebSocket connection
            self.ws_connection = websocket.WebSocketApp(
                ws_url,
                header=header_list,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            # Run WebSocket in a separate thread
            self._thread = threading.Thread(
                target=self.ws_connection.run_forever,
                kwargs={'ping_interval': 20, 'ping_timeout': 10}
            )
            self._thread.daemon = True
            self._thread.start()
            
            # Wait for connection to establish
            for _ in range(50):  # Wait up to 5 seconds
                if self._running:
                    break
                await asyncio.sleep(0.1)
            
            if not self._running:
                raise RuntimeError("WebSocket connection failed to establish")
                
        except Exception as e:
            logger.warning(f"WebSocket connection failed: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        self._running = False
        if self.ws_connection:
            try:
                self.ws_connection.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
            finally:
                self.ws_connection = None
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None
        
        self._loop = None
    
    def register_handler(self, event_type: str, handler: Callable) -> None:
        """
        Register a handler for specific event types.
        
        Args:
            event_type: Type of event (e.g., 'message.created', 'run.completed')
            handler: Callback function to handle the event
        """
        self._message_handlers[event_type] = handler
    
    async def listen(self) -> None:
        """
        Listen for WebSocket messages.
        
        The actual listening is done in the background thread.
        This method just waits while the connection is active.
        """
        if not self.ws_connection:
            raise RuntimeError("WebSocket not connected. Call connect() first.")
        
        try:
            # Wait while connection is active
            while self._running:
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"WebSocket listen error: {e}", exc_info=True)
            raise
    
    async def send_message(self, message: Dict[str, Any]) -> None:
        """
        Send a message through the WebSocket.
        
        Args:
            message: Message data to send (will be JSON serialized)
        """
        if not self.ws_connection or not self._running:
            raise RuntimeError("WebSocket not connected. Call connect() first.")
        
        try:
            self.ws_connection.send(json.dumps(message))
            logger.debug(f"Sent WebSocket message: {message.get('type', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            raise
    
    # Required abstract methods from BaseAPIClient
    def create(self, *args, **kwargs):
        raise NotImplementedError("Use async connect() method for WebSocket")
    
    def get(self, *args, **kwargs):
        raise NotImplementedError("Use async listen() method for WebSocket")
    
    def update(self, *args, **kwargs):
        raise NotImplementedError("Update not supported for WebSocket")
    
    def delete(self, *args, **kwargs):
        raise NotImplementedError("Use async disconnect() method for WebSocket")
