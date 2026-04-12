import logging

from typing import Optional, List, Dict

from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient

logger = logging.getLogger(__name__)


def get_agent_name_to_id_mapping() -> Dict[str, str]:
    """
    Fetch all agents and create a mapping from agent name to agent ID.
    
    Returns:
        Dictionary mapping agent names to agent IDs
    """
    try:
        agent_client = instantiate_client(AgentClient)
        agents = agent_client.get()
        
        # Handle both single agent dict and list of agents
        if isinstance(agents, dict):
            agents = [agents]
        
        # Create mapping: agent name -> agent ID
        name_to_id = {}
        for agent in agents:
            if isinstance(agent, dict):
                agent_name = agent.get('name')
                agent_id = agent.get('id')
                if agent_name and agent_id:
                    name_to_id[agent_name] = agent_id
        
        return name_to_id
    except Exception as e:
        logger.warning(f"Failed to fetch agent mapping: {e}")
        return {}


def resolve_agent_names_to_ids(agent_names: Optional[List[str]], agent_ids: Optional[List[str]]) -> Optional[List[str]]:
    """
    Convert agent names to agent IDs using the agent API and merge with provided agent IDs.
    
    This function handles three cases:
    1. Only agent_ids provided: Returns them as-is
    2. Only agent_names provided: Resolves to IDs
    3. Both provided: Resolves names to IDs and merges with provided IDs (no duplicates)
    
    Args:
        agent_names: List of agent names to convert
        agent_ids: List of agent IDs (if already provided)
    
    Returns:
        List of agent IDs (merged and deduplicated), or None if no agents specified
    """
    # Start with provided agent_ids (or empty list)
    all_agent_ids = list(agent_ids) if agent_ids else []
    # If no agent_names provided, return what we have
    if not agent_names:
        return all_agent_ids if all_agent_ids else None
    
    # Fetch agent mapping to resolve names
    name_to_id = get_agent_name_to_id_mapping()
    
    if not name_to_id:
        logger.warning("Could not fetch agent mapping. Filtering by agent name may not work due to API bug.")
        return all_agent_ids if all_agent_ids else None
    
    # Convert names to IDs
    for name in agent_names:
        agent_id = name_to_id.get(name)
        if agent_id:
            if agent_id not in all_agent_ids:  # Avoid duplicates
                all_agent_ids.append(agent_id)
        else:
            logger.warning(f"Agent '{name}' not found. Available agents: {', '.join(name_to_id.keys())}")
    
    return all_agent_ids if all_agent_ids else None
