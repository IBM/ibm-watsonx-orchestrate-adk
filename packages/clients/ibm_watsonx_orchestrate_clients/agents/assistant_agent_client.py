from typing_extensions import List

from ibm_watsonx_orchestrate_clients.common.base_client import BaseWXOClient, ClientAPIException
from ibm_watsonx_orchestrate_core.utils.workspaces import (
    add_workspace_query_param,
    resolve_and_inject_workspace,
    convert_workspace_id_to_name
)

class AssistantAgentClient(BaseWXOClient):
    """
    Client to handle CRUD operations for Assistant Agent endpoint
    """
    def create(self, payload: dict) -> dict:
        # Resolve workspace field and inject active workspace context
        payload = resolve_and_inject_workspace(payload)
        return self._post("/assistants/watsonx", data=payload)

    def get(self) -> dict:
        params = {'include_hidden': 'true'}
        # Add workspace filtering if applicable
        params = add_workspace_query_param(params)
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        agents = self._get(f"/assistants/watsonx?{query_string}")
        
        # Convert workspace_id to workspace name in response
        if isinstance(agents, list):
            agents = [convert_workspace_id_to_name(agent) for agent in agents]
        else:
            agents = convert_workspace_id_to_name(agents)
        
        return agents

    def update(self, agent_id: str, data: dict) -> dict:
        # Resolve workspace field and inject active workspace context
        data = resolve_and_inject_workspace(data)
        return self._patch(f"/assistants/watsonx/{agent_id}", data=data)

    def delete(self, agent_id: str) -> dict:
        return self._delete(f"/assistants/watsonx/{agent_id}")
    
    def get_draft_by_name(self, agent_name: str) -> List[dict]:
        return self.get_drafts_by_names([agent_name])

    def get_drafts_by_names(self, agent_names: List[str]) -> List[dict]:
        formatted_agent_names = [f"names={x}" for x  in agent_names]
        params = {'include_hidden': 'true'}
        # Add workspace filtering if applicable
        params = add_workspace_query_param(params)
        # Build query string with names and other params
        query_parts = formatted_agent_names + [f"{k}={v}" for k, v in params.items()]
        return self._get(f"/assistants/watsonx?{'&'.join(query_parts)}")
    
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
        params = {'include_hidden': 'true'}
        # Add workspace filtering if applicable
        params = add_workspace_query_param(params)
        # Build query string with ids and other params
        query_parts = formatted_agent_ids + [f"{k}={v}" for k, v in params.items()]
        return self._get(f"/assistants/watsonx?{'&'.join(query_parts)}")