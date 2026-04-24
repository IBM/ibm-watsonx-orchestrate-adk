from __future__ import annotations

from typing import Any, Dict, List, Optional

from ibm_watsonx_orchestrate_sdk.common.base_client import BaseAgenticClient
from ibm_watsonx_orchestrate_sdk.common.session import AgenticSession
from ibm_watsonx_orchestrate_sdk.memory.models import (
    CreateMemoriesResponse,
    DeleteAllMemoriesResponse,
    ListMemoriesResponse,
    MemoryMessage,
    SearchMemoriesResponse,
)
from ibm_watsonx_orchestrate_sdk.memory.request_builders import MemoryRequestBuilder
from ibm_watsonx_orchestrate_sdk.memory.request_propagator import MemoryRequestPropagator


class MemoryClient:
    """Facade for the managed memory APIs exposed by wxo-server."""

    def __init__(self, session: AgenticSession):
        self._session = session
        self._transport = BaseAgenticClient(session)
        self._propagator = MemoryRequestPropagator(self._transport)

    def add_messages(
        self,
        *,
        messages: List[Dict[str, Any] | MemoryMessage],
        infer: Optional[bool] = None,
        memory_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        sensitivity_classification: Optional[str] = None,
        source_reference: Optional[str] = None,
    ) -> CreateMemoriesResponse:
        request = MemoryRequestBuilder.build_add_messages_request(
            messages=messages,
            infer=infer,
            memory_type=memory_type,
            metadata=metadata,
            agent_id=agent_id,
            run_id=run_id or (self._session.identity.run_id if self._session.identity else None),
            sensitivity_classification=sensitivity_classification,
            source_reference=source_reference,
        )
        return self._propagator.add_messages(request)

    def search(
        self,
        *,
        query: str,
        limit: int = 10,
        memory_type: Optional[str] = None,
        expanded_query: Optional[str] = None,
        recall: Optional[bool] = None,
    ) -> SearchMemoriesResponse:
        request = MemoryRequestBuilder.build_search_request(
            query=query,
            limit=limit,
            memory_type=memory_type,
            expanded_query=expanded_query,
            recall=recall,
        )
        return self._propagator.search(request)

    def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> ListMemoriesResponse:
        return self._propagator.list(limit=limit, offset=offset)

    def delete_all(self) -> DeleteAllMemoriesResponse:
        return self._propagator.delete_all()

    def delete(self, *, memory_id: str) -> bool:
        return self._propagator.delete(memory_id)

    # Compatibility helper for the previous placeholder API.
    def retrieve(self, query: str, limit: int = 10) -> SearchMemoriesResponse:
        return self.search(query=query, limit=limit)
