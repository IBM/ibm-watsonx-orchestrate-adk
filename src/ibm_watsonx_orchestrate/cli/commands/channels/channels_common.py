# Common utilities for channel and phone channel controllers

import os
import sys
import json
import logging
from functools import wraps
from typing import Optional, List, Dict, Any, Callable, TypeVar

from ibm_watsonx_orchestrate.client.utils import is_local_dev
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


def block_local_dev() -> Callable[[F], F]:
    """Decorator to block operations in local development environment.

    The decorator checks for an 'enable_developer_mode' parameter in kwargs
    or the WXO_DEV_ONLY_ENABLE_LOCAL environment variable.
    If enable_developer_mode=True or env var is set, shows warning but allows operation.
    If enable_developer_mode=False or not provided and env var not set, blocks with error.

    Raises:
        SystemExit: If in local dev and developer mode is not enabled
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if enable_developer_mode is in kwargs or environment variable, default to False
            enable_developer_mode = kwargs.pop('enable_developer_mode', False) or os.environ.get("WXO_DEV_ONLY_ENABLE_LOCAL")

            if is_local_dev():
                if not enable_developer_mode:
                    logger.error("Channel authoring is not available in local development environment.")
                    sys.exit(1)
                else:
                    logger.warning("DEVELOPER MODE ENABLED - Proceed at your own risk! No official support will be provided.")
                    logger.warning("Operations in local development may cause unexpected behavior.")
                    logger.warning("This environment is not validated for production use.")
            return func(*args, **kwargs)
        return wrapper  # type: ignore
    return decorator


def parse_field(
    field_list: Optional[List[str]],
    nested_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Parse CLI field options in key=value format into a dictionary.

    Automatically detects and parses JSON values for lists and objects.

    Args:
        field_list: List of field strings in "key=value" format
        nested_fields: Optional list of field names that should be nested under 'security' key

    Returns:
        Dictionary with parsed field values
    """
    result = {}

    if not field_list:
        return result

    nested_fields = nested_fields or []

    for field_str in field_list:
        if "=" not in field_str:
            raise ValueError(f"Field '{field_str}' must be in key=value format")

        key, value = field_str.split("=", 1)
        key = key.strip()
        value = value.strip()

        # Try to parse as JSON for complex types (lists, dicts)
        parsed_value = value
        if value and (value.startswith('[') or value.startswith('{')):
            try:
                parsed_value = json.loads(value)
                logger.debug(f"Parsed field '{key}' as JSON: {type(parsed_value).__name__}")
            except json.JSONDecodeError as e:
                logger.warning(f"Field '{key}' looks like JSON but failed to parse: {e}. Using as string.")
                parsed_value = value

        # Check if this field should be nested under 'security'
        if key in nested_fields:
            if 'security' not in result:
                result['security'] = {}
            result['security'][key] = parsed_value
        else:
            result[key] = parsed_value

    return result


def check_local_dev_block(enable_developer_mode: bool = False, operation_type: str = "operations") -> None:
    """Check if channel/phone operations should be blocked in local dev.

    Args:
        enable_developer_mode: If True, allow operations in local dev with warnings
        operation_type: Type of operation (e.g., "Channel", "Phone config")
    """
    if is_local_dev():
        if not enable_developer_mode:
            logger.error(f"{operation_type} authoring is not available in local development environment.")
            sys.exit(1)
        else:
            logger.warning("DEVELOPER MODE ENABLED - Proceed at your own risk! No official support will be provided.")
            logger.warning(f"{operation_type} in local development may cause unexpected behavior.")
            logger.warning("This environment is not validated for production use.")


def get_agent_id_by_name(agent_client: AgentClient, agent_name: str) -> str | None:
    """Look up agent ID by agent name.

    Args:
        agent_client: Initialized AgentClient instance
        agent_name: Name of the agent

    Returns:
        Agent ID string
    """
    agent_spec = agent_client.get_draft_by_name(agent_name)

    if len(agent_spec) > 1:
        logger.error(f"Multiple agents with the name '{agent_name}' found. Please use a unique agent name.")
        sys.exit(1)
    if len(agent_spec) == 0:
        logger.error(f"No agent with the name '{agent_name}' found.")
        sys.exit(1)

    return agent_spec[0].get('id')


def get_agent_name_by_id(agent_client: AgentClient, agent_id: str) -> str | None:
    """Look up agent name by agent ID.

    Args:
        agent_client: Initialized AgentClient instance
        agent_id: ID of the agent

    Returns:
        Agent Name string
    """
    agent_spec = agent_client.get_draft_by_id(agent_id)

    if not agent_spec or not isinstance(agent_spec, dict):
        logger.error(f"No agent with the ID '{agent_id}' found.")
        sys.exit(1)

    return agent_spec.get('name')


def get_environment_id(agent_client: AgentClient, agent_name: str, env: str) -> str:
    """Get environment ID by agent name and environment name (draft/live).

    Args:
        agent_client: Initialized AgentClient instance
        agent_name: Name of the agent
        env: Environment name (draft or live)

    Returns:
        Environment ID
    """
    existing_agents = agent_client.get_draft_by_name(agent_name)

    if not existing_agents:
        raise ValueError(f"No agent found with the name '{agent_name}'")

    agent = existing_agents[0]
    agent_environments = agent.get("environments", [])

    is_local = is_local_dev()
    target_env = env or 'draft'

    if is_local:
        if env == 'live':
            logger.warning('Live environments do not exist for Local env, defaulting to draft.')
        target_env = 'draft'

    filtered_environments = [e for e in agent_environments if e.get("name") == target_env]

    if not filtered_environments:
        logger.error(f'This agent does not exist in the {target_env} environment.')
        if env == 'live':
            logger.error(f'You need to deploy the agent to {env} first.')
        sys.exit(1)

    return filtered_environments[0].get("id")


def build_local_webhook_url(
    agent_id: str,
    environment_id: str,
    channel_path: str,
    resource_id: str,
    endpoint: str = "runs"
) -> str:
    """Build webhook/event URL for local development environment.

    Args:
        agent_id: Agent identifier
        environment_id: Environment identifier
        channel_path: Channel type path (e.g., 'genesys_bot_connector', 'slack')
        resource_id: Channel/config identifier
        endpoint: Endpoint name (default: 'runs')

    Returns:
        Local webhook URL path
    """
    logger.info("Local environment detected")
    return f"/v1/agents/{agent_id}/environments/{environment_id}/channels/{channel_path}/{resource_id}/{endpoint}"


def build_saas_webhook_url(
    base_url: str,
    subscription_id: Optional[str],
    agent_id: str,
    environment_id: str,
    channel_path: str,
    resource_id: str,
    endpoint: str = "events",
    protocol_override: Optional[str] = None
) -> str:
    """Build webhook/event URL for SaaS environment.

    Args:
        base_url: Base URL from the client
        subscription_id: Subscription ID from token (can be None)
        agent_id: Agent identifier
        environment_id: Environment identifier
        channel_path: Channel type path (e.g., 'twilio_whatsapp', 'slack')
        resource_id: Channel/config identifier
        endpoint: Endpoint name (default: 'events')
        protocol_override: Optional protocol to use (e.g., 'wss://')

    Returns:
        Full SaaS webhook URL
    """
    # Clean up base URL by removing API version paths
    base_url_clean = base_url.replace('/v1/orchestrate', '').replace('/v1', '')

    # Parse URL to extract domain and instance ID
    if '/instances/' not in base_url_clean:
        logger.warning("Could not parse base_url to construct proper webhook URL")
        return f"{base_url_clean}/agents/{agent_id}/environments/{environment_id}/channels/{channel_path}/{resource_id}/{endpoint}"

    parts = base_url_clean.split('/instances/')
    domain = parts[0].replace('https://api.', f'{protocol_override or "https://"}channels.')
    instance_id = parts[1].rstrip('/')

    # Construct tenant ID
    tenant_id = get_tenant_id(subscription_id, instance_id)

    return f"{domain}/tenants/{tenant_id}/agents/{agent_id}/environments/{environment_id}/channels/{channel_path}/{resource_id}/{endpoint}"

def get_tenant_id(subscription_id: str | None, instance_id: str) -> str:
    """Construct tenant ID from subscription and instance IDs.

    Args:
        subscription_id: Subscription ID obtained from JWT
        instance_id: Instance ID from URL

    Returns:
        Combined tenant ID string
    """
    if not subscription_id:
        logger.warning("Missing subscription ID in token. The generated Event URL may be invalid.")
        return instance_id

    return f"{subscription_id}_{instance_id}"
