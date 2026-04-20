from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


MEMORY_TYPE_ALIASES = {
    "conversation": "conversational",
    "fact": "conversational",
    "episodic": "conversational",
    "profile": "profile_fact",
    "identity": "profile_fact",
    "preferences": "preference",
    "task": "tool",
    "procedure": "tool",
    "derived_event": "outcome",
}

SUPPORTED_MEMORY_TYPES = (
    "conversational",
    "profile_fact",
    "preference",
    "tool",
    "outcome",
)


def _format_invalid_memory_type_error(raw_value: str) -> str:
    accepted_aliases = ", ".join(MEMORY_TYPE_ALIASES.keys())
    supported_values = ", ".join(SUPPORTED_MEMORY_TYPES)
    return (
        f"Invalid memory_type '{raw_value}'. Supported values: {supported_values}. "
        f"Accepted aliases: {accepted_aliases}."
    )


def normalize_memory_type(memory_type: Optional[str]) -> Optional[str]:
    if memory_type is None:
        return None
    raw_value = memory_type.strip()
    normalized = raw_value.lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        return None
    normalized = MEMORY_TYPE_ALIASES.get(normalized, normalized)
    if normalized not in SUPPORTED_MEMORY_TYPES:
        raise ValueError(_format_invalid_memory_type_error(raw_value))
    return normalized


class MemoryMessage(BaseModel):
    role: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)


class MemoryItem(BaseModel):
    mem0_id: str
    content: str
    memory_type: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CreateMemoriesRequest(BaseModel):
    messages: List[MemoryMessage] = Field(..., min_length=1)
    infer: Optional[bool] = None
    memory_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    sensitivity_classification: Optional[str] = None
    source_reference: Optional[str] = None

    @field_validator("memory_type")
    @classmethod
    def _normalize_memory_type(cls, value: Optional[str]) -> Optional[str]:
        return normalize_memory_type(value)


class CreateMemoriesResponse(BaseModel):
    memories: List[MemoryItem]
    count: int


class ListMemoriesResponse(BaseModel):
    memories: List[MemoryItem]
    total: int
    limit: int
    offset: int


class DeleteAllMemoriesResponse(BaseModel):
    deleted_count: int


class SearchMemoriesRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=100)
    memory_type: Optional[str] = None
    expanded_query: Optional[str] = None
    recall: Optional[bool] = None

    @field_validator("memory_type")
    @classmethod
    def _normalize_memory_type(cls, value: Optional[str]) -> Optional[str]:
        return normalize_memory_type(value)


class SearchMemoryItem(MemoryItem):
    score: Optional[float] = None


class SearchMemoriesResponse(BaseModel):
    results: List[SearchMemoryItem]
    total: int
    query: str
