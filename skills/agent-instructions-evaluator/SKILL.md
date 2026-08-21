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

Before beginning analysis, collect all available metadata and context.

> **Path note:** All `scripts/` paths below are relative to the skill directory (`skills/agent-instructions-evaluator/`). Run these commands from that directory, or prefix the path accordingly (e.g. `skills/agent-instructions-evaluator/scripts/extract_agent_info.py`).

1. **Extract agent metadata** (if evaluating a YAML file):
   ```bash
   python scripts/extract_agent_info.py <agent.yaml> --json
   # If SKILL.md files live outside the agent's directory, point at the project root:
   python scripts/extract_agent_info.py <agent.yaml> --search-root /path/to/project --json
   ```
   This provides: name, display_name, kind, llm, collaborators, tools, context variables, instructions length, guidelines count, and the full **skills list** with each skill resolved.
   - Tool: [`extract_agent_info.py`](scripts/extract_agent_info.py)

2. **Extract tool metadata** for each referenced tool or agent collaborator:
   ```bash
   python scripts/extract_tool_info.py <tool.py|tool.json|tool.yaml> --json
   ```
   Auto-detects file type:
   - **Python `.py`**: `@tool` decorator → regular Python tool; `@flow` decorator → Python flow tool
   - **JSON `.json`**: `spec.kind == "flow"` → WxO Agentic Workflow; `data.nodes` (list) → Langflow workflow
   - **YAML `.yaml/.yml`**: `kind: knowledge_base` → WxO Knowledge Base; `kind: mcp` → MCP Toolkit

   This provides: tool signatures, parameters, return types, descriptions
   - Tool: [`extract_tool_info.py`](scripts/extract_tool_info.py)

3. **Identify missing tool definitions**: Note which tools/collaborators are referenced but not available for inspection

4. **Organize the data**: Create a complete picture of:
   - What the agent instructions say
   - What tools are actually available
   - What parameters those tools accept
   - What context variables exist
   - What guidelines constrain behavior
   - What skills are attached and what each skill brings (allowed-tools, scripts, references)

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

3. **Collaborators list** (`collaborators:`): Count the number of collaborators referenced. Each collaborator represents a tool-required behavior that needs trigger conditions, parameter specifications, and result handling.

4. **Tools list** (`tools:`): Count the number of tools referenced. Add these to the tool-required behaviors count.

5. **Context variables** (`context_variables:`): Note which variables are available. Check if the instructions require tracking additional state beyond these variables.

6. **Skills list** (`skills:`): A list of skill names that the agent can `load_skill` into context at runtime. Each skill is a dynamic instruction module — the agent swaps the active skill's `SKILL.md` content into its context window when routing to that domain.

   **Skill directory structure** (resolved by `extract_agent_info.py`):
   ```
   <skill-name>/
   ├── SKILL.md           # frontmatter: name, description, allowed-tools
   ├── WXO.yaml           # optional: server-side skill config
   ├── scripts/           # optional: Python scripts (.py) available to the skill at runtime
   │   └── *.py
   └── references/        # optional: reference files (any extension) loaded at runtime
       └── *
   ```

   For each skill, apply the following checks. These are **Skill Health** criteria — distinct from the five agent-level dimensions but equally important for production reliability.

   **SK-1 — Single Responsibility**: Does the skill do exactly one thing? A skill body that covers multiple unrelated intents, sub-topics, or tool categories is doing too much. Count the distinct tool calls or workflows described in the body. More than one primary workflow is a smell; three or more is a violation.

   **SK-2 — Distinct, Non-Overlapping Scope**: Do any two skills share coverage for the same user intent, topic, or trigger condition? Compare each skill's `description` frontmatter and body scope statements against every other skill in the agent's `skills:` list. Overlapping descriptions force the agent to make an ambiguous routing decision at every turn where both skills could plausibly apply — this is a systematic reliability failure, not an edge case. Flag every pair with detectable overlap, quote the overlapping text from both descriptions, and rate the overlap: *Exact* (same intent, same words), *High* (same intent, different words), *Moderate* (shared edge cases or boundary conditions), or *Low* (tangential but distinct).

   **SK-3 — Routing Clarity (Name + Description)**: Is the skill `name` specific enough to be meaningfully different from all other skill names? Is the `description` frontmatter clear, specific, and complete enough that the agent — without reading the body — can decide whether this skill applies to a given user turn? A description that requires the agent to already know the domain details to understand it is circular. A description that is vague enough to match multiple domains is ambiguous. Check: does the description explicitly state what intents it covers AND what intents it does NOT cover (boundary conditions)?

   **SK-4 — No Cross-Skill Dependencies (including dependency loops)**: Does the skill body assume that another skill has already run, set state, or returned a value? Look for references to "after X skill", "the result from the previous skill", "the intent identified earlier", or implicit assumptions about state that could only come from a previous skill execution. Skills must be independently executable — a skill that requires a prior skill to have run cannot be reliably activated in all valid routing paths.

   **Additionally, check for dependency loops across the full skill set.** A dependency loop exists when skill A depends on state from skill B, and skill B depends on state from skill A — or any longer chain (A → B → C → A). Loops make it impossible to determine which skill can legitimately be loaded first, creating a deadlock in routing logic that no amount of agent reasoning can resolve.

   **How to detect loops:**
   1. Build a directed dependency graph: for each skill, draw an edge to every other skill whose prior execution it assumes (explicitly or implicitly).
   2. Check for cycles in that graph. A cycle of length 2 (A ↔ B) is the most common; longer cycles (A → B → C → A) are possible in larger skill sets.
   3. Any cycle, regardless of length, is a **loop violation** — report it as a separate finding.

   **Signals that indicate a dependency edge from skill A to skill B:**
   - Skill A's body references a tool that is exclusively in skill B's `allowed-tools` (and not in A's own `allowed-tools` or the agent's top-level `tools:`)
   - Skill A's body references state, context variables, or outputs that can only be set by skill B's execution path
   - Skill A's body contains phrases like "after selecting the product" or "once the account is identified" where the selection/identification is the job of another named skill
   - Skill A's body instructs a `load_skill` call to skill B as a prerequisite before proceeding

   **SK-5 — Instruction Complexity Budget**: Apply the same complexity analysis used for agent instructions to each skill's `SKILL.md` body. Skills are just agent instructions scoped to a domain — the same rules apply:
   - Count lines of instruction content in the body (apply Rule E thresholds)
   - Count nested if/then branches (apply Rule C thresholds)
   - Count active operational rules per turn (apply Rule F budget)
   - Count MUST/NEVER/ALWAYS/EXACTLY constraints (apply Rule B for exact phrases)
   - Count implicit state variables (apply Rule A)
   A skill that individually exceeds any Rule C/E/F threshold is a complexity risk, regardless of how the agent-level instructions score. Report each skill's complexity signals separately.

   **SK-6 — Skill Correlation and Consolidation**: Are any two skills so closely related that they are likely to be loaded in the same turn or in immediate succession? Assess each skill pair for:
   - **Shared `allowed-tools`**: Skills that share ≥1 tool can both be candidates for the same user turn. Skills that share ≥2 tools are likely co-domain and should be evaluated for consolidation.
   - **Adjacent trigger intents**: Intents that users commonly express together in one message (e.g. "show my balance and last transactions") may span two skills, forcing a multi-skill load per turn.
   - **Cross-body tool references**: A skill body that instructs the agent to call a tool listed in another skill's `allowed-tools` creates a digression-based coupling — both instruction bodies will be in-context simultaneously.

   **Consolidation recommendation rule**: Recommend merging two skills into one when any of the following hold:
   - They share ≥2 tools in `allowed-tools`, OR
   - They have SK-2 Moderate or High overlap AND their intents plausibly co-occur in a single user turn, OR
   - One skill's body explicitly triggers a tool owned by the other skill.

   **SK-7 — Skill Architecture Performance Surface**: Assess the aggregate runtime cost of the skill architecture as a whole using these components (see Rule N in [`signal-rules.md`](signal-rules.md) for thresholds):
   - **Skill count**: total number of skills (>5: Medium; >10: High)
   - **Per-skill body size**: lines of instruction per skill body (>100: Medium; >150: High)
   - **Routing ambiguity**: average number of plausible skill candidates per typical user turn (>2: Medium; >4: High)
   - **Multi-skill turns**: estimated proportion of user intents that plausibly span ≥2 skills (>20%: Medium; >40%: High)
   - **Re-load frequency**: evidence of multiple `load_skill` calls per turn in the agent's instructions (any confirmed: Medium)
   - **Combined token cost**: estimated tokens across all skill bodies that could plausibly be loaded in one turn (>2,000: Medium; >4,000: High)
   Report each component with its measured value and risk rating, then produce an overall skill load overhead rating (Low / Medium / High).

   **Structural checks for each skill:**
   - **`description`** (frontmatter): Does it give the agent enough signal to decide when to load this skill (SK-3)? Vague descriptions cause misdirected routing.
   - **`allowed-tools`**: The explicit tool allowlist for this skill context. Check whether every tool the SKILL.md body instructs the agent to call is present here. Tools referenced in SKILL.md body but absent from `allowed-tools` cannot be called — this is an execution gap (feeds SK-1 and SK-5).
   - **`scripts/`**: Python scripts uploaded to the skill and available for the agent to invoke as tools within that skill context. Each `.py` file exposes callable functionality — treat these like tools when assessing execution feasibility (SK-5).
   - **`references/`**: Reference files (lookup tables, policy docs, etc.) available to the skill at runtime. Their presence may explain otherwise-invisible data sources referenced in SKILL.md body.
   - **`WXO.yaml`**: Server-side skill configuration. Note its presence but treat its contents as infrastructure-level.

**Counting rules for YAML:**
- **Prompt length**: Count only the lines in the `instructions:` field (exclude YAML structure, metadata, and guidelines)
- **Critical constraints**: Count MUST/NEVER/ALWAYS/EXACTLY in both `instructions:` and `guidelines:` sections
- **Nested conditionals**: Count if/then branches in `instructions:` plus each guideline's condition→action pair
- **Tool-required behaviors**: Sum of collaborators + tools (e.g., 12 collaborators + 1 tool = 13 tool-required behaviors)
- **Exact phrases**: Count "Respond exactly:", "Say:", and similar requirements in `instructions:` and `guidelines:`
- **Skill routing behaviors**: Each skill listed adds at least 1 conditional routing decision (when to `load_skill`) plus the full instruction surface of that skill's `SKILL.md` body
- **Per-skill complexity**: Count lines, nested branches, active rules, and implicit state for each skill's `SKILL.md` body independently — report these separately from agent-level counts (SK-5)
- **Skill overlap pairs**: Count the number of skill description pairs with detectable scope overlap (SK-2)
- **Correlated skill pairs**: Count pairs where shared `allowed-tools` or adjacent intents make co-loading likely (SK-6)
- **Skill performance surface**: Compute the seven SK-7 components and their aggregate risk rating

**Important:** Use the utility scripts ([`extract_agent_info.py`](scripts/extract_agent_info.py), [`extract_tool_info.py`](scripts/extract_tool_info.py)) to extract tool and skill metadata before scoring the "Execution & Tool Grounding" dimension. Both scripts live under `scripts/` relative to this skill file — not the top-level workspace. `extract_agent_info.py` now includes full skill resolution: pass `--search-root` pointing at the project root if SKILL.md files are not co-located with the agent YAML. If tools/collaborators/skills are referenced but their formal definitions cannot be extracted (file not found, unsupported format), note this as a limitation. The evaluation can proceed, but recommend that the user provide definitions and re-run the evaluation for a complete assessment.
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

For each resolved skill, additionally extract:
- **SK-1**: Number of distinct tool calls / primary workflows in the skill body
- **SK-2**: Any overlap with other skills — pairs, quoted evidence, overlap rating
- **SK-3**: Whether the `description` explicitly states covered intents AND boundary conditions (what it does NOT cover)
- **SK-4**: Any cross-skill state assumptions — explicit references to another skill's output or implicit state that could only come from a prior skill; **plus**: build the dependency graph across all skills and check for cycles — list any loop found as a separate item with all skills in the cycle named
- **SK-5**: Per-skill Rule A/B/C/E/F signal counts (lines, branches, active rules, exact phrases, implicit state)
- **SK-6**: Correlated skill pairs — shared `allowed-tools`, adjacent intent co-occurrence, cross-body tool references; consolidation recommendation (yes/no with justification)
- **SK-7**: Skill architecture performance surface — all seven components with measured values and risk ratings; overall skill-load overhead rating

Document the analysis mode in the report:
- **Enhanced Mode**: Used utility scripts to extract agent and tool metadata; SKILL.md bodies read and analyzed for Skill Health (SK-1 through SK-5)
- **Direct Analysis Mode**: Manual analysis only (no tool metadata available)
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

**When skills are present, also produce a Skill Health assessment** for each skill using the SK-1 through SK-7 criteria. Skill Health is reported per-skill with a Pass / Warn / Fail rating for each criterion — it does not produce a single numeric score but feeds directly into the five agent dimensions and the Runtime Performance Risk section:
- SK-1 violations raise complexity in Dimension 4 (Instruction Followability) — a bloated skill body inflates the effective instruction surface
- SK-2 violations lower Dimension 2 (Scope & Applicability) — overlapping skills mean the agent cannot reliably determine when each applies
- SK-3 failures lower Dimension 2 (Scope & Applicability) — unclear routing descriptions produce misdirected skill loads
- SK-4 violations lower Dimension 5 (State & Conflict Manageability) — cross-skill dependencies create hidden state coupling
- SK-5 failures lower Dimension 4 (Instruction Followability) and Dimension 3 (Execution & Tool Grounding) — complexity inside a skill degrades its own reliability independently of the agent instructions
- SK-6 triggers raise `skill_load_overhead_risk` in the Runtime Performance Risk section — correlated skills that co-load per turn add measurable latency and instruction interference; paired with a consolidation recommendation when the trigger threshold is met
- SK-7 surface assessment populates the full skill performance surface table in Runtime Performance Risk — the aggregate overhead rating (Low/Medium/High) is a deterministic output, not a judgment call
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

**Token optimization side report (`token_optimization_report.md`):** Always produced as part of every evaluation. Covers **both optimization surfaces**: (1) the agent's main instructions — loaded on every single turn, highest-leverage target — and (2) skill bodies, loaded per intent. Runs the full Rule O checklist against both surfaces and reports each pattern with a severity (High / Medium / Low / None found). If no issues are found, the report records the current per-turn token budget as a verified baseline and closes with that finding.

**Performance optimization side report (`performance_optimization_report.md`):** Always produced as part of every evaluation. Targets **execution call-graph depth**: unconditional tool calls, fixed sequential tool chains, `next_action` multi-hop dispatch, deep skill/collaborator stacks, guidelines overhead, and correlated tool sets. Runs the full Rule P checklist and reports each pattern with a severity. If no issues are found, the report records the current call-graph baseline and closes with that finding.

**Report set layout:**

```
instructions_eval/
├── index.md                                    ← manifest listing all reports and their overall verdicts
├── rules-summary.md                            ← copy of evaluation rules reference (copy from skill directory)
├── token_optimization_report.md                ← token consumption optimization report (optional — see Rule O)
├── performance_optimization_report.md          ← runtime performance optimization report (optional — see Rule P)
├── agent_<name>_report.md                      ← agent-level report (main instructions only)
├── agent_<name>_report_harness.json            ← agent-level JSON harness
├── skill_<skill-name>_report.md                ← one per resolved skill
├── skill_<skill-name>_report_harness.json
└── ...
```

**Filename conventions:**
- Agent report: `agent_<name>_report.md` / `agent_<name>_report_harness.json`
  - `<name>` = the agent's `name` field (snake_case, no spaces)
- Skill report: `skill_<skill-name>_report.md` / `skill_<skill-name>_report_harness.json`
  - `<skill-name>` = the skill's `name` frontmatter field (snake_case, no spaces)
- Index: `index.md`
- Default output directory: `eval/` relative to the agent YAML's directory. Create it if it does not exist.

**What goes in each report:**

| Content | Agent report | Skill report |
|---|---|---|
| Agent-level instructions analysis (all 5 dimensions) | ✓ | — |
| Agent-level Runtime Performance Risk | ✓ | — |
| Skill Health Assessment table (all skills, cross-skill SK-2/SK-6/SK-7) | ✓ | — |
| Consolidation recommendations (SK-6) | ✓ | — |
| Skill architecture performance surface (SK-7) | ✓ | — |
| Skill body analysis (5 dimensions applied to skill body) | — | ✓ |
| SK-1, SK-3, SK-4, SK-5 deep analysis for this skill | — | ✓ |
| Runtime Performance Risk for this skill body | — | ✓ |
| Back-reference to agent report | — | ✓ |
| Forward-references to all skill reports | ✓ | — |

**Evaluation order and save-as-you-go:**
1. Extract all metadata (Step 1) — this is fast and must complete before any analysis
2. Copy `rules-summary.md` from the skill directory into the output `eval/` directory — do this once, before writing any reports
3. Evaluate and save the **agent report** first — it scores the main instructions and sets the cross-skill context
4. Evaluate and save skill reports in **batches of at most 2 at a time** — analyse and write 2 skills, save both, then proceed to the next 2. Do not evaluate all skills simultaneously; batching limits context load and reduces the risk of analysis cross-contamination between skills
5. Evaluate and save the **token optimization side report** after all skill reports are complete — always; it synthesizes evidence from the full report set
6. Evaluate and save the **performance optimization side report** after the token optimization report — always; it can cross-reference Rule O items for dual-benefit opportunities
7. Write the **index file** last, after all reports are complete

**When SKILL.md files cannot be resolved:** produce the agent report with a "Partial Skill Mode" note; omit skill reports for unresolved skills; list them in the index as `unresolved`. Still produce both side reports — they will note the partial mode as a limitation.

**When there are no skills:** produce all reports including both side reports. The token and performance reports will note the reduced surface (agent instructions only; no skill bodies to assess) and may be brief if no issues are found.
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
- [`example-finding.md`](example-finding.md): Sample finding with all required elements
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
7. **Skill Health table** (when skills are present): one row per skill, SK-1 through SK-7 ratings with evidence notes
8. Cross-skill overlap summary (SK-2), consolidation recommendations (SK-6), skill architecture performance surface (SK-7)
9. Forward-links to each skill report: `See skill report: [skill-<name>_report.md](skill-<name>_report.md)`

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
2. Optimization inventory: one OPT-N entry per identified opportunity, with current cost, root cause, recommendation, and projected saving
3. Post-optimization token budget estimates (before/after table per turn type)
4. Implementation priority table (effort × token impact × reliability benefit)
5. Per-skill token footprint reference (current lines, current tokens, target after optimizations)
6. Anti-pattern section: patterns that produced the identified overhead, to guide future prompt authors
7. Back-reference to the agent report: `Side report to: [agent_<name>_report.md]`

*Performance optimization report* (`performance_optimization_report.md`) — always produced:
1. Current execution profile table: turn types, inference hops, tool-call RTTs, skill loads
2. Optimization inventory: one PERF-N entry per identified opportunity, with current cost, root cause, mechanism, and estimated impact
3. Tool composition candidates table: chains that could be collapsed into Python tools, flow tools, or agentic workflows
4. Post-optimization call-graph depth estimates (before/after table per turn type)
5. Implementation priority table (effort × latency impact × Rule O dual benefit)
6. Anti-pattern section: patterns that produced identified overhead
7. Cross-references to Rule O items where dual benefit exists
8. Back-reference to the agent report: `Side report to: [agent_<name>_report.md]`

*Index file* (`index.md`) + `rules-summary.md` (copied from skill directory):
1. Table listing every report, its artifact type, and its overall verdict/band
2. Agent-level scorecard summary (one row per dimension)
3. Skill Health summary table (collapsed SK-1–SK-7 ratings per skill)
4. List of any unresolved skills (SKILL.md not found)
5. Link to `token_optimization_report.md` in the Reference Documents section (when produced)
6. Link to `performance_optimization_report.md` in the Reference Documents section (when produced)
7. `rules-summary.md` present in the same `eval/` directory (copied, not regenerated)

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
