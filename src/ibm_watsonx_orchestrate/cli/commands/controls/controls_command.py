import typer
from typing import List
from typing_extensions import Annotated, Optional
from pathlib import Path
import logging

from ibm_watsonx_orchestrate.cli.commands.controls.controls_controller import ControlsController

logger = logging.getLogger(__name__)

controls_app = typer.Typer(no_args_is_help=True)


@controls_app.command(name="create", help="Create a control by binding a policy artifact to agents, tools, or models")
def create_control(
    artifact_name: Annotated[
        str,
        typer.Option(
            "--artifact", "-a",
            help="Name or display name of the policy artifact to bind (e.g., 'PII Filter', 'pii_filter'). Run 'orchestrate controls list-types' to see available artifacts."
        )
    ],
    name: Annotated[
        str,
        typer.Option(
            "--name", "-n",
            help="Internal name for this control binding"
        )
    ],
    display_name: Annotated[
        Optional[str],
        typer.Option(
            "--display-name",
            help="Display name for this control (defaults to name if not provided)"
        )
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option(
            "--description", "-d",
            help="Description of what this control does"
        )
    ] = None,
    hooks: Annotated[
        Optional[List[str]],
        typer.Option(
            "--hooks", "--hook",
            help="Execution hooks (e.g., agent_pre_invoke, agent_post_invoke, tool_pre_invoke, tool_post_invoke, prompt_pre_fetch, prompt_post_fetch). Can specify multiple times."
        )
    ] = None,
    priority: Annotated[
        int,
        typer.Option(
            "--priority", "-p",
            help="Execution priority (default: 100). Lower numbers execute first."
        )
    ] = 100,
    config: Annotated[
        Optional[str],
        typer.Option(
            "--config",
            help="JSON string with artifact-specific configuration (e.g., '{\"action\": \"redact\"}')"
        )
    ] = None,
    agent_names: Annotated[
        Optional[List[str]],
        typer.Option(
            "--agent",
            help="Agent name(s) to bind this control to. Can specify multiple times."
        )
    ] = None,
    tool_names: Annotated[
        Optional[List[str]],
        typer.Option(
            "--tool",
            help="Tool name(s) to bind this control to. Can specify multiple times."
        )
    ] = None,
    model_names: Annotated[
        Optional[List[str]],
        typer.Option(
            "--model",
            help="Model name(s) to bind this control to. Can specify multiple times."
        )
    ] = None,
):
    """
    Create a control by binding a policy artifact to one or more agents, tools, or models.

    Example:
        orchestrate controls create --artifact "PII Filter" --name "My PII Control" \\
            --agent my-agent --hooks agent_pre_invoke --priority 100
    """
    controller = ControlsController()
    controller.create_control(
        artifact_name=artifact_name,
        name=name,
        display_name=display_name,
        description=description,
        hooks=hooks,
        priority=priority,
        config=config,
        agent_names=agent_names,
        tool_names=tool_names,
        model_names=model_names
    )


@controls_app.command(name="list", help="List all controls, optionally filtered by agent, tool, or model")
def list_controls(
    agent_name: Annotated[
        Optional[str],
        typer.Option(
            "--agent",
            help="Filter controls by agent name"
        )
    ] = None,
    tool_name: Annotated[
        Optional[str],
        typer.Option(
            "--tool",
            help="Filter controls by tool name"
        )
    ] = None,
    model_name: Annotated[
        Optional[str],
        typer.Option(
            "--model",
            help="Filter controls by model name"
        )
    ] = None,
    artifact_name: Annotated[
        Optional[str],
        typer.Option(
            "--artifact",
            help="Filter controls by artifact name or display name"
        )
    ] = None,
    sort: Annotated[
        str,
        typer.Option(
            "--sort",
            help="Sort order: 'recent' (updated_at desc), 'asc' (created_on asc), 'desc' (created_on desc)"
        )
    ] = "recent",
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-v",
            help="Show full control details in JSON format"
        )
    ] = False,
):
    """
    List all controls with optional filtering.

    Example:
        orchestrate controls list --agent my-agent
        orchestrate controls list --sort recent --verbose
    """
    controller = ControlsController()
    controller.list_controls(
        agent_name=agent_name,
        tool_name=tool_name,
        model_name=model_name,
        artifact_name=artifact_name,
        sort=sort,
        verbose=verbose
    )


@controls_app.command(name="count", help="Get count of controls by asset type")
def count_controls():
    """
    Get the count of controls grouped by asset type (agents, tools, models).

    Example:
        orchestrate controls count
    """
    controller = ControlsController()
    controller.count_controls()


@controls_app.command(name="get-details", help="Get details of a specific control")
def get_control(
    control_name: Annotated[
        str,
        typer.Option(
            "--name", "-n",
            help="Name of the control to retrieve (shown in 'controls list')"
        )
    ],
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-v",
            help="Show full control details in JSON format"
        )
    ] = False,
):
    """
    Get detailed information about a specific control.

    Example:
        orchestrate controls get-details --name asdf_06650U
    """
    controller = ControlsController()
    controller.get_control(control_name, verbose)


@controls_app.command(name="update", help="Update an existing control")
def update_control(
    control_name: Annotated[
        str,
        typer.Option(
            "--name", "-n",
            help="Name of the control to update (shown in 'controls list')"
        )
    ],
    artifact_name: Annotated[
        Optional[str],
        typer.Option(
            "--artifact",
            help="New artifact name or display name to bind to (e.g., 'PII Filter', 'pii_filter')"
        )
    ] = None,
    new_name: Annotated[
        Optional[str],
        typer.Option(
            "--new-name",
            help="New internal name"
        )
    ] = None,
    display_name: Annotated[
        Optional[str],
        typer.Option(
            "--display-name",
            help="New display name"
        )
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option(
            "--description", "-d",
            help="New description"
        )
    ] = None,
    hooks: Annotated[
        Optional[List[str]],
        typer.Option(
            "--hooks", "--hook",
            help="New execution hooks. Replaces existing hooks. Can specify multiple times."
        )
    ] = None,
    priority: Annotated[
        Optional[int],
        typer.Option(
            "--priority", "-p",
            help="New execution priority"
        )
    ] = None,
    config: Annotated[
        Optional[str],
        typer.Option(
            "--config",
            help="New JSON configuration string"
        )
    ] = None,
    agent_names: Annotated[
        Optional[List[str]],
        typer.Option(
            "--agent",
            help="New agent name(s). Replaces existing agent bindings. Can specify multiple times."
        )
    ] = None,
    tool_names: Annotated[
        Optional[List[str]],
        typer.Option(
            "--tool",
            help="New tool name(s). Replaces existing tool bindings. Can specify multiple times."
        )
    ] = None,
    model_names: Annotated[
        Optional[List[str]],
        typer.Option(
            "--model",
            help="New model name(s). Replaces existing model bindings. Can specify multiple times."
        )
    ] = None,
):
    """
    Update an existing control. Only provided fields will be updated.

    Note: When updating asset names (agents, tools, models), the provided list
    replaces the existing bindings for that asset type.

    Example:
        orchestrate controls update --name asdf_06650U --priority 50 --hooks agent_post_invoke
    """
    controller = ControlsController()
    controller.update_control(
        control_name=control_name,
        artifact_name=artifact_name,
        name=new_name,
        display_name=display_name,
        description=description,
        hooks=hooks,
        priority=priority,
        config=config,
        agent_names=agent_names,
        tool_names=tool_names,
        model_names=model_names
    )


@controls_app.command(name="remove", help="Remove a control")
def remove_control(
    control_name: Annotated[
        str,
        typer.Option(
            "--name", "-n",
            help="Name of the control to remove (shown in 'controls list')"
        )
    ],
):
    """
    Remove a control and all of its associated bindings.

    Example:
        orchestrate controls remove --name asdf_06650U
    """
    controller = ControlsController()
    controller.remove_control(control_name)


@controls_app.command(name="import", help="Import controls from a file")
def import_controls(
    file: Annotated[
        Path,
        typer.Option(
            "--file", "-f",
            help="Path to YAML or JSON file containing control definitions",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True
        )
    ],
):
    """
    Import one or more controls from a YAML or JSON file.

    Example:
        orchestrate controls import --file controls.yaml
    """
    controller = ControlsController()
    controller.import_controls(file)


@controls_app.command(name="export", help="Export a control to a file")
def export_control(
    control_name: Annotated[
        str,
        typer.Option(
            "--name", "-n",
            help="Name of the control to export (shown in 'controls list')"
        )
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output", "-o",
            help="Path where the exported control should be saved (YAML format)"
        )
    ],
):
    """
    Export a control to a YAML file.

    Example:
        orchestrate controls export --name asdf_06650U --output control.yaml
    """
    controller = ControlsController()
    controller.export_control(control_name, output)


@controls_app.command(name="list-types", help="List available policy artifact types")
def list_artifact_types(
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-v",
            help="Show full artifact details in JSON format"
        )
    ] = False,
):
    """
    List all available policy artifact types (e.g., PII Filter, Content Guardrails).
    These are the artifacts that can be bound to assets when creating controls.

    Example:
        orchestrate controls list-types
    """
    controller = ControlsController()
    controller.list_artifact_types(verbose)


@controls_app.command(name="get-type", help="Get details of a specific policy artifact type")
def get_artifact_type(
    artifact_name: Annotated[
        str,
        typer.Option(
            "--name", "-n",
            help="Name or display name of the artifact type to retrieve (e.g., 'PII Filter', 'pii_filter')"
        )
    ],
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-v",
            help="Show full artifact details in JSON format"
        )
    ] = False,
):
    """
    Get detailed information about a specific policy artifact type.

    Example:
        orchestrate controls get-type --name "PII Filter"
        orchestrate controls get-type --name pii_filter
    """
    controller = ControlsController()
    controller.get_artifact_type(artifact_name, verbose)
