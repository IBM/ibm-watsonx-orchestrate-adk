---
name: agent-instructions-evaluator
description: Evaluate an agent instructions or agent definition for achievability and produce a structured, evidence-backed report artifact with per-dimension scores, findings, deterministic signals, and high-impact recommendations.
tags:
  - watsonx-orchestrate
  - agent-evaluation
  - prompt-evaluation
  - prompt-quality
  - instructions-evaluation
  - agent-design
  - evaluation-harness
  - report-generation
---

# Agent Instructions Evaluator

## Overview

Evaluate agent instructions or agent definitions for operational achievability in production settings. This skill focuses on runtime reliability and runtime efficiency rather than writing quality, identifying issues from hidden state, conflicting rules, vague scope, brittle exact phrasing, underspecified tool behavior, instruction overload, and performance friction caused by excessive or contradictory runtime reasoning.

**Use this skill when you need:**
- A practical evaluation report focused on runtime reliability
- Evidence-backed prompt review with concrete recommendations
- A reusable report artifact that can be shared with reviewers
- Per-dimension scoring that preserves nuance rather than averaging away critical issues

## Core Principle

Score the artifact not by how much behavior it describes, but by how much behavior the agent can reliably execute. More rules do not automatically make a better prompt—more rules often lower achievability. An instruction set that is technically understandable but expensive to reconcile at runtime should still be considered lower-achievability, because slow, unstable, or tool-heavy execution reduces production reliability.

## Evaluation Workflow

<Steps>
<Step>
**Gather all relevant data**

Before beginning analysis, collect all available metadata and context. **The raw JSON files produced by the extraction scripts are a required deliverable — save them into the `eval/` folder alongside the report files. Every report in the set must reference them.**

> **Path note:** All `scripts/` paths below are relative to the skill directory (`skills/agent-instructions-evaluator/`). Run these commands from that directory, or prefix the path accordingly (e.g. `skills/agent-instructions-evaluator/scripts/extract_agent_info.py`).

1. **Extract agent metadata** (if evaluating a YAML file):
   ```bash
   # Preferred — single command; auto-scans the project tree for tool source files
   python scripts/extract_agent_info.py <agent.yaml> \
       --search-root /path/to/project \
       --output-dir eval/ --json

   # Alternative — explicit toolkit directory (faster on large trees)
   python scripts/extract_agent_info.py <agent.yaml> \
       --search-root /path/to/project \
       --tools-root /path/to/toolkit \
       --output-dir eval/ --json

   # Alternative — use pre-extracted tool JSONs from step 2 below
   python scripts/extract_agent_info.py <agent.yaml> \
       --search-root /path/to/project \
       --tools-dir eval/ \
       --output-dir eval/ --json
   ```

   **`--tools-root` / auto-scan behaviour:**
   - When `--tools-root` is supplied, the script recursively scans that directory for tool source files.
   - When neither `--tools-root` nor `--tools-dir` is supplied, the scan runs automatically against `--search-root` (or the agent YAML's directory if `--search-root` is also absent). This means in most cases a single command is sufficient.
   - `.py` files are included only when they contain at least one `@tool`, `@flow`, or `@<any>.tool()` decorated function (e.g. `@mcp.tool()` in MCP server source files) — all other Python files are silently skipped.
   - `.json` files are included only when `detect_json_tool_type()` identifies them as an agentic workflow (`spec.kind == "flow"`) or Langflow format — all other JSON is silently skipped.
   - When both `--tools-dir` and `--tools-root` are supplied, `--tools-dir` entries take priority; `--tools-root` fills gaps.

   This produces **`eval/agent_<name>_extracted.json`** — a full snapshot including:
   - `name`, `display_name`, `kind`, `llm`, `context_variables`, `guidelines_count`
   - `instructions_length`, `instructions_chars`, `instructions_est_tokens`
   - `skill_catalog_est_tokens`, `collaborator_routing_est_tokens`, `tool_list_est_tokens`, `tools_spec_est_tokens`
   - `resolved_tools` — each agent-level tool with `spec_chars`, `spec_est_tokens`, `type`, `file_path`, `resolved`
   - `resolved_collaborators` — each collaborator with `display_name`, `description`, `kind`, `llm`, `tools`, `skills`, `instructions_length`, `guidelines_count`, `routing_est_tokens`, `collocated`
   - `skills` — each skill fully resolved: `description`, `name_length`, `description_length`, `name_too_long`, `description_too_long`, `unmatched_placeholders`, `allowed_tools`, `resolved_allowed_tools` (with per-tool `spec_est_tokens`), `allowed_tools_spec_est_tokens`, `body_chars`, `body_est_tokens`, `catalog_est_tokens`, `tool_binding_shadows`, `scripts`, `references`, `skill_file`

   - Always pass `--output-dir eval/` so the JSON is saved alongside the report files.
   - Co-located collaborator YAML files (same directory as the agent) are found automatically; remote files require `--search-root`.
   - Tool: [`extract_agent_info.py`](scripts/extract_agent_info.py)

2. **Extract individual tool metadata** (optional — only needed when `--tools-root` auto-scan is insufficient, e.g. tools in a remote registry or a non-standard format):
   ```bash
   python scripts/extract_tool_info.py <tool.py|tool.json|tool.yaml> --output-dir eval/ --json
   ```
   Auto-detects file type:
   - **Python `.py`**: `@tool` decorator → regular Python tool; `@flow` decorator → Python flow tool
   - **JSON `.json`**: `spec.kind == "flow"` → WxO Agentic Workflow; `data.nodes` (list) → Langflow workflow
   - **YAML `.yaml/.yml`**: `kind: knowledge_base` → WxO Knowledge Base; `kind: mcp` → MCP Toolkit

   This produces **`eval/tool_<name>_extracted.json`** per tool. Pass the containing directory to `extract_agent_info.py` via `--tools-dir eval/` to enrich all tool entries.
   - Tool: [`extract_tool_info.py`](scripts/extract_tool_info.py)

   **Token estimation rules applied during extraction:**
   - All estimates use **character count ÷ 4** (≈4 chars/token).
   - For Python `@tool` / `@flow` functions: spec = function name + docstring + each parameter serialised as its **JSON Schema representation** (not the bare type string). `Literal["a","b"]` → `{"type":"string","enum":["a","b"]}`; `list[str]` → `{"type":"array","items":{"type":"string"}}`; unknown custom classes → `{"type":"object"}` (conservative fallback). **Return type is excluded** — output schema is not injected into the agent context.
   - For WxO Agentic Workflow JSON: spec = name + display_name + description + input_schema only. **Output schema is excluded.**
   - For tools that cannot be resolved (definition file not found): a **200-token fallback estimate** is used. This appears in the output as `~200 est. tokens (fallback — definition not found)`.

3. **Identify missing tool definitions**: Note which tools/collaborators are referenced but not available for inspection.

4. **Organize the data**: Create a complete picture of:
   - What the agent instructions say
   - What tools are actually available
   - What parameters those tools accept
   - What context variables exist
   - What guidelines constrain behavior
   - What skills are attached and what each skill brings (allowed-tools, scripts, references)
   - Which tools are retrieval/knowledge-base surfaces, their passage-count limits, and where they are referenced (agent instructions, collaborator, or skill body)

   **When reviewing tool metadata, flag any tool as a potential retrieval surface if:**
   - Its `kind` is `knowledge_base`, OR
   - Its name or description contains any of: `search`, `query`, `retrieve`, `lookup`, `knowledge`, `kb`, `rag`, `find`, `fetch`, `document`, `semantic`
   - For flagged tools: note any `top_k`, `max_results`, `limit`, or `num_passages` parameter and its default value. If none exists, record the passage count as **unbounded**.

**Only after gathering all data**, proceed to analysis. This ensures:
- Tool grounding assessment is based on actual tool signatures, not assumptions
- Execution feasibility is evaluated against real capabilities
- Recommendations are specific and actionable
</Step>

<Step>
**Understand the input**
Accept any of these input types:
- Raw system prompt
- Instruction block for an agent
- watsonx Orchestrate native agent YAML
- External agent definition
- Design document describing agent behavior
- Partial excerpt from a larger prompt or policy

If the input is partial, state that the evaluation scope is partial and score only what is visible.

#### Processing watsonx Orchestrate Agent YAML
When evaluating a watsonx Orchestrate native agent YAML file, extract and evaluate these key sections:

1. **Instructions field** (`instructions:`): This contains the primary agent prompt. Evaluate this as the main instruction content for all dimensions.

2. **Guidelines field** (`guidelines:`): These are structured rules that supplement the instructions. Count these as additional constraints and conditional logic. Each guideline typically adds:
   - 1 conditional branch (condition → action)
   - 1+ critical constraints if the action contains MUST/NEVER/ALWAYS language
   - Potential tool triggers if the action specifies calling a tool/collaborator

3. **Collaborators list** (`collaborators:`): Each entry names a subordinate agent the supervisor can delegate to. The script now resolves each name to its YAML file (co-located first, then `--search-root`) and extracts: `display_name`, `description`, `kind`, `llm`, `tools`, nested `collaborators`, `skills`, `instructions_length`, `guidelines_count`, and `collocated` flag.

   **Recursive traversal:** Collaborators are themselves agents and may have their own `collaborators:` lists. Resolve and analyze collaborators at **all depths** — not just the immediate children of the root agent. For each resolved collaborator, check its own `collaborators:` list and apply the same resolution, CO-1 through CO-7 analysis, and report generation recursively. Stop only when a collaborator has no further `collaborators:` entries, or when a YAML cannot be resolved (note it as unresolved). Use a visited-set (by agent `name` or file path) to detect and break cycles — if a collaborator's YAML has already been resolved at a higher level, record the back-edge as a **dependency loop** (CO-4 violation) and do not recurse into it again.

   For each resolved collaborator at every depth, apply the **Collaborator Health** checks (**CO-1 through CO-7**) described below — these are the exact parallel of the SK-1 through SK-7 skill checks, applied to the collaborator's agent YAML instead of a SKILL.md body.

   **CO-1 — Single Responsibility**: Does the collaborator agent cover exactly one domain or capability? Count the distinct tool categories and top-level behavioral sections in its `instructions:`. More than one primary workflow is a smell; three or more is a violation.

   **CO-2 — Distinct, Non-Overlapping Scope**: Do any two collaborators share coverage for the same user intent, topic, or trigger condition? Compare each collaborator's `description` field and `instructions:` scope statements against every other collaborator in the parent agent's `collaborators:` list. Overlapping descriptions force the supervisor to make an ambiguous routing decision — this is a systematic reliability failure, not an edge case. Flag every pair with detectable overlap, quote the overlapping text, and rate the overlap: *Exact*, *High*, *Moderate*, or *Low*.

   **CO-3 — Routing Clarity (Name + Description)**: Is the collaborator `name` specific enough to be meaningfully different from all other collaborator names? Is the `description` field clear, specific, and complete enough that the supervisor — without reading the instructions body — can decide whether to route to this collaborator for a given user turn? Check: does the description explicitly state what intents it covers AND what intents it does NOT cover (boundary conditions)?

   **CO-4 — No Cross-Collaborator Dependencies (including dependency loops)**: Does the collaborator's instructions assume that another collaborator has already run, set state, or returned a value? Look for references to "after X agent", "the result from the previous agent", or implicit state assumptions that could only come from a prior collaborator execution. Collaborators must be independently invocable.

   **Additionally, check for dependency loops across the full collaborator set.** A dependency loop exists when collaborator A depends on state from collaborator B, and collaborator B depends on state from collaborator A — or any longer chain. Use the same directed-graph / cycle-detection approach as SK-4.

   **Signals that indicate a dependency edge from collaborator A to collaborator B:**
   - Collaborator A's instructions reference a tool exclusively available in collaborator B's `tools:` list
   - Collaborator A's instructions reference state or outputs that can only be produced by collaborator B's execution path
   - Collaborator A's instructions contain phrases implying B must have already acted (e.g., "once the account is selected", "after authentication")
   - Collaborator A's `collaborators:` list nests collaborator B (creating a direct dispatch dependency)

   **CO-5 — Instruction Complexity Budget**: Apply the same complexity analysis used for agent instructions to each collaborator's `instructions:` and `guidelines:`. Collaborators are just agents with their own instruction surface — the same rules apply:
   - Count lines of instruction content (apply Rule E thresholds)
   - Count nested if/then branches (apply Rule C thresholds)
   - Count active operational rules per turn (apply Rule F budget)
   - Count MUST/NEVER/ALWAYS/EXACTLY constraints (apply Rule B)
   - Count implicit state variables (apply Rule A)
   Report each collaborator's complexity signals separately from agent-level counts.

   **CO-6 — Collaborator Correlation and Consolidation**: Are any two collaborators so closely related in domain or trigger conditions that they are likely to be dispatched in the same turn or in immediate succession? Assess each collaborator pair for:
   - **Adjacent trigger intents**: Intents that users commonly express together may span two collaborators, forcing multi-hop dispatch per turn.
   - **Cross-instruction tool references**: A collaborator's instructions that reference tools exclusively available in another collaborator's `tools:` create coupling that requires co-dispatch.

   **Note on shared tools:** Two collaborators sharing tools is common and expected — it is not itself a consolidation signal. Do not recommend merging collaborators solely because they share tools.

   **Consolidation recommendation rule**: Recommend merging two collaborators into one when:
   - They have CO-2 Moderate or High overlap AND their intents plausibly co-occur in a single user turn, OR
   - One collaborator's instructions explicitly require tools available only in another collaborator's context.

   **CO-7 — Collaborator Architecture Performance Surface**: Assess the aggregate runtime cost of the collaborator architecture as a whole (see Rule N thresholds):
   - **Collaborator count**: total number of collaborators (>5: Medium; >10: High)
   - **Per-collaborator instructions size**: lines per collaborator (>100: Medium; >150: High)
   - **Routing ambiguity**: average number of plausible collaborator candidates per typical user turn (>2: Medium; >4: High)
   - **Multi-collaborator turns**: estimated proportion of user intents that plausibly require ≥2 collaborator calls (>20%: Medium; >40%: High)
   - **Re-dispatch frequency**: evidence of multiple collaborator hops per turn in the supervisor's instructions (any confirmed: Medium)
   - **Nested collaborator depth**: any collaborator that itself has collaborators (depth > 1: Medium; depth > 2: High)
   - **Combined instruction cost**: estimated tokens across all collaborator instruction bodies that could be involved in one turn (>2,000: Medium; >4,000: High)
   Report each component with its measured value and risk rating, then produce an overall collaborator dispatch overhead rating (Low / Medium / High).

   **Collaborator depth notation:** When reporting multi-level collaborators, qualify each collaborator's identity with its depth and parent, e.g. `account_agent (depth 2, parent: supervisor_agent)`. Cross-collaborator checks (CO-2, CO-4, CO-6) are applied **within each depth level** — compare siblings only. Parent-to-child relationships are already captured by CO-4 (dispatch dependency), not CO-2 (sibling overlap).

   **Structural checks for each resolved collaborator:**
   - **`description`**: Does it give the supervisor enough routing signal (CO-3)? Vague descriptions cause misdirected dispatch.
   - **`tools:`**: The tool list available to the collaborator. Check whether every tool referenced in its instructions is present. Missing tools are execution gaps (feeds CO-1 and CO-5).
   - **`collaborators:`**: Nested collaborators. Each nested entry adds another dispatch hop and potential CO-4 dependency edge.
   - **`instructions_length` / `guidelines_count`**: Directly feeds CO-5 complexity budget.
   - **`collocated`**: Whether the YAML was found co-located with the parent agent or resolved via `--search-root`. Remote collaborators may not be available for inspection in all environments.

4. **Tools list** (`tools:`): Count the number of tools referenced. Add these to the tool-required behaviors count.

5. **Context variables** (`context_variables:`): Note which variables are available. Check if the instructions require tracking additional state beyond these variables.

6. **Skills list** (`skills:`): A list of skill names that the agent can `load_skill` into context at runtime. Each skill is a dynamic instruction module — the agent swaps the active skill's `SKILL.md` content into its context window when routing to that domain.

   **Skill directory structure** (resolved by `extract_agent_info.py`):
   ```
   <skill-name>/
   ├── SKILL.md           # frontmatter: name, description, allowed-tools
   ├── scripts/           # optional: Python scripts (.py) available to the skill at runtime
   │   └── *.py
   └── references/        # optional: reference files (any extension) loaded at runtime
       └── *
   ```

   For each skill, apply the following checks. These are **Skill Health** criteria — distinct from the five agent-level dimensions but equally important for production reliability.

   **SK-1 — Single Responsibility**: Does the skill do exactly one thing? A skill body that covers multiple unrelated intents, sub-topics, or tool categories is doing too much. Count the distinct tool calls or workflows described in the body. More than one primary workflow is a smell; three or more is a violation.

   **SK-2 — Distinct, Non-Overlapping Scope**: Do any two skills share coverage for the same user intent, topic, or trigger condition? Compare each skill's `description` frontmatter and body scope statements against every other skill in the agent's `skills:` list. Overlapping descriptions force the agent to make an ambiguous routing decision at every turn where both skills could plausibly apply — this is a systematic reliability failure, not an edge case. Flag every pair with detectable overlap, quote the overlapping text from both descriptions, and rate the overlap: *Exact* (same intent, same words), *High* (same intent, different words), *Moderate* (shared edge cases or boundary conditions), or *Low* (tangential but distinct).

   **SK-3 — Routing Clarity (Name + Description)**: Is the skill `name` specific enough to be meaningfully different from all other skill names? Is the `description` frontmatter clear, specific, and complete enough that the agent — without reading the body — can decide whether this skill applies to a given user turn? A description that requires the agent to already know the domain details to understand it is circular. A description that is vague enough to match multiple domains is ambiguous. Check: does the description explicitly state what intents it covers AND what intents it does NOT cover (boundary conditions)?

   **SK-3a — Frontmatter validation (hard limits that prevent the skill from loading):**
   - **Name length**: The `name` field must be ≤ 64 characters. A name exceeding 64 characters will prevent the skill from importing. Flag immediately as a hard failure — the skill will not be reachable at all.
   - **Description length**: The `description` field must be ≤ 1024 characters. Past this limit the skill will not load. Flag immediately as a hard failure.
   - **Unmatched `{{placeholder}}` tokens**: Any `{{identifier}}` in the description or body with no matching `param` entry quietly becomes a hole — the model reads a sentence with a gap in it. Scan both the description and the body for `{{...}}` patterns and verify each has a matching `param`. Flag unmatched placeholders as a hard failure.

   **SK-4 — Cross-Skill Dependencies, Mid-Body Handoffs, and Dependency Loops**: This check covers three distinct cases. Assess each independently.

   **Case 1 — Backward assumption (violation):** Does the skill body assume that another skill has already run, set state, or returned a value? Look for references like "after X skill", "the result from the previous skill", "the intent identified earlier", or implicit state assumptions that could only come from a prior skill's execution. Skills must be independently executable — a skill that requires a prior skill to have run cannot be reliably activated in all valid routing paths.

   **Case 2 — Mid-body `load_skill` (violation):** Does the skill body issue a `load_skill` call before its own work is complete, and then expect to resume its own steps after? When the new skill loads, the current skill's instructions are **gone** — there is no returning. Any steps written after a mid-body `load_skill` are unreachable. Detect this by checking whether the `load_skill` call appears before the skill's terminal step and whether subsequent steps depend on coming back to this body.

   **Case 3 — Terminal handoff (document, do not flag as violation):** A skill body may issue a `load_skill` call as its **last action**, after all of its own steps are complete. This is a valid one-way handoff — the skill has finished its work, and the next skill picks up from the conversation state. Document these handoffs neutrally in the report (note the target skill). If a chain of terminal handoffs exists (A → B → C → …), note the chain depth — multiple hops mean each skill's instructions are replaced in sequence, which is a "telephone game" risk worth flagging for the author to assess. Document; do not penalise.

   **Dependency loop check (violation):** Build a directed graph using **forward `load_skill` pointers**: draw an edge A → B if skill A's body contains a `load_skill` call to skill B (mid-body or terminal). Check this graph for cycles. A cycle means whichever skill loads second erases the one that loaded first — neither finishes. Any cycle is a violation regardless of where in the body the `load_skill` call appears.

   **How to detect loops:**
   1. For each skill, find every `load_skill` call in its body — note both mid-body and terminal calls.
   2. Draw a directed edge for each: skill A → skill B.
   3. Check the full graph for cycles of any length (A → B → A, or A → B → C → A, etc.).
   4. Any cycle is a **loop violation** — report it as a separate finding, naming all skills in the cycle.

   **Signals that indicate a dependency edge from skill A to skill B:**
   - Skill A's body contains an explicit `load_skill` call targeting skill B (mid-body: violation; terminal: document)
   - Skill A's body references state, context variables, or outputs that can only be set by skill B's execution path
   - Skill A's body contains phrases like "after selecting the product" or "once the account is identified" where the selection/identification is the job of another named skill
   - Skill A's body references a tool that is exclusively in skill B's `allowed-tools` (and not in A's own `allowed-tools` or the agent's top-level `tools:`)

   **SK-5 — Instruction Complexity Budget**: Apply the same complexity analysis used for agent instructions to each skill's `SKILL.md` body. Skills are just agent instructions scoped to a domain — the same rules apply:
   - Count lines of instruction content in the body (apply Rule E thresholds)
   - Count nested if/then branches (apply Rule C thresholds)
   - Count active operational rules per turn (apply Rule F budget)
   - Count MUST/NEVER/ALWAYS/EXACTLY constraints (apply Rule B for exact phrases)
   - Count implicit state variables (apply Rule A)
   A skill that individually exceeds any Rule C/E/F threshold is a complexity risk, regardless of how the agent-level instructions score. Report each skill's complexity signals separately.

   **SK-6 — Skill Correlation, Consolidation, and Tool-Shadowing**: Assess each skill pair for sequential-load coupling, and separately assess the agent's tool declarations for shadowing gaps.

   **Tool declaration model (check this first):** Every tool any skill uses must be declared in `agent tools:` — that is the authoritative registry. A skill's `allowed-tools` restricts which declared tools are visible in the skill's context. This produces three categories:
   - **Agent-only tools** (in `agent tools:`, not in any `allowed-tools`): callable at base level ✓
   - **Skill-filtered tools** (in `agent tools:` AND in one or more `allowed-tools`): callable only inside those skill contexts — **shadowed at agent base level** ✗
   - **Skill-only tools** (skill-filtered AND not referenced in agent `instructions:`/`guidelines:`): informational only — no execution gap because the agent never intended to call them at base level

   **Correlation checks (per skill pair):**
   - **Adjacent trigger intents**: Intents that users commonly express together in one message (e.g. "show my balance and last transactions") may span two skills, forcing sequential `load_skill` calls. Each call replaces the active skill body — the first skill's instructions are gone by the time the second loads.
   - **Cross-body `load_skill` references**: A skill body that instructs the agent to `load_skill` another skill before the first body's own work is complete creates an instruction-loss risk (see SK-4). This is a coupling signal, not just a performance signal.

   **Tool-shadowing execution gap (Trigger 3 — High severity):** Cross-reference every tool named in the agent's `instructions:` or `guidelines:` against `shadowed_resolved_tools`. If any match, the agent has written an instruction it cannot execute at base level — the tool is declared but unreachable outside a skill context. This is a **deterministic silent execution gap**. Flag every affected tool individually. Fix: either remove the tool from the relevant skill's `allowed-tools` (making it callable at base level), or move the agent-level instruction into the skill body where the tool is accessible.

   **Zero-tool base coverage (Trigger 3a — intentionality check):** Check whether `active_resolved_tools` is empty (all declared tools are skill-filtered). If so, the agent has no tools before any skill loads. **This is a valid and common design for a pure skill-routing agent** — it is not an error. Check whether the agent `instructions:` contain an explicit statement confirming that every user intent is handled through a skill. If yes: record as confirmed, no note needed. If no such statement exists: raise a lightweight intentionality note asking the author to confirm. Either way, **Trigger 3a does not lower any dimension score**.

   **Consolidation recommendation rule**: Recommend merging two skills into one when:
   - They have SK-2 Moderate or High overlap AND their intents plausibly co-occur in a single user turn, OR
   - One skill's body issues a `load_skill` call to the other mid-workflow (indicating inseparable sequential dependency).

   **SK-7 — Skill Architecture Performance Surface**: Assess the aggregate runtime cost of the skill architecture as a whole using these components (see Rule N in [`signal-rules.md`](signal-rules.md) for thresholds). Because only one skill body is in the prompt at a time, the cost is per-load, not per-turn-sum.
   - **Skill count**: total number of skills (>5: Medium; >10: High)
   - **Per-skill body size**: lines of instruction per skill body (>100: Medium; >150: High)
   - **Routing ambiguity**: average number of plausible skill candidates per typical user turn (>2: Medium; >4: High)
   - **Load transitions per turn**: estimated number of `load_skill` calls per turn for multi-step intents (>1 per turn: Medium; >2 per turn: High)
   - **Re-load frequency**: evidence that the agent reloads the same skill within a single turn (any confirmed: Medium)
   - **Per-load token cost**: estimated tokens for the largest skill body likely to be loaded in one turn (>2,000: Medium; >4,000: High)
   Report each component with its measured value and risk rating, then produce an overall skill load overhead rating (Low / Medium / High).

   **SK-8 — Redundant or conflicting platform content**: Does the skill body or the agent instructions contain content that the platform already injects, or describe fixed platform behavior the author cannot change? Both produce token waste and risk in-context contradictions when the author's description drifts from actual platform behavior.

   > **Canonical item list and triggers: see Rule J2 in [`signal-rules.md`](signal-rules.md).** Items are organized into three categories: A (platform-injected content), B (fixed behavior the author cannot override), and C (content misplaced in the wrong location). Apply each trigger as defined there.

   **Effect:** Category A — remove (already provided). Category B — remove (conflict risk). Category C — move to the right location or omit.

   **Structural checks for each skill:**
   - **`description`** (frontmatter): Does it give the agent enough signal to decide when to load this skill (SK-3)? Vague descriptions cause misdirected routing.
   - **`allowed-tools`**: The explicit tool allowlist for this skill context. Check whether every tool the SKILL.md body instructs the agent to call is present here. Tools referenced in SKILL.md body but absent from `allowed-tools` cannot be called — this is an execution gap (feeds SK-1 and SK-5).
   - **`scripts/`**: Python scripts uploaded to the skill and available for the agent to invoke as sandboxed compute — **no network access, no file-system access**. Check all of the following:
     - Does the body instruct the script to call an external API or read a file? Flag as an execution gap — that work must move to a tool.
     - Does the body reference the exact script path (e.g., `scripts/calculate_fee.py`)? If not, the invocation may fail silently.
     - Do the argument names in the body match the script's declared parameters exactly? Mismatches are silent failures.
     - Does the body reproduce the script's logic in prose (e.g., re-stating the fee formula in text)? Flag — the model may do the math itself instead of calling the script, producing inconsistent results.
   - **`references/`**: Reference files (lookup tables, policy docs, etc.) available to the skill at runtime. They are read on demand and stay in context until the skill changes. Check all of the following:
     - Is each reference pointer conditional (e.g., "read X if the customer is on a legacy plan")? A bare pointer with no condition either gets read every turn or never — flag as ambiguous.
     - Does the body ever instruct reading the same reference twice? Flag — it is already in context.
     - Does the body put lookup tables or policy detail inline instead of in a reference? Flag — inline detail inflates the body size permanently; the detail should live in the reference and be read on demand.
     - Does the body use the exact reference path? Vague pointer names can fail silently.
     - Is the workflow logic in the body and the detail/lookup tables in the references? If the split is reversed, correct it.
**Counting rules for YAML:**
- **Prompt length**: Count only the lines in the `instructions:` field (exclude YAML structure, metadata, and guidelines)
- **Critical constraints**: Count MUST/NEVER/ALWAYS/EXACTLY in both `instructions:` and `guidelines:` sections
- **Nested conditionals**: Count if/then branches in `instructions:` plus each guideline's condition→action pair
- **Tool-required behaviors**: Sum of collaborators + tools (e.g., 14 collaborators + 1 tool = 15 tool-required behaviors)
- **Exact phrases**: Count "Respond exactly:", "Say:", and similar requirements in `instructions:` and `guidelines:`
- **Collaborator routing behaviors**: Each collaborator adds at least 1 conditional routing decision (when to dispatch) plus the full instruction surface of that collaborator's own agent YAML
- **Per-collaborator complexity**: Count lines, nested branches, active rules, and implicit state for each collaborator's `instructions:` independently — report these separately from agent-level counts (CO-5)
- **Collaborator overlap pairs**: Count the number of collaborator description pairs with detectable scope overlap (CO-2)
- **Correlated collaborator pairs**: Count pairs where shared tools or adjacent intents make co-dispatch likely (CO-6)
- **Collaborator performance surface**: Compute the seven CO-7 components and their aggregate risk rating
- **Skill routing behaviors**: Each skill listed adds at least 1 conditional routing decision (when to `load_skill`) plus the full instruction surface of that skill's `SKILL.md` body
- **Per-skill complexity**: Count lines, nested branches, active rules, and implicit state for each skill's `SKILL.md` body independently — report these separately from agent-level counts (SK-5)
- **Skill overlap pairs**: Count the number of skill description pairs with detectable scope overlap (SK-2)
- **Correlated skill pairs**: Count pairs where adjacent intents make sequential loading likely, or where a mid-body `load_skill` creates inseparable coupling (SK-6 Triggers 1 and 2)
- **Tool-shadowing execution gaps**: For each tool named in agent `instructions:` or `guidelines:`, check whether it also appears in `shadowed_resolved_tools`. Each match is a SK-6 Trigger 3 violation (High severity — agent instruction it cannot execute at base level). Count each affected tool separately.
- **Zero-tool base coverage**: Check whether `active_resolved_tools` is empty — SK-6 Trigger 3a (intentionality check only; valid design pattern; raise a lightweight note if no explicit confirmation in agent instructions; no score impact either way)
- **Skill-only tools**: Count tools in `skill_only_tools` — informational only; not a violation (SK-6 Trigger 3b)
- **Skill performance surface**: Compute the six SK-7 components and their aggregate risk rating

**Important:** Use the utility scripts ([`extract_agent_info.py`](scripts/extract_agent_info.py), [`extract_tool_info.py`](scripts/extract_tool_info.py)) to extract tool, collaborator, and skill metadata before scoring the "Execution & Tool Grounding" dimension. Both scripts live under `scripts/` relative to this skill file — not the top-level workspace. `extract_agent_info.py` now resolves both collaborator agent YAMLs (co-located first, then `--search-root`) and skills (SKILL.md). Pass `--search-root` pointing at the project root when collaborator YAMLs or SKILL.md files are not co-located with the agent YAML. If collaborators, tools, or skills are referenced but their formal definitions cannot be extracted, note this as a limitation and proceed — recommend that the user provide definitions and re-run for a complete assessment.
</Step>

<Step>
**Extract evidence**
Use the gathered data to identify and count:
- Exact phrase requirements
- Nested conditional branches
- Implicit state requirements
- Critical constraints (MUST, NEVER, ALWAYS, EXACTLY, etc.)
- Exception clauses
- Subjective classifiers
- Tool-required behaviors
- Hard conflicts between rules
- **Knowledge base / retrieval surfaces** — for each tool identified as a retrieval surface in Step 1:
  - **Passage count limit**: stated `top_k`/`max_results`/`limit` value, or "unbounded" if none
  - **Call condition**: is the tool called unconditionally on every turn, on most turns, or conditionally? Quote the trigger phrase from the instructions.
  - **Number of KB calls per turn**: count how many times the tool (or different retrieval tools) appear in a single turn's workflow
  - **Location**: agent instructions, collaborator instructions, or skill body (note the skill name and its estimated load frequency from SK-7)
  - **Estimated payload**: stated passage count × ≥500 tokens (conservative lower bound; actual chunk size is a runtime variable not visible from static analysis — state this as an approximation and flag the exact value as unverifiable without runtime inspection), or flag as unknown if unbounded

For each resolved collaborator, additionally extract:
- **CO-1**: Number of distinct tool categories / top-level behavioral workflows in the collaborator's instructions
- **CO-2**: Any overlap with other collaborators — pairs, quoted evidence, overlap rating
- **CO-3**: Whether the `description` explicitly states covered intents AND boundary conditions (what it does NOT cover)
- **CO-4**: Any cross-collaborator state assumptions — explicit references to another collaborator's output or implicit state; **plus**: build the dependency graph across all collaborators and check for cycles — list any loop found with all collaborators in the cycle named
- **CO-5**: Per-collaborator Rule A/B/C/E/F signal counts (lines, branches, active rules, exact phrases, implicit state)
- **CO-6**: Correlated collaborator pairs — shared tools, adjacent intent co-occurrence, cross-instruction tool references; consolidation recommendation (yes/no with justification)
- **CO-7**: Collaborator architecture performance surface — all seven components with measured values and risk ratings; overall collaborator dispatch overhead rating

For each resolved skill, additionally extract:
- **SK-1**: Number of distinct tool calls / primary workflows in the skill body
- **SK-2**: Any overlap with other skills — pairs, quoted evidence, overlap rating
- **SK-3**: Whether the `description` explicitly states covered intents AND boundary conditions (what it does NOT cover)
- **SK-4**: Case 1 — backward state assumptions (explicit or implicit references to another skill's prior execution). Case 2 — mid-body `load_skill` calls (note position: before or at terminal step; flag if before). Case 3 — terminal `load_skill` handoffs (document neutrally, note chain depth if > 1 hop). **Plus**: build the forward-pointer graph across all skills and check for cycles — report any loop as a separate finding with all skills in the cycle named.
- **SK-5**: Per-skill Rule A/B/C/E/F signal counts (lines, branches, active rules, exact phrases, implicit state)
- **SK-6**: Correlated skill pairs (Triggers 1–2) — adjacent intent co-occurrence, cross-body `load_skill` references; **tool-shadowing execution gaps (Trigger 3 — High)** — for each tool named in agent `instructions:`/`guidelines:`, check `shadowed_resolved_tools` for a match (each match = agent cannot execute that instruction at base level); **zero-tool base coverage (Trigger 3a — intentionality check, no score impact)** — is `active_resolved_tools` empty? if yes, is skill-only operation confirmed in agent instructions?; **skill-only tools (Trigger 3b — informational)** — tools in `skill_only_tools` (filtered but never referenced in agent text); consolidation recommendation (yes/no with justification)
- **SK-7**: Skill architecture performance surface — all six components with measured values and risk ratings; overall skill-load overhead rating

Document the analysis mode in the report:
- **Enhanced Mode**: Used utility scripts to extract agent and tool metadata; collaborator YAMLs and SKILL.md bodies read and analyzed for Collaborator Health (CO-1 through CO-7) and Skill Health (SK-1 through SK-7)
- **Direct Analysis Mode**: Manual analysis only (no tool metadata available)
- **Partial Collaborator Mode**: Agent has a `collaborators:` list but some collaborator YAMLs could not be resolved — Collaborator Health assessment is limited to the name/description visible in the parent agent's instructions
- **Partial Skill Mode**: Agent has a `skills:` list but SKILL.md files could not be resolved — Skill Health assessment is limited to description frontmatter only
</Step>

<Step>
**Score five dimensions + Skill Health**
Evaluate the artifact across these dimensions using the scoring rubrics in [`dimension-definitions.md`](dimension-definitions.md):

1. **Task Understanding** (0-5): Can the agent understand its primary job?
2. **Scope & Applicability** (0-5): Does the agent know when the instruction applies?
3. **Execution & Tool Grounding** (0-5): Can the required behavior be executed with available tools?
4. **Instruction Followability** (0-5): Can an LLM realistically follow all constraints at once?
5. **State & Conflict Manageability** (0-5): Does the prompt require hidden state tracking or conflicting rules?

Apply the deterministic signal rules from [`signal-rules.md`](signal-rules.md) to bound your judgment.

**When collaborators are present, also produce a Collaborator Health assessment** for each resolved collaborator using the CO-1 through CO-7 criteria. Collaborator Health is reported per-collaborator with a Pass / Warn / Fail rating for each criterion — it does not produce a single numeric score but feeds directly into the five agent dimensions and the Runtime Performance Risk section:
- CO-1 violations raise complexity in Dimension 4 (Instruction Followability) — a collaborator doing too much inflates the effective dispatch surface
- CO-2 violations lower Dimension 2 (Scope & Applicability) — overlapping collaborators mean the supervisor cannot reliably determine which to call
- CO-3 failures lower Dimension 2 (Scope & Applicability) — unclear collaborator descriptions produce misdirected dispatch
- CO-4 violations lower Dimension 5 (State & Conflict Manageability) — cross-collaborator dependencies create hidden state coupling and can deadlock dispatch chains
- CO-5 failures lower Dimension 4 (Instruction Followability) and Dimension 3 (Execution & Tool Grounding) — a complex collaborator is itself unreliable, degrading end-to-end reliability even if the supervisor instructions are clean
- CO-6 triggers raise `collaborator_dispatch_overhead_risk` in the Runtime Performance Risk section — correlated collaborators that are co-dispatched per turn add measurable latency and instruction interference; paired with a consolidation recommendation when the trigger threshold is met
- CO-7 surface assessment populates the collaborator architecture performance surface table in Runtime Performance Risk — the aggregate overhead rating (Low/Medium/High) is a deterministic output, not a judgment call

**When skills are present, also produce a Skill Health assessment** for each skill using the SK-1 through SK-8 criteria. Skill Health is reported per-skill with a Pass / Warn / Fail rating for each criterion.

**Important: skill health findings are reported in the per-skill reports, not as caps on the agent's five dimension scores.** A single bad skill does not make the whole agent unachievable — it only affects the achievability of that skill's own domain. The agent report shows a **Skill Health Summary table** (pass/warn/fail per SK criterion per skill) as context, but the agent's five dimension scores reflect only the agent's own instructions, guidelines, tools, and collaborators.

**The one exception** is where a skill defect directly affects the agent's routing or execution behavior (SK-2 overlap, SK-3/SK-3a description failures, SK-6 Trigger 3) — these affect the agent's Dimension 2 (Scope & Applicability) and Dimension 3 (Execution & Tool Grounding):
- SK-2 Exact or High overlap findings: lower agent Dimension 2 — the agent cannot reliably determine which skill to load
- SK-3a hard-limit failures (name too long, description too long, unmatched placeholders): lower agent Dimension 3 — the skill is unreachable
- SK-6 Trigger 3 (agent `instructions:`/`guidelines:` references a skill-filtered tool): lower agent Dimension 3 — the agent has written an instruction it cannot execute at base level (deterministic silent gap — **High** severity)
- SK-6 Trigger 3a (zero `active_resolved_tools`): **intentionality note only — does not lower any dimension score**; valid design for a pure skill-routing agent; raise a lightweight note if unconfirmed

All other SK findings (SK-1, SK-4, SK-5, SK-7, SK-8) stay in the per-skill report only:
- SK-1 violations are noted in the skill's own report; they do not cap agent Dimension 4
- SK-4 violations are noted in the skill's own report; they do not cap agent Dimension 5
- SK-5 failures are noted in the skill's own report; they do not cap agent Dimensions 3 or 4
- SK-7 surface assessment populates the skill performance surface table in Runtime Performance Risk — the aggregate overhead rating (Low/Medium/High) is a deterministic output added to the agent report's performance section, not to its five dimension scores
- SK-8 (platform-duplicated content) is reported per skill and at agent level; it surfaces via Rule O (token optimization), not as a dimension cap
</Step>

<Step>
**Generate findings**
For each major issue identified, create a finding with:
- **Evidence**: Direct quotes from the input
- **Why it matters**: Operational impact explanation
- **Deterministic or judgment-based**: Classification of the finding
- **Score impact**: Which dimensions are affected and how
- **Recommended change**: Specific, actionable fix

</Step>

<Step>
**Produce the report set**

Generate one report per evaluated artifact — the agent instructions plus one report for each resolved skill — and a lightweight index file. Each report is independent and can be written to disk as soon as its analysis is complete; do not wait for all reports to finish before saving any.

**Token optimization side report (`token_optimization_report.md`):** Always produced as part of every evaluation. Covers both optimization surfaces: agent instructions (every turn) and skill bodies (per load). Runs the full Rule O checklist; reports each pattern with a severity (High / Medium / Low / None found). If no issues are found, records the current per-turn token budget as a verified baseline.

**Performance optimization side report (`performance_optimization_report.md`):** Always produced. Targets execution call-graph depth: unconditional tool calls, sequential tool chains, `next_action` multi-hop dispatch, deep skill/collaborator stacks, guidelines overhead, correlated tool sets. For every identified sequential chain, recommends the appropriate offload mechanism: **`nextTool` chaining** (`_meta.nextTool`) if ≤5 steps, single Python MCP server, branching (if any) is stable and acceptable to hardcode in the tool, user interaction is simple Q&A at most, and no transaction audit is required; **Agentic Workflow** (`@flow` / WxO Agentic Workflow JSON) if branch logic may evolve, multi-step user confirmation needed, cross-server tools, >5 steps, or transaction audit/observability required. Both mechanisms eliminate LLM reasoning between steps, reducing token cost and inference passes simultaneously. Runs the full Rule P checklist with severity per pattern. If no issues are found, records the current call-graph baseline.

**Reliability optimization side report (`reliability_optimization_report.md`):** Always produced. Synthesises findings from the main agent and skill reports into a prioritised, implementation-ready rewrite plan grouped by failure class (implicit state, exact-phrase, scope/routing, conflicting rules, tool underspecification, skill body). Every REL-N item traces back to evidence already in the main reports — no new findings. Runs the full Rule Q checklist with severity per pattern. If no issues are found, records a stability baseline.

**Report set layout:**

```
instructions_eval/
├── index.md                                         ← manifest listing all reports and their overall verdicts
├── rules-summary.md                                 ← copy of evaluation rules reference (copy from skill directory)
├── agent_<name>_extracted.json                      ← raw extraction data from extract_agent_info.py  ← REQUIRED
├── tool_<name>_extracted.json                       ← raw extraction data per tool (when produced by extract_tool_info.py)
├── token_optimization_report.md                     ← token consumption optimization (Rule O — always produced)
├── performance_optimization_report.md               ← runtime performance optimization (Rule P — always produced)
├── reliability_optimization_report.md               ← reliability optimization (Rule Q — always produced)
├── agent_<name>_report.md                           ← agent-level report (main instructions only)
├── agent_<name>_report_harness.json                 ← agent-level JSON harness
├── collaborator_<collab-name>_report.md             ← one per resolved collaborator at any depth
├── collaborator_<collab-name>_report_harness.json
├── ...                                              ← repeat for every collaborator across all depth levels
├── skill_<skill-name>_report.md                     ← one per resolved skill (attached to agent or any collaborator)
├── skill_<skill-name>_report_harness.json
└── ...
```

All collaborator and skill reports live flat in the same `eval/` directory regardless of depth. Depth and parent context are encoded inside each report's header metadata, not in the file path.

The `agent_<name>_extracted.json` file is the authoritative source for all token estimates, tool spec data, and skill resolution metadata used across every report. It is produced by `extract_agent_info.py --output-dir eval/` and **must be present in every complete report set**. The `index.md` must link to it in the Reference Documents section.

**Filename conventions:**
- Agent report: `agent_<name>_report.md` / `agent_<name>_report_harness.json`
  - `<name>` = the agent's `name` field (snake_case, no spaces)
- Skill report: `skill_<skill-name>_report.md` / `skill_<skill-name>_report_harness.json`
  - `<skill-name>` = the skill's `name` frontmatter field (snake_case, no spaces)
- Index: `index.md`
- Default output directory: `eval/` relative to the agent YAML's directory. Create it if it does not exist.

**What goes in each report:**

| Content | Agent report | Collaborator report | Skill report |
|---|---|---|---|
| Agent-level instructions analysis (all 5 dimensions) | ✓ | — | — |
| Agent-level Runtime Performance Risk | ✓ | — | — |
| Collaborator Health Assessment table (direct children, CO-2/CO-6/CO-7) | ✓ | ✓ (if has sub-collaborators) | — |
| Collaborator consolidation recommendations (CO-6) | ✓ | ✓ (if has sub-collaborators) | — |
| Collaborator architecture performance surface (CO-7) | ✓ | ✓ (if has sub-collaborators) | — |
| Skill Health Assessment table (all skills, cross-skill SK-2/SK-6/SK-7) | ✓ | ✓ (if has skills) | — |
| Skill consolidation recommendations (SK-6) | ✓ | ✓ (if has skills) | — |
| Skill architecture performance surface (SK-7) | ✓ | ✓ (if has skills) | — |
| Collaborator instructions analysis (5 dimensions applied to collaborator body) | — | ✓ | — |
| CO-1, CO-3, CO-4, CO-5 deep analysis for this collaborator | — | ✓ | — |
| Runtime Performance Risk for this collaborator body | — | ✓ | — |
| Depth + parent metadata header (`Depth: N \| Parent: <name>`) | — | ✓ | — |
| Back-reference to parent report (agent or collaborator) | — | ✓ | ✓ |
| Forward-references to own sub-collaborator and skill reports | ✓ | ✓ (if has sub-collaborators or skills) | — |
| Skill body analysis (5 dimensions applied to skill body) | — | — | ✓ |
| SK-1, SK-3, SK-4, SK-5 deep analysis for this skill | — | — | ✓ |
| Runtime Performance Risk for this skill body | — | — | ✓ |

**Filename conventions (extended):**
- Collaborator report: `collaborator_<name>_report.md` / `collaborator_<name>_report_harness.json`
  - `<name>` = the collaborator's `name` field from its agent YAML (snake_case, no spaces)

**Evaluation order and save-as-you-go:**

> ⚠️ **Three mandatory side reports** — `token_optimization_report.md`, `performance_optimization_report.md`, and `reliability_optimization_report.md` — must ALL be written before the index. Set up your todo list to track all three explicitly and do not mark any of them complete until the file exists on disk. Missing any one of them is a hard omission failure.

1. Extract all metadata — run `extract_agent_info.py` with `--search-root` and `--output-dir eval/` so `agent_<name>_extracted.json` is saved before analysis begins. The script auto-scans for tool source files; use `--tools-root` to narrow the scan or `--tools-dir eval/` to use pre-extracted tool JSONs. These files are the grounding source for all tool and token claims in every report. Confirm `agent_<name>_extracted.json` exists in the `eval/` directory before proceeding.
2. Copy `rules-summary.md` from the skill directory into the output `eval/` directory — do this once, before writing any reports
3. Evaluate and save the **agent report** first — it scores the main instructions and sets the cross-collaborator and cross-skill context
4. Evaluate and save **collaborator reports** using a **breadth-first, batch-of-2 traversal** across all collaborator depths:
   - Start at depth 1 (direct children of the root agent); process in batches of at most 2
   - After all depth-1 collaborators are written, descend to depth 2 (children of depth-1 collaborators that have their own `collaborators:` lists); continue batches of at most 2
   - Continue until all reachable collaborators at every depth have a report
   - **Visited-set rule**: if a collaborator YAML (by `name` or file path) has already been resolved at any earlier depth, do not process it again — record the back-edge as a dependency loop in the nearest parent's collaborator report and skip
   - **Filename convention for sub-collaborators**: use `collaborator_<name>_report.md` regardless of depth; depth and parent are recorded inside the report's header metadata
5. Evaluate and save **skill reports** in **batches of at most 2 at a time** — same batching rule as collaborators; skills attached to any collaborator at any depth are included
6. Evaluate and save the **token optimization side report** after all collaborator and skill reports are complete — always; runs Rule O checklist
7. Evaluate and save the **performance optimization side report** after the token report — always; runs Rule P checklist; cross-references OPT-N items for dual-benefit opportunities
8. Evaluate and save the **reliability optimization side report** after the performance report — always; runs Rule Q checklist; synthesises findings from all main reports and cross-references OPT-N and PERF-N items
9. **Gate check before writing the index:** confirm all three side reports (`token_optimization_report.md`, `performance_optimization_report.md`, `reliability_optimization_report.md`) exist in the output directory. If any is missing, write it now before proceeding.
10. Write the **index file** last, after all reports are complete — include links to all three side reports in the Reference Documents section

**When collaborator YAMLs cannot be resolved:** produce the agent report with a "Partial Collaborator Mode" note; omit collaborator reports for unresolved collaborators; list them in the index as `unresolved`. Still produce all three side reports — note partial mode as a limitation on collaborator-body coverage.

**When SKILL.md files cannot be resolved:** produce the agent report with a "Partial Skill Mode" note; omit skill reports for unresolved skills; list them in the index as `unresolved`. Produce all three side reports — note partial mode as a limitation on skill-body coverage.

**When there are no collaborators and no skills:** produce all reports including all three side reports. Reports will note the reduced surface (agent instructions only) and may be brief if no issues are found.
</Step>
</Steps>

## Key Evaluation Rules

**Be evidence-based:**
- Quote or paraphrase concrete lines from the input, including the line number where available
- **Non-English quotes: ALWAYS follow every non-English quote with a `[Translation]: ...` line in English. This is mandatory — do not omit it, do not paraphrase it away, and do not assume the reviewer reads the source language. Every finding Evidence block that contains a non-English quote must have a corresponding translation on the very next line.**
- Do not make claims without pointing to supporting text
- Distinguish between deterministic signals and judgment-based conclusions

**Be operational, not academic:**
- Focus on runtime reliability, not writing elegance
- Evaluate what is written, not what the author probably meant
- If something is missing, score the missing clarity as risk

**Prefer deterministic recommendations:**
- Recommend explicit state objects over implicit memory
- Recommend explicit tool triggers over vague instructions
- Recommend explicit scope boundaries over subjective judgment
- Recommend rule prioritization when conflicts exist
- **Do not recommend time-based solutions** (wait, delay, retry later, follow up after X time) unless the prompt explicitly defines a scheduler, durable workflow, callback mechanism, or persisted state infrastructure to support temporal operations

**Do not overpraise:**
- If the prompt is long, exception-heavy, or stateful, say so directly
- If any dimension scores 0-1, treat that area as not reliable as written
- If two or more dimensions are 2 or below, recommend redesign

**Prioritize high-impact changes:**
- Put the highest-leverage fixes first
- Identify specific rewrite targets (exact sentences or rule bundles)
- Focus on changes that improve multiple dimensions

## Supporting Files

Refer to these files for detailed guidance:
- [`dimension-definitions.md`](dimension-definitions.md): Complete scoring rubrics for all five dimensions
- [`signal-rules.md`](signal-rules.md): Deterministic rules to reduce subjectivity (Rules A-N)
- [`report-template.md`](report-template.md): Required report structure and section order
- [`rules-summary.md`](rules-summary.md): Standalone rules reference document — copy into every report set so reviewers can interpret scores without accessing the skill directory

## Output Requirements

**Every evaluation must produce:**

*Agent report* (`agent_<name>_report.md` + `agent_<name>_report_harness.json`):
1. Full 5-dimension analysis of the agent's main `instructions:` and `guidelines:`
2. Per-dimension scores with confidence levels
3. Deterministic signal summary with counts
4. Runtime Performance Risk (agent-level)
5. At least 3-5 findings with evidence and recommendations
6. Key risks and high-impact changes
7. **Collaborator Health table** (when collaborators are present): one row per collaborator, CO-1 through CO-7 ratings with evidence notes
8. Cross-collaborator overlap summary (CO-2), consolidation recommendations (CO-6), collaborator architecture performance surface (CO-7)
9. **Skill Health table** (when skills are present): one row per skill, SK-1 through SK-7 ratings with evidence notes
10. Cross-skill overlap summary (SK-2), consolidation recommendations (SK-6), skill architecture performance surface (SK-7)
11. Forward-links to each collaborator report at all depths: `See collaborator report: [collaborator_<name>_report.md](collaborator_<name>_report.md)` — include depth and parent annotation for sub-collaborators, e.g. `(depth 2, parent: supervisor_agent)`
12. Forward-links to each skill report: `See skill report: [skill-<name>_report.md](skill-<name>_report.md)`

*Per-collaborator report* (`collaborator_<name>_report.md` + harness JSON), one per resolved collaborator **at any depth**:
1. Full 5-dimension analysis of the collaborator's `instructions:` and `guidelines:` (treated as the instruction content)
2. CO-1, CO-3, CO-4, CO-5 deep analysis sections
3. **If this collaborator itself has sub-collaborators**: include a Collaborator Health table (CO-1 through CO-7) for its own direct children, plus forward-links to their reports — mirror the same structure as the root agent report
4. Per-dimension scores with confidence levels
5. Deterministic signal summary for this collaborator
6. Runtime Performance Risk for this collaborator
7. At least 2-4 findings specific to this collaborator
8. Key risks and high-impact changes for this collaborator
9. Depth and parent metadata in the report header: `Depth: N | Parent agent: <name>` (root agent = depth 0; direct children = depth 1; etc.)
10. Back-link to parent report (agent or collaborator): `Part of agent evaluation: [<parent>_report.md](<parent>_report.md)`

*Per-skill report* (`skill_<skill-name>_report.md` + harness JSON), one per resolved skill:
1. Full 5-dimension analysis of the skill's `SKILL.md` body (treated as the instruction content)
2. SK-1, SK-3, SK-4, SK-5 deep analysis sections
3. Per-dimension scores with confidence levels
4. Deterministic signal summary for this skill body
5. Runtime Performance Risk for this skill body
6. At least 2-4 findings specific to this skill
7. Key risks and high-impact changes for this skill
8. Back-link to agent report: `Part of agent evaluation: [agent-<name>_report.md](agent-<name>_report.md)`

*Token optimization report* (`token_optimization_report.md`) — always produced:
1. Current per-turn token budget table: component, lines, estimated tokens, loaded every turn?
2. Optimization inventory: one OPT-N entry per identified opportunity, with current cost, removable lines as a **% of current component size**, root cause, recommendation, and projected saving expressed as `~X lines (~Y% of current size) → ~Z tokens saved per [turn type]`
3. Post-optimization token budget estimates (before/after table per turn type)
4. Implementation priority table (effort × token impact × reliability benefit)
5. Per-skill token footprint reference (current lines, current tokens, target after optimizations)
6. Anti-pattern section: patterns that produced the identified overhead, to guide future prompt authors
7. Back-reference to the agent report: `Side report to: [agent_<name>_report.md]`

*Performance optimization report* (`performance_optimization_report.md`) — always produced:
1. Current execution profile table: turn types, inference hops, tool-call RTTs, skill loads
2. Optimization inventory: one PERF-N entry per identified opportunity, with current cost, root cause, mechanism, and estimated impact
3. Tool composition candidates table: chains that could be collapsed into deterministic server-side pipelines — specifies mechanism (`nextTool` chaining vs. Agentic Workflow vs. pre-invoke plugin) per chain based on step count, branch structure, and server scope
4. Post-optimization call-graph depth estimates (before/after table per turn type)
5. Implementation priority table (effort × latency impact × Rule O dual benefit)
6. Anti-pattern section: patterns that produced identified overhead
7. Cross-references to Rule O items where dual benefit exists
8. Back-reference to the agent report: `Side report to: [agent_<name>_report.md]`

*Reliability optimization report* (`reliability_optimization_report.md`) — always produced:
1. Reliability checklist summary table: all 18 patterns, severity per pattern, source reference
2. Reliability optimization inventory: one REL-N entry per identified item (ordered Critical → High → Medium → Low), with failure mode, evidence, root cause, recommendation, reliability impact, rule cross-reference, and cross-report reference (OPT-N / PERF-N)
3. Implementation roadmap: Phase 1 (Critical + High), Phase 2 (Medium), Phase 3 (Low)
4. Anti-pattern section: patterns that produced identified failure modes
5. Back-reference and cross-references: `Side report to: [agent_<name>_report.md]`

*Index file* (`index.md`) + `rules-summary.md` (copied from skill directory):
1. Table listing every report, its artifact type, and its overall verdict/band
2. Agent-level scorecard summary (one row per dimension)
3. Collaborator Health summary table (collapsed CO-1–CO-7 ratings per collaborator, **all depths**) — group rows by depth level; include a "Depth" and "Parent" column
4. List of any unresolved collaborators (YAML not found) at any depth
5. Skill Health summary table (collapsed SK-1–SK-7 ratings per skill)
6. List of any unresolved skills (SKILL.md not found)
7. Links to all three side reports in Reference Documents, each with a one-line summary (issues found or baseline recorded)
8. `rules-summary.md` present in the same `eval/` directory (copied, not regenerated)

**The markdown report must be:**
- Specific and evidence-backed
- Structured and complete
- Practical for prompt redesign
- Suitable for sharing with prompt engineers, agent builders, or reviewers
- Directly saveable as a markdown file without rewriting

**The JSON harness file must be:**
- Valid JSON with complete structured extraction object
- Machine-readable for automated harness integration
- Include all signals, incidents, dimension scores, and findings
- Saved as a separate `.json` file alongside the markdown report
