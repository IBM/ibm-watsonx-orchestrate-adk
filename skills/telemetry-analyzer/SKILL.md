---
name: telemetry-analyzer
description: Use when the user wants to analyze agent telemetry traces to find bugs and get fix recommendations — walks through exporting traces from a local or remote watsonx Orchestrate server, parsing raw OTel JSON or Langfuse-format trace JSON directly, and reasoning over them to identify failures and suggest fixes.
---

# Agent Telemetry Analyzer

This skill exports agent telemetry traces from watsonx Orchestrate and analyzes them directly from raw OTel JSON **or Langfuse-format trace JSON** to produce structured bug reports with root-cause analysis and fix recommendations.

> **Two trace formats are supported:**
> - **OTel JSON** — produced by the classic `TracesController.export_trace_to_json()` ADK path and local IBM telemetry servers. Top-level key: `traceData.resourceSpans`.
> - **Langfuse JSON** — produced by the `agentops-v3` REST API (`GET /v1/agentops-v3/traces/<id>`) and the `export_traces_agentops_v3.py` script. Top-level key: `observations` (array of GENERATION / CHAIN / SPAN objects).
>
> Always **detect the format first** before reading any span data. See the `detect_format()` helper in Step 3C and the normalization table in Step 4.

> **Setup:** See [README.md](./README.md) for prerequisites (ADK installation, `.env` configuration, and environment activation) before running any scripts.

## What this skill does

1. **Identifies the trace source** — remote hosted env (wxO Traces API or agentops-v3 REST API), local env with IBM telemetry, or JSON files already on disk (OTel or Langfuse format)
2. **Exports trace files** — discovers traces by agent name or ID, paginates through results, and downloads them as OTel JSON (via ADK `TracesController`) or Langfuse JSON (via `export_traces_agentops_v3.py` / `search_traces_agentops_v3.py`)
3. **Analyzes for bugs** — detects the JSON format, normalizes spans to a common structure, and scans for hard errors, LLM failures, tool call failures, agent logic bugs, flow issues, token anomalies, and cache efficiency
4. **Produces a bug report** — structured HTML report with an executive summary, trace summary table, critical issues, warnings, observations, and fix recommendations *(multi-trace analysis only — a single-trace request goes straight to the conversational flow report)*
5. **Produces conversational flow reports** — thread-scoped reports that reconstruct multi-turn conversations and surface per-turn failures

## When to use this skill

Use this skill when you need to:

- Debug a failing or misbehaving watsonx Orchestrate agent
- Understand why an agent returned an empty or incorrect response
- Trace LLM token usage and identify prompt bloat or context overflow
- Identify tool call failures, retry loops, or hung async flows
- Analyze a batch of traces and surface the most impactful issues
- Reconstruct a full multi-turn conversation from thread-scoped traces

## How to invoke

Ask questions like:

- "Analyze the telemetry for the My Agent traces from the last 20 minutes"
- "What went wrong in trace `f492e71b957ccec2d07096ae99395d19`?"
- "Export and inspect all traces for the Supervisor agent in the last 2 hours"
- "Why did this agent return an empty response?"
- "Show me the conversational flow for this trace"

## Command-line usage

### Standard scripts (`_adk.py`) — wxO Traces API / local IBM telemetry

```bash
# Search traces and save IDs for bulk export
python scripts/search_traces_adk.py --agent-name "My Agent" --last 1h --all \
    --save-ids data/trace_ids.txt

# Export all discovered traces
python scripts/export_traces_adk.py --ids-file data/trace_ids.txt

# Export a single trace by ID
python scripts/export_traces_adk.py --trace-id <32-char-hex-id>
```

### agentops-v3 scripts (`_agentops_v3.py`) — agentops-v3 REST API

```bash
# Search traces for an agent (last 20 minutes by default)
python scripts/search_traces_agentops_v3.py --last 20m

# Narrow or widen the time window
python scripts/search_traces_agentops_v3.py --last 2h
python scripts/search_traces_agentops_v3.py --start 2025-01-01T09:00:00Z --end 2025-01-01T21:00:00Z

# Collect every trace in the window and save IDs for bulk export
python scripts/search_traces_agentops_v3.py --last 1h --all \
    --save-ids data/trace_ids.txt

# Quick count before committing to a full export
python scripts/search_traces_agentops_v3.py --last 2h --count

# Export a single trace by ID
python scripts/export_traces_agentops_v3.py --trace-id <32-char-hex-id>

# Bulk-export from a saved ID list
python scripts/export_traces_agentops_v3.py --ids-file data/trace_ids.txt
```

## Analysis capabilities

### Trace export and discovery
- Cursor-based pagination through the wxO Traces API with automatic 429 retry
- Supports `--limit N`, `--all`, and `--count` modes for controlling result volume
- Saves trace files as `data/<trace_id>.json` — OTel format via `export_traces_adk.py`, Langfuse format via `export_traces_agentops_v3.py`
- Works with remote hosted environments and local servers started with `--with-ibm-telemetry`
- `search_traces_agentops_v3.py` / `export_traces_agentops_v3.py` use the raw agentops-v3 REST API (bearer token from active env, no ADK SDK calls)

### Bug detection
Detected from normalized spans, supporting both OTel (`traceData.resourceSpans[0].scopeSpans[0].spans`) and Langfuse (`observations[]`) formats:

- **Hard errors** — any span with `status.code == STATUS_CODE_ERROR`
- **LLM failures** — `finish_reason == "length"`, empty `answer.task` output, zero output tokens (via `llm.token_count.completion` / `gen_ai.usage.output_tokens` attributes)
- **Tool call failures** — empty `ToolMessage` content in `*.tool` spans, retry loops, `duration_ms` > 30 000 ms
- **Agent logic bugs** — missing `answer.task` span, empty final answer, repeated `agent.task` cycles (multi-step loop), empty collaborator output
- **Flow issues** — `has_error` on any span, `widget_result.task` or `collaborator.task` with empty output
- **Token anomalies** — cumulative token totals exceeding 50 000, high input:output token ratio
- **Cache efficiency** — total cache-read tokens, cache hit rate below 20 % on multi-turn threads, zero cache reads across ≥ 3-turn threads, cache-write/read imbalance

### Conversational flow analysis
- Detects trace format and extracts `thread_id` from the correct location:
  - OTel: `traceloop.association.properties.thread_id` or `thread.id` span attribute
  - Langfuse: `metadata.attributes.thread_id` or `sessionId` top-level field
- Searches the local trace cache and the API for all traces belonging to a thread
- Reconstructs user message, routing decision, collaborator steps, and final response per turn
- Flags turns where the agent returned no response or encountered an error

## Output format

The analyzer produces:

1. **Bug Report** (HTML artifact for 3+ issues, inline for fewer)
   - Report header with agent ID, name, environment, date, and UTC time window
   - Executive Summary with KPI stat cards (for 10+ traces)
   - Categorical trace summary table grouped by routing pattern or error type
   - Per-trace detail table with start time, span count, token counts, and status
   - 🔴 Critical Issues, 🟠 Warnings, and 🟡 Observations tables with affected trace IDs
   - 🛠️ Fix Recommendations with root cause and actionable steps per issue

2. **Conversational Flow Report** (HTML artifact, thread-scoped)
   - Thread metadata: thread ID, turn count, agent, environment, time window, overall outcome
   - Per-turn timeline: user message, routing decision, collaborator steps, response delivered, token counts, error flags
   - Full span timing breakdown across all turns in the thread
   - Root cause summary comparing what worked vs. what failed

## Supporting files

Scripts in `scripts/` (created on first use by Step 1 if not already present):

| Script | Output format | Auth mechanism | Notes |
|---|---|---|---|
| `search_traces_adk.py` | OTel | ADK `TracesController` | Cursor-based pagination, agent-name filter, rate-limit retry |
| `export_traces_adk.py` | OTel | ADK `TracesController` | Single or bulk export by trace ID |
| `search_traces_agentops_v3.py` | Langfuse | Bearer token from active env | Page-based pagination, returns all traces in time window |
| `export_traces_agentops_v3.py` | Langfuse | Bearer token from active env | `GET /v1/agentops-v3/traces/<id>`, no ADK SDK trace call |

Use the `*_agentops_v3.py` scripts when the environment uses the **agentops-v3 REST API**. Use the standard scripts for environments backed by the classic wxO Traces API.

---

## Step-by-step workflow

### Step 1: Verify helper scripts are present

> **File placement rules** — apply throughout all steps:
> - All Python scripts written to disk must be saved under `scripts/` (e.g. `scripts/my_helper.py`).
> - All output files (`.json` trace dumps, `.txt` ID lists, etc.) must be saved under `data/` (e.g. `data/trace_ids.txt`, `data/<trace_id>.json`).
> - Inline code snippets shown in this document are for reading and reasoning only — they are **not** written to disk unless explicitly instructed.

Before doing anything else, confirm the required scripts exist on disk:

```
scripts/search_traces_adk.py
scripts/export_traces_adk.py
scripts/search_traces_agentops_v3.py
scripts/export_traces_agentops_v3.py
```

If any are missing, use `write_file` to create them — the canonical source for each script is in the `scripts/` directory of this skill. Write each missing file to its correct path under `scripts/` before continuing to Step 2.

---

### Step 2: Determine the trace source

**If the user's request does not clearly state where the traces or agent reside, always use `ask_followup_question` to clarify before doing anything else.** Do not assume a source or proceed to Step 3 without a confirmed answer to all of the following that are not already clear from context:

- Is the environment **remote** (a hosted wxO instance) or **local** (a locally running server)?
- If remote — what is the **environment name** (e.g. the name used with `orchestrate env activate`)?
- If the user mentioned an agent — what is the **agent name or ID**?
- What **time window** should be searched (or should it default to the last 20 minutes)?

Once the source is confirmed, classify it as one of:

1. **Remote env** — a hosted watsonx Orchestrate environment activated with `orchestrate env activate`. Always try the `_agentops_v3.py` scripts first; fall back to the `_adk.py` scripts if the agentops-v3 search returns an error or zero traces. See Step 3A for the full fallback procedure.
2. **Local env — IBM telemetry profile** — a locally running orchestrate server started with `--with-ibm-telemetry`. The Traces API is available at `http://localhost:4321`. Use the `_adk.py` scripts directly — agentops-v3 is not available on local environments.
3. **Trace files on disk** — the user already has one or more `{trace_id}.json` files on disk ready to analyze. Confirm they are in the `data/` directory; if not, ask the user for the path before proceeding.

---

### Step 3: Export the trace files

#### Option A — Remote env (agentops-v3 first, ADK fallback)

For all remote environments, **always try `_agentops_v3.py` first**. Fall back to `_adk.py` only if the agentops-v3 search fails or returns zero traces.

**Step A1 — Try agentops-v3:**

```bash
# 1. Activate the target environment
orchestrate env activate <env-name>

# 2. Search traces via agentops-v3
python scripts/search_traces_agentops_v3.py \
    --start 2025-01-01T09:00:00Z --end 2025-01-01T21:00:00Z \
    --all --save-ids data/trace_ids.txt
```

If the command exits with a non-zero status **or** prints `Found 0 trace(s)`, proceed to Step A2. Otherwise, export the discovered traces:

```bash
# 3. Export all discovered traces
python scripts/export_traces_agentops_v3.py --ids-file data/trace_ids.txt
```

**Step A2 — Fall back to ADK (only if agentops-v3 failed or returned 0 traces):**

```bash
# 2. Search traces via ADK — IDs checkpointed to disk after every page
python scripts/search_traces_adk.py --agent-name "My Agent" \
    --start 2025-01-01T09:00:00Z --end 2025-01-01T21:00:00Z \
    --all --save-ids data/trace_ids.txt

# 3. Export all discovered traces
python scripts/export_traces_adk.py --ids-file data/trace_ids.txt
```

`search_traces_adk.py` uses cursor-based pagination, retries automatically on 429 rate-limit responses, and handles mid-run 401 token expiry by refreshing the client. Always pass `--save-ids` so trace IDs are checkpointed to disk page-by-page and are not lost on timeout.

Use `--limit N` (default 50) for a capped sample, `--all` to exhaust the full window, or `--count` for a quick volume figure before committing to a full export.

#### Option B — Local env (IBM telemetry profile)

```bash
# 1. Start the local server with IBM telemetry enabled
orchestrate server start --with-ibm-telemetry --accept-terms-and-conditions

# 2. Activate the local environment
orchestrate env activate local

# 3. Search and export — identical to Option A
python scripts/search_traces_adk.py --agent-name "My Agent" --last 30m --all \
    --save-ids data/trace_ids.txt
python scripts/export_traces_adk.py --ids-file data/trace_ids.txt
```

The local Traces API endpoint is `http://localhost:4321`. The scripts detect `is_local_dev()` automatically and set `service_names=["wxo-server"]` in the filter, which is required when `FORCE_SINGLE_TENANT=true`.

#### Option C — Trace files already on disk

Confirm the directory or file path with the user. **Always detect the format before reading spans.** Use this helper:

```python
import json

def detect_format(raw: dict) -> str:
    """Return 'otel' or 'langfuse'."""
    if isinstance(raw.get('traceData'), dict) and 'resourceSpans' in raw['traceData']:
        return 'otel'
    if 'resourceSpans' in raw:  # traceData sometimes omitted at root
        return 'otel'
    if 'observations' in raw:   # Langfuse / agentops-v3 REST response
        return 'langfuse'
    return 'langfuse'           # safe default for agentops-v3 output

def get_spans(raw: dict) -> list:
    """Return a flat list of span/observation dicts regardless of format."""
    fmt = detect_format(raw)
    if fmt == 'otel':
        td = raw.get('traceData') or raw
        return [
            s
            for rs in td.get('resourceSpans', [])
            for ss in rs.get('scopeSpans', [])
            for s in ss.get('spans', [])
        ]
    return raw.get('observations', [])
```

Load a file and get its spans:

```python
with open("data/<trace_id>.json") as f:
    raw = json.load(f)
fmt   = detect_format(raw)
spans = get_spans(raw)
print(f"Format: {fmt}, span/observation count: {len(spans)}")
```

If the user provides a directory, glob for `*.json` files and skip any files not matching the 32-character hex trace ID pattern.

---

### Step 4: Analyze raw spans for bugs

> **Single-trace shortcut:** If the user has asked to analyze exactly **one** trace (by ID or as a single file on disk), **skip Steps 4 and 5 entirely**. Jump straight to Step 7 to produce the conversational flow report for the thread that trace belongs to. Only return to Step 5 (bug report) if the user explicitly asks for one after seeing the flow report.

Load each trace file using `detect_format()` + `get_spans()` from Step 3C, then normalize every span with the adapter below before running any bug-detection logic.

#### 4.1 Format normalization

```python
from datetime import datetime, timezone

def normalize_span(s: dict, fmt: str) -> dict:
    """
    Return a uniform dict with these keys regardless of source format:
      name, start_utc, duration_ms, status_error (bool),
      input, output, attrs (dict: key -> scalar value)
    """
    if fmt == 'otel':
        start_ns  = int(s.get('startTimeUnixNano', 0))
        end_ns    = int(s.get('endTimeUnixNano', 0))
        start_utc = datetime.fromtimestamp(start_ns / 1e9, tz=timezone.utc)
        duration_ms = (end_ns - start_ns) / 1e6
        status_error = s.get('status', {}).get('code') in ('STATUS_CODE_ERROR', 2)
        attrs = {}
        for a in s.get('attributes', []):
            v = a['value']
            attrs[a['key']] = (
                v.get('stringValue') or v.get('intValue') or
                v.get('doubleValue') or v.get('boolValue')
            )
        input_val  = attrs.get('traceloop.entity.input')
        output_val = attrs.get('traceloop.entity.output')
    else:  # langfuse
        start_utc = datetime.fromisoformat(
            s.get('startTime', '1970-01-01T00:00:00Z').replace('Z', '+00:00'))
        end_str   = s.get('endTime') or s.get('startTime', '1970-01-01T00:00:00Z')
        end_dt    = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        duration_ms = (end_dt - start_utc).total_seconds() * 1000
        status_error = (s.get('level') == 'ERROR' or bool(s.get('statusMessage')))
        meta  = s.get('metadata') or {}
        attrs = dict(meta.get('attributes', {}))
        usage = s.get('usage') or {}
        if usage.get('input'):
            attrs['llm.usage.prompt_tokens'] = usage['input']
        if usage.get('output'):
            attrs['llm.usage.completion_tokens'] = usage['output']
        input_val  = s.get('input')
        output_val = s.get('output')

    return dict(
        name=s.get('name', ''),
        start_utc=start_utc,
        duration_ms=duration_ms,
        status_error=status_error,
        input=input_val,
        output=output_val,
        attrs=attrs,
    )

def get_attr(attrs: dict, key: str):
    """Read a scalar from the normalized attrs dict (works for both formats)."""
    return attrs.get(key)
```

Build the normalized span list at the start of every analysis:

```python
fmt    = detect_format(raw)
spans  = get_spans(raw)
nspans = [normalize_span(s, fmt) for s in spans]

llm_spans  = [n for n in nspans if n['name'] == 'WatsonxChatModel.chat']
tool_spans  = [n for n in nspans if 'collaborator' in n['name'].lower()
               or n['attrs'].get('openinference.span.kind') == 'TOOL']
```

**Field mapping reference** — use this table when reading span data:

| Concept | OTel key (in `attrs` after normalization) | Langfuse source (in `attrs` after normalization) |
|---|---|---|
| LLM input tokens | `llm.token_count.prompt` or `llm.usage.prompt_tokens` | `llm.usage.prompt_tokens` (from `usage.input`) |
| LLM output tokens | `llm.token_count.completion` or `llm.usage.completion_tokens` | `llm.usage.completion_tokens` (from `usage.output`) |
| LLM model | `llm.model_name` or `gen_ai.request.model` | `llm.model_name` or `model` top-level field |
| Thread ID | `traceloop.association.properties.thread_id` or `thread.id` | `thread_id` or `thread.id` |
| Finish reason | `llm.finish_reason` or `gen_ai.usage.finish_reasons` | `llm.finish_reason` |
| Cache read tokens | `gen_ai.usage.cache_read_input_tokens` or `llm.token_count.cache_read` | `gen_ai.usage.cache_read_input_tokens` or `usage.cacheReadInputTokens` (check raw obs) |
| Cache creation tokens | `gen_ai.usage.cache_creation_input_tokens` or `llm.token_count.cache_creation` | `gen_ai.usage.cache_creation_input_tokens` or `usage.cacheCreationInputTokens` (check raw obs) |
| Span/obs input | `input` (normalized field) | `input` (normalized field) |
| Span/obs output | `output` (normalized field) | `output` (normalized field) |
| LLM reasoning | inside `output` JSON → `additional_kwargs.reasoning` | inside `output` dict → `additional_kwargs.reasoning` |
| Tool call name | span `name` ending in `.tool` | SPAN observation `name` (e.g. `chat_with_collaborator_*`) |

For each trace collect: `start_utc`, span names, `duration_ms`, `status_error`, collaborator tool call output, final answer output, `thread_id` (from `attrs`), and cache token counts.

Look for the following bug categories. For each issue found, record the span `name`, `start_utc`, and relevant `attrs` values.

#### 4.2 Hard errors
- Any normalized span where `status_error == True`.
  - OTel source: `status.code == "STATUS_CODE_ERROR"` or `2`.
  - Langfuse source: `level == "ERROR"` or `statusMessage` is non-empty.
- Capture span `name`, `duration_ms`, and the `output` field for the error message.

#### 4.3 LLM failures
- `get_attr(n['attrs'], 'llm.finish_reason') == "length"` — context length exceeded (works for both formats after normalization).
- `WatsonxChatModel.chat` span with `duration_ms == 0` or absent — silent LLM failure.
- Token counts: use `llm.token_count.prompt` / `llm.token_count.completion` (OTel attrs) or `llm.usage.prompt_tokens` / `llm.usage.completion_tokens` (Langfuse, auto-added by `normalize_span`). Zero completion tokens with non-zero prompt tokens = failed generation.
- Unexpectedly high prompt token count — possible system prompt bloat.
- Cache token counts: see §4.8. After normalization, try `get_attr(attrs, 'gen_ai.usage.cache_read_input_tokens')` first; fall back to the raw Langfuse `usage` dict. If absent on all LLM spans, note as an observation (provider may not support caching).

#### 4.4 Tool / collaborator call failures
- Tool span / SPAN observation whose `output` field contains an empty or null `content` (i.e. `ToolMessage.content == ""`).
  - **Langfuse note:** an empty `content` on the immediate `chat_with_collaborator_*` SPAN is the normal async dispatch pattern — the real result arrives via the nested `collaborator` CHAIN observation. Only flag as a failure if the outer `collaborator` CHAIN `output` is also empty.
- Any tool span with `duration_ms` > 30 000 ms — timeout or hung call.
- Same collaborator tool called twice in a row — retry loop.

#### 4.5 Agent logic bugs
- No span/observation named `answer` (or `answer.task` in OTel) — agent never produced a final answer.
- `answer` span `output` is empty or whitespace-only.
- `agent` (or `agent.task`) span count > 2 — multi-step LLM loop (agent re-planning instead of delegating immediately).
- `collaborator` (or `collaborator.task`) span present but `answer` output is empty — collaborator returned nothing and supervisor silently swallowed it.
- Internal reasoning text present in `answer` output or `output.additional_kwargs.reasoning` before the user-facing reply — check both OTel and Langfuse paths.

#### 4.6 Flow / widget issues
- Span/observation named `widget_result` (Langfuse) or `widget_result.task` (OTel) with empty `output` — widget state machine stalled.
- `LangGraph` GENERATION (Langfuse) or `LangGraph.workflow` span (OTel) with `duration_ms` >> sum of child span durations — unexplained gap in the workflow.

#### 4.7 Token / cost anomalies
- Cumulative prompt + completion tokens across all `WatsonxChatModel.chat` spans exceeds 50 000.
- Prompt tokens >> completion tokens (ratio > 200:1) — system prompt dominates context, little room for conversation history.

#### 4.8 Cache efficiency

> **Langfuse format caveat:** Cache token attributes (`cacheReadInputTokens`, `cacheCreationInputTokens`) are **not reliably collected** in Langfuse-format traces. When the source format is Langfuse (`fmt == 'langfuse'`), attempt both the `metadata.attributes` and top-level `usage` fallback paths below. If both are absent after exhausting all fallbacks, set `cache_unsupported = True` for the trace and **skip all cache-related analysis, stat cards, table columns, and observations** for that trace. Do not flag missing cache attributes as a bug or observation for Langfuse-format traces — they are expected to be absent.

Extract per-`WatsonxChatModel.chat` normalized span, with a Langfuse `usage` dict fallback for cache fields that may not be hoisted into `metadata.attributes`:

```python
def get_cache_tokens(nspan: dict, raw_obs: dict = None) -> tuple:
    """
    nspan   — normalized span dict (attrs already flattened from either format).
    raw_obs — original Langfuse observation dict (optional), used as fallback
              for cache fields that are in usage but not in metadata.attributes.
    Returns (cache_read, cache_creation) as ints.
    """
    attrs = nspan['attrs']
    cache_read = (
        get_attr(attrs, 'gen_ai.usage.cache_read_input_tokens') or
        get_attr(attrs, 'llm.token_count.cache_read') or 0
    )
    cache_creation = (
        get_attr(attrs, 'gen_ai.usage.cache_creation_input_tokens') or
        get_attr(attrs, 'llm.token_count.cache_creation') or 0
    )
    # Langfuse-specific fallback: check top-level usage dict
    if raw_obs and not cache_read and not cache_creation:
        usage = raw_obs.get('usage') or {}
        cache_read     = usage.get('cacheReadInputTokens') or 0
        cache_creation = usage.get('cacheCreationInputTokens') or 0
    return int(cache_read), int(cache_creation)
```

Aggregate across all LLM normalized spans in the trace (pass both the normalized span and the original raw observation when the source is Langfuse):

```python
total_cache_read     = sum(get_cache_tokens(n, raw_obs=spans[i] if fmt=='langfuse' else None)[0]
                           for i, n in enumerate(llm_spans))
total_cache_creation = sum(get_cache_tokens(n, raw_obs=spans[i] if fmt=='langfuse' else None)[1]
                           for i, n in enumerate(llm_spans))

# For Langfuse traces: if both totals are still 0 after all fallbacks, cache data
# is not collected by this environment — mark the trace and skip cache analysis.
cache_unsupported = (fmt == 'langfuse') and (total_cache_read == 0) and (total_cache_creation == 0)

# Effective billable input = input_tokens - total_cache_read
# Cache hit rate = total_cache_read / (input_tokens - total_cache_creation)
#                 only meaningful when input_tokens > total_cache_creation > 0
denom = input_tokens - total_cache_creation
cache_hit_rate = (total_cache_read / denom) if (not cache_unsupported and denom > 0) else None
```

Flag the following — **only when `cache_unsupported` is False**:

- **Low cache hit rate** — `cache_hit_rate < 0.20` (< 20 %) on a trace that belongs to a thread with ≥ 3 turns. The system prompt is likely not structured for prefix caching or varies per turn.
- **Zero cache reads on multi-turn thread** — every `cache_read_input_tokens == 0` across ≥ 3 turns in the same thread. The cache is never being warmed or the prefix changes each turn.
- **Cache write/read imbalance** — `total_cache_creation > total_cache_read * 5` across the batch. The cache is being populated but rarely re-used (cache TTL mismatch or non-repeating prefix).
- **No cache attributes present (OTel only)** — if the format is OTel and neither key is present on any LLM span, note it as an observation: the provider may not support prompt caching, or instrumentation does not emit these fields. Do **not** emit this observation for Langfuse-format traces.

---

### Step 5: Produce the bug report *(multi-trace analysis only)*

> **Skip this step** when the analysis scope is a single trace. Proceed directly to Step 7 instead.

#### Report title

```
Telemetry Bug Report — <AgentName>
```

#### Report header

| Field | Value |
|---|---|
| Agent ID | `<uuid>` |
| Agent Name | `<name>` |
| Environment | Instance URL or `local` |
| Report Date | `YYYY-MM-DD` (UTC) |
| Time Window (UTC) | `YYYY-MM-DD HH:MM – YYYY-MM-DD HH:MM UTC` |

#### Executive Summary (for 10+ traces)

Two rows of 4 KPI stat cards each:

- **Row 1** — Total traces (note if sampled), failed count (`.stat-bad`), successful count (`.stat-ok`), time window duration.
- **Row 2** — Total cache-read tokens, cache hit rate as %, total LLM input tokens, avg/p95 duration. **If all traces in the batch are Langfuse format and `cache_unsupported` is True for every trace, omit the cache-read and cache hit rate stat cards entirely and render only a single row of 4 cards (total traces, failed, successful, avg/p95 duration).**

No prose paragraphs — stat cards only.

Required CSS:

```css
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
.stat-card { background: #f7f8fa; border: 1px solid #e5e7eb; border-radius: 6px; padding: 12px 14px; }
.stat-val  { font-size: 22px; font-weight: 700; color: #1f2328; }
.stat-lbl  { font-size: 12px; color: #57606a; margin-top: 2px; }
.stat-bad  .stat-val { color: #b91c1c; }
.stat-ok   .stat-val { color: #15803d; }
.stat-warn .stat-val { color: #b45309; }
```

Cache-specific stat card values to compute before rendering:

```python
# Exclude traces where cache data is known to be uncollected (Langfuse with no cache attrs)
cache_rows = [r for r in rows if not r.get("cache_unsupported")]

if cache_rows:
    total_cache_read_all     = sum(r.get("cache_read_tokens", 0)     for r in cache_rows)
    total_cache_creation_all = sum(r.get("cache_creation_tokens", 0) for r in cache_rows)
    total_input_cache        = sum(r.get("input_tokens", 0)          for r in cache_rows)

    denom_all = total_input_cache - total_cache_creation_all
    batch_cache_hit_rate = (total_cache_read_all / denom_all * 100) if denom_all > 0 else None

    cache_attrs_present = total_cache_read_all > 0 or total_cache_creation_all > 0
    hit_rate_display = f"{batch_cache_hit_rate:.1f}%" if cache_attrs_present else "N/A"
    hit_rate_class   = "stat-bad" if (cache_attrs_present and batch_cache_hit_rate is not None and batch_cache_hit_rate < 20) else "stat-ok"
    show_cache_cards = True
else:
    # All traces are Langfuse with no cache data — omit both cache stat cards
    show_cache_cards = False
```

#### Trace Summary section

**Part 1 — Categorical summary table** (group by routing pattern, error type, etc.):

| Category | Traces | LLM Calls (avg) | Tool Calls (avg) | Success Rate | Status |
|---|---|---|---|---|---|

**Part 2 — Per-trace detail table** (ordered by start time ascending):

If `show_cache_cards` is True (cache data available for at least some traces), use the full 7-column layout:

| Trace ID | Start Time (UTC) | Spans | LLM | In / Out / Cached Tokens | Cache Hit % | Status |
|---|---|---|---|---|---|---|

`In / Out / Cached Tokens` — display as three values separated by ` / `, e.g. `12 450 / 320 / 8 100`. Show `—` for Cached on a specific row when that trace has `cache_unsupported == True`.
`Cache Hit %` — `cache_read_tokens / (input_tokens - cache_creation_tokens) * 100`, formatted as `42 %`. Show `—` for rows where `cache_unsupported == True`.

If `show_cache_cards` is False (all traces are Langfuse with no cache data), **drop the "Cached Tokens" and "Cache Hit %" columns** and use the 5-column layout:

| Trace ID | Start Time (UTC) | Spans | LLM | In / Out Tokens | Status |
|---|---|---|---|---|---|

Rules:
- For > 10 traces: omit rows with ✅ OK status — only include failed (❌) and warning (⚠) traces to keep the report compact.
- For ≤ 10 traces: include all traces regardless of status.
- Trace IDs must never be truncated — display full 32-character hex. Use `white-space: nowrap; font-family: monospace` on the Trace ID cell.

#### Issues and Warnings tables

| # | Span | Type | Description | Evidence | Affected Traces |
|---|------|------|-------------|----------|-----------------|

HTML rendering rules — apply these **exactly** to prevent column overflow:

1. **Table layout** — always set `table-layout: fixed; width: 100%` and declare explicit `<colgroup>` widths so the browser cannot let any column expand beyond its allocation:
   ```html
   <table style="table-layout:fixed; width:100%">
     <colgroup>
       <col style="width:3%">   <!-- # -->
       <col style="width:12%">  <!-- Span -->
       <col style="width:7%">   <!-- Type -->
       <col style="width:28%">  <!-- Description -->
       <col style="width:28%">  <!-- Evidence -->
       <col style="width:22%">  <!-- Affected Traces -->
     </colgroup>
     …
   </table>
   ```

2. **Every `<td>` and `<th>`** — add `overflow: hidden` to hard-clip any content that would otherwise bleed into the next column:
   ```html
   <td style="overflow:hidden; word-break:break-word">…</td>
   ```

3. **Evidence column** — allow wrapping and use `<br>` between individual evidence items. Do **not** set a fixed `max-width` — let the percentage-based `<colgroup>` width scale with the container:
   ```html
   <th>Evidence</th>
   <td style="overflow:hidden; word-break:break-word">
     <code>field: value</code><br>
     <code>field: value</code>
   </td>
   ```

4. **Affected Traces column** — use `word-break: break-all` (not `nowrap`) so long hex IDs wrap within the cell, and put each ID on its own line:
   ```html
   <th>Affected Traces</th>
   <td style="overflow:hidden; word-break:break-all; font-family:monospace; font-size:11px">
     tid1<br>tid2<br>…
   </td>
   ```

For Observations (prose), end each bullet with affected trace IDs in parentheses.

**Cache efficiency observations** — add the following bullets when applicable. **Skip all cache observations entirely when `show_cache_cards` is False** (all-Langfuse batch with no cache data):

- **No cache attributes found (OTel only)** — the format is OTel and neither `gen_ai.usage.cache_read_input_tokens` nor `llm.token_count.cache_read` was present on any LLM span. The provider may not support prompt caching, or the traceloop-sdk version predates cache attribute emission. (list affected trace IDs)
- **Zero cache reads on multi-turn thread** — `cache_read_input_tokens == 0` across all turns in thread `<thread_id>` (≥ 3 turns). The cache is never warmed; the static system prompt prefix likely changes per turn or is too short to cache. (list affected trace IDs)
- **Cache write/read imbalance** — `total_cache_creation_tokens` (`N`) is more than 5× `total_cache_read_tokens` (`M`) across the batch. The prompt-cache prefix is being written but not re-used — likely a cache TTL expiry or a prefix that varies each turn. (list affected trace IDs)

#### Fix Recommendations

For each critical issue and warning:

```
Issue: <description>
Root Cause: <likely cause>
Recommended Fix:
- <actionable step 1>
- <actionable step 2>
```

**Cache hit rate fix recommendation template** — include when cache hit rate < 20 % or zero cache reads observed on multi-turn threads:

```
Issue: Low prompt-cache hit rate (<X % batch average)
Root Cause: The system prompt either varies per turn, is not positioned at the start of
            the messages array, or the cache TTL expired between turns in long-gap threads.
Recommended Fix:
- Pin the static system prompt as the first message so the LLM provider can cache the
  longest common prefix across turns.
- Avoid injecting dynamic content (timestamps, user IDs, session state) into the system
  prompt — move that to the user turn instead.
- For Anthropic: add `cache_control: {"type": "ephemeral"}` to the last static content
  block to explicitly mark the cacheable prefix boundary.
- For OpenAI: ensure repeated calls use an identical token-level prefix of ≥ 1 024 tokens;
  caching is automatic but the prefix must be byte-for-byte identical.
- Verify the inter-turn gap is within the provider cache TTL: ~5 min for OpenAI and
  Anthropic ephemeral caches. For long-running sessions, refresh the cache before TTL
  expiry by issuing a short warm-up prompt.
- If cache attributes are absent entirely, upgrade the traceloop-sdk to a version that
  emits `gen_ai.usage.cache_read_input_tokens` / `gen_ai.usage.cache_creation_input_tokens`.
```

Render as `create_html_artifact` for 3+ issues; inline for fewer.

**HTML report outer wrapper** — use `width: 80%` centred with `margin: 0 auto` so the report occupies 80 % of the page width:

```html
<div style="width:80%; margin:0 auto; padding:20px 0; font-family:-apple-system,'Segoe UI',system-ui,sans-serif; font-size:14px; line-height:1.6">
  <!-- all report content here -->
</div>
```

---

### Step 6: Offer conversational flow report *(multi-trace analysis only)*

After delivering the bug report, ask:

> "Would you like a conversational flow report for any specific trace? If so, provide a trace ID and I'll pull all traces under the same thread and produce a full thread-level flow report."

Use `ask_followup_question` with suggestions drawn from the failing trace IDs.

---

### Step 7: Produce conversational flow report for a thread

A conversational flow report is **thread-scoped** — one thread ID may span multiple traces (one per user turn).

#### 7.1 Extract the thread_id

Use `detect_format()` from Step 3C, then read the thread ID from the correct location:

```python
import json

with open(f"data/{trace_id}.json") as f:
    raw = json.load(f)

fmt = detect_format(raw)
thread_id = None

if fmt == 'otel':
    spans = get_spans(raw)
    for s in spans:
        for a in s.get('attributes', []):
            if a['key'] in ('traceloop.association.properties.thread_id', 'thread.id'):
                thread_id = a['value']['stringValue']
                break
        if thread_id:
            break
else:  # langfuse
    # 1. Check top-level metadata.attributes (most reliable)
    meta_attrs = (raw.get('metadata') or {}).get('attributes', {})
    thread_id = (
        meta_attrs.get('thread.id') or
        meta_attrs.get('thread_id') or
        meta_attrs.get('langfuse.session.id') or
        raw.get('sessionId')   # Langfuse session == wxO thread
    )
    # 2. Fall back to any observation's metadata.attributes
    if not thread_id:
        for obs in raw.get('observations', []):
            obs_attrs = (obs.get('metadata') or {}).get('attributes', {})
            thread_id = obs_attrs.get('thread_id') or obs_attrs.get('thread.id')
            if thread_id:
                break

print(f"format: {fmt}, thread_id: {thread_id}")
```

#### 7.2 Collect all traces for the thread

First scan the local cache for matching `thread_id`, then search the API for any traces not yet downloaded. Re-run the local scan after downloading new files. If the wxO token is expired, work with cached traces only and note how many turns were found vs. potentially missing.

#### 7.3 Build the thread timeline

Sort all matched traces by `start_utc` ascending. For each trace call `detect_format()` + `normalize_span()` and extract using the unified field names:

| What to extract | OTel span name | Langfuse observation name | Field on normalized span |
|---|---|---|---|
| User message | `POST /orchestrate/runs` or `LangGraph.workflow` | `POST /chat/completions` GENERATION | `input` (top-level content string) |
| LLM call count | count of `WatsonxChatModel.chat` spans | count of `WatsonxChatModel.chat` GENERATIONs | `name == 'WatsonxChatModel.chat'` |
| Input / output tokens | `llm.token_count.prompt` / `.completion` attrs | `llm.usage.prompt_tokens` / `.completion_tokens` attrs (auto-added) | `get_attr(attrs, 'llm.usage.prompt_tokens')` etc. |
| Cache tokens | `gen_ai.usage.cache_read_input_tokens` attr | `usage.cacheReadInputTokens` (raw obs fallback) | `get_cache_tokens(nspan, raw_obs)` |
| Collaborator routing | `chat_with_collaborator_*.tool` span `output` | SPAN obs `chat_with_collaborator_*` → `output.content` | `output` field |
| Collaborator steps | `collaborator.task`, `tools.task`, `entrypoint.task` spans | CHAIN obs `collaborator`, `tools`, `LangGraph[collaborator:*]` | `name`, `duration_ms`, `output` |
| Final answer | `answer.task` span `output` | CHAIN obs `answer` → `output` | `output` field |
| Error flag | `status_error == True` on any span | `status_error == True` on any obs | `n['status_error']` |
| LLM reasoning | `output` JSON → `additional_kwargs.reasoning` | `output` dict → `additional_kwargs.reasoning` | parse `n['output']` |

#### 7.4 Render the conversational flow report

Produce a `create_html_artifact` with four sections:

1. **Thread Metadata** — thread ID, turn count, agent, environment, start/end time, total duration, overall outcome.
2. **Conversation Turns** — vertical timeline per turn: user message, routing decision, collaborator steps, response delivered (or red "NO RESPONSE" flag), duration, token counts (in / out / cached), cache hit % for the turn, error flags.
3. **Span Timing Breakdown** — table of every span across all turns: `Turn | Seq | Span name | Actor | Duration (ms) | Status`.
4. **Root Cause Summary** — two-column table comparing what worked vs. what failed.

---

### Step 8: Offer further follow-up actions

After the conversational flow report, offer:

1. **Deep-dive a specific span** — re-read the raw `data/{tid}.json`, detect format, and show full input / output content (`traceloop.entity.input` / `traceloop.entity.output` for OTel; `input` / `output` top-level fields for Langfuse). Use `normalize_span()` so the same display code works for both.
2. **Re-run after a fix** — guide the user to re-export and re-inspect after applying a fix.
3. **Batch analysis** — loop over multiple raw trace files directly using the inline Python pattern from Step 4.
4. **Compare two traces** — diff the span sequences (names, durations, collaborator calls) of two raw traces to identify regressions.
