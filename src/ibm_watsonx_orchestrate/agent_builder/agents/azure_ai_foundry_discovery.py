import logging
import re
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_AZURE_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
_AZURE_AI_SCOPE = "https://ai.azure.com/.default"
_AZURE_AI_FOUNDRY_AGENTS_PATH = "/api/projects/{project_name}/agents"
_AZURE_AI_FOUNDRY_API_VERSION = "2025-05-01"
_NAME_MAX_LEN = 64


class AzureAIFoundryDiscoveryService:
    """Discover Microsoft Azure AI Foundry agents and convert them to WXO external agent specs."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WatsonX-Orchestrate-AzureAIFoundry-Discovery/1.0",
            "Accept": "application/json",
        })

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _get_token(self, tenant_id: str, client_id: str, client_secret: str) -> str:
        """Exchange service principal credentials for a Microsoft Entra ID access token.

        Uses the client credentials (OAuth 2.0) flow to obtain a bearer token
        scoped to ``https://ai.azure.com/.default``.

        Args:
            tenant_id: Azure AD tenant ID.
            client_id: Service principal (application) client ID.
            client_secret: Service principal client secret.

        Returns:
            OAuth2 access token string.

        Raises:
            requests.HTTPError: If the token endpoint returns a non-2xx response.
        """
        token_url = _AZURE_TOKEN_URL.format(tenant_id=tenant_id)

        response = self.session.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": _AZURE_AI_SCOPE,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return str(response.json()["access_token"])

    # ------------------------------------------------------------------
    # Agent listing
    # ------------------------------------------------------------------

    def _list_agents(self, endpoint: str, project_name: str, token: str) -> list[dict]:
        """Call the Azure AI Foundry agent list API, following pagination.

        Args:
            endpoint: Azure AI Foundry account endpoint
                      (e.g. ``https://my-resource.services.ai.azure.com``).
            project_name: Azure AI Foundry project name.
            token: Bearer token obtained from :meth:`_get_token`.

        Returns:
            List of raw agent dicts from the API.

        Raises:
            requests.HTTPError: On any non-2xx response (401, 403, 404, etc.).
        """
        path = _AZURE_AI_FOUNDRY_AGENTS_PATH.format(project_name=project_name)
        url = endpoint.rstrip("/") + path

        headers = {"Authorization": f"Bearer {token}"}
        agents: list[dict] = []
        next_link: Optional[str] = url

        while next_link:
            params = {"api-version": _AZURE_AI_FOUNDRY_API_VERSION}
            response = self.session.get(
                next_link,
                headers=headers,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            agents.extend(data.get("value", []))
            next_link = data.get("nextLink")

        return agents

    def list_agents(
        self,
        endpoint: str,
        project_name: str,
        tenant_id: str,
        client_id: str,
        client_secret: str,
    ) -> list[dict]:
        """Authenticate and list all Azure AI Foundry agents for a project."""
        token = self._get_token(tenant_id, client_id, client_secret)
        return self._list_agents(endpoint, project_name, token)

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    @staticmethod
    def convert_to_wxo_external_agent_dict(agent: dict, endpoint: str, project_name: str) -> dict:
        """Convert a raw Azure AI Foundry agent dict to a WXO ExternalAgentSpec-compatible dict.

        Args:
            agent: Raw agent dict from the Azure AI Foundry list API.
            endpoint: Azure AI Foundry account endpoint — used to construct the resource URL.
            project_name: Azure AI Foundry project name — used to construct the resource URL.

        Returns:
            Dict suitable for ``ExternalAgent.model_validate()``.
        """
        display_name: str = agent.get("name", "")

        sanitized_name = (
            display_name.lower()
            .replace(" ", "_")
            .replace("-", "_")
        )
        sanitized_name = re.sub(r"[^a-z0-9_]", "_", sanitized_name)[:_NAME_MAX_LEN]

        if not sanitized_name or not sanitized_name.strip("_"):
            agent_id_part = agent.get("id", "unknown") or "unknown"
            sanitized_name = f"azure_agent_{agent_id_part.split('/')[-1]}"

        description = (
            agent.get("description")
            or f"Microsoft Azure AI Foundry agent: {display_name}"
        )

        raw_id = agent.get("id", "") or display_name
        agent_id = raw_id.split("/")[-1]
        api_url = (
            f"{endpoint.rstrip('/')}/api/projects/{project_name}/agents/{agent_id}"
        )

        return {
            "spec_version": "v1",
            "kind": "external",
            "name": sanitized_name,
            "title": display_name,
            "description": description,
            "provider": "azure_ai_foundry",
            "api_url": api_url,
            "auth_scheme": "NONE",
            "auth_config": {},
        }

    def discover_and_convert(
        self,
        raw_agents: list[dict],
        agents: Optional[list[str]],
        endpoint: str,
        project_name: str,
    ) -> list[dict]:
        """Filter raw agents by name and convert to WXO dicts.

        Args:
            raw_agents: Agents returned by :meth:`list_agents`.
            agents: List of agent names to keep (case-insensitive).  ``None`` = all.
            endpoint: Azure AI Foundry account endpoint, forwarded to
                      :meth:`convert_to_wxo_external_agent_dict`.
            project_name: Azure AI Foundry project name, forwarded to
                          :meth:`convert_to_wxo_external_agent_dict`.

        Returns:
            List of WXO-compatible agent dicts.
        """
        if agents is not None:
            filter_set = {a.lower() for a in agents}
            matched = [
                a for a in raw_agents
                if a.get("name", "").lower() in filter_set
            ]
            missing = filter_set - {a.get("name", "").lower() for a in matched}
            for name in missing:
                logger.warning(
                    "No Azure AI Foundry agent found with name matching '%s'", name
                )
            raw_agents = matched

        return [
            self.convert_to_wxo_external_agent_dict(a, endpoint, project_name)
            for a in raw_agents
        ]

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self) -> "AzureAIFoundryDiscoveryService":
        return self

    def __exit__(self, exc_type: type, exc_val: BaseException, exc_tb: object) -> None:
        self.close()
