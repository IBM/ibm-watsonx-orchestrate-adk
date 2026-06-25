# Agent Instructions Evaluator

Evaluate agent instructions or agent definitions for operational achievability in production settings. This skill focuses on runtime reliability and runtime efficiency rather than writing quality, identifying issues from hidden state, conflicting rules, vague scope, brittle exact phrasing, underspecified tool behavior, instruction overload, and performance friction caused by excessive or contradictory runtime reasoning.

## What This Skill Does

Produces a structured, evidence-backed evaluation report with:
- Per-dimension scores (0-5 scale) across 5 evaluation dimensions
- Deterministic signal counts (exact phrases, nested branches, implicit state, etc.)
- Detailed findings with evidence, impact analysis, and specific recommendations
- Key risks and high-impact changes prioritized by leverage
- Structured JSON for integration with evaluation harnesses
- Runtime performance risk assessment covering token overhead, reasoning overhead, tool-call overhead, retry-loop risk, and latency variance

## Important Notes on Evaluation

**Model Interpretation:** Evaluations are subject to interpretation by different LLM models. For best results, use a **coding agent with access to a frontier model** (e.g., IBM Bob, Claude 4.5 Sonnet, GPT-5.x, or equivalent) to run the evaluation, as coding agents have tool access and stronger reasoning capabilities for nuanced analysis.

**Using the Report:** The evaluation report is provided **as-is** and should be used as a **guide to improve agent instructions** rather than treated as an absolute score. Different models may score the same instructions differently based on their interpretation. Focus on the evidence-backed findings and recommendations to iteratively improve your agent's operational reliability.

## Core Principle

Score the artifact not by how much behavior it describes, but by how much behavior the agent can reliably execute. More rules do not automatically make a better prompt—more rules often lower achievability.

**Reliability and performance are coupled.** Instructions that are hard to follow are often also expensive to execute.

## Five Evaluation Dimensions

1. **Task Understanding** (0-5): Can the agent understand its primary job?
2. **Scope & Applicability** (0-5): Does the agent know when the instruction applies?
3. **Execution & Tool Grounding** (0-5): Can the required behavior be executed with available tools?
4. **Instruction Followability** (0-5): Can an LLM realistically follow all constraints at once?
5. **State & Conflict Manageability** (0-5): Does the prompt require hidden state tracking or conflicting rules?

## Utility Scripts

The `scripts/` directory (relative to this skill) contains utility scripts for enhanced evaluation capabilities.

> **Path note:** `scripts/` is relative to the skill directory (`skills/agent-instructions-evaluator/`), not the top-level workspace root.

### extract_agent_info.py

Extracts metadata from watsonx Orchestrate agent YAML files. Used to inspect collaborator definitions, available tools, and context variables before scoring.

```bash
python scripts/extract_agent_info.py path/to/agent.yaml --json
```

### extract_tool_info.py

**Unified tool extractor** — auto-detects `.py`, `.json`, and `.yaml`/`.yml` tool files. Used to verify tool signatures, parameters, and return types referenced in agent instructions.

```bash
python scripts/extract_tool_info.py path/to/tool.py --json
```

Supported formats auto-detected by file extension and content:
- **`.py`** — `@tool` decorator → regular Python tool; `@flow` decorator → Python flow tool
- **`.json`** — `spec.kind == "flow"` → WxO Agentic Workflow; `data.nodes` (list) → Langflow workflow
- **`.yaml/.yml`** — `kind: knowledge_base` → WxO Knowledge Base; `kind: mcp` → MCP Toolkit

See [`scripts/README.md`](scripts/README.md) for complete documentation.

**Requirements:**
```bash
pip install -r scripts/requirements.txt
```

## How to Use This Skill

### Sample Utterances

**Basic evaluation:**
```
Use the agent-instructions-evaluator skill to evaluate the instructions in 'agents/customer_service_agent.yaml'
```

**Evaluate a system prompt:**
```
Evaluate the agent prompt in 'prompts/investment_assistant.md' using the agent-instructions-evaluator skill
```

**Evaluate instructions from a file:**
```
Use agent-instructions-evaluator to analyze the instructions in 'docs/agent_spec.txt' and create a report
```

**Evaluate and save report:**
```
Run agent-instructions-evaluator on 'agents/support_bot.yaml' and save the report as 'support_bot_evaluation.md'
```

### What the Skill Accepts

- Raw system prompts
- Instruction blocks for agents
- watsonx Orchestrate native agent YAML files
- External agent definitions
- Design documents describing agent behavior
- Partial excerpts from larger prompts or policies

## Interpretation Bands

- **Very high-risk / Not achievable** → Any dimension 0-1
- **High-risk** → Two or more dimensions ≤2
- **Moderate-risk** → Mixed scores, some fragility
- **Low-risk** → Most dimensions 3-4, targeted improvements needed
- **Strong** → All dimensions 4-5

## Key Signal Thresholds

| Signal | Risk Threshold | Impact |
|--------|---------------|---------|
| Exact phrases | >10 | High brittleness (Rule B) |
| Nested branches | >20 | Workflow navigation errors (Rule C) |
| Implicit state vars | >2 | State tracking failures (Rule A) |
| Subjective classifiers | >7 | Inconsistent routing |
| Hard conflicts | Any | Critical - agent violates rules |
| Tool gaps | Any | Execution failures (Rule D) |
| Prompt length | >150 lines | Attention drift + token overhead risk (Rules E, F) |
| Interacting constraints | High concentration | Performance friction, latency variance (Rule F) |

## Files in This Skill

- **[`SKILL.md`](SKILL.md)** - Complete skill definition and evaluation methodology
- **[`dimension-definitions.md`](dimension-definitions.md)** - Detailed scoring rubrics for all five dimensions
- **[`signal-rules.md`](signal-rules.md)** - Deterministic rules (A-F) to reduce subjectivity
- **[`report-template.md`](report-template.md)** - Required report structure and section order
- **[`example-finding.md`](example-finding.md)** - Sample finding with all required elements

## Example Reports

- [AskHR Agent Evaluation](../../../multi-agent-askhr/askhr_agent_achievability_evaluation_report.md)
- [Banco Inter Investment Assistant Evaluation](../../../agent-prompt-eval/private_tests/banco_der_achievability_evaluation_report.md)

## Design Philosophy

**Evaluate operational achievability, not writing quality.**

- Focus on runtime reliability, not academic elegance
- Separate deterministic signals from judgment
- Prefer per-dimension truth over averaged scores
- Be evidence-based: quote concrete lines, don't fabricate
- Be operational: focus on production failure modes
- Prioritize high-leverage fixes that improve multiple dimensions
- **Reliability and performance are coupled.** Instructions that are hard to follow are often also expensive to execute.