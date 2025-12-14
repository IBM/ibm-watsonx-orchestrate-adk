# Retry Handling in IBM watsonx Orchestrate ADK

## Overview

The ADK includes an automatic retry mechanism with exponential backoff to handle transient errors like timeouts, network issues, and temporary server failures. This document explains how the retry system works, how to configure it, and how to troubleshoot issues.

## Table of Contents

- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Error Classification](#error-classification)
- [Logging and Observability](#logging-and-observability)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## Key Features

✅ **Automatic Retries**: Transient errors are automatically retried without user intervention  
✅ **Exponential Backoff**: Wait time doubles with each retry (1s → 2s → 4s)  
✅ **Jitter**: Random variation (±20%) prevents thundering herd  
✅ **Smart Error Classification**: Only retries errors that are likely to succeed on retry  
✅ **Rate Limit Handling**: Special handling for HTTP 429 errors with extended backoff  
✅ **Configurable**: Per-node, per-agent, or global retry settings  
✅ **Comprehensive Logging**: Detailed logs for debugging and monitoring  

## Quick Start

### Default Behavior (No Configuration Required)

The retry mechanism works automatically with sensible defaults:

```python
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient

# Uses default settings: max_retries=3, retry_interval=1000ms, timeout=300s
client = BaseAPIClient(base_url="https://api.example.com")

# Automatic retry on timeout/500 errors
response = client._get("/api/endpoint")
```

**Default values:**
- `max_retries`: 3 attempts
- `retry_interval`: 1000ms (1 second)
- `timeout`: 300 seconds (5 minutes)
- `backoff_multiplier`: 2.0
- `jitter_percentage`: 0.2 (±20%)

### Configuring Retry Settings in YAML

You can configure retry behavior in your agent/flow YAML files using `error_handler_config`:

```yaml
nodes:
  - id: information_gatherer_agent
    name: "Information Gatherer"
    type: agent
    agent_id: information_gatherer_agent
    error_handler_config:
      max_retries: 5              # Maximum retry attempts
      retry_interval: 2000         # Initial interval in milliseconds
      error_message: "Failed to gather information after 5 retries. Please try again later."
```

### Configuring Retry Settings in Code

```python
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient

# Custom retry configuration
client = BaseAPIClient(
    base_url="https://api.example.com",
    max_retries=5,           # Try up to 5 times
    retry_interval=2000,     # Start with 2 second wait
    timeout=120              # 2 minute timeout per request
)
```

## How It Works

### Retry Flow

```
┌─────────────────┐
│ Make Request    │
└────────┬────────┘
         │
         ▼
    ┌────────┐
    │Success?│──Yes──▶ Return Response
    └───┬────┘
        │ No
        ▼
┌────────────────┐
│ Retryable      │──No──▶ Raise Exception (Fail Fast)
│ Error?         │
└───┬────────────┘
    │ Yes
    ▼
┌────────────────┐
│ Max Retries    │──Yes──▶ Raise Exception
│ Exceeded?      │
└───┬────────────┘
    │ No
    ▼
┌────────────────┐
│ Calculate      │
│ Backoff Time   │◀──────┐
│ (Exponential + │       │
│  Jitter)       │       │
└───┬────────────┘       │
    │                    │
    ▼                    │
┌────────────────┐       │
│ Wait           │       │
└───┬────────────┘       │
    │                    │
    ▼                    │
┌────────────────┐       │
│ Make Request   │       │
│ Again          │       │
└───┬────────────┘       │
    │                    │
    ▼                    │
┌────────────────┐       │
│ Success?       │──No───┘
└───┬────────────┘
    │ Yes
    ▼
Return Response
```

### Exponential Backoff with Jitter

The retry mechanism uses exponential backoff to prevent overwhelming servers:

**Example with 3 retries, 1000ms interval:**

| Attempt | Base Wait | Jitter Range (±20%) | Actual Wait |
|---------|-----------|---------------------|-------------|
| 1       | 1s        | 0.8s - 1.2s        | ~1s         |
| 2       | 2s        | 1.6s - 2.4s        | ~2s         |
| 3       | 4s        | 3.2s - 4.8s        | ~4s         |

**Total time before giving up:** ~7 seconds (plus request time)

### Rate Limit Special Handling

HTTP 429 (Rate Limit Exceeded) errors receive **double** the normal backoff time:

```
Normal retry:     1s → 2s → 4s
Rate limit retry: 2s → 4s → 8s
```

This gives rate-limited services more time to recover.

## Configuration

### Configuration Hierarchy

Settings are applied in this order (later overrides earlier):

1. **Global defaults** (hardcoded in ADK)
2. **BaseAPIClient constructor parameters**
3. **YAML `error_handler_config`** (per-node)

### YAML Configuration

```yaml
error_handler_config:
  max_retries: 3            # Number of retry attempts (0 = no retries)
  retry_interval: 1000      # Initial wait time in milliseconds
  error_message: "Custom error message shown to users"
```

**Example: Different settings for different agents**

```yaml
nodes:
  # Fast-failing agent with minimal retries
  - id: validation_agent
    type: agent
    error_handler_config:
      max_retries: 1
      retry_interval: 500
      error_message: "Validation failed. Please check your input."
  
  # Patient agent for long-running operations
  - id: document_processor_agent
    type: agent
    error_handler_config:
      max_retries: 5
      retry_interval: 3000
      error_message: "Document processing timed out after 5 retries. The document may be too large."
```

### Code Configuration

```python
from ibm_watsonx_orchestrate.client.retry_handler import retry_with_backoff

# Custom decorator for specific functions
@retry_with_backoff(
    max_retries=5,
    retry_interval=2000,
    backoff_multiplier=2.0,
    jitter_percentage=0.2,
    context_name="custom_operation"
)
def my_function():
    # Your code here
    pass
```

## Error Classification

### Retryable Errors (Automatically Retried)

✅ **Network/Transport Errors:**
- `requests.Timeout`
- `requests.ConnectionError`

✅ **Server Errors (5xx):**
- `500 Internal Server Error`
- `502 Bad Gateway`
- `503 Service Unavailable`
- `504 Gateway Timeout`
- Any 5xx status code

✅ **Rate Limiting:**
- `429 Too Many Requests` (with extended backoff)

### Non-Retryable Errors (Fail Fast)

❌ **Client Errors (4xx):**
- `400 Bad Request`
- `401 Unauthorized`
- `403 Forbidden`
- `404 Not Found`
- `422 Unprocessable Entity`
- Any 4xx except 429

❌ **Success/Redirect Codes:**
- `2xx` Success codes
- `3xx` Redirect codes

❌ **Unknown Errors:**
- Any exception not explicitly classified as retryable

**Why fail fast on client errors?**  
Client errors (4xx) indicate problems with the request itself (bad data, authentication, etc.). Retrying won't help because the server will reject the same request again.

## Logging and Observability

### Log Levels

| Level   | When                        | Example Message                                      |
|---------|-----------------------------|------------------------------------------------------|
| INFO    | Successful retry            | `Retry 2/3 succeeded for operation after 2.1s wait` |
| WARNING | Retry attempt in progress   | `Retry 1/3 for operation after error: Timeout`      |
| ERROR   | Max retries exceeded        | `Max retries (3) exceeded for operation`            |
| ERROR   | Non-retryable error         | `Non-retryable error (400) for operation`           |

### Example Log Output

```
WARNING - Retry 1/3 for _get /api/agents/information-gatherer/execute after error: HTTPSConnectionPool(host='api.example.com', port=443): Read timed out. (read timeout=10). Waiting 1.2s before retry...

INFO - Retry 1/3 succeeded for _get /api/agents/information-gatherer/execute after 1.2s wait

WARNING - Retry 2/3 for _post /api/agents/email-writer/process after error: 500 Internal Server Error. Waiting 2.4s before retry...

ERROR - Max retries (3) exceeded for _get /api/agents/failing-endpoint. Last error: 500 Internal Server Error
```

### Monitoring in Langfuse

Retry attempts are automatically logged to Langfuse (if configured) with:
- Flow instance ID
- Node name
- Retry attempt count
- Error details
- Wait times

Look for traces with multiple spans for the same operation to identify retried requests.

## Best Practices

### 1. Configure Retries Based on Operation Type

**Fast operations (< 5 seconds):**
```yaml
error_handler_config:
  max_retries: 3
  retry_interval: 1000  # 1 second
```

**Long operations (document processing, ML inference):**
```yaml
error_handler_config:
  max_retries: 5
  retry_interval: 3000  # 3 seconds
```

**Critical operations (should rarely fail):**
```yaml
error_handler_config:
  max_retries: 1
  retry_interval: 500   # 0.5 seconds
```

### 2. Set Appropriate Timeouts

```python
# For fast API calls
client = BaseAPIClient(base_url=url, timeout=30)

# For document processing
client = BaseAPIClient(base_url=url, timeout=300)

# For ML model inference
client = BaseAPIClient(base_url=url, timeout=600)
```

### 3. Provide User-Friendly Error Messages

```yaml
error_handler_config:
  error_message: "We couldn't process your document. This might be because:
    • The file is too large
    • The service is temporarily unavailable
    Please try again in a few minutes or contact support."
```

### 4. Monitor Retry Patterns

Watch your logs for patterns:
- **High retry rate on specific agent** → Investigate that service
- **Timeouts on specific operations** → Increase timeout or optimize operation
- **Persistent failures** → Check service health

### 5. Test Failure Scenarios

```python
# Test with very low retries to simulate failures quickly
client = BaseAPIClient(
    base_url=url,
    max_retries=1,
    retry_interval=100,  # 0.1 seconds for fast testing
    timeout=5
)
```

## Troubleshooting

### Problem: Operations always timeout even with retries

**Possible causes:**
1. Timeout value is too low for the operation
2. Service is genuinely down (not transient)
3. Operation is too expensive and needs optimization

**Solutions:**
```yaml
# Increase timeout
error_handler_config:
  max_retries: 3
  retry_interval: 2000

# And in code:
client = BaseAPIClient(base_url=url, timeout=600)  # 10 minutes
```

### Problem: Too many retries causing slow user experience

**Solution:** Reduce max_retries for non-critical operations:
```yaml
error_handler_config:
  max_retries: 1  # Fail fast
  retry_interval: 500
```

### Problem: "Max retries exceeded" errors in logs

**Investigation steps:**
1. Check if the service is healthy: `curl https://service-url/health`
2. Look at error details in logs: Is it always 500? 503? Timeout?
3. Check Langfuse traces: Are all operations failing or just some?

**If service is flaky:**
```yaml
error_handler_config:
  max_retries: 5      # More retries
  retry_interval: 3000 # Longer waits
```

**If service is down:**
- Fix the service first
- Consider circuit breaker pattern (future enhancement)

### Problem: Getting rate limited (HTTP 429)

**The retry mechanism handles this automatically** with extended backoff, but if you're still hitting limits:

```yaml
error_handler_config:
  max_retries: 3
  retry_interval: 5000  # Start with 5 second wait (will become 10s for 429)
```

Or reduce request rate in your flow design.

### Problem: Want to disable retries for testing

```python
# In code
client = BaseAPIClient(base_url=url, max_retries=0)
```

```yaml
# In YAML
error_handler_config:
  max_retries: 0
```

### Problem: Logs too verbose

The retry mechanism logs at appropriate levels:
- Set log level to ERROR to see only failures
- Set log level to WARNING to see retry attempts
- Set log level to INFO to see successful retries

```python
import logging
logging.getLogger('ibm_watsonx_orchestrate').setLevel(logging.ERROR)
```

## Advanced Usage

### Custom Retry Logic

```python
from ibm_watsonx_orchestrate.client.retry_handler import retry_with_backoff

@retry_with_backoff(
    max_retries=5,
    retry_interval=1000,
    backoff_multiplier=3.0,  # Aggressive backoff: 1s → 3s → 9s
    jitter_percentage=0.1,   # Less jitter (±10%)
    context_name="aggressive_retry"
)
def my_aggressive_retry_function():
    pass
```

### Conditional Retry Based on Error Type

```python
from ibm_watsonx_orchestrate.client.retry_handler import (
    _is_retryable_error,
    _is_rate_limit_error
)

try:
    response = client._get("/api/endpoint")
except Exception as e:
    if _is_retryable_error(e):
        print("This error would be retried automatically")
    elif _is_rate_limit_error(e):
        print("This is a rate limit error with extended backoff")
    else:
        print("This error would NOT be retried")
        raise
```

### Creating Decorator from Config

```python
from ibm_watsonx_orchestrate.client.retry_handler import create_retry_decorator_from_config

# From NodeErrorHandlerConfig or dict
config = {
    "max_retries": 5,
    "retry_interval": 2000
}

decorator = create_retry_decorator_from_config(**config)

@decorator
def my_function():
    pass
```

## Performance Considerations

### Retry Overhead

With default settings (3 retries, 1s interval):
- **Best case** (success on first try): No overhead
- **Worst case** (all retries fail): ~7 seconds added
- **Average case** (success on 2nd try): ~1 second added

### Memory Usage

- Retry mechanism is stateless
- No memory accumulation over time
- Each request is independent

### Concurrent Requests

- Multiple concurrent requests each have independent retry logic
- No shared state between requests
- No contention or blocking

## Related Documentation

- [BaseAPIClient API Reference](./api/base_api_client.md)
- [Error Handling Best Practices](./error_handling.md)
- [Flow Configuration Guide](./flows.md)
- [Monitoring and Observability](./monitoring.md)

## Support

For issues or questions about retry handling:
1. Check this documentation first
2. Search existing GitHub issues
3. Create a new issue with:
   - Logs showing retry behavior
   - Your configuration (YAML or code)
   - Expected vs. actual behavior

---

**Last Updated:** 2024
**Version:** 1.0.0
