import logging
from typing import Union

from ibm_watsonx_orchestrate.client.customer_care.utils import get_customer_care_config_client

logger = logging.getLogger(__name__)


def coerce_value(raw: str) -> Union[bool, int, float, str]:
    """Coerce a CLI string value to the appropriate Python type.

    Rules (evaluated in order):
    1. "true" / "false" (case-insensitive) → bool
    2. All digits with optional leading '-'  → int  (round-trip check; rejects "1e5", "1.0")
    3. Parseable by float() and contains '.' → float (e.g. "0.7", "1.0", "-0.5")
    4. Anything else                         → str
    """
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    try:
        int_val = int(raw)
        # Round-trip check rejects scientific notation ("1e5") and
        # decimal strings ("1.0") that Python's int() silently truncates.
        if str(int_val) == raw:
            return int_val
    except ValueError:
        pass
    try:
        float_val = float(raw)
        if "." in raw:
            return float_val
    except ValueError:
        pass
    return raw


def list_assist_config() -> None:
    client = get_customer_care_config_client()
    overrides = client.get()
    if overrides is None:
        logger.info("No configuration overrides are set.")
        print("No configuration overrides are set.")
        return
    # Print values only — property names are never displayed
    for value in overrides.values():
        print(value)


def set_assist_config(property_name: str, value: str) -> None:
    client = get_customer_care_config_client()
    coerced = coerce_value(value)
    client.set({property_name: coerced})
    logger.info("Configuration updated.")


def remove_assist_config(property_name: str) -> None:
    client = get_customer_care_config_client()
    client.remove(property_name)
    logger.info("Configuration property removed.")


def reset_assist_config() -> None:
    client = get_customer_care_config_client()
    client.reset()
    logger.info("All configuration overrides removed.")
