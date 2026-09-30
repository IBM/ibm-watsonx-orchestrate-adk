# Discover and Register AWS Bedrock Agents

This guide explains how to discover agents deployed in **AWS Bedrock** and register them as callable collaborators in your IBM watsonx Orchestrate workspace using the ADK CLI.

> **Availability:** SaaS environments only. This command is not available in Developer Edition or on-premises deployments.

---

## Prerequisites

1. **AWS account** with one or more agents created in [Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html).
2. **IAM user or role** with permission to list Bedrock agents.  
   The required IAM permission is `bedrock:ListAgents`. A managed policy that grants this is `AmazonBedrockReadOnlyAccess` (or a custom policy scoped to this action).
3. **Access key ID and secret access key** (and optionally an STS session token) for the IAM identity.
4. **IBM watsonx Orchestrate CLI** (`orchestrate`) installed and authenticated to a SaaS workspace.

---

## Step 1 — Create a connection for your AWS credentials

Store your AWS IAM credentials in a `key_value` connection. The connection must contain the following entries:

| Entry key | Value |
|-----------|-------|
| `access_key_id` | Your AWS access key ID (e.g. `AKIAIOSFODNN7EXAMPLE`) |
| `secret_access_key` | Your AWS secret access key |
| `region` | AWS region where your agents are deployed (e.g. `us-east-1`) |
| `session_token` | *(Optional)* STS session token for temporary credentials |

```bash
# Create the connection
orchestrate connections add --app-id bedrock-conn

# Configure it as a team key_value connection in draft
orchestrate connections configure \
  --app-id bedrock-conn \
  --kind key_value \
  --type team \
  --environment draft

# Store the credentials
orchestrate connections set-credentials \
  --app-id bedrock-conn \
  --environment draft \
  --entries access_key_id=AKIAIOSFODNN7EXAMPLE \
  --entries secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY \
  --entries region=us-east-1
```

> **Tip:** For temporary credentials from `aws sts assume-role`, also pass `--entries session_token=<token>`.

---

## Step 2 — Discover and register agents

### Import all agents in the region

```bash
orchestrate agents discover \
  --provider bedrock_agent \
  --app-id bedrock-conn
```

The CLI will display a table of discovered agents and prompt you to confirm before importing.

### Import specific agents by name

```bash
orchestrate agents discover \
  --provider bedrock_agent \
  --app-id bedrock-conn \
  --name "Customer Support" \
  --name "Sales Assistant"
```

`--name` is repeatable and case-insensitive. Only agents whose `agentName` matches are imported.

### Skip confirmation (CI/scripted use)

```bash
orchestrate agents discover \
  --provider bedrock_agent \
  --app-id bedrock-conn \
  --yes
```

---

## Step 3 — Verify the registered agents

```bash
orchestrate agents list
```

Agents registered from Bedrock appear with `provider: bedrock_agent`.

---

## How agents are converted

| Bedrock field | WXO field | Notes |
|---------------|-----------|-------|
| `agentName` | `name` (sanitized) | Lowercased, spaces and dashes → underscores, max 64 chars |
| `agentName` | `title` | Used as the display title unchanged |
| `description` | `description` | Falls back to `"AWS Bedrock agent: <agentName>"` if empty |
| `agentId` | `api_url` | `https://bedrock-agent-runtime.{region}.amazonaws.com/agents/{agentId}/agentAliases/TSTALIASID/` |
| — | `provider` | Always `bedrock_agent` |

The `api_url` stores a canonical Bedrock runtime resource URL with a placeholder alias. It is used by the runtime invocation adapter once a Bedrock adapter is available in IBM watsonx Orchestrate.

---

## Known limitations

- **Credential environment is hardcoded to `draft`.**  
  Credentials are always retrieved from the `draft` connection environment. Live-environment credential support is not yet implemented.

- **No runtime invocation (yet).**  
  Registered `bedrock_agent` agents appear in `orchestrate agents list` and can be added as collaborators. However, live chat invocations will not be routed to AWS Bedrock until a runtime adapter is available.

- **Single region per connection.**  
  Each connection covers one `region`. To discover agents from multiple regions, create separate connections and run `discover` for each.

- **SaaS only.**  
  The `--provider bedrock_agent` flag is blocked on Developer Edition (`localhost`) and on-premises (CPD) environments.

---

## Troubleshooting

| Error | Likely cause | Fix |
|-------|-------------|-----|
| `--app-id is required` | `--app-id` not provided | Add `--app-id <connection-id>` |
| `missing the 'access_key_id' credential entry` | Connection not fully configured | Re-run `orchestrate connections set-credentials` |
| `missing the 'secret_access_key' credential entry` | Connection not fully configured | Re-run `orchestrate connections set-credentials` |
| `missing the 'region' credential entry` | Connection not fully configured | Re-run `orchestrate connections set-credentials` |
| `Failed to list AWS Bedrock agents: 403` | IAM user lacks `bedrock:ListAgents` | Grant `AmazonBedrockReadOnlyAccess` or a custom policy with `bedrock:ListAgents` |
| `Failed to list AWS Bedrock agents: 404` | Wrong `region` | Check that your agents exist in the configured region |
| `AWS Bedrock agent discovery is only supported in SaaS environments` | Running in Developer Edition or on-prem | Use a SaaS workspace |
