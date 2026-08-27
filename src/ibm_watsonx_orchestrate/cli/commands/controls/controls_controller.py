import logging
import sys
import json
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any

import rich
import rich.table
from rich.console import Console
from rich.json import JSON

from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.cli.common import ListFormats, rich_table_to_markdown
from ibm_watsonx_orchestrate_core.types.spec.types import SpecVersion
from ibm_watsonx_orchestrate_clients.controls.controls_client import ControlsClient
from ibm_watsonx_orchestrate_clients.agents.agent_client import AgentClient
from ibm_watsonx_orchestrate_clients.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate_clients.models.models_client import ModelsClient
from ibm_watsonx_orchestrate_clients.common.base_client import ClientAPIException

logger = logging.getLogger(__name__)
console = Console()


class ControlsController:
    """
    Controller for managing policy controls (bindings) via CLI.
    Handles business logic and formatting for the controls commands.
    """

    def __init__(self):
        self.client = None
        self.agent_client = None
        self.tool_client = None
        self.model_client = None

    def get_client(self) -> ControlsClient:
        """Get or create the ControlsClient instance."""
        if not self.client:
            self.client = instantiate_client(ControlsClient)
        return self.client

    def get_agent_client(self) -> AgentClient:
        """Get or create the AgentClient instance."""
        if not self.agent_client:
            self.agent_client = instantiate_client(AgentClient)
        return self.agent_client

    def get_tool_client(self) -> ToolClient:
        """Get or create the ToolClient instance."""
        if not self.tool_client:
            self.tool_client = instantiate_client(ToolClient)
        return self.tool_client

    def get_model_client(self) -> ModelsClient:
        """Get or create the ModelsClient instance."""
        if not self.model_client:
            self.model_client = instantiate_client(ModelsClient)
        return self.model_client

    def _resolve_control_id(self, name: str) -> str:
        """
        Resolve a control name slug to its UUID.

        Matches on the ``name`` field only (the auto-generated slug shown in
        ``controls list``), consistent with how other CLI commands (e.g. agents)
        identify resources by their unique name slug.

        Args:
            name: The control name slug (e.g. ``my_control_06650U``).

        Returns:
            The binding UUID string.
        """
        client = self.get_client()
        try:
            result = client.list_bindings()
        except ClientAPIException as e:
            logger.error(f"Failed to look up controls: {e}")
            sys.exit(1)

        bindings = result.get("bindings", [])

        for binding in bindings:
            if binding.get("name") == name:
                return binding["id"]

        logger.error(
            f"No control found with name '{name}'. "
            f"Run 'orchestrate controls list' to see available controls."
        )
        sys.exit(1)

    def _resolve_asset_names(self, asset_ids: List[str], asset_type: str) -> List[Dict[str, str]]:
        """
        Resolve asset IDs to names.

        Args:
            asset_ids: List of asset IDs to resolve
            asset_type: Type of asset ('agent', 'tool', or 'model')

        Returns:
            List of dicts with 'id' and 'name' keys
        """
        if not asset_ids:
            return []

        results = []
        try:
            if asset_type == 'agent':
                client = self.get_agent_client()
                agents = client.get_drafts_by_ids(asset_ids)
                for agent in agents:
                    results.append({
                        'id': agent.get('id'),
                        'name': agent.get('display_name') or agent.get('name', 'Unknown')
                    })
            elif asset_type == 'tool':
                client = self.get_tool_client()
                tools = client.get_drafts_by_ids(asset_ids)
                for tool in tools:
                    results.append({
                        'id': tool.get('id'),
                        'name': tool.get('display_name') or tool.get('name', 'Unknown')
                    })
            elif asset_type == 'model':
                client = self.get_model_client()
                models = client.get_drafts_by_ids(asset_ids)
                for model in models:
                    results.append({
                        'id': model.get('id'),
                        'name': model.get('display_name') or model.get('name', 'Unknown')
                    })
        except Exception as e:
            logger.warning(f"Failed to resolve {asset_type} names: {e}")
            # Return IDs only if resolution fails
            for asset_id in asset_ids:
                results.append({
                    'id': asset_id,
                    'name': asset_id
                })

        return results

    def _resolve_agent_names_to_ids(self, names: List[str]) -> List[str]:
        """
        Resolve a list of agent names to their UUIDs.
        Exits with an error if any name cannot be resolved.
        """
        client = self.get_agent_client()
        try:
            agents = client.get_drafts_by_names(names)
        except Exception as e:
            logger.error(f"Failed to look up agents: {e}")
            sys.exit(1)

        name_to_id = {a.get("name"): a.get("id") for a in agents if a.get("name")}
        ids = []
        for name in names:
            agent_id = name_to_id.get(name)
            if not agent_id:
                logger.error(
                    f"No agent found with name '{name}'. "
                    f"Run 'orchestrate agents list' to see available agents."
                )
                sys.exit(1)
            ids.append(agent_id)
        return ids

    def _resolve_tool_names_to_ids(self, names: List[str]) -> List[str]:
        """
        Resolve a list of tool names to their UUIDs.
        Exits with an error if any name cannot be resolved.
        """
        client = self.get_tool_client()
        try:
            tools = client.get_drafts_by_names(names)
        except Exception as e:
            logger.error(f"Failed to look up tools: {e}")
            sys.exit(1)

        name_to_id = {t.get("name"): t.get("id") for t in tools if t.get("name")}
        ids = []
        for name in names:
            tool_id = name_to_id.get(name)
            if not tool_id:
                logger.error(
                    f"No tool found with name '{name}'. "
                    f"Run 'orchestrate tools list' to see available tools."
                )
                sys.exit(1)
            ids.append(tool_id)
        return ids

    # ==================== Artifact Operations ====================

    def _resolve_artifact_id(self, name_or_display: str) -> str:
        """
        Resolve a policy artifact name or display name to its UUID.

        Matches against both ``name`` (e.g. ``pii_filter``) and
        ``display_name`` (e.g. ``PII Filter``) in a single pass.
        The artifact catalog is platform-owned and small, so name/display_name
        collisions across artifacts are not a concern.

        Args:
            name_or_display: The artifact name or display name supplied by the user.

        Returns:
            The artifact UUID string.
        """
        client = self.get_client()
        try:
            artifacts = client.list_artifacts()
        except ClientAPIException as e:
            logger.error(f"Failed to look up policy artifacts: {e}")
            sys.exit(1)

        for artifact in artifacts:
            if name_or_display in (artifact.get("name"), artifact.get("display_name")):
                return artifact["id"]

        logger.error(
            f"No policy artifact found with name or display name '{name_or_display}'. "
            f"Run 'orchestrate controls list-types' to see available artifacts."
        )
        sys.exit(1)

    def list_artifact_types(self, verbose: bool = False) -> None:
        """
        List all available policy artifact types, grouped by asset type.

        Args:
            verbose: If True, display full JSON details
        """
        client = self.get_client()

        try:
            artifacts = client.list_artifacts()

            if not artifacts:
                logger.info("No policy artifacts found")
                return

            if verbose:
                console.print(JSON(json.dumps(artifacts, indent=2)))
            else:
                # Group artifacts by asset type
                agent_artifacts = []
                tool_artifacts = []
                model_artifacts = []

                for artifact in artifacts:
                    asset_types = artifact.get("asset_type", [])
                    if "agent" in asset_types:
                        agent_artifacts.append(artifact)
                    if "tool" in asset_types:
                        tool_artifacts.append(artifact)
                    if "model" in asset_types:
                        model_artifacts.append(artifact)

                # Display Agent Artifacts
                if agent_artifacts:
                    console.print()
                    table = rich.table.Table(title="Agent Policy Artifact Types")
                    table.add_column("Display Name", style="yellow")
                    table.add_column("Name", style="cyan")
                    table.add_column("Description")

                    for artifact in agent_artifacts:
                        table.add_row(
                            artifact.get("display_name", ""),
                            artifact.get("name", ""),
                            artifact.get("description", "")
                        )

                    console.print(table)
                    logger.info(f"Agent artifacts: {len(agent_artifacts)}")

                # Display Tool Artifacts
                if tool_artifacts:
                    console.print()
                    table = rich.table.Table(title="Tool Policy Artifact Types")
                    table.add_column("Display Name", style="yellow")
                    table.add_column("Name", style="cyan")
                    table.add_column("Description")

                    for artifact in tool_artifacts:
                        table.add_row(
                            artifact.get("display_name", ""),
                            artifact.get("name", ""),
                            artifact.get("description", "")
                        )

                    console.print(table)
                    logger.info(f"Tool artifacts: {len(tool_artifacts)}")

                # Display Model Artifacts
                if model_artifacts:
                    console.print()
                    table = rich.table.Table(title="Model Policy Artifact Types")
                    table.add_column("Display Name", style="yellow")
                    table.add_column("Name", style="cyan")
                    table.add_column("Description")

                    for artifact in model_artifacts:
                        table.add_row(
                            artifact.get("display_name", ""),
                            artifact.get("name", ""),
                            artifact.get("description", "")
                        )

                    console.print(table)
                    logger.info(f"Model artifacts: {len(model_artifacts)}")

                console.print()

        except ClientAPIException as e:
            logger.error(f"Failed to list policy artifacts: {e}")
            sys.exit(1)

    def get_artifact_type(self, artifact_name: str, verbose: bool = False) -> None:
        """
        Get details of a specific policy artifact type.

        Args:
            artifact_name: The name or display name of the artifact to retrieve
            verbose: If True, display full JSON details
        """
        artifact_id = self._resolve_artifact_id(artifact_name)
        client = self.get_client()

        try:
            artifact = client.get_artifact(artifact_id)

            if not artifact:
                logger.error(f"Policy artifact '{artifact_name}' not found")
                sys.exit(1)

            if verbose:
                console.print(JSON(json.dumps(artifact, indent=2)))
            else:
                console.print(f"[bold cyan]Artifact ID:[/] {artifact.get('id')}")
                console.print(f"[bold cyan]Name:[/] {artifact.get('name')}")
                console.print(f"[bold cyan]Display Name:[/] {artifact.get('display_name')}")
                console.print(f"[bold cyan]Description:[/] {artifact.get('description')}")

                if artifact.get('config_schema'):
                    console.print(f"\n[bold cyan]Configuration Schema:[/]")
                    console.print(JSON(json.dumps(artifact.get('config_schema'), indent=2)))

        except ClientAPIException as e:
            logger.error(f"Failed to get policy artifact: {e}")
            sys.exit(1)

    # ==================== Control (Binding) Operations ====================

    def create_control(
        self,
        artifact_name: str,
        name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        hooks: Optional[List[str]] = None,
        priority: int = 100,
        config: Optional[str] = None,
        agent_names: Optional[List[str]] = None,
        tool_names: Optional[List[str]] = None,
        model_names: Optional[List[str]] = None,
    ) -> None:
        """
        Create a new control (policy binding).

        Args:
            artifact_name: Name or display name of the policy artifact to bind
            name: Internal name for the control
            display_name: Display name (defaults to name if not provided)
            description: Description of the control
            hooks: List of execution hooks
            priority: Execution priority (default: 100)
            config: JSON string with artifact-specific configuration
            agent_names: List of agent names to bind to (resolved to UUIDs)
            tool_names: List of tool names to bind to (resolved to UUIDs)
            model_names: List of model names to bind to (passed through; API accepts names directly)
        """
        artifact_id = self._resolve_artifact_id(artifact_name)
        client = self.get_client()

        # Build payload
        payload = {
            "artifact_id": artifact_id,
            "name": name,
            "priority": priority
        }

        if display_name:
            payload["display_name"] = display_name
        if description:
            payload["description"] = description
        if hooks:
            payload["hooks"] = hooks
        if config:
            try:
                payload["config"] = json.loads(config)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in config parameter: {e}")
                sys.exit(1)
        if agent_names:
            payload["agent_ids"] = self._resolve_agent_names_to_ids(agent_names)
        if tool_names:
            payload["tool_ids"] = self._resolve_tool_names_to_ids(tool_names)
        if model_names:
            payload["model_ids"] = model_names

        try:
            result = client.create_binding(payload)
            logger.info(f"Control created successfully with ID: {result.get('id')}")

        except ClientAPIException as e:
            logger.error(f"Failed to create control: {e}")
            sys.exit(1)

    def list_controls(
        self,
        agent_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        model_name: Optional[str] = None,
        artifact_name: Optional[str] = None,
        sort: str = "recent",
        verbose: bool = False
    ) -> None:
        """
        List controls with optional filtering.

        Args:
            agent_name: Filter by agent name
            tool_name: Filter by tool name
            model_name: Filter by model name (passed through; API accepts names directly)
            artifact_name: Filter by artifact name or display name
            sort: Sort order ('recent', 'asc', 'desc')
            verbose: If True, display full JSON details
        """
        client = self.get_client()

        try:
            artifact_id = self._resolve_artifact_id(artifact_name) if artifact_name else None
            resolved_agent_ids = self._resolve_agent_names_to_ids([agent_name]) if agent_name else None
            resolved_tool_ids = self._resolve_tool_names_to_ids([tool_name]) if tool_name else None
            result = client.list_bindings(
                agent_ids=resolved_agent_ids,
                tool_ids=resolved_tool_ids,
                model_ids=[model_name] if model_name else None,
                artifact_ids=[artifact_id] if artifact_id else None,
                sort=sort
            )

            bindings = result.get("bindings", [])
            total = result.get("total", 0)

            if not bindings:
                logger.info("No controls found")
                return

            if verbose:
                console.print(JSON(json.dumps(bindings, indent=2)))
            else:
                table = rich.table.Table(title="Controls")
                table.add_column("Name", style="cyan")
                table.add_column("Artifact", style="yellow")
                table.add_column("Hooks")
                table.add_column("Priority", justify="right")
                table.add_column("Assets")
                table.add_column("ID", style="dim")

                for binding in bindings:
                    name = binding.get("name", "")
                    display_name = binding.get("display_name", "")
                    combined = f"{name} ({display_name})" if display_name and name != display_name else name

                    agent_count = len(binding.get("agent_ids", []))
                    tool_count = len(binding.get("tool_ids", []))
                    model_count = len(binding.get("model_ids", []))
                    assets = f"A:{agent_count} T:{tool_count} M:{model_count}"

                    table.add_row(
                        combined,
                        binding.get("artifact_display_name", ""),
                        ", ".join(binding.get("hooks", [])),
                        str(binding.get("priority", "")),
                        assets,
                        binding.get("id", ""),
                    )

                console.print(table)
                logger.info(f"Total controls: {total}")

        except ClientAPIException as e:
            logger.error(f"Failed to list controls: {e}")
            sys.exit(1)

    def count_controls(self) -> None:
        """Get count of controls by asset type."""
        client = self.get_client()

        try:
            counts = client.get_bindings_count()

            console.print("\n[bold]Control Counts by Asset Type:[/]")
            console.print(f"  Agent Controls: {counts.get('agent_policies', 0)}")
            console.print(f"  Tool Controls: {counts.get('tool_policies', 0)}")
            console.print(f"  Model Controls: {counts.get('model_policies', 0)}")
            console.print(f"  [bold]Total Controls: {counts.get('total_policies', 0)}[/]\n")

        except ClientAPIException as e:
            logger.error(f"Failed to get control counts: {e}")
            sys.exit(1)

    def get_control(self, control_name: str, verbose: bool = False) -> None:
        """
        Get details of a specific control.

        Args:
            control_name: The display name or name slug of the control to retrieve
            verbose: If True, display full JSON details
        """
        control_id = self._resolve_control_id(control_name)
        client = self.get_client()

        try:
            binding = client.get_binding(control_id)

            if not binding:
                logger.error(f"Control '{control_id}' not found")
                sys.exit(1)

            if verbose:
                console.print(JSON(json.dumps(binding, indent=2)))
            else:
                console.print(f"\n[bold cyan]Control ID:[/] {binding.get('id')}")
                console.print(f"[bold cyan]Name:[/] {binding.get('name')}")
                console.print(f"[bold cyan]Display Name:[/] {binding.get('display_name')}")
                console.print(f"[bold cyan]Description:[/] {binding.get('description', 'N/A')}")
                console.print(f"[bold cyan]Artifact:[/] {binding.get('artifact_display_name')} ({binding.get('artifact_id')})")
                console.print(f"[bold cyan]Hooks:[/] {', '.join(binding.get('hooks', []))}")
                console.print(f"[bold cyan]Priority:[/] {binding.get('priority')}")
                console.print(f"[bold cyan]Version:[/] {binding.get('version')}")

                if binding.get('config'):
                    console.print(f"\n[bold cyan]Configuration:[/]")
                    console.print(JSON(json.dumps(binding.get('config'), indent=2)))

                # Resolve and display associated assets with names
                console.print(f"\n[bold cyan]Associated Assets:[/]")

                agent_ids = binding.get('agent_ids', [])
                if agent_ids:
                    agents = self._resolve_asset_names(agent_ids, 'agent')
                    console.print(f"  [bold]Agents ({len(agents)}):[/]")
                    for agent in agents:
                        console.print(f"    • {agent['name']} [dim]({agent['id']})[/]")
                else:
                    console.print(f"  [bold]Agents:[/] None")

                tool_ids = binding.get('tool_ids', [])
                if tool_ids:
                    tools = self._resolve_asset_names(tool_ids, 'tool')
                    console.print(f"  [bold]Tools ({len(tools)}):[/]")
                    for tool in tools:
                        console.print(f"    • {tool['name']} [dim]({tool['id']})[/]")
                else:
                    console.print(f"  [bold]Tools:[/] None")

                model_ids = binding.get('model_ids', [])
                if model_ids:
                    models = self._resolve_asset_names(model_ids, 'model')
                    console.print(f"  [bold]Models ({len(models)}):[/]")
                    for model in models:
                        console.print(f"    • {model['name']} [dim]({model['id']})[/]")
                else:
                    console.print(f"  [bold]Models:[/] None")

                console.print()

        except ClientAPIException as e:
            logger.error(f"Failed to get control: {e}")
            sys.exit(1)

    def update_control(
        self,
        control_name: str,
        artifact_name: Optional[str] = None,
        name: Optional[str] = None,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        hooks: Optional[List[str]] = None,
        priority: Optional[int] = None,
        config: Optional[str] = None,
        agent_names: Optional[List[str]] = None,
        tool_names: Optional[List[str]] = None,
        model_names: Optional[List[str]] = None,
    ) -> None:
        """
        Update an existing control.

        Args:
            control_name: The name of the control to update
            artifact_name: New artifact name or display name
            name: New internal name
            display_name: New display name
            description: New description
            hooks: New hooks (replaces existing)
            priority: New priority
            config: New JSON configuration string
            agent_names: New agent names (replaces existing agent bindings; resolved to UUIDs)
            tool_names: New tool names (replaces existing tool bindings; resolved to UUIDs)
            model_names: New model names (replaces existing model bindings; passed through)
        """
        control_id = self._resolve_control_id(control_name)
        client = self.get_client()

        # Build payload with only provided fields
        payload = {}

        if artifact_name is not None:
            payload["artifact_id"] = self._resolve_artifact_id(artifact_name)
        if name is not None:
            payload["name"] = name
        if display_name is not None:
            payload["display_name"] = display_name
        if description is not None:
            payload["description"] = description
        if hooks is not None:
            payload["hooks"] = hooks
        if priority is not None:
            payload["priority"] = priority
        if config is not None:
            try:
                payload["config"] = json.loads(config)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in config parameter: {e}")
                sys.exit(1)
        if agent_names is not None:
            payload["agent_ids"] = self._resolve_agent_names_to_ids(agent_names)
        if tool_names is not None:
            payload["tool_ids"] = self._resolve_tool_names_to_ids(tool_names)
        if model_names is not None:
            payload["model_ids"] = model_names

        if not payload:
            logger.warning("No fields provided to update")
            return

        try:
            client.update_binding(control_id, payload)
            logger.info(f"Control '{control_name}' updated successfully")

        except ClientAPIException as e:
            logger.error(f"Failed to update control: {e}")
            sys.exit(1)

    def remove_control(self, control_name: str) -> None:
        """
        Remove a control.

        Args:
            control_name: The display name or name slug of the control to remove
        """
        control_id = self._resolve_control_id(control_name)
        client = self.get_client()

        try:
            client.delete_binding(control_id)
            logger.info(f"Control '{control_name}' removed successfully")

        except ClientAPIException as e:
            logger.error(f"Failed to remove control: {e}")
            sys.exit(1)

    # ==================== Import/Export Operations ====================

    def import_controls(self, file: Path) -> None:
        """
        Import controls from a YAML or JSON file.

        Args:
            file: Path to the spec file
        """
        if not file.exists():
            logger.error(f"File not found: {file}")
            sys.exit(1)

        try:
            with safe_open(file, 'r') as f:
                if file.suffix == '.json':
                    content = json.load(f)
                elif file.suffix in ['.yaml', '.yml']:
                    content = yaml.safe_load(f)
                else:
                    logger.error("File must be .json, .yaml, or .yml")
                    sys.exit(1)

            # Validate spec structure
            if not content.get('spec_version'):
                logger.error("Missing 'spec_version' in spec file")
                sys.exit(1)

            if not content.get('kind') == 'control':
                logger.error("Spec 'kind' must be 'control'")
                sys.exit(1)

            # Extract control data
            control_data = content.get('control', {})
            if not control_data:
                logger.error("Missing 'control' section in spec file")
                sys.exit(1)

            # Create the control
            self.create_control(
                artifact_name=control_data.get('artifact_name'),
                name=control_data.get('name'),
                display_name=control_data.get('display_name'),
                description=control_data.get('description'),
                hooks=control_data.get('hooks'),
                priority=control_data.get('priority', 100),
                config=json.dumps(control_data.get('config')) if control_data.get('config') else None,
                agent_names=control_data.get('agent_names'),
                tool_names=control_data.get('tool_names'),
                model_names=control_data.get('model_names')
            )

        except Exception as e:
            logger.error(f"Failed to import control: {e}")
            sys.exit(1)

    def export_control(self, control_name: str, output: Path) -> None:
        """
        Export a control to a YAML file.

        Args:
            control_name: The display name or name slug of the control to export
            output: Path where the file should be saved
        """
        control_id = self._resolve_control_id(control_name)
        client = self.get_client()

        try:
            binding = client.get_binding(control_id)

            if not binding:
                logger.error(f"Control '{control_name}' not found")
                sys.exit(1)

            # Resolve UUIDs back to names for a human-readable, re-importable spec
            agent_ids = binding.get('agent_ids') or []
            tool_ids = binding.get('tool_ids') or []
            model_ids = binding.get('model_ids') or []

            agent_names = [a['name'] for a in self._resolve_asset_names(agent_ids, 'agent')]
            tool_names = [t['name'] for t in self._resolve_asset_names(tool_ids, 'tool')]
            model_names = [m['name'] for m in self._resolve_asset_names(model_ids, 'model')]

            # Build spec structure
            control_section = {
                'artifact_name': binding.get('artifact_display_name'),
                'name': binding.get('name'),
                'display_name': binding.get('display_name'),
                'description': binding.get('description'),
                'hooks': binding.get('hooks'),
                'priority': binding.get('priority'),
                'config': binding.get('config'),
            }
            if agent_names:
                control_section['agent_names'] = agent_names
            if tool_names:
                control_section['tool_names'] = tool_names
            if model_names:
                control_section['model_names'] = model_names

            spec = {
                'spec_version': str(SpecVersion.V1),
                'kind': 'control',
                'control': control_section,
            }

            # Remove None values
            spec['control'] = {k: v for k, v in spec['control'].items() if v is not None}

            # Write to file
            with safe_open(output, 'w') as f:
                yaml.dump(spec, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

            logger.info(f"Control exported to {output}")

        except ClientAPIException as e:
            logger.error(f"Failed to export control: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to write export file: {e}")
            sys.exit(1)
