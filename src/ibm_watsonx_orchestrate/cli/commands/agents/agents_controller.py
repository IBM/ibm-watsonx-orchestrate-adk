import yaml
import json
import typer
import importlib
import inspect
import sys
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
    with open(file, "r") as f:
        if file.endswith(".yaml") or file.endswith(".yml"):
            content = yaml.load(f, Loader=yaml.SafeLoader)
            agent = create_agent_from_spec(content)
            return [agent]
        elif file.endswith(".json"):
            content = json.load(f)
            agent = create_agent_from_spec(content)
            return [agent]
        elif file.endswith(".py"):
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
        if isinstance(agent, ExpertAgent):
            self.get_expert_client().create(agent.model_dump())

        self.persist_record(agent, **kwargs)

    def update_agent(
        self, agent_id: str, agent: OrchestrateAgent | ExpertAgent, **kwargs
    ) -> None:
        if isinstance(agent, OrchestrateAgent):
            self.get_orchestrator_client().update(agent_id, agent.model_dump())
        if isinstance(agent, ExpertAgent):
            self.get_expert_client().update(agent_id, agent.model_dump())

        self.persist_record(agent, **kwargs)

    def persist_record(self, agent: OrchestrateAgent | ExpertAgent, **kwargs):
        if "output_file" in kwargs and kwargs["output_file"] is not None:
            agent.dump_spec(kwargs["output_file"])
