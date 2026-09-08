"""Framework-agnostic client for the prompt optimization registry.

Talks to the ``/agentops-v3/prompt/`` endpoints. Handles:
- SDK connection handshake
- Active prompt fetching (production traffic)
- Candidate prompt fetching (during optimization runs)
- Prompt acknowledgement
"""

from __future__ import annotations

import logging

from ibm_watsonx_orchestrate_sdk.common.base_client import BaseAgenticClient
from ibm_watsonx_orchestrate_sdk.common.session import AgenticSession

logger = logging.getLogger(__name__)


# local service don't have the agentops-v3 prefix.
# the proxy maps v1/agentops-v3/prompt to v1/prompt
_CLUSTER_BASE = "/v1/agentops-v3/prompt"
_LOCAL_BASE = "/v1/prompt"



def _is_local_url(url: str) -> bool:
    from urllib.parse import urlparse
    host = urlparse(url).hostname or ""
    return host in ("localhost", "127.0.0.1", "0.0.0.0") or host.startswith("192.168.")


class PromptClient(BaseAgenticClient):

    def create(self, *args, **kwargs):
        raise NotImplementedError("PromptClient does not support generic create")

    def delete(self, *args, **kwargs):
        raise NotImplementedError("PromptClient does not support generic delete")

    def update(self, *args, **kwargs):
        raise NotImplementedError("PromptClient does not support generic update")

    def get(self, *args, **kwargs):
        raise NotImplementedError("PromptClient does not support generic get")

    def __init__(self, session: AgenticSession, agent_id: str):
        super().__init__(session)
        idx = self.base_url.find("/api/v1")
        if idx == -1:
            idx = self.base_url.find("/v1")
        if idx != -1:
            self.base_url = self.base_url[:idx]
        self._base = _LOCAL_BASE if _is_local_url(self.base_url) else _CLUSTER_BASE
        self._agent_id = agent_id
        # Server reassembles instructions + guidelines into a single string,
        # so this already contains the full prompt.
        self._active_prompt: str | None = None
        self._candidate_cache: dict[str, str] = {}
        self._connected = False

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def active_prompt(self) -> str | None:
        return self._active_prompt

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        try:
            resp = self._post(
                f"{self._base}/connect",
                data={"agent_id": self._agent_id},
            )
            self._connected = resp.get("status") == "connected"
        except Exception:
            logger.debug("Prompt connect failed for %s", self._agent_id, exc_info=True)

    def load_active_prompt(self) -> str | None:
        try:
            resp = self._get(f"{self._base}/agents/{self._agent_id}/active-prompt")
            # "instructions" includes the full reassembled prompt (instructions + guidelines)
            prompt = (resp.get("instructions") or "").strip()
            if prompt:
                self._active_prompt = prompt
                return prompt
        except Exception:
            logger.info("No active prompt for %s", self._agent_id, exc_info=True)
        return None

    def fetch_candidate(self, run_id: str) -> str | None:
        cached = self._candidate_cache.get(run_id)
        if cached is not None:
            return cached
        try:
            resp = self._get(f"{self._base}/optimization/runs/{run_id}/candidate-prompt")
            instructions = resp.get("instructions")
            if instructions:
                self._candidate_cache[run_id] = instructions
                self._ack(run_id, resp["version"])
                return instructions
        except Exception:
            logger.debug("Failed to fetch candidate for run %s", run_id, exc_info=True)
        return None

    def _ack(self, run_id: str, version: int) -> None:
        try:
            self._post(
                f"{self._base}/optimization/runs/{run_id}/prompt-ack",
                data={"version": version},
            )
        except Exception:
            logger.debug("Ack failed for run %s", run_id, exc_info=True)
