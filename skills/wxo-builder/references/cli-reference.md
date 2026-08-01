# `orchestrate` CLI Reference

Verified against `ibm-watsonx-orchestrate` 2.13.x. CLI evolves fast — always confirm with
`orchestrate <group> --help`. Short flags in `()`.

## Contents
- [§1 env](#1-env)
- [§2 agents](#2-agents)
- [§3 tools](#3-tools)
- [§4 toolkits (MCP)](#4-toolkits--mcp)
- [§5 knowledge-bases](#5-knowledge-bases)
- [§6 connections](#6-connections)
- [§7 models](#7-models)
- [§8 server (Developer Edition)](#8-server--developer-edition)
- [§9 chat](#9-chat)
- [§10 channels · evaluations · observability · voice · others](#10-channels--evaluations--observability--voice--others)
- [§11 skills](#11-skills)
- [§12 venv bootstrap](#12-venv-bootstrap)

Top-level groups: `env`, `agents`, `tools`, `toolkits`, `knowledge-bases`, `connections`,
`models`, `server`, `chat`, `channels`, `settings`, `evaluations`, `observability`,
`voice-configs`, `phone`, `partners`, `skills`.
> Note plural **`toolkits`**, **`voice-configs`**, and **`skills`** group names.

---

## 1. env

| Command | Key options |
|---------|-------------|
| `env list` | — |
| `env add` | `--name(-n)`, `--url(-u)`, `--type(-t)`, `--iam-url(-i)`, `--activate(-a)`, `--insecure`, `--verify` |
| `env activate <name>` | `--api-key(-a)` (SaaS/CPD), `--username(-u)` (CPD), `--password(-p)` (CPD), `--skip-version-check` |
| `env remove` | `--name(-n)` |

```bash
orchestrate env list
orchestrate env add -n prod -u https://api.us-south.watson-orchestrate.cloud.ibm.com/instances/XXXX
orchestrate env activate prod --api-key "$IBM_CLOUD_API_KEY"
orchestrate env remove --name prod

# On-prem (CPD)
orchestrate env add -n my-onprem -u https://<cpd-host>/orchestrate --type cpd
orchestrate env activate my-onprem --api-key "$CPD_API_KEY"   # or: --username/--password
```
CLI config lives at `~/.config/orchestrate/config.yaml` (shows `context.active_environment`).

---

## 2. agents

| Command | Key options |
|---------|-------------|
| `agents import` | `--file(-f)`, `--app-id(-a)` (external), `--package-root`, `--config-file`, `--safe` |
| `agents create` | `--name(-n)`, `--kind(-k)`, `--description`, `--llm`, `--style`, `--instructions`, `--tools`, `--collaborators`, `--knowledge-bases`, `--output(-o)`, external: `--title(-t)`, `--api(-a)`, `--auth-scheme`, `--provider(-p)`, `--auth-config`, `--nickname`, `--app-id`, `--context-access-enabled`, `--context-variable(-v)` |
| `agents list` | `--kind(-k)`, `--verbose(-v)` |
| `agents export` | `--name(-n)`, `--kind(-k)`, `--output(-o)`, `--agent-only` |
| `agents deploy` | `--name(-n)` |
| `agents undeploy` | `--name(-n)` |
| `agents remove` | `--name(-n)`, `--kind(-k)` |
| `agents copy` | `--name(-n)`, `--destination(-d)`, `--source(-s)` |
| `agents discover` | Discover and import an A2A agent from a well-known URI: `--url(-u)`, `--endpoint(-e)` (default `.well-known/agent-card.json`), `--name(-n)`, `--app-id(-a)` |
| `agents connect` | Add one or more application connections to a custom agent: `--name(-n)`, `--app-id(-a)` |
| `agents ai-builder` | AI tools to help create and refine agents. Subcommands: `create`, `prompt-tune`, `autotune` |

`--kind`: `native | external | assistant`.

```bash
orchestrate agents import -f agents/weather_agent.yaml
orchestrate agents list -k native -v
orchestrate agents export -n weather_agent -k native -o weather_agent.yaml --agent-only
orchestrate agents deploy -n weather_agent
```

---

## 3. tools

| Command | Key options |
|---------|-------------|
| `tools import` | `--kind(-k) python\|openapi\|flow\|langflow`, `--file(-f)`, `--requirements-file(-r)`, `--package-root(-p)`, `--app-id(-a)` (repeatable), `--name(-n)`, `--auto-discover`, `--llm`, `--env-file(-e)`, `--function`, `--save-flow-json`, `--translation`, `--safe` |
| `tools list` | `--verbose(-v)` |
| `tools export` | `--name(-n)`, `--output(-o)` ⚠ exports ZIP (not YAML); base name must be underscore-only |
| `tools remove` | `--name(-n)` |
| `tools auto-discover` | Annotate and generate docstring for a python tool via LLM: `--env-file(-e)` *(required)*, `--file(-f)` *(required)*, `--output(-o)` *(required)*, `--llm`, `--function` |
| `tools translation-export` | Retrieve translations for a flow tool: `--name(-n)` |
| `tools translation-import` | Import translations for a flow tool from a CSV file: `--name(-n)`, `--file(-f)` |

```bash
orchestrate tools import -k python -f tools/weather.py -r tools/requirements.txt
orchestrate tools import -k python -f tools/api_tool.py --app-id my_api
orchestrate tools import -k openapi -f specs/petstore.yaml
orchestrate tools import -k flow   -f tools/my_flow.py
```
`--package-root` when a tool spans multiple files. `--auto-discover` generates docstrings via LLM.

> ⚠ **Tool export ZIP reimport:** cannot pass zip to `tools import`. Unzip first:
> `unzip get_weather_export.zip -d /tmp/gw && orchestrate tools import -k python -f /tmp/gw/get_weather.py`

---

## 4. toolkits — MCP

Group is **`toolkits`** (plural). `add` configures inline; `import` loads a pre-written spec file.

| Command | Key options |
|---------|-------------|
| `toolkits add` | `--kind(-k) mcp\|python`, `--name(-n)`, `--description` *(all required)*, `--package`, `--package-root`, `--language(-l) node\|python`, `--command`, `--url(-u)`, `--transport streamable_http\|sse`, `--tools(-t) "*"`, `--app-id(-a)` (key_value only for STDIO), `--allowed-context tenant_id\|agent_id`, `--tier small\|medium\|large` (python) |
| `toolkits import` | `--file(-f)`, `--app-id(-a)` |
| `toolkits list` | `--verbose(-v)` |
| `toolkits export` | `--name(-n)`, `--output` |
| `toolkits remove` | `--name(-n)` |

```bash
# Local stdio (Node)
orchestrate toolkits add -k mcp -n math_toolkit --description "Factorial tools" \
  --package-root ./mcp_server --language node \
  --command '["node","dist/index.js","--transport","stdio"]' --tools "*"

# Remote HTTP
orchestrate toolkits add -k mcp -n remote_toolkit --description "Remote tools" \
  --url https://my-mcp.example.com --transport streamable_http --tools "tool_a,tool_b"

# From spec file
orchestrate toolkits import -f toolkits/math_toolkit.yaml
```
> **Restriction:** only `experimental_customer_care` style agents accept `toolkits:` in YAML.
> For standard agents, reference toolkit tools individually under `tools:`.

---

## 5. knowledge-bases

| Command | Key options |
|---------|-------------|
| `knowledge-bases import` | `--file(-f)`, `--safe` |
| `knowledge-bases list` | `--verbose(-v)` |
| `knowledge-bases status` | `--name(-n)` / `--id(-i)` |
| `knowledge-bases export` | `--name(-n)`/`--id(-i)`, `--output(-o)` |
| `knowledge-bases remove` | `--name(-n)`/`--id(-i)` |

```bash
orchestrate knowledge-bases import -f knowledge_base/kb.yaml
orchestrate knowledge-bases status -n my_kb    # watch ingestion progress
```

---

## 6. connections

| Command | Key options |
|---------|-------------|
| `connections add` | `--app-id(-a)` *(required)*, `--component`, `--category` |
| `connections configure` | `--app-id(-a)`, `--env [draft\|live]`, `--type(-t) [member\|team]`, `--kind(-k)` (see below), `--server-url(-u)`, `--sso`, `--config-entries(-e)` |
| `connections set-credentials` | `--app-id(-a)`, `--env`; creds: `--username(-u)`, `--password(-p)`, `--token`, `--api-key(-k)`, `--entries(-e) k=v`; OAuth: `--client-id`, `--client-secret`, `--token-url`, `--auth-url`, `--scope`, `--grant-type`, `--send-via [header\|body]` |
| `connections set-identity-provider` | `--idp-token-header`, `--idp-token-use`, `--idp-token-type`, `--app-token-header` |
| `connections import` | `--file(-f)` |
| `connections export` | `--output` |
| `connections list` | `--verbose(-v)` |
| `connections remove` | `--app-id(-a)` |

`--kind` (configure): `basic | bearer | api_key | key_value | kv | oauth_auth_code_flow |
oauth_auth_password_flow | oauth_auth_client_credentials_flow | oauth_auth_on_behalf_of_flow |
oauth_auth_token_exchange_flow | oauth_auth_direct_access_flow`

```bash
orchestrate connections add --app-id my_api
orchestrate connections configure -a my_api --kind api_key --type team --env draft
orchestrate connections set-credentials -a my_api --env draft --api-key "$MY_KEY"
orchestrate connections list
```

---

## 7. models

| Command | Key options |
|---------|-------------|
| `models list` | available in active env |
| `models import` | `--file(-f)`, `--app-id(-a)` (key_value connection) |
| `models add` | `--name(-n)`, `--description(-d)`, `--display-name`, `--provider-config` (JSON), `--app-id(-a)`, `--type [chat\|chat_vision\|completion\|embedding]` |
| `models export` | `--name(-n)`, `--output(-o)` |
| `models remove` | `--name(-n)` |
| `models validate` | Validate a model configuration: `--name(-n)`, `--verbose(-v)` |
| `models config` | subgroup: `list`, `default` (set tenant default), `denylist`, `reset`, `import`, `export`, `are-premier-models-enabled` (check status), `enable-premier-models`, `disable-premier-models` |
| `models policy` | route pseudo-models across downstreams: `add`, `remove`, `import`, `export` |

```bash
orchestrate models list
orchestrate models import -f models/granite.yaml --app-id watsonx_credentials
orchestrate models config default    # set tenant default LLM
```

---

## 8. server — Developer Edition

| Command | Key options |
|---------|-------------|
| `server start` | `--env-file(-e)`, `--with-langfuse(-l)`, `--with-ibm-telemetry(-i)`, `--with-doc-processing(-d)`, `--with-voice(-v)` (enable voice controller), `--with-connections-ui(-c)` (OAuth connections UI), `--with-langflow` (Langflow UI at http://localhost:7861), `--with-ai-builder` (AI Builder features), `--sequential-pull` (pull images individually), `--cert-bundle-path` (custom certificate bundle), `--service-username` / `--service-password` (Developer Edition service credentials), `--accept-terms-and-conditions` |
| `server stop` | — |
| `server reset` | wipe local tenant state |
| `server logs` | tail service logs |
| `server purge` | remove containers/volumes |
| `server images prune` | trim CPD docker image layer cache |
| `server edit/eject/ssh/attach-docker/release-docker` | advanced Docker lifecycle |

```bash
orchestrate server start -e .env --accept-terms-and-conditions
orchestrate server logs
orchestrate server reset    # fresh local state
orchestrate server stop
```

---

## 9. chat

| Command | Key options |
|---------|-------------|
| `chat start` | launch local chat UI |
| `chat ask <message>` | `--agent-name(-n)`, `--include-reasoning(-r)`, `--capture-logs(-l)`, `--thread-id(-t)` |
| `chat stop` | — |

```bash
orchestrate chat ask -n weather_agent "What's the weather in Paris?" -r
orchestrate chat ask -n weather_agent "And tomorrow?" -t <thread_id>
```
> ⚠ On IBM Cloud SaaS, `chat ask` can hang in scripted use (live-verified 2.13.x).
> Use the runtime REST API or `watsonx-orchestrate-adk:chat_with_agent` for CI/scripted testing.

---

## 10. channels · evaluations · observability · voice · others

- **channels**: `create`, `delete`, `get`, `list`, `list-channels`, `import`, `export`, `webchat` — expose deployed agent on a channel; `orchestrate channels webchat --help`.
  > ⚠ **Webchat embed CRN gotcha (SaaS):** `channels webchat embed` auto-fetch of the CRN 403s. Extract the CRN from the cached bearer token and pipe it in:
  > ```bash
  > CRN=$(python -c "
  > import yaml,os,json,base64
  > t=yaml.safe_load(open(os.path.expanduser('~/.cache/orchestrate/credentials.yaml')))['auth']['<env>']['wxo_mcsp_token']
  > p=t.split('.')[1];p+='='*(-len(p)%4)
  > print(json.loads(base64.urlsafe_b64decode(p))['unique_instance_crns'][0])")
  > echo "$CRN" | orchestrate channels webchat embed --agent-name <agent> --env live
  > ```
- **evaluations**: `evaluate`, `quick-eval`, `generate`, `analyze`, `record`, `validate-native`, `validate-external`, `red-teaming` (subgroup: `list`, `plan`, `run` — generate and run red-teaming attacks) — covered by the evaluations skill.
- **observability**: `traces search`, `traces export --trace-id <id>` — inspect execution traces.
  > ⚠ On SaaS, `traces search` returns 0 results even when traces exist. Prefer `traces export --trace-id`.
- **settings**: configure active env (observability/Langfuse tracing); `set-encoding` / `unset-encoding` (set encoding type for file access); `docker` (configuration for docker host).
- **voice-configs** / **phone**: voice-enabled agents. 2.13+ default: Deepgram Flux General English.
- **partners**: catalog/offering publishing.

---

## 11. skills

Manages IBM watsonx Orchestrate skills (distinct from Python tool functions).

| Command | Key options |
|---------|-------------|
| `skills import` | `--file(-f)`, `--safe` |
| `skills update` | `--file(-f)`, `--name(-n)` |
| `skills list` | `--verbose(-v)` |
| `skills remove` | `--name(-n)` |
| `skills export` | `--name(-n)`, `--output(-o)` |
| `skills get` | `--name(-n)` — retrieve skill details |
| `skills upload-script` | upload a skill script artifact |
| `skills upload-reference` | upload a skill reference artifact |

```bash
orchestrate skills list
orchestrate skills import -f skills/my_skill.yaml
orchestrate skills export -n my_skill -o my_skill_export.yaml
orchestrate skills remove -n my_skill
```

---

## 12. venv bootstrap

The ADK requires Python ≥3.11, <3.15. Use **`uv`** (fast) or the stdlib `venv` module.

**Preferred — `uv` with Python 3.12:**
```bash
# Install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create the venv at the repo/workspace root (shared by all projects inside)
cd /path/to/workspace-root
uv venv venv --python 3.12

# Activate and install the ADK
source venv/bin/activate
uv pip install -U ibm-watsonx-orchestrate
orchestrate --version   # confirm
```

**Fallback — stdlib venv:**
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -U ibm-watsonx-orchestrate
```

**Where to create the venv:**
- If you have a single project: create `venv/` at the project root.
- If you have multiple project sub-folders inside a workspace: create `venv/` at the **workspace root** (one level above all project folders). All `import-all.sh` scripts look `../venv/` first before falling back to `./venv/`.

**Never commit the venv** — add `venv/` to `.gitignore`.
