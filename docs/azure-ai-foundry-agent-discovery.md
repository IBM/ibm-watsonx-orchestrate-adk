# Discover and Register Microsoft Azure AI Foundry Agents

This guide explains how to discover agents deployed in **Microsoft Azure AI Foundry** and register them as callable collaborators in your IBM watsonx Orchestrate workspace using the ADK CLI.

> **Availability:** SaaS environments only. This command is not available in Developer Edition or on-premises deployments.

---

## Prerequisites

1. **Azure subscription** with an **Azure AI Foundry** resource and project deployed.
2. **Microsoft Entra ID (Azure AD) Service Principal** (App Registration) with permission to access Azure AI Foundry.
3. **Client ID, Client Secret, and Tenant ID** for the service principal.
4. **Endpoint and Project Name** for your Azure AI Foundry resource (e.g. `https://<resource-name>.services.ai.azure.com`).
5. **IBM watsonx Orchestrate CLI** (`orchestrate`) installed and authenticated to a SaaS workspace.

---

## Step 1 — Create a connection for your Azure credentials

Store your Microsoft Azure credentials in a `key_value` connection. The connection must contain five entries:

| Entry key | Value |
|-----------|-------|
| `tenant_id` | Microsoft Entra ID Tenant ID |
| `client_id` | Service Principal (App Registration) Client ID |
| `client_secret` | Service Principal Client Secret |
| `endpoint` | Azure AI Foundry resource endpoint (e.g. `https://my-resource.services.ai.azure.com`) |
| `project_name` | Azure AI Foundry project name |

```bash
# Create the connection
orchestrate connections add --app-id azure-conn

# Configure it as a team key_value connection in draft
orchestrate connections configure \
  --app-id azure-conn \
  --kind key_value \
  --type team \
  --environment draft

# Store the credentials
orchestrate connections set-credentials \
  --app-id azure-conn \
  --environment draft \
  --entries tenant_id=00000000-0000-0000-0000-000000000000 \
  --entries client_id=11111111-1111-1111-1111-111111111111 \
  --entries client_secret=my-client-secret-value \
  --entries endpoint=https://my-resource.services.ai.azure.com \
  --entries project_name=my-project
```

---

## Step 2 — Discover and register agents

### Import all agents in the project

```bash
orchestrate agents discover \
  --provider azure_ai_foundry \
  --app-id azure-conn
```

The CLI will display a table of discovered agents and prompt you to confirm before importing.

### Import specific agents by name

```bash
orchestrate agents discover \
  --provider azure_ai_foundry \
  --app-id azure-conn \
  --name "Customer Support" \
  --name "Sales Assistant"
```

`--name` is repeatable and case-insensitive. Only agents whose name matches are imported.

---

## Step 3 — Verify the registered agents

```bash
orchestrate agents list
```

Agents registered from Azure AI Foundry appear with `provider: azure_ai_foundry`.

---

## How agents are converted

| Azure AI Foundry field | WXO field | Notes |
|------------------------|-----------|-------|
| `name` | `name` (sanitized) | Lowercased, spaces and dashes → underscores, max 64 chars |
| `name` | `title` | Used as the display title unchanged |
| `description` | `description` | Falls back to `"Microsoft Azure AI Foundry agent: <name>"` if empty |
| `id` / `name` | `api_url` | `{endpoint}/api/projects/{project_name}/agents/{id}` |
| — | `provider` | Always `azure_ai_foundry` |

The `api_url` stores the canonical Azure AI Foundry agent resource URL. It is a placeholder for the runtime invocation adapter — once an Azure AI Foundry runtime adapter is available in IBM watsonx Orchestrate, it will use this URL to route chat messages to the agent.

---

## Known limitations

- **Credential environment is hardcoded to `draft`.**  
  Credentials are always retrieved from the `draft` connection environment. Live-environment credential support is not yet implemented.

- **No runtime invocation (yet).**  
  Registered `azure_ai_foundry` agents appear in `orchestrate agents list` and can be added as collaborators. However, live chat invocations will not be routed to Azure AI Foundry until a runtime adapter is available. This is tracked separately from this CLI feature.

- **Single project per connection.**  
  Each connection covers one `endpoint` + `project_name`. To discover agents from multiple projects, create separate connections and run `discover` for each.

- **SaaS only.**  
  The `--provider azure_ai_foundry` flag is blocked on Developer Edition (`localhost`) and on-premises (CPD) environments.

---

## Troubleshooting

| Error | Likely cause | Fix |
|-------|-------------|-----|
| `--app-id is required` | `--app-id` not provided | Add `--app-id <connection-id>` |
| `missing the 'client_secret' credential entry` | Connection not fully configured | Re-run `orchestrate connections set-credentials` |
| `Failed to list Azure AI Foundry agents: 401 Unauthorized` | Invalid `tenant_id`, `client_id`, or `client_secret` | Check your service principal credentials |
| `Failed to list Azure AI Foundry agents: 403 Forbidden` | Service principal lacks permissions in Azure AI Foundry | Grant appropriate role (e.g. Azure AI Developer) |
| `Failed to list Azure AI Foundry agents: 404 Not Found` | Wrong `endpoint` or `project_name` | Check your connection credentials |
| `Azure AI Foundry agent discovery is only supported in SaaS environments` | Running in Developer Edition or on-prem | Use a SaaS workspace |
