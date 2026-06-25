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

<Steps>
<Step>
**Gather all relevant data**

Before beginning analysis, collect all available metadata and context:

1. **Extract agent metadata** (if evaluating a YAML file):
   ```bash
   python scripts/extract_agent_info.py <agent.yaml> --json
   ```
   This provides: name, description, collaborators, tools, context variables, guidelines
   - Tool: [`extract_agent_info.py`](scripts/extract_agent_info.py)

2. **Extract tool metadata** for each referenced tool or agent collaborator:
   - For Python-based tools and JSON-based tools: `python scripts/extract_tool_info.py <tool.py|tool.json>`
   
   This provides: tool signatures, parameters, return types, descriptions
   - Tool: [`extract_tool_info.py`](scripts/extract_tool_info.py)

3. **Identify missing tool definitions**: Note which tools/collaborators are referenced but not available for inspection

4. **Organize the data**: Create a complete picture of:
   - What the agent instructions say
   - What tools are actually available
   - What parameters those tools accept
   - What context variables exist
   - What guidelines constrain behavior

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

**Counting rules for YAML:**
- **Prompt length**: Count only the lines in the `instructions:` field (exclude YAML structure, metadata, and guidelines)
- **Critical constraints**: Count MUST/NEVER/ALWAYS/EXACTLY in both `instructions:` and `guidelines:` sections
- **Nested conditionals**: Count if/then branches in `instructions:` plus each guideline's condition→action pair
- **Tool-required behaviors**: Sum of collaborators + tools (e.g., 12 collaborators + 1 tool = 13 tool-required behaviors)
- **Exact phrases**: Count "Respond exactly:", "Say:", and similar requirements in `instructions:` and `guidelines:`

**Important:** Use the utility scripts ([`extract_agent_info.py`](scripts/extract_agent_info.py), [`extract_tool_info.py`](scripts/extract_tool_info.py)) to extract tool metadata before scoring the "Execution & Tool Grounding" dimension. If tools/collaborators are referenced but their formal definitions cannot be extracted (file not found, unsupported format), note this as a limitation. The evaluation can proceed, but recommend that the user provide tool definitions and re-run the evaluation for a complete assessment.
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

Document the analysis mode in the report:
- **Enhanced Mode**: Used utility scripts to extract agent and tool metadata
- **Direct Analysis Mode**: Manual analysis only (no tool metadata available)
</Step>

<Step>
**Score five dimensions**
Evaluate the artifact across these dimensions using the scoring rubrics in [`dimension-definitions.md`](dimension-definitions.md):

1. **Task Understanding** (0-5): Can the agent understand its primary job?
2. **Scope & Applicability** (0-5): Does the agent know when the instruction applies?
3. **Execution & Tool Grounding** (0-5): Can the required behavior be executed with available tools?
4. **Instruction Followability** (0-5): Can an LLM realistically follow all constraints at once?
5. **State & Conflict Manageability** (0-5): Does the prompt require hidden state tracking or conflicting rules?

Apply the deterministic signal rules from [`signal-rules.md`](signal-rules.md) to bound your judgment.
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
**Produce the report artifacts**
Generate two artifacts:

1. **Markdown report:** Complete evaluation report using the structure defined in [`report-template.md`](report-template.md). The report must be directly saveable as a file.
   - **Default filename:** `agent_prompt_achievability_report.md`

2. **JSON harness handoff:** Structured extraction object for automated harness integration.
   - **Default filename:** `agent_prompt_achievability_report_harness.json`
   - Contains all signals, incidents, dimension scores, and findings in machine-readable format

Save both files if the environment supports it. Otherwise, output the complete markdown content and JSON separately.
</Step>
</Steps>

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
- [`dimension-definitions.md`](dimension-definitions.md): Complete scoring rubrics for all five dimensions
- [`signal-rules.md`](signal-rules.md): Deterministic rules to reduce subjectivity (Rules A-D)
- [`report-template.md`](report-template.md): Required report structure and section order
- [`example-finding.md`](example-finding.md): Sample finding with all required elements

## Output Requirements

**Every evaluation must produce:**
1. A complete markdown report artifact (not just scores or bullet points)
2. A separate JSON harness handoff file for automated integration
3. Per-dimension scores with confidence levels (do not compute weighted averages)
4. Extraction and tool summary explaining the analysis mode
5. Deterministic signal summary with counts
6. At least 3-5 detailed findings with evidence and recommendations
7. Key risks and high-impact changes sections

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
