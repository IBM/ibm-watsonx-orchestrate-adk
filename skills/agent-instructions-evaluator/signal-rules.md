# Deterministic Signal Rules

Use these rules to reduce subjectivity in scoring. These are **signals and bounds**, not automatic final verdicts.

## Rule A: Prompt-only state dependence

**Trigger:** The prompt requires tracking retry count, clarification count, survey state, or whether a user already provided information, AND no explicit state object exists.

**Scoring bounds:**
- State & Conflict Manageability should generally not exceed **2**
- Instruction Followability should generally not exceed **3**

**Why:** LLMs cannot reliably maintain hidden counters or conversation status across turns. This creates guaranteed compliance failures.

**Example red flags:**
- "mentally update the current status"
- "avoid requesting information already known again"
- "max ONE retry per request" (without external counter)
- "never ask twice in a call" (without external flag)

---

## Rule B: Exact phrase burden

**Trigger 1:** Exact-response phrases are greater than **5**

**Effect:** Note followability risk. Treat this as strong evidence that exactness may compete with other constraints (tone, brevity, context-awareness).

**Trigger 2:** Exact-response phrases are greater than **10**

**Effect:** Treat prompt-only compliance as highly fragile. The agent will fail to produce the correct exact phrase in many scenarios.

**Why:** Each exact phrase requirement adds cognitive load and reduces flexibility. When combined with other constraints, exact phrases create a high failure rate.

**What counts as an exact phrase:**
- "Respond EXACTLY with: ..."
- "Say EXACTLY: ..."
- "Your response text should say EXACTLY: ..."
- Any requirement for word-for-word reproduction

---

## Rule C: Nested rule burden

**Trigger 1:** The prompt contains more than **10** meaningful nested if/then branches

**Effect:** Note high workflow complexity risk.

**Trigger 2:** The prompt contains more than **20** meaningful nested if/then branches

**Effect:** Treat instruction-only compliance as highly fragile unless workflow logic is externalized to a state machine.

**Trigger 3:** The prompt contains more than **30** meaningful nested if/then branches

**Effect:** Treat instruction-only compliance as near-impossible. The agent cannot reliably navigate the full branch space in a single generation pass. Partial compliance is the expected outcome, not the edge case.

**Trigger 4:** The prompt contains more than **40** meaningful nested if/then branches

**Effect:** Treat instruction-only compliance as not achievable. Prompt-only control over this many branches will fail even under favorable conditions.

**Scoring bounds:**
- Prompts with >20 branches: Instruction Followability should generally not exceed **2**
- Prompts with >30 branches: Instruction Followability should generally not exceed **1**
- Prompts with >40 branches: Instruction Followability should generally not exceed **0**

**Why:** Deep nesting exceeds LLM working memory and creates navigation errors. The agent will get lost in branches, especially when workflows interact. Beyond 20 branches, the agent must hold a decision tree that exceeds the reliable working-memory capacity of most production LLMs during response generation. Beyond 30 branches, the tree is large enough that the agent will routinely follow the wrong path even with the prompt fully in context. Beyond 40 branches, the branching logic has grown into a workflow engine and belongs in deterministic tooling, not a prompt.

**What counts as a nested branch:**
- If/then/else conditions
- Exception clauses that modify other rules
- Multi-step workflows with branching
- Conditional sub-workflows

---

## Rule D: Tool-required behavior gap

**Trigger:** The prompt requires a tool call but does not specify trigger, input, output handling, AND failure handling.

**Effect:** Note an execution grounding gap. Treat tool reliability as weak or incomplete.

**Why:** Without complete tool specification, the agent must guess at invocation syntax, parameters, and result interpretation. This creates execution failures.

**Required for complete tool specification:**
1. **Tool name:** Explicit identifier (e.g., `search_knowledge_base`)
2. **Trigger conditions:** When to call the tool (e.g., "when user asks a question")
3. **Parameters:** What inputs to provide (e.g., "pass user query as `query` parameter")
4. **Result handling:** What to do with tool output (e.g., "summarize the results")
5. **Failure handling:** What to do if tool fails (e.g., "offer transfer to human")

---

## Rule E: Prompt length and attention drift

**Trigger 1:** The prompt exceeds **100 lines** of instruction content

**Effect:** Note attention drift risk. The agent may struggle to keep all constraints active simultaneously during response generation.

**Trigger 2:** The prompt exceeds **150 lines** of instruction content

**Effect:** Treat followability as fragile. The agent is likely to miss or forget constraints, especially those mentioned early or late in the prompt.

**Trigger 3:** The prompt exceeds **200 lines** of instruction content

**Effect:** Treat followability as highly fragile. Partial compliance is very likely. The agent is unlikely to reliably attend to all parts of the prompt.

**Scoring bounds:**
- Prompts >150 lines: Instruction Followability should generally not exceed **2**
- Prompts >200 lines: Instruction Followability should generally not exceed **1**

**Why:** LLMs have limited attention span during response generation. Very long prompts increase the risk of attention drift where constraints mentioned early may be forgotten by the time the agent generates a response, and constraints mentioned late may not be properly integrated with earlier context. This risk is especially high when the prompt contains dense procedural logic, nested conditions, or many interacting rules.

**Performance effect:** Long prompts also increase input token cost and may increase latency. When long prompts contain dense procedural logic, the model may spend additional reasoning effort resolving which rules apply, leading to slower and more variable responses.

**What counts toward line count:**
- Instruction content (rules, constraints, workflows, examples)
- Do NOT count: blank lines, section headers alone, or pure metadata
- Adjust for density: 100 lines of dense nested logic ≈ 150+ lines of simple instructions

**Attention drift patterns:**
- Early constraints forgotten when processing later sections
- Late constraints not integrated with earlier context
- Middle sections most vulnerable to being skipped or misremembered
- Interacting rules across distant sections fail to coordinate

---

## Rule F: Active operational rule burden

**What this rule measures:** The number of operational rules that may simultaneously apply to a single user turn. This is distinct from total rule count (Rule E measures bulk) and nested branches (Rule C measures structural complexity). A 100-rule prompt can be manageable if only 3–5 rules apply per turn. A 15-rule prompt can be unachievable if all 15 fire at once.

**What counts as an active operational rule:**
- A MUST / NEVER / ALWAYS constraint relevant to the current turn
- A conditional branch that may apply to the current input
- A required output-format constraint
- A tool invocation rule
- A failure-handling rule
- A state-dependent rule (e.g., "only ask once per call")
- An exact phrase requirement
- A safety / refusal / escalation rule

**What does not count:**
- Section headers and background context
- Examples that are not binding
- General style preferences that do not compete with operational requirements
- Rules scoped to a different task or flow that cannot apply to the current turn

**Active rule budget:**
| Active rules per turn | Risk level | Guidance |
|---|---|---|
| 0–5 | Low | Realistic target for most production agents |
| 6–10 | Manageable | Acceptable if rules are independent and prioritized |
| 11–20 | High | Followability becomes dependent on rule independence, prioritization, and prompt structure |
| 21–30 | Fragile | Prompt-only compliance is fragile; move branching, state, and validation into workflow or tooling |
| 30+ | Not achievable | Prompt is acting as a workflow engine; decompose into deterministic control logic |

**Scoring bounds:**
- More than 10 active rules per turn: Instruction Followability should generally not exceed **3**
- More than 20 active rules per turn: Instruction Followability should generally not exceed **2**
- More than 30 active rules per turn: Instruction Followability should generally not exceed **1**

**Key distinction:** Not all rules are equal. The budget is tighter for interacting rules than for independent ones:
- Simple style rules (e.g., "be concise", "avoid jargon"): 5–15 realistic
- Output-format rules: 3–7 realistic; 10+ risky
- Critical behavioral rules (MUST / NEVER / ALWAYS): 5–9 realistic; 10+ risky
- Conditional rules: 5–10 realistic; see also Rule C
- Exact phrase rules: 0–3 realistic; 5+ risky (see Rule B)
- Stateful rules: 0–2 realistic; any hidden counter/state is risky (see Rule A)
- Tool-use rules: 1–5 tools/flows realistic; any underspecified behavior is risky (see Rule D)

**The control-plane principle:** Rules about routing, retries, tool selection, escalation, validation, state transitions, "only ask once," or "after failure do X" are control-plane rules. They belong in deterministic workflow, explicit state, or tool contracts — not in the prompt. When these rules appear in the prompt, count them in the active rule budget and treat their presence as a signal that logic should be externalized.

**Why:** LLMs can follow a modest number of independent, prioritized rules. They struggle with large numbers of simultaneously active, interacting, stateful, or conflicting rules. The useful budget is not total rules in the prompt; it is active operational rules per turn.

---

## Rule G: Performance friction from instruction complexity

**Trigger:** The prompt contains a high volume of interacting constraints, long instruction content, ambiguous tool triggers, conflicting rules, or workflow logic that must be resolved by the LLM at runtime.

**Effect:** Note performance risk in addition to followability risk. The agent may require more reasoning tokens, produce longer outputs, call tools unnecessarily, enter correction loops, or show higher latency variance.

**Performance risk indicators:**
- Prompt length exceeds 100 / 150 / 200 instruction lines (see Rule E)
- Nested conditional branches exceed 10 / 20 / 30 / 40 (see Rule C)
- Active operational rules per turn exceed 10 / 20 / 30 (see Rule F)
- Tool trigger rules are ambiguous or overlapping
- Multiple rules compete in the same turn without priority
- The prompt asks the model to decide, execute, validate, remember, and recover in one pass
- Exact phrase requirements interact with tone, format, safety, or tool-use constraints
- Failure handling is prompt-only rather than workflow-managed

**Scoring impact:**
- Does not automatically reduce every dimension score
- Should influence Instruction Followability and Execution & Tool Grounding when applicable
- Should be called out separately as a Runtime Performance Risk in the report

**Why:** Unclear or conflicting instructions increase the amount of runtime deliberation needed to produce a compliant response. Even when the model eventually answers correctly, it may do so with higher latency, higher token usage, more tool calls, or greater variance across turns. Achievability is not only "can the model produce the right behavior?" — it is also "can the model produce the right behavior predictably, cheaply, and with bounded runtime variance?"

---

## Rule H: Skill single-responsibility violation (SK-1)

**Trigger:** A skill's `SKILL.md` body describes more than one primary workflow, covers more than one unrelated intent category, or calls tools from more than one logical domain.

**Effect:** Note complexity inflation. The skill is acting as a mini-orchestrator rather than a focused instruction module.

**Scoring bounds:**
- 2 primary workflows in one skill: Instruction Followability for that skill should generally not exceed **3**
- 3+ primary workflows in one skill: Instruction Followability for that skill should generally not exceed **2**; also lower agent-level Dimension 4 by at least 1 if the skill is large

**Why:** A skill that does multiple things compounds its own complexity and makes routing ambiguous. When the agent loads the skill, it inherits all its complexity — a bloated skill inflates the agent's effective active-rule budget even if the agent's own instructions are lean.

---

## Rule I: Skill scope overlap (SK-2)

**Trigger:** Two or more skills share detectable scope for the same user intent, topic, or trigger condition based on their `description` frontmatter or explicit scope statements in the body.

**Overlap ratings and scoring bounds:**

| Rating | Definition | Score impact on Dimension 2 |
|---|---|---|
| **Exact** | Same intent, same wording in both descriptions | Should not exceed **1** |
| **High** | Same intent, different wording | Should not exceed **2** |
| **Moderate** | Shared boundary conditions or edge cases | Note as risk; reduce by 1 if multiple pairs |
| **Low** | Tangential overlap only | Note only; no automatic score bound |

**Why:** When two skills overlap, the agent must decide which to load without reliable disambiguation. This forces judgment-based routing at exactly the point where deterministic routing is most important — the moment the agent selects its instruction context. Routing errors at this point cascade: the agent loads the wrong instructions, calls the wrong tools, and returns the wrong behavior.

---

## Rule J: Skill routing clarity (SK-3)

**Trigger 1:** A skill's `description` frontmatter does not explicitly state the intents it covers.
**Trigger 2:** A skill's `description` frontmatter does not include any boundary conditions (what it does NOT cover).
**Trigger 3:** A skill `name` is generic enough to match multiple skills in the same agent (e.g., `general`, `helper`, `support`).

**Effect:** Note routing clarity risk. Each trigger reduces the determinism of skill selection.

**Scoring bounds:**
- Trigger 1 alone: Dimension 2 should generally not exceed **3**
- Trigger 1 + 2 together: Dimension 2 should generally not exceed **2**
- Trigger 3: Dimension 2 should generally not exceed **3**
- All three triggers on the same skill: Dimension 2 should generally not exceed **1**

**Why:** The agent selects a skill to load based primarily on the skill's `name` and `description`. If either is vague or missing boundary conditions, the agent cannot reliably distinguish this skill from alternatives at routing time. Every skill load decision made without clear description-level guidance is effectively a guess.

---

## Rule K: Cross-skill state dependency and dependency loops (SK-4)

**Trigger 1 — Unidirectional dependency:** A skill's `SKILL.md` body contains any of the following:
- Explicit reference to another skill having run, a result from a prior skill, or state set by another skill
- Implicit assumptions about conversation state that could only exist if a specific prior skill had already executed (e.g., "the intent identified by the routing skill", "the product selected in the previous step")
- Instructions to "continue from where X skill left off" or similar
- Reference to a tool exclusively owned by another skill (in that skill's `allowed-tools` but not in the agent's top-level `tools:` or this skill's own `allowed-tools`)

**Trigger 2 — Dependency loop:** Two or more skills form a cycle in the dependency graph (A depends on B's prior execution AND B depends on A's prior execution, or any longer chain A → B → C → A). A loop means there is no valid first skill to load — the routing precondition can never be satisfied.

**How to check for loops:**
Build a directed graph across the full skill set: draw an edge from skill A to skill B whenever skill A has a Trigger 1 dependency on skill B. Then check for cycles. A cycle of any length is a loop violation.

**Effect:**
- Trigger 1 (unidirectional): Note a cross-skill coupling violation. Treat this skill as not independently executable.
- Trigger 2 (loop): Note a **dependency deadlock**. No valid execution order exists. This is a design error — report as a separate finding with higher severity than a plain unidirectional dependency.

**Scoring bounds:**
- Any Trigger 1 dependency: State & Conflict Manageability (Dimension 5) should generally not exceed **2**
- Multiple skills with Trigger 1 dependencies: Dimension 5 should generally not exceed **1**
- Any Trigger 2 loop detected: State & Conflict Manageability should generally not exceed **1**; if the loop involves skills that are required for the agent's primary use cases, score **0**

**Why:** Skills are loaded dynamically and must be independently executable. A unidirectional dependency makes routing order a hidden contract the agent must maintain reliably — LLMs cannot guarantee this. A dependency loop is strictly worse: it makes satisfying the routing precondition logically impossible regardless of instruction quality, because no skill in the cycle can be loaded first without violating another skill's precondition.

---

## Rule L: Skill body complexity (SK-5)

**Trigger:** A skill's `SKILL.md` instruction body individually exceeds any of the Rule C, E, or F thresholds when analyzed in isolation.

**Effect:** Apply the corresponding Rule C / E / F scoring bounds to that skill's effective contribution to agent-level Dimensions 4 (Instruction Followability) and 3 (Execution & Tool Grounding). A skill that is itself unachievable degrades the whole agent's achievability even if the agent's own instructions are clean.

**Additional SK-5 trigger — hidden state inside a skill:** A skill body that tracks retry counts, clarification counts, or step state without an explicit state object (Rule A pattern) is doubly risky: the hidden state lives inside a dynamically-loaded module that may be unloaded and reloaded across turns.

**Scoring bounds:** Use the same bounds as Rules A–F applied to the skill body in isolation, then apply any bound reduction to the corresponding agent-level dimension.

**Why:** Skills are not exempt from the complexity rules that govern agent instructions. A skill body is an instruction set — it is subject to attention drift (Rule E), nested branch overload (Rule C), active rule budget limits (Rule F), hidden state failure (Rule A), exact phrase brittleness (Rule B), and tool underspecification (Rule D). The fact that a skill is scoped to one domain does not make it immune to these failure modes.

## Rule M: Skill correlation and consolidation signal (SK-6)

**What this rule measures:** Whether two or more skills are so closely related in domain, tool coverage, or trigger conditions that they are likely to fire in the same turn or be loaded in immediate succession. High correlation between skills increases per-turn latency, inflates the effective instruction surface, and can create instruction interference when both skill bodies are simultaneously active in the context window.

**Trigger 1 — Shared tool coverage:** Two skills list one or more of the same tools in their `allowed-tools`. When both skills can call the same tool, the agent has no deterministic basis for choosing which skill to load first — both are valid — and the model may attempt to load both.

**Trigger 2 — Adjacent trigger conditions:** Two skills cover adjacent user intents that commonly occur in the same turn (e.g., "check balance" and "recent transactions" are separate skills but users often ask both in one message). Look for intent adjacency, not just intent identity.

**Trigger 3 — Frequent digression path:** A skill's body explicitly instructs the agent to call a tool that belongs to another skill's `allowed-tools`, or references behavior that the other skill owns. This creates a runtime dependency disguised as a digression.

**Consolidation recommendation trigger:** If two skills share ≥2 tools in `allowed-tools`, OR both exhibit SK-2 Moderate/High overlap AND cover intents likely to co-occur in a single turn, recommend consolidation into a single skill.

**Effect:** Note multi-skill-per-turn performance risk. Log the correlated pair with evidence.

**Scoring bounds (performance, not achievability):**
- 1 correlated pair: skill-load overhead risk is **Medium**
- 2+ correlated pairs: skill-load overhead risk is **High**; also note Instruction Followability risk from combined active-rule budget

**Why:** Loading a skill means injecting its `SKILL.md` body into the context window. If two skills are loaded in the same turn (or in back-to-back turns within a single user message due to multi-intent handling), the agent must reason over two full instruction bodies simultaneously. This raises active-rule counts above what either skill alone would produce, increases the probability of rule interference between the two bodies, and adds at least one additional context-window write + LLM inference pass per turn. In high-throughput production environments, this overhead is measurable and cumulative.

---

## Rule N: Skill context-load performance surface (SK-7)

**What this rule measures:** The total runtime cost introduced by the skill architecture itself, independent of any individual skill's complexity. This is the aggregate performance surface of having N skills, each with a body of B lines, that must be selectively loaded at runtime.

**Performance surface components — assess each:**

| Component | What to measure | Risk threshold |
|---|---|---|
| **Skill count** | Total number of skills in `skills:` list | >5 skills: Medium; >10 skills: High |
| **Per-skill body size** | Lines of instruction in each SKILL.md body | >100 lines/skill: Medium; >150 lines/skill: High |
| **Skill selection decision cost** | How many skills are plausible candidates per average turn (ambiguity in routing) | >2 plausible candidates/turn: Medium; >4: High |
| **Multi-skill turns** | How many user intents in the agent's domain plausibly span 2+ skills | >20% of intents: Medium; >40%: High |
| **Re-load frequency** | Does the agent's instruction body indicate that `load_skill` is called multiple times per turn (digression + return, multi-intent)? | Any confirmed multi-load pattern: Medium |
| **Skill body token cost** | Sum of tokens across all skill bodies that could plausibly be loaded in one turn | >2,000 tokens/turn: Medium; >4,000 tokens/turn: High |

**Effect:** Produce a skill performance surface summary: list each component, its measured value, and its risk rating. Include this in the Runtime Performance Risk section of the report.

**Scoring bounds:**
- Any single component at High: Runtime performance risk for `skill_load_overhead_risk` should be rated **High**
- Two or more components at Medium with no High: rate **Medium**
- All components Low: rate **Low**

**Why:** Each `load_skill` call is not free. It injects a skill body into the context window, which costs input tokens and may trigger an additional inference pass depending on the agent runtime implementation. The total performance surface is the product of skill body size × expected load frequency × disambiguation cost. Agents with many small, well-separated skills can have lower surface than agents with few large, overlapping skills — but agents with many large, overlapping skills have the worst possible surface.

---

## How to apply these rules

1. **Count the signals:** Extract exact counts for exact phrases, nested branches, active operational rules per turn, implicit state variables, and underspecified tools. **For agents with skills, repeat this count for each skill body (SK-5), perform overlap analysis across all skill descriptions (SK-2), identify correlated pairs (SK-6/Rule M), and compute the full performance surface (SK-7/Rule N).**

2. **Apply the bounds:** Use the thresholds above to establish scoring bounds (e.g., "State & Conflict Manageability should not exceed 2"). **When SK rules trigger, apply their bounds to the corresponding agent-level dimensions. When Rules M and N trigger, apply their risk ratings to the Runtime Performance Risk section.**

3. **Use judgment within bounds:** The bounds are not automatic scores. Use your judgment to score within the bounded range based on the full context.

4. **Explain the reasoning:** In your findings, cite both the deterministic signal (e.g., "20+ exact phrases") and the judgment-based conclusion (e.g., "this creates high brittleness because...").

5. **Do not fabricate counts:** If you cannot confidently count a signal, mark it as "unknown" and explain why. Do not guess.

---

## Confidence impact

When deterministic signals are counted manually (Direct Analysis Mode):
- **High confidence:** Signals that are easy to count accurately (e.g., exact phrases with "EXACTLY" keyword)
- **Medium confidence:** Signals that require interpretation (e.g., nested branches, implicit state variables)
- **Low confidence:** Signals that are ambiguous or context-dependent (e.g., subjective classifiers)

Always state your confidence level and explain what would improve it (e.g., "Confidence would be higher with automated extraction tool").