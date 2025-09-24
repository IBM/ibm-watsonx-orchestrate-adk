from ibm_watsonx_orchestrate.agent_builder.agents import SpecVersion
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import (
    AgentsController,
    AgentKind
)
from ibm_watsonx_orchestrate.cli.common import ListFormats

from typing_extensions import Optional, List, Literal
from ibm_watsonx_orchestrate_mcp_server.utils.common import silent_call;

from ibm_watsonx_orchestrate_mcp_server.utils.files.files import get_working_directory_path
from ibm_watsonx_orchestrate_mcp_server.src.agents.types import ListAgents, CreateAgentOptions, AnyAgent

def __get_existing_agent(name: str, kind: str) -> Optional[AnyAgent]:
    """
    Get an existing agent with the given name.
    """
    ac: AgentsController = AgentsController()
    try:
        agent: Optional[AnyAgent] = silent_call(fn=ac.get_agent, name=name, kind=kind)
        return agent
    except:
        return None

def list_agents(
    kind: Optional[AgentKind] = None,
    verbose: bool = False
) -> ListAgents:
    """
    Get a list of all the agents in watsonx Orchestrate (wxo)

    Args:
        kind (AgentKind, optional): Return only agents of the kind specified. If None is passed then return everything. Allowed values ['native' | 'external' | 'assistant' | None] (default: None)
        verbose (bool): When set the tool will return the raw agents specifications without resolving ids to names. This should only be done in edge cases as names are more widely used. (default: False)
    
    Returns:
        ListAgents: A class containing lists of native, assistant and external agents.
    """
    ac: AgentsController = AgentsController()
    format: Literal[ListFormats.JSON] | None = ListFormats.JSON if not verbose else None
    output: ListAgents = silent_call(fn=ac.list_agents, format=format, kind=kind, verbose=verbose)

    return output

def create_or_update_agent(options: CreateAgentOptions) -> AnyAgent:
    """
    Create or update an agent based on the provided options.
    If the agent name already exists, the agent will be updated with the provided options. Else it will create a new agent.

    Args:
        options (CreateAgentOptions): The options to use when creating the agent.
    
    Returns:
        AnyAgent: The newly created agent.
    """
    ac: AgentsController = AgentsController()
    existing_agents = {
        AgentKind.NATIVE:  __get_existing_agent(options.name, AgentKind.NATIVE),
        AgentKind.EXTERNAL: __get_existing_agent(options.name, AgentKind.EXTERNAL),
        AgentKind.ASSISTANT: __get_existing_agent(options.name, AgentKind.ASSISTANT)
    }
    existing_agents_list = [value for value in existing_agents.values() if value is not None]

    existing_agent = None
    if len(existing_agents_list) == 1:
        existing_agent = existing_agents_list[0]
    elif len(existing_agents_list) > 1:
        raise Exception(f"Multiple agents found with name {options.name} update is ambiguous. Please delete the duplicate and try again.")
    
    if not existing_agent:
        if not options.kind:
            options.kind = AgentKind.NATIVE
        agent: AnyAgent = silent_call(fn=ac.generate_agent_spec, **options.model_dump())
    else:
        agent = existing_agent.model_copy(update=options.model_dump(exclude_unset=True))
    silent_call(fn=ac.publish_or_update_agents, agents=[agent])
    agent.spec_version = SpecVersion.V1
    return agent

def import_agent(path: str, app_id: Optional[str]) -> List[AnyAgent]:
    """
    Import an agent into the watsonx Orchestrate platform using Agent spec files

    Args:
        path (str): The absolute of relative path to an agent spec file
        app_id (str | None): An optional app_id which relates an Orchestrate connection object to the Agent. Used for external and assistant Agent authentication.
    
    Returns:
        List[AnyAgent]: The newly created agent.
    """

    working_directory_path: str = get_working_directory_path(path)
    ac: AgentsController = AgentsController()
    agents: List[AnyAgent] = silent_call(ac.import_agent, file=working_directory_path, app_id=app_id)
    silent_call(fn=ac.publish_or_update_agents, agents=agents)
    return agents

def remove_agent(name: str, kind: AgentKind) -> str:
    """
    Remove an agent from the watsonx Orchestrate platform

    Args:
        name (str): The name of the agent to remove
        kind (AgentKind): The kind of agent to remove
    
    Returns:
        str: A message indicating the success of the removal
    """

    ac: AgentsController = AgentsController()
    silent_call(fn=ac.remove_agent, name=name, kind=kind)

    return f"The Agent {name} successfully removed"

def export_agent(name: str, kind: AgentKind, output_file_path: str, agent_only_flag: bool = False) -> str:
    """
    Export an agent from the watsonx Orchestrate platform.
    Args:
        name (str): The name of the agent to export
        kind (AgentKind): The kind of agent to export
        output_file_path (str): The path to export the agent to. Should be a zip file with a '.zip' extension unless the agent_only_flag is set in which case it should a yaml file with a '.yaml' extension.
        agent_only_flag (bool, optional): If set to True, only the agent definition will be exported and not the agent's dependencies. Defaults to False.
    
    Returns:
        str: A message indicating the success of the export
    """
    working_directory_output_path: str = get_working_directory_path(output_file_path)
    ac: AgentsController = AgentsController()
    silent_call(fn=ac.export_agent, name=name, kind=kind, output_path=working_directory_output_path, agent_only_flag=agent_only_flag)
    
    return f"The Agent {name} successfully exported"

def deploy_agent(name: str,) -> str:
    """
    Deploys an agent to the watsonx Orchestrate platform. Promoting it from the draft environment to the live environment. The agent must already have been created or imported into the Orchestrate platform.

    Args:
        name (str): The name of the agent you want to deploy.
    
    Returns:
        str: A message indicating the success of the deployment
    """
    ac: AgentsController = AgentsController()
    silent_call(fn=ac.deploy_agent, name=name)

    return f"The Agent {name} successfully deployed"

def undeploy_agent(name: str,) -> str:
    """
    Undeploys an agent from the watsonx Orchestrate platform. Demoting it from the live environment to the draft environment.
    Args:
        name (str): The name of the agent you want to undeploy.

    Returns:
        str: A message indicating the success of the undeployment
    """
    ac: AgentsController = AgentsController()
    silent_call(fn=ac.undeploy_agent, name=name)
    
    return f"The Agent {name} successfully undeployed"

__tools__ = [list_agents, create_or_update_agent, import_agent, remove_agent, export_agent]