# IBM watsonx Orchestrate LangChain Integration

A lightweight LangChain integration package that provides drop-in replacements for `ChatOpenAI` and `OpenAIEmbeddings`, routing all LLM and embedding calls through IBM watsonx Orchestrate's AI Gateway for enhanced security, centralized model management, and enterprise-grade features.

## Features

- ✅ **Automatic authentication** with token refresh
- ✅ **Dual mode support**: WxO Runtime (Agent running in WxO) and Standalone (direct API usage for LLM calls)
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

### Runtime Mode (within WxO)

When running inside a WxO runtime, credentials are automatically provided:

```python
from ibm_watsonx_orchestrate_sdk.langchain import ChatWxO
from langgraph.graph.state import RunnableConfig

def create_agent(config: RunnableConfig):
    llm = ChatWxO.from_config(
        config=config,
        model="virtual-model/watsonx/meta-llama/llama-3-2-90b-vision-instruct",
        temperature=0.2
    )
    
    response = llm.invoke("What is the capital of France?")
    print(response.content)
    
    return llm
```

### Standalone Mode (Direct API Usage)

For standalone scripts or applications outside WxO runtime:

```python
from ibm_watsonx_orchestrate_sdk.langchain import ChatWxO

llm = ChatWxO(
    model="virtual-model/watsonx/meta-llama/llama-3-2-90b-vision-instruct",
    api_key="your-wxo-api-key",
    wxo_base_url="https://your-instance.cloud.ibm.com",
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

llm = ChatWxO(
    model="virtual-model/watsonx/ibm/granite-3-8b-instruct",
    api_key="your-api-key",
    wxo_base_url="https://your-instance.cloud.ibm.com"
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
llm = ChatWxO(
    model="watsonx/meta-llama/llama-3-2-90b-vision-instruct",
    api_key="your-api-key",
    wxo_base_url="https://your-instance.cloud.ibm.com",
    
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

llm = ChatWxO(
    model="watsonx/meta-llama/llama-3-2-90b-vision-instruct",
    api_key="your-wxo-api-key",
    wxo_base_url="https://your-instance.cloud.ibm.com",
    temperature=0.7
)
```

**Key differences:**
1. Import from `ibm_watsonx_orchestrate_sdk.langchain` instead of `langchain_openai`
2. Use `ChatWxO` instead of `ChatOpenAI`
3. Provide `wxo_base_url` (your WxO instance URL)
4. Use WxO model IDs (format: `provider/model-name` or `provider/creator/model-name`)
5. All other parameters and methods remain the same!

## API Reference

### ChatWxO

```python
class ChatWxO(ChatOpenAI):
    """WatsonX Orchestrate LangChain Chat Model Wrapper."""
    
    def __init__(
        self,
        model: str,
        agent_api_key: str | None = None,
        user_id: str | None = None,
        tenant_id: str | None = None,
        api_key: str | None = None,
        wxo_base_url: str | None = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize ChatWxO wrapper.
        
        Args:
            model: Model ID (e.g., "virtual-model/watsonx/...")
            agent_api_key: Service-level API key (runtime mode)
            user_id: User identifier (runtime mode)
            tenant_id: Tenant identifier (runtime mode)
            api_key: WxO API key (standalone mode)
            wxo_base_url: WxO instance URL (required)
            **kwargs: Additional ChatOpenAI parameters
        """
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

- `from_config(config, model, **kwargs)` - Create from RunnableConfig (for LangGraph)

## Authentication Modes

### Runtime Mode (within WxO)

Credentials are automatically injected by the WxO runtime:

```python
def create_agent(config: RunnableConfig):
    llm = ChatWxO.from_config(config, model="virtual-model/...")
    # agent_api_key, user_id, tenant_id automatically provided
```

### Standalone Mode (Direct API)

Provide your WxO API key for automatic token management:

```python
llm = ChatWxO(
    model="virtual-model/...",
    api_key="your-wxo-api-key",
    wxo_base_url="https://your-instance.cloud.ibm.com"
)
# Token automatically generated and refreshed as needed
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

#### Runtime Mode (within WxO)

```python
from ibm_watsonx_orchestrate_sdk.langchain import WxOEmbeddings
from langgraph.graph.state import RunnableConfig

def create_agent(config: RunnableConfig):
    embeddings = WxOEmbeddings.from_config(
        config=config,
        model="openai/text-embedding-3-small"
    )
    
    # Embed a single query
    query_embedding = embeddings.embed_query("What is machine learning?")
    print(f"Embedding dimension: {len(query_embedding)}")
    
    return embeddings
```

#### Standalone Mode (Direct API Usage)

```python
from ibm_watsonx_orchestrate_sdk.langchain import WxOEmbeddings

embeddings = WxOEmbeddings(
    model="openai/text-embedding-3-small",
    api_key="your-wxo-api-key",
    wxo_base_url="https://your-instance.cloud.ibm.com"
)

# Embed a single query
query_embedding = embeddings.embed_query("What is machine learning?")
print(f"Embedding dimension: {len(query_embedding)}")
```

### Usage Examples

#### Basic Embeddings

```python
from ibm_watsonx_orchestrate_sdk.langchain import WxOEmbeddings

embeddings = WxOEmbeddings(
    model="openai/text-embedding-3-small",
    api_key="your-api-key",
    wxo_base_url="https://your-instance.cloud.ibm.com"
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
    embeddings = WxOEmbeddings(
        model="openai/text-embedding-3-small",
        api_key="your-api-key",
        wxo_base_url="https://your-instance.cloud.ibm.com"
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
embeddings = WxOEmbeddings(
    model="openai/text-embedding-3-small",
    api_key="your-api-key",
    wxo_base_url="https://your-instance.cloud.ibm.com"
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
embeddings = WxOEmbeddings(
    model="openai/text-embedding-3-small",
    api_key="your-api-key",
    wxo_base_url="https://your-instance.cloud.ibm.com"
)

llm = ChatWxO(
    model="watsonx/ibm/granite-3-8b-instruct",
    api_key="your-api-key",
    wxo_base_url="https://your-instance.cloud.ibm.com"
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

embeddings = WxOEmbeddings(
    model="openai/text-embedding-3-small",
    api_key="your-api-key",
    wxo_base_url="https://your-instance.cloud.ibm.com"
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

embeddings = WxOEmbeddings(
    model="openai/text-embedding-3-small",
    api_key="your-wxo-api-key",
    wxo_base_url="https://your-instance.cloud.ibm.com"
)
```

**Key differences:**
1. Import from `ibm_watsonx_orchestrate_sdk.langchain` instead of `langchain_openai`
2. Use `WxOEmbeddings` instead of `OpenAIEmbeddings`
3. Provide `wxo_base_url` (your WxO instance URL)
4. Use WxO model IDs (format: `provider/model-name`)
5. All other parameters and methods remain the same!

### API Reference - WxOEmbeddings

```python
class WxOEmbeddings(OpenAIEmbeddings):
    """WatsonX Orchestrate LangChain Embeddings Wrapper."""
    
    def __init__(
        self,
        model: str,
        agent_api_key: str | None = None,
        user_id: str | None = None,
        tenant_id: str | None = None,
        api_key: str | None = None,
        wxo_base_url: str | None = None,
        iam_url: str | None = None,
        auth_type: str | None = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize WxOEmbeddings wrapper.
        
        Args:
            model: Model ID (e.g., "openai/text-embedding-3-small")
            agent_api_key: Service-level API key (runtime mode)
            user_id: User identifier (runtime mode)
            tenant_id: Tenant identifier (runtime mode)
            api_key: WxO API key (standalone mode)
            wxo_base_url: WxO instance URL (required)
            iam_url: IAM URL for authentication (optional)
            auth_type: Authentication type (optional)
            **kwargs: Additional OpenAIEmbeddings parameters
        """
```

### Supported Methods

All `OpenAIEmbeddings` methods are supported:

- `embed_query(text)` - Embed a single text query
- `embed_documents(texts)` - Embed multiple documents
- `aembed_query(text)` - Async embed a single text query
- `aembed_documents(texts)` - Async embed multiple documents

### Class Methods

- `from_config(config, model, **kwargs)` - Create from RunnableConfig (for LangGraph)

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