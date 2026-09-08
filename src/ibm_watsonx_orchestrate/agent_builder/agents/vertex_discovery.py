import logging
import time
from typing import Optional

import jwt
import requests

logger = logging.getLogger(__name__)

_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_TOKEN_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"
_GOOGLE_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
_VERTEX_API_BASE = "https://{location}-aiplatform.googleapis.com"
_VERTEX_AGENTS_PATH = "/v1beta1/projects/{project_id}/locations/{location}/agents"
_NAME_MAX_LEN = 64


class VertexDiscoveryService:
    """Discover Google Vertex AI Agent Engine agents and convert them to WXO external agent specs."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WatsonX-Orchestrate-Vertex-Discovery/1.0",
            "Accept": "application/json",
        })

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _get_token(self, service_account_json: dict) -> str:
        """Exchange a service account JSON for a Google OAuth2 access token via RS256 JWT.

        Args:
            service_account_json: Parsed service account JSON dict.

        Returns:
            OAuth2 access token string.

        Raises:
            ValueError: If required fields are missing from the service account JSON.
            requests.HTTPError: If the token endpoint returns a non-2xx response.
        """
        try:
            private_key = service_account_json["private_key"]
            client_email = service_account_json["client_email"]
        except KeyError as exc:
            raise ValueError(
                f"service_account_json is missing required field: {exc}"
            ) from exc

        now = int(time.time())
        payload = {
            "iss": client_email,
            "sub": client_email,
            "aud": _GOOGLE_TOKEN_URL,
            "scope": _GOOGLE_SCOPE,
            "iat": now,
            "exp": now + 3600,
        }

        signed_jwt = jwt.encode(payload, private_key, algorithm="RS256")

        response = self.session.post(
            _GOOGLE_TOKEN_URL,
            data={
                "grant_type": _GOOGLE_TOKEN_GRANT_TYPE,
                "assertion": signed_jwt,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    # ------------------------------------------------------------------
    # Agent listing
    # ------------------------------------------------------------------

    def _list_agents(self, project_id: str, location: str, token: str) -> list[dict]:
        """Call the Vertex AI Agent Engine list API, following pagination.

        Args:
            project_id: GCP project ID.
            location: GCP region (e.g. ``us-central1``).
            token: OAuth2 Bearer token.

        Returns:
            List of raw agent dicts from the API.

        Raises:
            requests.HTTPError: On any non-2xx response (403, 404, etc.).
        """
        base_url = _VERTEX_API_BASE.format(location=location)
        path = _VERTEX_AGENTS_PATH.format(project_id=project_id, location=location)
        url = base_url + path

        headers = {"Authorization": f"Bearer {token}"}
        agents: list[dict] = []
        page_token: Optional[str] = None

        while True:
            params = {}
            if page_token:
                params["pageToken"] = page_token

            response = self.session.get(
                url,
                headers=headers,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            agents.extend(data.get("agents", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return agents

    def list_agents(
        self,
        project_id: str,
        location: str,
        service_account_json: dict,
    ) -> list[dict]:
        """Authenticate and list all Vertex AI agents for a project/location."""
        token = self._get_token(service_account_json)
        return self._list_agents(project_id, location, token)

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    @staticmethod
    def convert_to_wxo_external_agent_dict(agent: dict, location: str) -> dict:
        """Convert a raw Vertex AI agent dict to a WXO ExternalAgentSpec-compatible dict.

        Args:
            agent: Raw agent dict from the Vertex AI list API.
            location: GCP region — used to construct the resource URL.

        Returns:
            Dict suitable for ``ExternalAgent.model_validate()``.
        """
        display_name: str = agent.get("displayName", "")
        sanitized_name = (
            display_name.lower()
            .replace(" ", "_")
            .replace("-", "_")
        )[:_NAME_MAX_LEN]

        description = (
            agent.get("description")
            or f"Google Vertex AI agent: {display_name}"
        )

        resource_name = agent.get("name", "")
        api_url = (
            f"{_VERTEX_API_BASE.format(location=location)}/v1beta1/{resource_name}"
        )

        return {
            "spec_version": "v1",
            "kind": "external",
            "name": sanitized_name,
            "title": display_name,
            "description": description,
            "provider": "vertex_agent",
            "api_url": api_url,
            "auth_scheme": "NONE",
            "auth_config": {},
        }

    def discover_and_convert(
        self,
        raw_agents: list[dict],
        agents: Optional[list[str]],
        location: str,
    ) -> list[dict]:
        """Filter raw agents by display name and convert to WXO dicts.

        Args:
            raw_agents: Agents returned by :meth:`list_agents`.
            agents: List of display names to keep (case-insensitive).  ``None`` = all.
            location: GCP region, forwarded to :meth:`convert_to_wxo_external_agent_dict`.

        Returns:
            List of WXO-compatible agent dicts.
        """
        if agents is not None:
            filter_set = {a.lower() for a in agents}
            matched = [
                a for a in raw_agents
                if a.get("displayName", "").lower() in filter_set
            ]
            missing = filter_set - {a.get("displayName", "").lower() for a in matched}
            for name in missing:
                logger.warning(
                    "No Vertex AI agent found with displayName matching '%s'", name
                )
            raw_agents = matched

        return [
            self.convert_to_wxo_external_agent_dict(a, location)
            for a in raw_agents
        ]

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def close(self):
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
