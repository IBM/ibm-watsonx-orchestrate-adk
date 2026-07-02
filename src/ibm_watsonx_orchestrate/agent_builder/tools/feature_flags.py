"""
Temporary feature flags for in-progress features.

REMOVAL: When a flag is promoted to GA, delete its function here and remove
all call-sites that reference it (see the plan file for the full checklist).
"""
import os

from ibm_watsonx_orchestrate.utils.utils import parse_bool_safe

# ENV VAR: WXO_ENABLE_ASYNC_ENFORCEMENT
# Controls whether async standalone tools are blocked at import time.
# Default: False — enforcement is off until the supporting backend work lands.
_ASYNC_ENFORCEMENT_ENV_VAR = "WXO_ENABLE_ASYNC_ENFORCEMENT"


def is_async_enforcement_enabled() -> bool:
    """Return True if async-tool enforcement is active.

    Set ``WXO_ENABLE_ASYNC_ENFORCEMENT=true`` to enable.
    """
    return parse_bool_safe(os.environ.get(_ASYNC_ENFORCEMENT_ENV_VAR), fallback=False)
