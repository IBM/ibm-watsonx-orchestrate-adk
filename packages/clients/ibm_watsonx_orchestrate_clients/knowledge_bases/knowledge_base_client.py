import json
from typing import Optional
from typing_extensions import List

from ibm_watsonx_orchestrate_clients.common.utils import is_local_dev
from ibm_watsonx_orchestrate_clients.common.base_client import BaseWXOClient
from ibm_watsonx_orchestrate_core.utils.workspaces import (
    resolve_and_inject_workspace,
    add_workspace_query_param,
    convert_workspace_id_to_name,
)

class KnowledgeBaseClient(BaseWXOClient):
    """
    Client to handle CRUD operations for Native Knowledge Base endpoint
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_endpoint = "/orchestrate/knowledge-bases" if is_local_dev(self.base_url) else "/knowledge-bases"

    def create(self, payload: dict) -> dict:
        # Parse the JSON-serialized knowledge_base data
        if 'knowledge_base' in payload:
            kb_data = json.loads(payload['knowledge_base'])
            # Resolve workspace field and inject active workspace context
            kb_data = resolve_and_inject_workspace(kb_data)
            # Re-serialize back to JSON
            payload['knowledge_base'] = json.dumps(kb_data)
        return self._post_form_data(f"{self.base_endpoint}/documents", data=payload)
    
    def create_built_in(self, payload: dict, files: list) -> dict:
        # Parse the JSON-serialized knowledge_base data
        if 'knowledge_base' in payload:
            kb_data = json.loads(payload['knowledge_base'])
            # Resolve workspace field and inject active workspace context
            kb_data = resolve_and_inject_workspace(kb_data)
            # Re-serialize back to JSON
            payload['knowledge_base'] = json.dumps(kb_data)
        return self._post_form_data(f"{self.base_endpoint}/documents", data=payload, files=files)

    def get(self, workspace_id: Optional[str] = None) -> dict:
        # If workspace_id is explicitly provided, use it; otherwise use active workspace context
        params = {}
        if workspace_id is not None:
            params['workspace_id'] = workspace_id
        else:
            params = add_workspace_query_param(params)
        
        if params:
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            kbs = self._get(f"{self.base_endpoint}?{query_string}")
        else:
            kbs = self._get(self.base_endpoint)
        
        # Convert workspace_id to workspace name in response
        if isinstance(kbs, list):
            kbs = [convert_workspace_id_to_name(kb) for kb in kbs]
        elif isinstance(kbs, dict):
            kbs = convert_workspace_id_to_name(kbs)
        
        return kbs
    
    def get_by_name(self, name: str, workspace_id: Optional[str] = None) -> List[dict]:
        kbs = self.get_by_names([name], workspace_id=workspace_id)
        return None if len(kbs) == 0 else kbs[0]
    
    def get_by_id(self, knowledge_base_id: str, workspace_id: str = None) -> dict:
        # If workspace_id is explicitly provided, use it; otherwise use active workspace context
        if workspace_id is not None:
            params = {'workspace_id': workspace_id}
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            return self._get(f"{self.base_endpoint}/{knowledge_base_id}?{query_string}")
        else:
            return self._get(f"{self.base_endpoint}/{knowledge_base_id}")

    def get_by_names(self, names: List[str], workspace_id: Optional[str] = None) -> List[dict]:
        formatted_names = [f"names={x}" for x in names]
        params = {}
        
        # If workspace_id is explicitly provided, use it; otherwise use active workspace context
        if workspace_id is not None:
            params['workspace_id'] = workspace_id
        else:
            params = add_workspace_query_param(params)
        
        # Build query string with names and other params
        query_parts = formatted_names + [f"{k}={v}" for k, v in params.items()]
        return self._get(f"{self.base_endpoint}?{'&'.join(query_parts)}")
    
    def get_by_ids(self, ids: List[str]) -> List[dict]:
        formatted_ids = [f"ids={x}" for x in ids]
        params = {}
        # Add workspace filtering if applicable
        params = add_workspace_query_param(params)
        # Build query string with ids and other params
        query_parts = formatted_ids + [f"{k}={v}" for k, v in params.items()]
        return self._get(f"{self.base_endpoint}?{'&'.join(query_parts)}")
    
    def status(self, knowledge_base_id: str) -> dict:
        return self._get(f"{self.base_endpoint}/{knowledge_base_id}/status")

    def update(self, knowledge_base_id: str, payload: dict) -> dict:
        # Parse the JSON-serialized knowledge_base data
        if 'knowledge_base' in payload:
            kb_data = json.loads(payload['knowledge_base'])
            # Resolve workspace field and inject active workspace context
            kb_data = resolve_and_inject_workspace(kb_data)
            # Re-serialize back to JSON
            payload['knowledge_base'] = json.dumps(kb_data)
        return self._patch_form_data(f"{self.base_endpoint}/{knowledge_base_id}/documents", data=payload)
    
    def update_with_documents(self, knowledge_base_id: str, payload: dict, files: list) -> dict:
        # Parse the JSON-serialized knowledge_base data
        if 'knowledge_base' in payload:
            kb_data = json.loads(payload['knowledge_base'])
            # Resolve workspace field and inject active workspace context
            kb_data = resolve_and_inject_workspace(kb_data)
            # Re-serialize back to JSON
            payload['knowledge_base'] = json.dumps(kb_data)
        return self._patch_form_data(f"{self.base_endpoint}/{knowledge_base_id}/documents", data=payload, files=files)

    def delete(self, knowledge_base_id: str,) -> dict:
        return self._delete(f"{self.base_endpoint}/{knowledge_base_id}")