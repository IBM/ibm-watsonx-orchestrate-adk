from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient, ClientAPIException
from typing_extensions import List


class AssistantAgentClient(BaseAPIClient):
    """
    Client to handle CRUD operations for Assistant Agent endpoint
    """
    def create(self, payload: dict) -> dict:
        return self._post("/assistants/watsonx", data=payload)

    def get(self) -> dict:
        return self._get("/assistants/watsonx?include_hidden=true")

    def update(self, agent_id: str, data: dict) -> dict:
        return self._patch(f"/assistants/watsonx/{agent_id}", data=data)

    def delete(self, agent_id: str) -> dict:
        return self._delete(f"/assistants/watsonx/{agent_id}")
    
    def get_draft_by_name(self, agent_name: str) -> List[dict]:
        return self.get_drafts_by_names([agent_name])

    def get_drafts_by_names(self, agent_names: List[str]) -> List[dict]:
        formatted_agent_names = [f"names={x}" for x  in agent_names]
        return self._get(f"/assistants/watsonx?{'&'.join(formatted_agent_names)}&include_hidden=true")
    
    def get_draft_by_id(self, agent_id: str) -> dict | str:
        if agent_id is None:
            return ""
        else:
            try:
                agent = self._get(f"/assistants/watsonx/{agent_id}")
                return agent
            except ClientAPIException as e:
                if e.response.status_code == 404 and "Assistant not found" in e.response.text:
                    return ""
                raise(e)
    
    def get_drafts_by_ids(self, agent_ids: List[str]) -> List[dict]:
        formatted_agent_ids = [f"ids={x}" for x  in agent_ids]
        return self._get(f"/assistants/watsonx?{'&'.join(formatted_agent_ids)}&include_hidden=true")
