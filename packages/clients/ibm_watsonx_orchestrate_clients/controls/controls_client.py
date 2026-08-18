from typing import Optional, Dict, Any
from typing_extensions import List

from ibm_watsonx_orchestrate_clients.common.base_client import BaseWXOClient, ClientAPIException

import logging

logger = logging.getLogger(__name__)


class ControlsClient(BaseWXOClient):
    """
    Client to handle CRUD operations for Controls (Policy Bindings) endpoint.
    
    This client interacts with two main API groups:
    - /v1/policies/artifacts - Read-only policy artifact definitions
    - /v1/policies/bindings - Policy bindings (controls) that associate artifacts with agents/tools/models
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # ==================== Policy Artifacts (Read-Only) ====================

    def list_artifacts(self) -> List[Dict[str, Any]]:
        """
        List all available policy artifacts.
        
        GET /v1/policies/artifacts
        
        Returns:
            List of policy artifact dictionaries
        """
        try:
            response = self._get("/policies/artifacts")
            return response.get("artifacts", [])
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return []
            raise e

    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details of a specific policy artifact.
        
        GET /v1/policies/artifacts/{artifact_id}
        
        Args:
            artifact_id: The ID of the artifact to retrieve
            
        Returns:
            Artifact details dictionary or None if not found
        """
        try:
            return self._get(f"/policies/artifacts/{artifact_id}")
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return None
            raise e

    # ==================== Policy Bindings (Controls) ====================

    def create_binding(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new policy binding (control).
        
        POST /v1/policies/bindings
        
        Args:
            payload: Dictionary containing:
                - artifact_id (str): Required. Existing policy artifact ID
                - name (str): Conditional. Internal name; required if display_name is absent
                - display_name (str): Conditional. Display name; required if name is absent
                - description (str, optional): Binding description
                - hooks (List[str]): Required. One or more supported hooks
                - config (dict, optional): Artifact-specific configuration
                - priority (int, optional): Execution priority (default: 100)
                - agent_ids (List[str], optional): Native or external agent IDs
                - tool_ids (List[str], optional): Tool IDs
                - model_ids (List[str], optional): Model IDs
                
        Returns:
            Dictionary with 'id' and 'message' keys
        """
        return self._post("/policies/bindings", data=payload)

    def list_bindings(
        self,
        ids: Optional[List[str]] = None,
        artifact_ids: Optional[List[str]] = None,
        agent_ids: Optional[List[str]] = None,
        tool_ids: Optional[List[str]] = None,
        model_ids: Optional[List[str]] = None,
        sort: str = "recent"
    ) -> Dict[str, Any]:
        """
        List policy bindings with optional filtering.
        
        GET /v1/policies/bindings
        
        Args:
            ids: Filter by binding UUIDs (comma-separated)
            artifact_ids: Filter by artifact UUIDs (comma-separated)
            agent_ids: Filter by agent UUIDs (comma-separated)
            tool_ids: Filter by tool UUIDs (comma-separated)
            model_ids: Filter by model UUIDs or public model names (comma-separated)
            sort: Sort order - 'recent' (updated_at desc), 'asc' (created_on asc), 'desc' (created_on desc)
            
        Returns:
            Dictionary with 'bindings' (list) and 'total' (int) keys
            
        Note:
            Only the first populated filter is applied in this order:
            ids -> artifact_ids -> agent_ids -> tool_ids -> model_ids
        """
        params = {"sort": sort}
        
        # Apply filters in precedence order
        if ids:
            params["ids"] = ",".join(ids)
        elif artifact_ids:
            params["artifact_ids"] = ",".join(artifact_ids)
        elif agent_ids:
            params["agent_ids"] = ",".join(agent_ids)
        elif tool_ids:
            params["tool_ids"] = ",".join(tool_ids)
        elif model_ids:
            params["model_ids"] = ",".join(model_ids)
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        
        try:
            return self._get(f"/policies/bindings?{query_string}")
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return {"bindings": [], "total": 0}
            raise e

    def get_bindings_count(self) -> Dict[str, int]:
        """
        Get count of policy bindings by asset type.
        
        GET /v1/policies/bindings/count
        
        Returns:
            Dictionary with counts:
                - agent_policies (int): Number of agent bindings
                - tool_policies (int): Number of tool bindings
                - model_policies (int): Number of model bindings
                - total_policies (int): Total number of unique bindings
        """
        try:
            return self._get("/policies/bindings/count")
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return {
                    "agent_policies": 0,
                    "tool_policies": 0,
                    "model_policies": 0,
                    "total_policies": 0
                }
            raise e

    def get_binding(self, binding_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details of a specific policy binding.
        
        GET /v1/policies/bindings/{binding_id}
        
        Args:
            binding_id: The ID of the binding to retrieve
            
        Returns:
            Binding details dictionary or None if not found
        """
        try:
            return self._get(f"/policies/bindings/{binding_id}")
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return None
            raise e

    def update_binding(self, binding_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing policy binding.
        
        PATCH /v1/policies/bindings/{binding_id}
        
        Args:
            binding_id: The ID of the binding to update
            payload: Dictionary with fields to update (all optional):
                - artifact_id (str): New artifact ID
                - name (str): New internal name
                - display_name (str): New display name
                - description (str): New description
                - hooks (List[str]): New hooks (replaces existing)
                - config (dict): New configuration
                - priority (int): New priority
                - agent_ids (List[str]): New agent IDs (replaces existing)
                - tool_ids (List[str]): New tool IDs (replaces existing)
                - model_ids (List[str]): New model IDs (replaces existing)
                
        Returns:
            Dictionary with 'id' and 'message' keys
            
        Note:
            When an asset-ID field is supplied, its existing mappings are replaced.
            Omitting the field preserves existing mappings.
        """
        return self._patch(f"/policies/bindings/{binding_id}", data=payload)

    def delete_binding(self, binding_id: str) -> dict:
        """
        Delete a policy binding.
        
        DELETE /v1/policies/bindings/{binding_id}
        
        Args:
            binding_id: The ID of the binding to delete
            
        Returns:
            Response dictionary from the delete operation
            
        Note:
            Associated agent, tool, and model mappings are deleted through cascading relationships.
        """
        return self._delete(f"/policies/bindings/{binding_id}")

