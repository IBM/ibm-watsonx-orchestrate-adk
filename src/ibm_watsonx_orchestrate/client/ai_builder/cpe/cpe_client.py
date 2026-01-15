from typing import Dict, Any, List
from uuid import uuid4

from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient


class CPEClient(BaseWXOClient):
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

    def submit_chat_with_agent_architect(self, chat_llm: str |None, user_message: str | None =None,
                                         available_artifacts: Dict[str, Dict[str,Any]] = None, description:str = None,
                                         agent_info: Dict[str, Any] = None, examples: List[str] = None) -> dict:
        agent_info_for_payload = agent_info
        if examples:
            # These are added only to the payload version, since we assume that agent_info should be None if the agent is not generated yet
            agent_info_for_payload = {x:y for x,y in agent_info.items()}
            agent_info_for_payload["examples"] = examples
        payload = {
            "message": user_message,
            "available_artifacts": available_artifacts,
            "chat_id": self.chat_id,
            "description": description,
            "chat_model_name": self._get_chat_model_name_or_default(chat_llm),
            "agent_info": agent_info_for_payload,
            "run_mode": "LOCAL_CLI"
        }

        response = self._post_nd_json("/wxo-cpe/chat-with-agent-architect", data=payload)

        if response:
            return response[-1]


    def submit_refine_agent_with_chats(self, instruction: str, chat_llm: str | None, tools: Dict[str, Any], collaborators: Dict[str, Any], knowledge_bases: Dict[str, Any], trajectories_with_feedback: List[List[dict]], model: str | None = None) -> dict:
        """
        Refines an agent's instruction using provided chat trajectories and optional model name.
        This method sends a payload containing the agent's current instruction and a list of chat trajectories
        to the AI Builder for refinement.
        Optionally, a target model name can be specified to use in the refinement process.
        Parameters:
            instruction (str): The current instruction or prompt associated with the agent.
            chat_llm(str): The name of the model to use for refinement
            tools (Dict[str, Any]) - a dictionary containing the selected tools
            collaborators (Dict[str, Any]) - a dictionary containing the selected collaborators
            knowledge_bases (Dict[str, Any]) - a dictionary containing the selected knowledge_bases
            trajectories_with_feedback (List[List[dict]]): A list of chat trajectories, where each trajectory is a list
                of message dictionaries that may include user feedback.
            model (str | None): Optional. target model for the agent (not yet in use)
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

    def healthcheck(self):
        self._get("/version")