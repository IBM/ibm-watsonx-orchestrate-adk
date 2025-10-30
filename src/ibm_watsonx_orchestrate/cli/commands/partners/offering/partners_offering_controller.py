import json
import yaml
import zipfile
import logging
import sys
from pathlib import Path
import tempfile
import zipfile
import shutil
from shutil import make_archive
from ibm_watsonx_orchestrate.agent_builder.tools.types import ToolSpec
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient
from ibm_watsonx_orchestrate.client.agents.external_agent_client import ExternalAgentClient
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentsController, AgentKind, parse_create_native_args, parse_create_external_args
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.agent_builder.agents import (
    Agent,
    ExternalAgent,
    AgentKind,
)
from ibm_watsonx_orchestrate.cli.commands.connections.connections_controller import export_connection
from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolsController
from ibm_watsonx_orchestrate.utils.utils import sanitize_catalog_label
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from .types import *

APPLICATIONS_FILE_VERSION = '1.16.0'


logger = logging.getLogger(__name__)

def get_tool_bindings(tool_names: list[str]) -> dict[str, dict]:
    """
    Return the raw binding (e.g. python function, connections, requirements)
    for each tool name.
    """
    tools_controller = ToolsController()
    client = tools_controller.get_client()

    results = {}

    for name in tool_names:
        draft_tools = client.get_draft_by_name(tool_name=name)
        if not draft_tools:
            logger.warning(f"No tool named {name} found")
            continue
        if len(draft_tools) > 1:
            logger.warning(f"Multiple tools found with name {name}, using first")

        draft_tool = draft_tools[0]
        binding = draft_tool.get("binding", {})
        results[name] = binding

    return results

def _patch_agent_yamls(project_root: Path, publisher_name: str, parent_agent_name: str):
    agents_dir = project_root / "agents"
    if not agents_dir.exists():
        return

    for agent_yaml in agents_dir.glob("*.yaml"):
        with safe_open(agent_yaml, "r") as f:
            agent_data = yaml.safe_load(f) or {}

        extra_agent_fields = OfferingAgentExtras.from_agent_details(
            agent_data,
            publisher_name,
            parent_agent_name
        ).model_dump()

        extra_agent_fields = {k: v for k, v in extra_agent_fields.items() if v is not None}

        agent_data.update(extra_agent_fields)

        with safe_open(agent_yaml, "w") as f:
            yaml.safe_dump(agent_data, f, sort_keys=False)


def _create_applications_entry(connection_config: dict) -> dict:
    return {
        'app_id': connection_config.get('app_id'),
        'name': connection_config.get('catalog',{}).get('name','applications_file'),
        'description': connection_config.get('catalog',{}).get('description',''),
        'icon': connection_config.get('catalog',{}).get('icon','')
    }

def _compare_placeholders(value, placeholder) -> bool:
    if isinstance(placeholder, BaseModel):
        placeholder = placeholder.model_dump()
    
    return value == placeholder

def _validate_agent_placeholders(agent_data: dict, agent_name: str) -> None:
    for label, placeholder in AGENT_CATALOG_ONLY_PLACEHOLDERS.items():
        if _compare_placeholders(agent_data.get(label),  placeholder):
            logger.warning(f"Placeholder '{label}' detected for agent '{agent_name}', please ensure '{label}' is correct before packaging.")




class PartnersOfferingController:
    def __init__(self):
        self.root = Path.cwd()

    def get_native_client(self):
        self.native_client = instantiate_client(AgentClient)
        return self.native_client
    
    def get_external_client(self):
        self.native_client = instantiate_client(ExternalAgentClient)
        return self.native_client
    
    def get_tool_client(self):
        self.tool_client = instantiate_client(ToolClient)
        return self.tool_client

    def _to_agent_kind(self, kind_str: str) -> AgentKind:
        s = (kind_str or "").strip().lower()
        if s in ("native", "agentkind.native"):
            return AgentKind.NATIVE
        if s in ("external", "agentkind.external"):
            return AgentKind.EXTERNAL
        logger.error(f"Agent kind '{kind_str}' is not currently supported. Expected 'native' or 'external'.")
        sys.exit(1)

    def create(self, offering: str, publisher_name: str, agent_type: str, agent_name: str):

        # Sanitize offering name
        original_offering = offering
        offering = sanitize_catalog_label(offering)

        if offering != original_offering:
            logger.warning("Offering name must contain only alpahnumeric characters or underscore")
            logger.info(f"Offering '{original_offering}' has been updated to '{offering}'")

        # Create parent project folder
        project_root = self.root / offering

        # Check if the folder already exists — skip the whole thing
        if project_root.exists():
            logger.error(f"Offering folder '{offering}' already exists. Skipping creation.")
            sys.exit(1)

        project_root.mkdir(parents=True, exist_ok=True)

        # Scaffold subfolders that aren’t provided by Agent export
        for folder in [
            project_root / "connections",
            project_root / "offerings",
            project_root / "evaluations",
        ]:
            folder.mkdir(parents=True, exist_ok=True)

        # Export the agent (includes tools + collaborators) to a temp zip-----------------------------------
        output_zip = project_root / f"{offering}.zip"   # drives top-level folder inside zip
        agents_controller = AgentsController()
        kind_enum = self._to_agent_kind(agent_type)
        agents_controller.export_agent(
            name=agent_name,
            kind=kind_enum,
            output_path=str(output_zip),
            agent_only_flag=False,
            with_tool_spec_file=True
        )

        # Unzip into project_root
        with zipfile.ZipFile(output_zip, "r") as zf:
            zf.extractall(project_root)

        # Flatten "<offering>/" top-level from the zip into project_root
        extracted_root = project_root / output_zip.stem
        if extracted_root.exists() and extracted_root.is_dir():
            for child in extracted_root.iterdir():
                dest = project_root / child.name

                # Special case: flatten away "agents/native" (or "agents/external")
                if child.name == "agents":
                    agents_dir = project_root / "agents"
                    agents_dir.mkdir(exist_ok=True)
                    nested = child / kind_enum.value.lower()
                    if nested.exists() and nested.is_dir():
                        for agent_child in nested.iterdir():
                            shutil.move(str(agent_child), str(agents_dir))
                        shutil.rmtree(nested, ignore_errors=True)
                    continue

                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                shutil.move(str(child), str(dest))
            shutil.rmtree(extracted_root, ignore_errors=True)

        # Remove the temp zip
        output_zip.unlink(missing_ok=True)

        # Patch the agent yamls with publisher, tags, icon, etc.
        _patch_agent_yamls(project_root=project_root, publisher_name=publisher_name, parent_agent_name=agent_name)


        # Create offering.yaml file -------------------------------------------------------
        native_client = self.get_native_client()
        external_client = self.get_external_client()

        existing_native_agents = native_client.get_draft_by_name(agent_name)
        existing_native_agents = [Agent.model_validate(agent) for agent in existing_native_agents]
        existing_external_clients = external_client.get_draft_by_name(agent_name)
        existing_external_clients = [ExternalAgent.model_validate(agent) for agent in existing_external_clients]

        all_existing_agents = existing_external_clients + existing_native_agents

        if len(all_existing_agents) > 0:
                existing_agent = all_existing_agents[0]

        tool_client = self.get_tool_client()
        tool_names = []
        if hasattr(existing_agent,'tools') and existing_agent.tools:
            matching_tools = tool_client.get_drafts_by_ids(existing_agent.tools)
            tool_names = [tool['name'] for tool in matching_tools if 'name' in tool]

        all_agents_names = []
        all_agents_names.append(agent_name)
        all_tools_names = []
        all_tools_names.extend(tool_names)

        if hasattr(existing_agent,'collaborators') and existing_agent.collaborators:
            collaborator_agents = existing_agent.collaborators            
            for agent_id in collaborator_agents:
                native_collaborator_agent = native_client.get_draft_by_id(agent_id)
                external_collaborator_agent = external_client.get_draft_by_id(agent_id)

                # collect names of collaborators
                if native_collaborator_agent and "name" in native_collaborator_agent:
                    all_agents_names.append(native_collaborator_agent["name"])
                if external_collaborator_agent and "name" in external_collaborator_agent:
                    all_agents_names.append(external_collaborator_agent["name"])

                # collect tools of collaborators
                collaborator_tool_ids = []

                if native_collaborator_agent and "tools" in native_collaborator_agent:
                    collaborator_tool_ids.extend(native_collaborator_agent["tools"]) 
                if external_collaborator_agent and "tools" in external_collaborator_agent:
                    collaborator_tool_ids.extend(external_collaborator_agent["tools"]) 

                for tool_id in collaborator_tool_ids:
                    tool = tool_client.get_draft_by_id(tool_id)
                    if tool and "name" in tool:
                        all_tools_names.append(tool["name"])

        if not existing_agent.display_name:
            if hasattr(existing_agent,'title') and existing_agent.title:
                existing_agent.display_name = existing_agent.title
            elif hasattr(existing_agent,'nickname') and existing_agent.nickname:
                existing_agent.display_name = existing_agent.nickname
            else:
                existing_agent.display_name = ""
        
        offering_file = project_root / "offerings" / f"{offering}.yaml"
        if not offering_file.exists():
            offering = Offering(
                name=agent_name,
                display_name=existing_agent.display_name,
                publisher=publisher_name,
                description=existing_agent.description,
                agents=all_agents_names,
                tools=all_tools_names
            )
            offering_file.write_text(yaml.safe_dump(offering.model_dump(exclude_none=True), sort_keys=False))
        logger.info("Successfully created Offerings yaml file.")

        # Connection Yaml------------------------------------------------------------------
        bindings = get_tool_bindings(all_tools_names)
        seen_connections = set()  # track only unique connections by app+conn_id

        for _, binding in bindings.items():
            if "python" in binding and "connections" in binding["python"]:
                for app_id, conn_id in binding["python"]["connections"].items():
                    key = (app_id, conn_id)
                    if key in seen_connections:
                        continue
                    seen_connections.add(key)

                    conn_file = project_root / "connections" / f"{app_id}.yaml"
                    
                    # Using connection Id instead of app_id because app_id has been sanitized in the binding
                    export_connection(connection_id=conn_id, output_file=conn_file, include_catalog=True)


    def package(self, offering: str, folder_path: Optional[str] = None):
        # Root folder
        if folder_path:
            root_folder = Path(folder_path)
        else:
            root_folder = Path.cwd()

        if not root_folder.exists():
            raise ValueError(f"Folder '{str(root_folder)}' does not exist")
       
        project_root = root_folder / offering

        # Resilience in case path to project folder is passed as root
        if not project_root.exists() and str(root_folder).lower().endswith(offering.lower()):
            project_root = Path(root_folder)
            root_folder = Path(str(root_folder)[:-len(offering)])

        offering_file = project_root / "offerings" / f"{offering}.yaml"

        if not offering_file.exists():
            raise FileNotFoundError(f"Offering file '{offering_file}' does not exist")

        # Load offering data
        with safe_open(offering_file) as f:
            offering_obj = Offering(**yaml.safe_load(f))

        # Validate offering
        offering_obj.validate_ready_for_packaging()
        offering_data = offering_obj.model_dump()

        publisher_name = offering_obj.publisher or "default_publisher"
        zip_name = f"{offering}-{offering_obj.version}.zip"
        zip_path = root_folder / zip_name  # Zip created at root


        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            top_level_folder = offering

            # --- Add offering YAML as JSON ---
            offering_json_path = f"{top_level_folder}/offerings/{offering}/config.json"
            zf.writestr(offering_json_path, json.dumps(offering_data, indent=2))

            # --- Add & validate agents ---
            agents = offering_data.get("assets", {}).get(publisher_name, {}).get("agents", [])
            for agent_name in agents:
                agent_file = project_root / "agents" / f"{agent_name}.yaml"
                if not agent_file.exists():
                    logger.error(f"Agent {agent_name} not found")
                    sys.exit(1)

                with safe_open(agent_file) as f:
                    agent_data = yaml.safe_load(f)

                # Validate agent spec
                agent_kind = agent_data.get("kind")
                if agent_kind not in ("native", "external"):
                    logger.error(f"Agent {agent_name} has invalid kind: {agent_kind}") 
                    sys.exit(1)

                # Agent validation
                match agent_kind:
                    case AgentKind.NATIVE:
                        agent_details = parse_create_native_args(
                            **agent_data
                        )
                        agent = Agent.model_validate(agent_details)
                    case AgentKind.EXTERNAL:
                        agent_details = parse_create_external_args(
                            **agent_data
                        )
                        agent = ExternalAgent.model_validate(agent_details)
                
                _validate_agent_placeholders(agent_data, agent_name)

                agent_json_path = f"{top_level_folder}/agents/{agent_name}/config.json"
                zf.writestr(agent_json_path, json.dumps(agent_data, indent=2))
            
            # --- Add & validate tools ---
            tools_client = instantiate_client(ToolClient)
            tools = offering_data.get("assets", {}).get(publisher_name, {}).get("tools", [])
            for tool_name in tools:
                tool_dir = project_root / "tools" / tool_name
                if not tool_dir.exists():
                    logger.error(f"Tool {tool_name} not found")
                    sys.exit(1)

                spec_file = tool_dir / "config.json"
                if not spec_file.exists():
                    logger.warning(f"No spec file found for tool '{tool_name}', checking orchestrate")
                    tool_data = tools_client.get_draft_by_name(tool_name)
                    if not tool_data or not len(tool_data):
                        logger.error(f"Unable to locate tool '{tool_name}' in current env")
                        sys.exit(1)
                    
                    tool_data = ToolSpec.model_validate(tool_data[0]).model_dump(exclude_unset=True)
                else:
                    with safe_open(spec_file) as f:
                        tool_data = json.load(f)

                # Validate tool
                if not tool_data.get("binding",{}).get("python"):
                    logger.error(f"Tool {tool_name} is not a Python tool")
                    sys.exit(1)
                if "name" not in tool_data or tool_data["name"] != tool_name:
                    logger.error(f"Tool {tool_name} has invalid or missing name in spec")
                    sys.exit(1)

                # Write tool spec directly into zip
                tool_zip_path = f"{top_level_folder}/tools/{tool_name}/config.json"
                zf.writestr(tool_zip_path, json.dumps(tool_data, indent=2))

                # --- Build artifact zip in-memory instead of source ---
                artifact_zip_path = f"{top_level_folder}/tools/{tool_name}/attachments/{tool_name}.zip"
                py_files = [p for p in tool_dir.glob("*.py")]
                if py_files:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        tmp_zip = Path(tmpdir) / f"{tool_name}.zip"
                        make_archive(str(tmp_zip.with_suffix('')), 'zip', root_dir=tool_dir, base_dir='.')
                        zf.write(tmp_zip, artifact_zip_path)
                else:
                    logger.error(f"No Python files found for tool {tool_name}.")
                    sys.exit(1)

            # --- Add & validate connections(applications) ---
            applications_file_path = f"{top_level_folder}/applications/config.json"
            applications_file_data = {
                'name': 'applications_file',
                'version': APPLICATIONS_FILE_VERSION,
                'description': None
            }
            applications = []

            connections_folder_path = project_root / "connections"
            for connection_file in connections_folder_path.glob('*.yaml'):
                with safe_open(connection_file,"r") as f:
                    connection_data = yaml.safe_load(f)
                    applications.append(
                        _create_applications_entry(connection_data)
                    )

            applications_file_data['applications'] = applications
            
            zf.writestr(applications_file_path, json.dumps(applications_file_data, indent=2))


            
        logger.info(f"Successfully packed Offering into {zip_path}")







































