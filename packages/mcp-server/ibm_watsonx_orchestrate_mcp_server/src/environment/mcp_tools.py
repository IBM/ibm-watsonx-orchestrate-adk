"""
Add 'orchestrate environment' commands to MCP Server

Motivation: users should be able to ask Bob to manage WXO environments
without running CLI commands manually.

Maps the four CLI sub-commands to MCP tools so Bob can call them directly:

    list_environments    →  orchestrate environment list
    add_environment      →  orchestrate environment add
    remove_environment   →  orchestrate environment remove
    activate_environment →  orchestrate environment activate

Each tool delegates to environment_controller. CLI commands were not reused
directly because they print to stdout and return None; MCP tools must return
structured data the AI can reason about.
"""

# Reuse controller — it owns all business rules (reserved names, token
# validation, auth branching, config writes).
from ibm_watsonx_orchestrate.cli.commands.environment import environment_controller
from ibm_watsonx_orchestrate.cli.commands.environment.types import EnvironmentAuthType

# list_environments reads config directly (controller returns None for this op),
# so Config and its constants are needed at module level.
from ibm_watsonx_orchestrate.cli.config import (
    Config,
    ENVIRONMENTS_SECTION_HEADER,  # ini section: all environments
    CONTEXT_SECTION_HEADER,       # ini section: runtime context
    CONTEXT_ACTIVE_ENV_OPT,       # key: active environment name
    ENV_WXO_URL_OPT,              # key: instance URL
)

# Controllers call sys.exit() and write to stdout. silent_call suppresses
# stdout, redirects logging, and converts SystemExit → Exception so the
# server stays alive and returns a structured error to the client.
from ibm_watsonx_orchestrate_mcp_server.utils.common import silent_call


def list_environments() -> list[dict]:
    """
    List all configured watsonx Orchestrate environments.

    Equivalent to: orchestrate environment list

    Returns:
        list[dict]: A list of configured environments, each containing the environment
            name, URL, and whether it is currently active.
    """
    # list_envs() renders a rich table and returns None; read config directly.
    cfg = Config()
    active_env = cfg.read(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
    envs = cfg.get(ENVIRONMENTS_SECTION_HEADER)

    result = []
    for name, details in envs.items():
        result.append({
            "name": name,
            "url": details.get(ENV_WXO_URL_OPT, "N/A"),  # "N/A" mirrors the CLI table
            "active": name == active_env,  # False for all entries when active_env is None
        })
    return result


def add_environment(
    name: str,
    url: str,
    activate: bool = False,
    type_: EnvironmentAuthType | None = None,
    iam_url: str | None = None,
    insecure: bool = False,
    verify: str | None = None,
) -> str:
    """
    Add a new watsonx Orchestrate environment.

    Equivalent to: orchestrate environment add --name <name> --url <url> [options]

    Args:
        name (str): Name of the environment to create.
        url (str): URL for the watsonx Orchestrate instance.
        activate (bool): Activate the environment immediately after creation. Defaults to False.
        type_ (EnvironmentAuthType | None): Auth type override ('iam' | 'cpd'). Defaults to None.
        iam_url (str | None): IAM token endpoint URL. Defaults to None.
        insecure (bool): Ignore SSL errors (CPD only). Mutually exclusive with verify. Defaults to False.
        verify (str | None): Path to SSL cert file (CPD only). Mutually exclusive with insecure. Defaults to None.

    Returns:
        str: A message confirming the environment was created.
    """
    # The CLI command layer performs this check and calls sys.exit(1). Since
    # MCP tools bypass that layer, the guard is reproduced here as ValueError
    # so the server process is not terminated.
    if insecure and verify:
        raise ValueError("Please choose either 'insecure' or 'verify' but not both.")

    # 'activate' → 'should_activate': MCP uses natural English; controller
    # uses its own internal convention. Renamed at the call site only.
    silent_call(
        fn=environment_controller.add,
        name=name,
        url=url,
        should_activate=activate,
        iam_url=iam_url,
        type=type_,
        insecure=insecure,
        verify=verify,
    )
    return f"Environment '{name}' has been created."


def remove_environment(name: str) -> str:
    """
    Remove a configured watsonx Orchestrate environment.

    Equivalent to: orchestrate environment remove --name <name>

    Args:
        name (str): Name of the environment to remove.

    Returns:
        str: A message confirming the environment was removed.
    """
    # Controller handles all edge cases (reserved names, non-existent names,
    # active-env prompt). The prompt receives no input under silent_call, so
    # removing the active environment is silently skipped.
    silent_call(fn=environment_controller.remove, name=name)
    return f"Environment '{name}' has been removed."


def activate_environment(
    name: str,
    api_key: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> str:
    """
    Activate a configured watsonx Orchestrate environment.

    Equivalent to: orchestrate environment activate <name> [options]

    Args:
        name (str): Name of the environment to activate.
        api_key (str | None): WXO or CPD API key. Omit for local dev. Defaults to None.
        username (str | None): CPD username. Defaults to None.
        password (str | None): CPD password. Mutually exclusive with api_key. Defaults to None.

    Returns:
        str: A message confirming the environment is now active.
    """
    # 'api_key' → 'apikey': Typer maps '--api-key' to 'apikey'; preserved in controller.
    # registry/test_package_version_override/skip_version_check omitted: hidden=True
    # developer flags for PyPI mirror selection, not environment management concerns.
    silent_call(
        fn=environment_controller.activate,
        name=name,
        apikey=api_key,
        username=username,
        password=password,
    )
    return f"Environment '{name}' is now active."


# Consumed by src/__init__.py to register these functions as FastMCP tools.
__tools__ = [list_environments, add_environment, remove_environment, activate_environment]
