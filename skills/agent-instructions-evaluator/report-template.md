# Report Template Structure

This file defines **seven templates** that together form the **complete report set** produced for every evaluation.

> ⚠️ **All seven reports are mandatory.** An evaluation that omits any of these files is incomplete.

## Required report set

| # | Template | Filename | Always produced? |
|---|---|---|---|
| 1 | Agent report | `agent_<name>_report.md` + `agent_<name>_report_harness.json` | ✓ Yes |
| 2 | Skill report (one per skill) | `skill_<skill-name>_report.md` + `skill_<skill-name>_report_harness.json` | ✓ Yes — one per resolved skill |
| 3 | Index | `index.md` | ✓ Yes — written last |
| 4 | Token optimization report | `token_optimization_report.md` | ✓ Yes — even if no issues found |
| 5 | Performance optimization report | `performance_optimization_report.md` | ✓ Yes — even if no issues found |
| 6 | **Reliability optimization report** | **`reliability_optimization_report.md`** | ✓ **Yes — even if no issues found** |
| 7 | Rules reference copy | `rules-summary.md` | ✓ Yes — copied from skill directory |

All files go in `eval/` relative to the agent YAML's directory. Each report is saved to disk as soon as it is complete. Skill reports are produced in **batches of at most 2 at a time** — complete and save 2 skill reports before starting the next pair. Do not evaluate all skills in parallel.

**Writing order:**
1. Agent report (first — establishes cross-skill context)
2. Skill reports in batches of 2
3. Token optimization report (Template 4)
4. Performance optimization report (Template 5)
5. **Reliability optimization report (Template 6) — do not skip**
6. Index (last — references all of the above)

---

## Template 1: Agent Report

```markdown
# Agent Prompt Achievability Evaluation Report

## Evaluation Disclaimer

**This evaluation is subjective and based on the evaluating LLM's interpretation of its own ability to understand and follow the instructions.** The scores, findings, and recommendations should be treated as **indicative guidance** rather than absolute metrics. Different LLM models, versions, or instances may interpret the same instructions differently and achieve varying levels of compliance.

**Key limitations:**
- Scores reflect estimated achievability based on known LLM attention patterns and empirical thresholds, not guaranteed outcomes
- The evaluation cannot predict actual runtime behavior across all possible user inputs and contexts
- Tool grounding assessments are limited by the availability of formal tool definitions in the evaluation input
- Findings are based on manual analysis and may not capture all edge cases or interactions

**Recommended use:**
- Use this report as a diagnostic tool to identify high-risk areas in prompt design
- Validate findings through empirical testing with the target LLM in production-like conditions
- Prioritize changes based on severity and operational impact, not just scores
- Re-evaluate after making significant changes to instructions or tooling

## Artifact Summary
- Artifact type: [voice assistant system prompt | agent YAML | instruction block | etc.]
- Artifact name: [filename or identifier]
- Evaluation scope: [full | partial]
- Evaluation mode: [single-llm extraction + simple counting tool | direct analysis mode]
- Overall verdict: [brief summary of achievability]

## Extraction and Tool Summary
- Semantic extraction performed by: [running_llm | tool_name]
- Simple tool or harness used: [none | tool_name]
- Incidents extracted before scoring: [count or list]
- Signals derived from extracted incidents: [list of signal types]
- What was not counted via tool: [explanation]
- Confidence impact: [how lack of tooling affects confidence]

## Dimension Scorecard
| Dimension | Score (0-5) | Confidence (Low/Med/High) | Key Evidence | Deterministic Signals | Primary Risk |
|---|---:|---|---|---|---|
| Task Understanding | X | [Low/Med/High] | [brief evidence] | [signals] | [risk] |
| Scope & Applicability | X | [Low/Med/High] | [brief evidence] | [signals] | [risk] |
| Execution & Tool Grounding | X | [Low/Med/High] | [brief evidence] | [signals] | [risk] |
| Instruction Followability | X | [Low/Med/High] | [brief evidence] | [signals] | [risk] |
| State & Conflict Manageability | X | [Low/Med/High] | [brief evidence] | [signals] | [risk] |

## Deterministic Signal Summary
- Prompt length: [line count] lines ([Short ≤50 | Medium 51-100 | Long 101-200 | Very long >200])
- Likely critical constraints: [count]
- Exact phrase requirements found: [count]
- Exception clauses found: [count]
- Nested conditional branches found: [count]
- Implicit state requirements found: [count]
- Red-flag state phrases found: [list]
- Subjective classifiers found: [list]
- Tool-required behaviors missing execution details: [count]
- Hard conflicts found: [count]

## Overall Interpretation
- Interpretation band: [Very high-risk / High-risk / Moderate-risk / Low-risk / Strong]
- Strongest dimension: [dimension name] ([score]/5)
- Weakest dimension: [dimension name] ([score]/5)
- Reliability outlook: [paragraph explaining expected production behavior]
- What would most improve this artifact: [top 1-2 changes]

## Runtime Performance Risk
- Token overhead risk: [Low / Medium / High]
- Reasoning overhead risk: [Low / Medium / High]
- Tool-call overhead risk: [Low / Medium / High]
- Retry / repair-loop risk: [Low / Medium / High]
- Latency variance risk: [Low / Medium / High]
- Skill-load overhead risk: [Low / Medium / High / N/A — only when `skills:` are present]

### Main performance risk drivers
- [List the signals that drive runtime cost, e.g. prompt length, ambiguous tool triggers, interacting constraints, correlated skill pairs, large skill bodies]

### Skill architecture performance surface (omit section if no skills)
| Component | Measured value | Risk rating |
|---|---|---|
| Skill count | [N] | [Low / Medium / High] |
| Per-skill body size (max / avg lines) | [X / Y lines] | [Low / Medium / High] |
| Routing ambiguity (plausible candidates/turn) | [N] | [Low / Medium / High] |
| Load transitions per turn (est. `load_skill` calls for multi-step intents) | [N] | [Low / Medium / High] |
| Re-load frequency (confirmed same-skill reload in one turn) | [Yes / No] | [Medium if Yes / Low if No] |
| Per-load token cost (largest skill body likely loaded) | [~N tokens] | [Low / Medium / High] |
| **Overall skill-load overhead** | | **[Low / Medium / High]** |

### Correlated skill pairs (omit if none found)
| Skill A | Skill B | Correlation type | Consolidation recommended? |
|---|---|---|---|
| [skill-name] | [skill-name] | [Adjacent intents / Mid-body load_skill reference] | [Yes — reason / No] |

### Tool-binding shadows (omit if none found)
| Tool | Skill listing it in allowed-tools | Also in agent tools:? | Impact |
|---|---|---|---|
| [tool-name] | [skill-name] | Yes | Agent cannot call [tool-name] when no skill is active — silent execution gap |

### Performance interpretation
[Short paragraph explaining whether instruction complexity is likely to increase runtime cost, latency, tool-call count, or response variance. Distinguish deterministic evidence from judgment-based conclusions. When skills are present, include: expected per-turn skill-load cost, whether any skill pairs require sequential loads in the same turn, and whether the skill architecture as a whole adds measurable latency overhead.]

## Dimension Analysis

### 1. Task Understanding
- Score: X/5
- Confidence: [Low/Med/High]
- Evidence: [quotes or paraphrases from input]
- Deterministic signals: [list]
- Why this score: [explanation]
- Improvement priority: [Low/Medium/High/Critical]

### 2. Scope & Applicability
- Score: X/5
- Confidence: [Low/Med/High]
- Evidence: [quotes or paraphrases from input]
- Deterministic signals: [list]
- Why this score: [explanation]
- Improvement priority: [Low/Medium/High/Critical]

### 3. Execution & Tool Grounding
- Score: X/5
- Confidence: [Low/Med/High]
- Evidence: [quotes or paraphrases from input]
- Deterministic signals: [list]
- Why this score: [explanation]
- Improvement priority: [Low/Medium/High/Critical]

### 4. Instruction Followability
- Score: X/5
- Confidence: [Low/Med/High]
- Evidence: [quotes or paraphrases from input]
- Deterministic signals: [list]
- Why this score: [explanation]
- Improvement priority: [Low/Medium/High/Critical]

### 5. State & Conflict Manageability
- Score: X/5
- Confidence: [Low/Med/High]
- Evidence: [quotes or paraphrases from input]
- Deterministic signals: [list]
- Why this score: [explanation]
- Improvement priority: [Low/Medium/High/Critical]

## Skill Reports

> Links to per-skill evaluation reports (omit section if no skills):
> - [skill-<skill-name>_report.md](skill-<skill-name>_report.md) — [skill display name]
> - [Continue for each resolved skill]
> Unresolved skills (SKILL.md not found): [list, or "none"]

## Skill Health Summary (omit section if no skills)

> Per-skill dimension scores and deep analysis appear in individual skill reports. This table is a cross-skill health overview. Only SK-2 (overlap), SK-3 hard-limit failures, and SK-6 tool-binding shadows have direct impact on the agent's five dimension scores. All other SK findings are contained in the per-skill reports.

### Skill Health Summary Table
| Skill | SK-1 | SK-2 | SK-3 | SK-4 | SK-5 | SK-6 | SK-7 | SK-8 |
|---|---|---|---|---|---|---|---|---|
| [skill-name] | [P/W/F] | [P/W/F] | [P/W/F — incl. hard-limit] | [P/W/F] | [P/W/F] | [P/W/F — incl. shadow] | [P/W/F] | [P/W/F] |

> P = Pass, W = Warn, F = Fail. Hard-limit failures in SK-3 and tool-binding shadows in SK-6 are marked F and noted in agent Dimension 3. SK-2 Exact/High failures are marked F and noted in agent Dimension 2.

**Rating guide:**
- **Pass**: No issue detected
- **Warn**: Potential issue; monitor or improve before production scale
- **Fail**: Definite issue that will cause reliability or performance problems at production load

**Agent dimension impact from skill findings:**
- **SK-2 Exact/High** → lowers agent Dimension 2 (Scope & Applicability): ambiguous routing
- **SK-3 Fail (hard limit)** → lowers agent Dimension 3 (Execution & Tool Grounding): skill is unreachable
- **SK-6 tool-binding shadow** → lowers agent Dimension 3 (Execution & Tool Grounding): tool silently unavailable
- **All other SK Fails** → contained in per-skill reports; do not affect agent dimension scores

### Cross-skill overlap pairs (SK-2)
| Skill A | Skill B | Overlap rating | Evidence |
|---|---|---|---|
| [skill-name] | [skill-name] | [Exact/High/Moderate/Low] | [quoted text from both descriptions] |

### Consolidation recommendations (SK-6)
For each pair meeting the consolidation trigger threshold (SK-2 Moderate/High overlap + co-occurring intents, OR mid-body `load_skill` creating sequential dependency):

**[Skill A] + [Skill B] → consolidate into [suggested-name]**
- **Why**: [overlapping intents / mid-body load_skill reference — cite evidence]
- **Performance implication**: Sequential loads (A then B) add one extra `load_skill` call per turn — each call replaces the active body. For a workload of [N] turns/hour where [X%] require both, this adds [estimate] overhead per hour.
- **How to consolidate**: [Merge strategy: union the `allowed-tools` lists, merge the body sections, deduplicate rules, update the `description` to cover both intent sets and their combined boundary conditions]

### Skill health findings (agent-visible issues only)
[For SK-2, SK-3 hard-limit, or SK-6 tool-binding shadow Fail ratings, produce a full finding: Evidence, Why it matters, Deterministic or judgment-based, Agent dimension impact, Recommended change. For all other Warn/Fail ratings, note: "See [skill_X_report.md] for full analysis."]

## Findings

### Finding 1: [Short descriptive title]
**Evidence**
> [Direct quote from input] *(line N)*
> [Translation]: [English rendering — **REQUIRED if quote is not in English; omit only if quote is already in English**]
> [Another quote if relevant] *(line N)*
> [Translation]: [English rendering — **REQUIRED if quote is not in English**]

**Why it matters**
[Explanation of operational impact]

**Deterministic or judgment-based**
[Classification: Deterministic | Judgment-based | Both]

**Score impact**
- [Dimension name]: [how this finding affects the score]
- [Another dimension if applicable]: [impact]

**Recommended change**
[Specific, actionable fix]

### Finding 2: [Short descriptive title]
[Same structure as Finding 1]

[Continue for all major findings - aim for 3-7 findings]

## Key Risks
1. [First major risk with brief explanation]
2. [Second major risk]
3. [Third major risk]
[Continue as needed]

## High-Impact Changes
1. [Highest-leverage fix with expected impact]
2. [Second highest-leverage fix]
3. [Third highest-leverage fix]
[Continue as needed]

## Optional Rewrite Targets
- Rewrite candidate 1: [Specific section/rule to rewrite with line numbers if available]
- Rewrite candidate 2: [Another rewrite target]
- Rewrite candidate 3: [Another rewrite target]

---

## Template 2: Skill Report

Use this structure for `skill_<skill-name>_report.md`. The instruction content being evaluated is the skill's `SKILL.md` **body** (everything after the closing `---` of the frontmatter).

```markdown
# Skill Evaluation Report: [skill-name]

> Part of agent evaluation: [agent_<agent-name>_report.md](agent_<agent-name>_report.md)

## Evaluation Disclaimer

[Same disclaimer text as agent report]

## Artifact Summary
- Artifact type: skill body (watsonx Orchestrate SKILL.md)
- Skill name: [name from frontmatter] ([N chars] — [✓ within 64-char limit / ⚠ EXCEEDS 64-char limit — skill will not import])
- Skill description: [text from frontmatter description field]
- Description length: [N chars] — [✓ within 1024-char limit / ⚠ EXCEEDS 1024-char limit — skill will not load]
- Unmatched placeholders: [none / list of {{identifier}} tokens with no matching param — hard failure]
- Skill file: [relative path to SKILL.md]
- Agent: [agent name]
- Evaluation scope: [full | partial]
- Evaluation mode: [Enhanced Mode | Direct Analysis Mode | Partial Skill Mode]
- Overall verdict: [brief summary of this skill's achievability]

## Extraction and Tool Summary
- Skill body length: [line count] lines
- allowed-tools count: [N] — [list of tool names]
- scripts/ files: [list or "none"]
- references/ files: [list or "none"]
- Confidence impact: [explanation]

## Dimension Scorecard
| Dimension | Score (0-5) | Confidence | Key Evidence | Deterministic Signals | Primary Risk |
|---|---:|---|---|---|---|
| Task Understanding | X | [Low/Med/High] | [brief evidence] | [signals] | [risk] |
| Scope & Applicability | X | [Low/Med/High] | [brief evidence] | [signals] | [risk] |
| Execution & Tool Grounding | X | [Low/Med/High] | [brief evidence] | [signals] | [risk] |
| Instruction Followability | X | [Low/Med/High] | [brief evidence] | [signals] | [risk] |
| State & Conflict Manageability | X | [Low/Med/High] | [brief evidence] | [signals] | [risk] |

## Deterministic Signal Summary
- Skill body length: [line count] lines ([Short ≤50 | Medium 51-100 | Long 101-200 | Very long >200])
- Critical constraints (MUST/NEVER/ALWAYS/EXACTLY): [count]
- Exact phrase requirements: [count]
- Nested conditional branches: [count]
- Active operational rules per turn (est.): [count]
- Implicit state requirements: [count]
- Tool-required behaviors missing execution details: [count]
- Hard conflicts: [count]

## Skill Health — This Skill (SK-1, SK-3, SK-4, SK-5)
> Note: SK-2 (overlap), SK-6 (correlation), and SK-7 (architecture surface) are cross-skill checks and appear in the agent report only.

- **SK-1 Single Responsibility**: [Pass / Warn / Fail] — [evidence: N distinct workflows / tool categories]
- **SK-3 Routing Clarity**: [Pass / Warn / Fail] — [evidence: does description state intents + boundary conditions?]
- **SK-4 Cross-Skill Dependencies / Handoffs**:
  - Case 1 Backward assumptions: [Pass / Fail] — [evidence: any references to prior skill state, prior skill outputs, or tools exclusively owned by another skill?]
  - Case 2 Mid-body `load_skill`: [Pass / Fail] — [evidence: any `load_skill` call before terminal step with subsequent steps that depend on returning?]
  - Case 3 Terminal handoffs: [documented] — [list: skill-A → skill-B; chain depth if chain exists]
  - Dependency loop: [None detected / Cycle found: skill-A → skill-B → skill-A]
- **SK-5 Complexity Budget**: [Pass / Warn / Fail] — [evidence: Rule C/E/F signal counts]

## Overall Interpretation
- Interpretation band: [Very high-risk / High-risk / Moderate-risk / Low-risk / Strong]
- Strongest dimension: [dimension name] ([score]/5)
- Weakest dimension: [dimension name] ([score]/5)
- Reliability outlook: [paragraph]
- What would most improve this skill: [top 1-2 changes]

## Runtime Performance Risk (this skill body)
- Token overhead risk: [Low / Medium / High]
- Reasoning overhead risk: [Low / Medium / High]
- Tool-call overhead risk: [Low / Medium / High]
- Retry / repair-loop risk: [Low / Medium / High]
- Latency variance risk: [Low / Medium / High]

### Main performance risk drivers
- [List signals: body length, branch count, active rule count, underspecified tools]

### Performance interpretation
[Short paragraph. Focus on this skill body's own complexity, not the agent's. Note whether the skill body is lean enough to contribute low overhead when loaded.]

## Dimension Analysis

### 1. Task Understanding
- Score: X/5 — [evidence and reasoning]

### 2. Scope & Applicability
- Score: X/5 — [evidence and reasoning]

### 3. Execution & Tool Grounding
- Score: X/5 — [evidence and reasoning; note any tools in body not in allowed-tools]

### 4. Instruction Followability
- Score: X/5 — [evidence and reasoning; cite SK-5 signal counts]

### 5. State & Conflict Manageability
- Score: X/5 — [evidence and reasoning; cite any SK-4 issues found]

## Findings

### Finding 1: [Short title]
**Evidence**
> [Direct quote from SKILL.md body] *(line N)*
> [Translation]: [English rendering — **REQUIRED if quote is not in English; omit only if quote is already in English**]

**Why it matters** / **Deterministic or judgment-based** / **Score impact** / **Recommended change**
[Standard five-element structure]

[Continue for 2-4 findings]

## Key Risks
1. [First major risk]
2. [Second major risk]

## High-Impact Changes
1. [Highest-leverage fix]
2. [Second fix]

## Optional Rewrite Targets
- [Section or rule bundle to rewrite]
```

---

## Template 3: Index

Use this structure for `index.md`.

```markdown
# Evaluation Index — [Agent Name]

Generated: [date/time if available]

## Reference Documents

### Extraction Snapshots
- [agent_<name>_extracted.json](agent_<name>_extracted.json) — Full agent metadata snapshot: instructions tokens, skill catalog tokens, collaborator routing tokens, resolved skills + collaborators with all frontmatter validation flags
- [tool_<tool-name>_extracted.json](tool_<tool-name>_extracted.json) — Tool spec snapshot: signatures, parameters, return types, spec chars, spec token estimate *(one file per tool)*

### Evaluation Reports
- [rules-summary.md](rules-summary.md) — Evaluation rules reference (Rules A–Q, scoring dimensions, interpretation bands)
- [token_optimization_report.md](token_optimization_report.md) — Token consumption optimization ([N optimizations identified / No issues found] — ~X% per-turn reduction or baseline recorded)
- [performance_optimization_report.md](performance_optimization_report.md) — Runtime performance optimization ([N items identified / No issues found] — ~X hops eliminated or baseline recorded)
- [reliability_optimization_report.md](reliability_optimization_report.md) — Reliability optimization ([N items: X Critical / Y High / or "No issues found"] — implementation roadmap or baseline recorded)

## Report Set

| Report | Type | Artifact | Verdict | Weakest dimension |
|---|---|---|---|---|
| [agent_<name>_report.md](agent_<name>_report.md) | Agent | `<name>` | [Very high-risk / High-risk / Moderate-risk / Low-risk / Strong] | [dimension (score/5)] |
| [skill_<skill-name>_report.md](skill_<skill-name>_report.md) | Skill | `<skill-name>` | [band] | [dimension (score/5)] |
| [Continue for each skill] | | | | |

## Agent Dimension Scorecard

| Dimension | Score | Confidence |
|---|---:|---|
| Task Understanding | X/5 | [Low/Med/High] |
| Scope & Applicability | X/5 | [Low/Med/High] |
| Execution & Tool Grounding | X/5 | [Low/Med/High] |
| Instruction Followability | X/5 | [Low/Med/High] |
| State & Conflict Manageability | X/5 | [Low/Med/High] |

## Skill Health Summary

| Skill | SK-1 | SK-2 | SK-3 | SK-4 | SK-5 | SK-6 | SK-7 | Report |
|---|---|---|---|---|---|---|---|---|
| [skill-name] | [P/W/F] | [P/W/F] | [P/W/F] | [P/W/F] | [P/W/F] | [P/W/F] | [P/W/F] | [skill_<skill-name>_report.md](skill_<skill-name>_report.md) |

Legend: P = Pass · W = Warn · F = Fail

## Unresolved Skills

| Skill name | Reason |
|---|---|
| [skill-name] | SKILL.md not found under [search-root] |

(Omit this section if all skills resolved.)
```

---

## Template 4: Token Optimization Report

Use this structure for `token_optimization_report.md`. This report is **always produced** as part of every evaluation — it does not re-score the five evaluation dimensions.

**Coverage:** This report covers **three optimization surfaces**:
- **Agent instructions** — loaded on every turn; reductions here save tokens universally
- **Skill catalog** (all skill names + descriptions) — loaded on every turn regardless of which skill is active; overlong descriptions waste catalog tokens for detail that is only useful after loading
- **Skill bodies** — loaded per intent, one at a time; reductions here save tokens on the affected turn types

**When no issues are found:** still produce the full report. Use "None found" for each checklist item, include the current token budget table as a baseline, omit the OPT-N inventory section (or include it with a single "No opportunities identified" note), and close the report with the standard baseline statement.

```markdown
# Token Consumption Optimization Report
## [Agent Name]

> Side report to: [agent_<name>_report.md](agent_<name>_report.md)
> See also: [performance_optimization_report.md](performance_optimization_report.md) · [reliability_optimization_report.md](reliability_optimization_report.md)
> Generated: [date]
> Scope: Token and reasoning overhead across agent instructions + [N] skill bodies

---

## Purpose

[1–2 sentences stating the optimization goal. Note the original baseline token cost if a prior version exists, and the current per-turn cost range. Distinguish the two optimization surfaces: agent instructions (paid every turn) vs. skill bodies (paid per load).]

---

## Current State Baseline

### Token Budget (per turn, estimated)

> Token estimates use **character count ÷ 4** (≈4 chars/token). `extract_agent_info.py` computes these automatically — use the reported values directly. Token costs are **scoped per level** — report each level separately, never sum across levels.

#### Level 1 — Agent context (paid on every agent turn)

| Component | Chars | Est. Tokens | Notes |
|---|---:|---:|---|
| Agent instructions | [N] | ~[N] (`instructions_est_tokens`) | Always |
| Skill catalog — names + descriptions (N skills) | [N] | ~[N] (`skill_catalog_est_tokens`) | Always — agent needs all skill descriptions to decide which skill to load |
| Collaborator routing — names + descriptions (N collabs) | [N] | ~[N] (`collaborator_routing_est_tokens`) | Always — routing signal only; collaborator internals are in their own context |
| Agent tool list — names only (N active tools) | [N] | ~[N] (`tool_list_est_tokens`) | Active tools only — shadowed tools excluded (platform removes them from base set) |
| Agent tool specs — schemas (N active tools) | [N] | ~[N] (`tools_spec_est_tokens`) | Active tools only — shadowed tools not loaded at L1 |
| [Any mandatory pre-routing tool call] | — | ~[N] | Always / Conditional |
| **Agent floor total** | | **~[N] (`agent_floor_est_tokens`)** | **Paid on every turn** |

> **Tool-binding shadow — token scoping (SK-6):** When a skill lists a tool in its `allowed-tools`, the wxO platform removes that tool from the agent's base tool set. Its spec is therefore **not present in the L1 context** — `extract_agent_info.py` automatically excludes shadowed tools from `tool_list_est_tokens`, `tools_spec_est_tokens`, and `agent_floor_est_tokens`. The floor reflects only the tools that are truly active at the agent level. Shadowed tools are reported separately in `shadowed_resolved_tools` for the SK-6 reliability diagnostic (report in the reliability report, not the token optimization report).

#### Level 2 — Skill context (added on top of Level 1 when a skill is loaded)

| Component | Chars | Est. Tokens | Notes |
|---|---:|---:|---|
| Loaded skill body (avg) | [N] | ~[N] (`body_est_tokens` avg) | On every intent turn where a skill is loaded |
| Loaded skill body (max — [skill-name]) | [N] | ~[N] | On [intent type] turns |
| Skill allowed-tool list — names (avg) | [N] | ~[N] | Injected when skill loads — owned by the skill, not the agent |
| Skill allowed-tool specs — schemas (avg) | [N] | ~[N] (`allowed_tools_spec_est_tokens` avg) | Injected when skill loads — owned by the skill, not the agent |
| KB / retrieval tool output ([tool-name], [N] passages est.) | — | ~[N] | On [intent type] turns — see passage count note |
| **Typical skill-load cost (avg body + avg allowed-tools)** | | **~[N]** | Added to Level 1 floor |
| **Complex skill-load cost (max body + max allowed-tools + KB)** | | **~[N]** | Added to Level 1 floor |
| **Multi-step turn ([A] then [B] sequentially)** | | **~[N] per load** | On ~[N]% of turns — each load replaces the previous body |

#### Level 3 — Collaborator context (separate LLM call, own context window)

> Collaborator instructions, tools, and skills run in an entirely separate context window. These tokens are **not additive to Level 1 or Level 2** — they are a distinct per-call budget. Report collaborator token cost separately, not as part of the agent floor.

| Collaborator | Instructions | Tool list | Tool specs | Skill catalog | Per-call floor |
|---|---:|---:|---:|---:|---:|
| [collab-name] | ~[N] (`instructions_est_tokens`) | ~[N] | ~[N] | ~[N] | ~[N] |

---

> **Note — skill load model:** Only one skill body is active at a time. A turn that requires two sequential skill loads pays for each body (+ its allowed-tools) separately — the first is replaced when the second loads, not summed.
>
> **Note — allowed-tools scoping:** A skill's `allowed-tools` names and schemas are owned by the skill and injected only when that skill loads. They are **not** part of the agent's Level 1 floor. Do not include them in the agent floor total.
>
> **Note — collaborator scoping:** Collaborator internal costs (instructions, tools, skills) are in the collaborator's own context window. Only the collaborator's routing tokens (name + description) appear in the supervisor's Level 1 context.
>
> **KB / retrieval note:** Retrieved passages are injected into context at runtime and are **not visible to static analysis**. Use ≥500 tokens/passage as a conservative lower-bound estimate (typical chunks: 500–1,500 tokens). If no limit is stated, flag as High risk (unbounded). Always state as an approximation; exact values require runtime tracing.

---

## Optimization Opportunity Inventory

> Opportunities are grouped by surface. **Agent instruction optimizations first** — they have universal per-turn impact. Skill body optimizations follow.

### Agent Instruction Optimizations

#### OPT-1 — [Short title]

**Category:** Agent instructions
**Severity:** [High / Medium / Low]
**Current cost:** [N] lines / ~[N] tokens (paid on every turn)
**Removable:** ~[N] lines (~[X]% of current [total]-line agent instructions)

**Evidence:**
> [Direct quote or section reference from agent instructions]

**Root cause:** [missing tool schema / missing plugin hook / missing server-side state / copy-paste from prior version]

**Recommendation:** [Move to tool schema / move to plugin / move to server-side state / remove as redundant]
- **Target:** [What the agent instructions look like after: e.g., "reduce the tool-call contract section from 12 lines to a 2-line trigger + relay rule"]
- **Estimated saving:** ~[N] lines removed (~[X]% of current [total]-line agent instructions) → ~[Z] tokens saved on **every turn**

**Cross-report:** [PERF-N — also eliminates N inference hop / REL-N — also resolves Rule A/B/C/E/F signal / No cross-report overlap]

---

#### OPT-2 — [Short title]

[Same structure as OPT-1]

[Continue for all agent instruction opportunities]

---

### Skill Body Optimizations

#### OPT-[N] — Knowledge base / retrieval token risk

**Category:** KB / retrieval
**Severity:** [High / Medium / Low]
**Location:** [Agent instructions / Skill body — skill-name]
**Retrieval surface:** [tool-name] — identified as KB/retrieval tool by [name pattern / kind: knowledge_base / description keyword]
**Passage count:** [stated limit: N / no limit stated — unbounded]
**Call frequency:** [Always / On [intent type] turns / Conditional on [condition]]
**Estimated retrieval payload per call:** ~[N] passages × ≥500 tokens (lower bound) = ~[N] tokens
> ⚠ Passage token cost is a **runtime variable** — chunk size is set in the knowledge base configuration, not in the agent instructions, and cannot be verified from static analysis. The estimate above uses ≥500 tokens/passage as a conservative lower bound. Actual cost may be significantly higher (typically 500–1,500 tokens/passage). Verify with runtime tracing for an accurate figure.

**Evidence:**
> [Quote from instructions or tool definition showing KB reference; quote any passage count or limit; quote any condition or absence of condition]

**Risk assessment:**
- Passage count risk: [High — no limit / High — limit > 5 / Medium — limit 4–5 / Low — limit ≤ 3]
- Call frequency risk: [High — every turn / Medium — most turns / Low — conditional, infrequent]
- **Latency risk:** [High — unconstrained payload / Medium — bounded but large / Low — small bounded payload]
- Combined: [High / Medium / Low]

**Recommendation:** [Add or lower `top_k`/`max_results` to ≤ 3–5 / Condition the KB call on intent type / Restrict query scope / Merge with a prior tool call]
- **Target:** [e.g., "limit to top_k=3 on billing intent turns; remove KB call entirely on account-status turns"]
- **Estimated saving (token):** ~[N] lines removed (~[X]% of [component] current size) → ~[Z] tokens per [intent type] turn; ~[N]% of all turns affected
- **Estimated saving (latency):** [qualitative — "measurable latency reduction on [intent type] turns" — exact figures require runtime profiling]

**Cross-report:** PERF-N — this finding also applies to the performance optimization report (Rule P); cross-reference both. [REL-N — also resolves Rule X signal / No additional overlap]

---

#### OPT-[N] — [Short title]

**Category:** Skill body
**Severity:** [High / Medium / Low]
**Current cost:** [N] lines / ~[N] tokens in this skill body (paid when [intent type] is loaded)
**Removable:** ~[N] lines (~[X]% of current [total]-line skill body)

**Evidence:**
> [Direct quote or structural evidence from SKILL.md body]

**Root cause:** [copy-paste / coupling architecture / missing plugin / LLM-side classification / sequential-load pair]

**Recommendation:** [Consolidate skills / move to plugin / externalize to tool / remove repeated preamble]
- **Target:** [Target body size or structural outcome]
- **Estimated saving:** ~[N] lines removed (~[X]% of current [total]-line skill body) → ~[Z] tokens per [affected turn type]; ~[N]% of all turns affected

**Cross-report:** [PERF-N — also eliminates N inference hop / REL-N — also resolves Rule X signal / No cross-report overlap]

---

[Continue for all skill body opportunities]

---

## Summary: Projected Savings

> Savings are estimated as a percentage of the current component size (no rewrite assumed). Formula: removable lines ÷ total current lines × 100% → translate to tokens via `removable chars ÷ 4`.

| Item | Category | Current size | Lines removable | % saving | Est. tokens saved/turn | Turns affected |
|---|---|---:|---:|---:|---:|---|
| OPT-1: [title] | Agent instructions | [N] lines | ~[N] | ~[X]% | ~[Z] — **every turn** | All turns |
| OPT-2: [title] | Agent instructions | [N] lines | ~[N] | ~[X]% | ~[Z] — **every turn** | All turns |
| OPT-[N]: [title] | Skill: [name] | [N] lines | ~[N] | ~[X]% | ~[Z] | [intent type] turns |
| [Continue] | | | | | | |
| **Total** | | | **~[N] lines** | | **~[Z] (peak), ~[Z] (avg)** | |

### Revised per-turn estimates (post-optimization)

| Turn type | Current estimate | Post-opt estimate | Saving |
|---|---:|---:|---:|
| Typical turn (agent + catalog + avg skill) | ~[N] tokens | ~[N] tokens | ~[N]% |
| Complex turn (agent + catalog + max skill) | ~[N] tokens | ~[N] tokens | ~[N]% |
| Multi-step turn (sequential [A] then [B]) | ~[N] tokens/load | ~[N] tokens/load | ~[N]% |
| [Other key turn types] | ~[N] tokens | ~[N] tokens | ~[N]% |

---

## Implementation Priority

| Priority | Item | Category | Effort | Impact | Cross-report |
|---|---|---|---|---|---|
| **P1** | OPT-[N]: [title] | Agent instr. / Skill / KB | Low/Med/High | High — every turn / [N]% of turns | OPT-N / PERF-N / None |
| **P2** | OPT-[N]: [title] | Agent instr. / Skill / KB | Low/Med/High | Medium | OPT-N / PERF-N / None |
| [Continue] | | | | | |

> [1–2 sentences on suggested delivery sequence. Note that agent instruction optimizations (P1 candidates) should generally be delivered before skill body optimizations because their savings compound across all turns.]

---

## Token Footprint Reference

### Agent Instructions

| Section | Current lines | Est. tokens | After opt | Target lines | Primary opportunity |
|---|---:|---:|---|---:|---|
| [Section name, e.g. `# TOOL_CONTRACT`] | [N] | ~[N] | OPT-[N] | ~[N] | [short description] |
| [Continue per section] | | | | | |
| **Total agent instructions** | **[N]** | **~[N]** | | **~[N]** | **−[N]% agent token load** |

### Skill Bodies

| Skill | Current lines | Est. tokens | After opt | Target tokens | Primary opportunity |
|---|---:|---:|---|---:|---|
| [skill-name] | [N] | ~[N] | OPT-[N] | ~[N] | [short description] |
| [Continue for each skill] | | | | | |
| **Total skill set** | **[N]** | **~[N]** | | **~[N]** | **−[N]% total skill token load** |

> Note: Token estimates use **character count ÷ 4** (≈4 chars/token). `extract_agent_info.py` computes these automatically — use the reported `body_est_tokens` per skill and `instructions_est_tokens` per section directly. Actual values depend on the tokenizer and language model.

---

## Anti-Patterns to Avoid in Future Iterations

[List the specific anti-patterns found in this evaluation. For each, state what it is, where it appeared (agent instructions or skill body), and what overhead it created. If no anti-patterns were found, write: "No anti-patterns identified — the current design avoids all known token inflation patterns."]

1. **[Anti-pattern name]** — [What it is, where it appeared, and what overhead it created]
2. [Continue for all found patterns]

---

*Side report — does not modify achievability scores in the main reports.*

*Issues found:* Implement the optimizations above and re-run the evaluation with the updated files. *No issues found:* No token optimization opportunities were identified by static analysis. Re-run this evaluation after any significant change to agent instructions, skill bodies, or tool schemas.
```

---

## Template 5: Performance Optimization Report

Use this structure for `performance_optimization_report.md`. This report is **always produced** as part of every evaluation — it does not re-score the five evaluation dimensions.

**Coverage:** This report covers **two performance surfaces**:
- **Tool execution architecture** — tool-call RTTs (round-trip times: the elapsed time between the agent issuing a tool call and receiving its response), `next_action` multi-hop chains, sequential chains that could be collapsed, unconditional routing calls
- **Orchestration depth** — skill/collaborator layer count, redundant routing hops, guidelines overhead

**Relationship to token optimization:** Token cost (Rule O) and execution call-graph depth (Rule P) are complementary. Where an optimization reduces both tokens *and* hops, note it in both reports and flag the dual benefit here.

**When no issues are found:** still produce the full report. Use "None found" for each checklist item, include the current call-graph baseline table, omit the PERF-N inventory section (or note "No opportunities identified"), and close with the standard baseline statement.

```markdown
# Runtime Performance Optimization Report
## [Agent Name]

> Side report to: [agent_<name>_report.md](agent_<name>_report.md)
> See also: [token_optimization_report.md](token_optimization_report.md) · [reliability_optimization_report.md](reliability_optimization_report.md)
> Generated: [date]
> Scope: Execution architecture, tool call-graph depth, and orchestration overhead

---

## Purpose

[1–2 sentences. State the optimization goal in latency/throughput terms: what is the estimated per-turn call-graph depth today, and what is a realistic target? Note which turn types are worst-case.]

---

## Current State Baseline

### Execution Profile (per turn, estimated)

| Turn type | Inference hops | Tool-call RTTs | Skill loads | Notes |
|---|---:|---:|---:|---|
| Simple intent (no routing ambiguity) | [N] | [N] | [N] | [e.g. agent instr + 1 skill load + 1 tool call] |
| Complex intent (routing + multi-step) | [N] | [N] | [N] | [e.g. classify → skill load → domain tool → next_action → second tool] |
| Multi-step turn (sequential skill loads) | [N] | [N] | [N] | [e.g. load skill A → replace with skill B — each load is a separate inference pass] |
| Multi-step completion turn | [N] | [N] | [N] | [e.g. domain tool + state tool + close tool] |
| Special first-turn handling | [N] | [N] | [N] | [if applicable] |

> Latency model: inference hop ≈ 500ms–2s; tool-call RTT ≈ 50ms–500ms; skill load ≈ 1 inference hop + token overhead. All estimates are approximations — production profiling required for exact values.

---

## Optimization Opportunity Inventory

> Opportunities are grouped by category. Tool execution opportunities first — they have the most direct latency impact.

### Tool Execution Architecture

#### PERF-1 — [Short title]

**Category:** Tool execution
**Severity:** [High / Medium / Low]
**Current cost:** [N] tool-call RTTs + [N] inference hops on [turn type] turns
**Frequency:** ~[N]% of all turns / every turn / [specific trigger condition]

**Evidence:**
> [Direct quote from agent instructions, skill body, or tool call sequence description]

**Root cause:** [Missing tool composition / missing agentic workflow / missing pre-invoke plugin / `next_action` dispatch chain not encapsulated]

**Recommendation:** [Python tool chain / agentic workflow wrap / pre-invoke plugin migration / tool composition]

**Mechanism:** [How this reduces latency — e.g. "eliminates 1 tool-call RTT on every turn by absorbing the classification tool's output into the prior tool response"; "wraps 3-step `next_action` chain into a single agentic workflow call, reducing 3 RTTs to 1"]

**Estimated impact:** [RTTs eliminated per turn type]; [inference hops eliminated]; ~[N]% of all turns affected

**Cross-report:** [OPT-N — also reduces ~N tokens per turn / REL-N — also resolves reliability signal / No cross-report overlap]

---

#### PERF-2 — [Short title]

[Same structure as PERF-1]

[Continue for all tool execution opportunities]

---

### Orchestration Depth

#### PERF-[N] — [Short title]

**Category:** Orchestration depth — [skill routing / collaborator stack / in-skill re-routing]
**Severity:** [High / Medium / Low]
**Current cost:** [N] extra inference hops per turn from [routing pattern]
**Frequency:** ~[N]% of turns / every intent turn

**Evidence:**
> [Quote or structural observation from agent YAML, skill body, or collaborators list]

**Root cause:** [Skill load required for every intent / over-decomposed collaborators / redundant in-skill re-route]

**Recommendation:** [Collapse into agent instructions / consolidate collaborators / replace re-route with inline rule]

**Mechanism:** [e.g. "collapsing high-frequency skill body into agent instructions eliminates 1 `load_skill` inference hop for those intents"; "merging 3 narrow collaborators into 1 broader collaborator with shared tool access eliminates 2 delegation hops"]

**Estimated impact:** [hops eliminated]; [turn types affected]; [% of total volume]

**Cross-report:** [OPT-N — also saves ~N tokens by eliminating redundant preamble / REL-N — also resolves reliability signal / No cross-report overlap]

---

[Continue for all orchestration depth opportunities]

---

### Guidelines Overhead

#### PERF-[N] — [Short title]

**Category:** Guidelines overhead
**Severity:** [High / Medium / Low]
**Current cost:** [N] guidelines × 1 constraint-check pass overhead per turn = [N] extra constraint evaluations on every turn
**Frequency:** Every turn

**Evidence:**
> [List guidelines that fall into the identified patterns — restating instructions, expressing tool-call logic, complex conditions]

**Root cause:** [Guidelines used for execution logic rather than behavioral guardrails / guidelines duplicate instruction rules / guidelines have complex multi-clause conditions]

**Recommendation:** [Move to instructions / move to tool schema / remove as duplicate / decompose into instruction rule]

**Mechanism:** [e.g. "removing 3 guidelines that duplicate instruction rules reduces per-turn constraint evaluation surface; the remaining 2 behavioral guardrails are appropriate guideline use"]

**Estimated impact:** [N] guidelines removed; constraint evaluation surface reduced from [N] to [N] per turn

**Cross-report:** [OPT-N — also saves ~N tokens / REL-N — also resolves Rule F signal / No cross-report overlap]

---

[Continue for all guidelines opportunities]

---

## Summary: Projected Savings

| Item | Category | Hops eliminated | RTTs eliminated | Turns affected | Cross-report |
|---|---|---:|---:|---|---|
| PERF-1: [title] | Tool execution | [N] | [N] | [turn types / % volume] | OPT-N / None |
| PERF-[N]: [title] | Orchestration | [N] | — | [turn types / % volume] | OPT-N / None |
| PERF-[N]: [title] | Guidelines | — | — | Every turn | OPT-N / None |
| **Total** | | **[N]** | **[N]** | | |

### Revised call-graph depth (post-optimization)

| Turn type | Current hops | Post-opt hops | Saving |
|---|---:|---:|---:|
| Simple intent | [N] | [N] | [N] hops |
| Complex intent | [N] | [N] | [N] hops |
| Multi-step turn (sequential skill loads) | [N] | [N] | [N] hops |
| [Other key turn types] | [N] | [N] | [N] hops |

---

## Implementation Priority

| Priority | Item | Category | Effort | Impact | Cross-report |
|---|---|---|---|---|---|
| **P1** | PERF-[N]: [title] | [category] | Low/Med/High | High — every turn / [N]% of turns | OPT-N / REL-N / None |
| **P2** | PERF-[N]: [title] | [category] | Low/Med/High | Medium | OPT-N / REL-N / None |
| [Continue] | | | | | |

> [1–2 sentences on delivery sequence. Note dependencies: tool composition changes (P1) typically need to be deployed before orchestration changes that depend on the composed tool's new return schema.]

---

## Tool Composition Candidates

List every tool chain that could be collapsed into a deterministic server-side pipeline. For each, name the component tools, the sequence, and the recommended composition pattern.

**Mechanism selection guide:**
- **`nextTool` chaining** (`_meta.nextTool`) — ≤5 steps, no conditional branches, all steps within a single Python MCP server, inputs flow forward without user interaction between steps. Each tool returns `_meta: { nextTool: { tool, parameters } }` to trigger the next step directly.
- **Agentic Workflow** (`@flow` / WxO Agentic Workflow JSON) — any of: >5 steps, conditional branches, parallel paths, cross-server tool calls, or anticipated future editability. The flow graph is the control plane; the LLM calls the entry node once.
- **Pre-invoke plugin** — for mandatory context hydration calls that must fire before every turn; removes the call from the LLM instruction path entirely.

| Chain | Component tools | Sequence type | Steps | Branches? | Single server? | Recommended mechanism |
|---|---|---|---|---|---|---|
| [chain name] | [tool-A → tool-B → tool-C] | [Sequential / conditional] | [N] | [Yes / No] | [Yes / No] | `nextTool` chaining / Agentic Workflow / Pre-invoke plugin |
| [Continue for each candidate] | | | | | | |

---

## Anti-Patterns to Avoid in Future Iterations

[List the specific anti-patterns found in this evaluation. For each, state what it is, where it appeared, and what latency overhead it created. If no anti-patterns were found, write: "No anti-patterns identified — the current design avoids all known execution overhead patterns."]

1. **[Anti-pattern name]** — [What it is, where it appeared, and what overhead it created]
2. [Continue for all found patterns]

---

*Side report — does not modify achievability scores in the main reports.*

*Issues found:* Implement the optimizations above and re-run with production profiling to validate latency impact. *No issues found:* No runtime performance optimization opportunities were identified by static analysis. Re-run this evaluation after any significant change to tool schemas, skill architecture, or guidelines.
```

---

## Template 6: Reliability Optimization Report

Use this structure for `reliability_optimization_report.md`. This report is **always produced** as part of every evaluation — it does not re-score the five evaluation dimensions.

**This is a synthesis report:** every REL-N item must trace back to evidence already present in the main agent report or skill reports. It does not introduce new findings; it reorganises existing findings into a prioritised, implementation-ready rewrite plan grouped by failure class.

**Relationship to other side reports:** When a REL-N fix also reduces token cost, cross-reference the corresponding `OPT-N` item from the token optimization report. When a fix also reduces hops, cross-reference `PERF-N` from the performance optimization report. Do not re-explain the full recommendation — a one-line cross-reference is sufficient.

**When no issues are found:** still produce the full report. Run the full Rule Q checklist, record "None found" for each pattern, and close with the standard baseline statement.

```markdown
# Reliability Optimization Report
## [Agent Name]

> Side report to: [agent_<name>_report.md](agent_<name>_report.md)
> See also: [token_optimization_report.md](token_optimization_report.md) · [performance_optimization_report.md](performance_optimization_report.md)
> Generated: [date]
> Scope: Systematic compliance failure patterns across agent instructions + [N] skill bodies

---

## Purpose

[1–2 sentences. State what systematic failure patterns were found and what their combined reliability impact is. If none were found, state that the evaluation confirms the current design avoids all known systematic failure patterns.]

---

## Current State Baseline

### Reliability Checklist

> Full checklist — every pattern checked regardless of outcome. Severity: Critical · High · Medium · Low · None found.

| Category | Pattern | Severity | Source |
|---|---|---|---|
| Implicit state | LLM-side attempt counter | [severity] | [agent report Finding N / skill report: skill-name] |
| Implicit state | Cross-turn "already asked" memory | [severity] | [source or "None found"] |
| Implicit state | Journey step tracking without `current_state` | [severity] | [source or "None found"] |
| Exact-phrase | Verbatim relay with backend hook | [severity] | [source or "None found"] |
| Exact-phrase | Prohibited-phrase enforcement LLM-side | [severity] | [source or "None found"] |
| Exact-phrase | Enum classification without tool | [severity] | [source or "None found"] |
| Scope/routing | Tense or phrasing-dependent routing boundary | [severity] | [source or "None found"] |
| Scope/routing | Subjective "last resort" fallback without exclusion list | [severity] | [source or "None found"] |
| Scope/routing | Overlapping skill descriptions | [severity] | [source or "None found"] |
| Conflicting rules | Same-turn dual-field distinction | [severity] | [source or "None found"] |
| Conflicting rules | Competing output format rules | [severity] | [source or "None found"] |
| Conflicting rules | Double-negative fill condition | [severity] | [source or "None found"] |
| Tool underspecification | Missing tool failure handling | [severity] | [source or "None found"] |
| Tool underspecification | Undeclared context variable | [severity] | [source or "None found"] |
| Tool underspecification | `next_action` no-match case missing | [severity] | [source or "None found"] |
| Skill body | Skill body exceeds followability threshold | [severity] | [source or "None found"] |
| Skill body | Multi-workflow skill (SK-1 Warn/Fail) | [severity] | [source or "None found"] |
| Skill body | Cross-skill state assumption (SK-4 Warn/Fail) | [severity] | [source or "None found"] |
| Workflow encoding | LLM-orchestrated multi-step chain (3+ steps, known transitions) | [severity] | [source or "None found"] |

---

## Optimization Opportunity Inventory

> Items ordered by severity (Critical → High → Medium → Low). Omit this section entirely and replace with "No reliability optimization opportunities identified." if the checklist above shows all "None found".

### REL-1 — [Short title]

**Category:** [Implicit state / Exact-phrase / Scope-routing / Conflicting rules / Tool underspecification / Skill body / Workflow encoding]
**Severity:** [Critical / High / Medium / Low]
**Current cost:** [What goes wrong, under what specific conditions — e.g. "On every voice channel first turn, the LLM may omit or corrupt the required prefix, causing the post-invoke plugin to skip personalisation silently"]
**Frequency:** [Fraction of production turns affected — e.g. "every voice call first turn", "~15% of cancellation turns", "rare — neutral-phrasing edge cases only"]

**Evidence:**
> [Direct quote from agent instructions or skill body] *(line N)*
> [Translation]: [English rendering — **required if not in English**]

**Root cause:** [Missing state object / Missing plugin / Missing tool contract / Overlapping descriptions / Competing rules — 1 sentence]

**Recommendation:** [Specific rewrite — what to change, where, and what the result looks like]

**Estimated impact:** [Same as Frequency above — what fraction of turns this fix improves, and how]

**Cross-report:** [OPT-N — also reduces ~N tokens / PERF-N — also eliminates N RTT / No cross-report overlap]

---

### REL-2 — [Short title]

[Same structure as REL-1]

[Continue for all items, Critical first]

---

## Summary: Projected Savings

> Ordered by severity — Critical and High items first. Phase 1 = Critical + High; Phase 2 = Medium; Phase 3 = Low.

| Priority | Item | Category | Effort | Impact | Cross-report |
|---|---|---|---|---|---|
| **P1** | REL-[N]: [title] | [category] | Low/Med/High | Critical/High — [turns affected] | OPT-N / PERF-N / None |
| **P2** | REL-[N]: [title] | [category] | Low/Med/High | Medium | OPT-N / PERF-N / None |
| **P3** | REL-[N]: [title] | [category] | Low/Med/High | Low | None |
| [Continue] | | | | | |

> [1–2 sentences on sequencing. Note that Phase 1 plugin migrations and tool contract changes are usually independent of each other and can be parallelised. State which items have dependencies.]

### Implementation Roadmap

**Phase 1 — Critical and High** (address before production scale)

| REL-N | Title | Change type | Effort | Cross-report |
|---|---|---|---|---|
| REL-[N] | [title] | [Plugin migration / Tool contract / Instruction rewrite / Skill split / State variable] | Low/Med/High | OPT-N / PERF-N / None |
| [Continue] | | | | |

**Phase 2 — Medium** (address before high-throughput load)

| REL-N | Title | Change type | Effort | Cross-report |
|---|---|---|---|---|
| REL-[N] | [title] | [change type] | Low/Med/High | OPT-N / PERF-N / None |

**Phase 3 — Low** (monitor; address in next iteration)

| REL-N | Title | Change type | Effort | Cross-report |
|---|---|---|---|---|
| REL-[N] | [title] | [change type] | Low/Med/High | OPT-N / PERF-N / None |

---

## Anti-Patterns to Avoid in Future Iterations

[List the specific anti-patterns found. For each, state what it is, where it appeared, and the failure mode it created. If none found, write: "No anti-patterns identified — the current design avoids all known systematic failure patterns."]

1. **[Anti-pattern name]** — [What it is, where it appeared, and what failure mode it created]
2. [Continue for all found patterns]

---

*Side report — does not modify achievability scores in the main reports. Every REL-N item traces back to evidence in the main reports.*

*Issues found:* Address Phase 1 items before production scale. Re-run the full evaluation after changes to confirm resolution. *No issues found:* No reliability optimization opportunities were identified by static analysis. Re-run this evaluation after any significant change to agent instructions, skill bodies, or tool schemas.
```

---

## Template 1 continued: Evaluation Harness Handoff (Agent Report)

The structured extraction object for the agent report. Add `"report_type": "agent"` to distinguish from skill harness files.

## Evaluation Harness Handoff

### Structured extraction object
```json
{
  "report_type": "agent",
  "artifact_type": "",
  "artifact_name": "",
  "scope": "full|partial",
  "evaluation_mode": "single-llm extraction + simple counting tool | direct analysis mode",
  "extraction_summary": {
    "semantic_extraction_performed_by": "running_llm",
    "simple_tool_or_harness_used": "",
    "incidents_extracted_before_scoring": [],
    "signals_derived": [],
    "missing_tool_coverage": []
  },
  "candidate_regions": [],
  "incidents": [
    {
      "category": "implicit_state_requirement",
      "quote": "",
      "reason": "",
      "confidence": "Low|Medium|High",
      "affected_dimensions": ["state_conflict_manageability"]
    }
  ],
  "signals": {
    "prompt_length_lines": 0,
    "prompt_length_category": "Short|Medium|Long|Very long",
    "critical_constraints": 0,
    "exact_phrase_requirements": 0,
    "exception_clauses": 0,
    "nested_conditional_branches": 0,
    "implicit_state_requirements": 0,
    "red_flag_state_phrases": [],
    "subjective_classifiers": [],
    "tool_required_behaviors_missing_details": 0,
    "hard_conflicts": 0
  },
  "runtime_performance_risk": {
    "token_overhead_risk": "Low|Medium|High",
    "reasoning_overhead_risk": "Low|Medium|High",
    "tool_call_overhead_risk": "Low|Medium|High",
    "retry_repair_loop_risk": "Low|Medium|High",
    "latency_variance_risk": "Low|Medium|High",
    "skill_load_overhead_risk": "Low|Medium|High|N/A",
    "skill_performance_surface": {
      "skill_count": {"value": 0, "risk": "Low|Medium|High"},
      "per_skill_body_size_max_lines": {"value": 0, "risk": "Low|Medium|High"},
      "per_skill_body_size_avg_lines": {"value": 0, "risk": "Low|Medium|High"},
      "routing_ambiguity_candidates_per_turn": {"value": 0, "risk": "Low|Medium|High"},
      "multi_skill_turns_pct": {"value": 0, "risk": "Low|Medium|High"},
      "reload_frequency_confirmed": {"value": false, "risk": "Low|Medium"},
      "combined_token_cost_estimate": {"value": 0, "risk": "Low|Medium|High"},
      "overall_skill_load_overhead": "Low|Medium|High|N/A"
    },
    "correlated_skill_pairs": [
      {
        "skill_a": "",
        "skill_b": "",
        "correlation_type": "shared_tools|adjacent_intents|cross_body_reference",
        "shared_tools": [],
        "consolidation_recommended": true,
        "consolidation_reason": ""
      }
    ],
    "main_drivers": [],
    "performance_interpretation": ""
  },
  "skill_health": {
    "skills": [
      {
        "name": "",
        "sk1_single_responsibility": {"rating": "Pass|Warn|Fail", "workflows_count": 0, "note": ""},
        "sk2_non_overlapping": {"rating": "Pass|Warn|Fail", "overlap_pairs": [], "note": ""},
        "sk3_routing_clarity": {"rating": "Pass|Warn|Fail", "has_intent_coverage": true, "has_boundary_conditions": true, "note": ""},
        "sk4_no_cross_dependencies": {
          "rating": "Pass|Warn|Fail",
          "dependencies_found": [],
          "dependency_loop_detected": false,
          "loop_cycle": [],
          "note": ""
        },
        "sk5_complexity": {
          "rating": "Pass|Warn|Fail",
          "lines": 0,
          "nested_branches": 0,
          "active_rules_per_turn": 0,
          "exact_phrases": 0,
          "implicit_state_vars": 0,
          "note": ""
        },
        "sk6_correlation": {"rating": "Pass|Warn|Fail", "correlated_with": [], "consolidation_recommended": false, "note": ""},
        "sk7_perf_surface": {"rating": "Pass|Warn|Fail", "body_lines": 0, "estimated_tokens": 0, "note": ""}
      }
    ],
    "overlap_pairs": [
      {"skill_a": "", "skill_b": "", "overlap_rating": "Exact|High|Moderate|Low", "evidence": ""}
    ],
    "consolidation_recommendations": [
      {"skills": [], "suggested_name": "", "reason": "", "performance_implication": "", "merge_strategy": ""}
    ]
  },
  "dimension_scores": {
    "task_understanding": {"score": 0, "confidence": "Low", "evidence": [], "signals": []},
    "scope_applicability": {"score": 0, "confidence": "Low", "evidence": [], "signals": []},
    "execution_tool_grounding": {"score": 0, "confidence": "Low", "evidence": [], "signals": []},
    "instruction_followability": {"score": 0, "confidence": "Low", "evidence": [], "signals": []},
    "state_conflict_manageability": {"score": 0, "confidence": "Low", "evidence": [], "signals": []}
  },
  "findings": []
}
```

### Harness notes
- Preserve deterministic signal counts exactly as summarized from accepted incidents
- Use deterministic signals to **bound** judgment, not replace it
- Do not fabricate counts
- If a signal cannot be determined confidently, mark it as `unknown` and explain why
- The running LLM should extract **evidence-backed incidents**
- The simple tool should count, deduplicate, cluster, validate, or render those incidents
- Do not require the simple tool to call another LLM
```

## Section Guidelines

### Report set discipline
- Save each report to disk immediately after it is fully written. Do not hold all reports in memory and write them together.
- The agent report must be written before skill reports, because it establishes cross-skill context (SK-2, SK-6, SK-7). Skill reports are independent of each other and may be written in any order.
- The index is written last, after all individual reports are complete, because it references their verdicts and scores.
- If saving to disk is not possible in the current environment, output each report as a labelled block in chat (agent report first, then each skill report, then the index), making clear that each block is a separate file.

### Artifact Summary
Keep this concise. The overall verdict should be 1-2 sentences maximum. For skill reports, include the skill name and its parent agent in the summary.

### Extraction and Tool Summary
Be honest about the analysis mode. If no tool was used, say so clearly and explain the confidence impact. For skill reports, list the `allowed-tools`, `scripts/`, and `references/` counts explicitly — these are the tool grounding surface for the skill.

### Dimension Scorecard
This is a quick-reference table. Keep entries brief. Full details go in Dimension Analysis section. Scores in skill reports are scoped to the skill body only — do not blend agent-level context.

### Deterministic Signal Summary
Provide actual counts, not ranges. If you cannot count confidently, say "unknown" and explain why. For skill reports, count signals in the SKILL.md body exclusively (do not include agent instructions counts).

### Overall Interpretation
Use qualitative interpretation bands:
- Very high-risk / Not achievable as written (any dimension 0-1)
- High-risk (two or more dimensions ≤2)
- Moderate-risk (mixed scores, some fragility)
- Low-risk (most dimensions 3-4, targeted improvements needed)
- Strong (all dimensions 4-5)

### Dimension Analysis
Provide full reasoning for each score. Quote evidence. Explain why the score is what it is, not just what the score means.

**Special note for Execution & Tool Grounding:** If tools are referenced in the prompt but their formal definitions (schemas, APIs, specifications) were not included in the evaluation input, explicitly note this limitation in the dimension analysis. State that the score reflects only what could be assessed from the prompt text, and recommend that the user include tool definitions and re-run the evaluation for a complete assessment. Example language: "Note: This evaluation is based solely on tool references in the prompt. Tool definitions (schemas, APIs, specifications) were not provided. For a complete assessment of tool grounding, include formal tool definitions and re-run this evaluation."

**For skill reports:** Also check whether all tools referenced in the SKILL.md body are present in the skill's `allowed-tools`. A tool mentioned in the body but absent from `allowed-tools` is an execution gap — call this out explicitly in Dimension 3.

### Findings
Each finding must have all five elements: Evidence, Why it matters, Deterministic or judgment-based, Score impact, Recommended change. In skill reports, findings should reference the specific SKILL.md body line or section where the issue appears. Do not repeat agent-level findings in skill reports — the skill report covers only the skill body.

**Translation requirement (mandatory):** Every non-English quote in an Evidence block must be followed immediately by a `[Translation]: ...` line containing the English rendering. Do not skip this even for short phrases or when the meaning seems obvious. The reviewer may not read the source language.

### Key Risks
Focus on production failure modes, not theoretical concerns.

### High-Impact Changes
Prioritize by leverage: changes that improve multiple dimensions or address critical blockers.

### Rewrite Targets
Point to specific sections, line numbers, or rule bundles that contain the highest concentration of issues. For each target, describe what problems exist and suggest a rewrite strategy (approach/direction) without prescribing exact outcomes or specific line counts.

### Skill Reports (agent report section)
List every resolved skill with a relative Markdown link. List unresolved skills by name with a note explaining why they could not be resolved. This section makes the agent report the navigation entry point for the full report set.

### Runtime Performance Risk — Skill sections (agent report only)
The skill architecture performance surface table must be filled in whenever `skills:` are present, even if all components rate Low. Omit only when the agent has no `skills:` list at all. The correlated pairs table should only appear when at least one pair meets a Rule M trigger.

For skill reports, the Runtime Performance Risk section covers only the cost of loading and reasoning over this skill body — not the full agent architecture overhead. Do not include the skill architecture performance surface table in skill reports.

### Skill Health — This Skill (skill reports only)
SK-2, SK-6, and SK-7 are cross-skill checks and belong in the agent report only. Skill reports contain SK-1, SK-3, SK-4, and SK-5 for the skill in question. Do not attempt to assess SK-2/SK-6/SK-7 in isolation inside a skill report — they require the full skill set to be meaningful.

### Skill Health Summary (agent report only)
Place this section immediately after Dimension Analysis and before Findings in the agent report. The summary table uses P/W/F codes — full analysis is in per-skill reports. Agent dimension adjustments apply only for SK-2 Exact/High overlap, SK-3 hard-limit failures, and SK-6 tool-binding shadows. Consolidation recommendations must include a concrete merge strategy: which `allowed-tools` to carry forward, how to combine the body sections, what to do with the `description` frontmatter.

### Token Optimization Report
This report is always produced — it synthesizes evidence gathered across the agent report and all skill reports. Produce it after all individual reports are written. Run the full Rule O checklist and record a severity (High / Medium / Low / None found) for each pattern. When no issues are found, record the current token budget as a verified baseline and close with the standard baseline statement; do not produce an empty file. Follow Template 4.

### Performance Optimization Report
This report is always produced — focused on execution call-graph depth, tool composition, orchestration layers, and guidelines overhead. Produce it after the token optimization report so it can cross-reference Rule O items for dual-benefit opportunities. Run the full Rule P checklist and record a severity for each pattern. When no issues are found, record the current call-graph baseline and close with the standard baseline statement; do not produce an empty file. Follow Template 5.

### Reliability Optimization Report
This report is always produced — a synthesis of findings from the main evaluation reports reorganised into a prioritised, implementation-ready rewrite plan grouped by failure class. Produce it last among the three side reports (after token and performance) so it can cross-reference both OPT-N and PERF-N items. Every REL-N item must trace back to evidence in the main reports — do not introduce new findings. Run the full Rule Q checklist and record a severity for each pattern. When no issues are found, record a stability baseline and close with the standard statement; do not produce an empty file. Follow Template 6. The three side reports are siblings — flag cross-report overlaps with one-line cross-references but do not merge the reports.

### Index
The index is a navigation and summary document, not an analysis document. Keep it brief. Every report file in the eval/ directory must appear in the Report Set table. The Skill Health Summary table uses single-letter codes (P/W/F) for space; the full ratings are in the individual reports. The `rules-summary.md`, `token_optimization_report.md`, `performance_optimization_report.md`, and `reliability_optimization_report.md` files must always be present in the eval/ directory and linked from the index's Reference Documents section. For the three side reports, the one-line description should indicate whether issues were found (summarise the top result) or none were found (state "baseline recorded").

### Evaluation Harness Handoff
Both agent and skill JSON files must include `"report_type": "agent"` or `"report_type": "skill"` as the first key to make them machine-distinguishable. The agent JSON must include `skill_health` whenever skills are evaluated. The skill JSON must include `skill_health_this_skill` with only SK-1/SK-3/SK-4/SK-5. Omit the `skill_health` key from skill reports entirely.