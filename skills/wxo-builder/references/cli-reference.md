# `orchestrate` CLI Reference

Verified against `ibm-watsonx-orchestrate` 2.14.x. CLI evolves fast — always confirm with
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

Top-level groups: `env`, `agents`, `tools`, `skills`, `toolkits`, `knowledge-bases`, `connections`,
`voice-configs`, `models`, `server`, `chat`, `channels`, `phone`, `evaluations`, `settings`,
`partners`, `observability`.
> Note plural **`toolkits`**, **`voice-configs`**, **`knowledge-bases`**, and **`skills`** group names.

---

## 1. env

| Command | Key options |
|---------|-------------|
| `env list` | — |
| `env add` | `--name(-n)`, `--url(-u)`, `--activate(-a)`, `--type(-t)` (`ibm_iam\|mcsp\|mcsp_v1\|mcsp_v2\|cpd`), `--insecure`, `--verify` |
| `env activate <name>` | `--api-key(-a)` (SaaS/CPD), `--username(-u)` (CPD), `--password(-p)` (CPD), `--skip-version-check` / `--enable-version-check` |
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

> ⚠ **`env get-token`** is not available. To obtain a bearer token for the runtime REST API,
> use the credentials cached at `~/.cache/orchestrate/credentials.yaml` or authenticate via the IBM Cloud CLI.

---

## 2. agents

| Command | Key options |
|---------|-------------|
| `agents import` | `--file(-f)`, `--app-id(-a)` (external), `--package-root`, `--config-file`, `--safe` |
| `agents create` | `--name(-n)`, `--kind(-k)`, `--description`, `--llm`, `--style`, `--instructions`, `--tools`, `--collaborators`, `--knowledge-bases`, `--output(-o)`, external: `--title(-t)`, `--api(-a)`, `--auth-scheme`, `--provider(-p)`, `--auth-config`, `--tags`, `--chat-params`, `--config`, `--nickname`, `--app-id`, `--context-access-enabled`, `--context-variable(-v)`, `--custom-join-tool`, `--structured-output`, `--safe` |
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
| `tools translation-export` | Retrieve translations for a flow tool: `--kind(-k)` *(required, `openapi\|python\|mcp\|flow\|langflow`)*, `--translation` *(required, output CSV path)*, `--file(-f)` (flow file, mutually exclusive with `--name`), `--name` (imported tool name) |
| `tools translation-import` | Import translations for a flow tool from a CSV file: `--kind(-k)` *(required)*, `--translation` *(required, input CSV path)*, `--name` *(required, imported tool name)* |

```bash
orchestrate tools import -k python -f tools/weather.py -r tools/requirements.txt
orchestrate tools import -k python -f tools/api_tool.py --app-id my_api
orchestrate tools import -k openapi -f specs/petstore.yaml
orchestrate tools import -k flow   -f tools/my_flow.py
```
`--package-root` when a tool spans multiple files. `--auto-discover` generates docstrings via LLM.

> ⚠ **Tool export ZIP reimport:** cannot pass zip to `tools import`. Unzip first:
> `unzip get_weather_export.zip -d /tmp/gw && orchestrate tools import -k python -f /tmp/gw/get_weather.py`

> ⚠ **`translation-export`/`translation-import`:** `--kind` is required; use `--translation <csv-path>` for the CSV path; `--file` and `--name` are mutually exclusive for specifying the source tool. Only `flow` kind currently supported.

---

## 4. toolkits — MCP

Group is **`toolkits`** (plural). `add` configures inline; `import` loads a pre-written spec file.

| Command | Key options |
|---------|-------------|
| `toolkits add` | `--kind(-k) mcp\|python`, `--name(-n)`, `--description` *(all required)*, `--package`, `--package-root`, `--language(-l) node\|python`, `--command`, `--url(-u)`, `--transport streamable_http\|sse`, `--tools(-t) "*"`, `--app-id(-a)` (key_value only for STDIO), `--allowed-context tenant_id\|agent_id`, `--tier small\|medium\|large` (python) |
| `toolkits import` | `--file(-f)`, `--app-id(-a)` |
| `toolkits list` | `--verbose(-v)` |
| `toolkits export` | `--name(-n)`, `--output(-o)` |
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
| `knowledge-bases import` | `--file(-f)`, `--app-id(-a)`, `--safe` |
| `knowledge-bases list` | `--verbose(-v)` |
| `knowledge-bases status` | `--name(-n)` / `--id(-i)` |
| `knowledge-bases export` | `--output(-o)` *(required)*, `--name(-n)`, `--id(-i)` |
| `knowledge-bases remove` | `--name(-n)` / `--id(-i)` |

```bash
orchestrate knowledge-bases import -f knowledge_base/kb.yaml
orchestrate knowledge-bases status -n my_kb    # watch ingestion progress
orchestrate knowledge-bases export -n my_kb -o my_kb_export.yaml
```

---

## 6. connections

| Command | Key options |
|---------|-------------|
| `connections add` | `--app-id(-a)` *(required)*, `--component`, `--category` |
| `connections configure` | `--app-id(-a)`, `--environment/--env [draft\|live]`, `--type(-t) [member\|team]`, `--kind(-k)` (see below), `--server-url/--url(-u)`, `--sso(-s)`, `--idp-token-use`, `--idp-token-type`, `--idp-token-header`, `--app-token-header`, `--config-entries(-e)` |
| `connections set-credentials` | `--app-id(-a)`, `--environment/--env`; creds: `--username(-u)`, `--password(-p)`, `--token`, `--api-key(-k)`, `--entries(-e) k=v`, `--token-entries(-t)`, `--auth-entries`; OAuth: `--client-id`, `--client-secret`, `--token-url`, `--auth-url`, `--scope`, `--grant-type`, `--send-via [header\|body]` |
| `connections set-identity-provider` | `--app-id(-a)`, `--environment/--env`, `--url(-u)`, `--client-id`, `--client-secret`, `--scope`, `--grant-type`, `--token-entries(-t)` |
| `connections import` | `--file(-f)` |
| `connections export` | `--app-id(-a)` *(required)*, `--output(-o)` *(required)* |
| `connections list` | `--environment/--env [draft\|live]`, `--verbose(-v)` |
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
| `models list` | `--raw(-r)` (non-tabular), `--all(-a)` (all available models) |
| `models import` | `--file(-f)`, `--app-id(-a)` (key_value connection), `--skip-validation` |
| `models add` | `--name(-n)`, `--description(-d)`, `--display-name`, `--provider-config` (JSON), `--app-id(-a)`, `--type [chat\|chat_vision\|completion\|embedding]`, `--skip-validation` |
| `models export` | `--name(-n)`, `--output(-o)` |
| `models remove` | `--name(-n)` |
| `models validate` | Validate a model configuration: `--name(-n)`, `--verbose(-v)` |
| `models config` | subgroup: `list`, `default` (set tenant default), `denylist`, `reset`, `import`, `export`, `are-premier-models-enabled` (check status), `enable-premier-models`, `disable-premier-models` |
| `models policy` | route pseudo-models across downstreams: `add`, `remove`, `import`, `export` |

```bash
orchestrate models list
orchestrate models list --all       # show all models including disabled
orchestrate models import -f models/granite.yaml --app-id watsonx_credentials
orchestrate models config default   # set tenant default LLM
orchestrate models config are-premier-models-enabled
```

---

## 8. server — Developer Edition

| Command | Key options |
|---------|-------------|
| `server start` | `--env-file(-e)`, `--with-langfuse(-l)`, `--with-ibm-telemetry(-i)`, `--with-doc-processing(-d)`, `--with-voice(-v)` (enable voice controller), `--with-connections-ui(-c)` (OAuth connections UI), `--with-langflow` (Langflow UI at http://localhost:7861), `--with-ai-builder` (AI Builder features), `--compose-file(-f)` (custom docker-compose file), `--sequential-pull` (pull images individually), `--cert-bundle-path` (custom certificate bundle), `--service-username` / `--service-password` (Developer Edition service credentials), `--accept-terms-and-conditions` |
| `server stop` | `--env-file(-e)`, `--keep-vm` (don't stop the underlying VM) |
| `server reset` | `--env-file(-e)`, `--keep-vm` |
| `server logs` | `--id(-i)` (container ID), `--name(-n)` (container name), `--env-file(-e)` |
| `server purge` | remove containers/volumes |
| `server images prune` | trim CPD docker image layer cache |
| `server edit/eject/ssh/attach-docker/release-docker` | advanced Docker lifecycle |

```bash
orchestrate server start -e .env --accept-terms-and-conditions
orchestrate server logs -n <container-name>   # filter logs by container
orchestrate server reset    # fresh local state
orchestrate server stop --keep-vm   # stop services but keep VM running
```

---

## 9. chat

| Command | Key options |
|---------|-------------|
| `chat start` | `--env-file(-e)`, `--skip-open` (don't open browser) |
| `chat ask [message]` | `--agent-name(-n)`, `--include-reasoning(-r)`, `--capture-logs(-l)`, `--thread-id(-t)` |
| `chat stop` | `--env-file(-e)` |

```bash
orchestrate chat ask -n weather_agent "What's the weather in Paris?" -r
orchestrate chat ask -n weather_agent "And tomorrow?" -t <thread_id>
```
> ⚠ On IBM Cloud SaaS, `chat ask` can hang in scripted use.
> Use the runtime REST API or `watsonx-orchestrate-adk:chat_with_agent` for CI/scripted testing.

---

## 10. channels · evaluations · observability · voice · others

### channels
`create`, `delete`, `get`, `list`, `list-channels`, `import`, `export`, `webchat` — expose deployed agent on a channel.

| Command | Key options |
|---------|-------------|
| `channels list` | list supported channel types (no args) |
| `channels list-channels` | `--agent-name`, `--env(-e)` *(required)*, `--type(-t)` (filter), `--verbose(-v)`, `--format(-f) table\|json` |
| `channels import` | `--agent-name`, `--env(-e)`, `--file(-f)` *(all required)* |
| `channels create` | `--agent-name`, `--env(-e)`, `--type(-t)`, `--name(-n)` *(all required)*, `--description(-d)`, `--field(-f)` (repeatable `key=value`), `--output(-o)` (dry-run to file) |
| `channels get` | `--agent-name`, `--env(-e)`, `--type(-t)` *(required)*, `--id(-i)` or `--name(-n)`, `--verbose(-v)` |
| `channels export` | `--agent-name`, `--env(-e)`, `--type(-t)`, `--output(-o)` *(required)*, `--id(-i)` or `--name(-n)` |
| `channels delete` | `--agent-name`, `--env(-e)`, `--type(-t)` *(required)*, `--id(-i)` or `--name(-n)`, `--yes(-y)` |
| `channels webchat embed` | `--agent-name(-a)`, `--env(-e)` (default: `live`) |

Channel types: `webchat` · `twilio_whatsapp` · `twilio_sms` · `byo_slack` · `genesys_bot_connector` · `facebook` · `teams`.

  > ⚠ **Webchat embed CRN gotcha (SaaS):** `channels webchat embed` auto-fetch of the CRN 403s. Extract the CRN from the cached bearer token and pipe it in:
  > ```bash
  > CRN=$(python -c "
  > import yaml,os,json,base64
  > t=yaml.safe_load(open(os.path.expanduser('~/.cache/orchestrate/credentials.yaml')))['auth']['<env>']['wxo_mcsp_token']
  > p=t.split('.')[1];p+='='*(-len(p)%4)
  > print(json.loads(base64.urlsafe_b64decode(p))['unique_instance_crns'][0])")
  > echo "$CRN" | orchestrate channels webchat embed --agent-name <agent> --env live
  > ```

### evaluations
`evaluate`, `quick-eval`, `generate`, `analyze`, `record`, `validate-native`, `validate-external`, `red-teaming` (subgroup: `list`, `plan`, `run`)

| Command | Key options |
|---------|-------------|
| `evaluations evaluate` | `--config(-c)`, `--test-paths(-p)`, `--output-dir(-o)`, `--env-file(-e)`, `--with-langfuse(-l)` |
| `evaluations quick-eval` | LLM-as-a-judge evaluation: `--config(-c)`, `--test-paths(-p)`, `--tools-path(-t)`, `--output-dir(-o)`, `--env-file(-e)` |
| `evaluations generate` | `--stories-path(-s)` *(required)*, `--tools-path(-t)` *(required)*, `--output-dir(-o)`, `--env-file(-e)` |
| `evaluations analyze` | `--data-path(-d)` *(required)*, `--tools-path(-t)`, `--env-file(-e)`, `--mode(-m) default\|enhanced` |
| `evaluations record` | `--output-dir(-o)`, `--env-file(-e)`, `--context-variables(-cv)` JSON string |
| `evaluations validate-native` | `--tsv(-t)` *(required)*, `--output(-o)`, `--env-file(-e)` |
| `evaluations validate-external` | `--tsv(-t)`, `--external-agent-config(-ext)` *(required)*, `--output(-o)`, `--env-file(-e)`, `--credential(-crd)`, `--perf(-p)` |
| `evaluations red-teaming plan` | `--attacks-list(-a)`, `--datasets-path(-d)`, `--agents-path(-g)`, `--target-agent-name(-t)` *(all required)*, `--output-dir(-o)`, `--env-file(-e)`, `--max_variants(-n)` |
| `evaluations red-teaming run` | `--attack-paths(-a)` *(required)*, `--output-dir(-o)`, `--env-file(-e)` |
| `evaluations red-teaming list` | list available attack plans |

### observability
`traces search`, `traces export`

| Command | Options |
|---------|---------|
| `observability traces search` | `--start-time`, `--end-time` OR `--last` (e.g. `30m`, `3h`, `10d`); `--session-id` (multi); `--user-id(-u)` (multi); `--sort-field start_time\|end_time`, `--sort-direction asc\|desc`, `--limit(-l)` [1–1000, default 100] |
| `observability traces export` | `--trace-id(-t)` *(required)*, `--output(-o)`, `--pretty/--no-pretty` |

> ⚠ On SaaS, `traces search` returns 0 results even when traces exist. Prefer `traces export --trace-id`.

### settings
`set-encoding`, `unset-encoding`, `observability langfuse get/configure/remove`, `docker host`

```bash
orchestrate settings set-encoding utf-8
orchestrate settings unset-encoding
orchestrate settings observability langfuse configure --url <url> --health-uri <uri> --project-id <id> --api-key <key>
orchestrate settings observability langfuse get -o langfuse-config.yaml
orchestrate settings observability langfuse remove
```

### voice-configs / phone
Voice-enabled agents:

| `voice-configs` Command | Key options |
|---------|-------------|
| `voice-configs import` | `--file(-f)` *(required)* |
| `voice-configs list` | `--verbose(-v)` |
| `voice-configs get` | `--id(-i)` or `--name(-n)` |
| `voice-configs export` | `--output(-o)` *(required)*, `--id(-i)` or `--name(-n)` |
| `voice-configs remove` | `--id(-i)` or `--name(-n)` |

Phone configs are **global resources** attachable to multiple agents. Types: `genesys_audio_connector` · `sip_trunk`.

| `phone` Command | Key options |
|---------|-------------|
| `phone list` | list supported phone channel types |
| `phone create` | `--name(-n)`, `--type(-t)` *(required)*, `--description(-d)`, `--field(-f)` (repeatable), `--output(-o)` (dry-run) |
| `phone list-configs` | `--type(-t)`, `--verbose(-v)`, `--format(-f) table\|json` |
| `phone get` | `--id(-i)` or `--name(-n)`, `--verbose(-v)` |
| `phone delete` | `--id(-i)` or `--name(-n)`, `--yes(-y)` |
| `phone import` | `--file(-f)` *(required)* |
| `phone export` | `--output(-o)` *(required)*, `--id(-i)` or `--name(-n)` |
| `phone attach` | `--agent-name`, `--env(-e)` *(required)*, `--id(-i)` or `--name(-n)` |
| `phone detach` | `--agent-name`, `--env(-e)` *(required)*, `--id(-i)` or `--name(-n)`, `--yes(-y)` |
| `phone list-attachments` | `--id(-i)` or `--name(-n)`, `--format(-f) table\|json` |
| `phone add-number` | `--number` *(required)*, `--id(-i)` or `--name(-n)`, `--description(-d)`, `--agent-name`, `--env(-e)` |
| `phone list-numbers` | `--id(-i)` or `--name(-n)`, `--format(-f) table\|json` |
| `phone update-number` | `--number` *(required)*, `--id(-i)` or `--name(-n)`, `--new-number`, `--description(-d)`, `--agent-name`, `--env(-e)` |
| `phone delete-number` | `--number` *(required)*, `--id(-i)` or `--name(-n)`, `--yes(-y)` |

### partners
Catalog/offering publishing for partner-built agents.

| Command | Key options |
|---------|-------------|
| `partners offering create` | `--offering(-o)`, `--publisher(-p)`, `--type(-t) native\|external`, `--agent-name(-a)` *(all required)* |
| `partners offering package` | `--offering(-o)` *(required)*, `--folder(-f)` |

---

## 11. skills

Manages IBM watsonx Orchestrate skills. Note: flags use `--skill-id`/`--skill-name` (not `--name`).

| Command | Key options |
|---------|-------------|
| `skills import` | `--file(-f)` (single SKILL.md), `--dir(-d)` (directory), `--recursive(-r)` (search subdirs), `--workspace-id(-w)`, `--upsert(-u)` (update if exists) |
| `skills update` | `--file(-f)` *(required)*, `--skill-id(-s)`, `--skill-name(-n)` |
| `skills list` | `--workspace-id(-w)`, `--verbose(-v)` |
| `skills remove` | `--skill-id(-s)` or `--skill-name(-n)` |
| `skills export` | `--output(-o)` *(required, .zip or directory)*, `--skill-id(-s)`, `--skill-name(-n)` |
| `skills get` | `--skill-id(-s)` or `--skill-name(-n)` |
| `skills upload-script` | `--file(-f)` *(required)*, `--skill-id(-s)`, `--skill-name(-n)`, `--script-path(-p)` |
| `skills upload-reference` | `--file(-f)` *(required)*, `--skill-id(-s)`, `--skill-name(-n)`, `--reference-path(-p)` |

```bash
orchestrate skills list
orchestrate skills import -f skills/wxo-builder/SKILL.md --upsert
orchestrate skills import -d skills/ --recursive --upsert
orchestrate skills export --skill-name my_skill -o my_skill_export.zip
orchestrate skills remove --skill-name my_skill
```

> ⚠ `remove`/`get`/`update`/`export` use `--skill-id(-s)` / `--skill-name(-n)` to identify a skill — **not** `--name`.

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
