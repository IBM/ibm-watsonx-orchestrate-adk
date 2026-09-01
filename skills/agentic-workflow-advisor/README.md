# Agentic Workflow Advisor

A Bob skill that analyses IBM watsonx Orchestrate agentic workflow artefacts and returns prioritised architecture recommendations covering performance, routing, data mapping, parallelism, and context management.

## What it does

The skill performs static analysis of your workflow artefact and runs 7 detection checks covering the most impactful design patterns that cause performance issues, routing failures, or maintainability problems in production. Findings are grouped by impact — High, Medium, and Low — and each recommendation includes what was observed, why it matters, and what to do about it.

## Who it is for

- **Pro-code builders** — using the ADK path or reviewing exported workflow JSON
- **Low-code builders** — exporting their workflows built using the Flow Builder UI, for a pre-deployment review

## Usage

### Trigger phrases

- `"Review my agentic workflow"`
- `"Analyze my agentic workflow"`
- `"Audit this flow"`
- `"What architecture issues does my workflow have?"`
- `"Run an agentic workflow advisor check on this"`

### What to provide

| Artefact | Required | Notes |
|----------|----------|-------|
| Workflow JSON | ✅ Yes | Export from Flow Builder or ADK |
| Agent YAML | Optional | Required for Check 4 (guidelines analysis) only |

Paste the artefact directly into chat or attach the file.

### Example prompt

```
Review my agentic workflow

<paste workflow JSON here>
```

Or with multiple artefacts:

```
Run an agentic workflow advisor check on these files — I've attached the workflow JSON and agent YAML.
```

## Detection Checks

| # | Pattern | Impact |
|---|---------|--------|
| 1 | Sequential nodes with no data dependencies | 🔴 High |
| 2 | Required input field with no explicit mapping (or unmapped flow output field) | 🟡 Medium |
| 3 | LLM-based routing over a deterministic upstream result | 🔴 High |
| 4 | Flow-scoped variable expressions (`{flow.*}`, `{self.*}`) in agent guidelines | 🟡 Medium |
| 5 | Input schema with >20 fields | 🟢 Low |
| 6 | Toolkit tool with no external HTTP calls | 🟢 Low |
| 7 | Agent node that could be replaced with a Generative Prompt node | 🟡 Medium |

## Sample Output

```
## Agentic Workflow Advisor — customer_support_flow

### 🔴 High Impact

**Sequential tool execution**
- Observed: Nodes `get_account_details`, `get_order_history`, and `get_open_tickets` are connected sequentially with no data dependencies between them
- Why it matters: Each tool averages ~1.5s. Running sequentially costs ~4.5s; running in parallel costs ~1.5s — a saving of ~3s per invocation
- Recommended action: Wrap all three nodes in a Parallel Node

**LLM-based routing over deterministic result**
- Observed: Agent node `intent_router` receives the output of `feature_match_tool` (a fixed category string) and routes to downstream flows based on it
- Why it matters: Passing a deterministic result through an agent ReACT loop adds 2–10s per turn and introduces routing failures due to LLM variability
- Recommended action: Replace `intent_router` with a Master Flow using Branch (Match) nodes that evaluate the feature match output directly

### 🟡 Medium Impact

**Unmapped required input field**
- Observed: Node `create_ticket` has required field `customer_id` with no explicit mapping in input_map
- Why it matters: The runtime will use an LLM to resolve this field at execution time — this always costs 500–3000ms per invocation. Explicit mapping costs <10ms.
- Recommended action: Add an explicit mapping for `customer_id`. If this latency is acceptable for the use case, no action is needed.

### 🟢 Low Impact / Housekeeping

**Oversized input schema**
- Observed: The top-level flow input schema defines 34 fields
- Why it matters: Large schemas increase token usage on every auto-mapping call and agent context retrieval
- Recommended action: Audit which fields are actually read inside the flow and remove unused ones

---
_Review scope: workflow JSON ✅ | agent YAML ❌ not provided | Checks skipped: Check 4 (agent YAML not provided)_
```

## Scope and Limitations

- **All flows are in scope** — the skill evaluates any watsonx Orchestrate flow JSON. Checks that target a specific node kind produce no findings if that node kind is absent.
- **Static analysis only** — the skill does not invoke, modify, or connect to any running workflow or platform API.
- **No automated remediation** — the skill identifies and explains issues; it does not rewrite the workflow.
- **Agent YAML is optional** — Check 4 (guidelines analysis) requires the agent YAML; all other checks run from the workflow JSON alone.
- **Check 6 runs from description alone** — no toolkit Python source needed; the skill infers from the node's `description` and `display_name`.
- **Check 7 considers `thread_control_policy`** — if `REUSE_AND_CORRELATE` is set on the agent node, the recommendation explicitly notes that a Generative Prompt node cannot maintain conversation context continuity.

## Distribution

This skill is available via:
- **Bob** — auto-activates when trigger phrases are used in Bob chat (watsonx Orchestrate)
- **ADK** — available at `skills/agentic-workflow-advisor/` in the [ibm-watsonx-orchestrate-adk](https://github.com/IBM/ibm-watsonx-orchestrate-adk/tree/main/skills) repository

## References

- [ADK Skills Documentation](https://developer.watson-orchestrate.ibm.com/agents/agent_design/wxo_skills)
