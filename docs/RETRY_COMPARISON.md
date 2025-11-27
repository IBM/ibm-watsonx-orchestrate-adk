# ADK Retry Mechanisms: Client-Level vs Flow Node-Level

## Executive Summary

The IBM watsonx Orchestrate ADK provides **two distinct retry mechanisms** that operate at different layers of the architecture:

1. **Client-Level Retries** (Our Implementation) - Network/transport layer automatic retries
2. **Flow Node-Level Retries** (Orchestrate's Implementation) - Business logic/workflow retries

Both mechanisms serve different purposes and **work together** to provide comprehensive resilience.

---

## 📊 Comparison Table

| Aspect | Client-Level Retries (Our Implementation) | Flow Node-Level Retries |
|--------|-------------------------------------------|-------------------------|
| **Layer** | Network/HTTP Transport Layer | Business Logic/Workflow Layer |
| **Scope** | All HTTP requests from BaseAPIClient | Individual nodes in a flow |
| **Configuration** | Environment variables or code | YAML/JSON flow definition |
| **Automatic** | Yes - transparent to application | No - must be explicitly configured |
| **Error Types** | Network, timeout, server errors | Any node execution failure |
| **Retry Logic** | Exponential backoff with jitter | Fixed interval |
| **Use Case** | Handle transient network issues | Handle business logic failures |
| **Visibility** | Logs only | Visible in flow execution history |

---

## 🔧 Client-Level Retries (Our Implementation)

### What It Is
Client-level retries operate at the **HTTP transport layer** within the `BaseAPIClient`. These retries are **automatic and transparent** to the application logic, handling transient network issues without any flow-level awareness.

### How It Works
```python
# Automatically applied to ALL HTTP operations
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient

# Configure via environment variables
export ADK_MAX_RETRIES=3
export ADK_RETRY_INTERVAL=1000
export ADK_TIMEOUT=300

# Or configure in code
client = BaseAPIClient(
    base_url="https://api.example.com",
    max_retries=3,           # Retry up to 3 times
    retry_interval=1000,     # Start with 1 second wait
    timeout=300              # 5 minute timeout
)

# Every HTTP call is automatically protected
response = client._post("/api/agents/my-agent/execute", data={...})
# If this fails due to timeout/500 error, it automatically retries
```

### What It Handles
- ✅ **Network Errors**: Connection timeouts, connection resets
- ✅ **Server Errors**: HTTP 500, 502, 503, 504
- ✅ **Rate Limiting**: HTTP 429 with extended backoff
- ✅ **Timeouts**: Request timeouts

### Retry Pattern
```
Request → Fail → Wait 1s → Retry → Fail → Wait 2s → Retry → Fail → Wait 4s → Retry → Success/Fail
         ↑                                                                              ↓
         └──────────────────── Automatic, no code changes needed ──────────────────────┘
```

### Configuration
```bash
# .env file
ADK_MAX_RETRIES=3        # Maximum retry attempts
ADK_RETRY_INTERVAL=1000  # Initial wait in milliseconds
ADK_BACKOFF_MULTIPLIER=2.0  # Exponential backoff multiplier
ADK_JITTER_PERCENTAGE=0.2   # ±20% randomization
ADK_TIMEOUT=300          # Request timeout in seconds
```

---

## 📋 Flow Node-Level Retries (Orchestrate's Implementation)

### What It Is
Flow node-level retries operate at the **workflow/business logic layer**. These retries are configured in the flow definition and handle failures of specific nodes (tools, agents, etc.) within a workflow.

### How It Works
```json
// In flow JSON (e.g., get_number_random_fact_flow.json)
{
  "nodes": {
    "get_facts_about_numbers": {
      "spec": {
        "kind": "tool",
        "name": "get_facts_about_numbers",
        "error_handler_config": {
          "error_message": "An error has occurred while invoking the LLM",
          "max_retries": 1,
          "retry_interval": 1000
        },
        "tool": "get_facts_about_numbers"
      }
    }
  }
}
```

Or in Python flow builder:
```python
from ibm_watsonx_orchestrate.flow_builder.flows import Flow
from ibm_watsonx_orchestrate.flow_builder.types import NodeErrorHandlerConfig

# Configure retry for a specific node
ask_agent = aflow.agent(
    name="ask_agent_for_info",
    agent="information_agent",
    error_handler_config=NodeErrorHandlerConfig(
        error_message="Failed to get information from agent",
        max_retries=2,
        retry_interval=2000  # 2 seconds between retries
    )
)
```

### What It Handles
- ✅ **Tool Failures**: When a tool returns an error
- ✅ **Agent Failures**: When an agent cannot formalize a response
- ✅ **Business Logic Errors**: Application-specific failures
- ✅ **Validation Errors**: When output doesn't match expected schema

### Retry Pattern
```
Flow Start → Node Execute → Fail → Wait (fixed) → Retry Node → Fail → Wait (fixed) → Retry Node → Success/Fail
            ↑                                                                                      ↓
            └────────────────── Visible in flow execution history ────────────────────────────────┘
```

### Configuration in Flow Definition
```python
error_handler_config = {
    "error_message": "Custom error message for users",  # Optional
    "max_retries": 3,        # Maximum retry attempts
    "retry_interval": 1000   # Fixed interval in milliseconds (no backoff)
}
```

---

## 🔄 How They Work Together

### Layered Retry Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User's Flow/Application                  │
├─────────────────────────────────────────────────────────────┤
│                  Flow Node-Level Retries                     │
│  • Configured per node in YAML/JSON                          │
│  • Fixed interval retries                                    │
│  • Business logic aware                                      │
│  • Visible in flow execution                                 │
├─────────────────────────────────────────────────────────────┤
│                  Client-Level Retries (Our Implementation)   │
│  • Automatic for all HTTP calls                              │
│  • Exponential backoff with jitter                           │
│  • Network/transport errors                                  │
│  • Transparent to application                                │
├─────────────────────────────────────────────────────────────┤
│                     Network/HTTP Layer                       │
└─────────────────────────────────────────────────────────────┘
```

### Example Scenario

Consider a flow that calls an agent to process a document:

1. **Flow executes** → Calls agent node
2. **Agent node sends HTTP request** via BaseAPIClient
3. **Network timeout occurs** (e.g., slow network)
   - **Client-level retry** kicks in automatically
   - Waits 1s, retries... waits 2s, retries... succeeds
   - Flow node doesn't even know a retry happened
4. **Agent returns but with formalization error**
   - HTTP request succeeded (thanks to client-level retry)
   - But business logic failed
   - **Node-level retry** kicks in
   - Entire node execution is retried after fixed interval
5. **Success** after both retry mechanisms worked together

### Real Example from Code

Looking at `get_number_random_fact_flow.json`:

```json
{
  "nodes": {
    "get_facts_about_numbers": {
      "spec": {
        "error_handler_config": {
          "max_retries": 1,        // Node will retry once if it fails
          "retry_interval": 1000   // Wait 1 second between node retries
        }
      }
    }
  }
}
```

**What happens when this node executes:**

1. Node calls the `get_facts_about_numbers` tool
2. Tool makes HTTP request to numbers API
3. If HTTP request fails:
   - **Client-level retry** automatically retries with exponential backoff
   - Transparent to the node
4. If tool logic fails (even after successful HTTP):
   - **Node-level retry** retries the entire tool execution
   - Waits 1000ms (fixed)
   - Retries once (max_retries=1)

---

## 🎯 When to Use Which

### Use Client-Level Retries (Our Implementation) When:

- ✅ You want **automatic protection** against network issues
- ✅ You need **exponential backoff** for rate limiting
- ✅ You want retries to be **transparent** to business logic
- ✅ You're dealing with **transient infrastructure issues**
- ✅ You want **global configuration** for all operations

**Configuration:**
```bash
# For production environments with unreliable networks
export ADK_MAX_RETRIES=5
export ADK_RETRY_INTERVAL=2000
export ADK_TIMEOUT=600
```

### Use Flow Node-Level Retries When:

- ✅ You need **business logic awareness** of retries
- ✅ You want **retry visibility** in flow execution history
- ✅ You have **node-specific** retry requirements
- ✅ You need **custom error messages** for users
- ✅ You're handling **application-level failures**

**Configuration:**
```python
# For specific business operations that may fail
error_handler_config=NodeErrorHandlerConfig(
    error_message="Could not process your request. Please try again.",
    max_retries=3,
    retry_interval=5000  # 5 seconds for business logic retries
)
```

---

## 🔍 Key Differences in Implementation

### 1. Retry Timing

**Client-Level (Exponential Backoff):**
```
Attempt 1: Wait 1s
Attempt 2: Wait 2s  
Attempt 3: Wait 4s
Total: ~7s with jitter
```

**Node-Level (Fixed Interval):**
```
Attempt 1: Wait 1s
Attempt 2: Wait 1s
Attempt 3: Wait 1s
Total: 3s exactly
```

### 2. Error Detection

**Client-Level:**
```python
# Automatically detects retryable errors
if status_code in [429, 500, 502, 503, 504]:
    # Retry automatically
if isinstance(error, (requests.Timeout, requests.ConnectionError)):
    # Retry automatically
```

**Node-Level:**
```python
# Any exception from node execution triggers retry
try:
    result = execute_node()
except Exception as e:
    if retries_remaining > 0:
        # Retry entire node
```

### 3. Configuration Scope

**Client-Level:**
- Global via environment variables
- Per-client instance
- Affects ALL HTTP operations

**Node-Level:**
- Per-node in flow definition
- Only affects that specific node
- Must be explicitly configured

---

## 💡 Best Practices

### 1. Use Both Together
```python
# Configure robust client-level retries
export ADK_MAX_RETRIES=3
export ADK_RETRY_INTERVAL=1000

# Add node-level retries for critical operations
critical_node = aflow.tool(
    critical_tool,
    error_handler_config={
        "max_retries": 2,
        "retry_interval": 5000
    }
)
```

### 2. Different Timeouts for Different Layers
```python
# Fast client-level retries for network issues
export ADK_RETRY_INTERVAL=1000  # 1 second

# Slower node-level retries for business logic
error_handler_config={
    "retry_interval": 10000  # 10 seconds
}
```

### 3. Appropriate Error Messages
```python
# Client-level: Technical logs
logger.error("HTTP 500 error: Internal server error")

# Node-level: User-friendly messages  
error_handler_config={
    "error_message": "We couldn't process your document. Please try again in a few moments."
}
```

---

## 📝 Summary

- **Client-level retries** (our implementation) provide **automatic, transparent** protection against network and server issues
- **Node-level retries** provide **business logic aware** retry capabilities with flow visibility
- Both mechanisms are **complementary**, not competing
- Client-level retries happen **first** (at HTTP layer), node-level retries happen **second** (at business logic layer)
- Use **both together** for maximum resilience

### Quick Decision Guide

| If you need... | Use... |
|----------------|--------|
| Automatic network resilience | Client-Level Retries |
| Business logic retry control | Node-Level Retries |
| Exponential backoff | Client-Level Retries |
| Retry visibility in UI | Node-Level Retries |
| Global retry configuration | Client-Level Retries |
| Per-operation retry config | Node-Level Retries |
| Rate limit handling | Client-Level Retries |
| Custom user error messages | Node-Level Retries |

---

*Last Updated: November 2024*