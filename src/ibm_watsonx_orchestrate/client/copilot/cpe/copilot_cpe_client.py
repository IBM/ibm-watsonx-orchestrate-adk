from typing import Dict, Any
from uuid import uuid4

from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient


class CPEClient(BaseAPIClient):
    """
    Client to handle CRUD operations for Conversational Prompt Engineering Service
    """

    def __init__(self, *args, **kwargs):
        self.chat_id = str(uuid4())
        super().__init__(*args, **kwargs)
        self.base_url = kwargs.get("base_url", self.base_url)
        self.chat_model_name = 'llama-3-3-70b-instruct'

    def _get_headers(self) -> dict:
        return {
            "chat_id": self.chat_id
        }


    def submit_pre_cpe_chat(self, user_message: str | None =None, tools: Dict[str, Any] = None) -> dict:
        payload = {
            "message": user_message,
            "tools": tools,
            "chat_id": self.chat_id,
            "chat_model_name": self.chat_model_name
        }

        response = self._post_nd_json("/wxo-cpe/create-agent", data=payload)

        if response:
            return response[-1]


    def init_with_context(self, model: str | None = None, context_data: Dict[str, Any] = None) -> dict:
        payload = {
            "context_data": context_data,
            "chat_id": self.chat_id
        }

        if model:
            payload["target_model_name"] = model

        response = self._post_nd_json("/wxo-cpe/init_cpe_from_wxo", data=payload)

        if response:
            return response[-1]


    def invoke(self, prompt: str, model: str | None = None, context_data: Dict[str, Any] = None) -> dict:
        payload = {
            "prompt": prompt,
            "context_data": context_data,
            "chat_id": self.chat_id
        }

        if model:
            payload["target_model_name"] = model

        response = self._post_nd_json("/wxo-cpe/invoke", data=payload)

        if response:
            return response[-1]