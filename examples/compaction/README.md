# Compaction Demo — watsonx Orchestrate ADK

This example demonstrates **conversation compaction** for native agents in IBM watsonx Orchestrate. Compaction prevents context-window overflow during long conversations and when tool responses return large payloads.

## What's in this example

| File | Purpose |
|---|---|
| `agent.yaml` | Native agent with all compaction settings configured |
| `tools/knowledge_base_search.py` | Tool returning large **unstructured** text → exercises map-reduce summarization |
| `tools/get_order_history.py` | Tool returning large **structured** JSON → exercises truncation |

---

## How compaction works in Orchestrate

Compaction has two independent mechanisms that address different overflow scenarios.

### 1. Conversation-level compaction (turn based)

**Trigger:** Total conversation history exceeds `context_compaction_threshold` tokens.

**What happens:**
- The most recent `compaction_sliding_window` turns are kept **verbatim**.
- All older turns are replaced with an LLM-generated **rolling summary**.
- This runs **asynchronously** in the background — the current user turn is not blocked.

For instance, for a sliding window of 10:
```
Turn 1 ──┐
Turn 2   │  → Summarized into a single
Turn 3   │    "conversation summary" block
...      │
Turn N-10┘
Turn N-9 ──┐
...        │  Preserved verbatim
Turn N   ──┘  (sliding window = 10)
```

### 2. Conversation-level compaction (token based)

This setting controls when conversation-level compaction fires. The right value depends on your model's context window, you want it to trigger early enough that compaction finishes before the hard limit is hit, since it runs asynchronously.

A conservative threshold is to set it around 70% of the model's context lenght.

```yaml
# Example for a 128k-context lenght
compaction_settings:
  context_compaction_enabled: true
  context_compaction_threshold: 89000  # ~70% of 128k
```

> **Note:** If `context_compaction_threshold` is set too close to the model's hard context limit, the asynchronous compaction job may not complete before the next turn pushes the conversation over the limit — resulting in a context-length error. Setting it conservatively lower gives the compaction process a safe buffer.

### 3. Large message handling (synchronous / inline)

**Trigger:** A single message (e.g. a tool response) exceeds `large_message_threshold` tokens.

**What happens** (before the message enters conversation history):

| Content type | Strategy | Controlled by |
|---|---|---|
| Unstructured (prose, logs, docs) | Map-Reduce Summarization | `large_message_chunk_size`,  `large_message_target_summary` |
| Structured (JSON, tables) | Truncation | `large_message_detect_structured: true` |

**Map-Reduce flow for unstructured content:**
```
Large message
    │
    ├── Chunk 1 (30k tokens) → Summary 1 ──┐
    ├── Chunk 2 (30k tokens) → Summary 2   │ → Combined summary
    ├── ...                                │
    └── Chunk N (30k tokens) → Summary N ──┘   (≈ large_message_target_summary tokens)
```

---

## Compaction settings reference

| Field | Type | Default | Description |
|---|---|---|---|
| `context_compaction_enabled` | boolean | `false` | Must be `true` to activate any compaction. |
| `context_compaction_threshold` | integer | — | Token count that triggers conversation-level compaction. |
| `compaction_sliding_window` | integer | — | Number of recent turns to preserve verbatim. |
| `large_message_threshold` | integer | — | Per-message token count that triggers inline large-message handling. |
| `large_message_chunk_size` | integer | — | Chunk size (tokens) for map-reduce summarization of unstructured messages. |
| `large_message_target_summary` | integer | — | Target token length for the final compressed summary. |
| `large_message_detect_structured` | boolean | `false` | When `true`, detects structured data and uses truncation instead of summarization. |

---

## References

- [Conversation Compaction — Orchestrate Docs](https://developer.watson-orchestrate.ibm.com/agents/build_agent#conversation-compaction-settings)
