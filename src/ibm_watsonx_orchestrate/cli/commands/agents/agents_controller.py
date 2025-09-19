import yaml
import json
import rich
import requests
import importlib
import inspect
import zipfile
import sys
import io
import logging
from pathlib import Path
from copy import deepcopy

from typing import Iterable, List, TypeVar
from pydantic import BaseModel
from ibm_watsonx_orchestrate.agent_builder.agents.types import AgentStyle
from ibm_watsonx_orchestrate.agent_builder.tools.types import ToolSpec
from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import import_python_tool, ToolsController
from ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller import import_python_knowledge_base
from ibm_watsonx_orchestrate.cli.commands.models.models_controller import import_python_model

from ibm_watsonx_orchestrate.agent_builder.agents import (
    Agent,
    ExternalAgent,
    AssistantAgent,
    AgentKind,
    SpecVersion
)
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient, AgentUpsertResponse
from ibm_watsonx_orchestrate.client.agents.external_agent_client import ExternalAgentClient
from ibm_watsonx_orchestrate.client.agents.assistant_agent_client import AssistantAgentClient
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.voice_configurations.voice_configurations_client import VoiceConfigurationsClient
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.client.connections import get_connections_client
from ibm_watsonx_orchestrate.client.knowledge_bases.knowledge_base_client import KnowledgeBaseClient

from ibm_watsonx_orchestrate.client.utils import instantiate_client, is_local_dev
from ibm_watsonx_orchestrate.utils.utils import check_file_in_zip

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from enum import Enum

logger = logging.getLogger(__name__)

# Helper generic type for any agent
AnyAgentT = TypeVar("AnyAgentT", bound=Agent | ExternalAgent | AssistantAgent)

class AgentListFormats(str, Enum):
    Table = "table"
    JSON = "json"

    def __str__(self):
        return self.value 

    def __repr__(self):
        return repr(self.value)


def import_python_agent(file: str) -> List[Agent | ExternalAgent | AssistantAgent]:
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
        if isinstance(obj, Agent) or isinstance(obj, ExternalAgent) or isinstance(obj, AssistantAgent):
            agents.append(obj)
    return agents


def create_agent_from_spec(file:str, kind:str) -> Agent | ExternalAgent | AssistantAgent:
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

def parse_file(file: str) -> List[Agent | ExternalAgent | AssistantAgent]:
    if file.endswith('.yaml') or file.endswith('.yml') or file.endswith(".json"):
        with open(file, 'r') as f:
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
        raise BadRequest("file must end in .json, .yaml, .yml or .py")

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

def get_conn_id_from_app_id(app_id: str) -> str:
    connections_client = get_connections_client()
    connection = connections_client.get_draft_by_app_id(app_id=app_id)
    if not connection:
        logger.error(f"No connection exists with the app-id '{app_id}'")
        exit(1)
    return connection.connection_id

def get_app_id_from_conn_id(conn_id: str) -> str:
    connections_client = get_connections_client()
    app_id = connections_client.get_draft_by_id(conn_id=conn_id)
    if not app_id or app_id == conn_id:
        logger.error(f"No connection exists with the connection id '{conn_id}'")
        exit(1)
    return app_id


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
    def import_agent(file: str, app_id: str) -> List[Agent | ExternalAgent | AssistantAgent]:
        agents = parse_file(file)
        for agent in agents:
            if app_id and agent.kind != AgentKind.NATIVE and agent.kind != AgentKind.ASSISTANT:
                agent.app_id = app_id
        return agents


    @staticmethod
    def generate_agent_spec(
        name: str, kind: AgentKind, description: str, **kwargs
    ) -> Agent | ExternalAgent | AssistantAgent:
        match kind:
            case AgentKind.NATIVE:
                agent_details = parse_create_native_args(
                    name, kind=kind, description=description, **kwargs
                )
                agent = Agent.model_validate(agent_details)
                AgentsController().persist_record(agent=agent, **kwargs)
            case AgentKind.EXTERNAL:
                agent_details = parse_create_external_args(name, kind=kind, description=description, **kwargs)
                agent = ExternalAgent.model_validate(agent_details)
                AgentsController().persist_record(agent=agent, **kwargs)
                # for agents command without --app-id
                if kwargs.get("app_id") is not None:
                    connection_id = get_conn_id_from_app_id(kwargs.get("app_id"))

                    agent.connection_id = connection_id
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

        # If agent has style set to "planner" and have join_tool defined, then we need to include that tool as well
        if agent.style == AgentStyle.PLANNER and agent.custom_join_tool:
            matching_tools = tool_client.get_drafts_by_names(deref_agent.tools + [deref_agent.custom_join_tool])
        else:
            matching_tools = tool_client.get_drafts_by_names(deref_agent.tools)

        name_id_lookup = {}
        for tool in matching_tools:
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

        return deref_agent
    
    def reference_tools(self, agent: Agent) -> Agent:
        tool_client = self.get_tool_client()

        ref_agent = deepcopy(agent)
        
        # If agent has style set to "planner" and have join_tool defined, then we need to include that tool as well
        if agent.style == AgentStyle.PLANNER and agent.custom_join_tool:
            matching_tools = tool_client.get_drafts_by_ids(ref_agent.tools + [ref_agent.custom_join_tool])
        else:
            matching_tools = tool_client.get_drafts_by_ids(ref_agent.tools)

        id_name_lookup = {}
        for tool in matching_tools:
            if tool.get("id") in id_name_lookup:
                logger.error(f"Duplicate draft entries for tool '{tool.get('id')}'")
                sys.exit(1)
            id_name_lookup[tool.get("id")] = tool.get("name")
        
        ref_tools = []
        for id in agent.tools:
            name = id_name_lookup[id]
            if not name:
                logger.error(f"Failed to find tool. No tools found with the id '{id}'")
                sys.exit(1)
            ref_tools.append(name)
        ref_agent.tools = ref_tools
        
        if agent.style == AgentStyle.PLANNER and agent.custom_join_tool:
            join_tool_name = id_name_lookup.get(agent.custom_join_tool)
            if not join_tool_name:
                logger.error(f"Failed to find custom join tool. No tools found with the id '{agent.custom_join_tool}'")
                sys.exit(1)
            ref_agent.custom_join_tool = join_tool_name

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
        if (agent.tools and len(agent.tools)) or (agent.style == AgentStyle.PLANNER and agent.custom_join_tool):
            agent = self.dereference_tools(agent)
        if agent.knowledge_base and len(agent.knowledge_base):
            agent = self.dereference_knowledge_bases(agent)
        if agent.guidelines and len(agent.guidelines):
            agent = self.dereference_guidelines(agent)

        return agent
    
    def reference_native_agent_dependencies(self, agent: Agent) -> Agent:
        if agent.collaborators and len(agent.collaborators):
            agent = self.reference_collaborators(agent)
        if (agent.tools and len(agent.tools)) or (agent.style == AgentStyle.PLANNER and agent.custom_join_tool):
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
        self, agents: Iterable[Agent | ExternalAgent | AssistantAgent]
    ):
        for agent in agents:
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

                if agent_name == existing_agent.name:
                    if agent_kind != existing_agent.kind:
                        logger.error(f"An agent with the name '{agent_name}' already exists with a different kind. Failed to create agent")
                        sys.exit(1)
                    agent_id = existing_agent.id
                    self.update_agent(agent_id=agent_id, agent=agent)
            else:
                self.publish_agent(agent)

    def publish_agent(self, agent: Agent, **kwargs) -> None:
        if isinstance(agent, Agent):
            response = self.get_native_client().create(agent.model_dump(exclude_none=True))
            _raise_guidelines_warning(response)
            logger.info(f"Agent '{agent.name}' imported successfully")
        if isinstance(agent, ExternalAgent):
            self.get_external_client().create(agent.model_dump(exclude_none=True))
            logger.info(f"External Agent '{agent.name}' imported successfully")
        if isinstance(agent, AssistantAgent):
            self.get_assistant_client().create(agent.model_dump(exclude_none=True, by_alias=True))
            logger.info(f"Assistant Agent '{agent.name}' imported successfully")

    def update_agent(
        self, agent_id: str, agent: Agent, **kwargs
    ) -> None:
        if isinstance(agent, Agent):
            logger.info(f"Existing Agent '{agent.name}' found. Updating...")
            response = self.get_native_client().update(agent_id, agent.model_dump(exclude_none=True))
            _raise_guidelines_warning(response)
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
            Given a list if agents get all the unique values of a certain field
            Example: agent1.tools = [1 ,2 ,3] and agent2.tools = [2, 4, 5] then return [1, 2, 3, 4, 5]
            Example: agent1.id = "123" and agent2.id = "456" then return ["123", "456"]

            Args:
                agents: List of agents
                target_attr: The name of the field to access and get unique elements

            Returns:
                A list of unique elements from across all agents
        """
        all_ids = set()
        for agent in agents:
            attr_value = getattr(agent, target_attr, None)
            if attr_value:
                if isinstance(attr_value, list):
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
        ) -> List[str] | str | None:
        """
        Using a lookup table convert all the strings in a given field of an agent into their equivalent in the lookup table
        Example: lookup_table={1: obj1, 2: obj2} agent=Agent(tools=[1,2]) return. [obj1, obj2]

        Args:
            agent: An agent
            lookup_table: A dictionary that maps one value to another
            target_attr: The field to convert on the provided agent
            target_attr_display_name: The name of the field to be displayed in the event of an error
        """
        attr_value = getattr(agent, target_attr, None)
        if not attr_value:
            return
        
        if isinstance(attr_value, list):
            new_resource_list=[]
            for value in attr_value:
                if value in lookup_table:
                    new_resource_list.append(lookup_table[value])
                else:
                    logger.warning(f"{target_attr_display_name} with ID '{value}' not found. Returning {target_attr_display_name} ID")
                    new_resource_list.append(value)
            return new_resource_list
        else:
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
    
    # TODO: Once bulk knowledge base is added create a generaic fucntion as opposed to 3 seperate ones
    def _bulk_resolve_agent_knowledge_bases(self, agents: List[Agent]) -> List[Agent]:
        new_agents = agents.copy()
        all_kb_ids = self._get_all_unique_agent_resources(new_agents, "knowledge_base")

        all_kbs = []
        for id in all_kb_ids:
            try:
                all_kbs.append(self.get_knowledge_base_client().get_by_id(id))
            except:
                continue

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

    def _bulk_resolve_agent_app_ids(self , agents: List[ExternalAgent]) -> List[ExternalAgent]:
        new_agents = agents.copy()
        all_conn_ids = self._get_all_unique_agent_resources(new_agents, "connection_id")
        if not all_conn_ids:
            return new_agents
        
        all_connections = self._batch_request_resource(get_connections_client().get_drafts_by_ids, all_conn_ids)

        connection_lut = self._construct_lut_agent_resource(all_connections, "connection_id", "app_id")
        
        for agent in new_agents:
            app_id = self._lookup_agent_resource_value(agent, connection_lut, "connection_id", "Connection")
            if app_id:
                agent.app_id = app_id
        return new_agents

    # TODO: Make a shared util
    def _rich_table_to_markdown(self, table: rich.table.Table) -> str:
        headers = [column.header for column in table.columns]
        cols = [[cell for cell in col.cells] for col in table.columns]
        rows = list(map(list, zip(*cols)))

        # Header row
        md = "| " + " | ".join(headers) + " |\n"
        # Separator row
        md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        # # Data rows
        for row in rows:
            md += "| " + " | ".join(row) + " |\n"
        return md



    def list_agents(self, kind: AgentKind=None, verbose: bool=False, format: AgentListFormats | None = None) -> dict[str, dict] | None:
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
                resolved_native_agents = self._bulk_resolve_agent_knowledge_bases(resolved_native_agents)
                resolved_native_agents = self._bulk_resolve_agent_collaborators(resolved_native_agents)

                if format and format == AgentListFormats.JSON:
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
                        "Knowledge Base": {},
                        "ID": {"overflow": "fold"},
                    }
                    for column in column_args:
                        native_table.add_column(column, **column_args[column])

                    for agent in resolved_native_agents:
                        native_table.add_row(
                            agent.name,
                            agent.description,
                            agent.llm,
                            agent.style,
                            ", ".join(agent.collaborators),
                            ", ".join(agent.tools),
                            ", ".join(agent.knowledge_base),
                            agent.id,
                        )
                    if format == AgentListFormats.Table:
                        output_dictionary["native"] = self._rich_table_to_markdown(native_table)
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
                
                if format and format == AgentListFormats.JSON:
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
                    
                    for agent in external_agents:
                        connections_client =  get_connections_client()
                        app_id = connections_client.get_draft_by_id(agent.connection_id)
                        resolved_native_agents = self._bulk_resolve_agent_app_ids(external_agents)

                        external_table.add_row(
                            agent.name,
                            agent.title,
                            agent.description,
                            ", ".join(agent.tags or []),
                            agent.api_url,
                            json.dumps(agent.chat_params),
                            str(agent.config),
                            agent.nickname,
                            app_id,
                            agent.id
                        )
                    if format == AgentListFormats.Table:
                        output_dictionary["external"] = self._rich_table_to_markdown(external_table)
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
                resolved_external_agents = self._bulk_resolve_agent_app_ids(assistant_agents)
                
                if format and format == AgentListFormats.JSON:
                    assistant_agents_list = []
                    for agent in resolved_external_agents:
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
                    
                    for agent in assistant_agents:
                        assistants_table.add_row(
                            agent.name,
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
                    if format == AgentListFormats.Table:
                        output_dictionary["assistant"] = self._rich_table_to_markdown(assistants_table)
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

    def get_spec_file_content(self, agent: Agent | ExternalAgent | AssistantAgent):
        ref_agent = self.reference_agent_dependencies(agent)
        agent_spec = ref_agent.model_dump(mode='json', exclude_none=True)
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
        

    def export_agent(self, name: str, kind: AgentKind, output_path: str, agent_only_flag: bool=False, zip_file_out: zipfile.ZipFile | None = None, with_tool_spec_file: bool = False) -> None:
        output_file = Path(output_path)
        output_file_extension = output_file.suffix
        output_file_name = output_file.stem
        if not agent_only_flag and output_file_extension != ".zip":
            logger.error(f"Output file must end with the extension '.zip'. Provided file '{output_path}' ends with '{output_file_extension}'")
            sys.exit(1)
        elif agent_only_flag and (output_file_extension != ".yaml" and output_file_extension != ".yml"):
            logger.error(f"Output file must end with the extension '.yaml' or '.yml'. Provided file '{output_path}' ends with '{output_file_extension}'")
            sys.exit(1)
        
        agent = self.get_agent(name, kind)
        agent_spec_file_content = self.get_spec_file_content(agent)
        
        agent_spec_file_content.pop("hidden", None)
        agent_spec_file_content.pop("id", None)
        agent_spec_file_content["spec_version"] = SpecVersion.V1.value

        if agent_only_flag:
            logger.info(f"Exported agent definition for '{name}' to '{output_path}'")
            with open(output_path, 'w') as outfile:
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

        agent_tools = agent_spec_file_content.get("tools", [])

        tools_controller = ToolsController()
        tools_client = tools_controller.get_client() 
        tool_specs = None
        if with_tool_spec_file:
            tool_specs = {t.get('name'):t for t in tools_client.get_drafts_by_names(agent_tools) if t.get('name')}

        for tool_name in agent_tools:

            base_tool_file_path = f"{output_file_name}/tools/{tool_name}/"
            if check_file_in_zip(file_path=base_tool_file_path, zip_file=zip_file_out):
                continue
            
            logger.info(f"Exporting tool '{tool_name}'")
            tool_artifact_bytes = tools_controller.download_tool(tool_name)
            if not tool_artifact_bytes:
                continue
            
            with zipfile.ZipFile(io.BytesIO(tool_artifact_bytes), "r") as zip_file_in:
                for item in zip_file_in.infolist():
                    buffer = zip_file_in.read(item.filename)
                    if (item.filename != 'bundle-format'):
                        zip_file_out.writestr(
                            f"{base_tool_file_path}{item.filename}",
                            buffer
                        )
                if with_tool_spec_file and tool_specs:
                    current_spec = tool_specs[tool_name]
                    zip_file_out.writestr(
                        f"{base_tool_file_path}config.json",
                        ToolSpec.model_validate(current_spec).model_dump_json(exclude_unset=True,indent=2)
                    )
        
        for kb_name in agent_spec_file_content.get("knowledge_base", []):
            logger.warning(f"Skipping {kb_name}, knowledge_bases are currently unsupported by export")
        
        if kind == AgentKind.NATIVE:
            for collaborator_id in agent.collaborators:
                collaborator = self.get_agent_by_id(collaborator_id)

                if not collaborator:
                    logger.warning(f"Skipping {collaborator_id}, no agent with id {collaborator_id} found")
                    continue
                
                self.export_agent(
                    name=collaborator.name,
                    kind=collaborator.kind,
                    output_path=output_path,
                    agent_only_flag=False,
                    zip_file_out=zip_file_out)
        
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

