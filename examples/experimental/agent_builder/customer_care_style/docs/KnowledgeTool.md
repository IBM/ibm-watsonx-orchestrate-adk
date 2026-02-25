# Knowledge Tool

## Overview

The Knowledge Tool provides semantic search capabilities over a knowledge base using OpenSearch. It enables the AI assistant to search and retrieve relevant information from indexed documents to answer user questions with accurate, contextual information.

This tool is ideal for:
- Searching product documentation and FAQs
- Finding relevant policy information
- Retrieving troubleshooting guides
- Accessing company knowledge bases
- Providing accurate, source-backed responses

## Problems This Pattern Solves

### **Grounding AI Responses in Factual Information**

Without a knowledge tool, AI assistants would rely solely on their training data, which can lead to:
- Outdated or incorrect information
- Hallucinated responses
- Inability to access company-specific knowledge
- Lack of source attribution

The Knowledge Tool solves these issues by enabling real-time search of up-to-date, authoritative documents, ensuring responses are grounded in factual, verifiable information.

### **Semantic Search Over Large Document Collections**

The pattern enables:
- Natural language queries that understand user intent
- Vector-based semantic search for better relevance
- Fast retrieval from large document collections
- Configurable field mappings for different document structures

## Implementation

### Basic Example

Here's the core knowledge search tool implementation:

```typescript
export const searchKnowledgeTool = {
  name: 'search_knowledge_base',
  config: {
    title: 'Search Knowledge Base',
    description:
      process.env.SEARCH_TOOL_DESCRIPTION || 'Search the knowledge base for relevant information based on a query',
    inputSchema: {
      query: z
        .string()
        .min(1)
        .describe('Search query to find relevant knowledge'),
    },
    outputSchema: {
      query: z.string(),
      results: z.array(
        z.object({
          title: z.string(),
          body: z.string(),
          url: z.string().optional(),
          id: z.string().optional(),
          score: z.number().optional(),
        }),
      ),
      totalResults: z.number(),
      searchTime: z.number(),
    },
  },
  handler: async ({ query }: { query: string }, extra: any) => {
    const config = getOpenSearchConfig();
    const searchResult = await KnowledgeService.searchKnowledge(query, config);

    // Format results for display
    const resultsText = searchResult.results
      .map(
        (result, index) =>
          `${index + 1}. **${result.title}**\n\n${result.body}\n${result.url ? `\nURL: ${result.url}` : ''}`,
      )
      .join('\n---\n\n');

    return {
      content: [
        {
          type: 'text',
          text: `Knowledge Search Results\n\nQuery: "${searchResult.query}"\nFound ${searchResult.totalResults} result(s)\n\n${resultsText}`
        },
      ],
      structuredContent: searchResult,
    };
  },
};
```

**Key aspects:**

1. **Simple Input**: Takes a natural language query string
2. **Structured Output**: Returns both formatted text and structured data
3. **Error Handling**: Gracefully handles search failures
4. **Performance Metrics**: Includes search time and result count

### Full Working Example

For a complete implementation, see:

**TypeScript:**
- [`ts_server/src/knowledge.ts`](../toolkits/banking_mcp_server/ts_server/src/knowledge.ts) - Tool definition and configuration
- [`ts_server/src/knowledgeService.ts`](../toolkits/banking_mcp_server/ts_server/src/knowledgeService.ts) - OpenSearch integration and business logic

**Python:**
- [`py_server/src/knowledge.py`](../toolkits/banking_mcp_server/py_server/src/knowledge.py) - Tool definition and configuration
- [`py_server/src/knowledge_service.py`](../toolkits/banking_mcp_server/py_server/src/knowledge_service.py) - OpenSearch integration and business logic

### Configuration

The Knowledge Tool is configured via environment variables, making it easy to customize for different OpenSearch instances. The default values of these variables are configured to support the OpenSearch instance setup with the `docker compose` by following the instructions in [Knowledge.md](./Knowledge.md)

#### Environment Variables

```bash
# OpenSearch connection
OPENSEARCH_PASSWORD=your_password  # Required - tool only loads if set

# Optional - defaults provided
OPENSEARCH_ENDPOINT=https://localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USERNAME=admin
INDEX_NAME=knowledge_vector_index
```

#### Field Mapping Configuration

Customize field mappings to match your document structure:

```bash
# Map to your document fields
OPENSEARCH_FIELD_TITLE=title
OPENSEARCH_FIELD_BODY=passage_text
OPENSEARCH_FIELD_URL=url
```

#### Custom Query Configuration

For advanced use cases, you can provide a custom OpenSearch query body:

```bash
OPENSEARCH_QUERY_BODY='{"query":{"neural":{"passage_embedding":{"query_text":"$QUERY","k":10}}}}'
```

Placeholders available:
- `$QUERY` - Replaced with the user's search query
- `$BODY_FIELD` - Replaced with the body field name
- `$TITLE_FIELD` - Replaced with the title field name

### Conditional Tool Registration

The Knowledge Tool is only registered when `OPENSEARCH_PASSWORD` is set, allowing for flexible deployment:

**TypeScript Example** (from [`ts_server/src/index.ts`](../toolkits/banking_mcp_server/ts_server/src/index.ts)):
```typescript
if (process.env.OPENSEARCH_PASSWORD) {
  // Register knowledge tool (available at all times)
  registerToolsDirect(server, knowledgeTools);
}
```

**Python Example** (from [`py_server/src/server.py`](../toolkits/banking_mcp_server/py_server/src/server.py)):
```python
if os.getenv('OPENSEARCH_PASSWORD'):
    # Register knowledge tool (available at all times)
    register_tools_direct(server, knowledge_tools)
```

This pattern enables:
- Development without requiring OpenSearch setup
- Production deployment with full knowledge search
- Easy feature toggling via environment configuration

### How It Works

1. **User Query**: User asks a question that requires knowledge base information
2. **Model Decision**: AI model decides to use the search tool with an appropriate query
3. **Semantic Search**: Tool performs vector-based semantic search in OpenSearch
4. **Result Processing**: Results are formatted with titles, content, and optional URLs
5. **Response**: Model uses retrieved information to formulate an accurate response

## OpenSearch Integration

### Vector Search

The Knowledge Tool uses OpenSearch's neural search capabilities for semantic understanding:

```json
{
  "query": {
    "neural": {
      "passage_embedding": {
        "query_text": "user's question",
        "k": 10
      }
    }
  }
}
```

This enables:
- Understanding query intent beyond keyword matching
- Finding semantically similar content
- Better relevance ranking

### Document Structure

Expected document structure in OpenSearch:

```json
{
  "title": "Document Title",
  "passage_text": "Document content...",
  "url": "https://example.com/doc",
  "passage_embedding": [0.1, 0.2, ...]
}
```

Field names are configurable via environment variables.

## Error Handling

The tool includes comprehensive error handling:

```typescript
try {
  const searchResult = await KnowledgeService.searchKnowledge(query, config);
  // ... return results
} catch (error) {
  const errorMessage = error instanceof Error ? error.message : 'Unknown error';
  return {
    content: [
      {
        type: 'text',
        text: `Error searching knowledge: ${errorMessage}`,
      },
    ],
    isError: true,
  };
}
```

Common error scenarios:
- OpenSearch connection failures
- Invalid field mappings
- Missing required fields in documents
- Authentication errors


## See Also

- [Local Knowledge Setup Documentation](./Knowledge.md)
- [OpenSearch Documentation](https://opensearch.org/docs/latest/)