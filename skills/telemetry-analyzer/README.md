# Telemetry Analyzer

Skill for exporting, inspecting, and producing bug and conversational flow reports from watsonx Orchestrate agent telemetry traces.

Supports two trace formats: **OTel JSON** (classic wxO Traces API / IBM telemetry) and **Langfuse JSON** (agentops-v3 REST API). The skill detects the format automatically.

## Prerequisites

Before running any of the scripts, ensure the following are in place:

1. **watsonx Orchestrate ADK installed** — the `ibm-watsonx-orchestrate` package must be available in the active Python environment:
   ```bash
   pip install ibm-watsonx-orchestrate
   ```

2. **Virtual environment activated:**
   ```bash
   source venv/bin/activate
   ```

3. **wxO environment activated** — the orchestrate CLI must be authenticated and pointing at the correct tenant:
   ```bash
   orchestrate env activate <env-name>
   ```

4. **For local dev only** — the server must be started with the IBM telemetry profile:
   ```bash
   orchestrate server start --with-ibm-telemetry --accept-terms-and-conditions
   orchestrate env activate local
   ```

5. **`python-dotenv` installed** (optional but recommended — loaded automatically by the scripts):
   ```bash
   pip install python-dotenv
   ```

## Directory layout

```
.bob/skills/telemetry-analyzer/
├── SKILL.md                         # Skill instructions (read by Bob)
├── README.md                        # This file
├── scripts/                         # Helper scripts
│   ├── search_traces_adk.py             # OTel — cursor-based pagination via ADK TracesController
│   ├── export_traces_adk.py             # OTel — bulk/single export via ADK TracesController
│   ├── search_traces_agentops_v3.py # Langfuse — page-based search via agentops-v3 REST API
│   └── export_traces_agentops_v3.py # Langfuse — single/bulk export via agentops-v3 REST API
└── data/                            # Output — trace ID lists and exported JSON traces
```

The `scripts/` and `data/` directories are created automatically the first time the skill runs. You do not need to create them manually.

## Helper scripts

Two script pairs are provided — choose based on which API your environment uses:

### OTel scripts (classic wxO Traces API)

| Script | Purpose |
|--------|---------|
| `scripts/search_traces_adk.py` | Discover traces by agent name or ID. Cursor-based pagination, automatic 429 rate-limit retry, 401 token-expiry refresh. Always saves trace IDs to `data/` as it pages. Default window: last **20 minutes**. |
| `scripts/export_traces_adk.py` | Download individual or bulk traces by ID and save them as OTel JSON in `data/`. |

### agentops-v3 scripts (Langfuse format)

| Script | Purpose |
|--------|---------|
| `scripts/search_traces_agentops_v3.py` | Discover traces via `GET /v1/agentops-v3/traces`. Page-based pagination, automatic 429 retry. Saves trace IDs to `data/`. |
| `scripts/export_traces_agentops_v3.py` | Download individual or bulk traces via `GET /v1/agentops-v3/traces/<id>` and save as Langfuse JSON in `data/`. |

Auth for both agentops-v3 scripts is a bearer token obtained automatically from the active `orchestrate` environment — no extra configuration needed beyond running `orchestrate env activate <env-name>`.

## Quick start

### OTel environments

```bash
# Activate environment
orchestrate env activate <env-name>

# Search traces for an agent (last 20 minutes by default — IDs auto-saved to data/)
python scripts/search_traces_adk.py --agent-name "My Agent"

# Narrow or widen the window
python scripts/search_traces_adk.py --agent-name "My Agent" --last 30m
python scripts/search_traces_adk.py --agent-name "My Agent" --last 2h

# Explicit time range
python scripts/search_traces_adk.py --agent-name "My Agent" \
    --start 2025-01-01T09:00:00Z --end 2025-01-01T10:00:00Z

# Export all traces from a saved ID list
python scripts/export_traces_adk.py --ids-file data/<agent>_<timestamp>_ids.txt

# Export a single trace
python scripts/export_traces_adk.py --trace-id <32-char-hex-id>
```

### agentops-v3 environments (Langfuse format)

```bash
# Activate environment
orchestrate env activate <env-name> --api-key <API_KEY>

# Search all traces in the last 2 hours (IDs auto-saved to data/)
python scripts/search_traces_agentops_v3.py --last 2h

# Export a single trace by ID
python scripts/export_traces_agentops_v3.py --trace-id <32-char-hex-id>

# Bulk-export from a saved ID list
python scripts/export_traces_agentops_v3.py --ids-file data/traces_<timestamp>_ids.txt
```

## Trace source options

| Source | Script pair | Output format |
|--------|-------------|---------------|
| **wxO Traces API (remote)** | `search_traces_adk.py` + `export_traces_adk.py` | OTel JSON |
| **Local IBM telemetry** | `search_traces_adk.py` + `export_traces_adk.py` | OTel JSON |
| **agentops-v3 REST API** | `search_traces_agentops_v3.py` + `export_traces_agentops_v3.py` | Langfuse JSON |
| **JSON files already on disk** | — (point skill at `data/` directory) | OTel or Langfuse |

## Supported trace formats

| Format | Top-level key | Span list path | Produced by |
|--------|--------------|----------------|-------------|
| **OTel JSON** | `traceData` | `traceData.resourceSpans[].scopeSpans[].spans[]` | `export_traces_adk.py`, local IBM telemetry |
| **Langfuse JSON** | `observations` | `observations[]` (GENERATION / CHAIN / SPAN) | `export_traces_agentops_v3.py`, agentops-v3 REST API |

The skill detects the format automatically using `detect_format()` — no manual configuration needed.

## Rate limits

The wxO Traces API enforces strict rate limits (≈ 4 requests/min, 100 traces/page). The agentops-v3 API may also return 429. The scripts handle this automatically:

- **429** — reads `retry_after` from the response and waits before retrying (`search_traces_adk.py`, `search_traces_agentops_v3.py`)
- **401** — refreshes the ADK client token and retries the current page (`search_traces_adk.py` only)
- Trace IDs are checkpointed to `data/` after every page so a mid-run abort never loses progress

> **Note:** `export_traces_agentops_v3.py` does not retry on 429 — it marks the trace as failed and continues. If any exports fail with HTTP 429, re-run the export with the same `--ids-file`; successfully exported files are simply overwritten.
