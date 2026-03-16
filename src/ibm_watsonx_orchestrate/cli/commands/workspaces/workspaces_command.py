import typer
from typing import Optional
from typing_extensions import Annotated
from ibm_watsonx_orchestrate.cli.commands.workspaces.workspaces_controller import WorkspacesController
from ibm_watsonx_orchestrate.agent_builder.workspaces.types import WorkspaceRole
import logging

logger = logging.getLogger(__name__)

workspaces_app = typer.Typer(no_args_is_help=True)

# ==================== WORKSPACE CRUD COMMANDS ====================

@workspaces_app.command(name="create", help="Create or update a workspace.")
def create_workspace(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the workspace (must be unique within tenant)"),
    ],
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Description of the workspace"),
    ] = None,
):
    controller = WorkspacesController()
    controller.create_or_update_workspace(name=name, description=description)


@workspaces_app.command(name="list", help="List all workspaces with activation status")
def list_workspaces(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show full details of all workspaces as JSON"),
    ] = False,
):
    controller = WorkspacesController()
    controller.list_workspaces(verbose=verbose)


@workspaces_app.command(name="remove", help="Remove a workspace")
def remove_workspace(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the workspace to remove"),
    ],
    delete_artifacts: Annotated[
        bool,
        typer.Option("--delete-artifacts", help="Delete all workspace artifacts"),
    ] = False,
    keep_artifacts: Annotated[
        bool,
        typer.Option("--keep-artifacts", help="Move artifacts to global workspace"),
    ] = False,
):
    if delete_artifacts and keep_artifacts:
        logger.error("Cannot specify both --delete-artifacts and --keep-artifacts")
        raise typer.Exit(1)
    
    # Default to delete_artifacts if neither flag is specified
    should_delete = delete_artifacts or not keep_artifacts
    
    controller = WorkspacesController()
    controller.remove_workspace(name=name, delete_artifacts=should_delete)


@workspaces_app.command(name="activate", help="Activate a workspace")
def activate_workspace(
    name: Annotated[
        str,
        typer.Argument(help="Name of the workspace to activate"),
    ],
):
    controller = WorkspacesController()
    controller.activate_workspace(name=name)


@workspaces_app.command(name="deactivate", help="Deactivate current workspace (reset to global)")
def deactivate_workspace():
    controller = WorkspacesController()
    controller.deactivate_workspace()


@workspaces_app.command(name="export", help="Export all workspace resources to a zip file")
def export_workspace(
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Workspace name (uses active workspace if not specified)"),
    ] = None,
    output_file: Annotated[
        str,
        typer.Option("--output", "-o", help="Path to the output zip file"),
    ] = "workspace_export.zip",
):
    controller = WorkspacesController()
    controller.export_workspace(workspace_name=name, output_path=output_file)


# ==================== WORKSPACE MEMBER COMMANDS ====================

members_app = typer.Typer(no_args_is_help=True, help="Manage workspace members")
workspaces_app.add_typer(members_app, name="members")


@members_app.command(name="add", help="Add or update a member in a workspace.")
def add_member(
    user: Annotated[
        str,
        typer.Option("--user", "-u", help="User email address"),
    ],
    role: Annotated[
        WorkspaceRole,
        typer.Option("--role", "-r", help="Role to assign: owner or editor"),
    ],
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Workspace name (uses active workspace if not specified)"),
    ] = None,
):
    controller = WorkspacesController()
    controller.add_or_update_member(workspace_name=name, user_email=user, role=role)


@members_app.command(name="list", help="List all members in a workspace")
def list_members(
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Workspace name (uses active workspace if not specified)"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show full details as JSON"),
    ] = False,
):
    controller = WorkspacesController()
    controller.list_members(workspace_name=name, verbose=verbose)


@members_app.command(name="remove", help="Remove a member from a workspace")
def remove_member(
    user: Annotated[
        str,
        typer.Option("--user", "-u", help="User email address to remove"),
    ],
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Workspace name (uses active workspace if not specified)"),
    ] = None,
):
    controller = WorkspacesController()
    controller.remove_member(workspace_name=name, user_email=user)