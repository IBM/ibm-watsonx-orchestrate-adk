---
name: wxo-builder
description: >-
  Build, test, and publish IBM watsonx Orchestrate agents, tools, flows, connections,
  knowledge bases, and custom models using the `orchestrate` CLI and ADK.
tags:
  - watsonx-orchestrate
  - wxo
  - agent-development
  - workflow-automation
  - sop-to-code
---

# watsonx Orchestrate (wxO) — Build · Test · Debug · Publish

> **Golden rule:** the ADK moves fast. Always verify uncertain flags with `orchestrate <group> --help` — never rely on memory. Upgrade: `pip install -U ibm-watsonx-orchestrate` (Python ≥3.11, <3.15).
> **Pre-flight:** activate venv (`source venv/bin/activate`) · always import + test after code generation.

## 1. Mental Model

| Resource | What it is | Defined as |
|---|---|---|
| **Agent** | LLM-driven assistant. Kinds: `native`, `external` (A2A), `assistant` | YAML `kind: native` |
| **Tool** | Callable capability | Python `@tool`, OpenAPI spec, `@flow`, or Langflow |
| **Flow** | Multi-step workflow exposed as a tool | Python `@flow` (`build_<name>(aflow: Flow) -> Flow`) |
| **Toolkit** | Bundle of tools from an MCP server | `orchestrate toolkits add -k mcp …` |
| **Connection** | Stored credentials for an external service | YAML `kind: connection` + `connections` CLI |
| **Model** | LLM available to agents | YAML `kind: model` via the AI Gateway |
| **Knowledge base** | Documents for RAG/grounding | YAML `kind: knowledge_base` |

## 2. Setup & Environment

```bash
source venv/bin/activate && orchestrate --version   # venv auto-created by VS Code extension
# manual: python3 -m venv venv && source venv/bin/activate && pip install -U ibm-watsonx-orchestrate
```

`orchestrate` targets the **active environment** (`orchestrate env list`). Confirm before importing.

```bash
# SaaS — use API service URL (contains /instances/<id>), not the console URL
orchestrate env add -n my-saas -u https://api.<region>.watson-orchestrate.cloud.ibm.com/instances/<ID>
orchestrate env activate my-saas --api-key "$IBM_CLOUD_API_KEY"   # auth type auto-inferred (ibm_iam)
orchestrate agents list   # confirm connected
# Auth type override: --type [ibm_iam|mcsp|mcsp_v2|cpd]

# On-prem (CPD)
orchestrate env add -n my-onprem -u https://<cpd-host>/orchestrate --type cpd
orchestrate env activate my-onprem --api-key "$CPD_API_KEY"   # or: --username/--password

# Local Developer Edition (Docker, 16 GB RAM / 8 cores / 25 GB disk, entitlement key in .env)
orchestrate server start -e .env --accept-terms-and-conditions && orchestrate env activate local
```

`orchestrate env list` · `orchestrate env activate <name>` · `orchestrate env remove --name <name>`

> Keep secrets in a gitignored `.env`; pass via `"$VAR"` to stay out of shell history.

## 3. Canonical Lifecycle

```
write tools + connections/models/KB → write agent YAML
  → import-all.sh (connections → models → KB → tools/toolkits → agent)
  → test gate (§7) → debug + re-import → deploy to production (§11)
```

**Project scaffold:**
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

## 4. Python Tools (`@tool`)

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

**Credentials** — never pass as parameters; declare in `expected_credentials` and fetch at runtime:
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

## 5. Flows (`@flow`)

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

**Must-haves:** signature exactly `def build_<name>(aflow: Flow) -> Flow:` · one flow per file · `system_prompt` required on `aflow.prompt(...)` · `map_input`/`map_output` single-line Python only · wire with `aflow.sequence(START, …, END)` or `aflow.edge(a, b)`.

**Default LLM:** `groq/openai/gpt-oss-120b` · **Node builders:** `aflow.tool` · `aflow.prompt` · `aflow.agent` · `aflow.script` · `aflow.foreach` · `aflow.conditions` · `aflow.parallel_conditions` · `aflow.docext` · `aflow.docclassifier` · `aflow.docproc` · `aflow.userflow`

**Programmatic test:** `await build_weather_flow().compile_deploy()` then `.invoke({"city": "Paris"}, debug=True)`

Full flow node API → **[references/agents-tools-schemas.md §3–4](references/agents-tools-schemas.md)**.

## 6. Agent YAML

```yaml
spec_version: v1                # REQUIRED
kind: native                    # REQUIRED
name: weather_agent             # snake_case, no spaces
description: Returns weather information for a location.   # REQUIRED — drives routing
instructions: >
  You are a helpful weather assistant. When the user asks about weather,
  call get_weather with the city name and present the result clearly.
llm: groq/openai/gpt-oss-120b
style: react_intrinsic          # 2.12.0 default; `default` & `react` DEPRECATED
tools:
  - get_weather
starter_prompts:                # include 2–4; greatly improves UX
  is_default_prompts: false
  prompts: [{id: default0, title: Check weather, prompt: "What's the weather in Boston?", state: active}]
welcome_content:
  is_default_message: false
  welcome_message: Welcome to the Weather Agent
  description: Ask me about the weather in any city.
# Production extras:
# compaction_settings: {context_compaction_enabled: true, context_compaction_threshold: 20000, compaction_sliding_window: 10}
# llm_config: {temperature: 0, max_tokens: 2048}
# is_schedulable: true   # ⚠ must be enabled at tenant level first
```

**Key constraints:** `spec_version: v1` + `kind: native` mandatory · resources listed by **name** (imported first) · `toolkits` only for `experimental_customer_care` · snake_case `name`.

**Multi-agent (collaborators):**
```yaml
style: react_intrinsic   # experimental_customer_care does NOT support collaborators
collaborators:           # import/deploy collaborators FIRST
  - dr_wilson
  - dr_cuddy
```
wxO auto-generates `chat_with_collaborator_<name>` per collaborator. Routing driven by collaborator's **`description`** — make it distinct. Agent cannot list itself.

Full schema (external/assistant kinds, `guidelines`, `structured_output`, `chat_with_docs`, `memory_enabled`) → **[references/agents-tools-schemas.md §1](references/agents-tools-schemas.md)**.

## 7. Import (dependency-ordered)

> **Import rule — follow this priority order:**
> 1. **`import-all.sh` exists** → execute it. Always preferred.
>    ```bash
>    chmod +x import-all.sh && ./import-all.sh
>    ```
> 2. **`import-all.sh` does not exist** → create it first (connections → models → KB → tools → agent), then execute it.
> 3. **MCP tools** (`import_tool`, `import_agent`, etc.) → last resort only, when creating and running `import-all.sh` is not possible.

```bash
# import-all.sh template
source venv/bin/activate
orchestrate connections import   -f connections/my_api.yaml
orchestrate models import        -f models/granite.yaml --app-id watsonx_credentials
orchestrate knowledge-bases import -f knowledge_base/kb.yaml
orchestrate tools import -k python -f tools/weather.py
orchestrate tools import -k python -f tools/api_tool.py --app-id my_api
orchestrate tools import -k flow   -f tools/weather_flow.py
orchestrate agents import        -f agents/weather_agent.yaml
```

`-k` values: `python|openapi|flow|langflow`. Use `--safe` to prompt before overwriting.
MCP toolkit: `orchestrate toolkits add -k mcp -n <name> --description "…" --package-root ./mcp_server --language node --command '["node","dist/index.js"]' --tools "*"`

## 8. Test Gate (verify before handover)

**Deployed ≠ verified.** Never declare "done" until tested — or the human explicitly declines.

After `./import-all.sh`, ask:
> "`<agent>` is deployed to `<env>`. Want me to smoke-test it? I'll run 1 single-turn + 1 multi-turn — read-only prompts." — Yes / No

**Execute (preferred):** `watsonx-orchestrate-adk:chat_with_agent` — Turn 1 with `include_reasoning=True`, save `thread_id`, Turn 2 with same `thread_id`.
**CLI fallback:** `orchestrate chat ask -n <agent> "<prompt>" -r` (⚠ can hang on SaaS — use runtime REST API from `references/runtime-api.md` instead).

**Pass criteria:** no error · correct output · expected tool fired (check reasoning) · turn 2 uses context from turn 1.

**If a test fails — fix → re-import → re-test loop:** identify root cause from reasoning → fix `.py`/`.yaml` → `./import-all.sh` → re-run with `chat_with_agent`. Repeat until all pass.

Emit `TEST_REPORT.md`: `"deployed and tested (2/2)"` · `"deployed; test N failed — <reason>"` · `"deployed; not tested at your request."`

After testing, always tell the user how to test manually:
- **UI** — open the agent in the wxO web UI, use starter prompts or type directly.
- **CLI** — `orchestrate chat ask -n <agent_name> "<prompt>" -r` (`-r` = reasoning trace; ⚠ can hang on SaaS — use `chat_with_agent` MCP tool instead).
- **Bob** — *"Chat with `<agent_name>`: `<prompt>`"* — Bob calls `chat_with_agent` with `include_reasoning=True`.

Provide **3–5 sample prompts** covering: happy path · edge/unknown input · multi-turn. For each, state the expected output so the user knows what a pass looks like.

Full gate procedure + report template + pre-publish checklist → **[references/testing-debugging.md](references/testing-debugging.md)**.

## 9. Connections, Models, Knowledge Bases

**Connection YAML:**
```yaml
spec_version: v1
kind: connection       # singular — NOT 'connections'
app_id: my_api
environments:
  draft:
    security_scheme: api_key_auth   # NOT 'kind:' — must be 'security_scheme:'
    type: team                      # team (shared) | member (per-user)
    server_url: https://api.example.com
```
`security_scheme` values: `basic_auth` · `bearer_token` · `api_key_auth` · `oauth2` · `key_value_creds`.
OAuth2: use `oauth2_auth_code` — **not** `authorization_code`. YAML defines structure only — **never hardcode secrets**.
```bash
orchestrate connections import -f connections/my_api.yaml
orchestrate connections configure -a my_api --kind api_key --type team --env draft
orchestrate connections set-credentials -a my_api --env draft --api-key "$MY_API_KEY"
```

**Models:** `orchestrate models list` to see available IDs. Default: `groq/openai/gpt-oss-120b`. Premier models disabled by default in 2.12+. Custom watsonx.ai model: create a `watsonx_credentials` key-value connection + `kind: model` YAML → `orchestrate models import --app-id watsonx_credentials`.

**Knowledge bases:**
```
No existing vector DB → Built-in Milvus (default, no infra needed)
Existing DB          → AstraDB / Milvus / Elasticsearch (provider blocks in KB YAML)
Other (Pinecone etc) → custom Python @tool
```
```bash
orchestrate knowledge-bases import -f kb.yaml
orchestrate knowledge-bases status -n product_docs   # watch indexing
```
Reference in agent YAML: `knowledge_base: [product_docs]`

Full schemas → **[references/connections-models-kb.md](references/connections-models-kb.md)**.

## 10. Debugging Playbook

| Symptom | Cause → Fix |
|---|---|
| `agents import` required field error | Missing `spec_version`/`kind`/`name`/`description`, or dependency not imported yet |
| Agent ignores a tool | Vague docstring; tool not named in instructions → improve both |
| Docstring/type-hint warnings | **False positive in 2.12** — real cause: blank line between `Args:`/`Returns:`, or missing hints |
| "name cannot contain spaces" | Use snake_case |
| `ModuleNotFoundError` at runtime | Add to `requirements.txt`, re-import with `-r`. Never add `ibm-watsonx-orchestrate` |
| 401/403 on tool call | Wrong `app_id` or credentials not set → `orchestrate connections list` → re-run `set-credentials` |
| Works locally, missing in prod | Wrong active env → `orchestrate env list` → activate → re-import |
| `No agents with the name 'X'` | Used display name — get snake_case from `orchestrate agents list -v` |
| Flow won't compile | Check signature, `system_prompt` present, single-line expressions |
| Need reasoning trace | `orchestrate chat ask -n <agent> "…" -r` (`-r` reasoning, `-l` logs) |
| Server issues | `orchestrate server logs`; `orchestrate server reset` to wipe state |

Iterate: edit → re-import (idempotent by name) → re-test. Export: `orchestrate agents export -n <name> --kind native -o agents/<name>.yaml --agent-only`

Full failure-mode table + programmatic flow testing + observability/traces → **[references/testing-debugging.md](references/testing-debugging.md)**.

## 11. Publishing to Production

No `publish` verb — publishing = activate target env + re-import.
```bash
orchestrate env activate prod
./import-all.sh
orchestrate agents deploy   -n weather_agent
orchestrate agents undeploy -n weather_agent
```
One set of artifacts per project; only connection credentials and model `provider_config` differ per env.

**Embedded web chat:**
```bash
orchestrate channels webchat embed --agent-name <agent> --env live
```
⚠ **CRN gotcha (SaaS 2.12.0):** auto-fetch 403s — extract CRN from bearer token:
```bash
CRN=$(python -c "
import yaml,os,json,base64
t=yaml.safe_load(open(os.path.expanduser('~/.cache/orchestrate/credentials.yaml')))['auth']['<env>']['wxo_mcsp_token']
p=t.split('.')[1];p+='='*(-len(p)%4)
print(json.loads(base64.urlsafe_b64decode(p))['unique_instance_crns'][0])")
echo "$CRN" | orchestrate channels webchat embed --agent-name <agent> --env live
```

## 12. Runtime REST API

Base: `<service-url>/api/v1` · bearer-token auth (`orchestrate env get-token`). **Never expose the token to a browser — proxy through your backend.**

> ⚠ **SaaS path gotcha:** use `/v1/orchestrate/runs` not `/v1/runs` — bare path returns 404.

| Endpoint | Use |
|---|---|
| `/orchestrate/{agent_id}/chat/completions` | OpenAI-compatible. Reply at `choices[0].message.content` |
| `/orchestrate/runs` | Richer/async. Reply at `result.data.message.content[0].text`; `step_history` has tool outputs |
| `/orchestrate/runs/stream` | SSE streaming variant |
| `/completions/chat` | Raw LLM via AI Gateway — no agent/tools |

Both agent endpoints return `thread_id` — send it back to continue a conversation. Rule of thumb: `chat/completions` for portability, `/runs` for fidelity.

Full endpoint shapes, SSE event sequence, auth, multi-turn, file upload gotchas → **[references/runtime-api.md](references/runtime-api.md)**.

## 13. MCP Servers

`.bob/mcp.json` (Bob) / `.cursor/mcp.json` (Cursor) — replace `<VENV_PYTHON>` and `<WORKING_DIR>`:
```json
{
  "mcpServers": {
    "watsonx-orchestrate-adk-docs": {
      "command": "uvx",
      "args": ["mcp-proxy", "--transport", "streamablehttp", "https://developer.watson-orchestrate.ibm.com/mcp"]
    },
    "watsonx-orchestrate-adk": {
      "command": "<VENV_PYTHON>",
      "args": ["-m", "ibm_watsonx_orchestrate_mcp_server.server"],
      "env": {"WXO_MCP_WORKING_DIRECTORY": "<WORKING_DIR>"},
      "timeout": 300000
    }
  }
}
```

Use fully qualified names when calling MCP tools: `<ServerName>:<tool_name>`.

| Server | Key tools |
|---|---|
| `adk-docs` | `search_ibm_watsonx_orchestrate_adk` (broad) · `query_docs_filesystem_…` (read page by path, append `.mdx`) |
| `adk` (live platform) | `list/create_or_update/import/export/remove_agent` · `list/import/create/remove_tool` · `list/add/import/remove_toolkit` · `import/check_status/remove_knowledge_base` · `import/configure/set_credentials_connection` · `list/import/create_or_update_model` · `chat_with_agent` (add `thread_id` for multi-turn; `include_reasoning=True` for trace) |

## 14. References (load on demand)

| File | Contents |
|---|---|
| **[references/agents-tools-schemas.md](references/agents-tools-schemas.md)** | Full agent YAML schema (all kinds), `@tool`/`@flow` decorator signatures, all flow nodes (parallel, foreach, decisions, callbacks, masking, dynamic forms, docproc/KVP, docext, userflow, swarms) |
| **[references/connections-models-kb.md](references/connections-models-kb.md)** | Connection YAML + CLI lifecycle, watsonx.ai model setup, KB provider configs (AstraDB/Milvus/Elasticsearch) |
| **[references/examples.md](references/examples.md)** | Complete worked examples: tool agent, KB agent, multi-agent chain, conditional flow, foreach, document extraction |
| **[references/cli-reference.md](references/cli-reference.md)** | Full `orchestrate` CLI — every group, command, and flag |
| **[references/testing-debugging.md](references/testing-debugging.md)** | Post-deploy gate + TEST_REPORT template, failure-mode table, programmatic flow testing, traces/observability, pre-publish checklist |
| **[references/runtime-api.md](references/runtime-api.md)** | Runtime REST API: base URL/auth, endpoint families, SSE streaming, multi-turn, model-only completions, SaaS gotchas |
| **ADK docs** | https://developer.watson-orchestrate.ibm.com |
| **ADK examples** | https://github.com/IBM/ibm-watsonx-orchestrate-adk → `examples/` |

When a pattern isn't covered here, fetch a matching example from the public `examples/` directory.
