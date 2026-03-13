from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, model_validator, Field


class SpecVersion(str, Enum):
    V1 = "v1"

class KnowledgeBaseKind(str, Enum):
    KNOWLEDGE_BASE = "knowledge_base"

class ExtractionStrategy(str, Enum):
    EXPRESS = 'express'
    STANDARD = 'standard'
    HIGH_QUALITY = 'high_quality'

class RetrievalConfidenceThreshold(str, Enum):
    Off = "Off"
    Lowest = "Lowest"
    Low = "Low"
    High = "High"
    Highest = "Highest"


class GeneratedResponseLength(str, Enum):
    Concise = "Concise"
    Moderate = "Moderate"
    Verbose = "Verbose"


class ResponseConfidenceThreshold(str, Enum):
    Off = "Off"
    Lowest = "Lowest"
    Low = "Low"
    High = "High"
    Highest = "Highest"

class KnowledgeBaseRepresentation(str, Enum):
    auto = "auto"
    tool = "tool"

class ConfidenceThresholds(BaseModel):
    retrieval_confidence_threshold: Optional[RetrievalConfidenceThreshold] = None
    response_confidence_threshold: Optional[ResponseConfidenceThreshold] = None

class CitationsConfig(BaseModel):
    """
    example:
    {
        "citation_title": "how do i know",
        "citations_shown": 5,
    }
    """
    citation_title: Optional[str] = None
    citations_shown: Optional[int] = None


class HAPFilteringConfig(BaseModel):
    enabled: Optional[bool] = None
    threshold: Optional[float] = None


class HAPFiltering(BaseModel):
    """
    example
    {
        "output": {
            "enabled": True,
            "threshold": 0.7,
        }
    }

    """
    output: Optional[HAPFilteringConfig] = None

class QueryRewriteConfig(BaseModel):
    """
    example

    {
        "enabled": True,
        "model_id": "meta-llama/llama-3-1-70b-instruct"
    }

    """
    enabled: Optional[bool] = None
    model_id: Optional[str] = None

class GenerationConfiguration(BaseModel):
    """
    example
    {
        "model_id": "meta-llama/llama-3-1-70b-instruct",
        "prompt_instruction": "When the documents are in different languages, you should respond in english.",
        "max_docs_passed_to_llm": 10,
        "retrieval_confidence_threshold": "Lowest",
        "generated_response_length": "Moderate",
        "display_text_no_results_found": "no docs found",
        "display_text_connectivity_issue": "conn failed",
        "idk_message": "I dont know",
    }
    """

    model_id: Optional[str] = None
    prompt_instruction: Optional[str] = None
    max_docs_passed_to_llm: Optional[int] = None
    generated_response_length: Optional[GeneratedResponseLength] = None
    display_text_no_results_found: Optional[str] = None
    display_text_connectivity_issue: Optional[str] = None
    idk_message: Optional[str] = None
    enabled: bool = False

class FieldMapping(BaseModel):
    """
    example

    {
        "title": "title",
        "body": "text",
        "url": "some-url"
    }
    """
    title: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None

class MilvusConnection(BaseModel):
    """
    example:
    {
        "grpc_host": "https://xxxx.lakehouse.appdomain.cloud",
        "database": "test_db",
        "collection": "search_wa_docs",
        "index": "dense",
        "embedding_model_id": "sentence-transformers/all-minilm-l12-v2",
        "grpc_port": "30564",
        "filter": "title like \"%action%\"",
        "limit": 10,
        "field_mapping": {
                        "title": "title",
                        "body": "text",
                        "url": "some-url"
                    }
    }
    """
    grpc_host: Optional[str] = None
    grpc_port: Optional[str] = None
    server_cert: Optional[str] = None
    database: Optional[str] = None
    collection: Optional[str] = None
    index: Optional[str] = None
    embedding_model_id: Optional[str] = None
    limit : Optional[int] = None
    filter: Optional[str] = None
    field_mapping: Optional[FieldMapping] = None


class ElasticSearchConnection(BaseModel):
    """
    example:

    {
        "url": "https://xxxx.databases.appdomain.cloud",
        "index": "search-wa-docs",
        "port": "31871",
        "query_body": {"size":5,"query":{"text_expansion":{"ml.tokens":{"model_id":".elser_model_2_linux-x86_64","model_text": "$QUERY"}}}},
        "result_filter": [
                            {
                                "match": {
                                    "title": "A_keyword_in_title"
                                }
                            },
                            {
                                "match": {
                                    "text": "A_keyword_in_text"
                                }
                            },
                            {
                                "match": {
                                    "id": "A_specific_ID"
                                }
                            }
                        ] = None,
        "field_mapping": {
                        "title": "title",
                        "body": "text",
                        "url": "some-url"
                    }
    }
    """
    url: Optional[str] = None
    index: Optional[str] = None
    port: Optional[str] = None
    query_body: Optional[dict] = None
    result_filter: Optional[list] = None 
    field_mapping: Optional[FieldMapping] = None

class CustomSearchConnection(BaseModel):
    """
    example:
    {
        "url": "https://customsearch.xxxx.us-east.codeengine.appdomain.cloud",
        "filter": "...",
        "metadata": {...}
    }
    """
    url: str
    filter: Optional[str] = None
    metadata: Optional[dict] = None

class AstraDBConnection(BaseModel):
    """
    example:
    {
        "api_endpoint": "https://xxx-us-east-2.apps.astra.datastax.com",
        "key_space": "default_keyspace",
        "collection": "search_wa_docs",
        "embedding_model_id": "sentence-transformers/all-minilm-l12-v2",
        "port": "443",
        "filter": "productType: \"boots\"",
        "limit": 5,
        "field_mapping": {
                        "title": "title",
                        "body": "text",
                        "url": "some-url"
                    }
    }
    """
    api_endpoint: str
    port: Optional[str] = None
    server_cert: Optional[str] = None
    keyspace: Optional[str] = None
    data_type: str
    collection: Optional[str] = None
    table: Optional[str] = None
    index_column: Optional[str] = None
    embedding_mode: Optional[str] = None
    embedding_model_id: Optional[str] = None
    search_mode: Optional[str] = None
    limit: Optional[int] = 5
    filter: Optional[str] = None
    field_mapping: Optional[FieldMapping] = None

class IndexConnection(BaseModel):
    connection_id: Optional[str] = None
    app_id: Optional[str] = None
    milvus: Optional[MilvusConnection] = None
    elastic_search: Optional[ElasticSearchConnection] = None
    custom_search: Optional[CustomSearchConnection] = None
    astradb: Optional[AstraDBConnection] = None


class QuerySource(str, Enum):
    SessionHistory = "SessionHistory"
    Agent = "Agent"


class ConversationalSearchConfig(BaseModel):
    language: Optional[str] = None
    index_config: list[IndexConnection] = None
    generation: Optional[GenerationConfiguration] = None
    query_rewrite: Optional[QueryRewriteConfig] = None
    citations: Optional[CitationsConfig] = None
    hap_filtering: Optional[HAPFiltering] = None
    confidence_thresholds: Optional[ConfidenceThresholds] = None
    query_source: QuerySource = QuerySource.Agent
    agent_query_description: str = "The query to search for in the knowledge base"
    supports_full_document: Optional[bool] = None

    @model_validator(mode="after")
    def validate_agent_query_description(self) -> 'ConversationalSearchConfig':
        if self.query_source == QuerySource.Agent and len(self.agent_query_description) == 0:
            raise ValueError("Provide a non-empty agent_query_description when query source is `Agent`")
        return self

class KnowledgeBaseBuiltInVectorIndexConfig(BaseModel):
    embeddings_model_name: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    limit: Optional[int] = None
    extraction_strategy: Optional[ExtractionStrategy] = ExtractionStrategy.STANDARD

class FileUpload(BaseModel):
    path: str
    url: Optional[str] = None
    
class KnowledgeBaseSpec(BaseModel):
    """Schema for a complete knowledge-base."""
    spec_version: SpecVersion = None
    kind: KnowledgeBaseKind = KnowledgeBaseKind.KNOWLEDGE_BASE
    id: Optional[UUID] = None 
    tenant_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    vector_index: Optional[KnowledgeBaseBuiltInVectorIndexConfig] = None
    conversational_search_tool: Optional[ConversationalSearchConfig] | Optional[UUID] = None
    prioritize_built_in_index: Optional[bool] = None
    representation: Optional[KnowledgeBaseRepresentation] = None
    vector_index_id: Optional[UUID] = None 
    created_by: Optional[str] = None
    created_on: Optional[datetime] = None 
    updated_at: Optional[datetime] = None
    # For import/update
    documents: list[str] | list[FileUpload] = None

class KnowledgeBaseListEntry(BaseModel):
    name: str = Field(description="Name of the knowledge base")
    description: Optional[str] = Field(description="A description of the content contained in a knowledge base")
    app_id: Optional[str] = Field(description="The app id for a connection that connects the knowledge base to an external knowledge store")
    id: Optional[str] = Field(description="Unique identifier of the knowledge base")

    def get_row_details(self):
        return [self.name, self.description, self.app_id, self.id]