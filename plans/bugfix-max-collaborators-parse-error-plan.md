# Plan: Downgrade max-collaborators error to warning during agent list/get

## Overview

`agents list` fails to parse any agent that has more than 10 collaborators, even when
that agent was legally created via the Builder UI. The 10-collaborator cap is a
**client-side write guard** — it should not prevent the CLI from _reading_ agents
that already exist on the server.

The `validation_context` mechanism is already used in `validate_customer_care_fields`
to turn `BadRequest` into a `logger.warning` on read operations. This fix applies
the same pattern to the collaborator-count check.

---

## Sub-Task 1 — Fix `validate_agent_fields` in `types.py`

**Intent**
Make the `> 10 collaborators` check respect the existing `validation_context`.
On write paths (`import`, `create`, `update`) it still raises `BadRequest`.
On read paths (`list`, `get`, `get_by_id`, `prefetch`) it logs a warning and
continues, so the agent appears in the output rather than as a parse error.

**Expected Outcomes**
- `agents list` no longer drops agents with > 10 collaborators.
- Creating/importing an agent with > 10 collaborators still fails with the
  existing `BadRequest` message.
- A `logger.warning` is emitted on read so operators are aware.

**Todo List**
- [ ] In `validate_agent_fields` (types.py ~line 312), read `validation_context`
      and branch: warn on read contexts, raise on write contexts.

**Relevant Context**
- `src/ibm_watsonx_orchestrate/agent_builder/agents/types.py` — `validate_agent_fields()` line 298
- Read contexts: `"list"`, `"get"`, `"get_by_id"`, `"prefetch"` (same set used in `validate_customer_care_fields` line 387)
- `validation_context` is set to `"list"` at `agents_controller.py` line 1936

**Status** `[ ] pending`

---

## Sub-Task 2 — Add tests

**Intent**
Cover the new branching behaviour so a future refactor cannot silently revert it.

**Expected Outcomes**
- New test: > 10 collaborators in `list` context → no exception raised, warning logged.
- Existing tests still pass: > 10 collaborators outside context → `BadRequest`.
- Existing test: ≤ 10 collaborators → passes unchanged.

**Todo List**
- [ ] In `tests/agent_builder/agent/test_agent.py`, add
  `test_max_collaborators_exceeded_warns_in_list_context` that sets
  `validation_context` to `"list"`, constructs an `Agent` with 13 collaborators,
  asserts no exception, and asserts a warning was logged.

**Relevant Context**
- `tests/agent_builder/agent/test_agent.py` lines 450-466 (existing collaborator tests)
- Use `pytest.warns` or `caplog` fixture to assert the warning.
- Import `validation_context` from `ibm_watsonx_orchestrate.agent_builder.agents.types`

**Status** `[ ] pending`
