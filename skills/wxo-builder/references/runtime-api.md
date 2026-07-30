# Runtime REST API — Embedding Agents in Your Application

For **consuming** a deployed agent from your own app (web/mobile backend, service, IDE,
another agent) — **not** the drop-in webchat widget (`orchestrate channels webchat`).

## Contents
- [§1 Base URL & auth](#1-base-url--auth)
- [§2 Endpoint families](#2-endpoint-families)
- [§3 OpenAI-compatible: `/chat/completions`](#3-openai-compatible-chatcompletions)
- [§4 Rich runs: `/orchestrate/runs`](#4-rich-runs-orchestrateruns)
- [§5 Multi-turn (thread_id)](#5-multi-turn-thread_id)
- [§6 Model-only completions](#6-model-only-completions)
- [§7 App-backend embedding pattern](#7-app-backend-embedding-pattern)
- [§8 Production gotchas](#8-production-gotchas)

---

## 1. Base URL & auth

**Base URL:** `<service-url>/api/v1`
- Local Developer Edition: `http://localhost:4321/api/v1`
- SaaS/on-prem: instance service URL + `/v1` (same URL used in `orchestrate env add`)

> ⚠ **SaaS path gotcha (live-verified 2.12.x, us-south):** runtime paths require
> `/v1/orchestrate/…` — `POST <base>/v1/orchestrate/runs` → 200; bare `/v1/runs` → **404**
> (`WXO-PROXY-14009E`). Never drop the `/orchestrate` segment on SaaS.

**Auth:** `Authorization: Bearer <token>` on every request.
```bash
# Get token (any env)
TOKEN=$(orchestrate env get-token)

# Or extract locally from cached credentials
TOKEN=$(python3 -c "import yaml,os; print(yaml.safe_load(
  open(os.path.expanduser('~/.cache/orchestrate/credentials.yaml')))
  ['auth']['local']['wxo_mcsp_token'])")
```
Tokens expire — refresh on `401`. **Never expose the bearer token to a browser** — proxy
through your backend.

**`agent_id`:** a UUID — get it from `orchestrate agents list -v` (copy the `id` field, not
the display name and not the snake_case `name`).

---

## 2. Endpoint families

| Endpoint | Shape | Use when |
|----------|-------|----------|
| `POST /orchestrate/{agent_id}/chat/completions` | OpenAI-compatible | Drop-in for anything speaking OpenAI Chat Completions. Simplest. |
| `POST /orchestrate/runs` + `GET /orchestrate/runs/{run_id}` | Rich, async | Need tool-step outputs, `llm_params`, guardrails, usage, async polling. |
| `POST /orchestrate/runs/stream` | Rich + SSE | Same richness, token-by-token streaming. |
| `POST /completions`, `POST /completions/chat` | Model only, no agent | Raw LLM via AI Gateway (no tool routing). |

**Rule of thumb:** `chat/completions` for portability, `orchestrate/runs` for fidelity.

---

## 3. OpenAI-compatible: `/chat/completions`

```bash
BASE="https://api.<region>.watson-orchestrate.cloud.ibm.com/instances/<ID>/api/v1"
curl -sX POST "$BASE/orchestrate/$AGENT_ID/chat/completions" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"stream": false, "messages": [{"role": "user", "content": "Hi"}]}'
```
Reply text: `choices[0].message.content` · Thread ID: top-level `thread_id`.

With `"stream": true` → SSE `data:` lines of `object: "thread.message.delta"`,
each with `choices[0].delta.content` chunk — concatenate to assemble reply.

---

## 4. Rich runs: `/orchestrate/runs`

**Start a run** (`agent_id` is in the *body*, not the path):
```bash
curl -sX POST "$BASE/orchestrate/runs" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message": {"role":"user","content":"Hi"}, "agent_id": "'"$AGENT_ID"'"}'
# → { "thread_id": "...", "run_id": "...", "task_id": "...", "message_id": "..." }
```

Poll for result:
```bash
curl -sX GET "$BASE/orchestrate/runs/$RUN_ID" -H "Authorization: Bearer $TOKEN"
# When status: "completed" → reply at result.data.message.content[0].text
# step_history carries tool outputs
```

**Streaming** (`/orchestrate/runs/stream` or `?stream=true`) SSE event sequence:
`run.started` → `message.started` → many `message.delta` (append `data.delta.content[*].text`)
→ `message.created` (final at `data.message.content[0].text`) → `run.completed` → `done`

---

## 5. Multi-turn (thread_id)

Both families return `thread_id`. Send it back to continue the conversation:
- `chat/completions`: include prior turns in `messages` **and** reuse `thread_id`
- `orchestrate/runs`: pass `"thread_id": "<id>"` in body alongside `message` and `agent_id`

Python apps → use the `RunClient` SDK wrapper; non-Python → call HTTP directly.

---

## 6. Model-only completions

```bash
# Prompt-based (no messages, no agent)
curl -sX POST "$BASE/completions" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"model": "mistralai/mistral-large", "prompt": "Hi"}'

# Messages-based
curl -sX POST "$BASE/completions/chat" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"model": "watsonx/meta-llama/llama-3-3-70b-instruct",
       "messages": [{"role":"user","content":"Hi"}], "stream": false}'
```

---

## 7. App-backend embedding pattern

```
browser ──user msg──▶ YOUR backend ──Bearer token──▶ wxO /orchestrate/runs(/stream)
        ◀─stream/text─┘  (holds token,            ◀── thread_id + reply
                          persists thread_id
                          per user session)
```

Checklist:
- Token in backend only — never in client JS; refresh on `401`
- Persist `thread_id` per user session for conversation memory
- Stream for chat UI (`/stream` or `stream:true`); poll for fire-and-forget
- Deploy first — agent must be imported **and** `deploy`-ed; `agent_id` is env-specific
- OpenAI clients → `chat/completions`; full control → `orchestrate/runs`

---

## 8. Production gotchas

| Issue | Detail |
|-------|--------|
| SaaS 404 on `/v1/runs` | Must use `/v1/orchestrate/runs` — do not drop `/orchestrate` segment |
| Standardized error codes | All proxy errors return JSON with machine-readable error code + `transaction_id` — log the ID for support |
| `chat_with_docs` via API | File upload to `/v1/orchestrate/upload-to-s3` (no trailing slash); but ingestion only works via chat UI / embedded widget — **not** via `/orchestrate/runs`. For programmatic RAG use `knowledge_base:` instead |
| `RunClient.upload_file_to_s3` bug | Posts to `/v1/upload-to-s3/` → 404 on SaaS; correct path is `/v1/orchestrate/upload-to-s3` (no trailing slash) |
| Context overflow | Enable `compaction_settings` on the agent (see agents-tools-schemas.md §1); auto-summarizes at ~20,000 tokens |
| Traces via API | `GET /v1/agentops-v3/traces/<trace_id>` → rich JSON; old `/v1/agentops/…` → 404 |
