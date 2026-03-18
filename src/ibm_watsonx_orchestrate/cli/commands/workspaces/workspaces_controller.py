import logging
import sys
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.json import JSON
from rich.progress import Progress, SpinnerColumn, TextColumn
import typer

from ibm_watsonx_orchestrate.client.workspaces.workspace_client import WorkspaceClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client, is_local_dev, is_cpd_env, is_ibm_cloud_platform
from ibm_watsonx_orchestrate.agent_builder.workspaces.types import WorkspaceRole
from ibm_watsonx_orchestrate.cli.config import (
    Config,
    CONTEXT_SECTION_HEADER,
    CONTEXT_ACTIVE_WORKSPACE_OPT,
    CONTEXT_ACTIVE_ENV_OPT,
    ENVIRONMENTS_SECTION_HEADER,
    ENV_WXO_URL_OPT,
    ENV_CRN_OPT,
    AUTH_CONFIG_FILE_FOLDER,
    AUTH_CONFIG_FILE,
    AUTH_SECTION_HEADER,
    AUTH_MCSP_TOKEN_OPT
)
import zipfile
from pathlib import Path
from ibm_watsonx_orchestrate.agent_builder.agents.types import AgentKind
from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolsController
from ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller import ToolkitController
from ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller import KnowledgeBaseController
from ibm_watsonx_orchestrate.utils.utils import check_file_in_zip
from ibm_watsonx_orchestrate.cli.workspace_context import WorkspaceContext
import jwt
import re

logger = logging.getLogger(__name__)
console = Console()

GLOBAL_WORKSPACE_NAME = "Global Workspace"
GLOBAL_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"


class WorkspacesController:
    def __init__(self):
        """Initialize WorkspacesController with WorkspaceContext."""
        self.client: Optional[WorkspaceClient] = None
        self.workspace_context = WorkspaceContext()

    def get_client(self) -> WorkspaceClient:
        """Get or create workspace client instance."""
        if not self.client:
            self.client = instantiate_client(WorkspaceClient)
        return self.client

    def _check_ibm_cloud_env(self):
        """Validate that the active environment is IBM Cloud."""
        cfg = Config()
        try:
            active_env = cfg.get(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
            if not active_env:
                logger.error("No active environment. Please activate an environment first using 'orchestrate env activate'")
                sys.exit(1)
            
            env_url = cfg.get(ENVIRONMENTS_SECTION_HEADER, active_env, ENV_WXO_URL_OPT)
            if is_local_dev(env_url):
                logger.error(
                    "Workspaces functionality is only available in IBM Cloud environments.")
                sys.exit(1)
            
            if is_cpd_env(env_url):
                logger.error(
                    "Workspaces functionality is only available in IBM Cloud environments.")
                sys.exit(1)
            
            # Check if it's AWS/GA platform (not IBM Cloud)
            if not is_ibm_cloud_platform(env_url):
                logger.error(
                    "Workspaces functionality is only available in IBM Cloud environments.")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"Failed to validate environment: {str(e)}")
            sys.exit(1)
    
    def _get_active_workspace(self) -> Optional[str]:
        """
        Get the name of the currently active workspace.
        
        Uses WorkspaceContext for centralized workspace management.
        """
        return self.workspace_context.get_active_workspace_name()

    def _set_active_workspace(self, workspace_name: Optional[str]):
        """Set the active workspace in config."""
        cfg = Config()
        cfg.write(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_WORKSPACE_OPT, workspace_name)

    # ==================== WORKSPACE CRUD OPERATIONS ====================

    def _validate_workspace_name(self, name: str):
        # Name must be 1-40 characters, can contain letters, numbers, spaces, underscores, and hyphens
        # Must not be empty or only whitespace
        if not name or not name.strip():
            logger.error("Workspace name cannot be empty or only whitespace.")
            sys.exit(1)
        
        # Check maximum length (API enforces 40 characters)
        if len(name) > 40:
            logger.error(f"Invalid workspace name. Name must be at most 40 characters long (current length: {len(name)}).")
            sys.exit(1)
        
        # Allow letters, numbers, spaces, underscores, and hyphens
        # Name should start with a letter or number (not special characters)
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9 _-]*$', name.strip()):
            logger.error(
                f"Invalid workspace name '{name}'. "
                "Name must start with a letter or number and can contain only alphanumeric characters, spaces, underscores, and hyphens."
            )
            sys.exit(1)

    def create_or_update_workspace(self, name: str, description: Optional[str] = None):
        """Create or update a workspace (upsert)."""
        self._check_ibm_cloud_env()
        self._validate_workspace_name(name)
        
        try:
            client = self.get_client()
            
            # Check if workspace exists (use centralized workspace context)
            workspace_id = self.workspace_context._resolve_workspace_name_to_id(name)
            
            if workspace_id:
                # Update existing workspace
                payload = {}
                if description:
                    payload["description"] = description
                
                if payload:
                    with Progress(
                        SpinnerColumn(spinner_name="dots"),
                        TextColumn("[progress.description]{task.description}"),
                        transient=True,
                        console=console,
                    ) as progress:
                        progress.add_task(description="Updating workspace...", total=None)
                        client.update(workspace_id, payload)
                    
                    logger.info(f"Successfully updated workspace '{name}'")
                else:
                    logger.info(f"Workspace '{name}' already exists with no changes")
            else:
                # Create new workspace
                payload = {"name": name}
                if description:
                    payload["description"] = description
                
                with Progress(
                    SpinnerColumn(spinner_name="dots"),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True,
                    console=console,
                ) as progress:
                    progress.add_task(description="Creating workspace...", total=None)
                    response = client.create(payload)
                
                logger.info(f"Successfully created workspace '{name}' (ID: {response.get('workspace_id')})")
            
        except Exception as e:
            logger.error(f"Failed to create/update workspace: {str(e)}")
            sys.exit(1)

    def list_workspaces(self, verbose: bool = False):
        """List all accessible workspaces with activation status."""
        self._check_ibm_cloud_env()
        
        try:
            client = self.get_client()
            response = client.get(params={"show_all": "true"})
            workspaces = response if isinstance(response, list) else []
            
            active_workspace = self._get_active_workspace()
            
            if verbose:
                console.print(JSON.from_data(response))
            else:
                if not workspaces:
                    logger.info("No workspaces found")
                    return
                
                table = Table(title="Workspaces")
                table.add_column("Active", style="green", justify="center")
                table.add_column("Name", style="cyan")
                table.add_column("Workspace ID", style="magenta")
                
                for workspace in workspaces:
                    workspace_name = workspace.get("name", "")
                    workspace_id = workspace.get("workspace_id", "")
                    
                    # Check if this is the Global Workspace (by ID or name)
                    is_global = (
                        workspace_id == GLOBAL_WORKSPACE_ID or
                        workspace_name == GLOBAL_WORKSPACE_NAME
                    )
                    
                    # Determine if this workspace should show as active
                    is_active = ""
                    if active_workspace:
                        # A specific workspace is activated - check if it matches
                        is_active = "✓" if workspace_name == active_workspace else ""
                    elif is_global:
                        # No workspace activated - Global is the default active workspace
                        is_active = "✓"
                    
                    table.add_row(
                        is_active,
                        workspace_name,
                        workspace_id
                    )
                
                console.print(table)
                logger.info(f"Total: {len(workspaces)} workspace(s)")
                if active_workspace:
                    logger.info(f"Active workspace: {active_workspace}")
                else:
                    logger.info(f"Active workspace: Global Workspace")
                    
        except Exception as e:
            logger.error(f"Failed to list workspaces: {str(e)}")
            sys.exit(1)

    def remove_workspace(self, name: str, delete_artifacts: bool = True):
        self._check_ibm_cloud_env()
        
        try:
            # Check if removing the active workspace
            active_workspace = self._get_active_workspace()
            is_active = (active_workspace == name)
            
            # Get workspace ID (use centralized workspace context)
            workspace_id = self.workspace_context._resolve_workspace_name_to_id(name)
            if not workspace_id:
                logger.error(f"Workspace '{name}' not found")
                sys.exit(1)
            
            # Confirm deletion if delete_artifacts is True
            if delete_artifacts:
                if not typer.confirm(
                    f"WARNING: This will delete workspace '{name}' and ALL its resources. Continue?",
                    default=False
                ):
                    logger.info("Operation cancelled")
                    return
            
            client = self.get_client()
            
            with Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
                console=console,
            ) as progress:
                progress.add_task(description="Removing workspace...", total=None)
                client.delete(workspace_id, delete_artifacts=delete_artifacts)
            
            logger.info(f"Successfully removed workspace '{name}'")
            
            # If this was the active workspace, reset to global
            if is_active:
                self._set_active_workspace(None)
                logger.info(f"Workspace '{name}' was active. Reset to global workspace")
            
        except Exception as e:
            logger.error(f"Failed to remove workspace: {str(e)}")
            sys.exit(1)

    def activate_workspace(self, name: str):
        self._check_ibm_cloud_env()
        
        try:
            # Verify workspace exists
            workspace_id = self.workspace_context._resolve_workspace_name_to_id(name)
            if not workspace_id:
                logger.error(f"Workspace '{name}' not found")
                sys.exit(1)
            
            # Set as active
            self._set_active_workspace(name)
            logger.info(f"Activated workspace: {name}")
            
        except Exception as e:
            logger.error(f"Failed to activate workspace: {str(e)}")
            sys.exit(1)

    def deactivate_workspace(self):
        self._check_ibm_cloud_env()
        
        try:
            active_workspace = self._get_active_workspace()
            if not active_workspace:
                logger.info("No workspace is currently active")
                return
            
            self._set_active_workspace(None)
            logger.info(f"Deactivated workspace '{active_workspace}'. Reset to global workspace")
            
        except Exception as e:
            logger.error(f"Failed to deactivate workspace: {str(e)}")
            sys.exit(1)

    # ==================== WORKSPACE MEMBER OPERATIONS ====================

    def _resolve_workspace(self, workspace_name: Optional[str]) -> tuple[str, str]:
        """
        Resolve workspace name to workspace ID.
        Uses active workspace if name not provided.
        
        Returns:
            Tuple of (workspace_name, workspace_id)
        """
        if not workspace_name:
            workspace_name = self._get_active_workspace()
            if not workspace_name:
                logger.error("No workspace specified and no active workspace. Use -n to specify a workspace or activate one first")
                sys.exit(1)
        
        workspace_id = self.workspace_context._resolve_workspace_name_to_id(workspace_name)
        if not workspace_id:
            logger.error(f"Workspace '{workspace_name}' not found")
            sys.exit(1)
        
        return workspace_name, workspace_id

    def _get_account_id(self) -> str:
        """Extract IBM Cloud account ID from the active environment token."""

        try:
            auth_cfg = Config(AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE)
            cfg = Config()
            active_env = cfg.read(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
            
            if not active_env:
                logger.error("No active environment found")
                sys.exit(1)
            
            existing_auth_config = auth_cfg.get(AUTH_SECTION_HEADER).get(active_env, {})
            existing_token = existing_auth_config.get(AUTH_MCSP_TOKEN_OPT) if existing_auth_config else None
            
            if not existing_token:
                logger.error("No authentication token found for active environment")
                sys.exit(1)
            
            # Decode token to extract account information
            token = jwt.decode(existing_token, options={"verify_signature": False})
            
            # Get account ID from token
            account_id = token.get('account', {}).get('bss') if isinstance(token.get('account'), dict) else None
            
            if not account_id:
                # Try direct account field
                account_id = token.get('account')
            
            if not account_id:
                logger.error("Could not extract account ID from token")
                sys.exit(1)
            
            return account_id
            
        except Exception as e:
            logger.error(f"Failed to extract account ID: {str(e)}")
            sys.exit(1)

    def _resolve_email_to_user_id(self, email: str) -> str:
        """Resolve user email to IAM user ID using IBM Cloud User Management API."""
        try:
            account_id = self._get_account_id()
            client = self.get_client()
                        
            user_id = client.resolve_user_email_to_id(account_id, email)
            
            if not user_id:
                logger.error(f"User with email '{email}' not found in IBM Cloud account")
                sys.exit(1)
            
            return user_id
        except Exception as e:
            logger.error(f"Failed to resolve user email: {str(e)}")
            sys.exit(1)

    def add_or_update_member(self, workspace_name: Optional[str], user_email: str, role: WorkspaceRole):
        """Add or update a member in a workspace (upsert)."""
        self._check_ibm_cloud_env()
        
        try:
            workspace_name, workspace_id = self._resolve_workspace(workspace_name)
            user_id = self._resolve_email_to_user_id(user_email)
            
            client = self.get_client()
            
            # Check if user is already a member
            members = client.list_members(workspace_id)
            member_list = members if isinstance(members, list) else []
            existing_member = next((m for m in member_list if m.get("user_id") == user_id), None)
            
            if existing_member:
                # Update existing member - single object format
                payload = {"user_id": user_id, "role": role.value}
                
                with Progress(
                    SpinnerColumn(spinner_name="dots"),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True,
                    console=console,
                ) as progress:
                    progress.add_task(description="Updating member...", total=None)
                    client.update_member(workspace_id, payload)
                
                logger.info(f"Successfully updated member '{user_email}' to role '{role.value}' in workspace '{workspace_name}'")
            else:
                # Add new member - batch format with members array
                payload = {
                    "members": [
                        {"user_id": user_id, "role": role.value}
                    ]
                }
                
                with Progress(
                    SpinnerColumn(spinner_name="dots"),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True,
                    console=console,
                ) as progress:
                    progress.add_task(description="Adding member...", total=None)
                    client.add_member(workspace_id, payload)
                
                logger.info(f"Successfully added member '{user_email}' with role '{role.value}' to workspace '{workspace_name}'")
                
        except Exception as e:
            logger.error(f"Failed to add/update member: {str(e)}")
            sys.exit(1)

    def list_members(self, workspace_name: Optional[str], verbose: bool = False):
        """List all members in a workspace."""
        self._check_ibm_cloud_env()
        
        try:
            workspace_name, workspace_id = self._resolve_workspace(workspace_name)
            
            client = self.get_client()
            response = client.list_members(workspace_id)
            
            if verbose:
                console.print(JSON.from_data(response))
            else:
                members = response if isinstance(response, list) else []
                
                if not members:
                    logger.info(f"No members found in workspace '{workspace_name}'")
                    return
                
                table = Table(title=f"Members of '{workspace_name}'")
                table.add_column("User ID", style="cyan")
                table.add_column("Email", style="yellow")
                table.add_column("Role", style="green")
                
                for member in members:
                    table.add_row(
                        member.get("user_id", ""),
                        member.get("email", "") or "N/A",
                        member.get("role", "")
                    )
                
                console.print(table)
                logger.info(f"Total: {len(members)} member(s)")
                
        except Exception as e:
            logger.error(f"Failed to list members: {str(e)}")
            sys.exit(1)

    def remove_member(self, workspace_name: Optional[str], user_email: str):
        """Remove a member from a workspace."""
        self._check_ibm_cloud_env()
        
        try:
            workspace_name, workspace_id = self._resolve_workspace(workspace_name)
            user_id = self._resolve_email_to_user_id(user_email)
            
            client = self.get_client()
            # Remove member - single object format
            payload = {"user_id": user_id}
            
            with Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
                console=console,
            ) as progress:
                progress.add_task(description="Removing member...", total=None)
                client.remove_member(workspace_id, payload)
            
            logger.info(f"Successfully removed member '{user_email}' from workspace '{workspace_name}'")
                
        except Exception as e:
            logger.error(f"Failed to remove member: {str(e)}")
            sys.exit(1)
    
    def export_workspace(self, workspace_name: Optional[str], output_path: str):
        """
        Export all resources from a workspace to a zip file.
        
        This exports:
        - All agents (which include their attached tools, toolkits, and collaborators)
        - Standalone tools (not attached to any agent)
        - Standalone toolkits (not attached to any agent)
        - Knowledge bases (exported as YAML specs with connections)
        
        Args:
            workspace_name: Name of the workspace to export (uses active workspace if None)
            output_path: Path to the output zip file
        """
        
        try:
            # Resolve workspace
            workspace_name, workspace_id = self._resolve_workspace(workspace_name)
            
            # Validate output path
            output_file = Path(output_path)
            if output_file.suffix != ".zip":
                logger.error(f"Output file must end with '.zip'. Provided: '{output_path}'")
                sys.exit(1)
                        
            logger.info(f"Exporting workspace '{workspace_name}' to '{output_path}'...")
            
            output_file_name = output_file.stem
            
            with zipfile.ZipFile(output_path, "w") as zip_file:
                # Track exported resources
                exported_agents = set()
                standalone_tool_count = 0
                standalone_toolkit_count = 0
                
                # Export all agents in the workspace
                # Note: Agent export automatically includes their attached tools, toolkits, and collaborators
                # Lazy import to avoid circular dependency
                from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentsController
                agents_controller = AgentsController()
                
                # Get all agent types
                for agent_kind in [AgentKind.NATIVE, AgentKind.EXTERNAL, AgentKind.ASSISTANT]:
                    try:
                        # Fetch agents directly from client
                        agents, _ = agents_controller._fetch_and_parse_agents(agent_kind)
                        
                        for agent in agents:
                            agent_name = agent.name
                            if agent_name and agent_name not in exported_agents:
                                logger.info(f"Exporting {agent_kind.value} agent: {agent_name}")
                                # Pass output_path directly - agent export will use its stem as folder prefix
                                agents_controller.export_agent(
                                    name=agent_name,
                                    kind=agent_kind,
                                    output_path=output_path,
                                    zip_file_out=zip_file
                                )
                                exported_agents.add(agent_name)
                                
                    except Exception as e:
                        logger.warning(f"Could not export {agent_kind.value} agents: {str(e)}")
                
                # Export standalone tools (tools not attached to any agent)
                try:

                    tools_controller = ToolsController()
                    
                    # Get all tools
                    response = tools_controller.get_client().get()
                    
                    for tool_spec in response:
                        tool_name = tool_spec.get('name')
                        if tool_name:
                            # Check if tool was already exported with an agent
                            tool_path = f"{output_file_name}/tools/{tool_name}/"
                            if check_file_in_zip(file_path=tool_path, zip_file=zip_file):
                                continue
                                
                            try:
                                logger.info(f"Exporting standalone tool: {tool_name}")
                                tools_controller.export_tool(
                                    name=tool_name,
                                    output_path=tool_path,
                                    zip_file_out=zip_file,
                                    spec=tool_spec,
                                    connections_output_path=f"{output_file_name}/connections/"
                                )
                                standalone_tool_count += 1
                            except Exception as e:
                                logger.warning(f"Could not export tool '{tool_name}': {str(e)}")
                                
                except Exception as e:
                    logger.warning(f"Could not export standalone tools: {str(e)}")
                
                try:
                    toolkit_controller = ToolkitController()
                    
                    # Get all toolkits
                    toolkits, _ = toolkit_controller._fetch_and_parse_toolkits()
                    
                    for toolkit in toolkits:
                        toolkit_name = toolkit.__toolkit_spec__.name
                        if not toolkit_name:
                            continue
                            
                        # Check if toolkit was already exported
                        toolkit_path = f"{output_file_name}/toolkits/{toolkit_name}.yaml"
                        if check_file_in_zip(file_path=toolkit_path, zip_file=zip_file):
                            continue
                        
                        try:
                            logger.info(f"Exporting standalone toolkit: {toolkit_name}")
                            toolkit_controller.export_toolkit(
                                name=toolkit_name,
                                output_file=toolkit_path,
                                zip_file_out=zip_file,
                                connections_output_path=f"{output_file_name}/connections/"
                            )
                            standalone_toolkit_count += 1
                        except Exception as e:
                            logger.warning(f"Could not export toolkit '{toolkit_name}': {str(e)}")
                                
                except Exception as e:
                    logger.warning(f"Could not export standalone toolkits: {str(e)}")
                
                # Export knowledge bases
                knowledge_base_count = 0
                try:
                    kb_controller = KnowledgeBaseController()
                    
                    # Get all knowledge bases
                    knowledge_bases = kb_controller.get_client().get()
                    
                    for kb in knowledge_bases:
                        kb_name = kb.get('name')
                        kb_id = kb.get('id')
                        if kb_name and kb_id:
                            try:
                                logger.info(f"Exporting knowledge base: {kb_name}")
                                kb_path = f"{output_file_name}/knowledge_bases/"
                                kb_controller.knowledge_base_export(
                                    output_path=kb_path,
                                    id=kb_id,
                                    zip_file_out=zip_file,
                                    connections_output_path=f"{output_file_name}/connections/"
                                )
                                knowledge_base_count += 1
                            except Exception as e:
                                logger.warning(f"Could not export knowledge base '{kb_name}': {str(e)}")
                                
                except Exception as e:
                    logger.warning(f"Could not export knowledge bases: {str(e)}")
            
            logger.info(f"Successfully exported workspace '{workspace_name}' to '{output_path}'")
            logger.info(f"Agents exported: {len(exported_agents)}")
            logger.info(f"Standalone tools exported: {standalone_tool_count}")
            logger.info(f"Standalone toolkits exported: {standalone_toolkit_count}")
            logger.info(f"Knowledge bases exported: {knowledge_base_count}")
            
        except Exception as e:
            logger.error(f"Failed to export workspace: {str(e)}")
            sys.exit(1)