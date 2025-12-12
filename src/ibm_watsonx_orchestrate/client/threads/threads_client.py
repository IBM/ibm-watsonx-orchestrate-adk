from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient


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
