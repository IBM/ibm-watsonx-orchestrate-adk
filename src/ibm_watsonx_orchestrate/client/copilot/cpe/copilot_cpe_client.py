from typing import Dict, Any, List
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

    def _get_headers(self) -> dict:
        return {
            "chat_id": self.chat_id
        }

    def _get_chat_model_name_or_default(self, chat_nodel_name):
        if chat_nodel_name:
            return chat_nodel_name
        return 'watsonx/meta-llama/llama-3-3-70b-instruct'

    def submit_pre_cpe_chat(self, chat_llm: str |None, user_message: str | None =None,
                            tools: Dict[str, Any] = None, collaborators: Dict[str, Any] = None, knowledge_bases: Dict[str, Any] = None, selected:bool=False) -> dict:
        payload = {
            "message": user_message,
            "tools": tools,
            "collaborators": collaborators,
            "knowledge_bases": knowledge_bases,
            "chat_id": self.chat_id,
            "chat_model_name": self._get_chat_model_name_or_default(chat_llm),
            'selected':selected
        }

        response = self._post_nd_json("/wxo-cpe/create-agent", data=payload)

        if response:
            return response[-1]

    def refine_agent_with_chats(self, instruction: str, chat_llm: str | None,
                                tools: Dict[str, Any], collaborators: Dict[str, Any], knowledge_bases: Dict[str, Any], trajectories_with_feedback: List[List[dict]], model: str | None = None) -> dict:
        """
        Refines an agent's instruction using provided chat trajectories and optional model name.
        This method sends a payload containing the agent's current instruction and a list of chat trajectories
        to the Copilot Prompt Engine (CPE) for refinement.
        Optionally, a target model name can be specified to use in the refinement process.
        Parameters:
            instruction (str): The current instruction or prompt associated with the agent.
            chat_llm(str): The name of the chat model
            tools (Dict[str, Any]) - a dictionary containing the selected tools
            collaborators (Dict[str, Any]) - a dictionary containing the selected collaborators
            knowledge_bases (Dict[str, Any]) - a dictionary containing the selected knowledge_bases
            trajectories_with_feedback (List[List[dict]]): A list of chat trajectories, where each trajectory is a list
                of message dictionaries that may include user feedback.
            model (str | None): Optional. The name of the model to use for refinement.
        Returns:
            dict: The last response from the CPE containing the refined instruction.
        """

        payload = {
            "trajectories_with_feedback":trajectories_with_feedback,
            "instruction":instruction,
            "tools": tools,
            "collaborators": collaborators,
            "knowledge_bases": knowledge_bases,
            "chat_model_name": self._get_chat_model_name_or_default(chat_llm),
        }

        if model:
            payload["target_model_name"] = model

        response = self._post_nd_json("/wxo-cpe/refine-agent-with-trajectories", data=payload)

        if response:
            return response[-1]

    def init_with_context(self, chat_llm: str | None,
                          target_model_name: str | None = None, context_data: Dict[str, Any] = None) -> dict:
        payload = {
            "context_data": context_data,
            "chat_id": self.chat_id,
            "chat_model_name": self._get_chat_model_name_or_default(chat_llm),
        }

        if target_model_name:
            payload["target_model_name"] = target_model_name

        response = self._post_nd_json("/wxo-cpe/init_cpe_from_wxo", data=payload)

        if response:
            return response[-1]


    def invoke(self, prompt: str, chat_llm: str| None,
               target_model_name: str | None = None, context_data: Dict[str, Any] = None) -> dict:
        payload = {
            "prompt": prompt,
            "context_data": context_data,
            "chat_id": self.chat_id,
            "chat_model_name": self._get_chat_model_name_or_default(chat_llm),
        }

        if target_model_name:
            payload["target_model_name"] = target_model_name

        response = self._post_nd_json("/wxo-cpe/invoke", data=payload)

        if response:
            return response[-1]
    
    def healthcheck(self):
        self._get("/version")