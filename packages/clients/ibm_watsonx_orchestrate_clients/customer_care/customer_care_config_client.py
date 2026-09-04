import logging
from typing import Optional

from ibm_watsonx_orchestrate_clients.common.base_client import BaseWXOClient, ClientAPIException

logger = logging.getLogger(__name__)

_CONFIG_PATH = "/application_config/agent_assist_config"
_CREATE_PATH = "/application_config"
_CONFIG_PROPERTY_NAME = "Agent Assist Configuration"


class CustomerCareConfigClient(BaseWXOClient):
    """HTTP client for the agent-assist configuration overrides.

    Wraps GET / POST / PATCH / DELETE on
    /v1/orchestrate/application_config/agent_assist_config.

    The server's PATCH replaces configuration_value wholesale, so all
    mutating methods perform a read-merge-write cycle to avoid losing
    settings the caller did not intend to touch.
    """

    def get(self) -> Optional[dict]:
        """Return the current overrides dict, or None if no row exists."""
        try:
            response = self._get(_CONFIG_PATH)
            return response.get("configuration_value")
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return None
            raise

    def set(self, overrides: dict) -> None:
        """Persist *overrides*.

        If no row exists yet a POST is used; otherwise PATCH is used with the
        full merged configuration because the server replaces configuration_value
        wholesale.
        """
        existing = self.get()
        if existing is None:
            self._post(
                _CREATE_PATH,
                data={
                    "configuration_property_key": "agent_assist_config",
                    "configuration_property_name": _CONFIG_PROPERTY_NAME,
                    "configuration_value": overrides,
                },
            )
        else:
            merged = {**existing, **overrides}
            self._patch(
                _CONFIG_PATH,
                data={
                    "configuration_property_name": _CONFIG_PROPERTY_NAME,
                    "configuration_value": merged,
                },
            )

    def remove(self, property_name: str) -> None:
        """Remove a single property from the stored overrides.

        If removing the property leaves the dict empty the entire row is
        deleted (clean state). No-op if the property is not present or no
        row exists.

        Performs a GET then PATCH/DELETE (read-merge-write; same pattern as set()).
        """
        existing = self.get()
        if existing is None or property_name not in existing:
            return
        updated = {k: v for k, v in existing.items() if k != property_name}
        if updated:
            self._patch(
                _CONFIG_PATH,
                data={
                    "configuration_property_name": _CONFIG_PROPERTY_NAME,
                    "configuration_value": updated,
                },
            )
        else:
            self._delete(_CONFIG_PATH)

    def reset(self) -> None:
        """Delete all stored overrides. Silently ignores 404."""
        try:
            self._delete(_CONFIG_PATH)
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return
            raise

    # These abstract methods from BaseAPIClient are not applicable to this client.
    def create(self, *args, **kwargs):
        raise NotImplementedError

    def delete(self, *args, **kwargs):
        raise NotImplementedError

    def update(self, *args, **kwargs):
        raise NotImplementedError
