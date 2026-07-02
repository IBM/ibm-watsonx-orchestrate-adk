"""
Temporary feature flags for in-progress features.

REMOVAL: When a flag is promoted to GA, delete its function here and remove
all call-sites that reference it (see the plan file for the full checklist).
"""
import os

from ibm_watsonx_orchestrate.utils.utils import parse_bool_safe

# ENV VAR: EXPERIMENTAL_ASYNC_TOOLKITS
# Controls whether async standalone tools are blocked at import time.
# Default: False — enforcement is off until the supporting backend work lands.
_ASYNC_ENFORCEMENT_ENV_VAR = "EXPERIMENTAL_ASYNC_TOOLKITS"


def is_async_enforcement_enabled() -> bool:
    """Return True if async-tool enforcement is active.

    Set ``EXPERIMENTAL_ASYNC_TOOLKITS=true`` to enable.
    """
    return parse_bool_safe(os.environ.get(_ASYNC_ENFORCEMENT_ENV_VAR), fallback=False)
