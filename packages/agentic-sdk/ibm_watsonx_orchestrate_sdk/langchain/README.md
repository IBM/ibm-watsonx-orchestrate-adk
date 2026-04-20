# IBM watsonx Orchestrate LangChain Integration

A lightweight LangChain integration package that provides drop-in replacements for `ChatOpenAI` and `OpenAIEmbeddings`, routing all LLM and embedding calls through IBM watsonx Orchestrate's AI Gateway for enhanced security, centralized model management, and enterprise-grade features.

## Features

- ✅ **Automatic authentication** with token refresh
- ✅ **Multiple deployment modes**: Runtime (runs-on), Standalone (runs-elsewhere), and Local development
- ✅ **Enterprise features**: Centralized model policies, usage tracking, security controls

### Chat Models (ChatWxO)
- ✅ **Drop-in replacement** for `langchain_openai.ChatOpenAI`
- ✅ **Full ChatOpenAI API compatibility**: invoke, stream, batch, bind_tools, with_structured_output
- ✅ **Async support**: ainvoke, astream, abatch


### Embeddings (WxOEmbeddings)
- ✅ **Drop-in replacement** for `langchain_openai.OpenAIEmbeddings`
- ✅ **Full OpenAIEmbeddings API compatibility**: embed_query, embed_documents
- ✅ **Async support**: aembed_query, aembed_documents

## Installation

```bash
pip install ibm-watsonx-orchestrate-sdk
```

## Requirements

- Python 3.11, 3.12, or 3.13
- `langchain-openai >= 1.1.0`
- `ibm-watsonx-orchestrate-clients` (automatically installed)

## Quick Start

### Method 1: From Instance Credentials (Standalone/Runs-Elsewhere Mode)

For standalone scripts or applications outside WxO runtime:

```python
from ibm_watsonx_orchestrate_sdk.langchain import ChatWxO

llm = ChatWxO.from_instance_credentials(
    instance_url="https://your-instance.cloud.ibm.com",
    api_key="your-wxo-api-key",
    model="virtual-model/watsonx/meta-llama/llama-3-2-90b-vision-instruct",
    temperature=0.7,
    max_tokens=1000
)

response = llm.invoke("Tell me a joke about programming")
print(response.content)
```

### Method 2: From Execution Context (Runtime/Runs-On Mode)

When running inside a WxO runtime with execution context:

```python
from ibm_watsonx_orchestrate_sdk.langchain import ChatWxO

# Execution context provided by WxO runtime
execution_context = {
    "access_token": "runtime-token",
    "api_proxy_url": "https://proxy.example.com/v1",
    "tenant_id": "tenant-123",
    "user_id": "user-456",
    "thread_id": "thread-789",
    "run_id": "run-abc",
    "deployment_platform": "wxo"
}

llm = ChatWxO.from_execution_context(
    execution_context=execution_context,
    model="virtual-model/watsonx/ibm/granite-3-8b-instruct",
    temperature=0.2
)

response = llm.invoke("What is the capital of France?")
print(response.content)
```

### Method 3: From RunnableConfig (Runtime/Runs-On Mode)

For LangGraph agents with RunnableConfig:

```python
from ibm_watsonx_orchestrate_sdk.langchain import ChatWxO
from langgraph.graph.state import RunnableConfig

def create_agent(config: RunnableConfig):
    llm = ChatWxO.from_runnable_config(
        config=config,
        model="virtual-model/watsonx/meta-llama/llama-3-2-90b-vision-instruct",
        temperature=0.2
    )
    
    response = llm.invoke("What is the capital of France?")
    print(response.content)
    
    return llm
```

### Method 4: From WxO Agentic Session

For advanced use cases with pre-configured AgenticSession:

```python
from ibm_watsonx_orchestrate_sdk.langchain import ChatWxO
from ibm_watsonx_orchestrate_sdk.client import Client

# Create client and get session
client = Client.from_instance_credentials(
    instance_url="https://your-instance.cloud.ibm.com",
    api_key="your-wxo-api-key"
)

llm = ChatWxO.from_session(
    session=client.session,
    model="virtual-model/watsonx/ibm/granite-3-8b-instruct"
)

response = llm.invoke("Hello!")
print(response.content)
```

### Method 5: Direct Initialization (Advanced)

Direct initialization with all parameters:

```python
from ibm_watsonx_orchestrate_sdk.langchain import ChatWxO

llm = ChatWxO(
    instance_url="https://your-instance.cloud.ibm.com",
    api_key="your-wxo-api-key",
    model="virtual-model/watsonx/meta-llama/llama-3-2-90b-vision-instruct",
    temperature=0.7,
    max_tokens=1000
)

response = llm.invoke("Tell me a joke about programming")
print(response.content)
```

## Usage Examples

### Basic Chat Completion

```python
from ibm_watsonx_orchestrate_sdk.langchain import ChatWxO

llm = ChatWxO.from_instance_credentials(
    instance_url="https://your-instance.cloud.ibm.com",
    api_key="your-api-key",
    model="virtual-model/watsonx/ibm/granite-3-8b-instruct"
)

# Simple string input
response = llm.invoke("What is machine learning?")
print(response.content)

# Message format
from langchain_core.messages import HumanMessage, SystemMessage

messages = [
    SystemMessage(content="You are a helpful AI assistant."),
    HumanMessage(content="Explain quantum computing in simple terms.")
]

response = llm.invoke(messages)
print(response.content)
```

### Streaming Responses

```python
# Synchronous streaming
for chunk in llm.stream("Write a short story about a robot"):
    print(chunk.content, end="", flush=True)

# Async streaming
import asyncio

async def stream_example():
    async for chunk in llm.astream("Explain photosynthesis"):
        print(chunk.content, end="", flush=True)

asyncio.run(stream_example())
```

### Tool Calling (Function Calling)

```python
from pydantic import BaseModel, Field

class GetWeather(BaseModel):
    """Get the current weather for a location"""
    location: str = Field(description="City and state, e.g. San Francisco, CA")
    unit: str = Field(description="Temperature unit", enum=["celsius", "fahrenheit"])

class GetPopulation(BaseModel):
    """Get the population of a city"""
    location: str = Field(description="City and state, e.g. San Francisco, CA")

# Bind tools to the model
llm_with_tools = llm.bind_tools([GetWeather, GetPopulation])

response = llm_with_tools.invoke("What's the weather and population in NYC?")

# Access tool calls
for tool_call in response.tool_calls:
    print(f"Tool: {tool_call['name']}")
    print(f"Args: {tool_call['args']}")
```

### Structured Output

```python
from pydantic import BaseModel, Field

class Person(BaseModel):
    """Information about a person"""
    name: str = Field(description="Person's full name")
    age: int = Field(description="Person's age in years")
    occupation: str = Field(description="Person's job or profession")
    hobbies: list[str] = Field(description="List of hobbies")

# Create structured output model
structured_llm = llm.with_structured_output(Person)

# Get structured response
person = structured_llm.invoke(
    "Tell me about a software engineer named Alice who is 28 years old "
    "and enjoys hiking, reading, and photography."
)

print(f"Name: {person.name}")
print(f"Age: {person.age}")
print(f"Occupation: {person.occupation}")
print(f"Hobbies: {', '.join(person.hobbies)}")
```

### Batch Processing

```python
# Process multiple inputs in parallel
messages_batch = [
    "What is Python?",
    "What is JavaScript?",
    "What is Rust?"
]

responses = llm.batch(messages_batch)

for i, response in enumerate(responses):
    print(f"Q{i+1}: {messages_batch[i]}")
    print(f"A{i+1}: {response.content}\n")

# Async batch processing
async def batch_example():
    responses = await llm.abatch(messages_batch)
    return responses

asyncio.run(batch_example())
```

### Advanced Configuration

```python
llm = ChatWxO.from_instance_credentials(
    instance_url="https://your-instance.cloud.ibm.com",
    api_key="your-api-key",
    model="watsonx/meta-llama/llama-3-2-90b-vision-instruct",
    
    # Model parameters
    temperature=0.7,
    max_tokens=2000,
    top_p=0.9,
    frequency_penalty=0.0,
    presence_penalty=0.0,
    
    # Streaming configuration
    streaming=True,
    
    # Request configuration
    timeout=60.0,
    max_retries=3
)
```

## Migration from ChatOpenAI

Migrating from `langchain_openai.ChatOpenAI` to `ChatWxO` is straightforward:

### Before (ChatOpenAI)

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4",
    api_key="sk-...",
    temperature=0.7
)
```

### After (ChatWxO)

```python
from ibm_watsonx_orchestrate_sdk.langchain import ChatWxO

llm = ChatWxO.from_instance_credentials(
    instance_url="https://your-instance.cloud.ibm.com",
    api_key="your-wxo-api-key",
    model="watsonx/meta-llama/llama-3-2-90b-vision-instruct",
    temperature=0.7
)
```

**Key differences:**
1. Import from `ibm_watsonx_orchestrate_sdk.langchain` instead of `langchain_openai`
2. Use `ChatWxO()` instead of `ChatOpenAI()`
3. Provide `instance_url` (your WxO instance URL)
4. Use WxO model IDs (format: `provider/model-name` or `provider/creator/model-name`)
5. All other parameters and methods remain the same!

## API Reference
```python
class ChatWxO(ChatOpenAI):
    """
    IBM watsonx Orchestrate Chat Model Wrapper.
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        instance_url: Optional[str] = None,
        iam_url: Optional[str] = None,
        auth_type: Optional[str] = None,
        verify: Optional[str | bool] = None,
        authenticator: Optional[Authenticator] = None,
        local: bool = False,
        *,
        execution_context: Optional[ExecutionContext | Dict[str, Any]] = None,
        session: Optional[AgenticSession] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize ChatWxO wrapper.
        
        Args:
            model: Model ID in format "virtual-model/provider/model-name"
                  Example: "virtual-model/watsonx/meta-llama/llama-3-2-90b-vision-instruct"
            api_key: WxO API key (optional for local, required for SaaS standalone)
                    - Local: Not required (uses default local credentials)
                    - SaaS standalone: Provide your WxO API key for automatic token management
            instance_url: WxO instance base URL (required unless using execution_context or session)
                         - Local: "http://localhost:4321" (or your local instance URL)
                         - SaaS standalone: Your WxO instance URL (e.g., "https://your-instance.cloud.ibm.com")
            iam_url: IAM authentication URL (optional)
                    - For staging/test environments: "https://iam.platform.test.saas.ibm.com"
                    - If not provided, will be auto-detected based on environment
            auth_type: Authentication type (optional)
                      - Options: "ibm_iam" (SaaS), "mcsp", "mcsp_v1", "mcsp_v2" (AWS), "cpd" (on-prem)
                      - If not provided, will be auto-detected based on environment
            verify: Certificate verification (optional)
            authenticator: IBM Cloud SDK authenticator (optional)
            local: Whether to use local mode (default: False, auto-detected from instance_url)
            execution_context: ExecutionContext for runs-on mode (optional)
            session: Pre-configured AgenticSession (optional)
            **kwargs: Additional arguments passed to ChatOpenAI (temperature, max_tokens, etc.)
```

### Supported Methods

All `ChatOpenAI` methods are supported:

- `invoke(messages)` - Synchronous chat completion
- `ainvoke(messages)` - Async chat completion
- `stream(messages)` - Synchronous streaming
- `astream(messages)` - Async streaming
- `batch(messages_list)` - Batch processing
- `abatch(messages_list)` - Async batch processing
- `bind_tools(tools)` - Bind tools/functions
- `with_structured_output(schema)` - Structured output

### Class Methods

- `from_instance_credentials(instance_url, api_key, model, **kwargs)` - Create from instance credentials (standalone/runs-elsewhere)
- `from_execution_context(execution_context, model, **kwargs)` - Create from execution context (runtime/runs-on)
- `from_session(session, model, **kwargs)` - Create from AgenticSession
- `from_runnable_config(config, model, **kwargs)` - Create from RunnableConfig (LangGraph)

## Deployment Modes

### Runs-Elsewhere Mode (Standalone)

For standalone scripts with API key authentication:

```python
llm = ChatWxO.from_instance_credentials(
    instance_url="https://your-instance.cloud.ibm.com",
    api_key="your-wxo-api-key",
    model="virtual-model/..."
)
# Token automatically generated and refreshed as needed
```

### Runs-On Mode (Runtime)

For agents running inside WxO runtime with execution context:

```python
llm = ChatWxO.from_execution_context(
    execution_context=context,  # Provided by runtime
    model="virtual-model/..."
)
# or
llm = ChatWxO.from_runnable_config(
    config=config,  # Provided by runtime
    model="virtual-model/..."
)
# Uses runtime-provided access token
```

### Local Mode (Development)

For local development with simplified authentication:

```python
llm = ChatWxO(
    instance_url="http://localhost:4321",
    model="virtual-model/...",
    local=True
)
# Optimized for local development
```

## Model IDs

Use the model ID formats returned by the WxO `/models` endpoint:

```
provider/model-name
provider/creator/model-name
```

Examples:
- `watsonx/meta-llama/llama-3-2-90b-vision-instruct`
- `watsonx/ibm/granite-3-8b-instruct`
- `openai/gpt-4o`

## Error Handling

```python
from ibm_watsonx_orchestrate_sdk.langchain import ChatWxO

try:
    llm = ChatWxO(
        model="watsonx/test-model",
        api_key="your-api-key",
        wxo_base_url="https://your-instance.cloud.ibm.com"
    )
    response = llm.invoke("Hello!")
except TypeError as e:
    print(f"Missing required parameter: {e}")
except ValueError as e:
    print(f"Invalid parameter value: {e}")
except Exception as e:
    print(f"Error: {e}")
```

## WxOEmbeddings - Embeddings Model

### Quick Start

#### Method 1: From Instance Credentials (Standalone/Runs-Elsewhere Mode)

```python
from ibm_watsonx_orchestrate_sdk.langchain import WxOEmbeddings

embeddings = WxOEmbeddings.from_instance_credentials(
    instance_url="https://your-instance.cloud.ibm.com",
    api_key="your-wxo-api-key",
    model="openai/text-embedding-3-small"
)

# Embed a single query
query_embedding = embeddings.embed_query("What is machine learning?")
print(f"Embedding dimension: {len(query_embedding)}")
```

#### Method 2: From Execution Context (Runtime/Runs-On Mode)

```python
from ibm_watsonx_orchestrate_sdk.langchain import WxOEmbeddings

# Execution context provided by WxO runtime
execution_context = {
    "access_token": "runtime-token",
    "api_proxy_url": "https://proxy.example.com/v1",
    "tenant_id": "tenant-123",
    "user_id": "user-456"
}

embeddings = WxOEmbeddings.from_execution_context(
    execution_context=execution_context,
    model="openai/text-embedding-3-small"
)

query_embedding = embeddings.embed_query("What is machine learning?")
print(f"Embedding dimension: {len(query_embedding)}")
```

#### Method 3: From RunnableConfig (Runtime/Runs-On Mode)

```python
from ibm_watsonx_orchestrate_sdk.langchain import WxOEmbeddings
from langgraph.graph.state import RunnableConfig

def create_agent(config: RunnableConfig):
    embeddings = WxOEmbeddings.from_runnable_config(
        config=config,
        model="openai/text-embedding-3-small"
    )
    
    # Embed a single query
    query_embedding = embeddings.embed_query("What is machine learning?")
    print(f"Embedding dimension: {len(query_embedding)}")
    
    return embeddings
```

### Usage Examples

#### Basic Embeddings

```python
from ibm_watsonx_orchestrate_sdk.langchain import WxOEmbeddings

embeddings = WxOEmbeddings.from_instance_credentials(
    instance_url="https://your-instance.cloud.ibm.com",
    api_key="your-api-key",
    model="openai/text-embedding-3-small"
)

# Embed a single query
query = "What is the capital of France?"
query_embedding = embeddings.embed_query(query)
print(f"Query embedding: {len(query_embedding)} dimensions")

# Embed multiple documents
documents = [
    "Paris is the capital of France.",
    "London is the capital of England.",
    "Berlin is the capital of Germany."
]
doc_embeddings = embeddings.embed_documents(documents)
print(f"Embedded {len(doc_embeddings)} documents")
```

#### Async Embeddings

```python
import asyncio

async def embed_async():
    embeddings = WxOEmbeddings.from_instance_credentials(
        instance_url="https://your-instance.cloud.ibm.com",
        api_key="your-api-key",
        model="openai/text-embedding-3-small"
    )
    
    # Async single query
    query_embedding = await embeddings.aembed_query("What is AI?")
    print(f"Query embedding: {len(query_embedding)} dimensions")
    
    # Async multiple documents
    documents = ["Document 1", "Document 2", "Document 3"]
    doc_embeddings = await embeddings.aembed_documents(documents)
    print(f"Embedded {len(doc_embeddings)} documents")

asyncio.run(embed_async())
```

#### Semantic Search with Vector Store

```python
from ibm_watsonx_orchestrate_sdk.langchain import WxOEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Initialize embeddings
embeddings = WxOEmbeddings.from_instance_credentials(
    instance_url="https://your-instance.cloud.ibm.com",
    api_key="your-api-key",
    model="openai/text-embedding-3-small"
)

# Create documents
documents = [
    Document(page_content="Paris is the capital of France.", metadata={"country": "France"}),
    Document(page_content="London is the capital of England.", metadata={"country": "England"}),
    Document(page_content="Berlin is the capital of Germany.", metadata={"country": "Germany"}),
    Document(page_content="Madrid is the capital of Spain.", metadata={"country": "Spain"}),
]

# Create vector store
vectorstore = FAISS.from_documents(documents, embeddings)

# Perform similarity search
query = "What is the capital of France?"
results = vectorstore.similarity_search(query, k=2)

for doc in results:
    print(f"Content: {doc.page_content}")
    print(f"Metadata: {doc.metadata}\n")
```

#### RAG (Retrieval-Augmented Generation)

```python
from ibm_watsonx_orchestrate_sdk.langchain import ChatWxO, WxOEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

# Initialize embeddings and LLM
embeddings = WxOEmbeddings.from_instance_credentials(
    instance_url="https://your-instance.cloud.ibm.com",
    api_key="your-api-key",
    model="openai/text-embedding-3-small"
)

llm = ChatWxO.from_instance_credentials(
    instance_url="https://your-instance.cloud.ibm.com",
    api_key="your-api-key",
    model="watsonx/ibm/granite-3-8b-instruct"
)

# Create knowledge base
documents = [
    Document(page_content="Python is a high-level programming language."),
    Document(page_content="JavaScript is used for web development."),
    Document(page_content="Java is an object-oriented programming language."),
]

vectorstore = FAISS.from_documents(documents, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

# Create RAG chain
template = """Answer the question based on the following context:

Context: {context}

Question: {question}

Answer:"""

prompt = ChatPromptTemplate.from_template(template)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
)

# Ask a question
response = rag_chain.invoke("What is Python?")
print(response.content)
```

#### Similarity Calculation

```python
import numpy as np
from ibm_watsonx_orchestrate_sdk.langchain import WxOEmbeddings

embeddings = WxOEmbeddings.from_instance_credentials(
    instance_url="https://your-instance.cloud.ibm.com",
    api_key="your-api-key",
    model="openai/text-embedding-3-small"
)

# Embed texts
text1 = "Machine learning is a subset of artificial intelligence"
text2 = "AI includes machine learning and deep learning"
text3 = "The weather is nice today"

embedding1 = embeddings.embed_query(text1)
embedding2 = embeddings.embed_query(text2)
embedding3 = embeddings.embed_query(text3)

# Calculate cosine similarity
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

sim_1_2 = cosine_similarity(embedding1, embedding2)
sim_1_3 = cosine_similarity(embedding1, embedding3)

print(f"Similarity between text1 and text2: {sim_1_2:.4f}")
print(f"Similarity between text1 and text3: {sim_1_3:.4f}")
```

### Migration from OpenAIEmbeddings

Migrating from `langchain_openai.OpenAIEmbeddings` to `WxOEmbeddings` is straightforward:

#### Before (OpenAIEmbeddings)

```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key="sk-..."
)
```

#### After (WxOEmbeddings)

```python
from ibm_watsonx_orchestrate_sdk.langchain import WxOEmbeddings

embeddings = WxOEmbeddings.from_instance_credentials(
    instance_url="https://your-instance.cloud.ibm.com",
    api_key="your-wxo-api-key",
    model="openai/text-embedding-3-small"
)
```

**Key differences:**
1. Import from `ibm_watsonx_orchestrate_sdk.langchain` instead of `langchain_openai`
2. Use `WxOEmbeddings.from_instance_credentials()` instead of `OpenAIEmbeddings()`
3. Provide `instance_url` (your WxO instance URL)
4. Use WxO model IDs (format: `provider/model-name`)
5. All other parameters and methods remain the same!

### API Reference - WxOEmbeddings

```python
class WxOEmbeddings(OpenAIEmbeddings):
    """IBM watsonx Orchestrate Embeddings Wrapper."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        instance_url: Optional[str] = None,
        iam_url: Optional[str] = None,
        auth_type: Optional[str] = None,
        verify: Optional[str | bool] = None,
        authenticator: Optional[Authenticator] = None,
        local: bool = False,
        *,
        execution_context: Optional[ExecutionContext | Dict[str, Any]] = None,
        session: Optional[AgenticSession] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize WxOEmbeddings wrapper.
        
        Args:
            model: Model ID in format "provider/model-name" (e.g., "openai/text-embedding-3-small")
            api_key: WxO API key (optional for local, required for SaaS standalone)
            instance_url: WxO instance base URL (required unless using execution_context or session)
            iam_url: IAM authentication URL (optional)
            auth_type: Authentication type (optional)
            verify: Certificate verification (optional)
            authenticator: IBM Cloud SDK authenticator (optional)
            local: Whether to use local mode (default: False, auto-detected from instance_url)
            execution_context: ExecutionContext for runs-on mode (optional)
            session: Pre-configured AgenticSession (optional)
            **kwargs: Additional arguments passed to OpenAIEmbeddings
```

### Supported Methods

All `OpenAIEmbeddings` methods are supported:

- `embed_query(text)` - Embed a single text query
- `embed_documents(texts)` - Embed multiple documents
- `aembed_query(text)` - Async embed a single text query
- `aembed_documents(texts)` - Async embed multiple documents

### Class Methods

- `from_instance_credentials(instance_url, api_key, model, **kwargs)` - Create from instance credentials (standalone/runs-elsewhere)
- `from_execution_context(execution_context, model, **kwargs)` - Create from execution context (runtime/runs-on)
- `from_session(session, model, **kwargs)` - Create from AgenticSession
- `from_runnable_config(config, model, **kwargs)` - Create from RunnableConfig (runtime/runs-on)

### Embedding Model IDs

Use the model ID formats returned by the WxO `/models` endpoint:

```
provider/model-name
```

Examples:
- `openai/text-embedding-3-small`
- `openai/text-embedding-3-large`
- `openai/text-embedding-ada-002`
- `watsonx/ibm/slate-30m-english-rtrvr`

### Error Handling

```python
from ibm_watsonx_orchestrate_sdk.langchain import WxOEmbeddings

try:
    embeddings = WxOEmbeddings(
        model="openai/text-embedding-3-small",
        api_key="your-api-key",
        wxo_base_url="https://your-instance.cloud.ibm.com"
    )
    result = embeddings.embed_query("Hello!")
except TypeError as e:
    print(f"Missing required parameter: {e}")
except ValueError as e:
    print(f"Invalid parameter value: {e}")
except Exception as e:
    print(f"Error: {e}")
```

## License

This package is part of IBM watsonx Orchestrate and follows the same licensing terms.

## Support

For issues, questions, or contributions, please refer to the main wxo-clients repository.