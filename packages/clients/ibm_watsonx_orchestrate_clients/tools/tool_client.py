from typing import Literal, Optional

from typing_extensions import List

from ibm_watsonx_orchestrate_core.utils.file_manager import safe_open
from ibm_watsonx_orchestrate_core.utils.workspaces import (
    resolve_and_inject_workspace,
    add_workspace_query_param,
    convert_workspace_id_to_name
)
from ibm_watsonx_orchestrate_clients.common.base_client import BaseWXOClient, ClientAPIException

class ToolClient(BaseWXOClient):
    """
    Client to handle CRUD operations for Tool endpoint
    """

    def create(self, payload: dict) -> dict:
        # Resolve workspace field and inject active workspace context
        payload = resolve_and_inject_workspace(payload)
        return self._post("/tools", data=payload)

    def get(self, workspace_id: Optional[str] = None, include_global: bool = True) -> dict:
        # If workspace_id is explicitly provided, use it; otherwise use active workspace context
        params = {}
        if workspace_id is not None:
            params['workspace_id'] = workspace_id
        else:
            params = add_workspace_query_param(params)
        
        if include_global:
            params["include"] = "global"
        
        if params:
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            tools = self._get(f"/tools?{query_string}")
        else:
            tools = self._get("/tools")
        
        # Convert workspace_id to workspace name in response
        if isinstance(tools, list):
            tools = [convert_workspace_id_to_name(tool) for tool in tools]
        elif isinstance(tools, dict):
            tools = convert_workspace_id_to_name(tools)
        
        return tools

    def update(self, agent_id: str, data: dict) -> dict:
        # Resolve workspace field and inject active workspace context
        data = resolve_and_inject_workspace(data)
        return self._put(f"/tools/{agent_id}", data=data)

    def delete(self, tool_id: str) -> dict:
        return self._delete(f"/tools/{tool_id}")

    def upload_tools_artifact(self, tool_id: str, file_path: str) -> dict:
        return self._post(f"/tools/{tool_id}/upload", files={"file": (f"{tool_id}.zip", safe_open(file_path, "rb"), "application/zip", {"Expires": "0"})})

    def download_tools_artifact(self, tool_id: str) -> bytes:
        response = self._get(f"/tools/{tool_id}/download", return_raw=True)
        return response.content
    
    def download_tools_json(self, tool_id: str) -> dict:
        return self.download_tools_artifact(tool_id)

    def get_draft_by_name(self, tool_name: str, include_global: bool = True) -> List[dict]:
        return self.get_drafts_by_names([tool_name], include_global=include_global)

    def get_drafts_by_names(self, tool_names: List[str], workspace_id: Optional[str] = None, include_global: bool = True) -> List[dict]:
        formatted_tool_names = [f"names={x}" for x in tool_names]
        params = {}
        
        # If workspace_id is explicitly provided, use it; otherwise use active workspace context
        if workspace_id is not None:
            params['workspace_id'] = workspace_id
        else:
            # Add workspace filtering if applicable
            params = add_workspace_query_param(params)
        
        if include_global:
            params["include"] = "global"
        
        # Build query string with names and other params
        query_parts = formatted_tool_names + [f"{k}={v}" for k, v in params.items()]
        return self._get(f"/tools?{'&'.join(query_parts)}")
    
    def get_draft_by_id(self, tool_id: str) -> dict | Literal[""]:
        if tool_id is None:
            return ""
        else:
            try:
                tool = self._get(f"/tools/{tool_id}")
                return tool
            except ClientAPIException as e:
                if e.response.status_code == 404 and "not found with the given name" in e.response.text:
                    return ""
                raise(e)
    
    def get_drafts_by_ids(self, tool_ids: List[str], workspace_id: Optional[str] = None, include_global: bool = True) -> List[dict]:
        formatted_tool_ids = [f"ids={x}" for x in tool_ids]
        params = {}
        
        # If workspace_id is explicitly provided, use it; otherwise use active workspace context
        if workspace_id is not None:
            params['workspace_id'] = workspace_id
        else:
            # Add workspace filtering if applicable
            params = add_workspace_query_param(params)
        
        params["include"] = "global"
        
        # Build query string with ids and other params
        query_parts = formatted_tool_ids + [f"{k}={v}" for k, v in params.items()]
        return self._get(f"/tools?{'&'.join(query_parts)}")