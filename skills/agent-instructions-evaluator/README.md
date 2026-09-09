# Agent Instructions Evaluator

Evaluate agent instructions or agent definitions for operational achievability in production settings. This skill focuses on runtime reliability and runtime efficiency rather than writing quality, identifying issues from hidden state, conflicting rules, vague scope, brittle exact phrasing, underspecified tool behavior, instruction overload, performance friction caused by excessive or contradictory runtime reasoning, and — when the agent uses **skills** — skill architecture problems such as overlapping scope, cross-skill dependencies, dependency loops, and excessive context-load overhead.

## What This Skill Does

Produces a structured, evidence-backed **report set** saved as individual files in an `eval/` directory:

| File | Contents |
|---|---|
| `index.md` | Manifest of all reports with verdicts and Skill Health summary |
| `agent_<name>_extracted.json` | **Required** — raw extraction data from `extract_agent_info.py` |
| `tool_<name>_extracted.json` | Raw extraction data per tool (when produced by `extract_tool_info.py`) |
| `agent_<name>_report.md` | Agent-level analysis across 5 dimensions + Skill Health Assessment |
| `agent_<name>_report_harness.json` | Machine-readable JSON for harness integration |
| `skill_<name>_report.md` | Per-skill analysis — one file per resolved skill |
| `skill_<name>_report_harness.json` | Per-skill JSON harness |
| `token_optimization_report.md` | Token consumption optimization (Rule O — always produced) |
| `performance_optimization_report.md` | Runtime performance optimization (Rule P — always produced) |
| `reliability_optimization_report.md` | Reliability optimization (Rule Q — always produced) |
| `rules-summary.md` | Copy of evaluation rules reference |

Each report is written to disk as soon as its analysis is complete — **save-as-you-go**, not batched. The `agent_<name>_extracted.json` file is the authoritative source for all token estimates and must be saved before analysis begins.

## Core Principle

Score the artifact not by how much behavior it describes, but by how much behavior the agent can reliably execute. More rules do not automatically make a better prompt — more rules often lower achievability.

**Reliability and performance are coupled.** Instructions that are hard to follow are often also expensive to execute.

## Five Evaluation Dimensions

Applied to both agent instructions and each skill's `SKILL.md` body independently:

1. **Task Understanding** (0–5): Can the agent understand its primary job?
2. **Scope & Applicability** (0–5): Does the agent know when the instruction applies?
3. **Execution & Tool Grounding** (0–5): Can the required behavior be executed with available tools?
4. **Instruction Followability** (0–5): Can an LLM realistically follow all constraints at once?
5. **State & Conflict Manageability** (0–5): Does the prompt require hidden state tracking or conflicting rules?

## Skill Health Criteria (SK-1 through SK-7)

When the agent YAML contains a `skills:` list, each skill is evaluated against seven additional criteria. These feed directly into the five agent-level dimensions and the Runtime Performance Risk section.

| Criterion | What it checks | Feeds into |
|---|---|---|
| **SK-1** Single Responsibility | Does the skill do exactly one thing? | Dimension 4 |
| **SK-2** Non-Overlapping Scope | Do any two skills share the same user intent? | Dimension 2 |
| **SK-3** Routing Clarity | Is the name + description specific enough for the agent to route deterministically? | Dimension 2 |
| **SK-4** Cross-Skill Dependencies, Handoffs, Loop Detection | Does the skill assume another skill ran? Mid-workflow `load_skill`? Dependency cycle? | Dimension 5 |
| **SK-5** Complexity Budget | Does the skill body exceed Rule C/E/F complexity thresholds independently? | Dimensions 3, 4 |
| **SK-6** Correlation & Consolidation | Sequential loads in same turn? Tool-binding shadow? Should they be merged? | Runtime Performance Risk |
| **SK-7** Architecture Performance Surface | Aggregate context-load overhead of the skill architecture | Runtime Performance Risk |

Each criterion is rated **Pass / Warn / Fail** per skill.

## Utility Scripts

The `scripts/` directory (relative to this skill) contains utility scripts for enhanced evaluation capabilities.

> **Path note:** `scripts/` is relative to the skill directory (`skills/agent-instructions-evaluator/`), not the top-level workspace root.

### extract_agent_info.py

Extracts metadata from watsonx Orchestrate agent YAML files and **auto-discovers tool definitions** in one command. Saves a complete JSON snapshot to `--output-dir`.

```bash
# Preferred — single command, auto-scans project tree for tool source files
python scripts/extract_agent_info.py agent.yaml \
    --search-root /path/to/project \
    --output-dir eval/ --json

# Explicit toolkit directory (faster on large trees)
python scripts/extract_agent_info.py agent.yaml \
    --search-root /path/to/project \
    --tools-root /path/to/toolkit \
    --output-dir eval/ --json

# Pre-extracted tool JSONs (backward-compatible)
python scripts/extract_agent_info.py agent.yaml \
    --search-root /path/to/project \
    --tools-dir eval/ \
    --output-dir eval/ --json

# Extract a single field
python scripts/extract_agent_info.py agent.yaml --field skills
```

#### `--tools-root` / auto-scan behaviour

| Scenario | What happens |
|---|---|
| `--tools-root /path` supplied | Recursively scans that directory for tool source files |
| Neither `--tools-root` nor `--tools-dir` supplied | **Auto-scan**: recursively scans `--search-root` (or the agent YAML's directory) — no extra flags needed in most cases |
| Both `--tools-dir` and `--tools-root` supplied | `--tools-dir` entries take priority; `--tools-root` fills gaps |

**File inclusion rules during scan:**
- `.py` — included only when the file contains at least one `@tool` or `@flow` decorated function; all other Python files are silently skipped
- `.json` — included only when `detect_json_tool_type()` identifies the file as a WxO Agentic Workflow (`spec.kind == "flow"`) or Langflow format; all other JSON is silently skipped

#### Namespace prefix stripping

Agent YAMLs often reference tools with a toolkit namespace prefix (e.g. `silver:calculator_tool`). The script strips the prefix before lookup so `silver:calculator_tool` resolves to the same extracted spec as `calculator_tool`.

#### Per-turn token budget (three-level model)

Token costs are **scoped per level** — never summed across levels:

| Level | Context window | Components |
|---|---|---|
| **L1 — Agent** | Supervisor's context, every turn | `instructions_est_tokens` + `skill_catalog_est_tokens` + `collaborator_routing_est_tokens` + `tool_list_est_tokens` + `tools_spec_est_tokens` = `agent_floor_est_tokens` |
| **L2 — Skill** | Added to L1 only when a skill loads | `body_est_tokens` + skill allowed-tool names tokens + `allowed_tools_spec_est_tokens` |
| **L3 — Collaborator** | Separate LLM call, own context window | Collaborator's own instructions + tools + skills — **never additive to L1/L2** |

Key scoping rules:
- **Skill catalog** (`skill_catalog_est_tokens`): all skill names + descriptions are present on every agent turn so the agent can decide which skill to load
- **Collaborator routing** (`collaborator_routing_est_tokens`): collab names + descriptions only — collab internals run in a separate context and are not counted here
- **Tool list** (`tool_list_est_tokens`): agent-level tool names, present every turn for tool routing decisions — separate from tool spec bodies
- **Allowed-tools** in skills: names and schemas are owned by the skill and injected **only when that skill loads** — not part of the agent L1 floor
- Only one skill body is active at a time; sequential skill loads replace the previous body, not sum
- **Skill-filtered tools excluded from L1 floor:** In wxO, `agent tools:` is the authoritative declaration — tools must be listed there first. A skill's `allowed-tools` is a *filter* restricting which of those agent-owned tools are visible in the skill's context. Any tool in `agent tools:` that also appears in a skill's `allowed-tools` is removed from the agent's base tool set by the platform (it is only accessible while that skill is active). Its spec is **not loaded at L1** and is excluded from `tool_list_est_tokens` and `tools_spec_est_tokens`. Only `active_resolved_tools` (tools not filtered by any skill) are counted in the L1 floor. This is the expected and correct behaviour — it is not a defect. When `active_resolved_tools` is empty (every agent-level tool is skill-filtered), the evaluator raises a lightweight intentionality note only — this is a valid pure skill-routing design and does not lower any dimension score.

#### Unresolved tool fallback

When a tool definition cannot be found (file not in scan path, unsupported format), a **200-token fallback estimate** is used instead of zero. This appears in the output as:
```
[tool-name]  ~200 est. tokens (fallback — definition not found)
```

#### Extracted fields in `agent_<name>_extracted.json`

| Field | Description |
|---|---|
| `instructions_est_tokens` | Agent instructions token estimate |
| `instructions_chars` | Agent instructions character count |
| `skill_catalog_est_tokens` | Sum of (name + description) tokens for all skills — L1 cost |
| `collaborator_routing_est_tokens` | Sum of (name + description) tokens for all collaborators — L1 routing cost |
| `tool_list_est_tokens` | Sum of token cost of all agent-level tool names — L1 cost |
| `tools_spec_est_tokens` | Sum of spec body tokens for all agent-level tools — L1 cost |
| `agent_floor_est_tokens` | Total L1 floor — excludes shadowed tools (removed from base set by platform) |
| `active_resolved_tools` | Tools in `agent tools:` that are NOT filtered by any skill's `allowed-tools` — truly accessible at L1 (agent base context); their tokens are counted in the L1 floor |
| `shadowed_resolved_tools` | Tools in `agent tools:` that ARE filtered by at least one skill's `allowed-tools` — accessible only when that skill is active, not at the agent's base L1; excluded from L1 floor. This is the correct/expected pattern — listing these does not indicate a defect. |
| `skill_only_tools` | Subset of `shadowed_resolved_tools` where the tool name also does not appear in agent instructions/guidelines text — informational signal that the tool is used exclusively in skill contexts. Not a violation; just useful for authoring clarity. |
| `agent_callable_tools` | Complement: tools in `agent tools:` that ARE referenced in agent instructions/guidelines text, or are not filtered by any skill's `allowed-tools` — tools the agent can plausibly call at the base level |
| `resolved_tools` | Each tool with `spec_chars`, `spec_est_tokens`, `resolved`, `file_path` |
| `resolved_collaborators` | Each collaborator with `routing_est_tokens`, `instructions_est_tokens`, `collocated`, etc. |
| `skills[].catalog_est_tokens` | L1 cost for this skill (name + description, paid every turn) |
| `skills[].body_est_tokens` | L2 load cost — skill body only |
| `skills[].allowed_tools_spec_est_tokens` | L2 load cost — allowed-tool schemas (uses 200-token fallback for unresolved tools) |
| `skills[].tool_binding_shadows` | Tools that appear in both this skill's `allowed-tools` and the agent's top-level `tools:` — used to populate `shadowed_resolved_tools`. A non-empty list is normal and expected (every skill-used tool must be declared in `agent tools:` first). Becomes a **SK-6 Trigger 3 violation** only when the agent's `instructions:` or `guidelines:` also reference one of these tools (the instruction cannot be executed at base level). Becomes a **SK-6 Trigger 3a configuration risk** only when no tools are left in `active_resolved_tools`. |
| `skills[].name_too_long` | `true` if name exceeds 64-char hard limit (SK-3 hard failure) |
| `skills[].description_too_long` | `true` if description exceeds 1024-char hard limit (SK-3 hard failure) |
| `skills[].unmatched_placeholders` | `{{identifier}}` tokens with no matching `param` entry |

### extract_tool_info.py

**Unified tool extractor** — auto-detects `.py`, `.json`, and `.yaml`/`.yml` tool files. Used when the auto-scan in `extract_agent_info.py` is insufficient (e.g. tools in a remote registry).

```bash
python scripts/extract_tool_info.py path/to/tool.py --json
python scripts/extract_tool_info.py path/to/tool.py --output-dir eval/
```

Supported formats auto-detected by file extension and content:
- **`.py`** — `@tool` decorator → regular Python tool; `@flow` decorator → Python flow tool
- **`.json`** — `spec.kind == "flow"` → WxO Agentic Workflow; `data.nodes` (list) → Langflow workflow
- **`.yaml/.yml`** — `kind: knowledge_base` → WxO Knowledge Base; `kind: mcp` → MCP Toolkit

#### Token estimation rules

All estimates use **character count ÷ 4** (≈4 chars/token).

**Python `@tool` / `@flow` functions:**
Spec = function name + docstring + each parameter serialised as its **JSON Schema representation**:

| Python type annotation | JSON Schema used for counting |
|---|---|
| `str` | `{"type":"string"}` |
| `int` | `{"type":"integer"}` |
| `bool` | `{"type":"boolean"}` |
| `float` | `{"type":"number"}` |
| `list[str]` / `List[str]` | `{"type":"array","items":{"type":"string"}}` |
| `Optional[str]` / `Union[str, None]` | `{"type":"string"}` (nullable unwrapped) |
| `Literal["a","b"]` | `{"type":"string","enum":["a","b"]}` |
| `dict` / `Dict` | `{"type":"object"}` |
| Unknown custom class | `{"type":"object"}` (conservative fallback) |

**Return type is excluded** — output schema is not injected into the agent context.

**WxO Agentic Workflow JSON:**
Spec = name + display_name + description + `input_schema` only. **Output schema is excluded.**

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
Run agent-instructions-evaluator on 'agents/support_bot.yaml' and save all reports to 'agents/eval/'
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
| Sequential skill-load pair (same-turn) | M | SK-6 | Per-turn latency overhead |
| Skill architecture surface (count, size, ambiguity) | N | SK-7 | Aggregate context-load overhead |

### Token optimization signals (Rule O)

Rule O identifies patterns that inflate per-turn token cost beyond functional requirements. Three optimization surfaces — always assessed:

| Surface | When paid | What Rule O looks for |
|---|---|---|
| **Agent instructions** | Every turn | Procedure steps in instructions instead of tools, stateful protocol sections, overcrowded tool-call contracts, redundant scope statements |
| **Skill catalog** (all skill names + descriptions) | Every turn | Overlong descriptions that pay catalog tokens every turn for detail only needed after loading |
| **Skill bodies** | Per skill load | Correlated sequential-load pairs, oversized bodies, repeated base contract prose, LLM-side classification, exact-phrase contracts tied to backend systems |

Severity levels: **High** (exceeds Rule C/E/F/N threshold), **Medium** (present but below threshold), **Low** (marginal / low-frequency turns), **None found**.

Savings are reported as a percentage of current component size:
> `~X lines (~Y% of current [N]-line [component]) → ~Z tokens saved per [turn type]`

### Performance optimization signals (Rule P)

Rule P identifies avoidable runtime overhead in execution architecture — tool-call RTTs, multi-hop inference, deep orchestration layers, coupled tool sequences.

### Reliability optimization signals (Rule Q)

Rule Q synthesises agent and skill report findings into a prioritised, implementation-ready rewrite plan grouped by failure class (implicit state, exact-phrase, scope/routing, conflicting rules, tool underspecification, skill body complexity).

## Important Notes on Evaluation

**Model Interpretation:** Evaluations are subject to interpretation by different LLM models. For best results, use a **coding agent with access to a frontier model** (e.g., IBM Bob, Claude Sonnet, GPT-4o, or equivalent) with tool access and strong reasoning capabilities.

**Using the Report:** The evaluation report is provided **as-is** and should be used as a **guide to improve agent instructions** rather than an absolute score. Focus on the evidence-backed findings and recommendations to iteratively improve your agent's operational reliability.

## Files in This Skill

| File | Purpose |
|---|---|
| [`SKILL.md`](SKILL.md) | Complete skill definition and evaluation methodology |
| [`dimension-definitions.md`](dimension-definitions.md) | Detailed scoring rubrics for all five dimensions, with skill-specific guidance |
| [`signal-rules.md`](signal-rules.md) | Deterministic rules A–Q (agent-level A–G, skill-level H–N, optimization O–Q) |
| [`report-template.md`](report-template.md) | Report templates: agent, skill, index, token optimization, performance optimization, reliability optimization |
| [`rules-summary.md`](rules-summary.md) | Standalone rules reference — copied into every `eval/` directory |
| [`scripts/extract_agent_info.py`](scripts/extract_agent_info.py) | Extract agent metadata + auto-discover tools + resolve skills from agent YAML |
| [`scripts/extract_tool_info.py`](scripts/extract_tool_info.py) | Extract tool signatures from .py / .json / .yaml tool files |
| [`scripts/README.md`](scripts/README.md) | Full script documentation |

## Design Philosophy

**Evaluate operational achievability, not writing quality.**

- Focus on runtime reliability, not academic elegance
- Separate deterministic signals from judgment
- Prefer per-dimension truth over averaged scores
- Be evidence-based: quote concrete lines with line numbers; translate non-English content inline
- Be operational: focus on production failure modes
- Prioritize high-leverage fixes that improve multiple dimensions
- **Reliability and performance are coupled.** Instructions that are hard to follow are often also expensive to execute.
- **Skills are instructions too.** Apply the same complexity rules to skill bodies that you apply to agent instructions.
- **Token costs are scoped per level.** Never sum agent, skill, and collaborator token costs into a single flat total — each level has its own context window.
