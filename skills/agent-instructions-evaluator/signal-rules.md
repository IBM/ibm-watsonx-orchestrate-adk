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

## Rule O: Token consumption optimization

**What this rule measures:** Whether the agent's main instructions and skill bodies together inflate per-turn token cost beyond what the functional requirements demand. Token inflation matters because the agent instructions are loaded on **every single turn**, and each skill body is injected on top of them at load time — both sources compound. Excess tokens increase cost, increase latency, and reduce attention quality for constraints at the edges of a long context window.

**Two optimization surfaces — always assess both:**

1. **Agent instructions (permanent per-turn cost):** These tokens are paid on every turn, not just when a skill is active. Reducing the agent instructions by 20 lines saves tokens on every call — the highest-leverage single change available. Look for: procedure steps that belong in tools, stateful protocol sections that belong in server-side state, exact-phrase rules that belong in plugins, redundant policy restatements, and overcrowded tool-call contract sections that repeat what a tool schema already specifies.

2. **Skill bodies (per-skill-load cost):** These tokens are paid each time a skill is loaded — which for active intents can mean every turn. Look for: co-load pairs, oversized bodies, preamble duplication across multiple skill bodies, LLM-side classification tables, and exact-phrase enforcement that should live in plugins.

**Always produce** a `token_optimization_report.md` as part of every evaluation. If no optimization opportunities are found after running the full checklist, the report still exists and states that — providing a baseline for future comparisons.

**Severity classification** — for each item found, classify it as:
- **High** — pattern is confirmed present and exceeds a Rule C/E/F/N threshold, or is a co-load Fail
- **Medium** — pattern is present but below a hard threshold; warrants monitoring
- **Low** — pattern is marginal or applies only to low-frequency turn types
- **None found** — checklist item checked, no instance detected

**What to assess — optimization opportunity checklist:**

*Agent instructions (permanent cost — highest leverage):*

| Pattern | Check | Optimization action |
|---|---|---|
| **Procedure steps that belong in tools** | Agent instructions contain step-by-step workflow logic (sequential steps, retry logic, error handling) that a tool could encapsulate | Move procedure body into the tool contract; reduce agent instructions to: trigger condition + tool name + result relay rule |
| **Stateful protocol sections** | Agent instructions implement a counter, session flag, or multi-turn state machine inline (Rule A) | Move state tracking to a server-side variable, tool return field, or context variable; reduce instructions to a single check of that field |
| **Overcrowded tool-call contract sections** | Tool-call contract or parameter prose sections that duplicate what a tool schema already specifies | Reduce to trigger + relay rule only; move parameter detail to the tool schema or docstring |
| **Exact-phrase rules in agent instructions tied to backend hooks** | Prefix generation, sentinel detection, verbatim relay rules in the agent instructions that trigger a plugin hook | Move to pre/post invoke plugin; reduce agent instructions to a variable substitution or remove the rule entirely |
| **Redundant scope statements** | Agent instructions restate per-skill boundary conditions that are already in each skill's `description` frontmatter | Remove from agent instructions; the skill description is the authoritative scope statement for the agent |
| **Implicit state correction logic** | Agent instructions ask the LLM to review conversation history to self-correct a missed step (Rule A pattern) | Replace with a server-side counter surfaced as a tool return field; reduce agent instructions to forwarding the field value |

*Skill bodies (per-load cost):*

| Pattern | Check | Optimization action |
|---|---|---|
| **Correlated co-load pairs** | Two skills confirmed to co-load per SK-6/Rule M | Consolidate into one skill; report estimated token reduction per affected turn |
| **Oversized skill bodies** | Any skill body >100 lines (Rule E Trigger 1); especially >150 (Trigger 2) | Identify what inflates the body: classification tables, repeated preambles, inline decision trees, prohibited-phrase lists. Recommend moving each to tools or plugins |
| **Repeated base contract prose** | Same relay/handoff/end_session rules appear in multiple skill bodies AND are already stated in agent instructions | Remove duplicated prose from skill bodies; estimate total lines × skill count savings |
| **Exact-phrase rules tied to backend systems** | Any rule requiring exact prefix generation, exact verbatim relay, or prohibited-phrase enforcement that drives a plugin hook | Move to pre/post invoke plugin; remove from LLM instruction path; report reliability gain as well as token saving |
| **LLM-side classification inside skill bodies** | Free-text-to-enum classification (e.g., reason codes, intent buckets, category fields) running inside the skill body, not via tool call | Externalize to a dedicated classification tool; removes classification table + tiebreaker prose from body |
| **Mandatory in-skill re-routing calls** | A skill body that re-calls a routing or classification tool for ambiguous inputs | After consolidation or body simplification, assess whether the re-route can be replaced by an inline decision rule |
| **Shared protocol duplication** | Multiple skill bodies each separately restate the same base relay or handoff protocol that is already stated once in agent instructions | Lift the shared protocol to agent instructions once; remove per-skill restatements |

**For each identified opportunity, report:**
1. **OPT-N label** — numbered optimization item (OPT-1, OPT-2, …)
2. **Location** — agent instructions or skill body (name)
3. **Current cost** — lines and estimated tokens consumed by this pattern today
4. **Root cause** — why the inflation exists (copy-paste, missing tool contract, coupling architecture, missing plugin, missing server-side state)
5. **Recommendation** — specific actionable change (move to tool, move to plugin, move to server-side state, consolidate skills, remove redundant prose)
6. **Projected saving** — estimated lines removed and tokens saved per affected turn; which turn types are affected and their approximate frequency
7. **Reliability benefit** — whether the change also reduces a Rule A/B/C/E/F signal (secondary gain beyond token reduction)

**Token estimation guidance:**
- Use ~7.5 tokens/line as a working approximation for instruction prose
- Agent instructions: multiply their line count × tokens/line — this cost applies to **every** turn
- Per-skill cost: multiply each skill body's line count × tokens/line — this cost applies to every turn that skill is loaded
- Per-turn cost: agent instructions + the skill body loaded on that turn (+ second skill body if co-load is confirmed)
- State these estimates as approximations; exact values depend on the specific tokenizer and model

**Anti-patterns to document** (include in the report to guide future prompt authors):
- Procedure steps and tool-call contracts kept in agent instructions instead of tool schemas
- Implicit state correction logic asked of the LLM rather than tracked server-side
- Copy-pasting base contract rules into new skill bodies
- LLM-side classification inside skill bodies (should be tool calls)
- Bi-directional cross-dispatch between skills without consolidation
- Inline exact-phrase contracts tied to backend system hooks
- Fallback skills with subjective boundaries that inflate load frequency
- Redundant scope statements in agent instructions that duplicate skill descriptions

**Report structure:** Follow Template 4 in `report-template.md`.

**What this rule does NOT do:**
- Does not re-score the five dimensions (the optimization report is a side report, not a re-evaluation)
- Does not recommend architectural changes unrelated to token cost (do not use this report to surface general achievability concerns already covered in the main reports)

**When no issues are found:** The report is still produced. Include the full checklist results showing "None found" for each pattern, state the current per-turn token budget as a baseline, and close with: "No token optimization opportunities were identified by static analysis. Re-run this evaluation after any significant change to agent instructions, skill bodies, or tool schemas."

---

## Rule P: Runtime performance optimization

**What this rule measures:** Whether the agent's execution architecture introduces avoidable runtime overhead in the form of unnecessary tool-call round-trips (RTTs), multi-hop LLM inference passes, deep orchestration layers, or coupled tool sequences that could be collapsed into deterministic pipelines. Where Rule O measures *instruction token cost*, Rule P measures *execution latency and call-graph depth* — the two compound each other but have different remedies.

**Two performance surfaces — always assess both:**

1. **Tool execution architecture:** How many LLM inference passes and tool-call RTTs does a typical turn require? Are there sequential tool calls that always fire together and could be merged, chained in a Python tool, or wrapped in an agentic workflow? Are there mandatory pre/post routing calls (e.g. a classification tool called on every turn) that add a deterministic hop regardless of intent complexity?

2. **Orchestration depth:** How many layers of agents, skills, and collaborators does a request traverse before reaching the tool that executes the actual work? Each additional layer (orchestrator → skill → sub-agent → tool) adds at least one LLM inference pass and one context-window write. Deeper stacks amplify latency variance.

**Always produce** a `performance_optimization_report.md` as part of every evaluation. If no performance optimization opportunities are found after running the full checklist, the report still exists and states that — providing a call-graph baseline for future comparisons.

**Severity classification** — for each item found, classify it as:
- **High** — pattern is confirmed and adds ≥1 RTT or inference hop to ≥20% of turns
- **Medium** — pattern adds overhead but only to a minority of turns, or the overhead is bounded
- **Low** — pattern is present but impact is marginal or limited to rare turn types
- **None found** — checklist item checked, no instance detected

**What to assess — performance optimization checklist:**

*Tool execution architecture:*

| Pattern | Check | Optimization action |
|---|---|---|
| **Mandatory unconditional tool calls** | A tool is called on every turn regardless of intent (e.g. routing classification, context hydration, peek at pending state) | Evaluate whether the call can be eliminated by returning its output as a field in a prior tool response, or moved to a pre-invoke plugin that runs outside the LLM inference loop |
| **Fixed sequential tool chains** | Two or more tools are always called in the same order on the same turn type (e.g. tool A always followed by tool B with no branch) | Merge into a single Python tool or agentic workflow step; the LLM makes one call, the chain runs deterministically server-side |
| **`next_action` multi-hop dispatch** | A tool returns a `next_action` field that causes the agent to call another tool in the same turn, potentially chaining N calls | Evaluate whether the entire chain can be wrapped in an agentic workflow or Python flow tool that executes all steps deterministically; LLM orchestrates entry and receives final result |
| **LLM-side classification before tool call** | The agent must classify or route free text before deciding which tool to call (adds one deliberation pass) | Move classification to a classification tool or a pre-invoke plugin; the tool call becomes deterministic |
| **Correlated tool sets** | A set of tools is always called together across multiple skill bodies (appears in 3+ skills) | Evaluate whether the common set can be exposed as a single composed tool, reducing the call count per turn |
| **Tool failure handling in-prompt** | The agent instructions describe what to do when a tool fails, errors, or times out — handled via LLM reasoning rather than tool contract | Move failure handling to the tool's error return schema or to an agentic workflow retry policy; remove from LLM instruction path |

*Orchestration depth and skill/collaborator architecture:*

| Pattern | Check | Optimization action |
|---|---|---|
| **Deep collaborator stack** | Agent → collaborator → sub-agent → tool (≥ 3 hops before reaching the executing tool) | Flatten: evaluate whether the intermediate layer adds routing value or merely proxies the request; merge collaborators whose scope is narrow |
| **Skill routing overhead** | Every intent requires a `load_skill` call before the domain tool can be called (adds one routing decision pass + context inject) | For high-frequency intents, evaluate whether the skill body can be collapsed into agent instructions directly, eliminating the load step; for low-frequency intents this trade-off reverses |
| **Redundant skill-level routing** | A skill body re-calls a classification or routing tool for ambiguous phrases (double routing: once at agent level, once inside skill) | After skill consolidation or body simplification, replace the in-skill re-route with a deterministic inline decision rule |
| **Collaborator over-specialization** | Many narrow collaborators each handle a single tool, when a small set of broader collaborators with richer tool access would cover the same domain with fewer hops | Consolidate collaborators that cover adjacent intents and share tool dependencies; target ≤ 1 LLM hop between orchestrator and executing tool for the most frequent intents |

*Guidelines overhead:*

| Pattern | Check | Optimization action |
|---|---|---|
| **Guidelines restating agent instructions** | Guidelines duplicate rules already in the `instructions:` field | Remove duplicates from guidelines; each guideline is evaluated as an additional constraint pass at inference time |
| **Guidelines expressing tool-call rules** | A guideline says "when X, call tool Y" — a rule that belongs in the instructions as an explicit trigger, or in the tool contract as a precondition | Move tool-call rules to instructions or tool schema; guidelines are best for behavioral guardrails (tone, safety, scope), not execution logic |
| **High guideline count** | ≥ 5 guidelines each add constraint-check overhead on every turn, even when most are irrelevant to the current intent | Evaluate each guideline: can it be merged with a related instruction rule, expressed as a tool precondition, or removed because it duplicates an existing constraint? Target ≤ 3 execution-relevant guidelines |
| **Guidelines with complex conditions** | A guideline's condition is itself a multi-clause if/then (e.g. "if the customer has said X and the journey is in state Y and tool Z has been called") | Decompose into an explicit instruction rule with a named state variable, or encode as a tool precondition; complex guideline conditions are evaluated as additional branch nodes per turn |

*Cross-cutting (token cost × latency):*

| Pattern | Check | Optimization action |
|---|---|---|
| **High token cost on mandatory turns** | The per-turn token cost from Rule O/N is Medium or High, and those tokens appear on every turn (agent instructions) | Token reduction from Rule O directly reduces input processing latency; reference Rule O recommendations and their latency impact |
| **Large skill bodies on high-frequency intents** | The most-loaded skill bodies belong to the agent's highest-volume intents | Token reduction for those specific skill bodies (Rule O) has disproportionate latency impact; prioritize them first |

**For each identified opportunity, report:**
1. **PERF-N label** — numbered performance item (PERF-1, PERF-2, …)
2. **Category** — tool execution / orchestration depth / guidelines / token×latency
3. **Current cost** — RTTs added, inference passes added, or tokens on mandatory turns
4. **Root cause** — why the overhead exists (missing tool composition, missing agentic workflow, over-decomposed collaborators, guidelines duplication)
5. **Recommendation** — specific actionable change: Python tool chain, agentic workflow wrap, collaborator consolidation, guideline removal/relocation, pre-invoke plugin migration
6. **Mechanism** — *how* the recommendation reduces latency: fewer RTTs, fewer LLM inference passes, fewer context-window writes, or reduced per-turn token cost
7. **Estimated impact** — RTTs eliminated per affected turn type, or % turns affected

**Latency model guidance:**
- Each LLM inference pass adds ~500ms–2s latency (varies by model size and load); treat as one "inference hop"
- Each synchronous tool-call RTT adds ~50ms–500ms (varies by tool complexity and network); treat as one "tool hop"
- Context-window write (skill load, collaborator handoff) adds one inference hop plus token processing overhead
- Per-turn latency ≈ (inference hops × inference latency) + (tool hops × tool latency) + (token count × processing rate)
- State these estimates as approximations; actual values require production profiling

**Anti-patterns to document** (include in the report to guide future agent architects):
- Routing classification called unconditionally on every turn instead of being absorbed into prior tool output or a pre-invoke plugin
- `next_action` multi-hop chains that are never short-circuited — every turn traverses the full chain even when the answer is deterministic
- Collaborator stacks with 3+ hops where each intermediate layer adds no domain routing value
- Guidelines used to express tool-call logic (execution branching), causing the LLM to evaluate tool routing as a constraint rather than as an instruction
- Skill load required for every intent when high-frequency intents could bypass the skill layer via direct agent-instruction handling
- Correlated tool sets called in N separate LLM turns when they could be composed into a single deterministic tool

**Relationship to Rule O (token optimization):**
Rule O and Rule P are complementary but distinct. Rule O targets instruction token cost — the input the LLM must process before generating a response. Rule P targets execution call-graph depth — the number of round-trips and inference passes per turn. Both compound latency, but their remedies differ: Rule O remedies reduce tokens; Rule P remedies reduce hops. A complete performance analysis runs both. When Rule O recommendations also reduce hops (e.g. moving logic to a tool removes both tokens and a deliberation pass), flag the dual benefit in both reports.

**Report structure:** Follow Template 5 in `report-template.md`.

**What this rule does NOT do:**
- Does not re-score the five evaluation dimensions (side report only)
- Does not cover token cost in detail — that is Rule O's scope; reference Rule O for token-specific recommendations
- Does not prescribe specific tool implementation details (Python vs. REST vs. agentic workflow) — recommend the appropriate pattern and explain why; the implementor chooses the concrete technology

**When no issues are found:** The report is still produced. Include the full checklist results showing "None found" for each pattern, present the current call-graph baseline, and close with: "No runtime performance optimization opportunities were identified by static analysis. Re-run this evaluation after any significant change to tool schemas, skill architecture, or guidelines."

---

## Rule Q: Reliability optimization

**What this rule measures:** Whether the agent's design contains patterns that produce systematic, repeatable compliance failures at runtime — failures that occur not randomly but predictably, for specific turn types, because the instructions structurally cannot be followed reliably. Where Rule O targets token cost and Rule P targets execution depth, Rule Q targets **instruction-level fragility**: the patterns that cause the agent to consistently produce wrong, missing, or corrupted output for identifiable classes of input.

Rule Q is distinct from the five achievability dimensions: the main evaluation scores *what* the achievability risk is; Rule Q identifies *specific rewrite actions* that eliminate the highest-confidence failure sources, grouped by the class of fix rather than by dimension.

**Always produce** a `reliability_optimization_report.md` as part of every evaluation. If no reliability optimization opportunities are found after running the full checklist, the report still exists and states that — providing a stability baseline for future comparisons.

**Severity classification** — for each item found, classify it as:
- **Critical** — the pattern will produce a wrong or missing output on a predictable, non-trivial fraction of production turns; no workaround exists inside the current instruction design
- **High** — the pattern produces compliance failures under specific but commonly encountered conditions (e.g. multi-intent turns, adversarial phrasing, edge-of-scope inputs)
- **Medium** — the pattern is a known fragility that will cause occasional failures; manageable with targeted rewrite
- **Low** — marginal risk; failure mode is rare or recoverable
- **None found** — checklist item checked, no instance detected

**What to assess — reliability optimization checklist:**

*Implicit state and counters (Rule A patterns):*

| Pattern | Check | Optimization action |
|---|---|---|
| **LLM-side attempt counter** | Instructions ask the LLM to count missed calls, retry attempts, or clarification turns from conversation history | Move counter to server-side state or tool return field; agent reads a field value, never counts |
| **Cross-turn "already asked" memory** | Instructions say "never ask X twice" or "remember if the user already provided Y" without an explicit context variable | Add a boolean context variable set by the tool response; instructions check the variable |
| **Journey step tracking** | Agent must infer which step of a multi-step journey it is on from conversation history rather than a server-returned `current_state` | Ensure the journey tool always returns `current_state`; instructions branch on the field value, not on history review |

*Exact-phrase and verbatim requirements (Rule B patterns):*

| Pattern | Check | Optimization action |
|---|---|---|
| **Verbatim relay with backend hook** | A prefix, sentinel string, or exact body text the LLM must produce triggers a plugin, backend system, or downstream formatter | Move production to the plugin layer; LLM produces variable content, plugin adds the exact framing |
| **Prohibited-phrase enforcement** | Instructions list N phrases the LLM must never include in a specific response type; enforcement is entirely LLM-side | Move to post-invoke plugin text filter; the filter is deterministic, the LLM is not |
| **Enum classification without tool** | LLM must classify free text to a fixed enum (e.g. `reason_a \| reason_b \| other`) inside the instruction body; no tool validates the output | Externalize to a classification tool or routing tool enrichment field that returns and validates the enum value |

*Scope and routing fragility (Rule I/J patterns):*

| Pattern | Check | Optimization action |
|---|---|---|
| **Tense-based or phrasing-dependent routing boundary** | Two skills or two intents are distinguished by grammatical tense, a single keyword, or phrase form rather than semantic intent | Replace with a CAUSE-based or object-based boundary; add explicit disambiguation examples; add a fallback tool call for ambiguous cases |
| **Subjective "last resort" fallback** | A skill or handler is described as "use when nothing else applies" without an explicit exclusion list | Add an explicit exclusion list enumerating what this skill does NOT cover; transforms a judgment-based rule to a deterministic boundary |
| **Overlapping skill descriptions** | Two skills have descriptions that cover the same user intent; routing to the correct skill requires contextual judgment that was not present at routing time | Resolve overlap: either merge the skills or rewrite one description to explicitly exclude the shared edge case |

*Conflicting and competing rules (Rule A/F patterns):*

| Pattern | Check | Optimization action |
|---|---|---|
| **Same-turn dual-field distinction** | Agent must simultaneously distinguish two similarly named fields from different sources (e.g. `action_required` vs `action_should_be_offered`) and take opposite actions depending on which is true | Sequence the checks explicitly: check field A first; only if A is false, check field B. Or consolidate into a single action-type enum at the tool layer |
| **Competing output format rules** | Instructions specify both a short-response rule (e.g. "max 2 sentences") and a verbatim relay rule (e.g. "relay the tool's response text literally") — one will be violated when the tool response is long | Explicitly prioritize: verbatim relay overrides length limits; or note the exception case |
| **Double-negative fill conditions** | A fill/no-fill rule uses a double negative: "fill only when NOT condition_A AND NOT condition_B" — cognitively dense and error-prone | Rewrite as a positive condition: "fill only when [positive state is true]" |

*Underspecified tool behavior (Rule D patterns):*

| Pattern | Check | Optimization action |
|---|---|---|
| **Missing failure handling** | A tool call has no documented failure path in the instructions — no guidance on what to do if the tool returns an error, times out, or returns unexpected output | Add a 1-line failure handler per tool: "if tool unavailable or returns error → [specific action]"; or document this in the tool's error return schema |
| **Undeclared context variable** | Instructions reference a context variable (e.g. `user_context`, `channel`) that is not declared in the YAML `context_variables:` list | Declare the variable in `context_variables:` or document explicitly that it is injected by a pre-invoke plugin |
| **`next_action` value not fully enumerated** | A dispatch table handles N named `next_action` values but does not specify what to do when an unexpected value is returned (no-match case) | Add an explicit no-match handler: "if `next_action` value is not in the table → call the tool again without changes" or "→ offer handoff" |

*Skill body–specific reliability (SK-5 patterns):*

| Pattern | Check | Optimization action |
|---|---|---|
| **Skill body exceeds followability threshold** | A skill body triggers Rule E Trigger 2 (>150 lines) or Rule F high range (>10 active rules/turn) | Decompose: identify the 2–3 sub-sections driving line count; move each to a tool, plugin, or separate skill |
| **Multi-workflow skill (SK-1 Warn/Fail)** | A skill body contains 2+ distinct primary workflows with different output contracts (e.g. verbatim relay AND free synthesis) | Split into two skills, one per workflow, with non-overlapping `description` frontmatter |
| **Cross-skill state assumption (SK-4 Warn/Fail)** | A skill body assumes state, tool output, or a routing decision that could only come from another skill having already run | Remove the assumption; make the skill independently executable by adding a check-and-call for any prerequisite state |

*Workflow encoding (Rule C/F patterns):*

| Pattern | Check | Optimization action |
|---|---|---|
| **LLM-orchestrated multi-step chain** | Instructions contain a `next_action` dispatch table (or equivalent) driving 3+ sequential tool calls where each step follows deterministically from the previous one — a sequence with known transitions and known exit conditions | Wrap the chain in an agentic workflow or `@flow` tool; the LLM calls the entry point once and receives the final result; each link in the chain becomes a guaranteed deterministic transition, not a probabilistic LLM decision |

**For each identified opportunity, report:**
1. **REL-N label** — numbered reliability item (REL-1, REL-2, …)
2. **Category** — implicit state / exact-phrase / scope-routing / conflicting rules / tool underspecification / skill body / workflow encoding
3. **Failure mode** — the specific wrong output or compliance failure this pattern produces (what goes wrong, under what conditions)
4. **Evidence** — direct quote from agent instructions or skill body; line number if available; non-English quotes must include `[Translation]`
5. **Root cause** — why the design produces this failure (missing state object / missing plugin / missing tool contract / overlapping descriptions / competing rules)
6. **Recommendation** — specific rewrite: what to change, where, and what the result should look like
7. **Reliability impact** — estimated fraction of production turns where this failure will manifest (e.g. "every SIP first turn", "~15% of cancellation turns", "rare — only on neutral-phrasing edge cases")
8. **Rule cross-reference** — which achievability dimension and Rule letter this finding ties to (for traceability back to the main report)

**Relationship to main evaluation reports:**
- Rule Q does not re-score the five dimensions — that is the main agent/skill reports' job. Rule Q takes the findings *from* those reports and synthesises them into a single, prioritised, implementation-ready rewrite plan.
- Every REL-N item must trace back to at least one finding or signal in the main agent report or a skill report. Rule Q is a synthesis document, not an independent analysis.
- Findings already addressed by Rule O (token reduction) or Rule P (hop reduction) should cross-reference those items when the fix overlaps (e.g. "moving a classification step to a tool also reduces the skill body size — see OPT-N and PERF-N").

**Anti-patterns to document** (include in the report to guide future prompt authors):
- LLM asked to count or remember across turns without external state
- Exact-phrase requirements whose correctness drives a backend system — these belong in the plugin layer
- Routing boundaries defined by grammatical form (tense, pronoun) rather than semantic intent
- Competing rules stated at the same priority level without an explicit sequencing rule
- Tool dispatch tables with no no-match handler — every dispatch table needs an explicit default case
- Skills with multiple output contracts (verbatim vs. synthesized) — one skill, one contract
- Undeclared context variables that are assumed to be available at runtime
- Multi-step deterministic sequences (3+ steps, known transitions, known exits) implemented as LLM-orchestrated dispatch tables — every link is a probabilistic decision; compound errors accumulate; move the control plane to an agentic workflow or `@flow` tool

**Report structure:** Follow Template 6 in `report-template.md`.

**What this rule does NOT do:**
- Does not re-score the five evaluation dimensions (side report only)
- Does not introduce new findings — every REL-N item must trace back to evidence already in the main reports
- Does not duplicate Rule O or Rule P recommendations — when a fix reduces both reliability and token cost or hops, note the cross-reference but do not re-explain the full recommendation

**When no issues are found:** The report is still produced. Include the full checklist results showing "None found" for each pattern, and close with: "No reliability optimization opportunities were identified by static analysis. The current design avoids all known systematic failure patterns. Re-run this evaluation after any significant change to agent instructions, skill bodies, or tool schemas."

---

## How to apply these rules

1. **Count the signals:** Extract exact counts for exact phrases, nested branches, active operational rules per turn, implicit state variables, and underspecified tools. **For agents with skills, repeat this count for each skill body (SK-5), perform overlap analysis across all skill descriptions (SK-2), identify correlated pairs (SK-6/Rule M), and compute the full performance surface (SK-7/Rule N). After all main reports are complete, synthesise the three side reports: Rule O (token optimization), Rule P (performance optimization), and Rule Q (reliability optimization) — all three are always produced.**

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