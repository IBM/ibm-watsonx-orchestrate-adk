import time
import logging
import asyncio
import asyncio
import json
import uuid
import os

from typing import Optional, TypedDict, Callable, Dict, Any, List

from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient
from ibm_watsonx_orchestrate.client.utils import is_local_dev
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.client.chat.websocket_client import WebSocketClient

logger = logging.getLogger(__name__)

class RunResponse(TypedDict, total=False):
    """Response from creating a run"""
    thread_id: str
    run_id: str
    task_id: str
    message_id: str


class RunStatus(TypedDict, total=False):
    """Status information for a run"""
    run_id: str
    status: str
    thread_id: str
    task_id: str
    message_id: str
    error: str
    log_id: str


class RunClient(BaseWXOClient):
    """
    Client to handle orchestrate/runs operations for sending messages and managing runs
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_endpoint = "/orchestrate/runs" if is_local_dev(self.base_url) else "/runs"

    def create_run(
        self,
        message: str,
        agent_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        capture_logs: bool = False
    ) -> RunResponse:
        """
        Create a new run by sending a message to an agent.
        
        Args:
            message: The message content to send
            agent_id: Optional agent ID to send the message to
            thread_id: Optional thread ID to continue a conversation
            capture_logs: Whether to capture logs for this run
            
        Returns:
            Response containing thread_id, run_id, task_id, and message_id
        """
        payload = {
            "message": {
                "role": "user",
                "content": message
            },
            "capture_logs": capture_logs
        }

        if agent_id:
            payload["agent_id"] = agent_id
        
        if thread_id:
            payload["thread_id"] = thread_id
        
        return self._post(f"{self.base_endpoint}", data=payload)


    def upload_file_to_s3(
        self,
        file_path: str,
        text: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Upload a file to S3 storage for use in agent interactions.
        
        Args:
            file_path: Path to the file to upload
            text: Optional text message to send with the file
            
        Returns:
            List of file metadata dictionaries with upload URLs
            
        Example response:
            [
                {
                    "fileName": "document.pdf",
                    "id": null,
                    "url": "http://minio:9000/bucket/path/document.pdf?...",
                    "errorBody": null,
                    "errorSubject": null,
                    "statusCode": 200,
                    "invalid": false
                }
            ]
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        filename = os.path.basename(file_path)
        file_id = str(uuid.uuid4())
        
        # Prepare file metadata
        file_metadata = [{
            "fileName": filename,
            "invalid": False,
            "id": file_id,
            "statusCode": 200,
            "uploadStatus": "uploading",
            "url": ""
        }]
        
        # Prepare multipart form data
        with safe_open(file_path, "rb") as f:
            files = {
                "files": (filename, f, "application/octet-stream")
            }
            
            data = {
                "text": text,
                "fileMetaData": json.dumps(file_metadata)
            }
            
            # Upload to S3 endpoint and get the response
            endpoint = "/orchestrate/upload-to-s3/" if is_local_dev(self.base_url) else "/upload-to-s3/"
            response = self._post(endpoint, data=data, files=files)
            
        return response if isinstance(response, list) else [response]


    def create_run_with_files(
        self,
        message: str,
        file_urls: List[Dict[str, Any]],
        agent_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        capture_logs: bool = False
    ) -> RunResponse:
        """
        Create a new run with file attachments.
        
        Args:
            message: The message content to send (can be empty for file-only uploads)
            file_urls: List of file metadata from upload_file_to_s3
            agent_id: Optional agent ID to send the message to
            thread_id: Optional thread ID to continue a conversation
            capture_logs: Whether to capture logs for this run
            
        Returns:
            Response containing thread_id, run_id, task_id, and message_id
        """
        # Build context data with files
        # If message is empty, send empty content (for file-only uploads like file_upload_agent)
        # If message has text, include it (for agents like document_processing that need instructions)
        context_data = []
        
        # Add text data only if message is provided
        if message and message.strip():
            context_data.append({
                "id": str(uuid.uuid4()),
                "response_type": "text",
                "text": message
            })
        
        # Always add file data
        context_data.append({
            "id": str(uuid.uuid4()),
            "files": file_urls,
            "response_type": "file_download"
        })
        
        payload = {
            "message": {
                "role": "user",
                "content": message if message and message.strip() else ""
            },
            "context": {
                "data": context_data,
                "source": "TOOL"
            },
            "additional_properties": {},
            "capture_logs": capture_logs
        }

        if agent_id:
            payload["agent_id"] = agent_id
        
        if thread_id:
            payload["thread_id"] = thread_id
        
        return self._post(f"{self.base_endpoint}", data=payload)


    def get_run_status(self, run_id: str) -> RunStatus:
        """
        Get the status of a run.
        
        Args:
            run_id: The ID of the run to check
            
        Returns:
            Run status information
        """
        return self._get(f"{self.base_endpoint}/{run_id}")
        
    def wait_for_run_completion(
        self,
        run_id: str,
        poll_interval: int = 2,
        max_retries: Optional[int] = None
    ) -> RunStatus:
        """
        Poll for run completion and return the final status.
        
        Args:
            run_id: The ID of the run to wait for
            poll_interval: Seconds between polling attempts
            max_retries: Maximum number of polling attempts (None for unlimited, will poll until completion or Ctrl+C)
            
        Returns:
            Final run status
            
        Raises:
            KeyboardInterrupt: If user presses Ctrl+C
        """
        attempt = 0
        while True:
            try:
                status = self.get_run_status(run_id)
                
                # Check if run is complete
                run_state = status.get("status", "").lower()
                if run_state in {"completed", "failed", "cancelled"}:
                    return status
                
                time.sleep(poll_interval)
                attempt += 1
                
                if max_retries is not None and attempt >= max_retries:
                    raise TimeoutError(f"Run {run_id} did not complete within {max_retries * poll_interval} seconds")
                    
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.warning(f"Error polling run status (attempt {attempt + 1}): {e}")
                if max_retries is not None and attempt >= max_retries - 1:
                    raise
                time.sleep(poll_interval)

    async def stream_run_with_websocket(
        self,
        agent_id: str,
        thread_id: str,
        run_id: str,
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_intermediate: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_complete: Optional[Callable[[RunStatus], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ) -> RunStatus:
        """
        Stream run updates via WebSocket for real-time message delivery.
        
        NOTE: This method expects run_id to be empty string initially.
        It will create the run after establishing WebSocket connection.
        
        Args:
            agent_id: Agent identifier
            thread_id: Thread identifier (can be empty for new thread)
            run_id: Should be empty string - run will be created after connecting
            on_message: Callback for message events (message.created, message.delta)
            on_intermediate: Callback for intermediate/thinking events (run.step.intermediate)
            on_complete: Callback when run completes
            on_error: Callback for error events
            
        Returns:
            Final run status
            
        Raises:
            RuntimeError: If websockets package is not installed
        """
        
        ws_client = WebSocketClient(
            base_url=self.base_url.replace('/v1/orchestrate', '').replace('/v1', ''),
            api_key=self.api_key,
            authenticator=self.authenticator,
            verify=self.verify
        )
        
        final_status = None
        run_completed = False
        listen_task = None
        actual_run_id = run_id  # Will be set after creating run
        
        def handle_event(full_event: Dict[str, Any]):
            """
            Handle WebSocket events.
            
            Event structure:
            {
                "id": "...",
                "event": "run.step.intermediate",
                "data": {
                    "run_id": "...",
                    "message": {...},
                    ...
                }
            }
            """
            nonlocal final_status, run_completed
            event_type = full_event.get('event', '')
            event_data = full_event.get('data', {})
            
            # Known event types that we track
            KNOWN_EVENTS = {
                'run.started',
                'message.started',
                'message.completed',
                'run.step.delta',
                'message.delta'
            }
            
            if event_type == 'run.step.intermediate': # Intermediate thinking/progress messages
                if on_intermediate:
                    on_intermediate(full_event)
            
            elif event_type == 'slot.input': # Flow output messages
                if on_intermediate:
                    on_intermediate(full_event)
            
            elif event_type == 'message.created': # Includes final messages
                if on_message:
                    on_message(full_event)
            
            elif event_type == 'run.completed':
                final_status = event_data
                run_completed = True
                if on_complete:
                    on_complete(full_event)
            
            elif event_type == 'done':
                run_completed = True
            
            elif event_type == 'run.failed':
                final_status = event_data
                run_completed = True
                error_msg = final_status.get('error', 'Unknown error')
                if on_error:
                    on_error(error_msg)
            
            elif event_type not in KNOWN_EVENTS: # Warn about truly unknown event types
                logger.warning(f"Unhandled event type: {event_type}")
        
        # Register handlers for all event types
        ws_client.register_handler('run.started', handle_event)
        ws_client.register_handler('message.started', handle_event)
        ws_client.register_handler('run.step.intermediate', handle_event)
        ws_client.register_handler('run.step.delta', handle_event)
        ws_client.register_handler('message.delta', handle_event)
        ws_client.register_handler('message.created', handle_event)
        ws_client.register_handler('message.completed', handle_event)
        ws_client.register_handler('run.completed', handle_event)
        ws_client.register_handler('done', handle_event)
        ws_client.register_handler('run.failed', handle_event)
        ws_client.register_handler('slot.input', handle_event)  # Flow output messages
        
        try:
            # Step 1: Connect to WebSocket
            await ws_client.connect(agent_id, thread_id or "", run_id)
            
            # Step 2: Start listening in background
            listen_task = asyncio.create_task(ws_client.listen())
            
            # Step 3: Give listen() a moment to start
            await asyncio.sleep(0.1)
            
            # Step 4: Add actual_run_id based on the one listened from chat_controller
            actual_run_id = run_id
            
            # Step 5: Wait for run completion
            max_wait = 300  # 5 minutes timeout
            wait_interval = 0.1
            elapsed = 0
            
            while not run_completed and elapsed < max_wait:
                await asyncio.sleep(wait_interval)
                elapsed += wait_interval
                
                # Check if listen task failed
                if listen_task.done():
                    try:
                        listen_task.result()
                    except Exception as e:
                        logger.error(f"Listen task failed: {e}")
                        break
            
            if not run_completed:
                logger.warning(f"Run did not complete within {max_wait} seconds")
            
        except Exception as e:
            logger.error(f"WebSocket streaming error: {e}")
            raise
        finally: # Cancel listen task if still running
            if listen_task and not listen_task.done():
                listen_task.cancel()
                try:
                    await listen_task
                except asyncio.CancelledError:
                    pass
            
            await ws_client.disconnect()
        
        if not final_status and actual_run_id:
            logger.warning("WebSocket closed without final status, falling back to HTTP polling")
            final_status = self.get_run_status(actual_run_id)
        
        return final_status
    

    # Required abstract methods from BaseAPIClient
    def create(self, *args, **kwargs):
        return self.create_run(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.get_run_status(*args, **kwargs)

    def update(self, *args, **kwargs):
        raise NotImplementedError("Update not supported for orchestrate runs")

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Delete not supported for orchestrate runs")
