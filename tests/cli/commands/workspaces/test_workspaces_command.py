import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_command import workspaces_app
from ibm_watsonx_orchestrate.agent_builder.workspaces.types import WorkspaceRole


@pytest.fixture
def runner():
    """Create CLI test runner"""
    return CliRunner()


@pytest.fixture
def mock_controller():
    """Mock WorkspacesController"""
    with patch('ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_command.WorkspacesController') as mock:
        yield mock.return_value


class TestWorkspacesListCommand:
    """Tests for 'wxo workspaces list' command"""

    def test_list_command_basic(self, runner, mock_controller):
        """Test basic list command"""
        result = runner.invoke(workspaces_app, ['list'])
        
        assert result.exit_code == 0
        mock_controller.list_workspaces.assert_called_once_with(verbose=False)

    def test_list_command_verbose(self, runner, mock_controller):
        """Test list command with --verbose option"""
        result = runner.invoke(workspaces_app, ['list', '--verbose'])
        
        assert result.exit_code == 0
        mock_controller.list_workspaces.assert_called_once_with(verbose=True)


class TestWorkspacesCreateCommand:
    """Tests for 'wxo workspaces create' command"""

    def test_create_command_with_name(self, runner, mock_controller):
        """Test create command with name"""
        result = runner.invoke(workspaces_app, ['create', '--name', 'Marketing_Team_Workspace'])
        
        assert result.exit_code == 0
        mock_controller.create_or_update_workspace.assert_called_once_with(
            name='Marketing_Team_Workspace',
            description=None
        )

    def test_create_command_with_description(self, runner, mock_controller):
        """Test create command with name and description"""
        result = runner.invoke(workspaces_app, [
            'create',
            '--name', 'Marketing_Team_Workspace',
            '--description', 'Workspace for marketing automation'
        ])
        
        assert result.exit_code == 0
        mock_controller.create_or_update_workspace.assert_called_once_with(
            name='Marketing_Team_Workspace',
            description='Workspace for marketing automation'
        )

    def test_create_command_missing_name(self, runner, mock_controller):
        """Test create command without required name"""
        result = runner.invoke(workspaces_app, ['create'])
        
        assert result.exit_code != 0
        assert 'Missing option' in result.output or 'required' in result.output.lower()


class TestWorkspacesRemoveCommand:
    """Tests for 'wxo workspaces remove' command"""

    def test_remove_command_delete_artifacts(self, runner, mock_controller):
        """Test remove command with delete-artifacts flag"""
        result = runner.invoke(workspaces_app, [
            'remove',
            '--name', 'Marketing_Team_Workspace',
            '--delete-artifacts'
        ])
        
        assert result.exit_code == 0
        mock_controller.remove_workspace.assert_called_once_with(
            name='Marketing_Team_Workspace',
            delete_artifacts=True
        )

    def test_remove_command_keep_artifacts(self, runner, mock_controller):
        """Test remove command with keep-artifacts flag"""
        result = runner.invoke(workspaces_app, [
            'remove',
            '--name', 'Marketing_Team_Workspace',
            '--keep-artifacts'
        ])
        
        assert result.exit_code == 0
        mock_controller.remove_workspace.assert_called_once_with(
            name='Marketing_Team_Workspace',
            delete_artifacts=False
        )

    def test_remove_command_default_behavior(self, runner, mock_controller):
        """Test remove command default behavior (deletes artifacts)"""
        result = runner.invoke(workspaces_app, [
            'remove',
            '--name', 'Marketing_Team_Workspace'
        ])
        
        assert result.exit_code == 0
        mock_controller.remove_workspace.assert_called_once_with(
            name='Marketing_Team_Workspace',
            delete_artifacts=True
        )


class TestWorkspacesActivateCommand:
    """Tests for 'wxo workspaces activate' command"""

    def test_activate_command(self, runner, mock_controller):
        """Test activate command"""
        result = runner.invoke(workspaces_app, ['activate', 'Marketing_Team_Workspace'])
        
        assert result.exit_code == 0
        mock_controller.activate_workspace.assert_called_once_with(name='Marketing_Team_Workspace')

    def test_activate_command_missing_name(self, runner, mock_controller):
        """Test activate command without workspace name"""
        result = runner.invoke(workspaces_app, ['activate'])
        
        assert result.exit_code != 0


class TestWorkspacesDeactivateCommand:
    """Tests for 'wxo workspaces deactivate' command"""

    def test_deactivate_command(self, runner, mock_controller):
        """Test deactivate command"""
        result = runner.invoke(workspaces_app, ['deactivate'])
        
        assert result.exit_code == 0
        mock_controller.deactivate_workspace.assert_called_once()


class TestWorkspacesExportCommand:
    """Tests for 'wxo workspaces export' command"""

    def test_export_command_basic(self, runner, mock_controller):
        """Test basic export command with default output"""
        result = runner.invoke(workspaces_app, ['export'])
        
        assert result.exit_code == 0
        mock_controller.export_workspace.assert_called_once_with(
            workspace_name=None,
            output_path='workspace_export.zip'
        )

    def test_export_command_with_name(self, runner, mock_controller):
        """Test export command with workspace name"""
        result = runner.invoke(workspaces_app, [
            'export',
            '--name', 'Marketing_Team_Workspace',
            '--output', './export.zip'
        ])
        
        assert result.exit_code == 0
        mock_controller.export_workspace.assert_called_once_with(
            workspace_name='Marketing_Team_Workspace',
            output_path='./export.zip'
        )


class TestWorkspacesMembersCommands:
    """Tests for workspace member management commands"""

    def test_add_member_command(self, runner, mock_controller):
        """Test members add command"""
        result = runner.invoke(workspaces_app, [
            'members', 'add',
            '--user', 'user@example.com',
            '--role', 'editor'
        ])
        
        assert result.exit_code == 0
        mock_controller.add_or_update_member.assert_called_once_with(
            workspace_name=None,
            user_email='user@example.com',
            role=WorkspaceRole.EDITOR
        )

    def test_add_member_command_with_workspace(self, runner, mock_controller):
        """Test members add command with workspace name"""
        result = runner.invoke(workspaces_app, [
            'members', 'add',
            '--user', 'user@example.com',
            '--role', 'owner',
            '--name', 'Marketing_Team_Workspace'
        ])
        
        assert result.exit_code == 0
        mock_controller.add_or_update_member.assert_called_once_with(
            workspace_name='Marketing_Team_Workspace',
            user_email='user@example.com',
            role=WorkspaceRole.OWNER
        )

    def test_list_members_command(self, runner, mock_controller):
        """Test members list command"""
        result = runner.invoke(workspaces_app, ['members', 'list'])
        
        assert result.exit_code == 0
        mock_controller.list_members.assert_called_once_with(
            workspace_name=None,
            verbose=False
        )

    def test_list_members_command_with_workspace(self, runner, mock_controller):
        """Test members list command with workspace name"""
        result = runner.invoke(workspaces_app, [
            'members', 'list',
            '--name', 'Marketing_Team_Workspace',
            '--verbose'
        ])
        
        assert result.exit_code == 0
        mock_controller.list_members.assert_called_once_with(
            workspace_name='Marketing_Team_Workspace',
            verbose=True
        )

    def test_remove_member_command(self, runner, mock_controller):
        """Test members remove command"""
        result = runner.invoke(workspaces_app, [
            'members', 'remove',
            '--user', 'user@example.com'
        ])
        
        assert result.exit_code == 0
        mock_controller.remove_member.assert_called_once_with(
            workspace_name=None,
            user_email='user@example.com'
        )

    def test_remove_member_command_with_workspace(self, runner, mock_controller):
        """Test members remove command with workspace name"""
        result = runner.invoke(workspaces_app, [
            'members', 'remove',
            '--user', 'user@example.com',
            '--name', 'Marketing_Team_Workspace'
        ])
        
        assert result.exit_code == 0
        mock_controller.remove_member.assert_called_once_with(
            workspace_name='Marketing_Team_Workspace',
            user_email='user@example.com'
        )


class TestWorkspacesHelpCommand:
    """Tests for workspace command help"""

    def test_workspaces_help(self, runner):
        """Test workspaces command help"""
        result = runner.invoke(workspaces_app, ['--help'])
        
        assert result.exit_code == 0
        assert 'create' in result.output
        assert 'list' in result.output
        assert 'remove' in result.output

    def test_list_help(self, runner):
        """Test list subcommand help"""
        result = runner.invoke(workspaces_app, ['list', '--help'])
        
        assert result.exit_code == 0
        assert 'list' in result.output.lower()

    def test_create_help(self, runner):
        """Test create subcommand help"""
        result = runner.invoke(workspaces_app, ['create', '--help'])
        
        assert result.exit_code == 0
        assert 'create' in result.output.lower()
        assert 'name' in result.output.lower()

    def test_members_help(self, runner):
        """Test members subcommand help"""
        result = runner.invoke(workspaces_app, ['members', '--help'])
        
        assert result.exit_code == 0
        assert 'add' in result.output
        assert 'list' in result.output
        assert 'remove' in result.output
