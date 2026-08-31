---
name: agentic-workflow-advisor
description: Analyzes IBM watsonx Orchestrate agentic workflow artefacts (JSON or Python @flow) and returns prioritised architecture recommendations grouped by impact. Use when the user wants to review, analyze, or audit a workflow for performance issues, routing failures, or design best practices. Triggers on phrases like "review my workflow", "analyze my agentic workflow", "audit this flow", "what's wrong with my workflow", or when a workflow JSON or Python flow file is provided with a request for feedback.
tags:
  - watsonx-orchestrate
  - flow
  - architecture
  - analysis
  - performance
---

# Agentic Workflow Advisor

## Purpose

This skill defines the process for analyzing IBM watsonx Orchestrate agentic workflow artefacts (JSON or Python `@flow`) and generating a structured, prioritised set of architecture recommendations that help builders identify and fix design issues before they reach production.

The skill performs **static analysis only** — it does not invoke, modify, or connect to any running workflow or platform API. It works entirely from the artefact the builder provides.

**Use this skill when you need:**
- A prioritised list of architecture issues before deploying a workflow to production
- Performance diagnosis for flows with slow response times or high latency
- A repeatable design review that does not require engineering escalation
- Recommendations grounded in real platform behaviour and measured latency figures

## Objective

Analyze an agentic workflow artefact and produce a **structured recommendation report** that:
- Identifies architecture patterns known to cause performance problems, routing failures, or maintainability risks
- Prioritises findings by impact — High, Medium, and Low
- Provides a specific, actionable recommended action for each finding
- Is specific to the artefact provided — not generic advice

## Scope

This skill applies to:
- Any workflow JSON artefact exported from the IBM watsonx Orchestrate Flow Builder UI
- Any workflow JSON artefact authored via the ADK pro-code path
- Any Python flow file authored via the ADK pro-code path using the `@flow` decorator
- Agent YAML definitions (optional — used for Check 3 agent node analysis)

**In scope:**
- All watsonx Orchestrate flows — any JSON with `"spec": { "kind": "flow", ... }`, or any Python file with a `@flow`-decorated function, regardless of whether they contain an Agent node
- All supported node types: `tool`, `agent`, `script`, `branch`, `parallel`, `foreach`, `loop`, `prompt`, `docproc`, `docext`, `decisions`, `user`, `user_flow`
- Top-level flow structure and the internals of container nodes (`parallel`, `foreach`, `loop`, `user_flow`)

**Python `@flow` artefacts:**
When the artefact is a Python file using the ADK `@flow` decorator, the same 7 checks apply. Run `scripts/extract_flow_info.py <file.py>` to pre-extract the structural summary before analysis (see Step 1).

**Out of scope:**
- Agent definitions beyond their YAML (model selection, RAG configuration, knowledge base content)
- Python toolkit source code beyond identifying whether a tool makes external calls
- Automated remediation — this skill identifies and explains issues; it does not rewrite the workflow
- Performance benchmarking or load testing guidance

## Analysis Principles

**IMPORTANT**: Generate findings based ONLY on what is present in the provided artefact.

**Rules:**
- Reference actual `display_name` values from the artefact — never use internal node IDs like `tool_562086`
- Do not flag issues you cannot point to directly in the JSON
- Do not fabricate recommendations to appear thorough — a clean result is a valid and useful output
- Use measured latency figures from the platform: explicit mapping <10ms, auto-mapping 500–3000ms, context compression 1000–5000ms (triggers at >6500 tokens), per-task transition ~35ms, agent context retrieval ~500ms, Generative Prompt 500–3000ms, agent ReACT loop 2–10s
- Distinguish between definite findings and candidates (e.g. Check 6 is a candidate based on description, not a certainty)
- If an artefact is partially incomplete (`metadata.is_under_specified: true`), note this and scope findings accordingly
- **Output only what the 7 checks produce.** Do not add freeform observations, "worth noting" sections, commentary, or supplementary advice outside the check findings. If the checks produce no findings, the output is the clean result message — nothing else.

**Platform-managed fields — do NOT flag or comment on:**
- `assignees` — this field on `user_flow` nodes is populated automatically by the platform (defaulting to the flow initiator). It does not require an explicit `input_map`. Never suggest mapping `assignees` to a user list.
- Any other field whose absence of an `input_map` is intentional platform behaviour — if in doubt, do not flag it.

**Excluded from this assessment:**
- Non-functional requirements beyond what is detectable statically (throughput, concurrency, load behaviour)
- Business logic correctness — the skill assesses architecture patterns, not whether the flow does the right thing
- Security review of credentials, API keys, or data handling beyond what is visible in the JSON structure
- Completeness gaps on fields not covered by the 7 checks — missing `input_map` on a `user_flow` node is not an architecture issue detectable by this skill

---

## Core Principle

Evaluate the workflow artefact for what it will do at runtime — not for how it looks on the canvas. A flow that appears clean may have sequential tool nodes with no dependencies, auto-mapped fields invoking an LLM on every call, or an agent used purely to route a result that is already deterministic. These patterns are invisible in the UI and only surface under load or in production. This skill makes them visible before deployment.

## Workflow JSON Structure Reference

Before running analysis, understand the structure of a watsonx Orchestrate workflow JSON export:

```
{
  "spec": { "kind": "flow", "name": "...", "display_name": "...", "private_schema": { ... } },
  "nodes": {
    "<node_name>": {
      "spec": {
        "kind": "<node_kind>",
        "name": "...",
        "display_name": "...",
        "input_schema": { "type": "object", "required": [...], "properties": { ... } },
        "output_schema": { ... }
      },
      "input_map": {
        "spec": {
          "fallback_strategy": "ask_the_user" | "no_value",
          "maps": [
            {
              "metadata": { "assignmentType": "variable" | "literal" | "pyExpression" | "automap" },
              "target_variable": "self.input.<field>",
              "value_expression": "...",
              "has_no_value": false | true
            }
          ]
        }
      },
      "edges": [...],
      "nodes": { ... }
    }
  },
  "edges": [
    { "id": "...", "start": "<node_name>", "end": "<node_name>", "display_name": "..." }
  ],
  "metadata": { "source_kind": "ui" | "adk", "is_under_specified": true | false }
}
```

**Key structural facts:**
- Mappings live at `node.input_map.spec.maps[]` — not at `data_map`
- `fallback_strategy` lives at `node.input_map.spec.fallback_strategy`
- A required field is auto-resolved by the runtime if it has no entry in `maps[]` — detection is purely structural (gap between `input_schema.required[]` and `maps[].target_variable`)
- Empty `maps: []` means all required fields fall through to `fallback_strategy`
- `script` nodes (`"kind": "script"`) ARE Logic Code Blocks — inline `fn` expression, no external calls
- Container nodes (`parallel`, `foreach`, `loop`, `user_flow`) have their own inner `edges` and `nodes`
- Nodes inside a `parallel` container are already concurrent — do not flag them for sequential execution

**`"kind": "tool"` means exactly that — a tool node.**
Do NOT infer what lies behind it (MCP, OpenAPI, Python, sub-flow, or anything else) from the node's `name`, `display_name`, or `description`. Treat every `tool` node uniformly for all detection checks.

**Supported node kinds:**
`tool` | `agent` | `script` | `branch` | `parallel` | `foreach` | `loop` | `prompt` | `docproc` | `docext` | `decisions` | `user` | `user_flow` | `start` | `end`

---

## Analysis Workflow

### Step 1 — Collect the Artefact

If the user has not yet provided a workflow artefact in this message, reply with exactly this:
> _"Please paste your workflow JSON or provide the file path to analyze."_

Then stop. Do nothing else.

**STOP. The following are strictly forbidden before the user provides content in this message:**
- Do NOT explore, list, or search the workspace or any directory
- Do NOT read any file from disk — not `.bob/tmp/`, not `resource/`, not anywhere
- Do NOT use any previously seen files from earlier conversations or sessions
- Do NOT assume any file in the workspace is the intended target
- The ONLY valid input is content the user explicitly provides in the current message: either pasted JSON/Python, or a file path they typed in this message

The artefact must come from the user in this conversation turn. Nothing else is acceptable.

**Valid inputs (once the user provides one):**
1. **A file path** the user typed (e.g. `resource/MyFlow/MyFlow.json`) — fastest, Bob runs the script directly on it
2. **Pasted raw JSON or Python `@flow` content** — Bob saves to temp file and runs the script
3. **Agent YAML** — optional, used for Check 3 agent node analysis

If only partial artefacts are provided, proceed with what is available and clearly state at the end of the review what could not be assessed.

---

### Step 2 — Pre-flight: Determine Analysis Path

Do NOT ask the user any question.

**Path A — User provided a file path** (e.g. `resource/MyFlow/MyFlow.json`):
Run the extraction script directly on that path — do not read the file contents:
```
python3 .bob/skills/agentic-workflow-advisor/scripts/extract_flow_info.py <file_path>
```
Use `python3`. If not found, try `python`. Use the full path to the script relative to workspace root.
After the script runs, map its output keys to checks using the table at the end of this step, then proceed to Step 3.

---

**Path B — User pasted raw JSON content**:

**Do NOT write the JSON to any file. Do NOT use write_file. Do NOT run execute_command. Do NOT use a heredoc. Do NOT re-emit the JSON content in any tool call.** Re-emitting thousands of lines of JSON through any tool takes 10+ minutes. It must never happen.

Apply the extraction algorithm (E0–E3) below against the JSON in context. Then go directly to Step 4 output.

**OUTPUT RULE — strictly enforced:**
The first token Bob outputs to the user must be `##` (the report header: `## Agentic Workflow Advisor — [flow name]`).
Nothing else comes before it — no sentence, no label, no acknowledgement. Do not say "Running…", "Analysing…", "Working through…", "E0–E3…", "silently…", "against the pasted JSON", or any other intro phrase. The report header is the very first thing the user sees.

Everything from the report header onward is shown normally: flow name, execution path, findings, review scope line.

---

#### Extraction Algorithm (E0–E3 — internal only, never output)

**E0 — Resolve schemas**
- Top-level schema: `data.spec.input_schema` or `data.spec.private_schema`
- If that value is `{"$ref": "#/schemas/SomeName"}`, resolve it: `top_input_schema = data.schemas["SomeName"]`
- Otherwise use the value inline
- `top_properties` = keys of `top_input_schema.properties` (or `[]`)
- `top_required` = `top_input_schema.required` (or `[]`)
- `flow_name` = `data.spec.display_name` or `data.spec.name`

**E1 — Walk all nodes**
Iterate `data.nodes` (top-level dict, keys are node IDs). For each node:
- `kind` = `node.spec.kind`
- `display_name` = `node.spec.display_name` or node_id
- `description` = `node.spec.description` (or `""`)
- `input_schema_required` = `node.spec.input_schema.required` (or `[]`)
- `input_schema_properties` = keys of `node.spec.input_schema.properties` (or `[]`)
- `explicitly_mapped_fields` = all `target_variable` values in `node.input_map.spec.maps[]` that start with `"self.input."`, with the `"self.input."` prefix stripped
- `unmapped_required_fields` = fields in `input_schema_required` NOT in `explicitly_mapped_fields`
- `phantom_mapped_fields` = fields in `explicitly_mapped_fields` NOT in `input_schema_properties`
- `fallback_strategy` = `node.input_map.spec.fallback_strategy` (or `""`)
- If `kind == "agent"`: also capture `message` = `node.spec.message`, `thread_control_policy` = `node.spec.thread_control_policy`, `output_schema_properties` = keys of `node.spec.output_schema.properties`
- If `kind == "branch"`: also capture `branch_conditions` = `node.spec.evaluator.conditions[]` → each as `{expression, default, edge_id}`
- If `kind == "parallel"`: also capture `parallel_children` = entries in `node.nodes{}` where `kind` is NOT `"start"` or `"end"` → each as `{id, kind, display_name}`; `parallel_is_conditional` = any condition in `node.spec.evaluator.conditions[]` where `default != true`
- If `kind` is `"start"` or `"end"`: skip (internal plumbing)
- For nodes with sub-nodes (e.g. `parallel`): also walk `node.nodes{}` with the same rules above

**E2 — Build edge maps**
From `data.edges[]`:
- `successors[start_id]` = list of `end_id` values
- `predecessors[end_id]` = list of `start_id` values

**E3 — Derive check inputs** (populate these named results for Step 3):

**`check_1_sequential_tool_pairs`**: For each node where `kind == "tool"`, for each successor where `kind == "tool"`:
- Look at successor's `node.input_map.spec.maps[]` → collect all `value_expression` strings
- If any `value_expression` contains the current node's `display_name`, `name` (`node.spec.name`), or `node_id` → **has dependency** → skip
- Otherwise → **no dependency** → add `{node_a: display_name, node_b: successor_display_name}`

**`check_1_parallel_containers`**: All nodes where `kind == "parallel"` → `{display_name, children: parallel_children, is_conditional: parallel_is_conditional}`

**`check_2_unmapped_required_fields`**: All nodes where `unmapped_required_fields` is non-empty AND `kind` is NOT one of `start, end, branch, parallel, foreach, loop, user_flow` → `{display_name, kind, unmapped_required_fields, fallback_strategy}`

**`check_2_phantom_mappings`**: All nodes where `phantom_mapped_fields` is non-empty → `{display_name, kind, phantom_mapped_fields}`

**`check_3_branch_nodes`**: All nodes where `kind == "branch"` → `{display_name, conditions: branch_conditions}`

**`check_3_7_agent_nodes`**: All nodes where `kind == "agent"` → `{display_name, message, thread_control_policy, output_schema_properties, predecessors: [{display_name, kind}] from predecessors map}`

**`check_5_input_schema_field_count`**: `len(top_properties)`

**`check_6_tool_nodes`**: All nodes where `kind == "tool"` → `{display_name, description}`

**`node_kinds_present`**: sorted unique set of all `kind` values across all nodes

**`is_under_specified`**: `data.metadata.is_under_specified` (default `false`)

---

**Script output keys** (Path A — map script output directly to checks):
- `check_1_sequential_tool_pairs` → Check 1 candidates
- `check_1_parallel_containers` → Check 1 exemptions (children already concurrent)
- `check_2_unmapped_required_fields` → Check 2 unmapped field findings
- `check_2_phantom_mappings` → Check 2 phantom mapping findings
- `check_3_branch_nodes` → Check 3 branch condition evidence
- `check_3_7_agent_nodes` → Check 3 (predecessors) and Check 7 (message, tools, output_schema)
- `check_5_input_schema_field_count` → Check 5 field count
- `check_6_tool_nodes` → Check 6 tool descriptions
- `node_kinds_present` → which checks will produce findings
- `is_under_specified: true` → note at top that flow is incomplete, findings may be partial

---

### Step 3 — Run All 7 Detection Checks

Work through every check below. Collect all findings before composing the output — do not output findings one by one.

---

#### Check 1 — Sequential Tool Execution 🔴 High Impact

**What to look for:**
Two or more `"kind": "tool"` nodes connected sequentially in the top-level `edges` array with no data dependency between them.

**How to detect:**
1. Build the execution sequence from the top-level `edges` array
2. Find consecutive runs of tool nodes (skip `user_flow`, `script`, `branch`, `prompt`, `parallel`, etc.)
3. For each consecutive tool pair (A → B), check `node_B.input_map.spec.maps`:
   - If any map entry has a `value_expression` referencing node A's output (e.g. contains `flow["<node_A_display_name>"]` or `flow.<node_A_name>`), there IS a dependency — do not flag
   - If no map entry references node A, there is NO dependency — flag this pair
4. Skip nodes already inside a `parallel` container — they are intentionally concurrent

**Flag when:** 2 or more consecutive top-level tool nodes share no data dependency.

**Recommendation:**
> Sequential tool execution detected: [list node display_names]. These tool nodes execute one after the other but share no data dependency. Wrap them in a **Parallel Node** — in the Flow Builder, add a Parallel Node container and move these tool nodes inside it. The Parallel Node runs all contained nodes at the same time, so the total wait time becomes the duration of the slowest node rather than the sum of all nodes. Typical saving: 2–4s for tools averaging 1–2s each, plus 35ms orchestration overhead per eliminated sequential step.

---

#### Check 2 — Unmapped Required Input Field 🟡 Medium Impact

**What to look for:**
Any node where `input_schema.required[]` lists fields that have no explicit entry in `input_map.spec.maps` — meaning the runtime must resolve the value another way. Also covers the flow-level `output_map` if output fields are defined but not explicitly mapped. Applies to all node kinds that have an `input_schema`, including `tool`, `agent`, `prompt`, `docproc`, and `docext`.

**Context — automap is a supported feature with a known performance cost:**
Auto-mapping is valid and intentional — the runtime uses an LLM to resolve unmapped required fields from available context. However, it always costs 500–3000ms per invocation regardless of whether it was chosen deliberately or left as a default. This check always reports unmapped required fields with those numbers so the builder can make an informed decision. If explicit mapping is not feasible or the latency is acceptable for the use case, there is no need to act.

**How to detect:**
1. For each node that has both `input_schema.required` and `input_map`:
   - Collect required fields from `input_schema.required[]`
   - Collect explicitly mapped targets from `input_map.spec.maps[].target_variable` (extract field name after `self.input.`)
   - Any required field not covered by an explicit map entry will be resolved by the runtime at execution time
2. Also check the flow-level `output_map.spec.maps[]` — **only if `output_map.spec.maps` is non-empty** (i.e. the builder has defined at least one output field). If any output field has no explicit mapping source, flag it. If `output_map.spec.maps` is empty or absent, skip — there are no output fields to evaluate.
3. **Phantom mapping check** — for each `input_map.spec.maps` entry, extract the field name from `target_variable` (after `self.input.`) and verify it exists as a key in `input_schema.properties`. If it does NOT exist in `input_schema.properties`, it is a phantom mapping: the value is assigned to a field the node does not declare, so it is silently discarded at runtime. This is a copy-paste error signal — flag it regardless of performance intent. Common pattern: a field is renamed in the node spec but an old mapping with the previous name was not removed, resulting in both a phantom entry (old name) and a potentially missing entry (new name, which may or may not have a separate correct mapping).

**Flag when:** Any required field on a node has no explicit mapping (performance-mode recommendation), OR any `input_map.spec.maps` entry targets a field name not present in `input_schema.properties` (phantom mapping — always flag).

**Recommendation (node input — unmapped required field):**
> Unmapped required field on [display_name]: required field(s) [list field names] have no explicit mapping in input_map. The runtime will use an LLM to resolve each unmapped field at execution time — this costs 500–3000ms per invocation regardless of how many fields are unmapped. Explicit mapping costs <10ms. If this latency is acceptable for the use case, no action is needed; otherwise add explicit mappings under input_map.spec.maps for each field.

**Recommendation (flow output_map — unmapped output field):**
> Unmapped flow output field: output field(s) [list field names] in output_map have no explicit mapping source. The runtime will use an LLM to resolve these at execution time — this costs 500–3000ms per invocation. If this latency is acceptable, no action is needed; otherwise add an explicit data mapping pointing to the node output that produces each value.

**Recommendation (phantom mapping):**
> Phantom mapping on [display_name]: input_map entry targeting `self.input.[field_name]` does not match any field in `input_schema.properties`. This value is silently discarded at runtime — the node never receives it. This is typically a copy-paste error where a field was renamed in the node spec but the old mapping was not removed. Remove the phantom entry and verify the intended field has a correctly named mapping. Cross-check `input_schema.required` to confirm no required field is inadvertently left unmapped as a result.

---

#### Check 3 — LLM-Based Routing over Deterministic Result 🔴 High Impact

**What to look for:**
An `agent` node that exists solely to route based on an already-deterministic result — where a `branch` node or tool could make the same decision without an LLM call.

**How to detect:**
1. For each agent node, check what node directly precedes it in the top-level `edges`
2. If the preceding node is `decisions`, `docproc`, `docext`, or a tool that produces a categorical/classification output (e.g. `feature_match_tool` returning `is_match` + `feature_match`), inspect the agent's `message` field for routing language ("route", "call", "invoke", "initiate", "based on", "depending on")
3. Check what follows the agent — if it goes directly to `branch`, `__end__`, or another flow invocation, this is a routing-only agent
4. An agent node in a flow whose sole output feeds into a `branch` evaluator is a strong signal
5. **Also applicable at the top-level agent YAML level**: if the agent's `instructions` describe routing exclusively via a variable like `{llm_instruct}` or `{feature_match}` that was already computed by an upstream tool, this is LLM-based routing over a deterministic result — the agent adds latency without adding intelligence

**Do NOT flag:**
- Agent nodes doing genuine NLP work — semantic understanding, free-text matching from scratch, knowledge base search (RAG), or multi-turn reasoning. If the agent is performing the matching/classification itself (not receiving a pre-computed result), it is doing legitimate LLM work.
- An agent that receives a free-text user query and must determine the intent from scratch is NOT routing a deterministic result — it IS the decision-maker.

**Signal that separates the two:**
- 🔴 Flag: agent receives a pre-computed category string (e.g. `feature_match = "Block_Card_Flow"`) and passes it to another flow. The decision was already made.
- ✅ Do not flag: agent receives a raw user query and must determine intent, then act. The decision has NOT been made upstream.

**Flag when:** An agent exists solely to route based on a deterministic upstream result (the decision was already made before the agent was called).

**Recommendation:**
> LLM-based routing detected: agent [display_name] appears to route based on the output of [upstream display_name], which already produces a deterministic result. Passing this through an agent ReACT loop adds 2–10s per turn and introduces routing failures due to LLM variability. A Branch node evaluates the condition in <10ms with no LLM call. Replace with a Branch node — set the condition to evaluate the upstream result directly (e.g. `flow["<upstream>"].output.value == "category_x"`), eliminating the agent call entirely.

---

#### Check 5 — Oversized Input Schema 🟢 Low Impact

**What to look for:**
The top-level flow `spec.input_schema.properties` or any node's `input_schema.properties` has more than 20 fields.

**How to detect:**
- Count keys in `spec.input_schema.properties` for the flow and for each node
- Flag any that exceeds 20

**Flag when:** Any input schema has more than 20 fields.

**Recommendation:**
> Oversized input schema on [display_name]: [N] fields defined. Large schemas increase token footprint across every auto-mapping call and agent context retrieval. Critically, if the accumulated flow context exceeds 6500 tokens, the platform automatically triggers context compression — an LLM-based summarisation that adds 1000–5000ms of latency. Audit which fields are actually referenced in any input_map.spec.maps[].value_expression across the flow — unused fields can be removed or moved to flow.private (private_schema) to keep the context lean and prevent compression from triggering.

---

#### Check 6 — Tool Node That Should Be a Logic Code Block 🟢 Low Impact

**What to look for:**
A `"kind": "tool"` node whose evidence — across description, display_name, tool name, and output_schema shape — suggests pure in-process computation: string manipulation, formatting, arithmetic, data transformation, log item construction, timestamp generation — with no mention of external APIs, databases, or services.

**How to detect:**
Work through each signal in order. A node is a candidate if **any** signal points to pure computation and **none** contradicts it with an external-call indicator:

1. **`description` field** — read it. Explicit mentions of "API", "webhook", "database", "service", "HTTP", "external" rule it out. Phrases like "formats", "constructs", "matches", "computes", "prepares a log item", "returns a timestamp" are strong positive signals.
2. **`display_name` and `tool` field (the tool identifier string)** — when `description` is absent or empty, use these. Names like `prep_log_item_*`, `prep_log_event_item_*`, `timestamp`, `feature_match_tool`, `format_*`, `build_*` with no service qualifier are positive signals. Names like `post_*`, `send_*`, `fetch_*`, `get_*_from_api`, `notify_*` are negative (likely external calls).
3. **`output_schema` shape** — a schema with only simple string/boolean/number/object fields constructed from the inputs (no pagination, no status codes, no HTTP response wrapper) supports a pure-computation classification.
4. **`input_schema` fields** — if inputs are all primitive values (strings, booleans, numbers) and there are no fields like `url`, `endpoint`, `api_key`, `auth_token`, the tool likely makes no external call.
5. **Repetition pattern** — if multiple nodes share the same `tool` identifier and that identifier's name suggests data construction (e.g. four nodes all using `prep_log_event_item_6003BU`), evaluate them as a group. If the tool is a Logic Code Block candidate, flag all instances together.

- `"kind": "script"` nodes ARE already Logic Code Blocks — do not flag these, they are the correct pattern
- Only flag `"kind": "tool"` nodes
- When `description` is absent, rely on signals 2–5 above — do not skip the node

**Flag when:** A tool node's signals (description, tool name, display_name, output_schema, input_schema) collectively indicate pure in-process computation with no external calls. When multiple nodes share the same tool identifier and that tool is a candidate, flag all of them together as a group.

**Recommendation:**
> Logic Code Block candidate: tool node(s) [list display_names] appear to perform pure computation with no external API calls. Toolkit tools carry the overhead of a Python runtime invocation and network call (100–500ms per call). This logic can be moved into Script nodes (Logic Code Blocks) using inline Python expressions in the `fn` field. See any existing `"kind": "script"` nodes in this flow for the correct pattern. If these tools do make an external call not described in their metadata, disregard this finding.

---

#### Check 7 — Agent Node That Should Be a Generative Prompt Node 🟡 Medium Impact

**What to look for:**
An `agent` node whose `message` field contains a simple static prompt — plain text with no tool invocations, no RAG lookups, no multi-turn conversation, and no conditional logic — where a `prompt` node (`"kind": "prompt"`) would produce the same result at a fraction of the cost.

**Platform background:**
- An `agent` node starts a full ReACT loop: it creates or reuses a conversation thread, sends the message to the LLM, evaluates whether to call tools, waits for tool results, and iterates. This costs 2–10s per turn and carries thread management overhead.
- A `prompt` node (`"kind": "prompt"`) makes a single direct LLM call with a system prompt and optional user input. It has no ReACT loop, no thread, no tool calls. It is faster, cheaper, and simpler for tasks that only need one LLM response.

**How to detect:**
1. For each `agent` node, inspect the `message` field
2. Check whether the message is a **static string** with no variable references (no `{flow.`, `{self.`, `{context.`) — a hardcoded instruction like `"Tell a joke"` or `"Summarise the following"`
3. Check whether the agent has **no tools listed** — look for an empty or absent `tools` array in the agent's spec, and confirm no tool calls are implied by the message text
4. Check whether the agent's `description` and `output_schema` indicate a single text response (e.g. `output_schema.properties.value` of type `string`) — no structured multi-field output
5. Check whether the agent uses **memory or knowledge** — look for a `memory` configuration, a `knowledge_base` reference, or description language indicating conversation history or knowledge base retrieval
6. If steps 2–5 are all clear (static message, no tools, single text output, no memory/knowledge), this agent is doing work a `prompt` node could do

**Important — `thread_control_policy` caveat:**
If the agent node has `"thread_control_policy": "REUSE_AND_CORRELATE"`, note this explicitly in the recommendation. A `prompt` node does not maintain a conversation thread — replacing the agent with a `prompt` node will lose any conversation context continuity that `REUSE_AND_CORRELATE` was providing. Only suggest the replacement if thread continuity is not needed for this node's purpose.

**Do NOT flag:**
- Agent nodes whose `message` references flow variables (e.g. `{flow.input.user_query}`) — they are receiving dynamic input, not a static prompt
- Agent nodes that call tools, perform RAG, or have multi-turn reasoning in their description
- Agent nodes where `output_schema` defines multiple structured fields beyond a single `value` string
- Agent nodes that use memory or access a knowledge base — a `prompt` node has no memory and no knowledge base retrieval capability; replacing it would silently drop that functionality

**Flag when:** Agent `message` is a static string, the agent has no tools, no memory, no knowledge base, and the output is a single text response.

**Recommendation (without REUSE_AND_CORRELATE, no memory/knowledge):**
> Agent node [display_name] has a static message (`"[message text]"`) with no tool calls and a single text output. This is a simple LLM call — a **Generative Prompt node** (`kind: "prompt"`) will produce the same result without the overhead of a full agent ReACT loop (saving 2–10s per invocation). In the Flow Builder, replace this agent node with a Generative AI node and set its system prompt to the same text.

**Recommendation (with REUSE_AND_CORRELATE):**
> Agent node [display_name] has a static message (`"[message text]"`) with no tool calls and a single text output — a **Generative Prompt node** would normally be more efficient here. However, this node has `thread_control_policy: REUSE_AND_CORRELATE`, which means it is reusing an existing conversation thread to maintain context continuity. A Generative Prompt node does not support thread continuity. Only replace it if conversation context from previous turns is not needed for this node's purpose.

**Recommendation (agent uses memory or knowledge base):**
> Agent node [display_name] appears to use [memory / a knowledge base] — a Generative Prompt node does not support these capabilities, so no replacement is suggested. If the memory or knowledge base access can be removed, revisit this node for a potential simplification.

---

### Step 4 — Compose the Output

Use exactly the format below. Do not fabricate issues.

```
## Agentic Workflow Advisor — [spec.display_name]

> ⚠️ Note: This flow is marked as incomplete (is_under_specified: true). Findings may be partial.
> (Include this line only if metadata.is_under_specified is true)

**Execution path:** [display_name_1] → [display_name_2] → [display_name_3] → …
(Derive this from data.edges[] in order. Use display_name values only — no internal node IDs. Omit start/end nodes.)

---

### Check Results

| Check | Finding |
|---|---|
| Check 1 — Sequential Tool Execution | ⚠ [list sequential pairs found, e.g. "timestamp → prep_intent (no dependency)"] OR ✓ None |
| Check 2 — Unmapped Required Fields | ⚠ [node: field list] OR ✓ None |
| Check 2 — Phantom Mappings | ⚠ [node: field list] OR ✓ None |
| Check 3 — LLM-based Routing | ⚠ [agent name] OR ✓ None |
| Check 5 — Oversized Input Schema | ⚠ [N fields — exceeds 10] OR ✓ [N fields — within limit] |
| Check 6 — Logic Code Block Candidates | ⚠ [node names] OR ✓ None |
| Check 7 — Agent → Prompt Node | ⚠ [agent name] OR ✓ None |

---

### 🔴 High Impact
**[Issue title]**
- Observed: [what was found — use display_name values, not internal node IDs like tool_562086]
- Why it matters: [performance or stability impact with numbers where available]
- Recommended action: [specific, actionable step]

### 🟡 Medium Impact
**[Issue title]**
- Observed: [what was found]
- Why it matters: [impact]
- Recommended action: [action]

### 🟢 Low Impact / Housekeeping
**[Issue title]**
- Observed: [what was found]
- Why it matters: [impact]
- Recommended action: [action]

---
_Review scope: workflow JSON ✅ | agent YAML [✅/❌ not provided] | Checks skipped: [list any and why]_
```

If the workflow is clean:

```
## Agentic Workflow Advisor — [spec.display_name]

**Execution path:** [display_name_1] → [display_name_2] → …

### Check Results

| Check | Finding |
|---|---|
| Check 1 — Sequential Tool Execution | ✓ None |
| Check 2 — Unmapped Required Fields | ✓ None |
| Check 2 — Phantom Mappings | ✓ None |
| Check 3 — LLM-based Routing | ✓ None |
| Check 5 — Oversized Input Schema | ✓ [N fields] |
| Check 6 — Logic Code Block Candidates | ✓ None |
| Check 7 — Agent → Prompt Node | ✓ None |

✅ No architecture issues found across all applicable detection categories.

---
_Review scope: workflow JSON ✅ | agent YAML [✅/❌ not provided]_
```

---

## Key Analysis Rules

**Be evidence-based:**
- Reference actual node `display_name` values and field names from the artefact
- Do not flag issues you cannot point to in the JSON
- Distinguish between definite findings and candidates (e.g. Check 6 is a candidate, not a certainty)

**Be operational, not academic:**
- Focus on runtime performance and stability impact
- Evaluate what the JSON says, not what the builder probably intended
- Use measured latency figures (500–3000ms auto-mapping, 2–10s agent ReACT loop, 35ms per task transition)

**Do not fabricate:**
- If no issues are found in a category, do not flag it
- If an artefact is clean, say so directly — a clean result is a valid and useful output

**Prioritise high-impact changes:**
- Present High Impact findings first
- For each finding, give a specific, actionable recommended action — not a general suggestion

---

## Edge Case Handling

| Situation | Handling |
|-----------|----------|
| No `agent` nodes in the flow | Check 3 will produce no findings — continue with the remaining checks |
| Agent does genuine NLP work (RAG, free-text matching from scratch) | Do NOT flag for Check 3 — the agent is the decision-maker, not routing a pre-computed result |
| `kind: "script"` nodes | Already Logic Code Blocks — correct pattern, do not flag for Check 6 |
| Nodes inside `parallel` container | Already concurrent — do not flag for Check 1 |
| `decisions` node with empty `rules` | Partially configured — note in review but do not flag as architecture issue |
| `metadata.is_under_specified: true` | Note at top of review that flow is incomplete, findings may be partial |
| Any node with `fallback_strategy: ask_the_user` | Do NOT flag — valid HITL behaviour everywhere; the platform interrupts and prompts the user for the missing value |
| `output_map` with non-empty `spec.maps` and unmapped output fields | Flag for Check 2 (performance-mode) — output fields will be resolved at execution time, adding 500–3000ms |
| `output_map` with empty or absent `spec.maps` | Skip Check 2 on output_map — nothing to evaluate |
| Large workflow exceeding context window | Review top-level nodes first, then recurse into container nodes; consolidate into a single output |
| Multiple flows provided | Review each separately, then add a cross-flow summary for shared issues |

---

## Output Requirements

**Every review must produce:**
1. A structured markdown report using the format in Step 4
2. All findings grouped by impact level (High / Medium / Low)
3. Each finding with: observed pattern, why it matters, recommended action
4. A review scope footer listing what artefacts were provided and which checks were skipped

**The report must be:**
- Specific — reference actual `display_name` values, field names, and node types from the artefact
- Evidence-backed — every finding must point to something in the JSON
- Actionable — every recommended action must be a concrete step, not a general suggestion
- Honest — if no issues are found, say so; do not fabricate recommendations to appear thorough

---

## Usage Instructions

### To use this skill

1. **Provide the workflow artefact**: Export your flow from Flow Builder UI or share your ADK-authored workflow JSON
2. **Optionally provide the agent YAML**: Useful for deeper Check 3 (LLM-based routing) analysis
3. **Trigger the review**: Use any of the example prompts below
4. **Review findings**: Address High Impact findings first, then Medium, then Low
5. **Iterate**: Re-run after fixing issues to confirm they are resolved

### Example prompts

```
Review my agentic workflow
<paste workflow JSON here>
```

```
Analyze my agentic workflow for architecture issues
<attach workflow JSON file>
```

```
What architecture issues does my workflow have?
<paste or attach workflow JSON and optionally agent YAML>
```

```
Run an agentic workflow advisor check on this flow
<paste workflow JSON here>
```

### What to provide

| Artefact | Required | Notes |
|----------|----------|-------|
| Workflow JSON | ✅ Yes | Export from Flow Builder or ADK |
| Agent YAML | Optional | Useful for Check 3 (LLM-based routing) analysis |

### Example output

```
## Agentic Workflow Advisor — Customer Support Flow

### 🔴 High Impact
**Sequential tool execution**
- Observed: Nodes "Get Account Details", "Get Order History", and "Get Open Tickets" are connected sequentially with no data dependencies between them
- Why it matters: Each tool averages ~1.5s. Running sequentially costs ~4.5s; running in parallel costs ~1.5s — a saving of ~3s per invocation
- Recommended action: Wrap all three nodes in a Parallel Node

### 🟡 Medium Impact
**Auto-mapped input field**
- Observed: Node "Create Ticket" has required field "customer_id" with no explicit mapping in input_map
- Why it matters: The flow engine will invoke an LLM to resolve this field at runtime, adding 500–3000ms per invocation
- Recommended action: Add an explicit mapping for "customer_id" under input_map.spec.maps

---
_Review scope: workflow JSON ✅ | agent YAML ❌ not provided_
```

---

## Quality Standards

### Completeness
- All 6 checks run against the provided artefact (or explicitly skipped with reason)
- All findings documented with evidence, impact, and recommended action
- Review scope footer present on every output

### Accuracy
- Findings reference actual field names and `display_name` values from the artefact
- Latency figures match platform-measured values (not estimates)
- No findings fabricated or inferred without evidence in the JSON

### Clarity
- High Impact findings presented first
- Each finding self-contained — reader can act on it without reading the rest
- Clean result explicitly stated when no issues are found

### Usefulness
- Recommendations are specific enough to act on immediately
- Impact figures help builders prioritise which issues to fix first
- Scope footer tells the builder what was and was not assessed
