---
name: wxo-builder
description: >-
  Expert guide for building, testing, and publishing IBM watsonx Orchestrate
  solutions. Use when the user wants to: create or scaffold agents/tools/flows
  from a prompt or SOP; import/deploy to local, SaaS, or on-prem; test
  single-turn or multi-turn against a live environment; debug import or runtime
  failures; publish to production; embed a deployed agent in a web app via the
  runtime REST API; or use the `orchestrate` CLI / ADK
  (`ibm-watsonx-orchestrate`). Also covers multi-agent collaborators, knowledge
  bases, connections, custom models, MCP toolkits, and document processing flows.
tags:
  - watsonx-orchestrate
  - wxo
  - agent-development
  - workflow-automation
  - sop-to-code
---

# watsonx Orchestrate (wxO) — Build · Test · Debug · Publish

End-to-end guide grounded in the ADK source and `orchestrate` CLI (current: `ibm-watsonx-orchestrate` 2.12.x).

> **Golden rule:** the ADK moves fast. Always verify uncertain commands/flags with
> `orchestrate <group> --help`. Upgrade: `pip install -U ibm-watsonx-orchestrate` (Python ≥3.11, <3.15).

**⚠️ Pre-flight:** activate the venv (`source .venv/bin/activate`) · always import + test after code generation.

---

## 1. Mental Model

watsonx Orchestrate runs **agents** that route user requests to **tools**, **collaborators**, and **knowledge bases**, powered by an **LLM**.

| Resource | What it is | Defined as |
|---|---|---|
| **Agent** | LLM-driven assistant. Kinds: `native`, `external` (A2A), `assistant` | YAML `kind: native` |
| **Tool** | Callable capability | Python `@tool`, OpenAPI spec, `@flow`, or Langflow |
| **Flow** | Multi-step workflow exposed as a tool | Python `@flow` (`build_<name>(aflow: Flow) -> Flow`) |
| **Toolkit** | Bundle of tools from an MCP server | `orchestrate toolkits add -k mcp …` |
| **Connection** | Stored credentials for an external service | YAML `kind: connection` + `connections` CLI |
| **Model** | LLM available to agents | YAML `kind: model` via the AI Gateway |
| **Knowledge base** | Documents for RAG/grounding | YAML `kind: knowledge_base` |

---

## 2. Setup

The VS Code extension auto-creates the venv at `.venv/` and installs the ADK. Just activate it:
```bash
source .venv/bin/activate && orchestrate --version
```
Manual setup (outside VS Code extension):
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -U ibm-watsonx-orchestrate
```

---

## 3. Environment Connection

`orchestrate` targets the **active environment** (starred in `orchestrate env list`). Confirm before importing.

### SaaS (IBM Cloud)
Use the **API service URL** (containing `/instances/<id>`), not the console URL.
```bash
orchestrate env add -n my-saas \
  -u https://api.<region>.watson-orchestrate.cloud.ibm.com/instances/<INSTANCE_ID>
orchestrate env activate my-saas --api-key "$IBM_CLOUD_API_KEY"
orchestrate agents list          # confirm connected
```
Auth type auto-inferred (`ibm_iam`). Override with `--type [ibm_iam|mcsp|mcsp_v2|cpd]`.

### On-prem (Cloud Pak for Data)
```bash
orchestrate env add -n my-onprem -u https://<cpd-host>/orchestrate --type cpd
orchestrate env activate my-onprem --api-key "$CPD_API_KEY"
# or: -u "$CPD_USER" -p "$CPD_PASSWORD"
```

### Local Developer Edition (optional — offline iteration)
Requires Docker, 16 GB RAM / 8 cores / 25 GB disk, and an entitlement key in `.env`.
```bash
orchestrate server start -e .env --accept-terms-and-conditions
orchestrate env activate local
```

```bash
orchestrate env list                  # ★ = active; orchestrate env activate <name>; orchestrate env remove --name <name>
```
> Keep secrets in a gitignored `.env`; pass via `"$VAR"` to stay out of shell history.

---

## 4. Canonical Lifecycle

Dependencies must be imported **before** the thing that references them:
```
write tools + connections/models/KB → write agent YAML
  → import-all.sh (connections → models → KB → tools/toolkits → agent)
  → test gate (§9) → debug + re-import → deploy to production (§13)
```

### Project scaffold
```
my_agent/
├── agents/         *.yaml
├── tools/          *.py  (one @flow per file; @tool files self-contained)
├── connections/    *.yaml
├── knowledge_base/ *.yaml + source docs
├── models/         *.yaml  (custom models only)
├── import-all.sh   dependency-ordered imports
├── delete-all.sh
└── .env            secrets (gitignored)
```

---

## 5. Python Tools (`@tool`)

```python
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from pydantic import BaseModel

class WeatherInfo(BaseModel):
    city: str
    temp_c: float

@tool(permission=ToolPermission.READ_ONLY)
def get_weather(city: str) -> WeatherInfo:
    """Get current weather for a city.

    Args:
        city (str): Name of the city.
    Returns:
        WeatherInfo: Temperature in Celsius for the city.
    """
    return WeatherInfo(city=city, temp_c=21.1)
```

**Must-haves:** `@tool` on every callable · Google-style docstring (summary → `Args:` → `Returns:`, **no blank line between them**) · type hints on all params and return · self-contained file (no cross-file local imports) · Pydantic models as explicit classes · never add `ibm-watsonx-orchestrate` to `requirements.txt`.

### Credentials
Never pass credentials as function parameters — declare them in `expected_credentials` and fetch at runtime:
```python
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType, ExpectedCredentials
from ibm_watsonx_orchestrate.run import connections

APP_ID = "my_api"

@tool(permission=ToolPermission.READ_ONLY,
      expected_credentials=[ExpectedCredentials(app_id=APP_ID, type=ConnectionType.API_KEY_AUTH)])
def call_api(query: str) -> dict:
    """Call the API.

    Args:
        query (str): Search text.
    Returns:
        dict: API response.
    """
    conn = connections.api_key_auth(APP_ID)   # .api_key · .token · .username/.password · .access_token
    headers = {"Authorization": f"Bearer {conn.api_key}"}
```

```bash
orchestrate tools import -k python -f tools/api_tool.py --app-id my_api
```

Full decorator signature, ConnectionType values, and Pydantic patterns → **[references/agents-tools-schemas.md §2](references/agents-tools-schemas.md)**.

---

## 6. Flows (`@flow`)

```python
from pydantic import BaseModel
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END

class MyInput(BaseModel):
    city: str

@flow(name="weather_flow", display_name="Weather Flow",
      description="Fetch and summarise weather", input_schema=MyInput)
def build_weather_flow(aflow: Flow) -> Flow:
    fetch = aflow.tool(get_weather)
    summarize = aflow.prompt(
        name="summarize",
        system_prompt="You format weather data for users.",   # REQUIRED
        user_prompt=["Summarize: {weather}"],
        llm="groq/openai/gpt-oss-120b",
    )
    aflow.sequence(START, fetch, summarize, END)
    return aflow
```

**Must-haves:** signature exactly `def build_<name>(aflow: Flow) -> Flow:` · one flow per file · `system_prompt` required on `aflow.prompt(...)` · `map_input`/`map_output` expressions are single-line Python only · wire with `aflow.sequence(START, …, END)` or `aflow.edge(a, b)`.

**Default LLM:** `groq/openai/gpt-oss-120b`

**Node builders:** `aflow.tool(fn)` · `aflow.prompt(...)` · `aflow.userflow(...)` · `aflow.agent(...)` · `aflow.docext(...)` · `aflow.docclassifier(...)` · `aflow.docproc(...)` · `aflow.script(...)` · `aflow.foreach(...)` · `aflow.conditions(...)` · `aflow.parallel_conditions(...)`.

**Programmatic test:**
```python
import asyncio
async def main():
    fdef = await build_weather_flow().compile_deploy()
    await fdef.invoke({"city": "Paris"}, debug=True)   # debug=True prints node I/O
asyncio.run(main())
```

Full flow node API (parallel, private schema, decisions, callbacks, masking, dynamic forms, docproc/KVP) → **[references/agents-tools-schemas.md §3–4](references/agents-tools-schemas.md)**.

---

## 7. Agent YAML

```yaml
spec_version: v1                # REQUIRED
kind: native                    # REQUIRED
name: weather_agent             # snake_case, no spaces
description: Returns weather information for a location.   # REQUIRED — drives routing
instructions: >
  You are a helpful weather assistant. When the user asks about weather,
  call get_weather with the city name and present the result clearly.
llm: groq/openai/gpt-oss-120b
style: react_intrinsic          # 2.12.0 default; `default` & `react` are DEPRECATED
tools:
  - get_weather
starter_prompts:
  is_default_prompts: false
  prompts:
    - id: default0
      title: Check weather
      prompt: What's the weather in Boston?
      state: active
welcome_content:
  is_default_message: false
  welcome_message: Welcome to the Weather Agent
  description: Ask me about the weather in any city.
```

Always include `starter_prompts` (2–4 prompts) and `welcome_content` — they improve UX substantially.

**Key constraints:**
- `spec_version: v1` and `kind: native` are mandatory — omitting either fails import.
- `tools`/`collaborators`/`knowledge_base` list resources by **name** (must be imported first).
- `toolkits` only valid for `experimental_customer_care` style.
- Reference by `name` (snake_case), never display name. Use `orchestrate agents list -v` to find names.

### Production-grade fields
```yaml
compaction_settings:            # prevent context overflow
  context_compaction_enabled: true
  context_compaction_threshold: 20000
  compaction_sliding_window: 10
llm_config:                     # per-agent decoding params (2.11+)
  temperature: 0
  max_tokens: 2048
is_schedulable: true            # ⚠ must be enabled at tenant level first; YAML alone silently resets
```

### Multi-agent (collaborators)
```yaml
name: dr_house_advise
style: react_intrinsic          # experimental_customer_care does NOT support collaborators
tools:
  - differential_diagnosis
collaborators:                  # import/deploy collaborators FIRST
  - dr_wilson
  - dr_cuddy
```
wxO auto-generates `chat_with_collaborator_<name>` per collaborator. Routing is driven by the **collaborator's `description`** — make it distinct. Nesting works. An agent cannot list itself.

Full schema (external/assistant kinds, `guidelines`, `structured_output`, `chat_with_docs`, `memory_enabled`, Python API) → **[references/agents-tools-schemas.md §1](references/agents-tools-schemas.md)**.

---

## 8. Import (dependency-ordered)

```bash
# import-all.sh
#!/usr/bin/env bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

orchestrate connections import   -f "${SCRIPT_DIR}/connections/my_api.yaml"
orchestrate models import        -f "${SCRIPT_DIR}/models/granite.yaml" --app-id watsonx_credentials
orchestrate knowledge-bases import -f "${SCRIPT_DIR}/knowledge_base/kb.yaml"
orchestrate tools import -k python -f "${SCRIPT_DIR}/tools/weather.py"
orchestrate tools import -k python -f "${SCRIPT_DIR}/tools/api_tool.py" --app-id my_api
orchestrate tools import -k flow   -f "${SCRIPT_DIR}/tools/weather_flow.py"
# MCP toolkit (if any):
orchestrate toolkits add -k mcp -n my_toolkit --description "My MCP tools" \
  --package-root ./mcp_server --language node \
  --command '["node","dist/index.js","--transport","stdio"]' --tools "*"
orchestrate agents import -f "${SCRIPT_DIR}/agents/weather_agent.yaml"
```

`tools import -k python|openapi|flow|langflow`. Use `--safe` to be prompted before overwriting.

---

## 9. Test Gate (verify before handover)

**Deployed ≠ verified.** Never declare "done" until tested — or the human explicitly declines.

After `./import-all.sh`, ask:
> "`<agent>` is deployed to `<env>`. Want me to smoke-test it? I'll run 1 single-turn + 1 multi-turn test — read-only prompts." — Yes / No

**If the `watsonx-orchestrate-adk` MCP server is available** — use `chat_with_agent` (pass `thread_id` from turn 1 to turn 2).

**CLI fallback:**
```bash
orchestrate chat ask -n <agent> "<prompt>" -r
# multi-turn: add -t <thread_id> on turn 2
```
> ⚠ On IBM Cloud SaaS, `chat ask` can hang in scripted use (live-verified 2.12.0). Use the runtime API (§14) as fallback.

**Pass criteria:** no error · on-topic answer · expected tool invoked (visible via `-r`) · multi-turn uses prior context.

Emit `TEST_REPORT.md`: "deployed and tested (2/2)", "deployed; test 2 failed — …", or "deployed; not tested at your request." State the target env. Keep tests read-only.

---

## 10. Connections

```yaml
spec_version: v1
kind: connection            # singular — NOT 'connections'
app_id: my_api
environments:
  draft:                    # at least 'draft'; add 'live' for production
    security_scheme: api_key_auth   # NOT 'kind:' — must be 'security_scheme:'
    type: team              # team (shared) | member (per-user)
    server_url: https://api.example.com
```

`security_scheme` values: `basic_auth` · `bearer_token` · `api_key_auth` · `oauth2` · `key_value_creds`.
OAuth2 `auth_type`: use `oauth2_auth_code` — **not** `authorization_code`.

```bash
orchestrate connections import -f connections/my_api.yaml
orchestrate connections configure -a my_api --kind api_key --type team --env draft
orchestrate connections set-credentials -a my_api --env draft --api-key "$MY_API_KEY"
orchestrate connections list
```

YAML defines structure only. **Never hardcode secrets** — always set via `set-credentials`.

Full schemas (OAuth2, key-value, configure `--kind` values) → **[references/connections-models-kb.md §1](references/connections-models-kb.md)**.

---

## 11. Models / LLMs

```bash
orchestrate models list   # what the active env offers (use full ids)
```

Default: `groq/openai/gpt-oss-120b` (also required for `experimental_customer_care`). Premier models disabled by default in 2.12+ — enable before referencing.

To add a custom watsonx.ai model: create a `watsonx_credentials` key-value connection, a `kind: model` YAML, then `orchestrate models import --app-id watsonx_credentials`. Full schema → **[references/connections-models-kb.md §2](references/connections-models-kb.md)**.

---

## 12. Knowledge Bases

```
Existing vector DB?
├─ No  → Built-in Milvus (managed, default — no external infra)
└─ Yes → AstraDB / external Milvus / Elasticsearch  (provider blocks in KB YAML)
         anything else (Pinecone, Weaviate, Qdrant, custom) → custom Python @tool
```

```bash
orchestrate knowledge-bases import -f kb.yaml
orchestrate knowledge-bases status -n product_docs   # watch indexing
```

Reference in agent YAML: `knowledge_base: [product_docs]`

Full YAML schemas for all providers + auth matrix → **[references/connections-models-kb.md §3](references/connections-models-kb.md)**.

---

## 13. Publishing to Production

No `publish` verb — publishing means activating the target env and re-importing.

```bash
orchestrate env activate prod      # registered once in §3
./import-all.sh                    # set env credentials first
orchestrate agents deploy   -n weather_agent
orchestrate agents undeploy -n weather_agent
```

One set of YAML/Python artifacts; only connection credentials and model `provider_config` differ per env. Version artifacts in Git; `import-all.sh` is the source of truth.

### Embedded web chat
```bash
orchestrate channels webchat embed --agent-name <agent> --env live
```
Paste the `<script>` into a page with `<div id="root">`.

⚠ **CRN gotcha (SaaS, live-verified 2.12.0):** auto-fetch 403s with instance-scoped API key. Extract from bearer token:
```bash
CRN=$(python -c "
import yaml, os, json, base64
t = yaml.safe_load(open(os.path.expanduser('~/.cache/orchestrate/credentials.yaml')))['auth']['<env>']['wxo_mcsp_token']
p = t.split('.')[1]; p += '=' * (-len(p) % 4)
print(json.loads(base64.urlsafe_b64decode(p))['unique_instance_crns'][0])")
echo "$CRN" | orchestrate channels webchat embed --agent-name <agent> --env live
```

---

## 14. Runtime REST API

For consuming a deployed agent from your own app (not the drop-in webchat widget).
Base: `<service-url>/api/v1` · bearer-token auth.

| Endpoint | Use case |
|---|---|
| `/orchestrate/{agent_id}/chat/completions` | OpenAI-compatible. Reply at `choices[0].message.content`. |
| `/orchestrate/runs` | Richer/async. Reply at `result.data.message.content[0].text`. |
| `/orchestrate/runs/stream` | Streaming variant. |

Both return `thread_id` — send it back to continue a conversation. **Never expose the bearer token to a browser** — proxy through your backend. Rule of thumb: `chat/completions` for portability, `/runs` for fidelity.

```bash
TOKEN=$(orchestrate env get-token)
BASE="https://api.<region>.watson-orchestrate.cloud.ibm.com/instances/<ID>/api/v1"
RESP=$(curl -s -X POST "$BASE/orchestrate/runs" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"agent_id":"<agent>","input":{"content":[{"type":"text","text":"Hello"}]}}')
THREAD=$(echo "$RESP" | jq -r '.thread_id')
# Turn 2: add "thread_id":"$THREAD" to the payload
```

---

## 15. Debugging Playbook

| Symptom | Cause → Fix |
|---|---|
| `agents import` required field error | Missing `spec_version`/`kind`/`name`/`description`, or dependency not imported yet. |
| Agent ignores a tool | Vague tool docstring; or instructions don't mention it. Improve docstring; name the tool in `instructions`. |
| Docstring/type-hint warnings on import | **Often a false positive in 2.12** — fires even when correct. Real cause: blank line between `Args:` and `Returns:`, or missing type hints. |
| "name cannot contain spaces" | Use snake_case for tool/toolkit/agent `name`. |
| `ModuleNotFoundError` at tool runtime | Add to `requirements.txt`; re-import with `-r`. Never add `ibm-watsonx-orchestrate`. |
| 401/403 on a tool call | Connection not configured or wrong `app_id`. `orchestrate connections list` → re-run `set-credentials`. |
| Works locally, missing in prod | Wrong active env. `orchestrate env list` → activate → re-import. |
| `No agents with the name 'X'` | Used display name. Get snake_case `name` from `orchestrate agents list -v`. |
| Flow won't compile | Check signature, `system_prompt`, single-line expressions. |
| Doc flow can't get uploaded file | `docproc` prompts the user — agent just invokes the flow, doesn't pass the file. |
| Need reasoning trace | `orchestrate chat ask -n <agent> "…" -r` (`-r` = reasoning, `-l` = logs). |
| Server issues | `orchestrate server logs`; `orchestrate server reset` to wipe state. |

Iterate: edit → re-import (overwrites by name) → re-test. Export: `orchestrate agents export -n <name> --kind native -o agents/<name>.yaml --agent-only`

---

## 16. MCP Servers

Both servers are always available — configured automatically by the VS Code extension in `.bob/mcp.json`.
Use fully qualified names when calling tools: `<ServerName>:<tool_name>`.

### `watsonx-orchestrate-adk-docs` (live documentation)
| Tool | Use |
|---|---|
| `watsonx-orchestrate-adk-docs:search_ibm_watsonx_orchestrate_adk` | Broad/conceptual queries |
| `watsonx-orchestrate-adk-docs:query_docs_filesystem_ibm_watsonx_orchestrate_adk` | Read specific pages (append `.mdx` to path) |

Workflow: `search_*` for discovery → `query_docs_filesystem_*` to read full pages.

### `watsonx-orchestrate-adk` (live platform — active env)
| Domain | Key tools |
|---|---|
| Agents | `list_agents` · `create_or_update_agent` · `import_agent` · `export_agent` · `remove_agent` |
| Tools | `list_tools` · `get_tool_template` · `import_tool` · `create_tool` · `remove_tool` |
| Toolkits | `list_toolkits` · `add_toolkit` · `import_toolkit` · `remove_toolkit` |
| Knowledge bases | `list_knowledge_bases` · `import_knowledge_bases` · `check_knowledge_base_status` · `remove_knowledge_base` |
| Connections | `list_connections` · `import_connection` · `configure_connection` · `set_credentials_connection` |
| Models | `list_models` · `import_model` · `create_or_update_model` · `import_model_policy` |
| Chat/test | `chat_with_agent` (pass `thread_id` for multi-turn; `include_reasoning=True` for trace) |
| Skills | `list_available_skills` · `fetch_skill` · `fetch_all_skills` · `check_version` |

---
## 17. Resources

| Source | Contents |
|---|---|
| **[references/agents-tools-schemas.md](references/agents-tools-schemas.md)** | Full agent YAML schema (all kinds), `@tool`/`@flow` decorator signatures, flow node API (parallel, private schema, decisions, callbacks, masking, dynamic forms), docproc/KVP |
| **[references/connections-models-kb.md](references/connections-models-kb.md)** | Connection YAML + CLI lifecycle, watsonx.ai model setup, KB provider configs (AstraDB/Milvus/Elasticsearch) |
| **[references/examples.md](references/examples.md)** | Complete worked examples: tool agent, KB agent, multi-agent chain, conditional flow, foreach, document extraction |
| **ADK docs** | https://developer.watson-orchestrate.ibm.com |
| **ADK examples** | https://github.com/IBM/ibm-watsonx-orchestrate-adk → `examples/` |
| **SDK source** | Same repo → `src/ibm_watsonx_orchestrate/` |

When a pattern isn't covered here, fetch a matching example from the public `examples/` directory.
**Always prefer live `orchestrate ... --help` over memory when a flag is in doubt.**
