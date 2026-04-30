# Memory Coach SDK Agent

This example is a realistic memory-driven custom LangGraph agent that combines:

- an external LLM through OpenRouter
- the published [`ibm-watsonx-orchestrate-sdk`](../../../packages/agentic-sdk/ibm_watsonx_orchestrate_sdk/__init__.py)
- managed memory read/write calls for personalization across turns

Unlike the earlier heuristic-only POC, this version uses the LLM for both:

- planning whether to search/store memory
- generating the final user-facing response

For the current Agentic SDK memory surface, valid `memory_type` values, and
the recommended `runs-on` construction pattern, see
[`../local_memory_sdk_agent/SDK_MEMORY_REFERENCE.md`](../local_memory_sdk_agent/SDK_MEMORY_REFERENCE.md).

## Runtime Requirements

This agent expects an environment variable:

```text
OPENROUTER_API_KEY=<your-openrouter-key>
```

The key is read at runtime in [`_openrouter_chat()`](./agent.py).

## How It Works

The entrypoint is [`create_agent()`](./agent.py), which bootstraps the SDK through
[`Client.from_runnable_config()`](../../../packages/agentic-sdk/ibm_watsonx_orchestrate_sdk/client.py).

For each turn, the agent:

1. reads the latest user message and recent conversation turns
2. asks the LLM to produce a structured memory plan
3. searches memory when the plan says recall is useful
4. stores a distilled fact when the plan says the turn contains durable user information
5. asks the LLM to generate a natural final response using:
   - the recent conversation
   - retrieved memory context
   - memory write outcome

## Personalization Loop

The intended loop is:

- user shares facts, preferences, goals, or outcomes
- agent stores durable details using [`client.memory.add_messages()`](../../../packages/agentic-sdk/ibm_watsonx_orchestrate_sdk/memory/memory_client.py:26)
- later turns trigger [`client.memory.search()`](../../../packages/agentic-sdk/ibm_watsonx_orchestrate_sdk/memory/memory_client.py:50)
- the LLM uses those recalled memories to answer more personally and consistently

## Supported Memory Types

The planner constrains memory classification to backend-safe values:

- `profile_fact`
- `preference`
- `outcome`
- `conversational`

## Example Interactions

### Turn 1

```text
I recently moved to Bangalore and I prefer espresso over tea.
```

Expected behavior:
- LLM decides this contains durable personal information
- relevant facts may be stored as memory

### Turn 2

```text
What drink should you remember that I like?
```

Expected behavior:
- memory search runs
- the final response references the stored preference if retrieval succeeds

### Turn 3

```text
I'm preparing for a product architecture interview next week.
```

Expected behavior:
- the new goal/outcome context may be stored
- later coaching responses can become more tailored

## Import

```bash
orchestrate agents import \
  --experimental-package-root examples/custom_agents/memory_coach_sdk_agent
```

## Files

- [`agent.py`](./agent.py)
- [`agent.yaml`](./agent.yaml)
- [`config.yaml`](./config.yaml)
- [`requirements.txt`](./requirements.txt)
