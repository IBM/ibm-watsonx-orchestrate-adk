# Evaluation Rules Summary

This document is a concise reference for the deterministic signal rules applied during every agent instructions evaluation. Copy it into any report set so reviewers can interpret scores and findings without needing to access the full skill directory.

Rules **A–G** apply to all agent instruction sets and system prompts. Rules **H–N** (prefixed SK) apply specifically to agents that use a `skills:` architecture with individual `SKILL.md` files.

---

## Core Rules (apply to all agents)

### Rule A — Prompt-only state dependence
**What it checks:** Whether the prompt requires tracking retry counts, clarification counts, survey state, or "already asked" flags without an explicit external state object.

**Why it matters:** LLMs cannot reliably maintain hidden counters or conversation status across turns. Any rule that depends on this produces guaranteed compliance failures.

**Red-flag phrases:** "mentally update the current status", "avoid requesting information already known", "max ONE retry per request", "never ask twice in a call"

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

**Score bounds:** Apply the same bounds as Rules A–F to the skill body in isolation, then carry any bound reduction to the corresponding agent-level dimension.

**Additional trigger:** A skill body that tracks retry counts or step state without an explicit state object (Rule A pattern) is doubly risky — the hidden state lives inside a dynamically loaded/unloaded module.

---

### Rule M — Skill correlation and consolidation signal (SK-6)
**What it checks:** Whether two or more skills are so closely related in domain, tool coverage, or trigger conditions that they are likely to fire in the same turn or be loaded in immediate succession.

**Triggers:**
1. Two skills list one or more of the same tools in `allowed-tools`
2. Two skills cover adjacent user intents that commonly occur in the same turn
3. A skill's body references behavior or tools that belong to another skill

**Consolidation trigger:** Two skills share ≥ 2 tools in `allowed-tools`, OR both have SK-2 Moderate/High overlap AND cover co-occurring intents.

**Risk ratings:**
- 1 correlated pair: skill-load overhead risk is **Medium**
- 2+ correlated pairs: skill-load overhead risk is **High**; also note Instruction Followability risk from combined active-rule budget

---

### Rule N — Skill context-load performance surface (SK-7)
**What it checks:** The total runtime cost introduced by the skill architecture itself — the aggregate performance surface of having N skills, each with a body of B lines, that must be selectively loaded at runtime.

**Performance surface components:**
| Component | Medium threshold | High threshold |
|---|---|---|
| Skill count | > 5 skills | > 10 skills |
| Per-skill body size | > 100 lines/skill | > 150 lines/skill |
| Routing ambiguity (plausible candidates/turn) | > 2 candidates | > 4 candidates |
| Multi-skill turns (% of intents spanning ≥ 2 skills) | > 20% | > 40% |
| Confirmed multi-load per turn | Any confirmed pattern | — |
| Combined token cost (loadable in one turn) | > 2,000 tokens | > 4,000 tokens |

**Overall rating:**
- Any single component at High → skill-load overhead risk = **High**
- Two or more components at Medium (no High) → **Medium**
- All components Low → **Low**

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
