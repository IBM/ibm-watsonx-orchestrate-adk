"""Client for workspace management API operations."""

from typing import Optional
from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient


import requests
import logging
logger = logging.getLogger(__name__)

class WorkspaceClient(BaseWXOClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # ==================== WORKSPACE CRUD OPERATIONS ====================

    def create(self, payload: dict) -> dict:
        """
        Create a new workspace.
        
        Args:
            payload: Workspace creation data with name and optional description
            
        Returns:
            Dictionary with created workspace details 
        """
        return self._post("/workspaces", data=payload)

    def get(self, workspace_id: Optional[str] = None, params: Optional[dict] = None) -> dict:
        """
        Get workspace(s).
        
        If workspace_id is provided, returns a single workspace.
        Otherwise, returns a list of workspaces the user has access to.
        
        Args:
            workspace_id: Optional workspace UUID to get specific workspace
            params: Optional query parameters (limit, offset, exclude, show_all)
            
        Returns:
            Dictionary with workspace data or list of workspaces
        """
        if workspace_id:
            return self._get(f"/workspaces/{workspace_id}")
        else:
            return self._get("/workspaces", params=params or {})

    def update(self, workspace_id: str, payload: dict) -> dict:
        """
        Update workspace name and/or description.
        
        Args:
            workspace_id: Workspace UUID to update
            payload: Update data with optional name and/or description
            
        Returns:
            Empty dict on success (204 response)
        """
        return self._patch(f"/workspaces/{workspace_id}", data=payload)

    def delete(self, workspace_id: str, delete_artifacts: bool = True) -> dict:
        """
        Delete a workspace.
        
        Args:
            workspace_id: Workspace UUID to delete
            delete_artifacts: Whether to delete artifacts or move to global workspace
            
        Returns:
            Dictionary with status and workspace_id
        """
        return self._delete(f"/workspaces/{workspace_id}?delete_artifacts={str(delete_artifacts).lower()}")

    # ==================== WORKSPACE MEMBER OPERATIONS ====================

    def add_member(self, workspace_id: str, payload: dict) -> dict:
        """
        Add one or more members to a workspace.
        
        Args:
            workspace_id: Workspace UUID
            payload: Single member or batch of members to add
            
        Returns:
            Dictionary with batch operation results
        """
        return self._post(f"/workspaces/{workspace_id}/members", data=payload)

    def list_members(self, workspace_id: str) -> dict:
        """
        List all members in a workspace.
        
        Args:
            workspace_id: Workspace UUID
            
        Returns:
            Dictionary or list of member dictionaries
        """
        return self._get(f"/workspaces/{workspace_id}/members")

    def update_member(self, workspace_id: str, payload: dict) -> dict:
        """
        Update role(s) of workspace member(s).
        
        Args:
            workspace_id: Workspace UUID
            payload: Single member or batch of members to update
            
        Returns:
            Dictionary with batch operation results
        """
        return self._put(f"/workspaces/{workspace_id}/members", data=payload)

    def remove_member(self, workspace_id: str, payload: dict) -> dict:
        """
        Remove a member from a workspace.
        
        Args:
            workspace_id: Workspace UUID
            payload: Member to remove (single MemberInfo object with user_id)
            
        Returns:
            Dictionary with operation result
        """
        return self._delete(f"/workspaces/{workspace_id}/members", data=payload)

    # ==================== INTERNAL OPERATIONS ====================

    def list_account_users(self, tenant_id: str, workspace_id: Optional[str] = None) -> dict:
        """
        List all authorized users in the IBM Cloud account.
        
        Internal endpoint.
        
        Args:
            tenant_id: The tenant ID (must match the access token)
            workspace_id: Optional workspace ID (may be required by some deployments)
            
        Returns:
            Dictionary with list of authorized users
        """

        params = {}
        if workspace_id:
            params["workspace_id"] = workspace_id
            logger.debug(f"Calling account-users with workspace_id parameter: {workspace_id}")
        else:
            logger.debug("Calling account-users without workspace_id parameter")
        
        return self._get(f"/tenants/{tenant_id}/users", params=params)


    def resolve_user_email_to_id(self, account_id: str, email: str) -> Optional[str]:
        """
        Resolve user email to IAM user ID using IBM Cloud User Management API.
        
        Args:
            account_id: IBM Cloud account ID (from JWT token's account.bss claim)
            email: User email address to resolve
            
        Returns:
            IAM user ID (e.g., IBMid-693000JE6S) if found, None otherwise
            
        """
        
        try:
            # Determine the IBM Cloud User Management API base URL based on environment
            # Check if we're in test/preprod environment
            if "test.cloud.ibm.com" in self.base_url or "ibmpreprod" in self.base_url: # This can probably be removed after testing has finished. 
                user_mgmt_base_url = "https://user-management.test.cloud.ibm.com"
            else:
                user_mgmt_base_url = "https://user-management.cloud.ibm.com"
            
            endpoint = f"{user_mgmt_base_url}/v2/accounts/{account_id}/users"
            
            # Get the bearer token from the current session
            token = None
            if self.api_key:
                token = self.api_key
            elif self.authenticator:
                token = self.authenticator.token_manager.get_token()
            
            if not token:
                logger.error("No authentication token available")
                return None
            
            headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {token}"
            }
                        
            response = requests.get(endpoint, headers=headers, timeout=30)
            
            if response.status_code != 200:
                # Return None and let controller handle the error message
                return None
            
            data = response.json()
            users = data.get("resources", [])
                        
            # Find exact email match (case-insensitive)
            for user in users:
                user_email = user.get("email", "") or user.get("user_id", "")
                if user_email.lower() == email.lower():
                    # Get IAM ID - try multiple field names
                    iam_id = user.get("iam_id") or user.get("id") or user.get("user_id")
                    if iam_id:
                        return iam_id
            
            # User not found - return None and let the controller handle the error message
            return None
                    
        except requests.exceptions.RequestException:
            # Return None and let controller handle the error message
            return None
        except Exception:
            # Return None and let controller handle the error message
            return None