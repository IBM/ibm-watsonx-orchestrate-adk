# WxO LangChain Integration Tests

Integration tests for ChatWxO and WxOEmbeddings LangChain wrappers in standalone mode (runs-elsewhere).

## Overview

These tests verify end-to-end functionality of ChatWxO and WxOEmbeddings by making real API calls to WxO instances (local Developer Edition and/or SaaS) through the AI Gateway using the agentic-sdk client.

## Prerequisites

### Local Testing (Developer Edition)
- Local WxO instance running (wxo-server + ai-gateway)
- Valid API key for local instance
- At least one model configured and accessible

### SaaS Testing
- Access to a SaaS WxO instance
- Valid API key with model access
- Network connectivity to the SaaS instance

## Setup

### 1. Install Dependencies

```bash
# From the integration test directory
pip install -r requirements.txt

# Or install the package from source
cd ../../../packages/agentic-sdk
pip install -e .
```

### 2. Configure Environment

Copy the template and fill in your credentials:

```bash
cp template.env .env
```

Edit `.env` with your actual values:

```bash
# Local WxO Instance
LOCAL_WXO_API_KEY=your-local-api-key
LOCAL_INSTANCE_URL=http://localhost:4321

# SaaS WxO Instance
SAAS_WXO_API_KEY=your-saas-api-key
SAAS_INSTANCE_URL=https://your-instance.cloud.ibm.com

# Test Models (adjust based on available models)
LOCAL_CHAT_MODEL_1=virtual-model/watsonx/ibm/granite-3-8b-instruct
LOCAL_CHAT_MODEL_2=virtual-model/watsonx/meta-llama/llama-3-2-90b-vision-instruct

SAAS_CHAT_MODEL_1=virtual-model/watsonx/ibm/granite-3-8b-instruct
SAAS_CHAT_MODEL_2=virtual-model/openai/gpt-4o
```

### 3. Verify Model IDs

Make sure the model IDs in your `.env` match models available in your WxO instances. You can check available models via:

```bash
# For local instance
curl http://localhost:4321/api/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"

# For SaaS instance
curl https://your-instance.cloud.ibm.com/api/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Running Tests

### Run ChatWxO Tests

```bash
python standalone_chat_models_test.py
```

This will:
1. Load configuration from `.env`
2. Test each configured chat model in each environment
3. Display results with response content and metadata
4. Print a summary of passed/failed tests

### Run WxOEmbeddings Tests

```bash
python standalone_embeddings_test.py
```

This will:
1. Load configuration from `.env`
2. Test each configured embedding model in each environment
3. Display embedding dimensions and similarity scores
4. Print a summary of passed/failed tests

### Run All Tests

```bash
python standalone_chat_models_test.py && python standalone_embeddings_test.py
```

### Example Output

```
================================================================================
ChatWxO Integration Tests - Standalone Mode
================================================================================
Started at: 2024-01-15 10:30:00

================================================================================
Testing: Local - virtual-model/watsonx/ibm/granite-3-8b-instruct
================================================================================
Base URL: http://localhost:4321
Question: What is the capital of France? Answer in one sentence.
--------------------------------------------------------------------------------
✅ SUCCESS (1.23s)

Response:
The capital of France is Paris.

Metadata:
  - Finish Reason: stop
  - Token Usage: {'input_tokens': 15, 'output_tokens': 8, 'total_tokens': 23}

================================================================================
Test Summary
================================================================================

Total Tests: 4
✅ Passed: 4
❌ Failed: 0

Detailed Results:
--------------------------------------------------------------------------------
✅ PASS | Local      | virtual-model/watsonx/ibm/granite-3-8b-instruct
       Duration: 1.23s
✅ PASS | Local      | virtual-model/watsonx/meta-llama/llama-3-2-90b-vision-instruct
       Duration: 2.45s
✅ PASS | SaaS       | virtual-model/watsonx/ibm/granite-3-8b-instruct
       Duration: 1.87s
✅ PASS | SaaS       | virtual-model/openai/gpt-4o
       Duration: 1.56s

================================================================================
Completed at: 2024-01-15 10:30:15
================================================================================
```

## Test Configuration

### Partial Configuration

You can configure only one environment (local or SaaS) if you don't have access to both:

```bash
# Only local tests
LOCAL_WXO_API_KEY=your-key
LOCAL_WXO_BASE_URL=http://localhost:4321
LOCAL_CHAT_MODEL_1=virtual-model/watsonx/ibm/granite-3-8b-instruct

# Leave SaaS variables empty or commented out
# SAAS_WXO_API_KEY=
# SAAS_WXO_BASE_URL=
```

The test script will skip unconfigured environments with a warning.

### Single Model Testing

You can test with just one model per environment by leaving the second model variable empty:

```bash
LOCAL_CHAT_MODEL_1=virtual-model/watsonx/ibm/granite-3-8b-instruct
# LOCAL_CHAT_MODEL_2=  # Leave empty to skip
```

## What Gets Tested

### ChatWxO Tests (standalone_chat_models_test.py)

For each configured chat model in each environment, the following tests are run:

#### 1. Basic Invoke
Tests standard synchronous invocation:
- ✅ **Initialization**: Creates ChatWxO instance with API key and base URL
- ✅ **Authentication**: Verifies API key is accepted and token is generated
- ✅ **Model Routing**: Confirms request is routed through AI Gateway to correct model
- ✅ **Response Handling**: Validates response format and content
- ✅ **Metadata**: Checks token usage and finish reason are present

#### 2. Bind Tools
Tests tool/function calling capabilities:
- ✅ **Tool Binding**: Binds Pydantic models as tools (GetWeather, Calculator)
- ✅ **Tool Invocation**: Sends query that should trigger tool use
- ✅ **Tool Calls**: Validates tool_calls are present in response
- ✅ **Tool Schema**: Confirms tool schemas are properly formatted

#### 3. Structured Output
Tests structured output with Pydantic schemas:
- ✅ **Schema Binding**: Uses `with_structured_output()` with JokeResponse schema
- ✅ **Structured Response**: Validates response matches Pydantic model
- ✅ **Field Validation**: Checks setup, punchline, and optional rating fields
- ✅ **Type Safety**: Confirms response is properly typed

#### 4. Batch Processing
Tests batch invocation of multiple prompts:
- ✅ **Batch Invoke**: Sends multiple questions in a single batch
- ✅ **Response Count**: Validates correct number of responses returned
- ✅ **Individual Responses**: Checks each response is valid
- ✅ **Performance**: Measures batch processing time

#### 5. Async Streaming
Tests asynchronous streaming capabilities:
- ✅ **Async Stream**: Uses `astream()` for async token streaming
- ✅ **Chunk Collection**: Collects and concatenates stream chunks
- ✅ **Chunk Count**: Validates multiple chunks are received
- ✅ **Complete Response**: Verifies full response is assembled correctly

#### 6. Logprobs
Tests log probability output:
- ✅ **Logprobs Parameter**: Sets `logprobs=True` and `top_logprobs=3`
- ✅ **Logprobs Data**: Validates logprobs are present in response metadata
- ✅ **Token Details**: Checks logprob data for each token
- ✅ **Top Alternatives**: Verifies top alternative tokens are included

**Total ChatWxO Tests Per Model**: 6 tests × number of models × number of environments

### WxOEmbeddings Tests (standalone_embeddings_test.py)

For each configured embedding model in each environment, the following tests are run:

#### 1. Embed Query
Tests basic query embedding:
- ✅ **Initialization**: Creates WxOEmbeddings instance with API key and base URL
- ✅ **Authentication**: Verifies API key is accepted and token is generated
- ✅ **Query Embedding**: Embeds a single text query
- ✅ **Vector Validation**: Validates embedding is a list of floats
- ✅ **Dimension Check**: Confirms embedding has expected dimensionality

#### 2. Embed Documents
Tests batch document embedding:
- ✅ **Multiple Documents**: Embeds a list of text documents
- ✅ **Batch Processing**: Validates all documents are embedded
- ✅ **Consistent Dimensions**: Confirms all embeddings have same dimension
- ✅ **Vector Quality**: Checks each embedding is valid

#### 3. Async Embed Query
Tests asynchronous query embedding:
- ✅ **Async Operation**: Uses `aembed_query()` for async embedding
- ✅ **Token Refresh**: Validates token is refreshed before request
- ✅ **Response Format**: Confirms async response matches sync format
- ✅ **Performance**: Measures async operation time

#### 4. Async Embed Documents
Tests asynchronous batch embedding:
- ✅ **Async Batch**: Uses `aembed_documents()` for async batch embedding
- ✅ **Multiple Documents**: Embeds multiple documents asynchronously
- ✅ **Dimension Consistency**: Validates all embeddings have same dimension
- ✅ **Async Performance**: Measures batch async operation time

#### 5. Similarity Search
Tests embeddings for semantic similarity:
- ✅ **Query + Documents**: Embeds query and document corpus
- ✅ **Cosine Similarity**: Calculates similarity scores
- ✅ **Ranking**: Identifies most similar document to query
- ✅ **Semantic Understanding**: Validates embeddings capture meaning

**Total WxOEmbeddings Tests Per Model**: 5 tests × number of models × number of environments

## Known Issues

### Async Event Loop Cleanup Warning (WxOEmbeddings SaaS Tests)

When running async embedding tests (particularly `test_aembed_documents`) against SaaS environments, you may see a `RuntimeError: Event loop is closed` stack trace printed to the console after the test completes successfully:

```
Task exception was never retrieved
future: <Task finished name='Task-17' coro=<AsyncClient.aclose() done> exception=RuntimeError('Event loop is closed')>
Traceback (most recent call last):
  ...
  File "asyncio/base_events.py", line 545, in _check_closed
    raise RuntimeError('Event loop is closed')
RuntimeError: Event loop is closed
✅ SUCCESS (0.88s)
Documents embedded: 3
Embedding dimension: 768
```

**Why This Happens:**

1. Each async test uses `asyncio.run()` which creates a new event loop, runs the test, and immediately closes the loop
2. The underlying httpx `AsyncClient` (used by the OpenAI SDK) schedules cleanup tasks in the background
3. These cleanup tasks attempt to run after `asyncio.run()` has already closed the event loop

**Impact:**

- ✅ **Tests pass successfully** - The embedding operation completes before the error occurs
- ✅ **Embeddings are correct** - All embedding vectors are returned properly
- ✅ **No data loss** - The error happens during resource cleanup only, not during the actual operation
- ⚠️ **Cosmetic only** - The stack trace is printed but doesn't affect functionality

**Why Not Fixed:**

This is a known limitation of using `asyncio.run()` with libraries that have background cleanup tasks. The error cannot be suppressed with standard warning filters because it's printed directly by asyncio's exception handler. Fixing it would require restructuring the test runner to use a single event loop for all async tests, which would be a significant refactoring and the tests would no longer be as isolated.


## Troubleshooting

### Connection Errors

```
❌ FAILED
Error: Error connecting to target API
```

**Solutions:**
- Verify the base URL is correct and accessible
- Check that wxo-server and ai-gateway are running (for local)
- Verify network connectivity (for SaaS)

### Authentication Errors

```
❌ FAILED  
Error: 401 Unauthorized
```

**Solutions:**
- Verify your API key is correct
- Check that the API key has not expired
- Ensure the API key has access to the specified models

### Model Not Found

```
❌ FAILED
Error: Model not found: virtual-model/...
```

**Solutions:**
- Verify the model ID format is correct
- Check that the model is configured in your WxO instance
- Use the `/models` endpoint to see available models

### Invalid URL Format

```
❌ FAILED
Error: Invalid URL Format. URL must start with 'https://'
```

**Solutions:**
- For production/SaaS: Use `https://` URLs
- For local development: Use `http://localhost:4321` (automatically allowed)

## Adding to CI/CD

To run these tests in CI/CD pipelines:

1. Store credentials as secrets/environment variables
2. Ensure WxO instances are accessible from CI environment
3. Run tests as part of integration test suite:

```bash
# In CI pipeline
export LOCAL_WXO_API_KEY=$CI_LOCAL_API_KEY
export LOCAL_WXO_BASE_URL=$CI_LOCAL_BASE_URL
# ... other variables

python tests/integration_tests/langchain/standalone_chat_models_test.py
python tests/integration_tests/langchain/standalone_embeddings_test.py
```

## Notes

- These are **real API tests** that make actual calls to LLMs
- Tests may incur costs based on token usage
- Response times vary based on model and network latency
- Tests require active WxO instances with configured models

## Resources

- Main Package README: `packages/agentic-sdk/ibm_watsonx_orchestrate_sdk/langchain/README.md`