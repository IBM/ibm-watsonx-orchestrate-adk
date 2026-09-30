# Discover and Register Google Vertex AI Agents

This guide explains how to discover agents deployed in **Google Vertex AI Agent Engine** and register them as callable collaborators in your IBM watsonx Orchestrate workspace using the ADK CLI.

> **Availability:** SaaS environments only. This command is not available in Developer Edition or on-premises deployments.

---

## Prerequisites

1. **GCP project** with [Vertex AI Agent Engine](https://cloud.google.com/vertex-ai/docs/agent-builder/overview) enabled.
2. **Service account** in your GCP project with permission to list Vertex AI agents.  
   The required IAM permission is `aiplatform.agents.list`. A role that grants this is `roles/aiplatform.user` (or a custom role scoped to this permission).
3. **Service account JSON key** downloaded from the GCP console.
4. **IBM watsonx Orchestrate CLI** (`orchestrate`) installed and authenticated to a SaaS workspace.

---

## Step 1 — Create a connection for your Google credentials

Store your Google Cloud credentials in a `key_value` connection. The connection must contain three entries:

| Entry key | Value |
|-----------|-------|
| `service_account_json` | Full contents of the service account JSON key file |
| `project_id` | Your GCP project ID (e.g. `my-gcp-project`) |
| `location` | GCP region where your agents are deployed (e.g. `us-central1`) |

```bash
# Create the connection
orchestrate connections add --app-id vertex-conn

# Configure it as a team key_value connection in draft
orchestrate connections configure \
  --app-id vertex-conn \
  --kind key_value \
  --type team \
  --environment draft

# Store the credentials  (wrap the JSON in single quotes)
orchestrate connections set-credentials \
  --app-id vertex-conn \
  --environment draft \
  --entries service_account_json='{"type":"service_account","project_id":"my-gcp-project","private_key_id":"...","private_key":"-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n","client_email":"my-sa@my-gcp-project.iam.gserviceaccount.com","token_uri":"https://oauth2.googleapis.com/token"}' \
  --entries project_id=my-gcp-project \
  --entries location=us-central1
```

> **Tip:** Read the JSON key file and pass it inline: `--entries service_account_json="$(cat my-key.json)"`.  
> The CLI splits on the **first `=`** only, so embedded `=` characters inside the JSON are safe.

---

## Step 2 — Discover and register agents

### Import all agents in the project

```bash
orchestrate agents discover \
  --provider vertex_agent \
  --app-id vertex-conn
```

The CLI will display a table of discovered agents and prompt you to confirm before importing.

### Import specific agents by display name

```bash
orchestrate agents discover \
  --provider vertex_agent \
  --app-id vertex-conn \
  --agent "Customer Support" \
  --agent "Sales Assistant"
```

`--agent` is repeatable and case-insensitive. Only agents whose `displayName` matches are imported.

### Skip confirmation (CI/scripted use)

```bash
orchestrate agents discover \
  --provider vertex_agent \
  --app-id vertex-conn \
  --yes
```

---

## Step 3 — Verify the registered agents

```bash
orchestrate agents list
```

Agents registered from Vertex AI appear with `provider: vertex_agent`.

---

## How agents are converted

| Vertex AI field | WXO field | Notes |
|-----------------|-----------|-------|
| `displayName` | `name` (sanitized) | Lowercased, spaces and dashes → underscores, max 64 chars |
| `displayName` | `title` | Used as the display title unchanged |
| `description` | `description` | Falls back to `"Google Vertex AI agent: <displayName>"` if empty |
| Resource `name` path | `api_url` | `https://{location}-aiplatform.googleapis.com/v1beta1/{name}` |
| — | `provider` | Always `vertex_agent` |

The `api_url` stores the canonical Vertex AI resource URL. It is a placeholder for the runtime invocation adapter — once a Vertex AI runtime adapter is available in IBM watsonx Orchestrate, it will use this URL to route chat messages to the agent.

---

## Known limitations

- **Credential environment is hardcoded to `draft`.**  
  Credentials are always retrieved from the `draft` connection environment. Live-environment credential support is not yet implemented.

- **No runtime invocation (yet).**  
  Registered `vertex_agent` agents appear in `orchestrate agents list` and can be added as collaborators. However, live chat invocations will not be routed to Vertex AI until a runtime adapter is available. This is tracked separately from this CLI feature.

- **Single project/location per connection.**  
  Each connection covers one `project_id` + `location`. To discover agents from multiple regions or projects, create separate connections and run `discover` for each.

- **SaaS only.**  
  The `--provider vertex_agent` flag is blocked on Developer Edition (`localhost`) and on-premises (CPD) environments.

---

## Governance note

The **IBM watsonx Orchestrate Unified Gateway** (epic #85315) provides a separate governance scanner that also discovers Google Vertex AI / Gemini agents for shadow-agent visibility in the platform UI. That scanner uses the same service account JSON authentication method but runs as a separate control-plane-only microservice. The ADK CLI discovery described in this guide is independent — it registers agents as callable collaborators in your workspace, not as entries in the governance scanner.

In the governance UI, Vertex AI agents discovered by the Unified Gateway scanner appear under the **"Google Gemini"** provider label. Agents registered via the ADK CLI use the `vertex_agent` provider string.

---

## Troubleshooting

| Error | Likely cause | Fix |
|-------|-------------|-----|
| `--app-id is required` | `--app-id` not provided | Add `--app-id <connection-id>` |
| `missing the 'service_account_json' credential entry` | Connection not fully configured | Re-run `orchestrate connections set-credentials` |
| `Failed to list Vertex AI agents: 403 Forbidden` | Service account lacks `aiplatform.agents.list` | Grant `roles/aiplatform.user` or a custom role to the service account |
| `Failed to list Vertex AI agents: 404 Not Found` | Wrong `project_id` or `location` | Check your connection credentials |
| `Vertex AI agent discovery is only supported in SaaS environments` | Running in Developer Edition or on-prem | Use a SaaS workspace |
