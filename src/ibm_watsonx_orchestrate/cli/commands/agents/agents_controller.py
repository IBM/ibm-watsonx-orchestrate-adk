import yaml
import json
import rich
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
import requests
import importlib
import inspect
import io
import json
import logging
import sys
import zipfile
import os
import tempfile
from pathlib import Path
from copy import deepcopy
from pathlib import Path
from typing import Iterable, List, Optional, TypeVar

import requests
import rich
import yaml
from pydantic import BaseModel, field_validator
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ibm_watsonx_orchestrate.agent_builder.agents import (
    Agent,
    CustomAgent,
    ExternalAgent,
    AssistantAgent,
    AgentKind,
    SpecVersion,
    AgentRestrictionType,
    AgentStyle
)
from ibm_watsonx_orchestrate.agent_builder.models.types import ModelConfig
from ibm_watsonx_orchestrate.agent_builder.tools.types import ToolSpec
from ibm_watsonx_orchestrate.cli.commands.connections.connections_controller import export_connection, get_app_id_from_conn_id, get_conn_id_from_app_id
from ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller import \
    import_python_knowledge_base, KnowledgeBaseController
from ibm_watsonx_orchestrate.cli.commands.models.models_controller import import_python_model, ModelsController
from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import ToolKind, import_python_tool, ToolsController, \
    _get_kind_from_spec
from ibm_watsonx_orchestrate.cli.common import ListFormats, rich_table_to_markdown
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient, AgentUpsertResponse, transform_agents_from_flat_agent_spec
from ibm_watsonx_orchestrate.client.agents.external_agent_client import ExternalAgentClient
from ibm_watsonx_orchestrate.client.agents.assistant_agent_client import AssistantAgentClient
from ibm_watsonx_orchestrate.client.connections import get_connections_client
from ibm_watsonx_orchestrate.client.knowledge_bases.knowledge_base_client import KnowledgeBaseClient
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client, is_local_dev
from ibm_watsonx_orchestrate.client.voice_configurations.voice_configurations_client import VoiceConfigurationsClient
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.utils.utils import check_file_in_zip

logger = logging.getLogger(__name__)

# Helper generic type for any agent
AnyAgentT = TypeVar("AnyAgentT", bound=Agent | CustomAgent | ExternalAgent | AssistantAgent)

LOG_LEVEL_COLORS = {
    "DEBUG": "blue",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold red"
}


class CustomAgentConfig(BaseModel):
    """Configuration details from custom agent upload response."""
    language: Optional[str] = None
    framework: Optional[str] = None
    entrypoint: str
    agent_name: str
    agent_description: str
    requirements: List[str] = []
    file_count: int
    
    @field_validator('requirements', mode='before')
    @classmethod
    def parse_requirements(cls, v):
        """Convert requirements from string to list if needed."""
        if isinstance(v, str):
            if '\n' in v:
                return [r.strip() for r in v.split('\n') if r.strip()]
        return [v] if v is not None else []


class CustomAgentUploadResponse(BaseModel):
    """Response from custom agent artifact upload."""
    config: CustomAgentConfig


def import_python_agent(file: str) -> List[Agent | CustomAgent | ExternalAgent | AssistantAgent]:
    # Import tools
    import_python_tool(file)
    import_python_knowledge_base(file)
    import_python_model(file)

    file_path = Path(file)
    file_directory = file_path.parent
    file_name = file_path.stem
    sys.path.append(str(file_directory))
    module = importlib.import_module(file_name)
    del sys.path[-1]

    agents = []
    for _, obj in inspect.getmembers(module):
        if isinstance(obj, (Agent, ExternalAgent, AssistantAgent)):
            agents.append(obj)
    return agents


def create_agent_from_spec(file:str, kind:str) -> Agent | CustomAgent | ExternalAgent | AssistantAgent:
    if not kind:
        kind = AgentKind.NATIVE
    match kind:
        case AgentKind.NATIVE:
            agent = Agent.from_spec(file)
        case AgentKind.EXTERNAL:
            agent = ExternalAgent.from_spec(file)
        case AgentKind.ASSISTANT:
            agent = AssistantAgent.from_spec(file)
        case _:
            raise BadRequest("'kind' must be either 'native' or 'external'")

    return agent

def parse_file(file: str) -> List[Agent | CustomAgent | ExternalAgent | AssistantAgent]:
    if file.endswith('.yaml') or file.endswith('.yml') or file.endswith(".json"):
        with safe_open(file, 'r') as f:
            if file.endswith(".json"):
                content = json.load(f)
            else:
                content = yaml.load(f, Loader=yaml.SafeLoader)
        agent = create_agent_from_spec(file=file, kind=content.get("kind"))
        return [agent]
    elif file.endswith('.py'):
        agents = import_python_agent(file)
        return agents
    else:
        raise BadRequest("file must end in .json, .yaml, .yml, or .py")

def parse_create_native_args(name: str, kind: AgentKind, description: str | None, **args) -> dict:
    agent_details = {
        "name": name,
        "kind": kind,
        "description": description,
        "instructions": args.get("instructions"),
        "llm": args.get("llm"),
        "style": args.get("style"),
        "custom_join_tool": args.get("custom_join_tool"),
        "structured_output": args.get("structured_output"),
        "context_access_enabled": args.get("context_access_enabled", True),
    }

    collaborators = args.get("collaborators", [])
    collaborators = collaborators if collaborators else []
    collaborators = [x.strip() for x in collaborators if x.strip() != ""]
    agent_details["collaborators"] = collaborators

    tools = args.get("tools", [])
    tools = tools if tools else []
    tools = [x.strip() for x in tools if x.strip() != ""]
    agent_details["tools"] = tools

    plugins = args.get("plugins", [])
    plugins = plugins if plugins else []
    plugins = [x.strip() for x in plugins if x.strip() != ""]
    agent_details["plugins"] = plugins

    knowledge_base = args.get("knowledge_base", [])
    knowledge_base = knowledge_base if knowledge_base else []
    knowledge_base = [x.strip() for x in knowledge_base if x.strip() != ""]
    agent_details["knowledge_base"] = knowledge_base

    context_variables = args.get("context_variables", [])
    context_variables = context_variables if context_variables else []
    context_variables = [x.strip() for x in context_variables if x.strip() != ""]
    agent_details["context_variables"] = context_variables

    # hidden = args.get("hidden")
    # if hidden:
    #     agent_details["hidden"] = hidden 

    # starter_prompts = args.get("starter_prompts")
    # if starter_prompts:
    #     agent_details["starter_prompts"] = starter_prompts 

    # welcome_content = args.get("welcome_content")
    # if welcome_content:
    #     agent_details["welcome_content"] = welcome_content 

    return agent_details

def parse_create_external_args(name: str, kind: AgentKind, description: str | None, **args) -> dict:
    agent_details = {
        "name": name,
        "kind": kind,
        "description": description,
        "title": args.get("title"),
        "api_url": args.get("api_url"),
        "auth_scheme": args.get("auth_scheme"),
        "auth_config": args.get("auth_config", {}),
        "provider": args.get("provider"),
        "tags": args.get("tags", []),
        "chat_params": args.get("chat_params", {}),
        "config": args.get("config", {}),
        "nickname": args.get("nickname"),
        "app_id": args.get("app_id"),
        "context_access_enabled": args.get("context_access_enabled", True),
    }

    context_variables = args.get("context_variables", [])
    context_variables = context_variables if context_variables else []
    context_variables = [x.strip() for x in context_variables if x.strip() != ""]
    agent_details["context_variables"] = context_variables

    return agent_details

def parse_create_assistant_args(name: str, kind: AgentKind, description: str | None, **args) -> dict:
    agent_details = {
        "name": name,
        "kind": kind,
        "description": description,
        "title": args.get("title"),
        "tags": args.get("tags", []),
        "config": args.get("config", {}),
        "nickname": args.get("nickname"),
        "context_access_enabled": args.get("context_access_enabled", True),
    }

    context_variables = args.get("context_variables", [])
    context_variables = context_variables if context_variables else []
    context_variables = [x.strip() for x in context_variables if x.strip() != ""]
    agent_details["context_variables"] = context_variables

    return agent_details

def get_agent_details(name: str, client: AgentClient | ExternalAgentClient | AssistantAgentClient) -> dict:
    agent_specs = client.get_draft_by_name(name)
    if len(agent_specs) > 1:
            logger.error(f"Multiple agents with the name '{name}' found. Failed to get agent")
            sys.exit(1)
    if len(agent_specs) == 0:
            logger.error(f"No agents with the name '{name}' found. Failed to get agent")
            sys.exit(1)

    return agent_specs[0]

def _raise_guidelines_warning(response: AgentUpsertResponse) -> None:
    if response.warning:
        logger.warning(f"Agent Configuration Issue: {response.warning}")

class AgentsController:
    def __init__(self):
        self.native_client = None
        self.external_client = None
        self.assistant_client = None
        self.tool_client = None
        self.knowledge_base_client = None
        self.voice_configuration_client = None

    def get_native_client(self):
        if not self.native_client:
            self.native_client = instantiate_client(AgentClient)
        return self.native_client

    def get_external_client(self):
        if not self.external_client:
            self.external_client = instantiate_client(ExternalAgentClient)
        return self.external_client
    
    def get_assistant_client(self):
        if not self.assistant_client:
            self.assistant_client = instantiate_client(AssistantAgentClient)
        return self.assistant_client
    
    def get_tool_client(self):
        if not self.tool_client:
            self.tool_client = instantiate_client(ToolClient)
        return self.tool_client
    
    def get_knowledge_base_client(self):
        if not self.knowledge_base_client:
            self.knowledge_base_client = instantiate_client(KnowledgeBaseClient)
        return self.knowledge_base_client
    
    def get_voice_configuration_client(self):
        if not self.voice_configuration_client:
            self.voice_configuration_client = instantiate_client(VoiceConfigurationsClient)
        return self.voice_configuration_client
    
    @staticmethod
    def import_agent(
        file: str | None = None,
        app_id: str | None = None,
        custom_agent_file_path: str | None = None,
        custom_agent_config_file: str | None = None
    ) -> List[Agent | CustomAgent | ExternalAgent | AssistantAgent]:
        # Check if this is a custom agent with package root
        if custom_agent_file_path and os.path.isdir(custom_agent_file_path):
            # This is a custom agent with a directory - create a CustomAgent
            zip_path, extracted_agent_name = AgentsController._create_agent_zip(
                custom_agent_file_path,
                custom_agent_config_file
            )
            
            # Create a CustomAgent instance
            # Note: extracted_agent_name is guaranteed to be non-None because _create_agent_zip
            # will exit with an error if no agent name is found
            agent = CustomAgent(
                name=extracted_agent_name,  # type: ignore
                description="Custom agent imported from directory",
                kind=AgentKind.NATIVE,
                style=AgentStyle.CUSTOM
            )
            agent.custom_agent_file_path = zip_path
            
            return [agent]
        
        if not file:
            raise ValueError("File must be provided for native agents")
        
        agents = parse_file(file)
        for agent in agents:
            if app_id and agent.kind != AgentKind.NATIVE and agent.kind != AgentKind.ASSISTANT:
                agent.app_id = app_id
        
        return agents


    @staticmethod
    def generate_agent_spec(
        name: str, kind: AgentKind, description: str, **kwargs
    ) -> Agent | CustomAgent | ExternalAgent | AssistantAgent:
        match kind:
            case AgentKind.NATIVE:
                agent_details = parse_create_native_args(
                    name, kind=kind, description=description, **kwargs
                )
                # Use CustomAgent for custom style agents
                if kwargs.get('style') == AgentStyle.CUSTOM:
                    agent = CustomAgent.model_validate(agent_details)
                    custom_agent_file_path = kwargs.get('custom_agent_file_path')
                    custom_agent_config_file = kwargs.get('custom_agent_config_file')
                    
                    # If package_root is a directory, zip it and extract agent name
                    if custom_agent_file_path and os.path.isdir(custom_agent_file_path):
                        zip_path, extracted_agent_name = AgentsController._create_agent_zip(
                            custom_agent_file_path,
                            custom_agent_config_file
                        )
                        agent.custom_agent_file_path = zip_path
                        # Update agent name if we extracted it from config
                        if extracted_agent_name:
                            agent.name = extracted_agent_name
                            agent_details['name'] = extracted_agent_name
                    else:
                        agent.custom_agent_file_path = custom_agent_file_path
                else:
                    agent = Agent.model_validate(agent_details)
                AgentsController().persist_record(agent=agent, **kwargs)
            case AgentKind.EXTERNAL:
                agent_details = parse_create_external_args(name, kind=kind, description=description, **kwargs)
                agent = ExternalAgent.model_validate(agent_details)
                AgentsController().persist_record(agent=agent, **kwargs)
            case AgentKind.ASSISTANT:
                agent_details = parse_create_assistant_args(name, kind=kind, description=description, **kwargs)
                agent = AssistantAgent.model_validate(agent_details)
                AgentsController().persist_record(agent=agent, **kwargs)
            case _:
                raise ValueError("'kind' must be 'native' or 'external' for agent creation")
        return agent

    def get_all_agents(self, client: None):
        return {entry["name"]: entry["id"] for entry in client.get()}

    def dereference_collaborators(self, agent: Agent) -> Agent:
        native_client = self.get_native_client()
        external_client = self.get_external_client()
        assistant_client = self.get_assistant_client()

        deref_agent = deepcopy(agent)
        matching_native_agents = native_client.get_drafts_by_names(deref_agent.collaborators)
        matching_external_agents = external_client.get_drafts_by_names(deref_agent.collaborators)
        matching_assistant_agents = assistant_client.get_drafts_by_names(deref_agent.collaborators)
        matching_agents = matching_native_agents + matching_external_agents + matching_assistant_agents

        name_id_lookup = {}
        for a in matching_agents:
            if a.get("name") in name_id_lookup:
                logger.error(f"Duplicate draft entries for collaborator '{a.get('name')}'")
                sys.exit(1)
            name_id_lookup[a.get("name")] = a.get("id")
        
        deref_collaborators = []
        for name in agent.collaborators:
            id = name_id_lookup.get(name)
            if not id:
                logger.error(f"Failed to find collaborator. No agents found with the name '{name}'")
                sys.exit(1)
            deref_collaborators.append(id)
        deref_agent.collaborators = deref_collaborators

        return deref_agent
    
    def reference_collaborators(self, agent: Agent) -> Agent:
        native_client = self.get_native_client()
        external_client = self.get_external_client()
        assistant_client = self.get_assistant_client()

        ref_agent = deepcopy(agent)
        matching_native_agents = native_client.get_drafts_by_ids(ref_agent.collaborators)
        matching_external_agents = external_client.get_drafts_by_ids(ref_agent.collaborators)
        matching_assistant_agents = assistant_client.get_drafts_by_ids(ref_agent.collaborators)
        matching_agents = matching_native_agents + matching_external_agents + matching_assistant_agents
        
        id_name_lookup = {}
        for a in matching_agents:
            if a.get("id") in id_name_lookup:
                logger.error(f"Duplicate draft entries for collaborator '{a.get('id')}'")
                sys.exit(1)
            id_name_lookup[a.get("id")] = a.get("name")

        ref_collaborators = []
        for id in agent.collaborators:
            name = id_name_lookup.get(id)
            if not name:
                logger.error(f"Failed to find collaborator. No agents found with the id '{id}'")
                sys.exit(1)
            ref_collaborators.append(name)
        ref_agent.collaborators = ref_collaborators

        return ref_agent

    def dereference_tools(self, agent: Agent) -> Agent:
        tool_client = self.get_tool_client()
        deref_agent = deepcopy(agent)

        tool_names = list(deref_agent.tools)

        # If agent has style set to "planner" and have join_tool defined, then we need to include that tool as well
        if agent.style == AgentStyle.PLANNER and agent.custom_join_tool:
            tool_names.append(deref_agent.custom_join_tool)

        # Plugin tool names
        plugin_phases = {}

        if agent.plugins is not None:
            plugin_phases = {
                "agent_pre_invoke": getattr(agent.plugins, "agent_pre_invoke", None),
                "agent_post_invoke": getattr(agent.plugins, "agent_post_invoke", None),
            }

            for plugin_list in plugin_phases.values():
                if plugin_list:
                    tool_names.extend([p.plugin_name for p in plugin_list])

        # Fetch ALL tools at once 
        all_matching_tools = tool_client.get_drafts_by_names(tool_names)

        # Validate plugin placement
        if agent.plugins is not None:
            for phase_name, plugin_list in plugin_phases.items():
                if not plugin_list:
                    continue

                for plugin in plugin_list:
                    tool = next((t for t in all_matching_tools if t["name"] == plugin.plugin_name), None)
                    if not tool:
                        logger.error(f"Plugin {plugin.plugin_name} not found in fetched tools.")
                        sys.exit(1)

                    python_binding = tool.get("binding", {}).get("python", {})
                    tool_type = python_binding.get("type")

                    if not tool_type:
                        logger.error(f"Tool '{plugin.plugin_name}' missing 'type' in binding.")
                        sys.exit(1)

                    if tool_type != phase_name:
                        logger.error(
                            f"Tool '{plugin.plugin_name}' has type '{tool_type}' "
                            f"but is placed under the '{phase_name}' section of the Agent spec. Please update this."
                        )
                        sys.exit(1)

        name_id_lookup = {}
        for tool in all_matching_tools:
            if tool.get("name") in name_id_lookup:
                logger.error(f"Duplicate draft entries for tool '{tool.get('name')}'")
                sys.exit(1)
            name_id_lookup[tool.get("name")] = tool.get("id")
        
        deref_tools = []
        for name in agent.tools:
            id = name_id_lookup.get(name)
            if not id:
                logger.error(f"Failed to find tool. No tools found with the name '{name}'")
                sys.exit(1)
            deref_tools.append(id)
        deref_agent.tools = deref_tools
        
        if agent.style == AgentStyle.PLANNER and agent.custom_join_tool:
            join_tool_id = name_id_lookup.get(agent.custom_join_tool)
            if not join_tool_id:
                logger.error(f"Failed to find custom join tool. No tools found with the name '{agent.custom_join_tool}'")
                sys.exit(1)
            deref_agent.custom_join_tool = join_tool_id

        # # Dereference plugins
        if agent.plugins:
            # Make a deep copy of the agent's plugins so we don't mutate the original
            deref_agent.plugins = deepcopy(agent.plugins)

            for phase_name in ["agent_pre_invoke", "agent_post_invoke"]:
                phase_list = getattr(deref_agent.plugins, phase_name, None)
                if not phase_list:
                    continue

                for plugin in phase_list:
                    plugin_id = name_id_lookup.get(plugin.plugin_name)
                    if not plugin_id:
                        logger.error(f"Failed to find plugin tool. No tools found with the name '{plugin.plugin_name}'")
                        sys.exit(1)
                    plugin.plugin_id = plugin_id

        return deref_agent
    
    def reference_tools(self, agent: Agent) -> Agent:
        tool_client = self.get_tool_client()

        ref_agent = deepcopy(agent)

        # main tools
        main_tool_ids = list(ref_agent.tools)
        
        # Include custom join tool if planner style
        if agent.style == AgentStyle.PLANNER and agent.custom_join_tool:
            main_tool_ids.append(agent.custom_join_tool)

        # plugin tools
        plugin_tool_ids = []
        if ref_agent.plugins:
            # pre-invoke plugins
            if getattr(ref_agent.plugins, "agent_pre_invoke", None):
                plugin_tool_ids.extend(
                    p.plugin_id for p in ref_agent.plugins.agent_pre_invoke if p.plugin_id
                )

            # post-invoke plugins
            if getattr(ref_agent.plugins, "agent_post_invoke", None):
                plugin_tool_ids.extend(
                    p.plugin_id for p in ref_agent.plugins.agent_post_invoke if p.plugin_id
                )

        all_tool_ids = main_tool_ids + plugin_tool_ids
        matching_tools = tool_client.get_drafts_by_ids(all_tool_ids)

        id_name_lookup = {}
        for tool in matching_tools:
            tid = tool.get("id")
            tname = tool.get("name")
            if tid in id_name_lookup:
                logger.error(f"Duplicate draft entries for tool '{tid}'")
                sys.exit(1)
            id_name_lookup[tid] = tname

        # resolove main tools
        ref_tools = []
        for tid in agent.tools:
            name = id_name_lookup.get(tid)
            if not name:
                logger.error(f"Failed to find tool. No tools found with the id '{tid}'")
                sys.exit(1)
            ref_tools.append(name)
        ref_agent.tools = ref_tools

        # resolove custom join tool
        if agent.style == AgentStyle.PLANNER and agent.custom_join_tool:
            join_tool_name = id_name_lookup.get(agent.custom_join_tool)
            if not join_tool_name:
                logger.error(
                    f"Failed to find custom join tool. No tools found with the id '{agent.custom_join_tool}'"
                )
                sys.exit(1)
            ref_agent.custom_join_tool = join_tool_name

        # resolve plugin tools
        if agent.plugins:
            for phase_name in ["agent_pre_invoke", "agent_post_invoke"]:
                phase_list = getattr(ref_agent.plugins, phase_name, None)
                if not phase_list:
                    continue

                for plugin in phase_list:
                    plugin_name = id_name_lookup.get(plugin.plugin_id)
                    if not plugin_name:
                        logger.error(
                            f"Failed to find plugin tool. No plugin found with id '{plugin.plugin_id}'"
                        )
                        sys.exit(1)
                    plugin.plugin_name = plugin_name
                    # REMOVE plugin_id so it's not exported
                    del plugin.plugin_id

        return ref_agent
    
    def dereference_knowledge_bases(self, agent: Agent) -> Agent:
        client = self.get_knowledge_base_client()

        deref_agent = deepcopy(agent)
        matching_knowledge_bases = client.get_by_names(deref_agent.knowledge_base)

        name_id_lookup = {}
        for kb in matching_knowledge_bases:
            if kb.get("name") in name_id_lookup:
                logger.error(f"Duplicate draft entries for knowledge base '{kb.get('name')}'")
                sys.exit(1)
            name_id_lookup[kb.get("name")] = kb.get("id")
        
        deref_knowledge_bases = []
        for name in agent.knowledge_base:
            id = name_id_lookup.get(name)
            if not id:
                logger.error(f"Failed to find knowledge base. No knowledge base found with the name '{name}'")
                sys.exit(1)
            deref_knowledge_bases.append(id)
        deref_agent.knowledge_base = deref_knowledge_bases

        return deref_agent
    
    def reference_knowledge_bases(self, agent: Agent) -> Agent:
        client = self.get_knowledge_base_client()

        ref_agent = deepcopy(agent)
        
        ref_knowledge_bases = []
        for id in agent.knowledge_base:
            matching_knowledge_base = client.get_by_id(id)
            name = matching_knowledge_base.get("name")
            if not name:
                logger.error(f"Failed to find knowledge base. No knowledge base found with the id '{id}'")
                sys.exit(1)
            ref_knowledge_bases.append(name)
        ref_agent.knowledge_base = ref_knowledge_bases
        return ref_agent
    
    def dereference_guidelines(self, agent: Agent) -> Agent:
        tool_client = self.get_tool_client()
        
        guideline_tool_names = set()

        for guideline in agent.guidelines:
            if guideline.tool:
                guideline_tool_names.add(guideline.tool)
        
        if len(guideline_tool_names) == 0:
            return agent

        deref_agent = deepcopy(agent)

        matching_tools = tool_client.get_drafts_by_names(list(guideline_tool_names))

        name_id_lookup = {}
        for tool in matching_tools:
            if tool.get("name") in name_id_lookup:
                logger.error(f"Duplicate draft entries for tool '{tool.get('name')}'")
                sys.exit(1)
            name_id_lookup[tool.get("name")] = tool.get("id")
        
        for guideline in deref_agent.guidelines:
            if guideline.tool:
                id = name_id_lookup.get(guideline.tool)
                if not id:
                    logger.error(f"Failed to find guideline tool. No tools found with the name '{guideline.tool}'")
                    sys.exit(1)
                guideline.tool = id

        return deref_agent
    
    def reference_guidelines(self, agent: Agent) -> Agent:
        tool_client = self.get_tool_client()
        
        guideline_tool_ids = set()

        for guideline in agent.guidelines:
            if guideline.tool:
                guideline_tool_ids.add(guideline.tool)
        
        if len(guideline_tool_ids) == 0:
            return agent

        ref_agent = deepcopy(agent)

        matching_tools = tool_client.get_drafts_by_ids(list(guideline_tool_ids))

        id_name_lookup = {}
        for tool in matching_tools:
            if tool.get("id") in id_name_lookup:
                logger.error(f"Duplicate draft entries for tool '{tool.get('id')}'")
                sys.exit(1)
            id_name_lookup[tool.get("id")] = tool.get("name")
        
        for guideline in ref_agent.guidelines:
            if guideline.tool:
                name = id_name_lookup.get(guideline.tool)
                if not name:
                    logger.error(f"Failed to find guideline tool. No tools found with the id '{guideline.tool}'")
                    sys.exit(1)
                guideline.tool = name

        return ref_agent
    
    def get_voice_config_name_from_id(self, voice_config_id: str) -> str | None:
        client = self.get_voice_configuration_client()
        config = client.get_by_id(voice_config_id)
        return config.name if config else None

    def get_voice_config_id_from_name(self, voice_config_name: str) -> str | None:
        client = self.get_voice_configuration_client()
        configs = client.get_by_name(voice_config_name)

        if len(configs) == 0:
            logger.error(f"No voice_configs with the name '{voice_config_name}' found. Failed to get config")
            sys.exit(1)
        
        if len(configs) > 1:
            logger.error(f"Multiple voice_configs with the name '{voice_config_name}' found. Failed to get config")
            sys.exit(1)
        
        return configs[0].voice_configuration_id


    def reference_voice_config(self,agent: Agent):
        deref_agent = deepcopy(agent)
        deref_agent.voice_configuration = self.get_voice_config_name_from_id(agent.voice_configuration_id)
        del deref_agent.voice_configuration_id
        return deref_agent

    def dereference_voice_config(self,agent: Agent):
        ref_agent = deepcopy(agent)
        ref_agent.voice_configuration_id = self.get_voice_config_id_from_name(agent.voice_configuration)
        del ref_agent.voice_configuration
        return ref_agent

    @staticmethod
    def dereference_app_id(agent: ExternalAgent | AssistantAgent) -> ExternalAgent | AssistantAgent:
        if agent.kind == AgentKind.EXTERNAL:
            agent.connection_id = get_conn_id_from_app_id(agent.app_id)
        else:
            agent.config.connection_id = get_conn_id_from_app_id(agent.config.app_id)

        return agent
    
    @staticmethod
    def reference_app_id(agent: ExternalAgent | AssistantAgent) -> ExternalAgent | AssistantAgent:
        if agent.kind == AgentKind.EXTERNAL:
            agent.app_id = get_app_id_from_conn_id(agent.connection_id)
            agent.connection_id = None
        else:
            agent.config.app_id = get_app_id_from_conn_id(agent.config.connection_id)
            agent.config.connection_id = None

        return agent
    
    def dereference_common_agent_dependencies(self, agent: AnyAgentT) -> AnyAgentT:
        if agent.voice_configuration:
            agent = self.dereference_voice_config(agent)

        return agent  

    def reference_common_agent_dependencies(self, agent: AnyAgentT) -> AnyAgentT:
        if agent.voice_configuration_id:
            agent = self.reference_voice_config(agent)

        return agent

    def dereference_native_agent_dependencies(self, agent: Agent) -> Agent:
        if agent.collaborators and len(agent.collaborators):
            agent = self.dereference_collaborators(agent)

        plugins_has_entries = (
            (agent.plugins.agent_pre_invoke and len(agent.plugins.agent_pre_invoke) > 0) or
            (agent.plugins.agent_post_invoke and len(agent.plugins.agent_post_invoke) > 0)
        )

        if (agent.tools and len(agent.tools) > 0) or \
        (agent.style == AgentStyle.PLANNER and agent.custom_join_tool) or \
        plugins_has_entries:
            agent = self.dereference_tools(agent)

        if agent.knowledge_base and len(agent.knowledge_base) > 0:
            agent = self.dereference_knowledge_bases(agent)
        if agent.guidelines and len(agent.guidelines) > 0:
            agent = self.dereference_guidelines(agent)

        return agent
    
    def reference_native_agent_dependencies(self, agent: Agent) -> Agent:
        if agent.collaborators and len(agent.collaborators):
            agent = self.reference_collaborators(agent)
        if (agent.tools and len(agent.tools)) or (agent.style == AgentStyle.PLANNER and agent.custom_join_tool) or (agent.plugins is not None):
            agent = self.reference_tools(agent)
        if agent.knowledge_base and len(agent.knowledge_base):
            agent = self.reference_knowledge_bases(agent)
        if agent.guidelines and len(agent.guidelines):
            agent = self.reference_guidelines(agent)

        return agent
    
    def dereference_external_or_assistant_agent_dependencies(self, agent: ExternalAgent | AssistantAgent) -> ExternalAgent | AssistantAgent:
        agent_dict = agent.model_dump()

        if agent_dict.get("app_id") or agent.config.model_dump().get("app_id"):
            agent = self.dereference_app_id(agent)

        return agent

    def reference_external_or_assistant_agent_dependencies(self, agent: ExternalAgent | AssistantAgent) -> ExternalAgent | AssistantAgent:
        agent_dict = agent.model_dump()

        if agent_dict.get("connection_id") or agent.config.model_dump().get("connection_id"):
            agent = self.reference_app_id(agent)

        return agent
    
    # Convert all names used in an agent to the corresponding ids
    def dereference_agent_dependencies(self, agent: AnyAgentT) -> AnyAgentT:

        agent = self.dereference_common_agent_dependencies(agent)
        if isinstance(agent, Agent):
            return self.dereference_native_agent_dependencies(agent)
        if isinstance(agent, ExternalAgent) or isinstance(agent, AssistantAgent):
            return self.dereference_external_or_assistant_agent_dependencies(agent)

    # Convert all ids used in an agent to the corresponding names
    def reference_agent_dependencies(self, agent: AnyAgentT) -> AnyAgentT:

        agent = self.reference_common_agent_dependencies(agent)
        if isinstance(agent, Agent):
            return self.reference_native_agent_dependencies(agent)
        if isinstance(agent, ExternalAgent) or isinstance(agent, AssistantAgent):
            return self.reference_external_or_assistant_agent_dependencies(agent)

    def publish_or_update_agents(
        self, agents: Iterable[Agent | CustomAgent | ExternalAgent | AssistantAgent]
    ):
        for agent in agents:
            # Check for existing agents by name
            agent_name = agent.name

            native_client = self.get_native_client()
            external_client = self.get_external_client()
            assistant_client = self.get_assistant_client()

            existing_native_agents = native_client.get_draft_by_name(agent_name)
            existing_native_agents = [Agent.model_validate(agent) for agent in existing_native_agents]
            existing_external_clients = external_client.get_draft_by_name(agent_name)
            existing_external_clients = [ExternalAgent.model_validate(agent) for agent in existing_external_clients]
            existing_assistant_clients = assistant_client.get_draft_by_name(agent_name)
            existing_assistant_clients = [AssistantAgent.model_validate(agent) for agent in existing_assistant_clients]

            all_existing_agents = existing_external_clients + existing_native_agents + existing_assistant_clients
            
            agent = self.dereference_agent_dependencies(agent)

            if isinstance(agent, Agent) and agent.style == AgentStyle.PLANNER and isinstance(agent.custom_join_tool, str):
                tool_client = self.get_tool_client()

                join_tool_spec = ToolSpec.model_validate(
                    tool_client.get_draft_by_id(agent.custom_join_tool)
                )
                if not join_tool_spec.is_custom_join_tool():
                    logger.error(
                        f"Tool '{join_tool_spec.name}' configured as the custom join tool is not a valid join tool. A custom join tool must be a Python tool with specific input and output schema."
                    )
                    sys.exit(1)

            agent_kind = agent.kind

            if len(all_existing_agents) > 1:
                logger.error(f"Multiple agents with the name '{agent_name}' found. Failed to update agent")
                sys.exit(1)

            if len(all_existing_agents) > 0:
                existing_agent = all_existing_agents[0]
                agent_name = agent.name

                if agent_name == existing_agent.name:
                    if agent_kind != existing_agent.kind:
                        logger.error(f"An agent with the name '{agent_name}' already exists with a different kind. Failed to create agent")
                        sys.exit(1)
                    agent_id = existing_agent.id
                    self.update_agent(agent_id=agent_id, agent=agent)
            else:
                self.publish_agent(agent)

    @staticmethod
    def _create_agent_zip(package_root: str, config_file: str | None = None) -> tuple[str, str | None]:
        """
        Create a temporary zip file from a directory for custom agent upload.
        
        Args:
            package_root: Path to the directory to zip
            config_file: Optional path to a config.yaml file to include in the zip
            
        Returns:
            Tuple of (path to the created temporary zip file, agent name from config or None)
        """
        # Create a temporary file that won't be automatically deleted
        temp_fd, temp_path = tempfile.mkstemp(suffix='.zip', prefix='agent_package_')
        os.close(temp_fd)
        
        agent_name = None
        
        try:
            with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add all files from package_root
                for root, _, files in os.walk(package_root):
                    for file in files:
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, start=package_root)
                        zip_file.write(full_path, arcname=relative_path)
                        
                        # Try to extract agent name from agent.yaml
                        if agent_name is None and file.lower() in ['agent.yaml', 'agent.yml']:
                            try:
                                with open(full_path, 'r') as f:
                                    config_data = yaml.load(f, Loader=yaml.SafeLoader)
                                    agent_name = config_data.get('name')
                            except Exception as e:
                                logger.warning(f"Failed to parse config file for agent name: {e}")
                
                # Add config file if provided and not already in package_root
                if config_file:
                    config_filename = os.path.basename(config_file)
                    # Check if config.yaml already exists in the zip
                    if config_filename not in zip_file.namelist():
                        zip_file.write(config_file, arcname=config_filename)
                        # Try to extract agent name from the provided config file
                        if agent_name is None:
                            try:
                                with open(config_file, 'r') as f:
                                    config_data = yaml.load(f, Loader=yaml.SafeLoader)
                                    # Try 'name' field first (new format)
                                    agent_name = config_data.get('name')
                            except Exception as e:
                                logger.warning(f"Failed to parse config file for agent name: {e}")
                    else:
                        logger.warning(f"Config file '{config_filename}' already exists in package root, using the one from package root")
            
            logger.info(f"Created temporary zip file from directory: {package_root}")
            if agent_name:
                logger.info(f"Detected agent name from config: {agent_name}")
                return temp_path, agent_name
            
            # Clean up temp file if no agent name found
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.error(
                f"No agent name found in config file. Please ensure your package contains "
                f"an 'agent.yaml' file with a 'name' field."
            )
            sys.exit(1)
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    @staticmethod
    def _upload_custom_agent_artifact(
        native_client: AgentClient,
        agent_id: str,
        custom_agent_file_path: str
    ) -> tuple[dict | None, bool]:
        """
        Upload a custom agent artifact and return the response and temp file flag.
        
        Args:
            native_client: The agent client instance
            agent_id: The agent ID to upload to
            custom_agent_file_path: Path to the zip file
            
        Returns:
            Tuple of (upload_response, is_temp_file)
        """
        upload_response = None
        is_temp_file = False
        
        if custom_agent_file_path:
            logger.info(f"Uploading custom agent package...")
            upload_response = native_client.upload_agent_artifact(
                agent_id=agent_id,
                file_path=custom_agent_file_path
            )
            logger.info(f"Custom agent package uploaded successfully")
            
            # Check if this is a temporary file
            if custom_agent_file_path.startswith(tempfile.gettempdir()):
                is_temp_file = True
        
        return upload_response, is_temp_file
    
    @staticmethod
    def _display_custom_agent_config(
        config: CustomAgentConfig,
        agent_id: str,
        agent_name: str,
        is_update: bool = False
    ) -> None:
        """
        Display custom agent configuration details in a formatted table.
        
        Args:
            config: The configuration from upload response
            agent_id: The agent ID
            agent_name: The agent name
            is_update: Whether this is an update operation
        """
        console = Console()
        
        # Display operation type
        operation = "Updated" if is_update else "Created"
        logger.info(f"Agent '{agent_name}' {operation.lower()} successfully")
        
        # Create a panel with agent info
        info_panel = Panel(
            f"[bold cyan]Agent ID:[/bold cyan] {agent_id}\n"
            f"[bold cyan]Operation:[/bold cyan] {operation}\n"
            f"[bold cyan]Name:[/bold cyan] {agent_name}",
            title=f"[bold green]✓ Custom Agent {operation}[/bold green]",
            border_style="green"
        )
        console.print(info_panel)
        
        # Create a table for the custom agent configuration
        config_table = Table(
            title="Configuration Details",
            show_header=True,
            header_style="bold cyan",
            show_lines=True,
        )
        config_table.add_column("Property", style="cyan", no_wrap=True)
        config_table.add_column("Value", style="green")
        
        config_table.add_row("Language", config.language)
        config_table.add_row("Framework", config.framework)
        config_table.add_row("Entrypoint", config.entrypoint)
        config_table.add_row("Agent Name", config.agent_name)
        config_table.add_row("Agent Description", config.agent_description)
        config_table.add_row("Requirements", '\n'.join(config.requirements) if config.requirements else "None")
        config_table.add_row("Files in Package", str(config.file_count))
        
        console.print(config_table)
    
    @staticmethod
    def _cleanup_temp_file(file_path: str, is_temp: bool) -> None:
        """
        Clean up a temporary file if needed.
        
        Args:
            file_path: Path to the file
            is_temp: Whether the file is temporary
        """
        if is_temp and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.debug(f"Cleaned up temporary zip file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary zip file: {e}")

    def publish_agent(self, agent: Agent | CustomAgent | ExternalAgent | AssistantAgent, **kwargs) -> None:
        if isinstance(agent, Agent):
            # Get the raw response to check for custom agent config
            native_client = self.get_native_client()
            response_data = native_client._post(
                native_client.base_endpoint,
                data=transform_agents_from_flat_agent_spec(agent.model_dump(exclude_none=True))
            )
            response = AgentUpsertResponse.model_validate(response_data)
            _raise_guidelines_warning(response)
            
            # Check if this is a custom agent - always upload if file path provided
            if agent.style == AgentStyle.CUSTOM and isinstance(response_data, dict):
                custom_agent_file_path = getattr(agent, 'custom_agent_file_path', None) or kwargs.get('custom_agent_file_path')
                
                if custom_agent_file_path:
                    if response.id:
                        # Upload artifact using helper
                        upload_response, is_temp_file = self._upload_custom_agent_artifact(
                            self.get_native_client(),
                            response.id,
                            custom_agent_file_path
                        )
                        
                        # Display configuration if available
                        if upload_response:
                            try:
                                response_model = CustomAgentUploadResponse.model_validate(upload_response)
                                if response_model.config:
                                    agent_name = response_model.config.agent_name or agent.name
                                    self._display_custom_agent_config(response_model.config, response.id, agent_name, is_update=False)
                                else:
                                    logger.info(f"Agent '{agent.name}' imported successfully")
                            except Exception as e:
                                logger.warning(f"Could not parse upload response: {e}")
                                logger.info(f"Agent '{agent.name}' imported successfully")
                        else:
                            logger.info(f"Agent '{agent.name}' imported successfully")
                        
                        # Clean up temporary file
                        self._cleanup_temp_file(custom_agent_file_path, is_temp_file)
                else:
                    logger.info(f"Agent '{agent.name}' imported successfully")
            else:
                logger.info(f"Agent '{agent.name}' imported successfully")
                
        if isinstance(agent, ExternalAgent):
            self.get_external_client().create(agent.model_dump(exclude_none=True))
            logger.info(f"External Agent '{agent.name}' imported successfully")
        if isinstance(agent, AssistantAgent):
            self.get_assistant_client().create(agent.model_dump(exclude_none=True, by_alias=True))
            logger.info(f"Assistant Agent '{agent.name}' imported successfully")

    def update_agent(
        self, agent_id: str, agent: Agent | CustomAgent | ExternalAgent | AssistantAgent, **kwargs
    ) -> None:
        if isinstance(agent, Agent):
            logger.info(f"Existing Agent '{agent.name}' found. Updating...")
            exclude_fields = {'custom_agent_file_path'} if hasattr(agent, 'custom_agent_file_path') else None
            response = self.get_native_client().update(agent_id, agent.model_dump(exclude_none=True, exclude=exclude_fields))
            _raise_guidelines_warning(response)
            
            # Handle custom agent artifact upload for updates
            if agent.style == AgentStyle.CUSTOM:
                custom_agent_file_path = getattr(agent, 'custom_agent_file_path', None) or kwargs.get('custom_agent_file_path')
                
                if custom_agent_file_path:
                    # Upload artifact using helper
                    upload_response, is_temp_file = self._upload_custom_agent_artifact(
                        self.get_native_client(),
                        agent_id,
                        custom_agent_file_path
                    )
                    
                    # Display configuration if available
                    if upload_response and 'config' in upload_response:
                        config_dict = upload_response.get('config', {})
                        try:
                            config = CustomAgentConfig.model_validate(config_dict)
                            agent_name = config.agent_name or agent.name
                            self._display_custom_agent_config(config, agent_id, agent_name, is_update=True)
                        except Exception as e:
                            logger.warning(f"Could not parse upload response config: {e}")
                            logger.info(f"Agent '{agent.name}' updated successfully")
                    else:
                        logger.info(f"Agent '{agent.name}' updated successfully")
                    
                    # Clean up temporary file
                    self._cleanup_temp_file(custom_agent_file_path, is_temp_file)
                else:
                    logger.info(f"Agent '{agent.name}' updated successfully")
            else:
                logger.info(f"Agent '{agent.name}' updated successfully")
                
        if isinstance(agent, ExternalAgent):
            logger.info(f"Existing External Agent '{agent.name}' found. Updating...")
            self.get_external_client().update(agent_id, agent.model_dump(exclude_none=True))
            logger.info(f"External Agent '{agent.name}' updated successfully")
        if isinstance(agent, AssistantAgent):
            logger.info(f"Existing Assistant Agent '{agent.name}' found. Updating...")
            self.get_assistant_client().update(agent_id, agent.model_dump(exclude_none=True, by_alias=True))
            logger.info(f"Assistant Agent '{agent.name}' updated successfully")

    @staticmethod
    def persist_record(agent: Agent, **kwargs):
        if "output_file" in kwargs and kwargs["output_file"] is not None:
            agent.spec_version = SpecVersion.V1
            agent.dump_spec(kwargs["output_file"])

    def get_agent_tool_names(self, tool_ids: List[str]) -> List[str]:
        """Retrieve tool names for a given agent based on tool IDs."""
        tool_client = self.get_tool_client()
        tools = []
        for tool_id in tool_ids:
            try:
                tool = tool_client.get_draft_by_id(tool_id)
                tools.append(tool["name"])
            except Exception as e:
                logger.warning(f"Tool with ID {tool_id} not found. Returning Tool ID")
                tools.append(tool_id)
        return tools

    def get_agent_collaborator_names(self, agent_ids: List[str]) -> List[str]:
        """Retrieve collaborator names for a given agent based on collaborator IDs."""
        collaborator_client = self.get_native_client()
        external_client = self.get_external_client()
        assistant_client = self.get_assistant_client()
        collaborators = []
        
        for agent_id in agent_ids:
            try:
                # First try resolving from native agents
                collaborator = collaborator_client.get_draft_by_id(agent_id)
                if collaborator:
                    collaborators.append(collaborator["name"])
                    continue
            except Exception:
                pass

            try:
                # If not found in native, check external agents
                external_collaborator = external_client.get_draft_by_id(agent_id)
                if external_collaborator:
                    collaborators.append(external_collaborator["name"])
                    continue
            except Exception:
                pass

            try:
                # If not found in native or external, check assistant agents
                assistant_collaborator = assistant_client.get_draft_by_id(agent_id)
                if assistant_collaborator:
                    collaborators.append(assistant_collaborator["name"])
                    continue
            except Exception:
                pass

            logger.warning(f"Collaborator with ID {agent_id} not found. Returning Collaborator ID")
            collaborators.append(agent_id)

        return collaborators

    def get_agent_knowledge_base_names(self, knowlede_base_ids: List[str]) -> List[str]:
        """Retrieve knowledge base names for a given agent based on knowledge base IDs."""
        client = self.get_knowledge_base_client()
        knowledge_bases = []
        for id in knowlede_base_ids:
            try:
                kb = client.get_by_id(id)
                knowledge_bases.append(kb["name"])
            except Exception as e:
                logger.warning(f"Knowledge base with ID {id} not found. Returning Tool ID")
                knowledge_bases.append(id)
        return knowledge_bases
    
    def _fetch_and_parse_agents(self, target_agent_kind: AgentKind) -> tuple[List[Agent] | List[ExternalAgent] | List[AssistantAgent], List[List[str]]]:
        parse_errors = []
        target_kind_display_name = None
        target_kind_class = None
        agent_client = None

        match(target_agent_kind):
            case AgentKind.NATIVE:
                target_kind_display_name = "Agent"
                target_kind_class = Agent
                agent_client = self.get_native_client()
            case AgentKind.EXTERNAL:
                target_kind_display_name = "External Agent"
                target_kind_class = ExternalAgent
                agent_client = self.get_external_client()
            case AgentKind.ASSISTANT:
                target_kind_display_name = "Assistant Agent"
                target_kind_class = AssistantAgent
                agent_client = self.get_assistant_client()
            case _:
                return ([], [[f"Invalid Agent kind '{target_agent_kind}'"]])
        
        response = agent_client.get()
        agents = []
        for agent in response:
            try:
                agents.append(target_kind_class.model_validate(agent))
            except Exception as e:
                name = agent.get('name', None)
                parse_errors.append([
                    f"{target_kind_display_name} '{name}' could not be parsed",
                    json.dumps(agent),
                    e
                ])
        return (agents, parse_errors)

    def _get_all_unique_agent_resources(self, agents: List[Agent], target_attr: str) -> List[str]:
        """
        Given a list of agents, get all unique values of a certain field.
        Handles both flat lists (like agent.tools = [id1, id2]) and nested plugin objects.
        """
        all_ids = set()

        for agent in agents:
            attr_value = getattr(agent, target_attr, None)
            if not attr_value:
                continue

            # Special handling for Plugins model
            if target_attr == "plugins" and hasattr(attr_value, "agent_pre_invoke"):
                for plugin_ref in getattr(attr_value, "agent_pre_invoke", []):
                    all_ids.add(plugin_ref.plugin_id)
                for plugin_ref in getattr(attr_value, "agent_post_invoke", []):
                    all_ids.add(plugin_ref.plugin_id)

            elif isinstance(attr_value, list):
                all_ids.update(attr_value)

            else:
                all_ids.add(attr_value)

        return list(all_ids)

    def _construct_lut_agent_resource(self, resource_list: List[dict], key_attr: str, value_attr) -> dict:
        """
            Given a list of dictionaries build a key -> value look up table
            Example [{id: 1, name: obj1}, {id: 2, name: obj2}] return {1: obj1, 2: obj2}

            Args:
                resource_list: A list of dictionries from which to build the lookup table from
                key_attr: The name of the field whose value will form the key of the lookup table
                value_attrL The name of the field whose value will form the value of the lookup table

            Returns:
                A lookup table
        """
        lut = {}
        for resource in resource_list:
            if isinstance(resource, BaseModel):
                resource = resource.model_dump()
            lut[resource.get(key_attr, None)] = resource.get(value_attr, None)
        return lut
    
    def _lookup_agent_resource_value(
        self,
        agent: Agent, 
        lookup_table: dict[str, str], 
        target_attr: str,
        target_attr_display_name: str
    ) -> list[str] | str | None:
        """
        Using a lookup table convert all the strings in a given field of an agent into their equivalent in the lookup table
        Example: lookup_table={1: obj1, 2: obj2} agent=Agent(tools=[1,2]) return. [obj1, obj2]

        This function also takes into account plugins.

        Args:
            agent: An agent
            lookup_table: A dictionary that maps one value to another
            target_attr: The field to convert on the provided agent
            target_attr_display_name: The name of the field to be displayed in the event of an error
        """
        attr_value = getattr(agent, target_attr, None)
        if not attr_value:
            return None

        # Special case for Plugins
        if target_attr == "plugins" and hasattr(attr_value, "agent_pre_invoke"):
            resolved_names = []

            for plugin_ref in getattr(attr_value, "agent_pre_invoke", []):
                plugin_id = plugin_ref.plugin_id
                resolved_names.append(lookup_table.get(plugin_id, plugin_id))

            for plugin_ref in getattr(attr_value, "agent_post_invoke", []):
                plugin_id = plugin_ref.plugin_id
                resolved_names.append(lookup_table.get(plugin_id, plugin_id))

            return resolved_names

        # Normal list of strings
        if isinstance(attr_value, list):
            new_resource_list = []
            for value in attr_value:
                if value in lookup_table:
                    new_resource_list.append(lookup_table[value])
                else:
                    logger.warning(f"{target_attr_display_name} with ID '{value}' not found. Returning {target_attr_display_name} ID")
                    new_resource_list.append(value)
            return new_resource_list

        # Single string
        if attr_value in lookup_table:
            return lookup_table[attr_value]
        else:
            logger.warning(f"{target_attr_display_name} with ID '{attr_value}' not found. Returning {target_attr_display_name} ID")
            return attr_value

    def _batch_request_resource(self, client_fn, ids, batch_size=50) -> List[dict]:
        resources = []
        for i in range(0, len(ids), batch_size):
                chunk = ids[i:i + batch_size]
                resources += (client_fn(chunk))
        return resources


    def _bulk_resolve_agent_tools(self, agents: List[Agent]) -> List[Agent]:
        new_agents = agents.copy()
        all_tools_ids = self._get_all_unique_agent_resources(new_agents, "tools")
        if not all_tools_ids:
            return new_agents
        
        all_tools = self._batch_request_resource(self.get_tool_client().get_drafts_by_ids, all_tools_ids)

        tool_lut = self._construct_lut_agent_resource(all_tools, "id", "name")
        
        for agent in new_agents:
            tool_names = self._lookup_agent_resource_value(agent, tool_lut, "tools", "Tool")
            if tool_names:
                agent.tools = tool_names
        return new_agents
    
    def _bulk_resolve_agent_plugins(self, agents: List[Agent]) -> List[Agent]:
        new_agents = agents.copy()
        all_plugin_ids = self._get_all_unique_agent_resources(new_agents, "plugins")
        if not all_plugin_ids:
            return new_agents

        all_plugins = self._batch_request_resource(self.get_tool_client().get_drafts_by_ids, all_plugin_ids)

        plugin_lut = self._construct_lut_agent_resource(all_plugins, "id", "name")

        for agent in new_agents:
            plugin_names = self._lookup_agent_resource_value(agent, plugin_lut, "plugins", "Plugin")
            if plugin_names:
                agent.plugins = plugin_names
        return new_agents

    def _bulk_resolve_agent_knowledge_bases(self, agents: List[Agent]) -> List[Agent]:
        new_agents = agents.copy()
        all_kb_ids = self._get_all_unique_agent_resources(new_agents, "knowledge_base")
        if not all_kb_ids:
            return new_agents

        all_kbs = self._batch_request_resource(self.get_knowledge_base_client().get_by_ids, all_kb_ids)

        kb_lut = self._construct_lut_agent_resource(all_kbs, "id", "name")
        
        for agent in new_agents:
            kb_names = self._lookup_agent_resource_value(agent, kb_lut, "knowledge_base", "Knowledge Base")
            if kb_names:
                agent.knowledge_base = kb_names
        return new_agents
    
    def _bulk_resolve_agent_collaborators(self, agents: List[Agent]) -> List[Agent]:
        new_agents = agents.copy()
        all_collab_ids = self._get_all_unique_agent_resources(new_agents, "collaborators")
        if not all_collab_ids:
            return new_agents

        native_agents = self._batch_request_resource(self.get_native_client().get_drafts_by_ids, all_collab_ids)
        external_agents = self._batch_request_resource(self.get_external_client().get_drafts_by_ids, all_collab_ids)
        assitant_agents = self._batch_request_resource(self.get_assistant_client().get_drafts_by_ids, all_collab_ids)

        all_collabs = native_agents + external_agents + assitant_agents

        collab_lut = self._construct_lut_agent_resource(all_collabs, "id", "name")
        
        for agent in new_agents:
            collab_names = self._lookup_agent_resource_value(agent, collab_lut, "collaborators", "Collaborator")
            if collab_names:
                agent.collaborators = collab_names
        return new_agents

    def _bulk_resolve_agent_app_ids(self , agents: List[ExternalAgent] | List[AssistantAgent], is_assistant: bool = False) -> List[ExternalAgent] | List[AssistantAgent]:
        new_agents = agents.copy()
        all_conn_ids = []
        if is_assistant:
            configs = [a.config for a in new_agents] 
            all_conn_ids = self._get_all_unique_agent_resources(configs, "connection_id")
        else:
            all_conn_ids = self._get_all_unique_agent_resources(new_agents, "connection_id")
        if not all_conn_ids:
            return new_agents
        
        all_connections = self._batch_request_resource(get_connections_client().get_drafts_by_ids, all_conn_ids)

        connection_lut = self._construct_lut_agent_resource(all_connections, "connection_id", "app_id")
        
        for agent in new_agents:
            conn_id_location = agent.config if is_assistant else agent
            app_id = self._lookup_agent_resource_value(conn_id_location, connection_lut, "connection_id", "Connection")
            if app_id:
                if is_assistant:
                    agent.config.app_id = app_id
                else:
                    agent.app_id = app_id
        return new_agents

    def list_agents(self, kind: AgentKind=None, verbose: bool=False, format: ListFormats | None = None) -> dict[str, dict] | dict[str, str] | None:
        """
        List agents in the active wxo environment

        Args:
            kind: Filter to only list a certain kind of agent. Allowed values "native", "assistant", "external"
            verbose: Show raw json output without table formatting or id to name resolution
            format: Optional value. If provided print nothing and return a string containing the agents in the requested format. Allowed values "table", "json" 
        """
        if verbose and format:
            logger.error("For agents list, `--verbose` and `--format` are mutually exclusive options")
            sys.exit(1)

        parse_errors = []
        output_dictionary = {
                "native": None,
                "assistant": None,
                "external": None 
        }

        if kind == AgentKind.NATIVE or kind is None:
            native_agents, new_parse_errors = self._fetch_and_parse_agents(AgentKind.NATIVE)
            parse_errors += new_parse_errors

            if verbose:
                agents_list = []
                for agent in native_agents:
                    agents_list.append(json.loads(agent.dumps_spec()))

                output_dictionary["native"] = agents_list
            else:
                resolved_native_agents = self._bulk_resolve_agent_tools(native_agents)
                resolved_native_agents = self._bulk_resolve_agent_plugins(native_agents)
                resolved_native_agents = self._bulk_resolve_agent_knowledge_bases(resolved_native_agents)
                resolved_native_agents = self._bulk_resolve_agent_collaborators(resolved_native_agents)

                if format and format == ListFormats.JSON:
                    agents_list = []
                    for agent in resolved_native_agents:
                        agents_list.append(json.loads(agent.dumps_spec()))

                    output_dictionary["native"] = agents_list
                else:
                    native_table = rich.table.Table(
                        show_header=True, 
                        header_style="bold white", 
                        title="Agents",
                        show_lines=True
                    )

                    column_args = {
                        "Name": {"overflow": "fold"},
                        "Description": {},
                        "LLM": {"overflow": "fold"},
                        "Style": {},
                        "Collaborators": {},
                        "Tools": {},
                        "Plugins": {},
                        "Knowledge Base": {},
                        "ID": {"overflow": "fold"},
                    }
                    for column in column_args:
                        native_table.add_column(column, **column_args[column])

                    for agent in resolved_native_agents:
                        # If agent.plugins might be a list of tuples
                        # Build plugin strings for display
                        plugin_strings = []
                        if agent.plugins:
                            # If it's a Plugins object
                            if hasattr(agent.plugins, "agent_pre_invoke"):
                                plugin_strings.extend(
                                    [p.plugin_name for p in agent.plugins.agent_pre_invoke if p.plugin_name]
                                )
                                plugin_strings.extend(
                                    [p.plugin_name for p in agent.plugins.agent_post_invoke if p.plugin_name]
                                )
                            elif isinstance(agent.plugins, list):
                                for p in agent.plugins:
                                    if isinstance(p, dict) and "plugin_name" in p:
                                        plugin_strings.append(p["plugin_name"])
                                    elif isinstance(p, str):
                                        plugin_strings.append(p)
                        agent_name = self._format_agent_display_name(agent)
                        native_table.add_row(
                            agent_name,
                            agent.description,
                            agent.llm,
                            agent.style,
                            ", ".join(agent.collaborators),
                            ", ".join(agent.tools),
                            ", ".join(plugin_strings),
                            ", ".join(agent.knowledge_base),
                            agent.id,
                        )
                    if format == ListFormats.Table:
                        output_dictionary["native"] = rich_table_to_markdown(native_table)
                    else:
                        rich.print(native_table)
      
        if kind == AgentKind.EXTERNAL or kind is None:
            external_agents, new_parse_errors = self._fetch_and_parse_agents(AgentKind.EXTERNAL)
            parse_errors += new_parse_errors

            if verbose:
                external_agents_list = []
                for agent in external_agents:
                    external_agents_list.append(json.loads(agent.dumps_spec()))
                output_dictionary["external"] = external_agents_list
            else:
                resolved_external_agents = self._bulk_resolve_agent_app_ids(external_agents)
                
                if format and format == ListFormats.JSON:
                    external_agents_list = []
                    for agent in resolved_external_agents:
                        external_agents_list.append(json.loads(agent.dumps_spec()))

                    output_dictionary["external"] = external_agents_list
                else:
                    external_table = rich.table.Table(
                        show_header=True, 
                        header_style="bold white", 
                        title="External Agents",
                        show_lines=True
                    )
                    column_args = {
                        "Name": {"overflow": "fold"},
                        "Title": {},
                        "Description": {},
                        "Tags": {},
                        "API URL": {"overflow": "fold"},
                        "Chat Params": {},
                        "Config": {},
                        "Nickname": {},
                        "App ID": {"overflow": "fold"},
                        "ID": {"overflow": "fold"}
                    }
                    
                    for column in column_args:
                        external_table.add_column(column, **column_args[column])
                    
                    for agent in resolved_external_agents:
                        agent_name = self._format_agent_display_name(agent)
                        external_table.add_row(
                            agent_name,
                            agent.title,
                            agent.description,
                            ", ".join(agent.tags or []),
                            agent.api_url,
                            json.dumps(agent.chat_params),
                            str(agent.config),
                            agent.nickname,
                            agent.app_id,
                            agent.id
                        )
                    if format == ListFormats.Table:
                        output_dictionary["external"] = rich_table_to_markdown(external_table)
                    else:
                        rich.print(external_table)
        
        if kind == AgentKind.ASSISTANT or kind is None:
            assistant_agents, new_parse_errors = self._fetch_and_parse_agents(AgentKind.ASSISTANT)
            parse_errors += new_parse_errors

            if verbose:
                assistant_agents_list = []
                for agent in assistant_agents:
                    assistant_agents_list.append(json.loads(agent.dumps_spec()))
                output_dictionary["assistant"] = assistant_agents_list
            else:
                resolved_assistant_agents = self._bulk_resolve_agent_app_ids(assistant_agents, is_assistant=True)
                
                if format and format == ListFormats.JSON:
                    assistant_agents_list = []
                    for agent in resolved_assistant_agents:
                        assistant_agents_list.append(json.loads(agent.dumps_spec()))

                    output_dictionary["assistant"] = assistant_agents_list
                else:
                    assistants_table = rich.table.Table(
                        show_header=True, 
                        header_style="bold white", 
                        title="Assistant Agents",
                        show_lines=True)
                    column_args = {
                        "Name": {"overflow": "fold"},
                        "Title": {},
                        "Description": {},
                        "Tags": {},
                        "Nickname": {},
                        "CRN": {},
                        "Instance URL": {},
                        "Assistant ID": {"overflow": "fold"},
                        "Environment ID": {"overflow": "fold"},
                        "ID": {"overflow": "fold"}
                    }
                    
                    for column in column_args:
                        assistants_table.add_column(column, **column_args[column])
                    
                    for agent in resolved_assistant_agents:
                        agent_name = self._format_agent_display_name(agent)
                        assistants_table.add_row(
                            agent_name,
                            agent.title,
                            agent.description,
                            ", ".join(agent.tags or []),
                            agent.nickname,
                            agent.config.crn,
                            agent.config.service_instance_url,
                            agent.config.assistant_id,
                            agent.config.environment_id,
                            agent.id
                        )
                    if format == ListFormats.Table:
                        output_dictionary["assistant"] = rich_table_to_markdown(assistants_table)
                    else:
                        rich.print(assistants_table)

        if verbose:
            rich.print_json(data=output_dictionary)

        for error in parse_errors:
            for l in error:
                logger.error(l)
        
        if verbose or format:
            return output_dictionary
        

    def remove_agent(self, name: str, kind: AgentKind):
        try:
            if kind == AgentKind.NATIVE:
                client = self.get_native_client()
            elif kind == AgentKind.EXTERNAL:
                client = self.get_external_client()
            elif kind == AgentKind.ASSISTANT:
                client = self.get_assistant_client()
            else:
                raise BadRequest("'kind' must be 'native'")

            draft_agents = client.get_draft_by_name(name)
            if len(draft_agents) > 1:
                logger.error(f"Multiple '{kind}' agents found with name '{name}'. Failed to delete agent")
                sys.exit(1)
            if len(draft_agents) > 0:
                draft_agent = draft_agents[0]
                agent_id = draft_agent.get("id")
                client.delete(agent_id=agent_id)

                logger.info(f"Successfully removed agent {name}")
            else:
                logger.warning(f"No agent named '{name}' found")
        except requests.HTTPError as e:
            logger.error(e.response.text)
            exit(1)

    def get_spec_file_content(self, agent: Agent | ExternalAgent | AssistantAgent, exclude: List[str] | None = None):
        ref_agent = self.reference_agent_dependencies(agent)
        agent_spec = ref_agent.model_dump(mode='json', exclude_none=True, exclude=exclude)
        return agent_spec

    def get_agent(self, name: str, kind: AgentKind) -> Agent | ExternalAgent | AssistantAgent:
        match kind:
            case AgentKind.NATIVE:
                client = self.get_native_client()
                agent_details = get_agent_details(name=name, client=client)
                agent = Agent.model_validate(agent_details)
            case AgentKind.EXTERNAL:
                client = self.get_external_client()
                agent_details = get_agent_details(name=name, client=client)
                agent = ExternalAgent.model_validate(agent_details)
            case AgentKind.ASSISTANT:
                client = self.get_assistant_client()
                agent_details = get_agent_details(name=name, client=client)
                agent = AssistantAgent.model_validate(agent_details)
        
        return agent
    
    def get_agent_by_id(self, id: str) -> Agent | ExternalAgent | AssistantAgent | None:
        native_client = self.get_native_client()
        external_client = self.get_external_client()
        assistant_client = self.get_assistant_client()

        native_result = native_client.get_draft_by_id(id)
        external_result = external_client.get_draft_by_id(id)
        assistant_result = assistant_client.get_draft_by_id(id)

        if native_result:
            return Agent.model_validate(native_result)
        if external_result:
            return ExternalAgent.model_validate(external_result)
        if assistant_result:
            return AssistantAgent.model_validate(assistant_result)
        
    def get_agent_by_names(self, names: List[str]) -> List[dict]:
        native_client = self.get_native_client()
        external_client = self.get_external_client()
        assistant_client = self.get_assistant_client()

        native_result = native_client.get_drafts_by_names(names)
        external_result = external_client.get_drafts_by_names(names)
        assistant_result = assistant_client.get_drafts_by_names(names)

        return native_result + external_result + assistant_result

    def export_agent(self, name: str, kind: AgentKind, output_path: str, agent_only_flag: bool=False, zip_file_out: zipfile.ZipFile | None = None, with_tool_spec_file: bool = False, exclude: List[str] | None = None) -> None:
        output_file = Path(output_path)
        output_file_extension = output_file.suffix
        output_file_name = output_file.stem
        
        # Get the agent first to check if it's a custom agent
        agent = self.get_agent(name, kind)
        is_custom_agent = isinstance(agent, Agent) and agent.style == AgentStyle.CUSTOM
        
        # For custom agents, handle differently
        if is_custom_agent:
            if output_file_extension != ".zip":
                logger.error(f"Output file must end with the extension '.zip' for custom agents. Provided file '{output_path}' ends with '{output_file_extension}'")
                sys.exit(1)
            
            # Download the custom agent package directly
            self.download_agent_artifact(agent_name=name, output_path=output_path)
            return
        
        # For non-custom agents, proceed with regular export logic
        if not agent_only_flag and output_file_extension != ".zip":
            logger.error(f"Output file must end with the extension '.zip'. Provided file '{output_path}' ends with '{output_file_extension}'")
            sys.exit(1)
        elif agent_only_flag and (output_file_extension != ".yaml" and output_file_extension != ".yml"):
            logger.error(f"Output file must end with the extension '.yaml' or '.yml'. Provided file '{output_path}' ends with '{output_file_extension}'")
            sys.exit(1)
        
        agent = self.get_agent(name, kind)

        if agent.restrictions == AgentRestrictionType.NON_EDITABLE:
            logger.error(f"Agent '{agent.name}' is not editable and cannot be exported")
            sys.exit(1)

        agent_spec_file_content = self.get_spec_file_content(agent, exclude=exclude)
        
        agent_spec_file_content.pop("hidden", None)
        agent_spec_file_content.pop("id", None)
        agent_spec_file_content["spec_version"] = SpecVersion.V1.value

        llm_config = ModelConfig(**(agent_spec_file_content.get("llm_config") or dict()))
        llm_config = llm_config.model_dump(exclude_unset=True, exclude_defaults=True, exclude_none=True)
        if "llm_config" in agent_spec_file_content and not llm_config:
            agent_spec_file_content.pop("llm_config", None)

        if agent_only_flag:
            logger.info(f"Exported agent definition for '{name}' to '{output_path}'")
            with safe_open(output_path, 'w') as outfile:
                yaml.dump(agent_spec_file_content, outfile, sort_keys=False, default_flow_style=False, allow_unicode=True)
            return
        
        close_file_flag = False
        if zip_file_out is None:
            close_file_flag = True
            zip_file_out = zipfile.ZipFile(output_path, "w")

        logger.info(f"Exporting agent definition for '{name}'")
        
        agent_spec_yaml = yaml.dump(agent_spec_file_content, sort_keys=False, default_flow_style=False, allow_unicode=True)
        agent_spec_yaml_bytes = agent_spec_yaml.encode("utf-8")
        agent_spec_yaml_file = io.BytesIO(agent_spec_yaml_bytes)

        # Skip processing an agent if its already been saved
        agent_file_path = f"{output_file_name}/agents/{agent_spec_file_content.get('kind', 'unknown')}/{agent_spec_file_content.get('name')}.yaml"
        if check_file_in_zip(file_path=agent_file_path, zip_file=zip_file_out):
            logger.warning(f"Skipping {agent_spec_file_content.get('name')}, agent with that name already exists in the output folder")
            if close_file_flag:
                zip_file_out.close()
            return
        
        zip_file_out.writestr(
            agent_file_path,
            agent_spec_yaml_file.getvalue()
        )

        # Export Connections
        app_id = None
        if kind == AgentKind.EXTERNAL:
            app_id = agent_spec_file_content.get("app_id")
        elif kind == AgentKind.ASSISTANT:
            app_id = agent_spec_file_content.get("config", {}).get("app_id")
        
        if app_id:
            export_connection(output_file=f"{output_file_name}/connections/", app_id=app_id, zip_file_out=zip_file_out)

        # Export Tools
        agent_tools = agent_spec_file_content.get("tools", [])

        tools_controller = ToolsController()
        tools_client = tools_controller.get_client() 
        tool_specs = None
        tool_specs = {t.get('name'):t for t in tools_client.get_drafts_by_names(agent_tools) if t.get('name')}

        for tool_name in agent_tools:

            current_spec = tool_specs.get(tool_name)
            if current_spec and _get_kind_from_spec(current_spec) == ToolKind.mcp:
                base_tool_file_path = f"{output_file_name}/toolkits/"
            else:
                base_tool_file_path = f"{output_file_name}/tools/{tool_name}/"

                if check_file_in_zip(file_path=base_tool_file_path, zip_file=zip_file_out):
                    continue

            tools_controller.export_tool(
                name=tool_name,
                output_path=base_tool_file_path,
                zip_file_out=zip_file_out, 
                spec=current_spec, 
                connections_output_path=f"{output_file_name}/connections/"
            )

            if with_tool_spec_file and tool_specs:
                zip_file_out.writestr(
                    f"{base_tool_file_path}config.json",
                    ToolSpec.model_validate(current_spec).model_dump_json(exclude_unset=True,indent=2)
                )

        # Export Plugins
        agent_plugins = agent_spec_file_content.get("plugins", {})

        tools_controller = ToolsController()
        tools_client = tools_controller.get_client()

        for phase_name, plugin_list in agent_plugins.items():
            for plugin in plugin_list:
                plugin_name = plugin.get("plugin_name")
                if not plugin_name:
                    continue

                base_plugin_file_path = f"{output_file_name}/plugins/{plugin_name}/"
                if check_file_in_zip(file_path=base_plugin_file_path, zip_file=zip_file_out):
                    continue

                plugin_specs = {t.get('name'): t for t in tools_client.get_drafts_by_names([plugin_name]) if t.get('name')}
                current_spec = plugin_specs.get(plugin_name)

                tools_controller.export_tool(
                    name=plugin_name,
                    output_path=base_plugin_file_path,
                    zip_file_out=zip_file_out,
                    spec=current_spec,
                    connections_output_path=f"{output_file_name}/connections/"
                )

                # Optionally, write a config.json for the plugin spec
                if with_tool_spec_file and current_spec:
                    zip_file_out.writestr(
                        f"{base_plugin_file_path}config.json",
                        ToolSpec.model_validate(current_spec).model_dump_json(exclude_unset=True, indent=2)
                    )
        
        # Export Knowledge Bases
        knowledge_base_controller = KnowledgeBaseController()
        for kb_name in agent_spec_file_content.get("knowledge_base", []):
            knowledge_base_file_path = f"{output_file_name}/knowledge-bases/"
            knowledge_base_controller.knowledge_base_export(
                name=kb_name,
                output_path=knowledge_base_file_path,
                zip_file_out=zip_file_out,
                connections_output_path=f"{output_file_name}/connections/"
                )
        
        # Export Collaborators
        if kind == AgentKind.NATIVE:
            for collaborator_id in agent.collaborators:
                collaborator = self.get_agent_by_id(collaborator_id)

                if not collaborator:
                    logger.warning(f"Skipping {collaborator_id}, no agent with id {collaborator_id} found")
                    continue

                if collaborator.restrictions == AgentRestrictionType.NON_EDITABLE:
                    logger.warning(f"Collaborator '{collaborator.name}' is not editable and cannot be exported")
                    continue
                
                self.export_agent(
                    name=collaborator.name,
                    kind=collaborator.kind,
                    output_path=output_path,
                    agent_only_flag=False,
                    zip_file_out=zip_file_out)

        # Export Models / Model Policies
        models_controller = ModelsController()
        model_name = agent_spec_file_content.get("llm", "")
        if model_name.startswith("virtual-model/"):
            models_controller.export_model(name=model_name, output_path=output_path, zip_file_out=zip_file_out)
        elif model_name.startswith("virtual-policy/"):
            models_controller.export_model_policy(name=model_name, output_path=output_path, zip_file_out=zip_file_out)

        if close_file_flag:
            logger.info(f"Successfully wrote agents and tools to '{output_path}'")
            zip_file_out.close()


    def deploy_agent(self, name: str):
        if is_local_dev():
            logger.error("Agents cannot be deployed in Developer Edition")
            sys.exit(1)
        native_client = self.get_native_client()
        external_client = self.get_external_client()
        assistant_client = self.get_assistant_client()

        existing_native_agents = native_client.get_draft_by_name(name)
        existing_external_agents = external_client.get_draft_by_name(name)
        existing_assistant_agents = assistant_client.get_draft_by_name(name)

        if len(existing_native_agents) == 0 and (len(existing_external_agents) >= 1 or len(existing_assistant_agents) >= 1):
            logger.error(f"No native agent found with name '{name}'. Only Native Agents can be deployed to a Live Environment")
            sys.exit(1)
        if len(existing_native_agents) > 1:
            logger.error(f"Multiple native agents with the name '{name}' found. Failed to get agent")
            sys.exit(1)
        if len(existing_native_agents) == 0:
            logger.error(f"No native agents with the name '{name}' found. Failed to get agent")
            sys.exit(1)
            

        agent_details = existing_native_agents[0]
        agent_id = agent_details.get("id")

        environments = native_client.get_environments_for_agent(agent_id)

        live_environment = [env for env in environments if env.get("name") == "live"]
        if live_environment is None:
            logger.error("No live environment found for this tenant")
            sys.exit(1)

        live_env_id = live_environment[0].get("id")

        console = Console()
        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
                ) as progress:
                    progress.add_task(description="Deploying agent to Live envrionment", total=None)

                    status = native_client.deploy(agent_id, live_env_id)

        if status:
            logger.info(f"Successfully deployed agent {name}")
        else:
            logger.error(f"Error deploying agent {name}")

    def undeploy_agent(self, name: str):
        if is_local_dev():
            logger.error("Agents cannot be undeployed in Developer Edition")
            sys.exit(1)

        native_client = self.get_native_client()
        external_client = self.get_external_client()
        assistant_client = self.get_assistant_client()

        existing_native_agents = native_client.get_draft_by_name(name)
        existing_external_agents = external_client.get_draft_by_name(name)
        existing_assistant_agents = assistant_client.get_draft_by_name(name)

        if len(existing_native_agents) == 0 and (len(existing_external_agents) >= 1 or len(existing_assistant_agents) >= 1):
            logger.error(f"No native agent found with name '{name}'. Only Native Agents can be undeployed from a Live Environment")
            sys.exit(1)
        if len(existing_native_agents) > 1:
            logger.error(f"Multiple native agents with the name '{name}' found. Failed to get agent")
            sys.exit(1)
        if len(existing_native_agents) == 0:
            logger.error(f"No native agents with the name '{name}' found. Failed to get agent")
            sys.exit(1)

        agent_details = existing_native_agents[0]
        agent_id = agent_details.get("id")

        environments = native_client.get_environments_for_agent(agent_id)
        live_environment = [env for env in environments if env.get("name") == "live"]
        if live_environment is None:
            logger.error("No live environment found for this tenant")
            sys.exit(1)
        version_id = live_environment[0].get("current_version")

        if version_id is None:
            agent_name = agent_details.get("name")
            logger.error(f"Agent {agent_name} does not exist in a Live environment")
            sys.exit(1)

        draft_environment = [env for env in environments if env.get("name") == "draft"]
        if draft_environment is None:
            logger.error("No draft environment found for this tenant")
            sys.exit(1)
        draft_env_id = draft_environment[0].get("id")

        console = Console()
        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
                ) as progress:
                    progress.add_task(description="Undeploying agent to Draft envrionment", total=None)

                    status = native_client.undeploy(agent_id, version_id, draft_env_id)
        if status:
            logger.info(f"Successfully undeployed agent {name}")
        else:
            logger.error(f"Error undeploying agent {name}")
    
    @staticmethod
    def _format_agent_display_name(agent: AnyAgentT) -> str:
        return f"{agent.name} ({agent.display_name})" if agent.display_name and agent.name != agent.display_name else agent.name

    def connect_connections_to_agent(self, agent_name: str, connection_ids: List[str]) -> None:
        """
        Connect connections to an agent using the PATCH endpoint.
        
        Args:
            agent_name: Name of the agent to connect connections to
            connection_ids: List of connection IDs (app_ids) to connect
        """
        native_client = self.get_native_client()
        connections_client = get_connections_client()
        
        existing_agents = native_client.get_draft_by_name(agent_name)
        
        if len(existing_agents) == 0:
            logger.error(f"No agent found with name '{agent_name}'")
            sys.exit(1)
        if len(existing_agents) > 1:
            logger.error(f"Multiple agents with the name '{agent_name}' found. Failed to connect connections")
            sys.exit(1)
        
        agent = existing_agents[0]
        agent_id = agent.get("id")

        if agent.get("style") != AgentStyle.CUSTOM:
            logger.error(f"Agent '{agent_name}' is not a custom agent. Failed to connect connections")
            sys.exit(1)
            
        connection_uuids = []
        for app_id in connection_ids:
            connection = connections_client.get_draft_by_app_id(app_id=app_id)
            if not connection:
                logger.error(f"No connection exists with the app-id '{app_id}'")
                sys.exit(1)
            if connection.connection_id in agent.get("connection_ids", []):
                logger.error(f"Connection with app-id '{app_id}' is already connected to agent '{agent_name}'")
                sys.exit(1)
            connection_uuids.append(connection.connection_id)
        
        # Connect the connections to the agent
        logger.info(f"Connecting {len(connection_uuids)} connection(s) to agent '{agent_name}'...")
        native_client.connect_connections(agent_id, connection_uuids)
        logger.info(f"Successfully connected connections to agent '{agent_name}'")

    def run_agent(
        self,
        message: str,
        agent_name: str | None = None,
        thread_id: str | None = None,
        capture_logs: bool = False
    ) -> None:
        """
        Send a message to an agent, optionally capturing and displaying logs.
        
        Args:
            message: The message to send to the agent
            agent_name: Optional agent name to send the message to (will be resolved to agent_id)
            thread_id: Optional thread ID to continue a conversation
            capture_logs: Whether to capture and display logs (only works with custom agents)
        """
        from ibm_watsonx_orchestrate.client.chat import RunClient
        from ibm_watsonx_orchestrate.client.threads.threads_client import ThreadsClient
        from ibm_watsonx_orchestrate.client.utils import instantiate_client
        from datetime import datetime
        
        console = Console()
        
        # Initialize clients
        run_client = instantiate_client(RunClient)
        threads_client = instantiate_client(ThreadsClient)
        
        # Resolve agent name to agent ID if provided
        agent_id = None
        if agent_name:
            try:
                native_client = self.get_native_client()
                external_client = self.get_external_client()
                assistant_client = self.get_assistant_client()
                
                # Try to find the agent by name
                native_agents = native_client.get_draft_by_name(agent_name)
                external_agents = external_client.get_draft_by_name(agent_name)
                assistant_agents = assistant_client.get_draft_by_name(agent_name)
                
                all_agents = native_agents + external_agents + assistant_agents
                
                if len(all_agents) == 0:
                    console.print(f"[red]✗[/red] No agent found with name '{agent_name}'")
                    sys.exit(1)
                elif len(all_agents) > 1:
                    console.print(f"[red]✗[/red] Multiple agents found with name '{agent_name}'. Please use a unique agent name.")
                    sys.exit(1)
                
                agent_details = all_agents[0]
                agent_style = agent_details.get("style")
                
                # Verify this is a custom agent only if capture_logs is enabled
                if capture_logs and agent_style != AgentStyle.CUSTOM:
                    console.print(f"[red]✗[/red] Agent '{agent_name}' is not a custom agent (style: {agent_style}).")
                    console.print("[red]The --capture-logs flag only works with custom style agents.[/red]")
                    sys.exit(1)
                
                agent_id = agent_details.get("id")
                if agent_style == AgentStyle.CUSTOM:
                    console.print(f"[dim]Using custom agent: {agent_name} (ID: {agent_id})[/dim]")
                else:
                    console.print(f"[dim]Using agent: {agent_name} (ID: {agent_id})[/dim]")
            except Exception as e:
                console.print(f"[red]✗[/red] Error resolving agent name: {e}")
                sys.exit(1)
        
        try:
            # Step 1: Send message with optional log capture
            console.print("\n[cyan]Sending message to agent...[/cyan]")
            run_response = run_client.create_run(
                message=message,
                agent_id=agent_id,
                thread_id=thread_id,
                capture_logs=capture_logs
            )
            
            returned_thread_id = run_response.get("thread_id")
            run_id = run_response.get("run_id")
            
            if not run_id:
                console.print("[red]✗[/red] Failed to get run ID from response")
                return
            
            console.print(f"[green]✓[/green] Message sent (Thread: {returned_thread_id}, Run: {run_id})")
            
            # Step 2: Wait for run completion
            console.print("\n[cyan]Waiting for response...[/cyan]")
            
            with Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
                console=console,
            ) as progress:
                progress.add_task(description="Processing...", total=None)
                final_status = run_client.wait_for_run_completion(run_id)
            
            run_state = final_status.get("status", "").lower()
            
            if run_state == "failed":
                console.print("[red]✗[/red] Run failed")
                error_msg = final_status.get("error", "Unknown error")
                console.print(f"[red]Error: {error_msg}[/red]")
                return
            elif run_state == "cancelled":
                console.print("[yellow]✗[/yellow] Run was cancelled")
                return
            
            console.print("[green]✓[/green] Response received")
            
            # Step 3: Get the assistant's response message
            thread_messages_response = threads_client.get_thread_messages(returned_thread_id)
            
            # Handle both list and dict responses
            match thread_messages_response:
                case list():
                    messages = thread_messages_response
                case {"messages": msgs}:
                    messages = msgs
                case _:
                    messages = []
            
            # Find the assistant's response (last message with role 'assistant')
            assistant_message = None
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    assistant_message = msg
                    break
            
            if not assistant_message:
                console.print("[yellow]⚠[/yellow] No assistant response found")
                return
            
            # Display agent response
            console.print("\n[bold cyan]Agent Response:[/bold cyan]")
            console.print("─" * 60)
            content = assistant_message.get("content", [])
            
            # Handle different content structures
            match content:
                case list() if content:
                    for item in content:
                        match item:
                            case {"type": "text", "text": dict() as text_obj}:
                                console.print(text_obj.get("value", ""))
                            case {"type": "text", "text": text_obj}:
                                console.print(str(text_obj))
                            case {"type": "text"}:
                                console.print("")
                            case {"text": text_val}:
                                console.print(text_val)
                            case dict():
                                console.print(str(item))
                            case str():
                                console.print(item)
                case str():
                    console.print(content)
                case []:
                    console.print("[dim]No content in response[/dim]")
                case _:
                    console.print(str(content))
            console.print("─" * 60)
            
            # Step 4: Retrieve and display logs only if capture_logs is enabled
            if capture_logs:
                log_id = assistant_message.get("log_id")
                
                # Check in assistant message metadata
                if not log_id:
                    metadata = assistant_message.get("additional_properties", {})
                    if isinstance(metadata, dict):
                        log_id = metadata.get("log_id")
                
                # Check in the run response (nested in result.data.message)
                if not log_id:
                    result = final_status.get("result", {})
                    if isinstance(result, dict):
                        data = result.get("data", {})
                        if isinstance(data, dict):
                            message = data.get("message", {})
                            if isinstance(message, dict):
                                log_id = message.get("log_id")
                
                # Check if log_id is valid
                if not log_id or (isinstance(log_id, str) and log_id.strip() == ""):
                    console.print("\n[yellow]✗ No logs captured for this run[/yellow]")
                    return
                
                # Step 5: Retrieve captured logs
                try:
                    console.print(f"\n[bold cyan]Captured Logs (Log ID: {log_id}):[/bold cyan]")
                    console.print("─" * 60)
                    
                    logs_response = threads_client.get_logs_by_log_id(log_id)
                    captured_logs = logs_response.get("captured_logs", {})
                    entries = captured_logs.get("logs", [])
                    
                    if not entries:
                        console.print("[yellow]No log entries found[/yellow]")
                    else:
                        for entry in entries:
                            timestamp = entry.get("timestamp", "")
                            level = entry.get("level", "INFO")
                            log_message = entry.get("message", "")
                            
                            # Format timestamp if present
                            if timestamp:
                                try:
                                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                                except:
                                    formatted_time = timestamp
                            else:
                                formatted_time = "Unknown"
                            
                            # Color code by level
                            level_color = LOG_LEVEL_COLORS.get(level.upper(), "white")
                            
                            console.print(f"[dim]{formatted_time}[/dim] [{level_color}]{level}[/{level_color}]: {log_message}")
                    
                    console.print("─" * 60)
                    console.print(f"[cyan]Total log entries: {len(entries)}[/cyan]")
                    
                except Exception as e:
                    console.print(f"\n[red]✗ Error retrieving logs: {e}[/red]")
        
        except TimeoutError as e:
            console.print(f"\n[red]✗ Error: {e}[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[red]✗ Error: {e}[/red]")
            logger.error(f"Failed to run with logs: {e}")
            sys.exit(1)

    def upload_agent_artifact(self, agent_name: str, file_path: str) -> dict:
        """
        Upload a custom file artifact for an agent.
        
        Args:
            agent_name: Name of the agent to upload the file for
            file_path: Path to the file to upload
            
        Returns:
            Response dictionary from the upload operation
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            sys.exit(1)
        
        native_client = self.get_native_client()
        existing_agents = native_client.get_draft_by_name(agent_name)
        
        if len(existing_agents) == 0:
            logger.error(f"No agent found with name '{agent_name}'")
            sys.exit(1)
        if len(existing_agents) > 1:
            logger.error(f"Multiple agents with the name '{agent_name}' found. Failed to upload file")
            sys.exit(1)
        
        agent = existing_agents[0]
        agent_id = agent.get("id")
        
        try:
            logger.info(f"Uploading file '{file_path}' for agent '{agent_name}'...")
            response = native_client.upload_agent_artifact(
                agent_id=agent_id,
                file_path=file_path
            )
            logger.info(f"Successfully uploaded file for agent '{agent_name}'")
            return response
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            sys.exit(1)

    def download_agent_artifact(self, agent_name: str, output_path: str) -> None:
        """
        Download a custom agent package (zip file).
        Only works for custom agents.
        
        Args:
            agent_name: Name of the custom agent to download
            output_path: Path where the zip file should be saved
        """
        native_client = self.get_native_client()
        existing_agents = native_client.get_draft_by_name(agent_name)
        
        if len(existing_agents) == 0:
            logger.error(f"No agent found with name '{agent_name}'")
            sys.exit(1)
        if len(existing_agents) > 1:
            logger.error(f"Multiple agents with the name '{agent_name}' found. Failed to download")
            sys.exit(1)
        
        agent = existing_agents[0]
        agent_id = agent.get("id")
        agent_style = agent.get("style")
        
        if agent_style != AgentStyle.CUSTOM:
            logger.error(f"Agent '{agent_name}' is not a custom agent (style: {agent_style}). Only custom agents can be downloaded.")
            sys.exit(1)
        
        try:
            logger.info(f"Downloading custom agent package for '{agent_name}'...")
            zip_content = native_client.download_agent_artifact(agent_id=agent_id)
            
            with open(output_path, 'wb') as f:
                f.write(zip_content)
            
            logger.info(f"Successfully downloaded custom agent package to '{output_path}'")
        except Exception as e:
            logger.error(f"Failed to download agent package: {e}")
            sys.exit(1)
