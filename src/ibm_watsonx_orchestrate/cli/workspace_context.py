"""
Workspace context utilities for managing active workspace state across CLI operations.

This module provides centralized workspace context management for IBM Cloud deployments,
including workspace ID resolution, active workspace tracking, and environment detection.
"""

import logging
from typing import Optional

from ibm_watsonx_orchestrate.cli.config import (
    Config,
    CONTEXT_SECTION_HEADER,
    CONTEXT_ACTIVE_WORKSPACE_OPT,
    CONTEXT_ACTIVE_ENV_OPT,
    ENVIRONMENTS_SECTION_HEADER,
    ENV_WXO_URL_OPT,
)

logger = logging.getLogger(__name__)

# Global workspace ID constant
GLOBAL_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
GLOBAL_WORKSPACE_NAME = "Global workspace"


def is_ibm_cloud_platform(url: str) -> bool:
    """Check if the given URL is an IBM Cloud platform URL."""

    return "test.cloud.ibm.com" in url or "cloud.ibm.com" in url


class WorkspaceContext:
    """
    Manages workspace context for CLI operations.
    
    This class provides methods to:
    - Get the active workspace ID
    - Check if workspaces are supported in the current environment (Only IBM Cloud for now)
    - Resolve workspace names to IDs
    - Validate workspace context
    """
    
    def __init__(self):
        """Initialize workspace context manager."""
        self.config = Config()
    
    def should_use_workspaces(self) -> bool:
        """Check if the current environment supports workspaces."""
        try:
            active_env = self.config.get(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
            if not active_env:
                return False
            
            url = self.config.get(ENVIRONMENTS_SECTION_HEADER, active_env, ENV_WXO_URL_OPT)
            if not url or not isinstance(url, str):
                return False
            
            return is_ibm_cloud_platform(url)
        except Exception as e:
            logger.debug(f"Error checking workspace support: {e}")
            return False
    
    def get_active_workspace_name(self) -> Optional[str]:
        """Get the name of the currently active workspace."""

        try:
            workspace_name = self.config.get(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_WORKSPACE_OPT)
            if workspace_name and isinstance(workspace_name, str):
                return workspace_name
            return None
        except Exception as e:
            logger.debug(f"Error getting active workspace name: {e}")
            return None
    
    def get_active_workspace_id(self) -> Optional[str]:
        """Get the ID of the currently active workspace."""

        workspace_name = self.get_active_workspace_name()
        
        if not workspace_name:
            return None
        
        # Handle global workspace
        if workspace_name == GLOBAL_WORKSPACE_NAME:
            return GLOBAL_WORKSPACE_ID
        
        # For other workspaces, we need to resolve the name to ID
        return self._resolve_workspace_name_to_id(workspace_name)
    
    def _resolve_workspace_name_to_id(self, workspace_name: str) -> Optional[str]:
        """Resolve a workspace name to its ID."""

        # Import here to avoid circular dependency
        from ibm_watsonx_orchestrate.client.workspaces.workspace_client import WorkspaceClient
        from ibm_watsonx_orchestrate.client.utils import instantiate_client
        
        try:
            workspace_client = instantiate_client(WorkspaceClient)
            
            # Get all workspaces without filtering (use show_all=true to bypass workspace context)
            # This prevents circular dependency where get() would add workspace_id query param
            workspaces = workspace_client._get("/workspaces", params={'show_all': 'true'})
            
            if not isinstance(workspaces, list):
                logger.warning("Unexpected workspace response format")
                return None
            
            for workspace in workspaces:
                if workspace.get("name") == workspace_name:
                    return workspace.get("workspace_id")
            
            # Workspace not found - return None and let caller handle the error message
            return None
            
        except Exception as e:
            logger.error(f"Error resolving workspace name to ID: {e}")
            return None
    
    def resolve_workspace_id_to_name(self, workspace_id: str) -> Optional[str]:
        """Resolve a workspace ID to its name."""

        # Handle global workspace
        if workspace_id == GLOBAL_WORKSPACE_ID:
            return GLOBAL_WORKSPACE_NAME
        
        # Import here to avoid circular dependency
        from ibm_watsonx_orchestrate.client.workspaces.workspace_client import WorkspaceClient
        from ibm_watsonx_orchestrate.client.utils import instantiate_client
        
        try:
            workspace_client = instantiate_client(WorkspaceClient)
            
            # Get workspace by ID
            workspace = workspace_client.get(workspace_id)
            return workspace.get("name")
            
        except Exception as e:
            logger.error(f"Error resolving workspace ID to name: {e}")
            return None
    


# Convenience functions for common operations
def get_active_workspace_id() -> Optional[str]:
    """Get the ID of the currently active workspace."""
    
    context = WorkspaceContext()
    return context.get_active_workspace_id()


def should_use_workspaces() -> bool:
    """
    Check if the current environment supports workspaces.
    
    Returns:
        True if workspaces are supported, False otherwise
    """
    context = WorkspaceContext()
    return context.should_use_workspaces()


def get_active_workspace_name() -> Optional[str]:
    """Get the name of the currently active workspace."""

    context = WorkspaceContext()
    return context.get_active_workspace_name()


# Payload manipulation functions for API clients
def resolve_and_inject_workspace(payload: dict) -> dict:
    """
    Resolve workspace field and inject active workspace context into payload.
    
    This function implements the following logic:
    1. If active workspace exists, use it (warn if spec has different workspace)
    2. If no active workspace, resolve workspace name from spec to workspace_id
    3. Remove the workspace field and add workspace_id field
    
    Args:
        payload: The request payload dictionary
        
    Returns:
        Modified payload with workspace_id instead of workspace
    """
    try:
        # Only process if workspaces are supported (IBM Cloud)
        if not should_use_workspaces():
            # Remove workspace field if present for non-IBM Cloud environments
            payload.pop('workspace', None)
            return payload
        
        context = WorkspaceContext()
        active_workspace_id = context.get_active_workspace_id()
        spec_workspace_name = payload.pop('workspace', None)
        
        # Case 1: Active workspace exists
        if active_workspace_id:
            # Warn if spec has different workspace
            if spec_workspace_name:
                active_workspace_name = context.get_active_workspace_name()
                if spec_workspace_name != active_workspace_name:
                    logger.warning(
                        f"Active workspace '{active_workspace_name}' will be used instead of "
                        f"spec workspace '{spec_workspace_name}'"
                    )
            
            payload['workspace_id'] = active_workspace_id
        
        # Case 2: No active workspace, but spec has workspace
        elif spec_workspace_name:
            workspace_id = context._resolve_workspace_name_to_id(spec_workspace_name)
            if workspace_id:
                payload['workspace_id'] = workspace_id
            else:
                logger.warning(f"Workspace '{spec_workspace_name}' not found, proceeding without workspace_id")
        
        # Case 3: No active workspace and no spec workspace - default to Global Workspace
        else:
            # For IBM Cloud, always inject Global Workspace ID if no workspace is specified
            logger.debug("No workspace specified, defaulting to Global Workspace")
            payload['workspace_id'] = GLOBAL_WORKSPACE_ID
        
        return payload
    except Exception as e:
        # If we can't resolve workspace context (e.g., during environment activation),
        # just remove workspace field and return payload unchanged
        logger.debug(f"Could not resolve workspace context: {e}")
        payload.pop('workspace', None)
        return payload


def convert_workspace_id_to_name(response: dict) -> dict:
    """
    Convert workspace_id to workspace name in API response for export.
    
    Args:
        response: The API response dictionary
        
    Returns:
        Modified response with workspace instead of workspace_id
    """
    try:
        # Only process if workspaces are supported (IBM Cloud)
        if not should_use_workspaces():
            return response
        
        workspace_id = response.pop('workspace_id', None)
        
        if workspace_id:
            context = WorkspaceContext()
            workspace_name = context.resolve_workspace_id_to_name(workspace_id)
            
            if workspace_name:
                response['workspace'] = workspace_name
            else:
                logger.warning(f"Could not resolve workspace_id '{workspace_id}' to name")
        
        return response
    except Exception as e:
        # If we can't resolve workspace names (e.g., during environment activation),
        # just return response unchanged
        logger.debug(f"Could not convert workspace_id to name: {e}")
        return response


def add_workspace_query_param(params: Optional[dict] = None) -> dict:
    """
    Add workspace_id query parameter for list operations.
    
    If active workspace exists, adds workspace_id to query parameters.
    
    Args:
        params: Existing query parameters (optional)
        
    Returns:
        Query parameters with workspace_id added if applicable
    """
    if params is None:
        params = {}
    
    try:
        # Only process if workspaces are supported (IBM Cloud)
        if not should_use_workspaces():
            return params
        
        context = WorkspaceContext()
        active_workspace_id = context.get_active_workspace_id()
        
        if active_workspace_id:
            params['workspace_id'] = active_workspace_id
        
        return params
    except Exception as e:
        # If we can't determine workspace context (e.g., during environment activation),
        # just return params unchanged
        logger.debug(f"Could not add workspace query param: {e}")
        return params