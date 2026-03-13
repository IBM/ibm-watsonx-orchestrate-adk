import logging
import sys

from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient
from ibm_watsonx_orchestrate.client.agents.external_agent_client import ExternalAgentClient
from ibm_watsonx_orchestrate.client.agents.assistant_agent_client import AssistantAgentClient
from ibm_watsonx_orchestrate.client.connections import get_connections_client, get_connection_type
from typing import List
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

def get_available_connections() -> List[dict]:
    """
    Fetch all available connections from the orchestrate environment.
    Returns unique connections (deduplicated by app_id).
    
    Returns:
        List of connection dictionaries with 'app_id' and 'name' keys
    """
    try:
        connections_client = get_connections_client()
        connections = connections_client.list()
        
        unique_connections = {}
        for conn in connections:
            app_id = conn.app_id
            if conn.environment is None:
                continue
            
            if app_id not in unique_connections:
                try:
                    connection_type = get_connection_type(security_scheme=conn.security_scheme, auth_type=conn.auth_type)
                except:
                    connection_type = conn.auth_type or 'unknown'
                
                unique_connections[app_id] = {
                    'app_id': app_id,
                    'name': conn.name or app_id,
                    'auth_type': connection_type
                }
        
        return sorted(unique_connections.values(), key=lambda x: x['app_id'])
    except Exception as e:
        logger.error(f"Failed to fetch connections: {e}")
        return []

def prompt_select_app_ids(tool_name: str, available_connections: List[dict]) -> List[str]:
    """
    Interactive prompt to select one or more app IDs from available connections.
    Returns a list of selected app IDs.
    """
    if not available_connections:
        logger.warning("No connections available to select from")
        return []

    try:
        import tty
        import termios

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            tty.setcbreak(fd)

            current_index = 0
            selected_indices = set()
            first_render = True

            def render_menu():
                nonlocal first_render
                
                if not first_render:
                    lines_to_clear = 3 + len(available_connections)
                    sys.stdout.write(f'\033[{lines_to_clear}A')
                    sys.stdout.write('\033[J')
                else:
                    first_render = False
                    sys.stdout.write('\n')
                
                sys.stdout.write(f"\033[1;36mSelect connections for tool '{tool_name}'\033[0m\n")
                sys.stdout.write("\033[90m(Use ↑/↓ arrows to navigate, SPACE to select, ENTER to confirm, 'q' to skip)\033[0m\n\n")

                for i, conn in enumerate(available_connections):
                    checkbox = "[✓]" if i in selected_indices else "[ ]"

                    if i == current_index:
                        sys.stdout.write(f"\033[1;32m❯ {checkbox}\033[0m ")
                    else:
                        sys.stdout.write(f"  {checkbox} ")

                    display_name = f"{conn['name']} ({conn['app_id']}) - {conn['auth_type']}"
                    sys.stdout.write(f"{display_name}\n")

                sys.stdout.flush()

            render_menu()

            while True:
                char = sys.stdin.read(1)

                # Handle escape sequences (arrow keys)
                if char == '\x1b':
                    next_char = sys.stdin.read(1)
                    if next_char == '[':
                        arrow = sys.stdin.read(1)
                        if arrow == 'A':  # Up arrow
                            current_index = max(0, current_index - 1)
                            render_menu()
                        elif arrow == 'B':  # Down arrow
                            current_index = min(len(available_connections) - 1, current_index + 1)
                            render_menu()

                # Handle spacebar (toggle selection)
                elif char == ' ':
                    if current_index in selected_indices:
                        selected_indices.remove(current_index)
                    else:
                        selected_indices.add(current_index)
                    render_menu()

                # Handle enter (confirm)
                elif char in ('\r', '\n'):
                    break

                # Handle 'q' (quit/skip)
                elif char.lower() == 'q':
                    selected_indices.clear()
                    break

                # Handle Ctrl+C
                elif char == '\x03':
                    raise KeyboardInterrupt()

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            # Clear the menu area
            lines_to_clear = 3 + len(available_connections)
            sys.stdout.write(f'\033[{lines_to_clear}A')  # Move up
            sys.stdout.write('\033[J')  # Clear from cursor down
            sys.stdout.flush()

        # Get selected app_ids
        selected_app_ids = [available_connections[i]['app_id'] for i in sorted(selected_indices)]

        if selected_app_ids:
            logger.info(f"Selected {len(selected_app_ids)} connection(s) for tool '{tool_name}': {', '.join(selected_app_ids)}")
        else:
            logger.info(f"No connections selected for tool '{tool_name}'")

        return selected_app_ids

    except (ImportError, AttributeError):
        # Fallback for non-Unix systems or missing termios
        logger.warning("Interactive terminal not available. Using simple input method.")
        return _prompt_select_app_ids_fallback(tool_name, available_connections)
    except KeyboardInterrupt:
        logger.info("\nConnection selection cancelled by user")
        return []
    except Exception as e:
        logger.error(f"Error during connection selection: {e}")
        return _prompt_select_app_ids_fallback(tool_name, available_connections)


def _prompt_select_app_ids_fallback(tool_name: str, available_connections: List[dict]) -> List[str]:
    """
    Fallback method for connection selection when interactive terminal is not available.
    Uses simple numbered input.
    """
    print(f"\nSelect connections for tool '{tool_name}':")
    print("(Enter numbers separated by commas, or press Enter to skip)\n")

    for i, conn in enumerate(available_connections, 1):
        display_name = f"{conn['name']} ({conn['app_id']}) - {conn['auth_type']}"
        print(f"  {i}. {display_name}")

    try:
        user_input = input("\nYour selection (e.g., 1,3,4): ").strip()

        if not user_input:
            logger.info(f"No connections selected for tool '{tool_name}'")
            return []

        selected_indices = []
        for part in user_input.split(','):
            try:
                index = int(part.strip()) - 1
                if 0 <= index < len(available_connections):
                    selected_indices.append(index)
            except ValueError:
                continue

        selected_app_ids = [available_connections[i]['app_id'] for i in selected_indices]

        if selected_app_ids:
            logger.info(f"Selected {len(selected_app_ids)} connection(s) for tool '{tool_name}': {', '.join(selected_app_ids)}")
        else:
            logger.info(f"No valid connections selected for tool '{tool_name}'")

        return selected_app_ids

    except (EOFError, KeyboardInterrupt):
        logger.info("\nConnection selection cancelled by user")
        return []
