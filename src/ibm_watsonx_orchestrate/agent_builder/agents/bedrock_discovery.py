import logging
from typing import Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

_BEDROCK_AGENT_ENDPOINT = "https://bedrock-agent.{region}.amazonaws.com"
_BEDROCK_AGENT_PATH = "/agents/"
_BEDROCK_RUNTIME_ENDPOINT = "https://bedrock-agent-runtime.{region}.amazonaws.com"
_NAME_MAX_LEN = 64


class BedrockDiscoveryService:
    """Discover AWS Bedrock agents via the Bedrock Agent Management API and register them to WXO."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WatsonX-Orchestrate-Bedrock-Discovery/1.0",
            "Accept": "application/json",
        })

    # ------------------------------------------------------------------
    # Auth — SigV4 signing via botocore
    # ------------------------------------------------------------------

    def _sign_request(
        self,
        method: str,
        url: str,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        session_token: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> requests.PreparedRequest:
        """Build a SigV4-signed PreparedRequest for the given URL.

        Args:
            method: HTTP method string (e.g. ``"GET"``).
            url: Full URL to sign.
            region: AWS region (e.g. ``"us-east-1"``).
            access_key_id: AWS access key ID.
            secret_access_key: AWS secret access key.
            session_token: Optional STS session token.
            params: Optional query-string parameters dict.

        Returns:
            A :class:`requests.PreparedRequest` with ``Authorization``,
            ``x-amz-date``, and (when present) ``x-amz-security-token`` headers set.
        """
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            from botocore.credentials import Credentials
        except ImportError:
            raise ImportError(
                "The 'botocore' package is required for AWS Bedrock agent discovery. "
                "Install it with: pip install 'ibm-watsonx-orchestrate[aws]'"
            )

        credentials = Credentials(
            access_key=access_key_id,
            secret_key=secret_access_key,
            token=session_token,
        )
        # Build the full URL with query string BEFORE signing so that SigV4
        # covers the query parameters in the canonical request.  botocore's
        # AWSRequest does not embed params into its .url, so passing them
        # separately would sign over the base URL while sending the full URL,
        # causing a SignatureDoesNotMatch 403 on every paginated call.
        signed_url = url + "?" + urlencode(params) if params else url
        aws_request = AWSRequest(method=method, url=signed_url)
        SigV4Auth(credentials, "bedrock-agent", region).add_auth(aws_request)

        prepared = requests.Request(
            method=method,
            url=aws_request.url,   # already contains the query string
            headers=dict(aws_request.headers),
            # do NOT pass params here — they are already encoded in the URL
        ).prepare()
        return prepared

    # ------------------------------------------------------------------
    # Agent listing
    # ------------------------------------------------------------------

    def _list_agents(
        self,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        session_token: Optional[str] = None,
    ) -> list[dict]:
        """Call the Bedrock ListAgents API, following pagination.

        Args:
            region: AWS region (e.g. ``"us-east-1"``).
            access_key_id: AWS access key ID.
            secret_access_key: AWS secret access key.
            session_token: Optional STS session token.

        Returns:
            List of raw ``agentSummary`` dicts from the API.

        Raises:
            requests.HTTPError: On any non-2xx response (403, 404, etc.).
        """
        base_url = _BEDROCK_AGENT_ENDPOINT.format(region=region)
        url = base_url + _BEDROCK_AGENT_PATH

        agents: list[dict] = []
        next_token: Optional[str] = None

        while True:
            params: dict = {}
            if next_token:
                params["nextToken"] = next_token

            prepared = self._sign_request(
                method="GET",
                url=url,
                region=region,
                access_key_id=access_key_id,
                secret_access_key=secret_access_key,
                session_token=session_token,
                params=params,
            )
            response = self.session.send(prepared, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            agents.extend(data.get("agentSummaries", []))
            next_token = data.get("nextToken")
            if not next_token:
                break

        return agents

    def list_agents(
        self,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        session_token: Optional[str] = None,
    ) -> list[dict]:
        """Authenticate and list all Bedrock agents in the given region."""
        return self._list_agents(
            region=region,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            session_token=session_token,
        )

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    @staticmethod
    def convert_to_wxo_external_agent_dict(agent: dict, region: str) -> dict:
        """Convert a raw Bedrock agentSummary dict to a WXO ExternalAgentSpec-compatible dict.

        Args:
            agent: Raw agentSummary dict from the Bedrock ListAgents API.
            region: AWS region — used to construct the runtime resource URL.

        Returns:
            Dict suitable for ``ExternalAgent.model_validate()``.
        """
        agent_name: str = agent.get("agentName", "")
        sanitized_name = (
            agent_name.lower()
            .replace(" ", "_")
            .replace("-", "_")
        )[:_NAME_MAX_LEN]

        if not sanitized_name or not sanitized_name.strip("_"):
            agent_id = agent.get("agentId", "unknown")
            sanitized_name = f"bedrock_agent_{agent_id.lower()}"[:_NAME_MAX_LEN]

        description = (
            agent.get("description")
            or f"AWS Bedrock agent: {agent_name}"
        )

        agent_id = agent.get("agentId", "")
        # Use a stable placeholder alias path; the runtime adapter will resolve the live alias.
        api_url = (
            f"{_BEDROCK_RUNTIME_ENDPOINT.format(region=region)}"
            f"/agents/{agent_id}/agentAliases/TSTALIASID/"
        )

        return {
            "spec_version": "v1",
            "kind": "external",
            "name": sanitized_name,
            "title": agent_name,
            "description": description,
            "provider": "bedrock_agent",
            "api_url": api_url,
            "auth_scheme": "NONE",
            "auth_config": {},
        }

    def discover_and_convert(
        self,
        raw_agents: list[dict],
        agents: Optional[list[str]],
        region: str,
    ) -> list[dict]:
        """Filter raw agents by agent name and convert to WXO dicts.

        Args:
            raw_agents: Agents returned by :meth:`list_agents`.
            agents: List of agent names to keep (case-insensitive). ``None`` = all.
            region: AWS region, forwarded to :meth:`convert_to_wxo_external_agent_dict`.

        Returns:
            List of WXO-compatible agent dicts.
        """
        if agents is not None:
            filter_set = {a.lower() for a in agents}
            matched = [
                a for a in raw_agents
                if a.get("agentName", "").lower() in filter_set
            ]
            missing = filter_set - {a.get("agentName", "").lower() for a in matched}
            for name in missing:
                logger.warning(
                    "No Bedrock agent found with agentName matching '%s'", name
                )
            raw_agents = matched

        return [
            self.convert_to_wxo_external_agent_dict(a, region)
            for a in raw_agents
        ]

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self) -> "BedrockDiscoveryService":
        return self

    def __exit__(self, exc_type: type, exc_val: BaseException, exc_tb: object) -> None:
        self.close()
