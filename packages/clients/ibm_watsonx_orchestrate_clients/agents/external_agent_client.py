from typing_extensions import List

from ibm_watsonx_orchestrate_clients.common.base_client import BaseWXOClient, ClientAPIException
from ibm_watsonx_orchestrate_core.utils.workspaces import (
    add_workspace_query_param
)

class ExternalAgentClient(BaseWXOClient):
    """
    Client to handle CRUD operations for External Agent endpoint
    """

    def create(self, payload: dict) -> dict:
        return self._post("/agents/external-chat", data=payload)

    def get(self) -> dict:
        return self._get("/agents/external-chat?include_hidden=true")

    def update(self, agent_id: str, data: dict) -> dict:
        return self._patch(f"/agents/external-chat/{agent_id}", data=data)

    def delete(self, agent_id: str) -> dict:
        return self._delete(f"/agents/external-chat/{agent_id}")
    
    def get_draft_by_name(self, agent_name: str) -> List[dict]:
        return self.get_drafts_by_names([agent_name])

    def get_drafts_by_names(self, agent_names: List[str]) -> List[dict]:
        formatted_agent_names = [f"names={x}" for x  in agent_names]
        params = {'include_hidden': 'true'}
        # Add workspace filtering if applicable
        params = add_workspace_query_param(params)
        # Build query string with names and other params
        query_parts = formatted_agent_names + [f"{k}={v}" for k, v in params.items()]
        return self._get(f"/agents/external-chat?{'&'.join(query_parts)}")
    
    def get_draft_by_id(self, agent_id: str) -> List[dict]:
        if agent_id is None:
            return ""
        else:
            try:
                agent = self._get(f"/agents/external-chat/{agent_id}")
                return agent
            except ClientAPIException as e:
                if e.response.status_code == 404 and ("not found with the given name" in e.response.text or "Assistant not found" in e.response.text):
                    return ""
                raise(e)

    def get_drafts_by_ids(self, agent_ids: List[str]) -> List[dict]:
        formatted_agent_ids = [f"ids={x}" for x  in agent_ids]
        params = {'include_hidden': 'true'}
        # Add workspace filtering if applicable
        params = add_workspace_query_param(params)
        # Build query string with ids and other params
        query_parts = formatted_agent_ids + [f"{k}={v}" for k, v in params.items()]
        return self._get(f"/agents/external-chat?{'&'.join(query_parts)}")