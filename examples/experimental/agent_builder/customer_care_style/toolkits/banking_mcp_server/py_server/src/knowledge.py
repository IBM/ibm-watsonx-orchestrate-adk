"""
Knowledge Tools Module

Contains tool definitions for knowledge search operations.
Uses dict-based tool definitions to match the TypeScript implementation.
"""

import os
import json

from .knowledge_service import KnowledgeService, get_opensearch_config
from . import logger


async def search_knowledge_base_handler(args: dict, extra: dict) -> dict:
    """Search knowledge base tool handler."""
    query = args.get("query", "")

    try:
        logger.info(f'[KNOWLEDGE] Searching for "{query}"')

        config = get_opensearch_config()
        search_result = await KnowledgeService.search_knowledge(query, config)

        # Format results for display
        results_text = json.dumps(
            [
                {
                    "title": r.title,
                    "body": r.body,
                    "url": r.url,
                    "score": r.score,
                }
                for r in search_result.results
            ]
        )

        logger.info(
            f"[KNOWLEDGE] Found {search_result.total_results} result(s) "
            f"in {search_result.search_time:.3f} seconds"
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Knowledge Search Results\n\n"
                        f'Query: "{search_result.query}"\n'
                        f"Found {search_result.total_results} result(s) "
                        f"in {search_result.search_time:.3f} seconds\n\n"
                        f"{results_text}"
                    ),
                }
            ],
            "structuredContent": {
                "query": search_result.query,
                "results": [
                    {
                        "title": r.title,
                        "body": r.body,
                        "url": r.url,
                        "id": r.id,
                        "score": r.score,
                    }
                    for r in search_result.results
                ],
                "total_results": search_result.total_results,
                "search_time": search_result.search_time,
            },
        }
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error searching knowledge: {error_message}")

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error searching knowledge: {error_message}",
                }
            ],
            "isError": True,
        }


# Tool definitions in dict format (matching TypeScript structure)
search_knowledge_base_tool = {
    "name": "search_knowledge_base",
    "config": {
        "title": "Search Knowledge Base",
        "description": (
            os.getenv("SEARCH_TOOL_DESCRIPTION")
            or "Search banking FAQs covering checking/savings accounts and mortgage/home loan "
            "products, including rates, fees, requirements, and policies."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for the knowledge base",
                },
            },
            "required": ["query"],
        },
    },
    "handler": search_knowledge_base_handler,
}

# Export all knowledge tools
knowledge_tools = [search_knowledge_base_tool]
