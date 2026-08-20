# Report Template Structure

This file defines three templates that together form the **report set** produced for every evaluation:

1. **Agent report** — scores the main agent instructions; contains the Skill Health Assessment (cross-skill) and links to skill reports
2. **Skill report** — scores one skill's `SKILL.md` body; links back to the agent report
3. **Index** — one-page manifest summarising the full set

**Filename conventions** (all files go in `eval/` relative to the agent YAML's directory):
- `agent_<name>_report.md` / `agent_<name>_report_harness.json`
- `skill_<skill-name>_report.md` / `skill_<skill-name>_report_harness.json`
- `index.md`

Each report is saved to disk as soon as it is complete. Skill reports are produced in **batches of at most 2 at a time** — complete and save 2 skill reports before starting the next pair. Do not evaluate all skills in parallel.

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
| Multi-skill turns (% of intents spanning ≥2 skills) | [~N%] | [Low / Medium / High] |
| Re-load frequency (confirmed multi-load per turn) | [Yes / No] | [Medium if Yes / Low if No] |
| Combined token cost (tokens loadable in one turn) | [~N tokens] | [Low / Medium / High] |
| **Overall skill-load overhead** | | **[Low / Medium / High]** |

### Correlated skill pairs (omit if none found)
| Skill A | Skill B | Correlation type | Consolidation recommended? |
|---|---|---|---|
| [skill-name] | [skill-name] | [Shared tools: X, Y / Adjacent intents / Cross-body reference] | [Yes — reason / No] |

### Performance interpretation
[Short paragraph explaining whether instruction complexity is likely to increase runtime cost, latency, tool-call count, or response variance. Distinguish deterministic evidence from judgment-based conclusions. When skills are present, include: expected per-turn skill-load cost, whether correlated pairs are likely to co-load, and whether the skill architecture as a whole adds measurable latency overhead.]

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

## Skill Health Assessment (omit section if no skills)

### Skill Health Table
| Skill | SK-1 Single Resp. | SK-2 Non-Overlap | SK-3 Routing Clarity | SK-4 No Cross-Dep. | SK-5 Complexity | SK-6 Correlation | SK-7 Perf. Surface |
|---|---|---|---|---|---|---|---|
| [skill-name] | [Pass/Warn/Fail — note] | [Pass/Warn/Fail — note] | [Pass/Warn/Fail — note] | [Pass/Warn/Fail — note] | [Pass/Warn/Fail — note] | [Pass/Warn/Fail — note] | [Pass/Warn/Fail — note] |

**Rating guide:**
- **Pass**: No issue detected
- **Warn**: Potential issue; monitor or improve before production scale
- **Fail**: Definite issue that will cause reliability or performance problems at production load

### Cross-skill overlap pairs (SK-2)
| Skill A | Skill B | Overlap rating | Evidence |
|---|---|---|---|
| [skill-name] | [skill-name] | [Exact/High/Moderate/Low] | [quoted text from both descriptions] |

### Consolidation recommendations (SK-6)
For each pair meeting the consolidation trigger threshold:

**[Skill A] + [Skill B] → consolidate into [suggested-name]**
- **Why**: [shared tools / overlapping intents / cross-body references — cite evidence]
- **Performance implication**: Loading both skills adds ~[N] lines of instruction and [N] tokens to the active context. For a workload of [N] turns/hour where [X%] require both skills, this adds [estimate] overhead per hour.
- **How to consolidate**: [Describe the merge strategy: keep the stricter `allowed-tools` union, merge the body sections, deduplicate rules, update the `description` to cover both intent sets and their combined boundary conditions]

### Skill health findings
[For any Warn or Fail rating, produce a full finding using the standard finding structure: Evidence, Why it matters, Deterministic or judgment-based, Score impact, Recommended change. Link each finding back to its SK criterion and Rule letter.]

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
- Skill name: [name from frontmatter]
- Skill file: [relative path to SKILL.md]
- Agent: [agent name]
- Evaluation scope: [full | partial]
- Evaluation mode: [Enhanced Mode | Direct Analysis Mode | Partial Skill Mode]
- Overall verdict: [brief summary of this skill's achievability]

## Extraction and Tool Summary
- Skill body length: [line count] lines
- allowed-tools count: [N]
- scripts/ files: [list or "none"]
- references/ files: [list or "none"]
- WXO.yaml present: [Yes / No]
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
- **SK-4 No Cross-Skill Dependencies**: [Pass / Warn / Fail] — [evidence: any references to prior skill state or exclusively-owned tools of another skill?]; dependency loop detected: [Yes — cycle: skill-A → skill-B → skill-A / No]
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

- [rules-summary.md](rules-summary.md) — Evaluation rules reference (Rules A–N, scoring dimensions, interpretation bands)

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

### Skill Health Assessment (agent report only)
Place this section immediately after Dimension Analysis and before Findings in the agent report. Each row in the Skill Health Table must have a brief but specific evidence note — do not write "N/A" without explanation. Consolidation recommendations must include a concrete merge strategy: which `allowed-tools` to carry forward, how to combine the body sections, what to do with the `description` frontmatter.

### Index
The index is a navigation and summary document, not an analysis document. Keep it brief. Every report file in the eval/ directory must appear in the Report Set table. The Skill Health Summary table uses single-letter codes (P/W/F) for space; the full ratings are in the individual reports. The `rules-summary.md` file must be present in the eval/ directory and linked from the index's Reference Documents section.

### Evaluation Harness Handoff
Both agent and skill JSON files must include `"report_type": "agent"` or `"report_type": "skill"` as the first key to make them machine-distinguishable. The agent JSON must include `skill_health` whenever skills are evaluated. The skill JSON must include `skill_health_this_skill` with only SK-1/SK-3/SK-4/SK-5. Omit the `skill_health` key from skill reports entirely.