# Agent Instructions Evaluator

Evaluate agent instructions or agent definitions for operational achievability in production settings. This skill focuses on runtime reliability and runtime efficiency rather than writing quality, identifying issues from hidden state, conflicting rules, vague scope, brittle exact phrasing, underspecified tool behavior, instruction overload, performance friction caused by excessive or contradictory runtime reasoning, and — when the agent uses **skills** — skill architecture problems such as overlapping scope, cross-skill dependencies, dependency loops, and excessive context-load overhead.

## What This Skill Does

Produces a structured, evidence-backed **report set** saved as individual files:

| File | Contents |
|---|---|
| `instructions_eval/index.md` | Manifest of all reports with verdicts and Skill Health summary |
| `instructions_eval/agent_<name>_report.md` | Agent-level analysis across 5 dimensions + Skill Health Assessment |
| `instructions_eval/agent_<name>_report_harness.json` | Machine-readable JSON for harness integration |
| `instructions_eval/skill_<name>_report.md` | Per-skill analysis — one file per resolved skill |
| `instructions_eval/skill_<name>_report_harness.json` | Per-skill JSON harness |

Each report is written to disk as soon as its analysis is complete — **save-as-you-go**, not batched.

**Every agent report includes:**
- Per-dimension scores (0–5) across 5 evaluation dimensions with confidence levels
- Deterministic signal counts (exact phrases, nested branches, implicit state, etc.)
- Detailed findings with evidence quotes (line numbers + English translation where needed), impact, and specific recommendations
- Key risks and high-impact changes prioritised by leverage
- Runtime performance risk (token, reasoning, tool-call, retry-loop, latency variance)
- Skill Health Assessment table (SK-1 through SK-7) when skills are present
- Consolidation recommendations and skill architecture performance surface

**Each skill report includes:**
- Full 5-dimension analysis of the skill's `SKILL.md` body
- SK-1, SK-3, SK-4, SK-5 deep analysis (single responsibility, routing clarity, dependencies, complexity)
- Runtime performance risk scoped to that skill body
- Back-link to the agent report

## Important Notes on Evaluation

**Model Interpretation:** Evaluations are subject to interpretation by different LLM models. For best results, use a **coding agent with access to a frontier model** (e.g., IBM Bob, Claude Sonnet, GPT-4o, or equivalent) with tool access and strong reasoning capabilities.

**Using the Report:** The evaluation report is provided **as-is** and should be used as a **guide to improve agent instructions** rather than an absolute score. Focus on the evidence-backed findings and recommendations to iteratively improve your agent's operational reliability.

## Core Principle

Score the artifact not by how much behavior it describes, but by how much behavior the agent can reliably execute. More rules do not automatically make a better prompt — more rules often lower achievability.

**Reliability and performance are coupled.** Instructions that are hard to follow are often also expensive to execute.

## Five Evaluation Dimensions

Applied to both agent instructions and each skill's `SKILL.md` body independently:

1. **Task Understanding** (0-5): Can the agent understand its primary job?
2. **Scope & Applicability** (0-5): Does the agent know when the instruction applies?
3. **Execution & Tool Grounding** (0-5): Can the required behavior be executed with available tools?
4. **Instruction Followability** (0-5): Can an LLM realistically follow all constraints at once?
5. **State & Conflict Manageability** (0-5): Does the prompt require hidden state tracking or conflicting rules?

## Skill Health Criteria (SK-1 through SK-7)

When the agent YAML contains a `skills:` list, each skill is evaluated against seven additional criteria. These feed directly into the five agent-level dimensions and the Runtime Performance Risk section.

| Criterion | What it checks | Feeds into |
|---|---|---|
| **SK-1** Single Responsibility | Does the skill do exactly one thing? | Dimension 4 |
| **SK-2** Non-Overlapping Scope | Do any two skills share the same user intent? | Dimension 2 |
| **SK-3** Routing Clarity | Is the name + description specific enough for the agent to route deterministically? | Dimension 2 |
| **SK-4** No Cross-Skill Dependencies (+ loop detection) | Does the skill assume another skill has already run? Are there dependency cycles? | Dimension 5 |
| **SK-5** Complexity Budget | Does the skill body exceed Rule C/E/F complexity thresholds independently? | Dimensions 3, 4 |
| **SK-6** Correlation & Consolidation | Are two skills likely to co-load in the same turn? Should they be merged? | Runtime Performance Risk |
| **SK-7** Architecture Performance Surface | What is the aggregate context-load overhead of the skill architecture? | Runtime Performance Risk |

Each criterion is rated **Pass / Warn / Fail** per skill. SK-4 includes dependency loop detection: a directed graph is built across all skills and checked for cycles — any cycle is a **dependency deadlock** and reported as a separate finding.

## Utility Scripts

The `scripts/` directory (relative to this skill) contains utility scripts for enhanced evaluation capabilities.

> **Path note:** `scripts/` is relative to the skill directory (`skills/agent-instructions-evaluator/`), not the top-level workspace root.

### extract_agent_info.py

Extracts metadata from watsonx Orchestrate agent YAML files, including the full **skills list** with each skill resolved to its `SKILL.md` location and metadata.

```bash
# Basic extraction
python scripts/extract_agent_info.py path/to/agent.yaml --json

# When SKILL.md files are not co-located with the agent YAML
python scripts/extract_agent_info.py path/to/agent.yaml --search-root /path/to/project --json

# Extract a single field
python scripts/extract_agent_info.py path/to/agent.yaml --field skills
```

**Extracted fields:** `name`, `display_name`, `kind`, `llm`, `tools`, `collaborators`, `context_variables`, `instructions_length`, `guidelines_count`, and for each resolved skill: `description`, `allowed_tools`, `scripts/`, `references/`, `has_wxo_yaml`, `skill_file`.

**Skill discovery:** searches recursively from `--search-root` (default: agent YAML directory) for `SKILL.md` files whose frontmatter `name` matches the skill name. Falls back to parent directory name matching.

**Skill directory structure resolved:**
```
<skill-name>/
├── SKILL.md           # frontmatter: name, description, allowed-tools
├── WXO.yaml           # optional: server-side skill config
├── scripts/           # optional: Python scripts available at runtime
│   └── *.py
└── references/        # optional: reference files available at runtime
    └── *
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

**Evaluate a watsonx Orchestrate agent YAML with skills:**
```
Use the agent-instructions-evaluator skill to evaluate 'agents/my_agent.yaml',
search for skills under 'examples/local/myproject'
```

**Evaluate a system prompt:**
```
Evaluate the agent prompt in 'prompts/investment_assistant.md' using the agent-instructions-evaluator skill
```

**Evaluate and save report set:**
```
Run agent-instructions-evaluator on 'agents/support_bot.yaml' and save all reports to 'agents/instructions_eval/'
```

**Evaluate a single skill:**
```
Use agent-instructions-evaluator to evaluate the SKILL.md in 'skills/billing/'
as part of agent 'agents/my_agent.yaml'
```

### What the Skill Accepts

- Raw system prompts
- Instruction blocks for agents
- watsonx Orchestrate native agent YAML files (with or without a `skills:` list)
- External agent definitions
- Design documents describing agent behavior
- Partial excerpts from larger prompts or policies
- Individual `SKILL.md` files (evaluated as skill body only)

## Evidence Quoting Rules

All findings quote the original text directly. Two conventions apply regardless of report type:

- **Line numbers**: quotes include the source line number where available — `> "text…" *(line N)*`
- **Non-English content**: if the quoted text is not in English, the original is quoted first, then an English translation is provided on the next line — `> [Translation]: …` — so findings are self-contained for all reviewers

## Interpretation Bands

| Band | Condition |
|---|---|
| **Very high-risk / Not achievable** | Any dimension 0–1 |
| **High-risk** | Two or more dimensions ≤ 2 |
| **Moderate-risk** | Mixed scores, some fragility |
| **Low-risk** | Most dimensions 3–4, targeted improvements needed |
| **Strong** | All dimensions 4–5 |

## Signal Thresholds

### Agent-level signals (Rules A–G)

| Signal | Risk threshold | Rule | Impact |
|---|---|---|---|
| Implicit state vars | Any | A | State tracking failures |
| Exact phrases | > 10 | B | High brittleness |
| Nested branches | > 20 | C | Workflow navigation errors |
| Tool grounding gap | Any | D | Execution failures |
| Prompt length | > 150 lines | E | Attention drift + token overhead |
| Active rules/turn | > 20 | F | Partial compliance |
| Instruction complexity | High concentration | G | Performance friction, latency variance |

### Skill-level signals (Rules H–N)

| Signal | Rule | SK | Impact |
|---|---|---|---|
| Multiple workflows in one skill | H | SK-1 | Complexity inflation |
| Skill scope overlap | I | SK-2 | Ambiguous routing |
| Missing intent coverage or boundary conditions | J | SK-3 | Misdirected skill loads |
| Cross-skill dependency (unidirectional) | K T1 | SK-4 | Hidden sequencing contract |
| Dependency loop (cycle in dependency graph) | K T2 | SK-4 | Routing deadlock — score 0 for primary skills |
| Skill body exceeds Rule C/E/F thresholds | L | SK-5 | Per-skill achievability failure |
| Correlated skill pair likely to co-load | M | SK-6 | Per-turn latency overhead |
| Skill architecture surface (count, size, ambiguity) | N | SK-7 | Aggregate context-load overhead |

## Files in This Skill

| File | Purpose |
|---|---|
| [`SKILL.md`](SKILL.md) | Complete skill definition and evaluation methodology |
| [`dimension-definitions.md`](dimension-definitions.md) | Detailed scoring rubrics for all five dimensions, with skill-specific guidance |
| [`signal-rules.md`](signal-rules.md) | Deterministic rules A–N (agent-level A–G, skill-level H–N) |
| [`report-template.md`](report-template.md) | Three templates: agent report, skill report, index |
| [`example-finding.md`](example-finding.md) | Sample finding with all required elements; finding categories |
| [`scripts/extract_agent_info.py`](scripts/extract_agent_info.py) | Extract agent metadata + resolve skills from agent YAML |
| [`scripts/extract_tool_info.py`](scripts/extract_tool_info.py) | Extract tool signatures from .py / .json / .yaml tool files |
| [`scripts/README.md`](scripts/README.md) | Full script documentation |

## Design Philosophy

**Evaluate operational achievability, not writing quality.**

- Focus on runtime reliability, not academic elegance
- Separate deterministic signals from judgment
- Prefer per-dimension truth over averaged scores
- Be evidence-based: quote concrete lines with line numbers; translate non-English content
- Be operational: focus on production failure modes
- Prioritize high-leverage fixes that improve multiple dimensions
- **Reliability and performance are coupled.** Instructions that are hard to follow are often also expensive to execute.
- **Skills are instructions too.** Apply the same complexity rules to skill bodies that you apply to agent instructions.
