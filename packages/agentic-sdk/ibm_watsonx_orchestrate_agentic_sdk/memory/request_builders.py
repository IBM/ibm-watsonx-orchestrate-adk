from __future__ import annotations

from typing import Any, Dict, List, Optional

from ibm_watsonx_orchestrate_agentic_sdk.memory.models import (
    CreateMemoriesRequest,
    MemoryMessage,
    SearchMemoriesRequest,
)


class MemoryRequestBuilder:
    """Builds validated request payloads for memory operations."""

    @staticmethod
    def build_add_messages_request(
        *,
        messages: List[Dict[str, Any] | MemoryMessage],
        infer: Optional[bool] = None,
        memory_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        sensitivity_classification: Optional[str] = None,
        source_reference: Optional[str] = None,
    ) -> CreateMemoriesRequest:
        normalized_messages = [
            message if isinstance(message, MemoryMessage) else MemoryMessage.model_validate(message)
            for message in messages
        ]
        return CreateMemoriesRequest(
            messages=normalized_messages,
            infer=infer,
            memory_type=memory_type,
            metadata=metadata,
            agent_id=agent_id,
            run_id=run_id,
            sensitivity_classification=sensitivity_classification,
            source_reference=source_reference,
        )

    @staticmethod
    def build_search_request(
        *,
        query: str,
        limit: int = 10,
        memory_type: Optional[str] = None,
        expanded_query: Optional[str] = None,
        recall: Optional[bool] = None,
    ) -> SearchMemoriesRequest:
        return SearchMemoriesRequest(
            query=query,
            limit=limit,
            memory_type=memory_type,
            expanded_query=expanded_query,
            recall=recall,
        )
