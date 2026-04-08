from __future__ import annotations

from ibm_watsonx_orchestrate_clients.common.base_client import BaseAPIClient

from ibm_watsonx_orchestrate_agentic_sdk.common.session import AgenticSession


class BaseAgenticClient(BaseAPIClient):
    """Base transport for agentic SDK services."""

    def __init__(self, session: AgenticSession):
        self.session = session
        super().__init__(
            base_url=session.base_url,
            api_key=session.access_token,
            verify=session.verify,
            authenticator=session.authenticator,
        )
