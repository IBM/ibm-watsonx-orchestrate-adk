# Evaluation Rules Summary

This document is a concise reference for the deterministic signal rules applied during every agent instructions evaluation. Copy it into any report set so reviewers can interpret scores and findings without needing to access the full skill directory.

Rules **A–G** apply to all agent instruction sets and system prompts. Rules **H–N** (prefixed SK) apply specifically to agents that use a `skills:` architecture with individual `SKILL.md` files. Rules **O**, **P**, and **Q** each produce a side report — always, for every evaluation.

---

## Core Rules (apply to all agents)

### Rule A — Prompt-only state dependence
**What it checks:** Whether the prompt requires tracking retry counts, clarification counts, survey state, or "already asked" flags without an explicit external state object.

**Why it matters:** LLMs cannot reliably maintain hidden counters or conversation status across turns. Any rule that depends on this produces guaranteed compliance failures.

**Red-flag phrases:** "remember what was said earlier", "avoid asking for information already provided", "max ONE retry per request", "never ask the same question twice"

**Score bounds triggered:**
- State & Conflict Manageability ≤ **2**
- Instruction Followability ≤ **3**

---

### Rule B — Exact phrase burden
**What it checks:** The number of requirements for word-for-word or exact-text reproduction (e.g., `"Respond EXACTLY with: ..."`, `"Say EXACTLY: ..."`).

**Why it matters:** Each exact phrase adds cognitive load and competes with tone, brevity, and context-awareness constraints. High counts make compliance fragile.

**Thresholds:**
| Exact phrases | Effect |
|---|---|
| > 5 | Note followability risk |
| > 10 | Treat prompt-only compliance as highly fragile |

---

### Rule C — Nested rule burden
**What it checks:** The number of meaningful nested if/then branches (conditions, exception clauses, sub-workflows, conditional sub-branches).

**Why it matters:** Deep nesting exceeds LLM working memory. The agent will follow wrong branches, especially when workflows interact.

**Thresholds and score bounds:**
| Branch count | Effect | Instruction Followability bound |
|---|---|---|
| > 10 | High workflow complexity risk | — |
| > 20 | Compliance fragile without state machine | ≤ **2** |
| > 30 | Near-impossible; partial compliance is the norm | ≤ **1** |
| > 40 | Not achievable via prompt alone | ≤ **0** |

---

### Rule D — Tool-required behavior gap
**What it checks:** Whether every tool-required behavior specifies all five elements: (1) tool name, (2) trigger condition, (3) input parameters, (4) result handling, (5) failure handling.

**Why it matters:** Without complete specification the agent must guess invocation syntax and result interpretation, leading to execution failures.

**Effect:** Each incomplete tool specification is an execution grounding gap. Treat tool reliability as weak or incomplete.

---

### Rule E — Prompt length and attention drift
**What it checks:** Total lines of instruction content (excluding blank lines, section headers alone, and pure metadata).

**Why it matters:** LLMs have limited attention span during generation. Very long prompts increase the risk that constraints mentioned early or late are forgotten or not properly integrated.

**Thresholds and score bounds:**
| Line count | Effect | Instruction Followability bound |
|---|---|---|
| > 100 | Attention drift risk | — |
| > 150 | Followability fragile | ≤ **2** |
| > 200 | Followability highly fragile; partial compliance very likely | ≤ **1** |

**Note:** Dense nested logic counts heavier — 100 lines of dense conditionals ≈ 150+ lines of simple instructions.

---

### Rule F — Active operational rule burden
**What it checks:** The number of operational rules that may simultaneously apply to a single user turn. This is distinct from total rule count (Rule E) and structural nesting (Rule C).

**What counts:** MUST/NEVER/ALWAYS constraints, conditional branches relevant to the current turn, output-format constraints, tool invocation rules, failure-handling rules, state-dependent rules, exact phrase requirements, safety/refusal/escalation rules.

**What does not count:** Section headers, non-binding examples, general style preferences that don't compete with operational requirements.

**Active rule budget:**
| Active rules per turn | Risk level |
|---|---|
| 0–5 | Low — realistic target for most agents |
| 6–10 | Manageable if rules are independent and prioritized |
| 11–20 | High — depends on rule independence and structure |
| 21–30 | Fragile — move branching, state, and validation to workflow |
| 30+ | Not achievable — the prompt is acting as a workflow engine |

**Score bounds:**
- > 10 active rules/turn: Instruction Followability ≤ **3**
- > 20 active rules/turn: Instruction Followability ≤ **2**
- > 30 active rules/turn: Instruction Followability ≤ **1**

**Control-plane principle:** Rules about routing, retries, tool selection, escalation, state transitions, or "only ask once" belong in deterministic workflow or tool contracts — not in the prompt. When they appear in the prompt, count them in this budget.

---

### Rule G — Performance friction from instruction complexity
**What it checks:** Whether the prompt contains a high volume of interacting constraints, ambiguous tool triggers, conflicting rules, or workflow logic that the LLM must resolve at runtime — increasing token usage, latency, or response variance.

**Why it matters:** Achievability is not just "can the model produce the right behavior?" — it is also "can the model produce it predictably, cheaply, and with bounded runtime variance?"

**Performance risk indicators:**
- Prompt length exceeds 100 / 150 / 200 lines (Rule E)
- Nested branches exceed 10 / 20 / 30 / 40 (Rule C)
- Active rules/turn exceed 10 / 20 / 30 (Rule F)
- Ambiguous or overlapping tool triggers
- Multiple rules compete in the same turn without priority
- Exact phrase requirements interact with tone, format, safety, or tool-use constraints
- Failure handling is prompt-only rather than workflow-managed

**Score impact:** Does not automatically reduce every dimension. Influences Instruction Followability and Execution & Tool Grounding when applicable. Reported separately as Runtime Performance Risk.

---

## Skill Architecture Rules (apply when `skills:` are present)

### Rule H — Skill single-responsibility violation (SK-1)
**What it checks:** Whether a skill's `SKILL.md` body describes more than one primary workflow, covers more than one unrelated intent category, or calls tools from more than one logical domain.

**Why it matters:** A multi-responsibility skill acts as a mini-orchestrator. When the agent loads it, it inherits all the compounded complexity — inflating the agent's effective active-rule budget even if the agent's own instructions are lean.

**Score bounds:**
- 2 primary workflows in one skill: Instruction Followability ≤ **3**
- 3+ primary workflows: Instruction Followability ≤ **2**; also lower agent Dimension 4 by at least 1 if the skill is large

---

### Rule I — Skill scope overlap (SK-2)
**What it checks:** Whether two or more skills share detectable scope for the same user intent, topic, or trigger condition.

**Why it matters:** Overlapping skills force the agent to make a disambiguation decision at exactly the moment when deterministic routing is most important. Routing errors cascade: wrong instructions → wrong tools → wrong behavior.

**Overlap ratings and score bounds on Dimension 2 (Scope & Applicability):**
| Rating | Definition | Dimension 2 bound |
|---|---|---|
| Exact | Same intent, same wording in both descriptions | ≤ **1** |
| High | Same intent, different wording | ≤ **2** |
| Moderate | Shared boundary conditions or edge cases | Reduce by 1 if multiple pairs |
| Low | Tangential overlap only | Note only; no automatic bound |

---

### Rule J — Skill routing clarity (SK-3)
**What it checks:** Whether a skill's `description` frontmatter explicitly states the intents it covers, includes boundary conditions (what it does NOT cover), and uses a specific enough name to be disambiguated from other skills.

**Why it matters:** The agent selects a skill primarily from the skill's `name` and `description`. Vague or boundary-free descriptions make every skill load decision a guess.

**Score bounds on Dimension 2:**
- Missing explicit intent coverage alone: ≤ **3**
- Missing intent coverage + missing boundary conditions: ≤ **2**
- Generic skill name alone: ≤ **3**
- All three triggers on the same skill: ≤ **1**

---

### Rule J2 — Redundant or conflicting platform content (SK-8)

> **Single source of truth: [`signal-rules.md`](signal-rules.md) — Rule J2.** That file defines the three item categories (A: platform-injected; B: fixed platform behavior; C: misplaced content), all four triggers, and the per-category remediation. Refer to `signal-rules.md` for the complete rule when evaluating or reviewing an SK-8 finding.

**Score bounds:** No dimension penalty — this is a token and maintainability issue, not an achievability issue. Report via Rule O (token optimization). Do **not** recommend adding any of the listed items to author-written files.

---

### Rule K — Cross-skill state dependency and dependency loops (SK-4)
**What it checks:** Whether a skill's body assumes state or results from a prior skill (unidirectional dependency), or whether two or more skills form a circular dependency where no valid first skill exists.

**Why it matters:** Skills are loaded dynamically and must be independently executable. Unidirectional dependencies make routing order a hidden contract the LLM cannot reliably maintain. Dependency loops make satisfying any routing precondition logically impossible.

**Score bounds on Dimension 5 (State & Conflict Manageability):**
- Any unidirectional dependency: ≤ **2**
- Multiple unidirectional dependencies: ≤ **1**
- Any dependency loop detected: ≤ **1**; if the loop involves required skills for primary use cases: **0**

---

### Rule L — Skill body complexity (SK-5)
**What it checks:** Whether a skill's `SKILL.md` instruction body individually exceeds any of the Rule C, E, or F thresholds when analyzed in isolation.

**Why it matters:** Skills are not exempt from the complexity rules that govern agent instructions. A skill body is an instruction set — it is subject to attention drift (E), nested branch overload (C), active rule budget limits (F), hidden state failure (A), exact phrase brittleness (B), and tool underspecification (D). An unachievable skill degrades the whole agent's achievability.

**Score bounds:** Apply the same bounds as Rules A–F to the skill body in isolation. These bounds apply to the **skill's own dimension scores** in the per-skill report. They do not automatically cap the agent's five dimension scores — skill body complexity is a per-skill finding, not an agent-level cap. The skill findings that reach the agent's scorecard are: SK-2 Exact/High overlap (→ agent Dimension 2); SK-3 hard-limit failures (→ agent Dimension 3); SK-6 Trigger 3 — agent instructions reference a skill-filtered tool (→ agent Dimension 3, **High severity**). SK-6 Trigger 3a (zero `active_resolved_tools`) is an intentionality note only — it does not lower any dimension score regardless of whether it is confirmed. SK-6 Trigger 3b (skill-only tools) is informational only.

**Additional trigger:** A skill body that tracks retry counts or step state without an explicit state object (Rule A pattern) is doubly risky — the hidden state lives inside a dynamically loaded/unloaded module.

---

### Rule M — Skill correlation and consolidation signal (SK-6)
**What it checks:** Whether two or more skills are so closely related in domain, tool coverage, or trigger conditions that they are likely to fire in the same turn or be loaded in immediate succession. Also checks for the tool-shadowing execution gap described below.

**Platform model:** Every tool any skill needs must be declared in `agent tools:` — that list is the authoritative registry. A skill's `allowed-tools` is a *filter* restricting which of those declared tools are visible inside the skill. Three resulting categories:

- **Agent-only tool**: in `agent tools:`, not in any skill's `allowed-tools` → callable at base level, not in skill context
- **Skill-filtered tool**: in `agent tools:` AND in one or more skills' `allowed-tools` → **only callable inside those skill contexts; shadowed at agent base level**
- **Skill-only tool** (subset of skill-filtered, informational): skill-filtered AND the agent `instructions:`/`guidelines:` never reference it → no execution gap; the agent never intended to call it at base level

The critical implication: **if the agent's `instructions:` or `guidelines:` direct it to call a skill-filtered tool, that call silently fails whenever no skill is active** — the tool is declared but unreachable at the base level.

**Note on shared tools:** Two skills listing the same tool in their `allowed-tools` is expected — the tool is visible inside each of those skill contexts. Shared entries are not a correlation signal and do not trigger this rule.

**Triggers:**
1. **Adjacent trigger intents:** Two skills cover adjacent user intents that commonly occur in the same turn — each intent requires its own `load_skill` call; the first body is replaced when the second loads.
2. **Mid-body `load_skill` reference:** A skill body instructs the agent to call `load_skill` for another skill before that body's own work is complete (SK-4 violation + coupling signal).
3. **Agent instruction references a skill-filtered tool (silent execution gap — High):** The agent's `instructions:` or `guidelines:` names a tool that also appears in at least one skill's `allowed-tools`. That tool is unreachable at the agent's base level. This is a deterministic reliability violation. Detect by cross-referencing agent text against `shadowed_resolved_tools` (excluding `skill_only_tools`). Fix: either remove the tool from the skill's `allowed-tools` (keep it in agent base set), or move the agent-level instruction into the skill body.
4. **Zero-tool base coverage — intentionality check:** Every tool in `agent tools:` is filtered by at least one skill's `allowed-tools`, leaving `active_resolved_tools` empty. **This is a valid design** for a pure skill-routing agent. Raise a lightweight intentionality note if the agent `instructions:` contain no explicit statement confirming that every user intent is handled through a skill. If the author confirms the intent, record it as confirmed — no finding and no score impact.

**Consolidation trigger:** Both skills have SK-2 Moderate/High overlap AND cover intents likely to co-occur in a single turn, OR one skill's body issues a mid-body `load_skill` call to the other (inseparable sequential dependency).

**Risk ratings:**
- 1 correlated pair (Trigger 1 or 2): skill-load overhead risk is **Medium**
- 2+ correlated pairs: skill-load overhead risk is **High**
- Any Trigger 3 violation: **High** — lowers agent Dimension 3 (Execution & Tool Grounding)
- Trigger 3a (zero `active_resolved_tools`, unconfirmed): intentionality note only — no score impact

---

### Rule N — Skill context-load performance surface (SK-7)
**What it checks:** The total runtime cost introduced by the skill architecture itself — the aggregate performance surface of having N skills, each with a body of B lines, that must be selectively loaded at runtime.

**Performance surface components:**
| Component | Medium threshold | High threshold |
|---|---|---|
| Skill count | > 5 skills | > 10 skills |
| Per-skill body size | > 100 lines/skill | > 150 lines/skill |
| Routing ambiguity (plausible candidates/turn) | > 2 candidates | > 4 candidates |
| Load transitions per turn (sequential loads for multi-step intents) | > 1 per turn | > 2 per turn |
| Same-skill reload within a single turn | Any confirmed | — |
| Per-load token cost (largest body loaded in one turn) | > 2,000 tokens | > 4,000 tokens |

**Overall rating:**
- Any single component at High → skill-load overhead risk = **High**
- Two or more components at Medium (no High) → **Medium**
- All components Low → **Low**

---

### Rule O — Token consumption optimization
**What it checks:** Whether the agent's main instructions, skill catalog, and skill bodies together inflate per-turn token cost beyond what the functional requirements demand. **Three surfaces are assessed:** agent instructions (paid on every turn — highest leverage), skill catalog (all skill names + descriptions, paid on every turn), and skill bodies (paid per intent load — one at a time).

**Always produced** as part of every evaluation. If no issues are found, the report states that and records the current token budget as a baseline.

**Severity per item:** High (exceeds a Rule threshold) · Medium (present, below threshold) · Low (marginal) · **None found** (checked, not detected).

**Agent instruction optimization patterns (permanent cost — highest leverage):**
| Pattern | Check | Action |
|---|---|---|
| Procedure steps that belong in tools | Step-by-step workflow / retry / error handling logic in agent instructions | Move to tool contract; reduce to trigger + relay rule. For deterministic multi-step sequences: use **`nextTool` chaining** (`_meta.nextTool`) if ≤5 steps, single Python MCP server, branching (if any) is stable to hardcode, simple Q&A interaction only, no transaction audit; use **Agentic Workflow** (`@flow` / WxO Agentic Workflow JSON) if branch logic may evolve, multi-step user confirmation, cross-server tools, >5 steps, or transaction audit required. Both remove the sequence prose from agent instructions entirely. |
| Stateful protocol sections | Inline counter, session flag, or multi-turn state machine (Rule A) | Move to server-side variable or tool return field |
| Overcrowded tool-call contract sections | Per-tool parameter prose duplicating what a tool schema already specifies | Reduce to trigger + relay rule only |
| Exact-phrase rules tied to backend hooks | Prefix generation, sentinel detection, verbatim relay rules driving plugin hooks | Move to pre/post invoke plugin |
| Redundant scope statements | Agent instructions restate per-skill boundaries already in skill `description` frontmatter | Remove; skill description is the authoritative scope |
| Implicit state correction logic | LLM asked to review history to self-correct a missed step (Rule A) | Move to server-side counter surfaced as tool return field |

**Knowledge base / retrieval token risk (any surface):**
| Pattern | Check | Action |
|---|---|---|
| KB-like tool with no passage limit | Tool flagged as retrieval + no `top_k`/`max_results`/`limit` in instructions or tool definition | Add explicit passage limit ≤ 5; flag as High |
| Unconstrained or large passage count | Limit > 5, or instruction says "all relevant" / "full context" | Lower limit; flag as High if > 5, Medium if 4–5 |
| High KB call frequency | KB called unconditionally on every turn or most turns | Condition the call; flag as High |
| Multiple KB calls per turn | Two or more retrieval calls in a single turn workflow | Merge or condition; flag as High |
| KB in high-frequency skill | Retrieval tool in a skill body loaded on most turns | Flag as Medium; compound token risk |

**Skill body optimization patterns (per-load cost):**
| Pattern | Check | Action |
|---|---|---|
| Correlated sequential-load pairs | Confirmed SK-6 Trigger 1 or 2 | Consolidate skills; report token reduction per turn |
| Overlong catalog descriptions | Description > ~200 chars with procedure detail | Trim to routing signal; move procedure to body |
| Oversized skill bodies | >100 lines (Trigger 1) or >150 lines (Trigger 2) | Identify inflation source; move to tools or plugins |
| Repeated base contract prose | Same relay/handoff rules in multiple bodies AND in agent instructions | **Medium (not Low)** — duplication is a maintenance-driven conflict risk, not just token overhead: when skill bodies and agent instructions hold slightly different versions of the same rule, both are active in context simultaneously. Any edit that updates one copy and misses the others silently introduces an in-context contradiction. Remove from skill bodies; single authoritative version stays in agent instructions |
| Exact-phrase rules tied to backend hooks | Prefix generation, verbatim relay, prohibited-phrase lists driving plugin behavior | Move to pre/post invoke plugin |
| LLM-side classification | Free-text-to-enum inside skill body | Externalize to tool call |
| Mandatory in-skill re-routing | Skill body re-calls a routing or classification tool for ambiguous inputs | Replace with inline decision rule after consolidation |
| Shared protocol duplication | Multiple skills restate the same base relay or handoff protocol | **Medium (not Low)** — each per-skill copy is an independent maintenance surface: a future edit that updates the protocol in one skill but not the others creates in-context rule conflicts. Lift to agent instructions once; skill bodies keep only tool-specific detail (e.g., which named tool to call) |

**Token estimation guidance:** Use **character count ÷ 4** (≈4 chars/token) rather than a lines-based estimate — line length varies too much for lines to be reliable. `extract_agent_info.py` computes `instructions_est_tokens`, `skill_catalog_est_tokens` (all skill names + descriptions, paid every turn), `collaborator_routing_est_tokens` (all collaborator names + descriptions, paid every supervisor turn), `body_est_tokens` per skill, and `routing_est_tokens` per collaborator. Use these values directly. State estimates as approximations.

**This rule does NOT re-score the five dimensions.** It is a side report only. When no issues are found, the report still exists and states that.

---

### Rule P — Runtime performance optimization
**What it checks:** Whether the agent's execution architecture introduces avoidable runtime overhead — unnecessary tool-call RTTs, multi-hop LLM inference passes, deep orchestration layers, or coupled tool sequences that could be collapsed into deterministic pipelines. Where Rule O measures *instruction token cost*, Rule P measures *execution call-graph depth and latency*. Both compound each other but have different remedies.

**Always produced** as part of every evaluation. If no issues are found, the report states that and records the current call-graph depth as a baseline.

**Severity per item:** High (≥1 RTT/hop added on ≥20% of turns) · Medium (minority of turns or bounded overhead) · Low (marginal) · **None found** (checked, not detected).

**Deterministic sequence offload — two mechanisms:**

When instructions encode a deterministic tool sequence, move it out of the LLM reasoning path using the right mechanism. **This is not solely a performance optimisation:** when a confirmation step or high-stakes gate is expressed only in agent instructions, it is prompt-injectable — adversarial user messages can convince the LLM to skip it. Moving the sequence server-side makes every gate structurally mandatory and bypasses LLM reasoning entirely.

| Mechanism | Branching | User interaction | When to choose | Token saving | Latency saving |
|---|---|---|---|---|---|
| **`nextTool` chaining** (`_meta.nextTool`) | Supported — but branch logic is hardcoded inside the tool; changes require modifying and redeploying the tool | Simple Q&A only | ≤5 steps, single Python MCP server, branching (if any) is stable and acceptable to hardcode, user interaction is simple Q&A at most, no transaction audit required | Removes step prose from instructions | Eliminates 1 LLM inference pass per chained step |
| **Agentic Workflow** (`@flow` / WxO Agentic Workflow JSON) | Supported with externalised logic — branch edges in the flow graph; business logic changes without touching tool code | Full multi-step confirmations | Branch logic may evolve; multi-step user confirmation; cross-server tools; >5 steps; transaction audit/observability required; or future editability needed | Same | Same — each transition becomes a deterministic flow edge |

**Decision rule:**
- **Security check first:** if the sequence contains any high-stakes gate (payment, transfer, account change, data deletion, authorisation check), it **must** be offloaded to either mechanism — keeping it in instructions makes it prompt-injectable.
- **Prefer Agentic Workflow** when any of: branch logic likely to change; multi-step user confirmation needed; cross-server tools; >5 steps; transaction audit/observability required.
- **`nextTool` chaining** is appropriate when all of: ≤5 steps; single Python MCP server; branching (if any) is stable and acceptable to hardcode in the tool; user interaction (if any) is simple Q&A; no transaction audit requirement.
- When in doubt, choose Agentic Workflow — it externalises control flow from tool code, supports richer user interaction, and provides built-in observability at no extra instrumentation cost.

**Tool execution patterns to check:**
| Pattern | Check | Action |
|---|---|---|
| Mandatory unconditional tool calls | Tool called on every turn regardless of intent | Absorb output into prior tool response or pre-invoke plugin |
| Fixed sequential tool chains | Tool A always followed by Tool B | Use **`nextTool` chaining** if ≤5 steps, single Python server, stable branching, simple interaction, no audit. Use **Agentic Workflow** if branch logic may evolve, multi-step user confirmation, cross-server, >5 steps, or audit required |
| `next_action` multi-hop dispatch | Tool returns field causing agent to call another tool in same turn | Apply the decision rule above: `nextTool` if stable-branch ≤5 steps, single server, no audit; Agentic Workflow if evolving-branch, multi-step interaction, multi-server, >5 steps, or audit required |
| LLM-side classification before tool call | Agent classifies free text before deciding which tool to call | Move to a classification tool or pre-invoke plugin |
| Correlated tool sets | Same tool set always called together across multiple skill bodies | Compose into a single tool; reduce LLM call count per turn |
| Tool failure handling in-prompt | LLM reasons about tool errors rather than using tool contract | Move to tool error return schema or agentic workflow retry policy |
| KB / retrieval on high-frequency intents | KB tool called with no passage limit or on most/all turns | Condition the call; set `top_k` ≤ 5; each unconstrained retrieval call adds unknown token payload + one RTT + enlarged context processing latency on all subsequent inference passes in the turn |
| Multiple KB calls per turn | Two or more retrieval calls in a single turn workflow | Merge into a single broader query or cache first result; each separate call is a separate RTT and widens the context further |

**Orchestration depth patterns to check:**
| Pattern | Check | Action |
|---|---|---|
| Deep collaborator stack | ≥ 3 hops before reaching the executing tool | Flatten; merge narrow collaborators covering adjacent intents |
| Skill routing overhead on every intent | Every intent requires `load_skill` before domain tool call | Collapse high-frequency skill bodies into agent instructions |
| Redundant in-skill re-routing | Skill re-calls a routing tool for ambiguous phrases | Replace with deterministic inline decision rule |
| Collaborator over-specialization | Many single-tool collaborators when broader collaborators would cover the domain in fewer hops | Consolidate; target ≤ 1 LLM hop between orchestrator and executing tool for high-frequency intents |

**Guidelines overhead to check:**
| Pattern | Check | Action |
|---|---|---|
| Guidelines restating instructions | Guidelines duplicate rules in `instructions:` | Remove duplicates; each guideline adds constraint-check pass at inference time |
| Guidelines expressing tool-call rules | Guideline says "when X, call tool Y" | Move to instructions or tool schema; guidelines are for behavioral guardrails, not execution logic |
| High guideline count | ≥ 5 guidelines adding per-turn overhead | Merge into instructions or tool preconditions; target ≤ 3 execution-relevant guidelines |
| Guidelines with complex conditions | Multi-clause if/then in guideline condition | Decompose into instruction rule with named state variable or tool precondition |

**Latency model guidance:** Each LLM inference pass ≈ 500ms–2s; each tool-call RTT ≈ 50ms–500ms; skill/collaborator load adds one inference hop. **Large retrieval payloads (5,000+ tokens injected) add a latency multiplier on top of inference hops** — input-token processing time scales with context size and cannot be modelled as a fixed hop. State estimates as approximations — production profiling required for exact values.

**Relationship to Rule O:** Rule O reduces tokens (input processing). Rule P reduces hops (call-graph depth). Both compound latency. When a recommendation reduces both, flag the dual benefit in both reports.

**This rule does NOT re-score the five dimensions.** It is a side report only. When no issues are found, the report still exists and states that.

---

### Rule Q — Reliability optimization
**What it checks:** Whether the agent's design contains patterns that produce **systematic, repeatable compliance failures** at runtime — failures that occur predictably for specific turn types because the instructions structurally cannot be followed reliably. Rule Q takes findings *from* the main evaluation reports and synthesises them into a single, prioritised, implementation-ready rewrite plan. Every REL-N item traces back to evidence in the main reports.

**Always produced** as part of every evaluation. If no issues are found, the report states that and records the current design as a reliability baseline.

**Severity per item:** Critical (wrong output on a predictable, non-trivial fraction of turns) · High (failures under commonly encountered conditions) · Medium (occasional failures, targeted rewrite needed) · Low (rare or recoverable) · **None found** (checked, not detected).

**Implicit state and counter patterns (Rule A):**
| Pattern | Check | Action |
|---|---|---|
| LLM-side attempt counter | LLM counts missed calls or retries from history | Move to server-side state or tool return field |
| Cross-turn "already asked" memory | "Never ask X twice" without context variable | Add boolean context variable set by tool response |
| Journey step tracking | Agent infers journey step from history, not `current_state` | Ensure tool always returns `current_state` |

**Exact-phrase and verbatim patterns (Rule B):**
| Pattern | Check | Action |
|---|---|---|
| Verbatim relay with backend hook | LLM must produce exact prefix/sentinel for plugin hook | Move production to plugin layer |
| Prohibited-phrase enforcement | LLM must suppress N specific phrases LLM-side | Move to post-invoke plugin text filter |
| Enum classification without tool | LLM classifies free text to a fixed enum inside the instruction body | Externalize to a classification tool or routing tool enrichment field |

**Scope and routing fragility (Rules I/J):**
| Pattern | Check | Action |
|---|---|---|
| Tense/phrasing-dependent routing boundary | Skills distinguished by grammatical form not semantic intent | Replace with CAUSE-based boundary + explicit examples |
| Subjective "last resort" fallback | No explicit exclusion list | Add exclusion list to description |
| Overlapping skill descriptions | Same intent covered by two skill descriptions | Merge or rewrite to explicitly exclude shared edge case |

**Conflicting and competing rules (Rules A/F):**
| Pattern | Check | Action |
|---|---|---|
| Same-turn dual-field distinction | Two similar fields from different sources require opposite actions | Sequence checks explicitly or consolidate into enum at tool layer |
| Competing output format rules | Short-response rule and verbatim relay rule conflict | Explicitly prioritize one; note the exception |
| Double-negative fill conditions | "Fill only when NOT X AND NOT Y" | Rewrite as positive condition |

**Underspecified tool behavior (Rule D):**
| Pattern | Check | Action |
|---|---|---|
| Missing failure handling | No guidance for tool error / timeout / unexpected output | Add 1-line failure handler per tool or document in tool error schema |
| Undeclared context variable | Variable referenced in instructions but absent from `context_variables:` | Declare in YAML or document as plugin-injected |
| `next_action` no-match case | Dispatch table has no handler for unexpected values | Add explicit default/no-match case |

**Skill body reliability (SK-5):**
| Pattern | Check | Action |
|---|---|---|
| Skill body exceeds followability threshold | >150 lines (Rule E Trigger 2) or >10 active rules/turn (Rule F high) | Decompose — move sub-sections to tool, plugin, or separate skill |
| Multi-workflow skill (SK-1 Warn/Fail) | Two distinct output contracts in one skill body | Split into two skills, one contract each |
| Cross-skill state assumption (SK-4 Warn/Fail) | Skill assumes state from another skill's prior execution | Remove assumption; make skill independently executable |

**Workflow encoding and instruction-layer security (Rule C/F):**
| Pattern | Check | Action |
|---|---|---|
| LLM-orchestrated multi-step chain | `next_action` dispatch table (or equivalent) drives sequential tool calls with known transitions and known exits | Apply the Rule P mechanism decision. **`nextTool` chaining** if: ≤5 steps, single Python MCP server, branching (if any) is stable and acceptable to hardcode, simple Q&A interaction only, no transaction audit. **Agentic Workflow** (`@flow`) if: branch logic may evolve, multi-step user confirmation, cross-server tools, >5 steps, or transaction audit/observability required. LLM calls entry point once, receives final result; all transitions become deterministic. |
| **Instruction-only confirmation gate on high-stakes operation** | Confirmation step, authorisation check, or mandatory approval before payment / transfer / account change / data deletion is expressed only in agent instructions or a skill body | **Severity: Critical.** Instruction-layer gates are prompt-injectable — adversarial prompting can bypass them under specific context. Move into the tool chain (`nextTool` or Agentic Workflow node); platform enforces it structurally. Cross-report: PERF-N (removes deliberation pass) + OPT-N (removes confirmation prose from instruction surface). |

**Cross-references:** Rule Q findings that also reduce token cost should note `OPT-N` from Rule O; findings that also reduce hops should note `PERF-N` from Rule P.

**This rule does NOT re-score the five dimensions.** It is a synthesis document — every REL-N item must trace back to evidence already in the main reports. When no issues are found, the report still exists and states that.

---

## How scores are assigned

Scores run from **0 to 5** across five dimensions:

| Dimension | What it asks |
|---|---|
| **1. Task Understanding** | Can the agent understand its primary job? |
| **2. Scope & Applicability** | Does the agent know when each instruction applies? |
| **3. Execution & Tool Grounding** | Can the required behavior be executed with available tools? |
| **4. Instruction Followability** | Can an LLM realistically follow all constraints at once? |
| **5. State & Conflict Manageability** | Does the prompt require hidden state tracking or produce conflicting rules? |

## Interpretation bands

| Band | Conditions |
|---|---|
| **Strong** | All dimensions 4–5 |
| **Low-risk** | Most dimensions 3–4; targeted improvements needed |
| **Moderate-risk** | Mixed scores; some fragility present |
| **High-risk** | Two or more dimensions ≤ 2 |
| **Very high-risk / Not achievable as written** | Any dimension 0–1 |

## General evaluation principles

- **Evidence-based:** Every score must be supported by direct quotes or paraphrases from the input. Claims without evidence are not valid findings.
- **Operational, not academic:** Focus on runtime reliability, not writing elegance. Evaluate what is written, not what the author probably meant.
- **Do not overpraise:** If the prompt is long, exception-heavy, or stateful, say so directly.
- **No time-based solutions:** Do not recommend wait/delay/retry-later approaches unless the prompt explicitly defines a scheduler, durable workflow, or persisted state infrastructure to support them.
- **Prioritize high-impact changes:** Fixes that improve multiple dimensions or address critical blockers come first.
