# Agentic SDK Memory Quick Reference

This is the shortest reliable guide to using the SDK memory APIs on this branch.
It reflects the current code and the current memory-service contract.

## If You Only Remember 3 Things

1. In a `runs-on` agent, use:

```python
client = Client(execution_context=execution_context)
```

2. Use only these `memory_type` values:

- `conversational`
- `profile_fact`
- `preference`
- `outcome`
- `tool`

3. If you pass random `memory_type` values, the backend can return `422`, which often shows up in agents as a generic memory error.

## The Most Common Working Pattern

```python
from ibm_watsonx_orchestrate_sdk import Client

client = Client(execution_context=execution_context)

search_response = client.memory.search(
    query="What is my favorite drink?",
    limit=3,
)

client.memory.add_messages(
    messages=[{"role": "user", "content": "My favorite drink is coffee"}],
    memory_type="preference",
    infer=False,
)
```

## Which Client Constructor Should I Use?

### Local ADK

Use this from local scripts or notebooks when talking to developer edition:

```python
from ibm_watsonx_orchestrate_sdk import Client

client = Client()
```

This defaults to local mode and talks to:

```text
http://localhost:4321/api/v1
```

### Runs-On Agent

Use this inside a custom agent running on the platform:

```python
from ibm_watsonx_orchestrate_sdk import Client

client = Client(execution_context=execution_context)
```

Required runtime context:

```python
execution_context = {
    "access_token": "...",
    "thread_id": "...",
    "api_proxy_url": "http://wxo-server:4321/api/v1",
}
```

Notes:
- `thread_id` is required
- `access_token` is required
- `api_proxy_url` is required unless `WXO_API_PROXY_URL` is already present in the environment

### LangGraph / RunnableConfig

If your runtime gives you a `RunnableConfig`, use:

```python
from ibm_watsonx_orchestrate_sdk import Client

client = Client.from_runnable_config(config)
```

### Runs-Elsewhere

Use this when you are not inside the runtime:

```python
from ibm_watsonx_orchestrate_sdk import Client

client = Client(
    instance_url="https://api.<env>.watson-orchestrate.ibm.com/instances/<instance-id>",
    api_key="<api-key>",
)
```

## Memory APIs You Can Use Today

### Add memory

```python
client.memory.add_messages(
    messages=[{"role": "user", "content": "I prefer coffee"}],
    infer=False,
    memory_type="preference",
    metadata={"source": "manual-test"},
)
```

### Add memory with metadata

```python
client.memory.add_messages(
    messages=[{"role": "user", "content": "My name is Suyash"}],
    infer=False,
    memory_type="profile_fact",
    metadata={
        "source": "chat",
        "scope": "user_profile",
        "source_request_id": "req-123",
        "wxo_memory_type": "profile_fact",
    },
)
```

### Search memory

```python
results = client.memory.search(
    query="favorite drink",
    limit=3,
    memory_type="preference",
)
```

### List memory

```python
memories = client.memory.list(limit=20, offset=0)
```

### Delete one memory

```python
client.memory.delete(memory_id="mem-123")
```

### Delete all memories for the current user

```python
client.memory.delete_all()
```

## Exact Public Method Signatures

### `add_messages`

```python
add_messages(
    *,
    messages,
    infer=None,
    memory_type=None,
    metadata=None,
    agent_id=None,
    run_id=None,
    sensitivity_classification=None,
    source_reference=None,
)
```

`metadata` is currently:

```python
dict[str, Any] | None
```

and is forwarded to the memory service as part of the create request.

### `search`

```python
search(
    *,
    query,
    limit=10,
    memory_type=None,
    expanded_query=None,
    recall=None,
)
```

### `list`

```python
list(*, limit=100, offset=0)
```

### `delete_all`

```python
delete_all()
```

### `delete`

```python
delete(*, memory_id)
```

## Valid Message Shape

Each message must be a dict like this:

```python
{"role": "user", "content": "I like dark mode"}
```

or:

```python
{"role": "assistant", "content": "Got it, I will remember that"}
```

Current validation is simple:
- `role` must be a non-empty string
- `content` must be a non-empty string
- `messages` must be a non-empty list

## Metadata: What Is Supported?

Short version:
- yes, metadata is supported on `add_messages(...)`
- it is an open-ended dictionary, not a strict typed SDK schema
- use JSON-serializable values only
- prefer top-level fields such as `memory_type`, `agent_id`, and `run_id` when those concepts already exist as first-class arguments

### What the SDK Accepts

The SDK accepts:

```python
metadata: dict[str, Any] | None
```

The request builder and client do not currently enforce a narrow metadata schema.
If you pass a Python dict, it is forwarded to the backend.

### What the Memory Service Does With It

On create, the memory service builds a Mem0 metadata payload and merges your `metadata` into it.

The service also adds platform-managed keys such as:
- `tenant_id`
- `memory_type`
- `source_agent_id`
- `source_run_id`
- `source_request_id`
- `source_message_roles`
- `wxo_ingest_pass`

So your metadata is supported, but it is not the only metadata present in storage.

### Keys That Are Actually Useful Today

These are the keys worth documenting for users:

- `source_request_id`
  - lets you pass a caller-side correlation/request id
  - if omitted, the service generates one

- `wxo_memory_type`
  - useful when you map an internal type to one of the supported backend types
  - example: keep original business meaning while storing under a supported canonical type

- `scope`
  - preserved in payload metadata
  - useful if your application wants a lightweight custom grouping label

- custom business metadata
  - examples: `source`, `channel`, `case_id`, `ticket_id`, `customer_segment`
  - these are accepted as long as the payload stays JSON-friendly

### What to Put in Top-Level Fields Instead

Do not treat `metadata` as a replacement for first-class fields that already exist.

Prefer these top-level arguments:
- `memory_type=...`
- `agent_id=...`
- `run_id=...`
- `sensitivity_classification=...`
- `source_reference=...`

That keeps your code aligned with the actual API contract.

### What Not to Assume

- Do not assume metadata is validated client-side against a strict schema.
- Do not assume arbitrary metadata keys will be surfaced back through current SDK response models.
- Do not assume `metadata` is the right place for tenant/user scoping.

The current SDK accepts metadata on write, but response models are intentionally minimal.

## Valid `memory_type` Values

The current memory service accepts:

- `conversational`
- `profile_fact`
- `preference`
- `outcome`
- `tool`

The SDK only normalizes one alias by itself:

- `conversation` -> `conversational`

Everything else is passed through unchanged.

That means this works:

```python
client.memory.add_messages(
    messages=[{"role": "user", "content": "I like dark mode"}],
    memory_type="conversation",
)
```

and the SDK sends:

```json
{
  "messages": [{"role": "user", "content": "I like dark mode"}],
  "memory_type": "conversational"
}
```

## Why Users See `422` or “memory unavailable”

This is the part users usually trip on.

The SDK does not fully validate `memory_type` against the backend enum before sending the request.

So if you do this:

```python
client.memory.add_messages(
    messages=[{"role": "user", "content": "My name is Jane"}],
    memory_type="random_type",
)
```

the SDK can still send it, and the memory service can return `422`.

In a custom agent, if that exception is caught broadly, users often see only a generic message such as:

- "memory service unavailable"
- "I couldn't access memory right now"

The real issue is often just an unsupported `memory_type`.

## Safe Mapping for Older/Internal Types

If your code already uses older categories, map them before calling the SDK:

- `conversation` -> `conversational`
- `profile_fact` -> `profile_fact`
- `profile` -> `profile_fact`
- `identity` -> `profile_fact`
- `preference` -> `preference`
- `fact` -> `conversational`
- `episodic` -> `conversational`
- `procedure` -> `tool`
- `task` -> `tool`
- `derived_event` -> `outcome`

Example:

```python
client.memory.add_messages(
    messages=[{"role": "user", "content": "My name is Suyash"}],
    memory_type="profile_fact",
    metadata={"wxo_memory_type": "profile_fact"},
)
```

## Metadata Examples That Read Well in Real Code

### Example: preserve original internal type

```python
client.memory.add_messages(
    messages=[{"role": "user", "content": "My name is Suyash"}],
    infer=False,
    memory_type="profile_fact",
    metadata={
        "wxo_memory_type": "identity",
        "source": "agent",
    },
)
```

Use this when your application used an internal label such as `identity`, but you want to store it under the supported backend type `profile_fact`.

### Example: pass a request correlation id

```python
client.memory.add_messages(
    messages=[{"role": "user", "content": "I prefer email over SMS"}],
    infer=False,
    memory_type="preference",
    metadata={
        "source_request_id": "req-9fd5a2",
        "source": "web-chat",
    },
)
```

### Example: lightweight scope tag

```python
client.memory.add_messages(
    messages=[{"role": "user", "content": "My support ticket was escalated"}],
    infer=False,
    memory_type="outcome",
    metadata={
        "scope": "support",
        "ticket_id": "INC-1042",
    },
)
```

### Example: scoped runtime context plus metadata

```python
client.memory.add_messages(
    messages=[{"role": "user", "content": "I must complete MFA before password reset"}],
    infer=False,
    memory_type="tool",
    agent_id="agent-123",
    run_id="run-456",
    metadata={
        "source": "workflow",
        "case_id": "case-789",
    },
)
```

In this pattern:
- `agent_id` and `run_id` stay in first-class fields
- custom business fields stay in `metadata`

## Copy-Paste Examples

### Save a preference

```python
client.memory.add_messages(
    messages=[{"role": "user", "content": "I prefer email over SMS"}],
    memory_type="preference",
    infer=False,
)
```

### Save a profile fact

```python
client.memory.add_messages(
    messages=[{"role": "user", "content": "My name is Suyash"}],
    memory_type="profile_fact",
    infer=False,
)
```

### Save general conversation context

```python
client.memory.add_messages(
    messages=[{"role": "user", "content": "I mentioned my Honda Civic earlier"}],
    memory_type="conversational",
    infer=False,
)
```

### Search only preferences

```python
client.memory.search(
    query="communication preference",
    limit=5,
    memory_type="preference",
)
```

### Search everything

```python
client.memory.search(
    query="What do you remember about me?",
    limit=5,
)
```

## What the Responses Look Like

Note:
- current SDK write/search/list response models do not expose a top-level `metadata` field back to the caller
- metadata is supported on write and used downstream, but the SDK currently returns a simplified model

### `add_messages`

```python
response = client.memory.add_messages(...)
print(response.count)
print(response.memories[0].mem0_id)
print(response.memories[0].content)
```

### `search`

```python
response = client.memory.search(query="coffee")
for item in response.results:
    print(item.mem0_id, item.score, item.memory_type, item.content)
```

### `list`

```python
response = client.memory.list(limit=20, offset=0)
print(response.total)
for item in response.memories:
    print(item.mem0_id, item.memory_type, item.content)
```

## Local Example Agent in This Repo

The working example agent is:

- `local_memory_sdk_agent`

Import it with:

```bash
./.venv/bin/orchestrate agents import \
  --experimental-package-root examples/custom_agents/local_memory_sdk_agent
```

## Practical Recommendation

If you want the least surprising setup:

- use `Client(execution_context=execution_context)` in `runs-on`
- use only the supported `memory_type` values
- treat `profile_fact` as supported
- map older internal labels before calling the SDK
- if users report “memory unavailable”, inspect the underlying exception before assuming the service is down
