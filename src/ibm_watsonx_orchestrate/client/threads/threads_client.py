import time
import logging
from typing import Optional

from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient

logger = logging.getLogger(__name__)

# Polling constants for async flows
POLL_INTERVAL = 1  # seconds


class ThreadsClient(BaseWXOClient):
    """
    Client to handle read operations for Threads (chat history- trajectories) endpoints
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_endpoint = "/threads"

    def get_all_threads(self, agent_id) -> dict:
        return self._get(self.base_endpoint, params={"agent_id": agent_id})

    def get_thread_messages(self, thread_id) -> dict:
        return self._get(f"{self.base_endpoint}/{thread_id}/messages")

    def get(self) -> dict:
        return self._get(self.base_endpoint)

    def get_threads_messages(self, thread_ids: list[str]):
        """
        get the messages for a list of threads (chats) ids
        :param thread_ids:
        :param threads_client:
        :return:
        """
        all_thread_messages = []
        for thread_id in thread_ids:
            thread_messages = self.get_thread_messages(thread_id=thread_id)
            all_thread_messages.append(thread_messages)

        return all_thread_messages

    def get_logs_by_log_id(self, log_id: str) -> dict:
        """
        Retrieve captured logs by log_id.
        
        Args:
            log_id: The log ID to retrieve logs for
            
        Returns:
            Dictionary containing captured logs
        """
        return self._get(f"{self.base_endpoint}/logs/{log_id}")

    def get_logs_by_message_id(self, thread_id: str, message_id: str) -> dict:
        """
        Retrieve captured logs by thread_id and message_id.
        
        Args:
            thread_id: The thread ID
            message_id: The message ID
            
        Returns:
            Dictionary containing captured logs
        """
        return self._get(f"{self.base_endpoint}/{thread_id}/messages/{message_id}/logs")

    def poll_for_flow_completion(
        self,
        thread_id: str,
        initial_message_count: int,
        poll_interval: int = POLL_INTERVAL,
        max_retries: Optional[int] = None
    ) -> Optional[dict]:
        """
        Poll for flow completion by waiting for a new assistant message.
        
        Args:
            thread_id: The thread ID to poll
            initial_message_count: Number of messages before the flow started
            poll_interval: Seconds between polling attempts (default: 1)
            max_retries: Maximum number of polling attempts (None for unlimited, will poll until completion or Ctrl+C)
            
        Returns:
            The new assistant message dict, or None if not found
            
        Raises:
            KeyboardInterrupt: If user presses Ctrl+C
        """
        
        attempt = 0
        while True:
            try:
                thread_messages_response = self.get_thread_messages(thread_id)
                
                if isinstance(thread_messages_response, list):
                    messages = thread_messages_response
                elif isinstance(thread_messages_response, dict) and "data" in thread_messages_response:
                    messages = thread_messages_response["data"]
                else:
                    messages = []
                
                if len(messages) > initial_message_count: # Check if we have more messages than before
                    for msg in reversed(messages): # Find the newest assistant message
                        if isinstance(msg, dict) and msg.get("role") == "assistant":
                            # Check if this is not a "flow started" message
                            content = msg.get("content", "")
                            if isinstance(content, str):
                                if "flow has started" not in content.lower() and "flow instance ID" not in content:
                                    return msg
                            elif isinstance(content, list):
                                text_parts = []
                                for item in content:
                                    if isinstance(item, dict):
                                        if item.get("response_type") == "text":
                                            text_parts.append(item.get("text", ""))
                                        elif "text" in item:
                                            text_parts.append(item["text"])
                                full_text = "\n".join(text_parts)
                                if "flow has started" not in full_text.lower() and "flow instance ID" not in full_text:
                                    return msg
                            break
                
                time.sleep(poll_interval)
                attempt += 1
                if max_retries is not None and attempt >= max_retries:
                    logger.warning(f"Flow did not complete after {max_retries} polling attempts")
                    return None
                
            except KeyboardInterrupt:
                logger.info(f"Flow polling interrupted by user (Ctrl+C) after {attempt} attempts")
                raise
            except Exception as e:
                logger.warning(f"Error polling for flow completion (attempt {attempt + 1}): {e}")
                if max_retries is not None and attempt >= max_retries - 1:
                    raise
                time.sleep(poll_interval)
