from __future__ import annotations

from ibm_watsonx_orchestrate_sdk.common.base_client import BaseAgenticClient
from ibm_watsonx_orchestrate_sdk.memory.models import (
    CreateMemoriesRequest,
    CreateMemoriesResponse,
    DeleteAllMemoriesResponse,
    ListMemoriesResponse,
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

    def list(self, *, limit: int, offset: int) -> ListMemoriesResponse:
        response = self._transport._get(
            "/memories/user",
            params={"limit": limit, "offset": offset},
        )
        return ListMemoriesResponse.model_validate(response)

    def search(self, request: SearchMemoriesRequest) -> SearchMemoriesResponse:
        response = self._transport._post("/memories/search", data=request.model_dump(exclude_none=True))
        return SearchMemoriesResponse.model_validate(response)

    def delete_all(self) -> DeleteAllMemoriesResponse:
        response = self._transport._delete("/memories/user")
        return DeleteAllMemoriesResponse.model_validate(response)

    def delete(self, memory_id: str) -> bool:
        self._transport._delete(f"/memories/{memory_id}")
        return True
