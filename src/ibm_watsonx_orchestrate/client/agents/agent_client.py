from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient, ClientAPIException
from typing_extensions import List


class AgentClient(BaseAPIClient):
    """
    Client to handle CRUD operations for Native Agent endpoint
    """

    def create(self, payload: dict) -> dict:
        return self._post("/orchestrate/agents", data=payload)

    def get(self) -> dict:
        return self._get("/orchestrate/agents")

    def update(self, agent_id: str, data: dict) -> dict:
        return self._patch(f"/orchestrate/agents/{agent_id}", data=data)

    def delete(self, agent_id: str) -> dict:
        return self._delete(f"/orchestrate/agents/{agent_id}")
    
    def get_draft_by_name(self, agent_name: str) -> List[dict]:
        return self.get_drafts_by_names([agent_name])

    def get_drafts_by_names(self, agent_names: List[str]) -> List[dict]:
        formatted_agent_names = [f"names={x}" for x  in agent_names]
        return self._get(f"/orchestrate/agents?{'&'.join(formatted_agent_names)}")
    
    def get_draft_by_id(self, agent_id: str) -> List[dict]:
        if agent_id is None:
            return ""
        else:
            try:
                agent = self._get(f"/orchestrate/agents/{agent_id}")
                return agent
            except ClientAPIException as e:
                if e.response.status_code == 404 and "not found with the given name" in e.response.text:
                    return ""
                raise(e)

    
