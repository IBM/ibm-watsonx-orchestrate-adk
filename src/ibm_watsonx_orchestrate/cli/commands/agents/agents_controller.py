import yaml
import json
import rich
import typer
import requests
import importlib
import inspect
import sys
import logging
from pathlib import Path
from enum import Enum

from typing import Iterable, List
from ibm_watsonx_orchestrate.cli.commands.tools.tools_controller import (
    import_python_tool,
)
from ibm_watsonx_orchestrate.agent_builder.agents.expert_agent import ExpertAgent
from ibm_watsonx_orchestrate.agent_builder.agents.orchestrate_agent import (
    OrchestrateAgent,
)
from ibm_watsonx_orchestrate.agent_builder.agents.types import (
    SupervisorConfig,
    ExpertAgentType,
)
from ibm_watsonx_orchestrate.client.agents.orchestrator_agent_client import (
    OrchestratorAgentClient,
)
from ibm_watsonx_orchestrate.client.agents.expert_agent_client import ExpertAgentClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client

DEFAULT_REFLECTION_RETRY_COUNT_WHEN_ENABLED = 3

logger = logging.getLogger(__name__)

class AgentTypes(str, Enum):
    expert = "expert"
    orchestrator = "orchestrator"


def import_python_agent(file: str) -> list[ExpertAgent | OrchestrateAgent]:
    # Import tools
    import_python_tool(file)

    file_path = Path(file)
    file_directory = file_path.parent
    file_name = file_path.stem
    sys.path.append(str(file_directory))
    module = importlib.import_module(file_name)
    del sys.path[-1]

    agents = []
    for _, obj in inspect.getmembers(module):
        if isinstance(obj, ExpertAgent) or isinstance(obj, OrchestrateAgent):
            agents.append(obj)
    return agents


def create_agent_from_spec(agent_details: dict) -> ExpertAgent | OrchestrateAgent:
    match agent_details["type"]:
        case "orchestrator":
            agent_details.pop("type", None)
            agent = OrchestrateAgent(**agent_details)
        case x if x in [e.value for e in ExpertAgentType]:
            agent = ExpertAgent(**agent_details)
        case _:
            raise ValueError("'type' must be either orchestrator or expert")

    return agent

def parse_file(file: str) -> list[ExpertAgent | OrchestrateAgent]:
    with open(file, 'r') as f:
        if file.endswith('.yaml') or file.endswith('.yml'):
            content = yaml.load(f, Loader=yaml.SafeLoader)
            agent = create_agent_from_spec(content)
            return [agent]
        elif file.endswith(".json"):
            content = json.load(f)
            agent = create_agent_from_spec(content)
            return [agent]
        elif file.endswith('.py'):
            agents = import_python_agent(file)
            return agents
        else:
            raise ValueError("file must end in .json, .yaml, .yml or .py")


def parse_create_expert_args(name: str, type: AgentTypes, **args) -> dict:
    agent_details = {
        "name": name,
        "type": type,
        "description": args.get("description", ""),
        "role": args.get("role", None),
        "goal": args.get("goal", None),
        "instructions": args.get("instructions", None),
        "backstory": args.get("backstory", None),
        "llm": args.get("llm", None)
    }

    tools = args.get("tools", "")

    tools = [x.strip() for x in tools.split(",")] if tools is not None else []
    agent_details["tools"] = tools
    return agent_details


def parse_create_orchestrator_args(name: str, **args) -> dict:
    agent_details = {
        "name": name,
        "management_style": args.get("management_style", ""),
        "llm": args.get("llm", None),
    }

    agent_details["management_style_config"] = None

    if "management_style_config" in args and args["management_style_config"]:
        management_style_config = args["management_style_config"]
        config = {}
        for kv_pair in management_style_config.split(","):
            k, v = kv_pair.split("=")
            k, v = k.strip(), v.strip()
            if k == "reflection_enabled":
                v = v.lower() == "true"
            if k == "reflection_retry_count":
                try:
                    v = int(v)
                except ValueError as e:
                    raise ValueError(f"{v} is not a valid retry count")
            config[k] = v
        if (
            config.get("reflection_enabled", False)
            and "reflection_retry_count" not in config
        ):
            config[
                "reflection_retry_count"
            ] = DEFAULT_REFLECTION_RETRY_COUNT_WHEN_ENABLED

        supervisor_config = SupervisorConfig(**config)
        agent_details["management_style_config"] = supervisor_config

    agents = args.get("agents", "")
    agents = [x.strip() for x in agents.split(",")] if agents is not None else []
    agent_details["agents"] = agents
    return agent_details


def validate_create_expert_args(**kwargs) -> None:
    missing_params = []
    if kwargs["role"] is None or len(kwargs["role"]) == 0:
        missing_params.append("--role")
    if kwargs["goal"] is None or len(kwargs["goal"]) == 0:
        missing_params.append("--goal")
    if kwargs["instructions"] is None or len(kwargs["instructions"]) == 0:
        missing_params.append("--instructions")

    if kwargs["tools"] is None or len(kwargs["tools"]) == 0:
        missing_params.append("--tools")

    if len(missing_params) > 0:
        raise typer.BadParameter(
            f"Missing flags {missing_params} required for expert agent. These value cannot be missing or empty."
        )


def validate_create_orchestrator_args(**kwargs) -> None:
    missing_params = []
    if kwargs["agents"] is None or len(kwargs["agents"]) == 0:
        missing_params.append("--agents")

    if len(missing_params) > 0:
        raise typer.BadParameter(
            f"Missing flags {missing_params} required for type 'orchestrator'. These value cannot be missing ot empty."
        )


class AgentsController:
    def __init__(self):
        self.orchestrator_client = None
        self.expert_client = None

    def get_expert_client(self):
        if not self.expert_client:
            self.expert_client = instantiate_client(ExpertAgentClient)
        return self.expert_client

    def get_orchestrator_client(self):
        if not self.orchestrator_client:
            self.orchestrator_client = instantiate_client(OrchestratorAgentClient)
        return self.orchestrator_client

    @staticmethod
    def import_agent(file: str) -> Iterable:
        agents = parse_file(file)
        return agents

    @staticmethod
    def generate_agent_spec(
        name: str, type: AgentTypes, **kwargs
    ) -> OrchestrateAgent | ExpertAgent:
        match type.value:
            case "orchestrator":
                validate_create_orchestrator_args(**kwargs)
                agent_details = parse_create_orchestrator_args(name, **kwargs)
                agent = OrchestrateAgent(**agent_details)
            case x if x in [e.value for e in ExpertAgentType]:
                validate_create_expert_args(**kwargs)
                agent_details = parse_create_expert_args(name, type, **kwargs)
                agent = ExpertAgent(**agent_details)
            case _:
                raise ValueError("'type' must be either orchestrator or expert")
        return agent

    def get_all_expert_agents(self):
        return {entry["name"]: entry["id"] for entry in self.get_expert_client().get()}

    def get_all_orchestrator_agents(self):
        return {
            entry["name"]: entry["id"] for entry in self.get_orchestrator_client().get()
        }

    def publish_or_update_agents(
        self, agents: Iterable[OrchestrateAgent | ExpertAgent]
    ):
        existing_expert_agent = None
        existing_orchestrator_agent = None
        for agent in agents:
            exist = False
            agent_id = None
            if isinstance(agent, ExpertAgent):
                if not existing_expert_agent:
                    existing_expert_agent = self.get_all_expert_agents()
                if agent.name in existing_expert_agent:
                    exist = True
                    agent_id = agent.name
            if isinstance(agent, OrchestrateAgent):
                if not existing_orchestrator_agent:
                    existing_orchestrator_agent = self.get_all_orchestrator_agents()
                if agent.name in existing_orchestrator_agent:
                    agent_id = agent.name
                    exist = True

            if exist:
                self.update_agent(agent_id=agent_id, agent=agent)
            else:
                self.publish_agent(agent)

    def publish_agent(self, agent: OrchestrateAgent | ExpertAgent, **kwargs) -> None:
        if isinstance(agent, OrchestrateAgent):
            self.get_orchestrator_client().create(agent.model_dump())
            logger.info(f"Orchestrator Agent '{agent.name}' imported successfully")
        if isinstance(agent, ExpertAgent):
            self.get_expert_client().create(agent.model_dump())
            logger.info(f"Expert Agent '{agent.name}' imported successfully")

        self.persist_record(agent, **kwargs)

    def update_agent(
        self, agent_id: str, agent: OrchestrateAgent | ExpertAgent, **kwargs
    ) -> None:
        if isinstance(agent, OrchestrateAgent):
            logger.info(f"Existing Orchestrator Agent '{agent.name}' found. Updating...")
            self.get_orchestrator_client().update(agent_id, agent.model_dump())
            logger.info(f"Orchestrator Agent '{agent.name}' updated successfully")
        if isinstance(agent, ExpertAgent):
            logger.info(f"Existing Expert Agent '{agent.name}' found. Updating...")
            self.get_expert_client().update(agent_id, agent.model_dump())
            logger.info(f"Expert Agent '{agent.name}' updated successfully")

        self.persist_record(agent, **kwargs)

    def persist_record(self, agent: OrchestrateAgent | ExpertAgent, **kwargs):
        if "output_file" in kwargs and kwargs["output_file"] is not None:
            agent.dump_spec(kwargs["output_file"])
    
    def list_agents(self, type: AgentTypes=None, verbose: bool=False):
        if type == AgentTypes.orchestrator or type is None:
            response = self.get_orchestrator_client().get()
            orchestrator_agents = [OrchestrateAgent.model_validate(agent) for agent in response]

            if verbose:
                for agent in orchestrator_agents:
                    rich.print(agent.dumps_spec())
            else:
                orchestrator_table = rich.table.Table(
                    show_header=True, 
                    header_style="bold white", 
                    title="Orchestrator Agents",
                    show_lines=True)
                column_args = {
                    "Name": {},
                    "Management Style": {}, 
                    "Management Style Config": {}, 
                    "LLM": {"overflow": "fold"}, 
                    "Agents": {}
                    }
                for column in column_args:
                    orchestrator_table.add_column(column, **column_args[column])
                
                for agent in orchestrator_agents:
                    orchestrator_table.add_row(
                        agent.name,
                        agent.management_style,
                        agent.management_style_config.model_dump_json(),
                        agent.llm,
                        ", ".join(agent.agents)
                    )
                rich.print(orchestrator_table)

        if type == AgentTypes.expert or type is None:
            response = self.get_expert_client().get()
            expert_agents = [ExpertAgent.model_validate(agent) for agent in response]

            if verbose:
                for agent in expert_agents:
                    rich.print(agent.dumps_spec())
            else:
                expert_table = rich.table.Table(
                    show_header=True, 
                    header_style="bold white", 
                    title="Expert Agents",
                    show_lines=True)
                column_args = {
                    "Name": {},
                    "Type": {},
                    "Description": {},
                    "Role": {},
                    "Goal": {},
                    "Instructions": {}, 
                    "Backstory": {},
                    "LLM": {"overflow": "fold"},
                    "Tools": {}}
                
                for column in column_args:
                    expert_table.add_column(column, **column_args[column])
                
                for agent in expert_agents:
                    expert_table.add_row(
                        agent.name,
                        agent.type,
                        agent.description,
                        agent.role,
                        agent.goal,
                        agent.instructions,
                        agent.backstory,
                        agent.llm,
                        ", ".join(agent.tools)
                    )
                rich.print(expert_table)

    def remove_agent(self, name: str, type: AgentTypes):
            try:
                if type == AgentTypes.orchestrator:
                    self.get_orchestrator_client().delete(agent_id=name)
                elif type == AgentTypes.expert:
                    self.get_expert_client().delete(agent_id=name)
                else:
                    raise ValueError("'type' must be either 'expert' or 'orchestrator'")
                
                logger.info(f"Successfully removed agent {name}")
            except requests.HTTPError as e:
                logger.error(e.response.text)
                exit(1)

