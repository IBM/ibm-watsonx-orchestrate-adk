# Knowledge Pattern

## Overview

This pattern demonstrates how to implement a knowledge base that answers customer questions with user provided content. The pattern focuses on supporting the semantic search of the retrieval phase in Retrieval-Augmented Generation (RAG) pipeline, while leaves the answer generation phase to the agent to handle.

## Problems This Pattern Solves

### **Setting Up And Configuring A Vector Store**

Knowledge requires a vector store that persists the embedded vectors of user provided content. After a user chooses a vector store, the user needs to setup and configure the vector store in order to be used by Knowledge.

The Knowledge Pattern addresses this issues by presenting clear steps from setup to configuring the vector store.

### **Creating Vector Indices**

When the vector store is setup and prepared, the user needs to create the vector indices to store and search user provided content and embedded vectors.

This pattern demonstrates the options of creating the vector indices in the vector store.

### **Ingesting User Provided Content**

In order to do semantic search, the user also needs to ingest the user provided content in the vector index. For user provided content in PDF format, the user needs to read the PDF file, chunk it, vectorize the content, and persist the embedded vectors in the index.

This pattern addresses all these requirements.

## Implementation Walkthrough

Below we walk through the knowledge implementation that demonstrates this pattern.

### Setup And Configure A Vector Store

To setup an OpenSearch vector store, user can use the docker compose file like the following, set the administrator's password by using the environment variable `OPENSEARCH_INITIAL_ADMIN_PASSWORD`, and run a command such as `docker compose up`.

**File:** [`knowledge/docker-compose.yaml`](../toolkits/banking_mcp_server/knowledge/docker-compose.yaml)

This creates a single node OpenSearch cluster locally.

After the OpenSearch cluster is created, user will need to configure the vector store in order to be used by knowledge.

User can run the following python program to configure the OpenSearch vector. 

**File:** [`knowledge/register_model_and_create_pipelines.py`](../toolkits/banking_mcp_server/knowledge/register_model_and_create_pipelines.py)
 
By default, this program configures the local OpenSearch instance. User can customize the OpenSearch instance that needs to be configured for knowledge by using the following environment variables:

```
OPENSEARCH_ENDPOINT (default: 'https://localhost')
OPENSEARCH_PORT (default: '9200')
OPENSEARCH_USERNAME (default: 'admin')
OPENSEARCH_PASSWORD
```

The program does the following configuration steps:

#### Step 1: Enable Machine Learning In The Opensearch Cluster

This step allows running the embedding model on the single node in the cluster. It also enables the model access control and set the native memory threshold.

#### Step 2: Register Model Group

In OpenSearch, a model group is a collection that organizes different versions of a specific machine learning (ML) model and controls user access to those models. It is a key component of model access control within the OpenSearch ML Commons plugin

This step checks the existence of the model group by name. It creates a new model group if one does not exist. It also gets the `model group id`, which is required by the subsequent steps.

The model group name can be customized by using the following environment variable:

```
MODEL_GROUP_NAME (default: 'local_model_group')
```

#### Step 3: Register Model

Knowledge uses semantic search which uses embedded vectors in the vector store. This step registers an embedding model which is required to vectorize user provided content and customer queries. 

The embedding model to register can be customized by using the following environment variables:

```
MODEL_NAME (default: 'huggingface/sentence-transformers/msmarco-distilbert-base-tas-b')
MODEL_VERSION (default: '1.0.3')
MODEL_FORMAT (default: 'TORCH_SCRIPT')
```

For more pretrained models in OpenSearch, please refer to: https://docs.opensearch.org/latest/ml-commons-plugin/pretrained-models/

#### Step 4: Obtain Model ID

The task of registering a model in the OpenSearch cluster takes time to complete. This step waits for the step to complete. If the step is still not complete after the wait, this step will attempt a few more times to obtain the model ID. The model ID is required in the subsequent steps.

The wait time and the number of attempts can be customized by using the following environment variables:

```
REGISTER_MODEL_WAIT_SECS (default: 8)
REGISTER_MODEL_ATTEMPTS (default: 5)
```

#### Step 5: Deploy Model

The registered model needs to be deployed in order to be used in ingestion and search. This step deploys the registered model.

#### Step 6: Create Ingest Pipeline

This step creates an ingest pipeline which will be used to vectorize user provided content and embed the vectors in the vector index.

The pipeline name can be customized by using the following environment variable:

```
INGEST_PIPELINE_NAME (default: 'ingest_pipeline')
```

#### Step 7: Create Search Pipeline

This step creates a search pipeline which will be used to embed customer queries for semantic search.

The pipeline name can be customized by using the following environment variable:

```
SEARCH_PIPELINE_NAME (default: 'search_pipeline')
```

### Create Vector Indices

After the vector store is setup and configured, users can create vector indices for knowledge.

The following python program creates a vector index in the OpenSearch vector store. 

**File:** [`knowledge/create_vector_index.py`](../toolkits/banking_mcp_server/knowledge/create_vector_index.py)
 
By default, this program creates a vector index in the local OpenSearch instance. User can customize the OpenSearch instance details by using the following environment variables:

```
OPENSEARCH_ENDPOINT (default: 'https://localhost')
OPENSEARCH_PORT (default: '9200')
OPENSEARCH_USERNAME (default: 'admin')
OPENSEARCH_PASSWORD
```

This program creates a vector index that is compatible with the chosen embedding model. It also sets the index to use the desired pipelines for ingestion and search.

The index name, ingest pipeline name and search pipeline name can be customized by using the following environment variable:

```
INDEX_NAME (default: 'knowledge_vector_index')
INGEST_PIPELINE_NAME (default: 'ingest_pipeline')
SEARCH_PIPELINE_NAME (default: 'search_pipeline')
```

The ingest pipeline and search pipeline names need to be the same as the ones used in step 6 and 7 of the setup and configure vector store program.

### Ingest Documents

After the vector store is setup and configured, and the vector index is created, users can ingest content into the vector index as the knowledge source.

The following python program ingests a document into a vector index. 

**File:** [`knowledge/ingest_document.py`](../toolkits/banking_mcp_server/knowledge/ingest_document.py)
 
By default, this program ingests a document to a vector index in the local OpenSearch instance. User can customize the OpenSearch instance details by using the following environment variables:

```
OPENSEARCH_ENDPOINT (default: 'https://localhost')
OPENSEARCH_PORT (default: '9200')
OPENSEARCH_USERNAME (default: 'admin')
OPENSEARCH_PASSWORD
```

This program can ingest a PDF document to a vector index at a time. The PDF document has a size limit of 25 MB. The usage of this program is `python ingest_document.py`, for example: `python ingest_document.py faq/Mortgage_FQA.pdf`

The vector index name, chunk size and chunk overlap can be customized by using the following environment variables:

```
INDEX_NAME (default: 'knowledge_vector_index')
CHUNK_SIZE (default: 400)
CHUNK_OVERLAP (default: 50)
```

### How the Knowledge Setup Flow Works

1. **Setup The OpenSearch Vector Store**: User runs `docker compose up` to setup a local OpenSearch instance 
2. **Configure The OpenSearch Vector Store**: User runs the [`knowledge/register_model_and_create_pipelines.py`](../toolkits/banking_mcp_server/knowledge/register_model_and_create_pipelines.py) program to configure OpenSearch
3. **Create Vector Index**: User runs the [`knowledge/create_vector_index.py`](../toolkits/banking_mcp_server/knowledge/create_vector_index.py) program to create a vector index
4. **Ingest Document**: User runs the [`knowledge/ingest_document.py`](../toolkits/banking_mcp_server/knowledge/ingest_document.py) program to ingest user content

## Key Takeaways

The Knowledge Pattern provides essential capabilities for customer care applications that need content grounded answers.

**When to use this pattern:**

- Customer asks a question such as `What's the daily transfer limit between my accounts?` during a conversation flow

**Channel Adaptation:**

- **Web/Mobile**: Displays the content grounded answer provided by knowledge
- **Voice**: Presents the content grounded answer provided by knowledge

The Knowledge Pattern is essential for customer care applications that need to answer customer questions with user provided content at any point in time during a conversation..
