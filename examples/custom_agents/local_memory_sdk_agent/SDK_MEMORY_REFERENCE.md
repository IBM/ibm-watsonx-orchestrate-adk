# Agentic SDK Runs-On and Memory Guide

This guide is the current reference for building `runs-on` custom agents in
`wxo-clients` that use the Agentic SDK memory APIs.

It is written against the current SDK code on this branch, not against older
placeholder memory helpers.

## What This Guide Covers

- how to structure a `runs-on` LangGraph agent
- how to initialize the SDK from runtime context
- which memory APIs are stable today
- which `memory_type` values are accepted
- what metadata is useful
- what the real memory scoping rules are

## The Three SDK Modes

The SDK currently supports three session modes:

- `runs-on`
- `runs-elsewhere`
- `local`

For platform custom agents, the mode you care about is `runs-on`.

Use `local` only for developer-edition testing.
Use `runs-elsewhere` only when your app or agent is running outside the WXO
runtime and authenticates with instance credentials.

## The Recommended Runs-On Pattern

For LangGraph agents running on the platform, prefer:

```python
from ibm_watsonx_orchestrate_sdk import Client

client = Client.from_runnable_config(config)
```

This is better than manually extracting `execution_context` because it keeps the
entrypoint smaller and matches how the SDK expects runtime context to be passed
through LangGraph.

If you do need to extract it manually, this is still valid:

```python
execution_context = config.get("configurable", {}).get("execution_context", {}) or {}
client = Client(execution_context=execution_context)
```

## What a Runs-On Agent Must Receive

The runtime must provide `execution_context` with at least:

- `access_token`
- `thread_id`
- `api_proxy_url`

Important detail:

- the SDK uses `api_proxy_url` as-is
- it does not append `/v1/orchestrate`
- it does not append an instance path

So the runtime value of `api_proxy_url` must already be the full base URL that
the SDK should call.

For example, if the SDK is going to call:

```text
/memories
/memories/search
/context/summarize
```

then `api_proxy_url` must already point at the correct orchestrate API base for
that environment.

Also note:

- `WXO_API_PROXY_URL` from the environment currently overrides
  `execution_context["api_proxy_url"]`
- `runs-on` defaults to `verify=False` unless the caller overrides it

## The Minimum File Set for a Runs-On Custom Agent

The example in this folder uses the standard custom-agent package layout:

- `agent.py`
- `agent.yaml`
- `config.yaml`
- `requirements.txt`

You only need a few things for the SDK-specific part:

1. An entrypoint function, usually `create_agent(config)`
2. The SDK in `requirements.txt`
3. A runtime graph or callable that uses `Client.from_runnable_config(config)`

## Minimal Runs-On LangGraph Agent

```python
from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import RunnableConfig

from ibm_watsonx_orchestrate_sdk import Client


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def _latest_user_message(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if getattr(message, "type", "") == "human":
            content = getattr(message, "content", "")
            if isinstance(content, str) and content.strip():
                return content
    return ""


def create_agent(config: RunnableConfig):
    client = Client.from_runnable_config(config)

    def agent_node(state: AgentState):
        user_text = _latest_user_message(state.get("messages", []))
        if not user_text:
            return {"messages": [AIMessage(content="No user message found.")]}

        search_response = client.memory.search(query=user_text, limit=3)

        if search_response.results:
            memory_text = "\n".join(item.content for item in search_response.results)
            response_text = f"I found related memories:\n{memory_text}"
        else:
            response_text = "I do not have anything relevant in memory yet."

        return {"messages": [AIMessage(content=response_text)]}

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.set_entry_point("agent")
    builder.add_edge("agent", END)
    return builder.compile()
```

## Packaging and Import

The example agent in this folder is imported with:

```bash
./.venv/bin/orchestrate agents import \
  --experimental-package-root examples/custom_agents/local_memory_sdk_agent
```

That command packages the directory, creates or updates the agent definition,
and uploads the code bundle.

For custom agents, this is the path you should document and test. Importing only
the YAML is not enough when the agent has code and dependencies.

## The Memory APIs to Use

The stable write API is:

```python
client.memory.add_messages(...)
```

The stable read APIs are:

```python
client.memory.search(...)
client.memory.list(...)
client.memory.retrieve(...)
```

Delete APIs:

```python
client.memory.delete(memory_id="...")
client.memory.delete_all()
```

The old `store()` helper has been removed from this SDK surface. Use
`add_messages(...)` instead.

## Recommended Usage Pattern

When you know what kind of memory you are writing, pass it explicitly:

```python
client.memory.add_messages(
    messages=[{"role": "user", "content": "I prefer coffee"}],
    memory_type="preference",
    infer=False,
    metadata={"source": "manual-test"},
)
```

Then search with either a semantic query:

```python
response = client.memory.search(query="favorite drink", limit=3)
```

or a semantic query plus a type filter:

```python
response = client.memory.search(
    query="favorite drink",
    limit=3,
    memory_type="preference",
)
```

## Public Method Signatures

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

### `retrieve`

```python
retrieve(query, limit=10)
```

This is just a compatibility helper around `search(...)`.

### `list`

```python
list(*, limit=100, offset=0)
```

### `delete`

```python
delete(*, memory_id)
```

### `delete_all`

```python
delete_all()
```

## Valid Message Shape

Each message must be a non-empty object like:

```python
{"role": "user", "content": "I prefer coffee"}
```

Supported roles are whatever your calling flow passes through, but the memory
service behavior is driven mainly by `user`, `assistant`, and `tool` messages.

For `runs-on` custom agents, the most common shapes are:

- a single `user` message
- a short `user` + `assistant` window
- `user` + `tool` messages for procedural or tool-result memory

## Supported `memory_type` Values

The SDK and backend currently agree on these canonical values:

- `conversational`
- `profile_fact`
- `preference`
- `outcome`
- `tool`

The SDK also normalizes these aliases:

- `conversation` -> `conversational`
- `fact` -> `conversational`
- `episodic` -> `conversational`
- `profile` -> `profile_fact`
- `identity` -> `profile_fact`
- `preferences` -> `preference`
- `task` -> `tool`
- `procedure` -> `tool`
- `derived_event` -> `outcome`

If you pass an unsupported type, the SDK now fails fast with a validation error
instead of silently shipping a bad payload.

## What Metadata Is Supported

`metadata` is supported on `add_messages(...)` as:

```python
dict[str, Any] | None
```

Useful examples:

```python
metadata={
    "source": "chat",
    "source_request_id": "req-123",
    "scope": "user_profile",
    "case_id": "case-42",
    "ticket_id": "ticket-99",
}
```

Prefer top-level fields when the SDK already exposes them:

- `memory_type`
- `agent_id`
- `run_id`
- `sensitivity_classification`
- `source_reference`

Do not bury those concepts in `metadata` unless you are intentionally adding
extra source annotations.

## Scoping Rules That Matter

This is one of the biggest sources of confusion.

Managed memory is user-scoped first.

That means:

- memories are primarily stored for the current user in the current tenant
- `agent_id` is context, not an ownership boundary
- `run_id` is source metadata, not an ownership boundary

Practical implications:

- the same user can recall relevant memories across agents
- `delete_all()` is not thread-scoped
- `list()` is not thread-scoped

So when you write tests, validate user-level behavior, not per-agent isolation.

## Choosing `infer=True` vs `infer=False`

Use `infer=False` when:

- you already know what memory you are writing
- you want a predictable, typed write
- you are intentionally storing a distilled fact

Use the default behavior when:

- you are providing a richer message window
- you want backend extraction to decide what durable memory to keep

For most custom agents, the safest pattern is still:

1. decide the memory type in your agent logic
2. call `add_messages(...)` with an explicit `memory_type`
3. use `infer=False` for deterministic writes

## A Simple Runs-On Memory Loop

```python
from ibm_watsonx_orchestrate_sdk import Client


def remember_preference(config, text: str):
    client = Client.from_runnable_config(config)
    return client.memory.add_messages(
        messages=[{"role": "user", "content": text}],
        memory_type="preference",
        infer=False,
        metadata={"source": "agent"},
    )


def recall_preferences(config, query: str):
    client = Client.from_runnable_config(config)
    return client.memory.search(
        query=query,
        memory_type="preference",
        limit=3,
    )
```

## Common Failure Modes

### 1. `execution_context.api_proxy_url is required`

The runtime did not provide `api_proxy_url`, and `WXO_API_PROXY_URL` was not set.

### 2. TLS warnings or hostname errors on `runs-on`

The SDK uses the `api_proxy_url` exactly as provided. If that host has a cert
that does not match the hostname, requests will fail unless the environment is
intentionally configured for unverified internal HTTPS.

### 3. Invalid `memory_type`

This is now an SDK validation error, not a backend surprise.

### 4. Empty search results

This is a valid outcome. Do not treat an empty search result as a transport or
SDK failure.

## What to Test for a Runs-On Agent

At minimum:

1. agent initializes from `RunnableConfig`
2. `client.memory.add_messages(...)` succeeds with an explicit type
3. `client.memory.search(...)` returns a typed response object
4. empty search results are handled cleanly
5. invalid `memory_type` fails fast with a clear error

## Recommended Mental Model

- `runs-on` is the runtime integration path
- `Client.from_runnable_config(config)` is the cleanest constructor for
  LangGraph agents
- `add_messages(...)` is the main write API
- `search(...)` is the main read API
- memory is user-scoped, not agent-owned
- `api_proxy_url` must already be the correct API base path

If you keep those six points straight, most of the SDK memory usage becomes
predictable.
