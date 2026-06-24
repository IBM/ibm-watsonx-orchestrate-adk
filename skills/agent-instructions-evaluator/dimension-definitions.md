# Dimension Definitions and Scoring Rubrics

This document provides complete scoring rubrics for all five evaluation dimensions.

## 1. Task Understanding

### What it asks
Can the agent understand its primary job?

### Checklist
- [ ] The agent role is clearly defined
- [ ] The primary task is explicit
- [ ] The desired output is clear
- [ ] The user interaction mode is clear
- [ ] Success criteria are understandable

### Scoring rules
- **5** = Clear role, task, output, and success criteria
- **4** = Mostly clear with minor ambiguity
- **3** = Understandable but broad
- **2** = Multiple possible interpretations
- **1** = Agent role/task is vague
- **0** = No clear task

### What to look for
- Explicit role statement (e.g., "You are a customer service agent")
- Clear task definition (e.g., "Answer questions about product features")
- Output format specification (e.g., "Provide concise answers in 2-3 sentences")
- Interaction mode clarity (e.g., "via chat", "over phone", "in email")
- Success criteria (e.g., "Resolve user questions", "Provide accurate information")

---

## 2. Scope & Applicability

### What it asks
Does the agent know when the instruction applies and when it does not?

### Checklist
- [ ] In-scope topics are listed
- [ ] Out-of-scope topics are listed
- [ ] Ambiguous topics have a defined handling path
- [ ] Escalation/refusal rules are clear
- [ ] The agent is not asked to infer business scope from vague examples alone

### Scoring rules
- **5** = Clear in-scope, out-of-scope, and ambiguous handling
- **4** = Mostly clear, minor edge cases
- **3** = Scope is understandable but subjective
- **2** = Many cases rely on model judgment
- **1** = Scope is mostly implicit
- **0** = No scope boundary

### What to look for
- Explicit in-scope list (e.g., "Handle questions about: billing, account settings, password reset")
- Explicit out-of-scope list (e.g., "Do not handle: technical support, sales inquiries")
- Handling rules for ambiguous cases (e.g., "If unclear, ask clarifying question")
- Escalation triggers (e.g., "Transfer to human if user requests it")
- Subjective classifiers that create inconsistency (e.g., "banking-adjacent", "unclear", "vague")

---

## 3. Execution & Tool Grounding

### What it asks
Can the required behavior be executed with available tools or deterministic system logic?

### Checklist
- [ ] Every required tool action is named
- [ ] Tool trigger conditions are explicit
- [ ] Tool parameters are specified
- [ ] Tool result handling is defined
- [ ] Tool failure handling is defined
- [ ] The model is not expected to simulate tool results
- [ ] The prompt separates **decide** from **execute**

### Scoring rules
- **5** = Every required action maps cleanly to a tool or system function
- **4** = Minor trigger/parameter ambiguity
- **3** = Tool flow is understandable but partly subjective
- **2** = Multiple tool decisions rely on LLM judgment
- **1** = Required tools or states are missing
- **0** = Cannot execute required behavior

### What to look for
- Named tools (e.g., "Use the `search_knowledge_base` tool")
- Trigger conditions (e.g., "Search KB when user asks a question")
- Parameter specifications (e.g., "Pass user query as `query` parameter")
- Result handling (e.g., "If KB returns results, summarize them")
- Failure handling (e.g., "If KB search fails, offer transfer to human")
- Underspecified tools (mentioned but not defined)
- LLM expected to simulate tool behavior
- **Missing tool definitions:** If tools are referenced but their formal definitions (schemas, APIs, specifications) are not included in the evaluation input, note this limitation and recommend including tool definitions for a complete evaluation

---

## 4. Instruction Followability

### What it asks
Can an LLM realistically follow all constraints at once? A prompt can be very clear and still be low-followability.

### Checklist
- [ ] The prompt has a small number of critical rules
- [ ] Critical rules are prioritized
- [ ] There are few exact-response requirements
- [ ] Exceptions are limited
- [ ] The prompt avoids many nested conditions
- [ ] The response does not need to satisfy many constraints simultaneously
- [ ] Formatting, tone, safety, and tool rules do not all compete in the same turn

### Scoring rules
- **5** = Few, prioritized, non-conflicting constraints
- **4** = Several constraints, low interaction complexity
- **3** = Many constraints, but mostly modular
- **2** = Many interacting constraints; likely partial compliance
- **1** = Very long, exception-heavy, brittle
- **0** = Impossible to comply with fully

### What to look for
- Total number of critical constraints (MUST, NEVER, ALWAYS, EXACTLY, etc.)
- Number of exact-phrase requirements (e.g., "Respond EXACTLY with: ...")
- Number of exception clauses (e.g., "EXCEPTION: Do NOT do X if Y")
- Nested conditional depth (if/then/else chains)
- Competing constraints (tone + exactness + brevity + tool rules all active)
- **Prompt length and attention drift risk:**
  - Short (≤50 lines): Low attention drift risk
  - Medium (51-100 lines): Moderate attention drift risk; prioritization becomes important
  - Long (101-200 lines): High attention drift risk; agent will miss or forget constraints
  - Very long (>200 lines): Severe attention drift; partial compliance guaranteed
  - Note: Dense procedural logic increases effective length (e.g., 100 lines of nested rules ≈ 150+ lines of simple instructions)

---

## 5. State & Conflict Manageability

### What it asks
Does the prompt require the LLM to maintain hidden state, counters, conversation status, or resolve conflicting rules?

### Checklist
- [ ] The prompt avoids implicit memory requirements
- [ ] Required state variables are explicitly named
- [ ] Retry counts are tracked outside the LLM
- [ ] Clarification counts are tracked outside the LLM
- [ ] Survey state is explicit
- [ ] Transfer state is explicit
- [ ] The agent is not asked to "mentally update" state
- [ ] The agent is not asked to remember whether something was already asked unless that fact is represented in state
- [ ] The agent is not asked to wait, delay, retry later, or follow up after a time period without explicit scheduler/workflow support
- [ ] No two rules prescribe different actions for the same situation
- [ ] Rule priority is defined when multiple rules apply

### Scoring rules
- **5** = Minimal state; no meaningful conflicts
- **4** = Some state, explicitly represented
- **3** = Moderate state burden; manageable with system support
- **2** = Heavy implicit state burden or several soft conflicts
- **1** = Prompt depends heavily on hidden LLM memory
- **0** = State/conflict requirements make the prompt unachievable

### What to look for
- Red-flag phrases: "mentally update", "remember", "avoid requesting information already known"
- Implicit counters: "max ONE retry", "never ask twice", "only once per call"
- Implicit state variables: survey step, transfer offered, topic stated, greeting handled
- Time-delay/deferred-action rules: "wait", "retry later", "follow up after", "resume after", "check back in X minutes" without explicit scheduler, durable workflow, callback mechanism, or persisted state
- Hard conflicts: two rules prescribe different actions for the same situation
- Missing rule priority when multiple rules could apply
- Workflow state tracking without explicit state machine