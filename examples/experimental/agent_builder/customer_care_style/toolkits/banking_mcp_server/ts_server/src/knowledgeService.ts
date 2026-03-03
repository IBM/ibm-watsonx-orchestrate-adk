/**
 * Knowledge Service - OpenSearch Implementation
 *
 * Contains business logic for knowledge search operations using OpenSearch
 */

import { Agent } from 'undici';

export interface KnowledgeSearchResult {
  query: string;
  results: KnowledgeResult[];
  totalResults: number;
  searchTime: number;
}

export interface KnowledgeResult {
  title: string;
  body: string;
  url?: string;
  id?: string;
  score?: number;
  highlight?: {
    body?: string[];
  };
}

export interface OpenSearchCredentials {
  username?: string;
  password?: string;
}

export interface FieldMapping {
  title: string;
  body: string;
  url?: string;
}

export interface OpenSearchConnection {
  url: string;
  port?: string;
  index: string;
  credentials: OpenSearchCredentials;
  field_mapping: FieldMapping;
}

interface OpenSearchResponse {
  hits?: {
    hits?: Array<{
      _source?: Record<string, any>;
      highlight?: Record<string, string[]>;
      _score?: number;
      _id?: string;
    }>;
    total?: {
      value: number;
    };
  };
  took?: number;
}

/**
 * Knowledge Service
 */
export class KnowledgeService {
  /**
   * Search knowledge base using OpenSearch
   *
   * @param query - Search query string
   * @param config - OpenSearch connection configuration
   * @returns Search results with relevant articles
   */
  static async searchKnowledge(
    query: string,
    config: OpenSearchConnection,
  ): Promise<KnowledgeSearchResult> {
    // Validate query
    if (!query || query.trim().length === 0) {
      throw new Error('Search query is required');
    }

    const opensearchCreds = config.credentials;
    let authHeader: string | undefined;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Set up authentication
    const credentials = Buffer.from(
        `${opensearchCreds.username}:${opensearchCreds.password}`,
      ).toString('base64');
    authHeader = `Basic ${credentials}`;

    if (authHeader) {
      headers['Authorization'] = authHeader;
    }

    // Build query body
    const osPort = config.port !== undefined ? config.port : '';
    let osQueryBody = process.env.OPENSEARCH_QUERY_BODY ? 
      JSON.parse(process.env.OPENSEARCH_QUERY_BODY) :
      {
        _source: {
          excludes: [
            "passage_embedding"
          ]
        },
        query: {
          neural: {
            passage_embedding: {
              query_text: '$QUERY',
              k: 10
            }
          }
        }
      };

    // Replace placeholders
    let queryBodyStr = JSON.stringify(osQueryBody)
      .replace(/\$QUERY/g, query)
      .replace(/\$BODY_FIELD/g, config.field_mapping.body)
      .replace(/\$TITLE_FIELD/g, config.field_mapping.title);

    const queryBody = JSON.parse(queryBodyStr);

    // Build URL
    const portPart = osPort ? `:${osPort}` : '';
    const url = `${config.url}${portPart}/${config.index}/_search`;

    // Make request
    const startTime = Date.now();
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(queryBody),
      // @ts-ignore
      dispatcher: new Agent({
        connect: {
          rejectUnauthorized: false,
        },
      })
    });

    if (!response.ok) {
      throw new Error(
        `OpenSearch request failed: ${response.status} ${response.statusText}`,
      );
    }

    const responseData = (await response.json()) as OpenSearchResponse;
    const elapsedTime = (Date.now() - startTime) / 1000; // Convert to seconds

    // Process results
    const searchResults: KnowledgeResult[] = [];
    const hits = responseData.hits?.hits || [];

    for (const hit of hits) {
      const source = hit._source || {};
      
      // Check if body field exists
      if (
        !source[config.field_mapping.body] &&
        (!hit.highlight || !hit.highlight[config.field_mapping.body])
      ) {
        throw new Error(
          `The Body field <${config.field_mapping.body}> cannot be found`,
        );
      }

      // Extract highlight if available
      let highlight: { body?: string[] } | undefined;
      if (hit.highlight && hit.highlight[config.field_mapping.body]) {
        highlight = {
          body: hit.highlight[config.field_mapping.body],
        };
      }

      searchResults.push({
        title: source[config.field_mapping.title] || '',
        body: source[config.field_mapping.body] || '',
        url: config.field_mapping.url
          ? source[config.field_mapping.url]
          : undefined,
        id: String(hit._id),
        score: hit._score,
        highlight,
      });
    }

    return {
      query,
      results: searchResults,
      totalResults: searchResults.length,
      searchTime: elapsedTime,
    };
  }
}