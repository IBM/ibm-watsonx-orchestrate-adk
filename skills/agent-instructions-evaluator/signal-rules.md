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

**Why:** Deep nesting exceeds LLM working memory and creates navigation errors. The agent will get lost in branches, especially when workflows interact.

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

## How to apply these rules

1. **Count the signals:** Extract exact counts for exact phrases, nested branches, implicit state variables, and underspecified tools.

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