# Box Knowledge Base Example

This example demonstrates how to create a knowledge base backed by a Box content source and wire it to an HR benefits agent.

## Prerequisites

- `orchestrate` CLI installed and authenticated
- `jq` installed (`brew install jq` on macOS, `apt-get install jq` on Linux)
- A Box application with a service account and JWT credentials

## Files

```
box_knowledge/
├── agents/
│   └── hr_benefits_agent.yaml        # Agent that uses the knowledge base
├── knowledge_base/
│   └── box_knowledge_base.yaml       # KB spec with content_source + sync_job
├── config-box-template.json          # Template for Box credentials
├── import_all.sh                     # Creates connection, imports KB + agent
├── remove_all.sh                     # Removes KB + agent
└── README.md
```

## Setup

### Step 1 — Configure Box credentials

Copy the credentials template and fill in your Box application details:

```bash
cp config-box-template.json config-box.json
```

Edit `config-box.json` and replace the placeholder values with your Box JWT credentials:

| Field | Description |
|---|---|
| `client_id` | OAuth2 client ID from your Box app |
| `client_secret` | OAuth2 client secret from your Box app |
| `enterprise_id` | Your Box enterprise ID |
| `public_key` | Public key ID from the JWT key pair |
| `private_key` | PEM-encoded private key |
| `private_key_password` | Passphrase for the private key |

### Step 2 — Run import_all.sh

```bash
./import_all.sh
```

This will:
1. Create and configure the `box` connection
2. Import the knowledge base, resolving the Box connection via `-a box`
3. Import the `hr_benefits_agent`

A custom credentials file path can be passed as an argument:

```bash
./import_all.sh /path/to/my-box-creds.json
```

## Cleanup

```bash
./remove_all.sh
```
