# Connections, Models & Knowledge Bases

Current as of `ibm-watsonx-orchestrate` 2.13.x.

## Contents
- [§1 Connections — YAML schema + CLI lifecycle](#1-connections)
- [§2 Models via the watsonx.ai AI Gateway](#2-models-via-the-watsonxai-ai-gateway)
- [§3 Knowledge Bases (RAG)](#3-knowledge-bases-rag)
  - Built-in Milvus · AstraDB · External Milvus · Elasticsearch · Provider auth matrix

---

## 1. Connections

A connection stores credentials/config for an external service, referenced by `app_id`.
Two halves: a **YAML definition** (structure) and **credentials** set separately via the CLI.
**Never put real secrets in YAML.**

### Connection YAML schema

```yaml
spec_version: v1
kind: connection            # singular — NOT 'connections'
app_id: my_api              # unique id; tools reference this in ExpectedCredentials
environments:
  draft:                    # at least 'draft' required; add 'live' for production
    security_scheme: api_key_auth   # NOT 'kind:' here — must be 'security_scheme:'
    type: team              # team (shared credentials) | member (per-user credentials)
    server_url: https://api.example.com
```

**`security_scheme` values:** `basic_auth`, `bearer_token`, `api_key_auth`, `oauth2`, `key_value_creds`.

### OAuth2 example (note `auth_type` — NOT `authorization_code`)
```yaml
spec_version: v1
kind: connection
app_id: google_sheets
environments:
  draft:
    security_scheme: oauth2
    auth_type: oauth2_auth_code         # REQUIRED for OAuth2; do NOT use 'authorization_code'
    type: team
    server_url: https://sheets.googleapis.com
    auth_url: https://accounts.google.com/o/oauth2/v2/auth
    token_url: https://oauth2.googleapis.com/token
    scope:
      - https://www.googleapis.com/auth/spreadsheets.readonly
```

### CLI lifecycle

```bash
# Import a connection YAML
orchestrate connections import -f connections/my_api.yaml

# Configure auth kind and type
orchestrate connections configure -a my_api --kind api_key --type team --env draft

# Set credentials (keep secrets in .env, pass via $VAR to stay out of shell history)
source ./.env
orchestrate connections set-credentials -a my_api --env draft --api-key "$MY_API_KEY"

# Basic auth
orchestrate connections set-credentials -a my_api --env draft -u "$USER" -p "$PASS"

# Key-value entries (e.g. for watsonx_credentials)
orchestrate connections set-credentials -a my_api --env draft --entries "api_key=$KEY,space_id=$SPACE"

# Inspect
orchestrate connections list
orchestrate connections list -v    # full detail
```

`--kind` values for `configure`: `basic | bearer | api_key | key_value | kv |
oauth_auth_code_flow | oauth_auth_password_flow | oauth_auth_client_credentials_flow |
oauth_auth_on_behalf_of_flow | oauth_auth_token_exchange_flow | oauth_auth_direct_access_flow`.

**Common mistakes:**
- ❌ `kind: connections` (plural) — must be `kind: connection`
- ❌ `kind:` inside `environments.<env>` — must be `security_scheme:`
- ❌ `auth_type: authorization_code` — must be `auth_type: oauth2_auth_code`

---

## 2. Models via the watsonx.ai AI Gateway

```bash
orchestrate models list   # list what the active env offers; reference models by full id
```

Example ids: `watsonx/meta-llama/llama-3-3-70b-instruct`,
`watsonx/ibm/granite-3-3-8b-instruct`, `groq/openai/gpt-oss-120b`.

- **Default model**: `groq/openai/gpt-oss-120b`.
- **Premier models are disabled by default** — enable explicitly with `orchestrate models config enable-premier-models`; check status with `orchestrate models config are-premier-models-enabled`; `models list` won't show them otherwise.
- `experimental_customer_care` style requires `groq/openai/gpt-oss-120b`.

### Adding a custom watsonx.ai model

**Step 1 — create a `watsonx_credentials` connection:**
```bash
orchestrate connections import -f connections/watsonx_credentials.yaml
orchestrate connections configure -a watsonx_credentials --kind key_value --type team --env draft
source ./.env
orchestrate connections set-credentials -a watsonx_credentials --env draft \
  --entries "api_key=${WATSONX_APIKEY},watsonx_space_id=${SPACE_ID}"
```

Connection YAML:
```yaml
spec_version: v1
kind: connection
app_id: watsonx_credentials
environments:
  draft:
    security_scheme: key_value_creds
    type: team
```

**Step 2 — model YAML:**
```yaml
spec_version: v1
kind: model
name: watsonx/ibm/granite-3-3-8b-instruct
display_name: IBM Granite (watsonx.ai)
description: IBM watsonx.ai model.
tags: [ibm, watsonx]
model_type: chat
provider_config:
  watsonx_space_id: my-space-id   # OR watsonx_project_id / watsonx_deployment_id
```

**Step 3 — import:**
```bash
orchestrate models import -f models/granite.yaml --app-id watsonx_credentials
```

**provider_config fields (use at least one of space/project/deployment):**
`api_key`, `watsonx_space_id`, `watsonx_project_id`, `watsonx_deployment_id`,
`watsonx_cpd_url`/`username`/`password` (on-prem), `watsonx_version`, `custom_host`, `request_timeout`.

Keep the model `name` stable across environments; only `provider_config` / credentials differ between dev/stage/prod.

---

## 3. Knowledge Bases (RAG)

### Decision tree
```
Existing vector DB?
├─ No  → Built-in Milvus (managed — default choice; no external infra required)
└─ Yes → AstraDB / external Milvus / Elasticsearch  (use provider blocks below)
         Anything else (Pinecone, Weaviate, Qdrant, Chroma, custom REST) → custom Python @tool
         (see agents-tools-schemas.md §5)
```

### Built-in Milvus (managed — minimum config)
```yaml
spec_version: v1
kind: knowledge_base
name: product_docs
description: Product documentation for grounding answers.
documents:
  - doc1.pdf
  - doc2.docx
vector_index:
  embeddings_model_name: ibm/slate-125m-english-rtrvr-v2
```
- No external infra required. Supports **PDF/DOCX/PPTX/XLSX/CSV/HTML/TXT** — `.md` is **not** supported and will error at import time.
- `documents:` entries are **flat strings** (not `- path: …` objects).
- **Path resolution**: document paths are resolved **relative to the KB YAML file's directory**, not the shell CWD. Either place docs alongside the YAML, or run `import` with `cd` into the YAML's directory: `(cd knowledge-bases && orchestrate knowledge-bases import -f kb.yaml)`.
- `orchestrate knowledge-bases import -f kb.yaml`
- `orchestrate knowledge-bases status -n product_docs`  — watch indexing progress.
- Reference in agent YAML: `knowledge_base: [product_docs]`

### AstraDB (DataStax)
Auth: **API key**. Set `prioritize_built_in_index: false` and an `app_id` connection.
```yaml
spec_version: v1
kind: knowledge_base
name: astra_kb
description: KB on AstraDB
app_id: astradb_conn
prioritize_built_in_index: false
conversational_search_tool:
  index_config:
    - astradb:
        api_endpoint: 'https://xxx.apps.astra.datastax.com'
        data_type: collection        # or 'table'
        collection: my_collection
        embedding_model_id: nvidia/nv-embedqa-e5-v5
        embedding_mode: server       # or 'client'
        port: '443'
        search_mode: vector          # 'vector' | 'lexical' | 'hybrid'
        limit: 5
        field_mapping: { title: title, body: content, url: url }
```
```bash
orchestrate connections configure -a astradb_conn --kind api_key --type team --env draft
orchestrate connections set-credentials -a astradb_conn --env draft --api-key "$ASTRA_TOKEN"
```

### External Milvus
Auth: **basic**.
```yaml
spec_version: v1
kind: knowledge_base
name: milvus_kb
description: KB on external Milvus
app_id: milvus_conn
prioritize_built_in_index: false
conversational_search_tool:
  index_config:
    - milvus:
        endpoint: 'https://my-milvus.com'
        collection_name: my_collection
        embedding_provider: nvidia
        embedding_model: nvidia/nv-embedqa-e5-v5
        embedding_dimension: 1024
        field_mapping: { title: title, body: content, url: source_url }
```
```bash
orchestrate connections configure -a milvus_conn --kind basic --type team --env draft
orchestrate connections set-credentials -a milvus_conn --env draft -u "$USER" -p "$PASS"
```

### Elasticsearch
Auth: **API key or basic**.
```yaml
spec_version: v1
kind: knowledge_base
name: es_kb
description: KB on Elasticsearch
app_id: es_conn
prioritize_built_in_index: false
conversational_search_tool:
  index_config:
    - elasticsearch:
        endpoint: 'https://es.example.com'
        index_name: my_index
        embedding_field: vector_embedding
        field_mapping: { title: title, body: content, url: url }
```
```bash
# API key
orchestrate connections configure -a es_conn --kind api_key --type team --env draft
orchestrate connections set-credentials -a es_conn --env draft --api-key "$ES_KEY"
# Basic auth
orchestrate connections configure -a es_conn --kind basic --type team --env draft
orchestrate connections set-credentials -a es_conn --env draft -u "$ES_USER" -p "$ES_PASS"
```

### Provider authentication matrix

| Provider | Basic | API Key | Notes |
|---|---|---|---|
| Built-in Milvus | N/A | N/A | Managed; no auth needed |
| AstraDB | ❌ | ✅ | Application Token as API key |
| External Milvus | ✅ | ❌ | |
| Elasticsearch | ✅ | ✅ | Either scheme supported |
| Custom `@tool` | Depends on implementation | | Use `expected_credentials` pattern |

### Best practices
1. Use built-in Milvus when no existing vector DB is required — tightest integration.
2. Always set `field_mapping` to match your data schema.
3. Test KB connectivity with `orchestrate knowledge-bases status` before deploying agents.
4. Keep credentials in `.env` and set via `connections set-credentials`; never hardcode.
