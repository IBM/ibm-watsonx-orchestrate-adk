from typing_extensions import List, Optional

from ibm_watsonx_orchestrate_clients.common.base_client import BaseWXOClient, ClientAPIException
from ibm_watsonx_orchestrate_core.utils.workspaces import (
    add_workspace_query_param,
    resolve_and_inject_workspace,
    convert_workspace_id_to_name
)
from ibm_watsonx_orchestrate.cli.workspace_context import GLOBAL_WORKSPACE_ID

class ExternalAgentClient(BaseWXOClient):
    """
    Client to handle CRUD operations for External Agent endpoint
    """

    def create(self, payload: dict) -> dict:
        # Resolve workspace field and inject active workspace context
        payload = resolve_and_inject_workspace(payload)
        return self._post("/agents/external-chat", data=payload)

    def get(self, workspace_id: Optional[str] = None, include_global: bool = True) -> dict:
        params = {'include_hidden': 'true'}

        # If workspace_id is explicitly provided, use it; otherwise use active workspace context
        if workspace_id is not None:
            params['workspace_id'] = workspace_id
        else:
            params = add_workspace_query_param(params)

        if include_global:
            params["include"] = "global"

        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        agents = self._get(f"/agents/external-chat?{query_string}")
        
        # Convert workspace_id to workspace name in response
        if isinstance(agents, list):
            agents = [convert_workspace_id_to_name(agent) for agent in agents]
        else:
            agents = convert_workspace_id_to_name(agents)
        
        return agents

    def update(self, agent_id: str, data: dict, skip_workspace_injection: bool = False) -> dict:
        # Resolve workspace field and inject active workspace context
        # Skip injection for cross-workspace updates
        if not skip_workspace_injection:
            data = resolve_and_inject_workspace(data)
        return self._patch(f"/agents/external-chat/{agent_id}", data=data)

    def delete(self, agent_id: str) -> dict:
        return self._delete(f"/agents/external-chat/{agent_id}")
    
    def get_draft_by_name(self, agent_name: str, workspace_id: Optional[str] = None, include_global: bool = True) -> List[dict]:
        return self.get_drafts_by_names([agent_name], workspace_id=workspace_id, include_global=include_global)

    def get_drafts_by_names(self, agent_names: List[str], workspace_id: Optional[str] = None, include_global: bool = True) -> List[dict]:
        formatted_agent_names = [f"names={x}" for x  in agent_names]
        params = {'include_hidden': 'true'}
        
        # If workspace_id is explicitly provided, use it; otherwise use active workspace context
        if workspace_id is not None and workspace_id != GLOBAL_WORKSPACE_ID:
            params['workspace_id'] = workspace_id
        elif workspace_id is None:
            # Add workspace filtering if applicable (only when not explicitly set)
            params = add_workspace_query_param(params)
        
        if include_global:
            params["include"] = "global"
        
        # Build query string with names and other params
        query_parts = formatted_agent_names + [f"{k}={v}" for k, v in params.items()]
        return self._get(f"/agents/external-chat?{'&'.join(query_parts)}")
    
    def get_draft_by_id(self, agent_id: str, workspace_id: Optional[str] = None, include_global: bool = True) -> List[dict]:
        if agent_id is None:
            return ""
        else:
            try:
                params = {}
                
                # If workspace_id is explicitly provided, use it; otherwise use active workspace context
                if workspace_id is not None and workspace_id != GLOBAL_WORKSPACE_ID and not include_global:
                    params['workspace_id'] = workspace_id
                elif workspace_id is None and not include_global:
                    # Add workspace filtering if applicable (only when not explicitly set)
                    params = add_workspace_query_param(params)
                
                # Build query string if params exist
                if params:
                    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
                    agent = self._get(f"/agents/external-chat/{agent_id}?{query_string}")
                else:
                    agent = self._get(f"/agents/external-chat/{agent_id}")
                return agent
            except ClientAPIException as e:
                if e.response.status_code == 404 and ("not found with the given name" in e.response.text or "Assistant not found" in e.response.text):
                    return ""
                raise(e)

    def get_drafts_by_ids(self, agent_ids: List[str], workspace_id: Optional[str] = None, include_global: bool = True) -> List[dict]:
        formatted_agent_ids = [f"ids={x}" for x  in agent_ids]
        params = {'include_hidden': 'true'}
        
        # If workspace_id is explicitly provided, use it; otherwise use active workspace context
        if workspace_id is not None and workspace_id != GLOBAL_WORKSPACE_ID:
            params['workspace_id'] = workspace_id
        elif workspace_id is None:
            # Add workspace filtering if applicable (only when not explicitly set)
            params = add_workspace_query_param(params)
        
        if include_global:
            params["include"] = "global"
        
        # Build query string with ids and other params
        query_parts = formatted_agent_ids + [f"{k}={v}" for k, v in params.items()]
        return self._get(f"/agents/external-chat?{'&'.join(query_parts)}")