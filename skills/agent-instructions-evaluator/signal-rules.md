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

## How to apply these rules

1. **Count the signals:** Extract exact counts for exact phrases, nested branches, active operational rules per turn, implicit state variables, and underspecified tools.

2. **Apply the bounds:** Use the thresholds above to establish scoring bounds (e.g., "State & Conflict Manageability should not exceed 2").

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