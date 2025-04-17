from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient, ClientAPIException
from typing_extensions import List
from ibm_watsonx_orchestrate.client.utils import is_local_dev


class AgentClient(BaseAPIClient):
    """
    Client to handle CRUD operations for Native Agent endpoint
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_endpoint = "/orchestrate/agents" if is_local_dev(self.base_url) else "/agents"


    def create(self, payload: dict) -> dict:
        return self._post(self.base_endpoint, data=payload)

    def get(self) -> dict:
        return self._get(self.base_endpoint)

    def update(self, agent_id: str, data: dict) -> dict:
        return self._patch(f"{self.base_endpoint}/{agent_id}", data=data)

    def delete(self, agent_id: str) -> dict:
        return self._delete(f"{self.base_endpoint}/{agent_id}")
    
    def get_draft_by_name(self, agent_name: str) -> List[dict]:
        return self.get_drafts_by_names([agent_name])

    def get_drafts_by_names(self, agent_names: List[str]) -> List[dict]:
        formatted_agent_names = [f"names={x}" for x  in agent_names]
        return self._get(f"{self.base_endpoint}?{'&'.join(formatted_agent_names)}")
    
    def get_draft_by_id(self, agent_id: str) -> List[dict]:
        if agent_id is None:
            return ""
        else:
            try:
                agent = self._get(f"{self.base_endpoint}/{agent_id}")
                return agent
            except ClientAPIException as e:
                if e.response.status_code == 404 and "not found with the given name" in e.response.text:
                    return ""
                raise(e)

    
