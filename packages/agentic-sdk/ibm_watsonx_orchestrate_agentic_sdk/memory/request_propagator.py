from __future__ import annotations

from ibm_watsonx_orchestrate_agentic_sdk.common.base_client import BaseAgenticClient
from ibm_watsonx_orchestrate_agentic_sdk.memory.models import (
    CreateMemoriesRequest,
    CreateMemoriesResponse,
    SearchMemoriesRequest,
    SearchMemoriesResponse,
)


class MemoryRequestPropagator:
    """Propagates validated memory requests to the configured service boundary."""

    def __init__(self, transport: BaseAgenticClient):
        self._transport = transport

    def add_messages(self, request: CreateMemoriesRequest) -> CreateMemoriesResponse:
        response = self._transport._post("/memories", data=request.model_dump(exclude_none=True))
        return CreateMemoriesResponse.model_validate(response)

    def search(self, request: SearchMemoriesRequest) -> SearchMemoriesResponse:
        response = self._transport._post("/memories/search", data=request.model_dump(exclude_none=True))
        return SearchMemoriesResponse.model_validate(response)
