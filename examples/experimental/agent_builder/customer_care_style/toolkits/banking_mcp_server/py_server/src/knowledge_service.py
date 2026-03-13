"""
Knowledge Service - OpenSearch Implementation

Contains business logic for knowledge search operations using OpenSearch.
"""

import os
import json
from dataclasses import dataclass
from datetime import datetime
import httpx

from . import logger


@dataclass
class KnowledgeResult:
    """Single knowledge search result."""

    title: str
    body: str
    url: str | None = None
    id: str | None = None
    score: float | None = None


@dataclass
class KnowledgeSearchResult:
    """Knowledge search results."""

    query: str
    results: list[KnowledgeResult]
    total_results: int
    search_time: float


@dataclass
class OpenSearchCredentials:
    """OpenSearch authentication credentials."""

    username: str | None = None
    password: str | None = None


@dataclass
class FieldMapping:
    """OpenSearch field mapping."""

    title: str
    body: str
    url: str | None = None


@dataclass
class OpenSearchConnection:
    """OpenSearch connection configuration."""

    url: str
    port: str | None
    index: str
    credentials: OpenSearchCredentials
    field_mapping: FieldMapping


def get_opensearch_config() -> OpenSearchConnection:
    """
    Get OpenSearch configuration from environment variables.
    In production, this would be loaded from environment variables or a config service.
    """
    return OpenSearchConnection(
        url=os.getenv("OPENSEARCH_ENDPOINT", "https://localhost"),
        port=os.getenv("OPENSEARCH_PORT", "9200"),
        index=os.getenv("INDEX_NAME", "knowledge_vector_index"),
        credentials=OpenSearchCredentials(
            username=os.getenv("OPENSEARCH_USERNAME", "admin"),
            password=os.getenv("OPENSEARCH_PASSWORD"),
        ),
        field_mapping=FieldMapping(
            title=os.getenv("OPENSEARCH_FIELD_TITLE", "title"),
            body=os.getenv("OPENSEARCH_FIELD_BODY", "passage_text"),
            url=os.getenv("OPENSEARCH_FIELD_URL", "url"),
        ),
    )


class KnowledgeService:
    """Knowledge Service using OpenSearch."""

    @staticmethod
    async def search_knowledge(
        query: str,
        config: OpenSearchConnection,
    ) -> KnowledgeSearchResult:
        """
        Search knowledge base using OpenSearch.

        Args:
            query: Search query string
            config: OpenSearch connection configuration

        Returns:
            Search results with relevant articles
        """
        # Validate query
        if not query or not query.strip():
            raise ValueError("Search query is required")

        # Build auth header
        headers: dict[str, str] = {"Content-Type": "application/json"}

        if config.credentials.username and config.credentials.password:
            import base64

            credentials = base64.b64encode(
                f"{config.credentials.username}:{config.credentials.password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"

        # Build query body
        query_body_env = os.getenv("OPENSEARCH_QUERY_BODY")
        if query_body_env:
            query_body = json.loads(query_body_env)
        else:
            query_body = {
                "_source": {"excludes": ["passage_embedding"]},
                "query": {
                    "neural": {
                        "passage_embedding": {
                            "query_text": "$QUERY",
                            "k": 10,
                        }
                    }
                },
            }

        # Replace placeholders
        query_body_str = json.dumps(query_body)
        query_body_str = query_body_str.replace("$QUERY", query)
        query_body_str = query_body_str.replace("$BODY_FIELD", config.field_mapping.body)
        query_body_str = query_body_str.replace("$TITLE_FIELD", config.field_mapping.title)
        query_body = json.loads(query_body_str)

        # Build URL
        port_part = f":{config.port}" if config.port else ""
        url = f"{config.url}{port_part}/{config.index}/_search"

        # Make request
        start_time = datetime.now()

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                url,
                headers=headers,
                json=query_body,
            )

            if response.status_code != 200:
                raise ValueError(
                    f"OpenSearch request failed: {response.status_code} {response.text}"
                )

            response_data = response.json()

        elapsed_time = (datetime.now() - start_time).total_seconds()

        # Process results
        search_results: list[KnowledgeResult] = []
        hits = response_data.get("hits", {}).get("hits", [])

        for hit in hits:
            source = hit.get("_source", {})

            # Check if body field exists
            body_field = config.field_mapping.body
            if body_field not in source:
                highlight = hit.get("highlight", {})
                if body_field not in highlight:
                    raise ValueError(f"The Body field <{body_field}> cannot be found")

            search_results.append(
                KnowledgeResult(
                    title=source.get(config.field_mapping.title, ""),
                    body=source.get(body_field, ""),
                    url=source.get(config.field_mapping.url) if config.field_mapping.url else None,
                    id=str(hit.get("_id")),
                    score=hit.get("_score"),
                )
            )

        return KnowledgeSearchResult(
            query=query,
            results=search_results,
            total_results=len(search_results),
            search_time=elapsed_time,
        )
