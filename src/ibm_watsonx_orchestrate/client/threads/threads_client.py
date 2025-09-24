from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient


class ThreadsClient(BaseAPIClient):
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
