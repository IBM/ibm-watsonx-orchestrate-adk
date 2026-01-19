import logging
import sys

from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient
from ibm_watsonx_orchestrate.client.agents.external_agent_client import ExternalAgentClient
from ibm_watsonx_orchestrate.client.agents.assistant_agent_client import AssistantAgentClient
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient

logger = logging.getLogger(__name__)

def get_agent_id_by_name(agent_name: str) -> str:
    """
    Resolve agent name to ID by searching across all agent client types.
    Automatically discovers all agent client classes that extend BaseWXOClient.
    
    Args:
        agent_name: Name of the agent to find
        
    Returns:
        Agent ID string
        
    Raises:
        SystemExit: If no agent found or multiple agents with same name
    """
    
    # List of all agent client classes (add new ones here when created)
    agent_client_classes = [
        AgentClient,
        ExternalAgentClient,
        AssistantAgentClient,
    ]
    
    all_agents = []
    
    # Search across all agent client types
    for client_class in agent_client_classes:
        try:
            client = instantiate_client(client_class)
            agents = client.get_draft_by_name(agent_name)
            all_agents.extend(agents)
        except Exception as e:
            logger.warning(f"Error searching {client_class.__name__}: {e}")
            continue
    
    if len(all_agents) == 0:
        logger.error(f"No agent found with name '{agent_name}'")
        logger.info("Tip: Use 'orchestrate agents list' to see available agents")
        sys.exit(1)
    elif len(all_agents) > 1:
        logger.error(f"Multiple agents found with name '{agent_name}'. Please use a unique agent name or specify --agent-id instead.")
        logger.info("Found agents:")
        for agent in all_agents:
            logger.info(f"  - {agent.get('name')} (ID: {agent.get('id')}, Style: {agent.get('style')})")
        sys.exit(1)
    
    # Get agent ID with type safety
    agent_id = all_agents[0].get('id')
    if not agent_id:
        logger.error(f"Agent '{agent_name}' found but has no ID")
        sys.exit(1)
    
    logger.info(f"Using agent: {agent_name} (ID: {agent_id})")
    return agent_id
