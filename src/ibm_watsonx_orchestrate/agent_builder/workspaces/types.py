"""Type definitions for workspace management."""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class WorkspaceRole(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"


# ==================== REQUEST SCHEMAS ====================

class WorkspaceCreateRequest(BaseModel):
    """Request model for creating a new workspace."""
    name: str = Field(..., min_length=1, description="Workspace name (must be unique within tenant)")
    description: Optional[str] = Field(None, description="Workspace description")


class WorkspaceUpdateRequest(BaseModel):
    """Request model for updating a workspace."""
    name: Optional[str] = Field(None, min_length=1, description="New workspace name")
    description: Optional[str] = Field(None, description="New workspace description")


class MemberAddRequest(BaseModel):
    """Request model for adding a single member to a workspace."""
    user_id: str = Field(..., description="User IAM identifier (e.g., IBMid-662002K7XL)")
    role: WorkspaceRole = Field(..., description="Workspace role for the user")


class MemberBatchAddRequest(BaseModel):
    """Request model for adding multiple members to a workspace."""
    members: List[MemberAddRequest] = Field(..., min_length=1, description="List of members to add")


class MemberUpdateRequest(BaseModel):
    """Request model for updating a single member's role."""
    user_id: str = Field(..., description="User IAM identifier to update")
    role: WorkspaceRole = Field(..., description="New workspace role for the user")


class MemberBatchUpdateRequest(BaseModel):
    """Request model for updating multiple members' roles."""
    members: List[MemberUpdateRequest] = Field(..., min_length=1, description="List of members to update")


class MemberInfo(BaseModel):
    """Information about a member for removal operations."""
    user_id: str = Field(..., description="User IAM ID (e.g., IBMid-662002K7XL)")


class MemberBatchRemoveRequest(BaseModel):
    """Request model for removing multiple members from a workspace."""
    members: List[MemberInfo] = Field(..., min_length=1, description="List of members to remove")


# ==================== RESPONSE SCHEMAS ====================

class WorkspaceResponse(BaseModel):
    """Response model for workspace operations."""
    workspace_id: Optional[str] = Field(None, description="Workspace UUID")
    tenant_id: str = Field(..., description="Tenant identifier")
    name: str = Field(..., description="Workspace name")
    description: Optional[str] = Field(None, description="Workspace description")
    created_by: str = Field(..., description="Creator user ID")
    created_on: datetime = Field(..., description="Workspace creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    role: Optional[str] = Field(None, description="User's role in the workspace (owner or editor)")


class WorkspaceListResponse(BaseModel):
    """Response model for listing workspaces."""
    workspaces: List[WorkspaceResponse] = Field(..., description="List of workspaces (global workspace always first)")
    total: Optional[int] = Field(None, description="Total number of accessible workspaces")


class WorkspaceSettingsResponse(BaseModel):
    """Response model for workspace settings."""
    trusted_profile_setup: bool = Field(..., description="Whether trusted profile is configured and found")


class WorkspaceMember(BaseModel):
    """Model representing a workspace member."""
    workspace_id: str = Field(..., description="Workspace identifier")
    user_id: str = Field(..., description="User IAM identifier")
    role: WorkspaceRole = Field(..., description="User's role in the workspace")
    email: Optional[str] = Field(None, description="User email address from IBM Cloud")


class MemberOperationResult(BaseModel):
    """Result of a single member operation."""
    user_id: str = Field(..., description="User identifier")
    success: bool = Field(..., description="Whether operation succeeded")
    error: Optional[str] = Field(None, description="Error message if operation failed")


class BatchMemberOperationResponse(BaseModel):
    """Response model for batch member operations."""
    results: List[MemberOperationResult] = Field(..., description="Results for each operation")
    total: int = Field(..., description="Total number of operations attempted")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")


class TenantUser(BaseModel):
    """Tenant user information from IBM Cloud account."""
    name: Optional[str] = Field(None, description="User's full name")
    email: Optional[str] = Field(None, description="User's email address")
    id: Optional[str] = Field(None, description="User's IAM identifier")


class AccountUsersResponse(BaseModel):
    """Response model for listing account users."""
    users: List[TenantUser] = Field(..., description="List of authorized account users (ACTIVE status only)")