# Example Finding

This document shows a complete example of a well-structured finding with all required elements.

## Finding 1: Implicit state management

**Evidence**
> "mentally update the current status of the interaction"
> "avoid requesting information already known again"

**Why it matters**
The prompt asks the LLM to maintain conversation state internally, but does not define an explicit state object, counters, or durable memory. This makes compliance fragile in multi-turn conversations. The agent will:
- Forget retry counts and violate "max ONE retry" rules
- Lose track of whether it already asked a clarifying question
- Fail to remember what information the user already provided
- Inconsistently apply rules that depend on conversation history

**Deterministic or judgment-based**
Both. The phrases "mentally update" and "avoid requesting information already known again" are extractable signals (deterministic). The conclusion that this makes the prompt unachievable in production is judgment-based but strongly supported by Rule A (prompt-only state dependence).

**Score impact**
- Instruction Followability: Reduced to 1/5 due to inability to comply with state-dependent rules
- State & Conflict Manageability: Reduced to 0/5 due to severe risk from prompt-only state dependence (per Rule A)

**Recommended change**
Move conversation status into an explicit state object with fields such as:
- `retry_count_this_request`: integer counter reset per user request
- `clarification_count_this_request`: integer counter reset per user request
- `survey_step`: enum (not_started, step_1, step_2, etc.)
- `transfer_offered`: boolean flag
- `pivot_asked`: boolean flag
- `topic_stated_in_call`: boolean flag
- `known_user_facts`: dictionary of facts provided by user

Update this state object after each turn using a state management tool or system. The agent should read from this state object rather than trying to remember internally.

---

## Anatomy of a Good Finding

### 1. Evidence (Required)
- Use direct quotes from the input
- Use blockquote formatting (>)
- Include multiple quotes if they support the same finding
- Be specific: cite line numbers if available

### 2. Why it matters (Required)
- Explain the operational impact
- Focus on production failure modes
- Be concrete: what will actually go wrong?
- Avoid academic language; use practical terms

### 3. Deterministic or judgment-based (Required)
- Classify the finding clearly
- If both, explain which parts are which
- Reference signal rules when applicable (Rule A, B, C, or D)
- Be honest about uncertainty

### 4. Score impact (Required)
- List affected dimensions
- Explain how the finding affects each dimension's score
- Be specific about the severity (e.g., "reduced to 1/5" not just "lowered")
- Connect to scoring rubrics when possible

### 5. Recommended change (Required)
- Provide a specific, actionable fix
- Include examples when helpful
- Prioritize changes that are feasible to implement
- Focus on high-leverage fixes that improve multiple dimensions

---

## Common Mistakes to Avoid

### ❌ Vague evidence
"The prompt has state issues"

### ✅ Specific evidence
> "mentally update the current status of the interaction"
> "avoid requesting information already known again"

---

### ❌ Academic explanation
"This violates principles of stateless design and creates cognitive load"

### ✅ Operational explanation
"The agent will forget retry counts and violate 'max ONE retry' rules"

---

### ❌ Generic recommendation
"Fix the state management"

### ✅ Specific recommendation
"Move conversation status into an explicit state object with fields: `retry_count_this_request`, `clarification_count_this_request`, `survey_step`"

---

### ❌ Unclear classification
"This is a problem"

### ✅ Clear classification
"Both. The phrases are extractable signals (deterministic). The conclusion is judgment-based but supported by Rule A."

---

### ❌ Vague score impact
"This affects followability"

### ✅ Specific score impact
"Instruction Followability: Reduced to 1/5 due to inability to comply with state-dependent rules"

---

## Finding Categories

Common finding categories include:
- **implicit_state_requirement**: Agent must track state without explicit state object
- **exact_phrase_burden**: Too many exact-response requirements
- **tool_grounding_gap**: Required tool behavior not specified
- **subjective_classifier**: Scope or branching relies on subjective judgment
- **nested_workflow_complexity**: Too many nested conditional branches
- **hard_conflict**: Two rules prescribe different actions for same situation
- **underspecified_constraint**: Rule is vague or ambiguous
- **missing_failure_handling**: No guidance for error cases
- **competing_constraints**: Multiple constraints that cannot be satisfied simultaneously
- **runtime_performance_friction**: Instruction complexity is likely to increase token usage, reasoning overhead, tool-call variance, retry loops, or latency

Use these categories to organize your findings, but always provide the five required elements for each finding.

---

## Example Finding: Runtime performance friction

### Finding: Runtime performance friction from unresolved rule complexity

**Evidence**
> [Quote the long or conflicting rule bundle]
> [Quote the ambiguous tool trigger or exception clause]

**Why it matters**
The agent must resolve multiple competing constraints at runtime before it can answer. Even if it eventually produces a correct response, this increases token usage, latency, tool-call variance, and correction-loop risk. Instructions that require the model to simultaneously decide, execute, validate, remember, and recover in one pass create bounded but elevated performance instability.

**Deterministic or judgment-based**
Both. The rule count, branch count, prompt length, and tool gaps are deterministic signals (per Rules C, D, E, and F). The expected runtime impact is judgment-based but supported by the concentration of complexity signals.

**Score impact**
- Instruction Followability: Lowered because the model must keep many interacting constraints active simultaneously.
- Execution & Tool Grounding: Lowered if ambiguity may cause unnecessary or incorrect tool calls.
- Runtime Performance Risk: Elevated — note in the Runtime Performance Risk section as Medium or High across relevant dimensions.

**Recommended change**
Externalize deterministic branching into workflow or state-machine logic. Keep the prompt focused on judgment, language generation, and exception handling that cannot be represented deterministically. Separate high-priority rules from low-priority guidance so the model does not need to arbitrate priority at inference time.