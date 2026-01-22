import time
import logging

from typing import Optional, TypedDict

from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient
from ibm_watsonx_orchestrate.client.utils import is_local_dev

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

    # Required abstract methods from BaseAPIClient
    def create(self, *args, **kwargs):
        return self.create_run(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.get_run_status(*args, **kwargs)

    def update(self, *args, **kwargs):
        raise NotImplementedError("Update not supported for orchestrate runs")

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Delete not supported for orchestrate runs")
