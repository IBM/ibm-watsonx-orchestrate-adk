import pytest
from unittest.mock import patch, MagicMock, Mock
from ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller import WorkspacesController
from ibm_watsonx_orchestrate.client.workspaces.workspace_client import WorkspaceClient
from ibm_watsonx_orchestrate.agent_builder.workspaces.types import WorkspaceRole


@pytest.fixture
def mock_workspace_client():
    """Mock WorkspaceClient for testing"""
    client = MagicMock(spec=WorkspaceClient)
    return client


@pytest.fixture
def workspaces_controller(mock_workspace_client):
    """Create WorkspacesController with mocked client"""
    controller = WorkspacesController()
    controller.client = mock_workspace_client
    return controller


@pytest.fixture
def sample_workspace():
    """Sample workspace data"""
    return {
        "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
        "tenant_id": "tenant-123",
        "name": "Marketing_Team_Workspace",
        "description": "Workspace for marketing automation",
        "created_by": "IBMid-662002K7XL",
        "created_on": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-20T14:45:00Z",
        "role": "owner"
    }


@pytest.fixture
def sample_workspaces_list(sample_workspace):
    """Sample list of workspaces - API returns list directly"""
    return [
        {
            "workspace_id": "00000000-0000-0000-0000-000000000001",
            "name": "Global Workspace",
            "description": "Global workspace",
            "role": "owner"
        },
        sample_workspace,
        {
            "workspace_id": "223e4567-e89b-12d3-a456-426614174001",
            "name": "Engineering_Team",
            "description": "Workspace for engineering",
            "role": "editor"
        }
    ]


class TestWorkspacesList:
    """Tests for workspace list command"""

    @patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller.Config')
    def test_list_workspaces_success(self, mock_config, workspaces_controller, mock_workspace_client, sample_workspaces_list):
        """Test successful workspace listing"""
        # Mock IBM Cloud environment check
        mock_cfg_instance = Mock()
        mock_cfg_instance.get.side_effect = lambda section, *args: {
            ('context', 'active_environment'): 'prod',
            ('environments', 'prod', 'wxo_url'): 'https://cloud.ibm.com'
        }.get((section, *args))
        mock_config.return_value = mock_cfg_instance
        
        mock_workspace_client.get.return_value = sample_workspaces_list

        workspaces_controller.list_workspaces()

        mock_workspace_client.get.assert_called_once()


class TestWorkspacesCreate:
    """Tests for workspace create/update command"""

    @patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller.Config')
    def test_create_workspace_success(self, mock_config, workspaces_controller, mock_workspace_client, sample_workspace):
        """Test successful workspace creation"""
        # Mock IBM Cloud environment check
        mock_cfg_instance = Mock()
        mock_cfg_instance.get.side_effect = lambda section, *args: {
            ('context', 'active_environment'): 'prod',
            ('environments', 'prod', 'wxo_url'): 'https://cloud.ibm.com'
        }.get((section, *args))
        mock_config.return_value = mock_cfg_instance
        
        # Mock workspace doesn't exist
        workspaces_controller.workspace_context._resolve_workspace_name_to_id = Mock(return_value=None)
        mock_workspace_client.create.return_value = sample_workspace

        workspaces_controller.create_or_update_workspace(
            name="Marketing_Team_Workspace",
            description="Workspace for marketing automation"
        )

        mock_workspace_client.create.assert_called_once()

    @patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller.Config')
    def test_update_workspace_success(self, mock_config, workspaces_controller, mock_workspace_client):
        """Test successful workspace update"""
        # Mock IBM Cloud environment check
        mock_cfg_instance = Mock()
        mock_cfg_instance.get.side_effect = lambda section, *args: {
            ('context', 'active_environment'): 'prod',
            ('environments', 'prod', 'wxo_url'): 'https://cloud.ibm.com'
        }.get((section, *args))
        mock_config.return_value = mock_cfg_instance
        
        # Mock workspace exists
        workspaces_controller.workspace_context._resolve_workspace_name_to_id = Mock(return_value="workspace-123")
        mock_workspace_client.update.return_value = {}

        workspaces_controller.create_or_update_workspace(
            name="Marketing_Team_Workspace",
            description="Updated description"
        )

        mock_workspace_client.update.assert_called_once()


class TestWorkspacesDelete:
    """Tests for workspace delete command"""

    @patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller.typer.confirm')
    @patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller.Config')
    def test_remove_workspace_with_artifacts(self, mock_config, mock_confirm, workspaces_controller, mock_workspace_client):
        """Test deleting workspace and its artifacts"""
        # Mock IBM Cloud environment check
        mock_cfg_instance = Mock()
        mock_cfg_instance.get.side_effect = lambda section, *args: {
            ('context', 'active_environment'): 'prod',
            ('environments', 'prod', 'wxo_url'): 'https://cloud.ibm.com'
        }.get((section, *args))
        mock_config.return_value = mock_cfg_instance
        
        # Mock confirmation
        mock_confirm.return_value = True
        
        # Mock workspace exists
        workspaces_controller.workspace_context._resolve_workspace_name_to_id = Mock(return_value="workspace-123")
        mock_workspace_client.delete.return_value = {
            "status": "deleted",
            "workspace_id": "workspace-123"
        }

        workspaces_controller.remove_workspace(
            name="Marketing_Team_Workspace",
            delete_artifacts=True
        )

        mock_workspace_client.delete.assert_called_once_with("workspace-123", delete_artifacts=True)


class TestWorkspacesActivate:
    """Tests for workspace activate command"""

    @patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller.Config')
    def test_activate_workspace_by_name(self, mock_config, workspaces_controller):
        """Test activating workspace by name"""
        # Mock IBM Cloud environment check
        mock_cfg_instance = Mock()
        mock_cfg_instance.get.side_effect = lambda section, *args: {
            ('context', 'active_environment'): 'prod',
            ('environments', 'prod', 'wxo_url'): 'https://cloud.ibm.com'
        }.get((section, *args))
        mock_cfg_instance.write = Mock()
        mock_config.return_value = mock_cfg_instance
        
        # Mock workspace exists
        workspaces_controller.workspace_context._resolve_workspace_name_to_id = Mock(return_value="workspace-123")

        workspaces_controller.activate_workspace(name="Marketing_Team_Workspace")

        mock_cfg_instance.write.assert_called_once_with("context", "active_workspace", "Marketing_Team_Workspace")


class TestWorkspaceMembers:
    """Tests for workspace member management"""

    @patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller.Config')
    @patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller.jwt')
    def test_add_member(self, mock_jwt, mock_config, workspaces_controller, mock_workspace_client):
        """Test adding member to workspace"""

        mock_auth_cfg = Mock()
        mock_auth_cfg.get.return_value = {'prod': {'wxo_mcsp_token': 'fake-token'}}
        
        mock_cfg_instance = Mock()
        mock_cfg_instance.get.side_effect = lambda section, *args: {
            ('context', 'active_environment'): 'prod',
            ('environments', 'prod', 'wxo_url'): 'https://cloud.ibm.com'
        }.get((section, *args))
        mock_cfg_instance.read.return_value = 'prod'
        
        # Config() is called multiple times: _check_ibm_cloud_env, _get_account_id (twice)
        # Return auth_cfg for first call (with args), cfg_instance for others (no args)
        def config_side_effect(*args, **kwargs):
            if args:  # Called with AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE
                return mock_auth_cfg
            else:  # Called without args
                return mock_cfg_instance
        
        mock_config.side_effect = config_side_effect
        
        mock_jwt.decode.return_value = {'account': {'bss': 'account-123'}}
        
        workspaces_controller.workspace_context._resolve_workspace_name_to_id = Mock(return_value="workspace-123")
        
        mock_workspace_client.resolve_user_email_to_id.return_value = "IBMid-123"
        
        # Mock member list (user doesn't exist)
        mock_workspace_client.list_members.return_value = []
        
        # Mock add member
        mock_workspace_client.add_member.return_value = {
            "results": [{"user_id": "IBMid-123", "success": True}],
            "total": 1,
            "successful": 1,
            "failed": 0
        }

        workspaces_controller.add_or_update_member(
            workspace_name="Marketing_Team_Workspace",
            user_email="user@example.com",
            role=WorkspaceRole.EDITOR
        )

        mock_workspace_client.add_member.assert_called_once()

    @patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller.Config')
    def test_list_members(self, mock_config, workspaces_controller, mock_workspace_client):
        """Test listing workspace members"""
        mock_cfg_instance = Mock()
        mock_cfg_instance.get.side_effect = lambda section, *args: {
            ('context', 'active_environment'): 'prod',
            ('environments', 'prod', 'wxo_url'): 'https://cloud.ibm.com'
        }.get((section, *args))
        mock_config.return_value = mock_cfg_instance
        
        workspaces_controller.workspace_context._resolve_workspace_name_to_id = Mock(return_value="workspace-123")
        
        mock_workspace_client.list_members.return_value = [
            {"user_id": "IBMid-123", "role": "owner", "email": "user1@example.com"},
            {"user_id": "IBMid-456", "role": "editor", "email": "user2@example.com"}
        ]

        workspaces_controller.list_members(workspace_name="Marketing_Team_Workspace")

        mock_workspace_client.list_members.assert_called_once_with("workspace-123")

    @patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller.Config')
    @patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller.jwt')
    def test_remove_member(self, mock_jwt, mock_config, workspaces_controller, mock_workspace_client):
        """Test removing member from workspace"""

        mock_auth_cfg = Mock()
        mock_auth_cfg.get.return_value = {'prod': {'wxo_mcsp_token': 'fake-token'}}
        
        # Mock main config (for default Config())
        mock_cfg_instance = Mock()
        mock_cfg_instance.get.side_effect = lambda section, *args: {
            ('context', 'active_environment'): 'prod',
            ('environments', 'prod', 'wxo_url'): 'https://cloud.ibm.com'
        }.get((section, *args))
        mock_cfg_instance.read.return_value = 'prod'
        
        def config_side_effect(*args, **kwargs):
            if args:  # Called with AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE
                return mock_auth_cfg
            else:  # Called without args
                return mock_cfg_instance
        
        mock_config.side_effect = config_side_effect
        
        mock_jwt.decode.return_value = {'account': {'bss': 'account-123'}}
        
        workspaces_controller.workspace_context._resolve_workspace_name_to_id = Mock(return_value="workspace-123")
        
        mock_workspace_client.resolve_user_email_to_id.return_value = "IBMid-123"
        
        # Mock remove member
        mock_workspace_client.remove_member.return_value = {
            "results": [{"user_id": "IBMid-123", "success": True}],
            "total": 1,
            "successful": 1,
            "failed": 0
        }

        workspaces_controller.remove_member(
            workspace_name="Marketing_Team_Workspace",
            user_email="user@example.com"
        )

        mock_workspace_client.remove_member.assert_called_once()


class TestWorkspaceExport:
    """Tests for workspace export command"""

    @patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller.zipfile.ZipFile')
    @patch('ibm_watsonx_orchestrate.cli.commands.agents.agents_controller.AgentsController')
    @patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller.ToolsController')
    @patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller.ToolkitController')
    @patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller.KnowledgeBaseController')
    def test_export_workspace(self, mock_kb_controller, mock_toolkit_controller, mock_tools_controller,
                             mock_agents_controller, mock_zipfile, workspaces_controller):
        """Test exporting workspace"""
        # Mock workspace resolution
        workspaces_controller.workspace_context._resolve_workspace_name_to_id = Mock(return_value="workspace-123")
        
        # Mock workspace activation/deactivation methods
        workspaces_controller.activate_workspace = Mock()
        workspaces_controller.deactivate_workspace = Mock()
        
        mock_agents_ctrl = Mock()
        mock_agents_ctrl._fetch_and_parse_agents.return_value = ([], None)
        mock_agents_controller.return_value = mock_agents_ctrl
        
        mock_tools_ctrl = Mock()
        mock_tools_ctrl.get_client().get.return_value = []
        mock_tools_controller.return_value = mock_tools_ctrl
        
        mock_toolkit_ctrl = Mock()
        mock_toolkit_ctrl._fetch_and_parse_toolkits.return_value = ([], None)
        mock_toolkit_controller.return_value = mock_toolkit_ctrl
        
        mock_kb_ctrl = Mock()
        mock_kb_ctrl.get_client().get.return_value = []
        mock_kb_controller.return_value = mock_kb_ctrl
        
        # Mock zipfile
        mock_zip = Mock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip

        workspaces_controller.export_workspace(
            workspace_name="Marketing_Team_Workspace",
            output_path="/tmp/export.zip"
        )

        mock_zipfile.assert_called_once_with("/tmp/export.zip", "w")
