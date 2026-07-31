# Catalog Onboarding Example

This example contains a reference native agent YAML with all fields required for
submitting to the **watsonx Orchestrate Agent Catalog** via the IBM Concierge app.

It is intentionally minimal (no tools, no connections) so it can be used as a
packaging test without any external dependencies.

## Files

| File | Purpose |
|---|---|
| `agents/catalog_example_agent.yaml` | Complete reference YAML with all required catalog fields |

## Required Catalog Fields

| Field | Type | Rule |
|---|---|---|
| `display_name` | string | Human-readable name |
| `publisher` | string | No underscores — e.g. `"Acme Corp"` |
| `category` | string | Always `"agent"` |
| `agent_role` | string | `"manager"` or `"collaborator"` |
| `hidden` | boolean | `false` to publish |
| `restrictions` | string | `"editable"`, `"non_editable"`, or `"custom"` |
| `bundled` | boolean | |
| `delete_by` | string/null | `YYYY-MM-DD` or `null` |
| `version` | string | Semver `x.y.z` — must increment on re-submission |
| `change_log` | string[] | One entry per version |
| `language_support` | string[] | Each entry starts with a capital letter |
| `tags` | string[] | Each entry starts with a capital letter |
| `icon` | string | Inline SVG |
| `part_number` | object | Keys: `aws`, `ibmcloud`, `cp4d` (note: `ibmcloud` not `ibm_cloud`) |
| `scope` | object | `form_factor` with keys `aws`, `ibmcloud`, `cp4d` |
| `channels` | array | |
| `related_links` | array | Keys capitalised, no underscores; type is `"hyperlink"` or `"embedded"` |
| `billing` | object | `{ "metered": false }` |
| `supported_apps` | array | |
| `collaborators` | array | |
| `tools` | array | |

### `part_number` + `scope` Business Rule

If `part_number.<platform>` is **not null** → `scope.form_factor.<platform>` must be `"paid"`.  
If `part_number.<platform>` is **null** → `scope.form_factor.<platform>` must be `"free"`.

## Packaging Commands

```bash
# 1. Import the agent into your local environment
orchestrate env activate local
orchestrate agents import -f examples/agent_builder/catalog_onboarding/agents/catalog_example_agent.yaml

# 2. Create the offering folder
orchestrate partners offering create \
  --offering catalog_example \
  --publisher "Acme Corp" \
  --type native \
  --agent-name catalog_example_agent

# 3. Review / update placeholder values in catalog_example/agents/catalog_example_agent.yaml

# 4. Package
orchestrate partners offering package \
  --offering catalog_example \
  --folder .
# Produces: catalog_example-1.0.0.zip
```
