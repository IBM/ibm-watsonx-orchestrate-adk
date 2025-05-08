from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base import KnowledgeBase
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.types import ConversationalSearchConfig, IndexConnection, MilvusConnection, FieldMapping

built_in_knowledge = KnowledgeBase(
    name="ibm_knowledge_base",
    description="General information about IBM and its history",
    documents=["../../../../examples/agent_builder/ibm_knowledge/knowledge_base/IBM_wikipedia.pdf",
               "../../../../examples/agent_builder/ibm_knowledge/knowledge_base/history_of_ibm.pdf"]
)

external_knowledge_base = KnowledgeBase(
    name="wxa_knowledge_base",
    description="Information about WXA docs",
    conversational_search_tool=ConversationalSearchConfig(
        index_config=[
            IndexConnection(milvus=MilvusConnection(
                grpc_host="https://xxxx.lakehouse.appdomain.cloud",
                database="test_db",
                collection="search_wa_docs",
                index="dense",
                embedding_model_id="sentence-transformers/all-minilm-l12-v2",
                field_mapping=FieldMapping(title="title", body="text")
            ))
        ]
    )
)