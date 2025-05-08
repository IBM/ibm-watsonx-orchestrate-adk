import yaml
import json
import rich
import requests
import importlib
import inspect
import sys
import logging
from pathlib import Path
from copy import deepcopy

from typing import Iterable, List
from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import import_python_tool
from ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller import import_python_knowledge_base

from ibm_watsonx_orchestrate.agent_builder.agents import (
    Agent,
    ExternalAgent,
    AssistantAgent,
    AgentKind,
    SpecVersion
)
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient
from ibm_watsonx_orchestrate.client.agents.external_agent_client import ExternalAgentClient
from ibm_watsonx_orchestrate.client.agents.assistant_agent_client import AssistantAgentClient
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_watsonx_orchestrate.client.connections import get_connections_client
from ibm_watsonx_orchestrate.client.knowledge_bases.knowledge_base_client import KnowledgeBaseClient

from ibm_watsonx_orchestrate.client.utils import instantiate_client

logger = logging.getLogger(__name__)

def import_python_agent(file: str) -> List[Agent | ExternalAgent | AssistantAgent]:
    # Import tools
    import_python_tool(file)
    import_python_knowledge_base(file)

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
            raise ValueError("'kind' must be either 'native' or 'external'")

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
        raise ValueError("file must end in .json, .yaml, .yml or .py")

def parse_create_native_args(name: str, kind: AgentKind, description: str | None, **args) -> dict:
    agent_details = {
        "name": name,
        "kind": kind,
        "description": description,
        "llm": args.get("llm"),
        "style": args.get("style"),
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
    }

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
    }

    return agent_details

def get_conn_id_from_app_id(app_id: str) -> str:
    connections_client = get_connections_client()
    connection = connections_client.get_draft_by_app_id(app_id=app_id)
    if not connection:
        logger.error(f"No connection exits with the app-id '{app_id}'")
        exit(1)
    return connection.connection_id

class AgentsController:
    def __init__(self):
        self.native_client = None
        self.external_client = None
        self.assistant_client = None
        self.tool_client = None
        self.knowledge_base_client = None

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
    
    @staticmethod
    def import_agent(file: str, app_id: str) -> Iterable:
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
                agent_details = parse_create_native_args(name, kind=kind, description=description, **kwargs)
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
    
    def dereference_tools(self, agent: Agent) -> Agent:
        tool_client = self.get_tool_client()

        deref_agent = deepcopy(agent)
        matching_tools = tool_client.get_drafts_by_names(deref_agent.tools)

        name_id_lookup = {}
        for tool in matching_tools:
            if tool.get("name") in name_id_lookup:
                logger.error(f"Duplicate draft entries for tol '{tool.get('name')}'")
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

        return deref_agent
    
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
    
    @staticmethod
    def dereference_app_id(agent: ExternalAgent | AssistantAgent) -> ExternalAgent | AssistantAgent:
        if agent.kind == AgentKind.EXTERNAL:
            agent.connection_id = get_conn_id_from_app_id(agent.app_id)
        else:
            agent.config.connection_id = get_conn_id_from_app_id(agent.config.app_id)

        return agent


    def dereference_native_agent_dependencies(self, agent: Agent) -> Agent:
        if agent.collaborators and len(agent.collaborators):
            agent = self.dereference_collaborators(agent)
        if agent.tools and len(agent.tools):
            agent = self.dereference_tools(agent)
        if agent.knowledge_base and len(agent.knowledge_base):
            agent = self.dereference_knowledge_bases(agent)

        return agent
    
    def dereference_external_or_assistant_agent_dependencies(self, agent: ExternalAgent | AssistantAgent) -> ExternalAgent | AssistantAgent: 
        agent_dict = agent.model_dump()

        if agent_dict.get("app_id") or agent.config.model_dump().get("app_id"):
            agent = self.dereference_app_id(agent)

        return agent
                
    def dereference_agent_dependencies(self, agent: Agent ) -> Agent | ExternalAgent | AssistantAgent:
        if isinstance(agent, Agent):
            return self.dereference_native_agent_dependencies(agent)
        if isinstance(agent, ExternalAgent) or isinstance(agent, AssistantAgent):
            return self.dereference_external_or_assistant_agent_dependencies(agent)
        

    def publish_or_update_agents(
        self, agents: Iterable[Agent]
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
            self.get_native_client().create(agent.model_dump())
            logger.info(f"Agent '{agent.name}' imported successfully")
        if isinstance(agent, ExternalAgent):
            self.get_external_client().create(agent.model_dump())
            logger.info(f"External Agent '{agent.name}' imported successfully")
        if isinstance(agent, AssistantAgent):
            self.get_assistant_client().create(agent.model_dump(by_alias=True))
            logger.info(f"Assistant Agent '{agent.name}' imported successfully")

    def update_agent(
        self, agent_id: str, agent: Agent, **kwargs
    ) -> None:
        if isinstance(agent, Agent):
            logger.info(f"Existing Agent '{agent.name}' found. Updating...")
            self.get_native_client().update(agent_id, agent.model_dump())
            logger.info(f"Agent '{agent.name}' updated successfully")
        if isinstance(agent, ExternalAgent):
            logger.info(f"Existing External Agent '{agent.name}' found. Updating...")
            self.get_external_client().update(agent_id, agent.model_dump())
            logger.info(f"External Agent '{agent.name}' updated successfully")
        if isinstance(agent, AssistantAgent):
            logger.info(f"Existing Assistant Agent '{agent.name}' found. Updating...")
            self.get_assistant_client().update(agent_id, agent.model_dump(by_alias=True))
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

    def list_agents(self, kind: AgentKind=None, verbose: bool=False):
        if kind == AgentKind.NATIVE or kind is None:
            response = self.get_native_client().get()
            native_agents = [Agent.model_validate(agent) for agent in response]

            if verbose:
                agents_list = []
                for agent in native_agents:

                    agents_list.append(json.loads(agent.dumps_spec()))

                rich.print(rich.json.JSON(json.dumps(agents_list, indent=4)))
            else:
                native_table = rich.table.Table(
                    show_header=True, 
                    header_style="bold white", 
                    title="Agents",
                    show_lines=True
                )
                column_args = {
                    "Name": {},
                    "Description": {},
                    "LLM": {"overflow": "fold"},
                    "Style": {},
                    "Collaborators": {},
                    "Tools": {},
                    "Knowledge Base": {},
                    "ID": {},
                }
                for column in column_args:
                    native_table.add_column(column, **column_args[column])

                for agent in native_agents:
                    tool_names = self.get_agent_tool_names(agent.tools)
                    knowledge_base_names = self.get_agent_knowledge_base_names(agent.knowledge_base)
                    collaborator_names = self.get_agent_collaborator_names(agent.collaborators)

                    native_table.add_row(
                        agent.name,
                        agent.description,
                        agent.llm,
                        agent.style,
                        ", ".join(collaborator_names),
                        ", ".join(tool_names),
                        ", ".join(knowledge_base_names),
                        agent.id,
                    )
                rich.print(native_table)

      
        if kind == AgentKind.EXTERNAL or kind is None:
            response = self.get_external_client().get()

            external_agents = [ExternalAgent.model_validate(agent) for agent in response]

            response_dict = {agent["id"]: agent for agent in response}

            # Insert config values into config as config object is not retruned from api
            for external_agent in external_agents:
                if external_agent.id in response_dict:
                    response_data = response_dict[external_agent.id]
                    external_agent.config.enable_cot = response_data.get("enable_cot", external_agent.config.enable_cot)
                    external_agent.config.hidden = response_data.get("hidden", external_agent.config.hidden)

            external_agents_list = []
            if verbose:
                for agent in external_agents:
                    external_agents_list.append(json.loads(agent.dumps_spec()))
                rich.print(rich.json.JSON(json.dumps(external_agents_list, indent=4)))
            else:
                external_table = rich.table.Table(
                    show_header=True, 
                    header_style="bold white", 
                    title="External Agents",
                    show_lines=True
                )
                column_args = {
                    "Name": {},
                    "Title": {},
                    "Description": {},
                    "Tags": {},
                    "API URL": {"overflow": "fold"},
                    "Chat Params": {},
                    "Config": {},
                    "Nickname": {},
                    "App ID": {},
                    "ID": {}
                    }
                
                for column in column_args:
                    external_table.add_column(column, **column_args[column])
                
                for agent in external_agents:
                    connections_client =  get_connections_client()
                    app_id = connections_client.get_draft_by_id(agent.connection_id)

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
                rich.print(external_table)
        
        if kind == AgentKind.ASSISTANT or kind is None:
            response = self.get_assistant_client().get()

            assistant_agents = [AssistantAgent.model_validate(agent) for agent in response]

            response_dict = {agent["id"]: agent for agent in response}

            # Insert config values into config as config object is not retruned from api
            for assistant_agent in assistant_agents:
                if assistant_agent.id in response_dict:
                    response_data = response_dict[assistant_agent.id]
                    assistant_agent.config.api_version = response_data.get("api_version", assistant_agent.config.api_version)
                    assistant_agent.config.assistant_id = response_data.get("assistant_id", assistant_agent.config.assistant_id)
                    assistant_agent.config.crn = response_data.get("crn", assistant_agent.config.crn)
                    assistant_agent.config.service_instance_url = response_data.get("service_instance_url", assistant_agent.config.service_instance_url)
                    assistant_agent.config.environment_id = response_data.get("environment_id", assistant_agent.config.environment_id)
                    assistant_agent.config.authorization_url = response_data.get("authorization_url", assistant_agent.config.authorization_url)

            if verbose:
                for agent in assistant_agents:
                    rich.print(agent.dumps_spec())
            else:
                assistants_table = rich.table.Table(
                    show_header=True, 
                    header_style="bold white", 
                    title="Assistant Agents",
                    show_lines=True)
                column_args = {
                    "Name": {},
                    "Title": {},
                    "Description": {},
                    "Tags": {},
                    "Nickname": {},
                    "CRN": {},
                    "Instance URL": {},
                    "Assistant ID": {},
                    "Environment ID": {},
                    "ID": {}
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
                rich.print(assistants_table)

    def remove_agent(self, name: str, kind: AgentKind):
            try:
                if kind == AgentKind.NATIVE:
                    client = self.get_native_client()
                elif kind == AgentKind.EXTERNAL:
                    client = self.get_external_client()
                elif kind == AgentKind.ASSISTANT:
                    client = self.get_assistant_client()
                else:
                    raise ValueError("'kind' must be 'native'")

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

