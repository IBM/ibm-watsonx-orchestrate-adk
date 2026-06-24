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

Evaluate agent instructions or agent definitions for operational achievability in production settings. This skill focuses on runtime reliability rather than writing quality, identifying issues from hidden state, conflicting rules, vague scope, brittle exact phrasing, underspecified tool behavior, or instruction overload.

**Use this skill when you need:**
- A practical evaluation report focused on runtime reliability
- Evidence-backed prompt review with concrete recommendations
- A reusable report artifact that can be shared with reviewers
- Per-dimension scoring that preserves nuance rather than averaging away critical issues

## Core Principle

Score the artifact not by how much behavior it describes, but by how much behavior the agent can reliably execute. More rules do not automatically make a better prompt—more rules often lower achievability.

## Evaluation Workflow

### Step 1: Understand the input
Accept any of these input types:
- Raw system prompt
- Instruction block for an agent
- watsonx Orchestrate native agent YAML
- External agent definition
- Design document describing agent behavior
- Partial excerpt from a larger prompt or policy

If the input is partial, state that the evaluation scope is partial and score only what is visible.

**Important:** If tools are referenced in the prompt but their formal definitions (schemas, APIs, specifications) are not included in the evaluation input, note this as a limitation in the "Execution & Tool Grounding" dimension. The evaluation can proceed, but recommend that the user include tool definitions and re-run the evaluation for a complete assessment of tool grounding.

### Step 2: Extract evidence (Direct Analysis Mode)
Since no automated extraction tool is available, manually identify and count:
- Exact phrase requirements
- Nested conditional branches
- Implicit state requirements
- Critical constraints (MUST, NEVER, ALWAYS, EXACTLY, etc.)
- Exception clauses
- Subjective classifiers
- Tool-required behaviors
- Hard conflicts between rules

Mark the report as **Direct Analysis Mode** and note that all counts were performed manually by the running LLM.

### Step 3: Score five dimensions
Evaluate the artifact across these dimensions using the scoring rubrics in `dimension-definitions.md`:

1. **Task Understanding** (0-5): Can the agent understand its primary job?
2. **Scope & Applicability** (0-5): Does the agent know when the instruction applies?
3. **Execution & Tool Grounding** (0-5): Can the required behavior be executed with available tools?
4. **Instruction Followability** (0-5): Can an LLM realistically follow all constraints at once?
5. **State & Conflict Manageability** (0-5): Does the prompt require hidden state tracking or conflicting rules?

Apply the deterministic signal rules from `signal-rules.md` to bound your judgment.

### Step 4: Generate findings
For each major issue identified, create a finding with:
- **Evidence**: Direct quotes from the input
- **Why it matters**: Operational impact explanation
- **Deterministic or judgment-based**: Classification of the finding
- **Score impact**: Which dimensions are affected and how
- **Recommended change**: Specific, actionable fix

### Step 5: Produce the report artifact
Generate a complete markdown report using the structure defined in `report-template.md`. The report must be directly saveable as a file.

**Default filename:** `agent_prompt_achievability_report.md`

Save the report as a file if the environment supports it. Otherwise, output the complete markdown content.

## Key Evaluation Rules

**Be evidence-based:**
- Quote or paraphrase concrete lines from the input
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
- `dimension-definitions.md`: Complete scoring rubrics for all five dimensions
- `signal-rules.md`: Deterministic rules to reduce subjectivity (Rules A-D)
- `report-template.md`: Required report structure and section order
- `example-finding.md`: Sample finding with all required elements

## Output Requirements

**Every evaluation must produce:**
1. A complete markdown report artifact (not just scores or bullet points)
2. Per-dimension scores with confidence levels (do not compute weighted averages)
3. Extraction and tool summary explaining the analysis mode
4. Deterministic signal summary with counts
5. At least 3-5 detailed findings with evidence and recommendations
6. Key risks and high-impact changes sections
7. Structured JSON extraction object for harness handoff

**The report must be:**
- Specific and evidence-backed
- Structured and complete
- Practical for prompt redesign
- Suitable for sharing with prompt engineers, agent builders, or reviewers
- Directly saveable as a markdown file without rewriting
