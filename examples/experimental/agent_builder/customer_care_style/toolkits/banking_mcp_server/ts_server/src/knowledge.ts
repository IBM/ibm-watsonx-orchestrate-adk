/**
 * Knowledge Tools Module
 *
 * Contains tool definitions for knowledge search operations
 */

import { z } from 'zod';
import * as logger from './logger';
import { KnowledgeService, OpenSearchConnection } from './knowledgeService';

/**
 * Get OpenSearch configuration from environment variables or config
 * In production, this would be loaded from environment variables or a config service
 */
function getOpenSearchConfig(): OpenSearchConnection {
  // TODO: Load from environment variables or configuration service
  // For now, return a placeholder configuration
  return {
    url: process.env.OPENSEARCH_ENDPOINT || "https://localhost",
    port: process.env.OPENSEARCH_PORT || "9200",
    index: process.env.INDEX_NAME || 'knowledge_vector_index',
    credentials: {
      username: process.env.OPENSEARCH_USERNAME || "admin",
      password: process.env.OPENSEARCH_PASSWORD
    },
    field_mapping: {
      title: process.env.OPENSEARCH_FIELD_TITLE || 'title',
      body: process.env.OPENSEARCH_FIELD_BODY || 'passage_text',
      url: process.env.OPENSEARCH_FIELD_URL || 'url',
    }
  };
}

/**
 * Search knowledge base tool definition
 */
export const searchKnowledgeTool = {
  name: 'search_knowledge_base',
  config: {
    title: 'Search Knowledge Base',
    description:
      process.env.SEARCH_TOOL_DESCRIPTION || 'Search banking FAQs covering checking/savings accounts and mortgage/home loan products, including rates, fees, requirements, and policies.',
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
  handler: async (
    {
      query,
    }: {
      query: string;
    },
    extra: any,
  ) => {
    try {
      logger.info(`[KNOWLEDGE] Searching for "${query}"`);

      const config = getOpenSearchConfig();
      const searchResult = await KnowledgeService.searchKnowledge(query, config);

      // Format results for display
      const resultsText = JSON.stringify(searchResult.results)

      logger.info(`[KNOWLEDGE] Found ${searchResult.totalResults} result(s) in ${searchResult.searchTime.toFixed(3)} seconds`);

      return {
        content: [
          {
            type: 'text',
            text: `Knowledge Search Results\n\nQuery: "${searchResult.query}"\nFound ${searchResult.totalResults} result(s) in ${searchResult.searchTime.toFixed(3)} seconds\n\n${resultsText}`
          },
        ],
        structuredContent: searchResult,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      logger.error(`Error searching knowledge: ${errorMessage}`)

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
  },
};

/**
 * Get all knowledge tools
 */
export const knowledgeTools = [searchKnowledgeTool];