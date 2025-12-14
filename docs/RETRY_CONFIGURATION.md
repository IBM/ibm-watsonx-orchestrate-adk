# Retry Configuration Guide for IBM watsonx Orchestrate ADK

## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Configuration Methods](#configuration-methods)
- [Usage Examples](#usage-examples)
- [Integration with ADK Features](#integration-with-adk-features)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Reference](#reference)

## Overview

The IBM watsonx Orchestrate ADK includes a robust retry mechanism that automatically handles transient failures, network issues, and temporary service unavailabilities. This guide explains how to configure the retry functionality using environment variables and code-based configuration.

### Key Features

- **Automatic Retry with Exponential Backoff**: Failed requests are automatically retried with increasing wait times
- **Environment Variable Configuration**: Configure retry behavior globally via environment variables
- **Smart Error Classification**: Only retries errors that are likely to succeed on retry
- **Jitter for Load Distribution**: Prevents thundering herd problem with randomized retry timing
- **Flexible Configuration**: Override global settings per-client or per-operation

## Quick Start

### Using Environment Variables

1. Copy the example configuration file:
   ```bash
   cp .env.example .env
   ```

2. Set your retry preferences in `.env`:
   ```bash
   # Retry Configuration
   ADK_MAX_RETRIES=3
   ADK_RETRY_INTERVAL=1000
   ADK_TIMEOUT=300
   ```

3. Your ADK client will automatically use these settings:
   ```python
   from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient
   
   # Automatically uses environment variable configuration
   client = BaseAPIClient(base_url="https://api.example.com")
   ```

### Using Code-Based Configuration

```python
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient

# Override environment variables with explicit configuration
client = BaseAPIClient(
    base_url="https://api.example.com",
    max_retries=5,           # Override ADK_MAX_RETRIES
    retry_interval=2000,     # Override ADK_RETRY_INTERVAL (milliseconds)
    timeout=600              # Override ADK_TIMEOUT (seconds)
)
```

## Environment Variables

### Core Retry Settings

| Variable | Default | Description | Example Values |
|----------|---------|-------------|----------------|
| `ADK_MAX_RETRIES` | `3` | Maximum number of retry attempts | `0` (disable), `1-5` (typical) |
| `ADK_RETRY_INTERVAL` | `1000` | Initial retry interval in milliseconds | `500` (fast), `2000` (conservative) |
| `ADK_TIMEOUT` | `300` | Request timeout in seconds | `30` (fast ops), `600` (long ops) |

### Advanced Settings

| Variable | Default | Description | Range |
|----------|---------|-------------|-------|
| `ADK_BACKOFF_MULTIPLIER` | `2.0` | Exponential backoff multiplier | `1.5` - `3.0` |
| `ADK_JITTER_PERCENTAGE` | `0.2` | Randomization factor for retry timing | `0.0` - `0.5` |

## Configuration Methods

### Method 1: Global Configuration via Environment

Set environment variables before running your application:

```bash
export ADK_MAX_RETRIES=5
export ADK_RETRY_INTERVAL=2000
export ADK_TIMEOUT=600

python your_app.py
```

### Method 2: Using a .env File

Create a `.env` file in your project root:

```env
# Production configuration
ADK_MAX_RETRIES=3
ADK_RETRY_INTERVAL=1000
ADK_TIMEOUT=300
ADK_BACKOFF_MULTIPLIER=2.0
ADK_JITTER_PERCENTAGE=0.2
```

Load with python-dotenv:
```python
from dotenv import load_dotenv
load_dotenv()

# Now environment variables are loaded
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient
client = BaseAPIClient(base_url="https://api.example.com")
```

### Method 3: Per-Client Configuration

Override global settings for specific clients:

```python
# Fast client for quick operations
fast_client = BaseAPIClient(
    base_url="https://api.example.com",
    max_retries=1,
    retry_interval=500,
    timeout=30
)

# Patient client for long-running operations
patient_client = BaseAPIClient(
    base_url="https://api.example.com",
    max_retries=5,
    retry_interval=3000,
    timeout=600
)
```

### Method 4: Custom Decorator Configuration

For fine-grained control over specific functions:

```python
from ibm_watsonx_orchestrate.client.retry_handler import retry_with_backoff

@retry_with_backoff(
    max_retries=10,
    retry_interval=5000,
    context_name="critical_operation"
)
def critical_api_call():
    # Your critical API operation
    pass
```

## Usage Examples

### Example 1: Development Environment

Fail fast with minimal retries for quick feedback:

```env
# .env.development
ADK_MAX_RETRIES=1
ADK_RETRY_INTERVAL=500
ADK_TIMEOUT=30
```

### Example 2: Production Environment

Balanced configuration for reliability:

```env
# .env.production
ADK_MAX_RETRIES=3
ADK_RETRY_INTERVAL=1000
ADK_TIMEOUT=300
```

### Example 3: High-Reliability Operations

Maximum resilience for critical operations:

```env
# .env.critical
ADK_MAX_RETRIES=5
ADK_RETRY_INTERVAL=2000
ADK_TIMEOUT=600
ADK_BACKOFF_MULTIPLIER=2.5
```

### Example 4: Document Processing

Long timeout for document-heavy operations:

```python
import os
os.environ['ADK_TIMEOUT'] = '900'  # 15 minutes

from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient

client = BaseAPIClient(base_url="https://api.example.com")
# Process large documents with extended timeout
response = client._post("/process-document", data=document_data)
```

## Integration with ADK Features

### With Agent Builder

```python
from ibm_watsonx_orchestrate.agent_builder import Agent
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient

# Configure retry for agent operations
os.environ['ADK_MAX_RETRIES'] = '3'
os.environ['ADK_TIMEOUT'] = '120'

agent_client = AgentClient(base_url="https://api.example.com")
agent = Agent(name="my_agent", client=agent_client)
```

### With Flow Builder

```python
from ibm_watsonx_orchestrate.flow_builder import Flow

# Flows inherit retry configuration from environment
flow = Flow(name="my_flow")
# Operations within the flow will use ADK retry settings
```

### With YAML Configuration

In your agent/flow YAML files:

```yaml
nodes:
  - id: document_processor
    type: agent
    error_handler_config:
      max_retries: 5          # Overrides ADK_MAX_RETRIES
      retry_interval: 2000    # Overrides ADK_RETRY_INTERVAL
      error_message: "Document processing failed after multiple attempts"
```

## Best Practices

### 1. Choose Configuration by Environment

```python
import os

# Detect environment
env = os.getenv('ENVIRONMENT', 'development')

if env == 'development':
    os.environ['ADK_MAX_RETRIES'] = '1'
    os.environ['ADK_TIMEOUT'] = '30'
elif env == 'production':
    os.environ['ADK_MAX_RETRIES'] = '3'
    os.environ['ADK_TIMEOUT'] = '300'
```

### 2. Log Configuration on Startup

```python
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"Retry Configuration:")
logger.info(f"  MAX_RETRIES: {os.getenv('ADK_MAX_RETRIES', '3')}")
logger.info(f"  RETRY_INTERVAL: {os.getenv('ADK_RETRY_INTERVAL', '1000')}ms")
logger.info(f"  TIMEOUT: {os.getenv('ADK_TIMEOUT', '300')}s")
```

### 3. Test Your Configuration

```python
# test_retry_config.py
import os
import unittest
from unittest.mock import patch, Mock
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient

class TestRetryConfiguration(unittest.TestCase):
    
    @patch.dict(os.environ, {'ADK_MAX_RETRIES': '5'})
    def test_environment_configuration(self):
        client = BaseAPIClient(base_url="http://test.com")
        self.assertEqual(client.max_retries, 5)
    
    def test_code_overrides_environment(self):
        client = BaseAPIClient(base_url="http://test.com", max_retries=10)
        self.assertEqual(client.max_retries, 10)
```

### 4. Monitor Retry Behavior

```python
import logging

# Enable debug logging to see retry attempts
logging.getLogger('ibm_watsonx_orchestrate').setLevel(logging.DEBUG)
```

## Troubleshooting

### Issue: Retries Not Working

**Check environment variables are set:**
```python
import os
print(f"ADK_MAX_RETRIES: {os.getenv('ADK_MAX_RETRIES')}")
print(f"ADK_RETRY_INTERVAL: {os.getenv('ADK_RETRY_INTERVAL')}")
```

**Verify client configuration:**
```python
client = BaseAPIClient(base_url="https://api.example.com")
print(f"Max retries: {client.max_retries}")
print(f"Retry interval: {client.retry_interval}")
print(f"Timeout: {client.timeout}")
```

### Issue: Operations Timing Out

**Increase timeout for long operations:**
```env
ADK_TIMEOUT=600  # 10 minutes
```

Or per-client:
```python
client = BaseAPIClient(base_url=url, timeout=600)
```

### Issue: Too Many Retries Slowing Down Development

**Reduce retries in development:**
```env
# .env.development
ADK_MAX_RETRIES=0  # Disable retries
ADK_TIMEOUT=10     # Quick timeout
```

### Issue: Rate Limiting (429 errors)

The retry mechanism automatically handles rate limits with extended backoff. To further customize:

```env
ADK_RETRY_INTERVAL=5000     # Start with 5 second wait
ADK_BACKOFF_MULTIPLIER=3.0  # Triple wait time each retry
```

## Reference

### Retryable Errors

The following errors are automatically retried:
- Network errors: `requests.Timeout`, `requests.ConnectionError`
- Server errors: HTTP 500, 502, 503, 504
- Rate limiting: HTTP 429

### Non-Retryable Errors

These errors fail immediately without retry:
- Client errors: HTTP 400, 401, 403, 404, 422
- Authentication failures
- Invalid request data

### Retry Timing Formula

The wait time between retries is calculated as:
```
wait_time = retry_interval * (backoff_multiplier ^ attempt) * (1 ± jitter_percentage)
```

Example with defaults:
- Attempt 1: ~1 second
- Attempt 2: ~2 seconds  
- Attempt 3: ~4 seconds

### Environment Variable Precedence

1. Code-based configuration (highest priority)
2. Environment variables
3. Default values (lowest priority)

### Related Documentation

- [Retry Handling Technical Details](./RETRY_HANDLING.md)
- [BaseAPIClient API Reference](../src/ibm_watsonx_orchestrate/client/base_api_client.py)
- [ADK Main Documentation](https://developer.watson-orchestrate.ibm.com)

## Support

For issues or questions:
1. Check the [troubleshooting](#troubleshooting) section
2. Review debug logs with `LOG_LEVEL=DEBUG`
3. Create an issue on GitHub with:
   - Your configuration (environment variables)
   - Error messages and logs
   - Expected vs. actual behavior