# Report Template Structure

Use this exact structure and section order for all evaluation reports.

```markdown
# Agent Prompt Achievability Evaluation Report

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

## Findings

### Finding 1: [Short descriptive title]
**Evidence**
> [Direct quote from input]
> [Another quote if relevant]

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

## Evaluation Harness Handoff

### Structured extraction object
```json
{
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

### Artifact Summary
Keep this concise. The overall verdict should be 1-2 sentences maximum.

### Extraction and Tool Summary
Be honest about the analysis mode. If no tool was used, say so clearly and explain the confidence impact.

### Dimension Scorecard
This is a quick-reference table. Keep entries brief. Full details go in Dimension Analysis section.

### Deterministic Signal Summary
Provide actual counts, not ranges. If you cannot count confidently, say "unknown" and explain why.

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

### Findings
Each finding must have all five elements: Evidence, Why it matters, Deterministic or judgment-based, Score impact, Recommended change.

### Key Risks
Focus on production failure modes, not theoretical concerns.

### High-Impact Changes
Prioritize by leverage: changes that improve multiple dimensions or address critical blockers.

### Rewrite Targets
Be specific. Point to exact sections, line numbers, or rule bundles that should be rewritten first.

### Evaluation Harness Handoff
The JSON object should be valid and complete. It serves as a data contract for automated harness integration.