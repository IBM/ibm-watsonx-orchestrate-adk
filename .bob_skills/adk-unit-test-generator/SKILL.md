---
name: adk-unit-test-generator
description: >-
  Use when a contributor needs to generate unit tests for their ADK PR changes.
  Guides through reading the changed code, tracing execution paths, writing
  requirement-based tests before implementation, and writing edge case tests
  after, following the project's three-section file structure and AAAC-per-test
  standard.
tags:
  - unit-testing
  - test-generation
  - adk
  - wxo-clients
  - pytest
---

# ADK Unit Test Generator

## Purpose

Guide a contributor through generating well-structured, human-maintainable unit
tests for their PR changes in the `wxo-clients` repo. Tests produced by this
skill must follow the project's three-section file layout, use one action per
test, and read like documentation.

This skill is the canonical source of truth for test generation in this repo.
Do not skip or reorder steps.

---

## Step 1 — Read the changed files

For each file changed in the PR:

1. Read the full file using `read_file`.
2. Read any files it imports from that are relevant to the changes — especially
   base classes, abstract interfaces, and shared utilities the new code depends
   on.
3. Build a module dependency map:
   - What does each changed file import?
   - What abstract contracts (ABC methods, Pydantic fields, protocol methods)
     must it satisfy?
   - What does it export into the package `__all__`?

Use `GetSymbolsOverview` for large files to understand the shape before reading
method bodies. Use `FindSymbol` with `include_body: true` for specific methods
you need to trace.

Do not write any tests yet.

---

## Step 2 — Static codepath simulation

For each non-trivial public function or method introduced or changed, trace the
execution path manually — do not run the code.

**For each public method trace:**

- **Happy path** — valid inputs, normal flow, expected return value
- **Edge cases** — `None` inputs, empty collections, repeated calls,
  re-initialization, zero/negative values
- **Error paths** — what happens when a dependency raises, returns `None`, or
  returns an unexpected type
- **State mutations** — track every field that changes, in order, across the
  full call sequence

**For stateful classes, always simulate these sequences in full:**

1. Construction with defaults
2. Initialization (fresh session)
3. Primary operation (e.g. user input / update)
4. Serialization / wire format output
5. Completion / teardown
6. **Restore from persisted state** — this is where off-by-one and type
   mismatch bugs hide
7. Error recovery paths

Document each simulation as a step-by-step state trace showing field values
before and after each call. This trace is the direct source of what tests to
write — both the requirement tests in Step 3 and the edge case tests in Step 5.

---

## Step 3 — Write requirement-based tests

**Write these tests before generating any implementation code.**

From the static trace in Step 2, identify every stated contract or behavioural
requirement — what the function or class is *supposed* to do under normal
conditions. Write one test per requirement.

**File location:**

```
tests/<module_path>/test_<feature>.py
```

First check whether a test directory already exists for the module's area (e.g.
`tests/mcp_server/`, `tests/cli/`, `tests/core/`). If one exists, place the
test file there. If none exists, mirror the source path under `tests/`.

**File structure — three sections, always in this order:**

```python
"""
<One-line description of what module is under test>

<Optional: table listing each test class and the count + purpose of its tests>

    TestFoo  (N) — what this class covers
    TestBar  (N) — what this class covers
"""

# ---------------------------------------------------------------------------
# SECTION 1 — ARRANGE
# Shared constants and pytest fixtures used across multiple tests.
# Nothing in this section runs a function under test.
# ---------------------------------------------------------------------------

CONSTANT_A = ...
CONSTANT_B = ...

@pytest.fixture
def fixture_name():
    """What this fixture sets up and why it avoids filesystem/network access."""
    ...


# ---------------------------------------------------------------------------
# SECTION 2 — REQUIREMENT TESTS
# One class per subject (function, method, or behaviour group).
# Each test verifies one stated contract from the requirements.
# ---------------------------------------------------------------------------

class TestSubjectName:
    # <Optional class-level comment explaining what the group covers and any
    #  non-obvious patching convention, e.g. why the mock is patched here.>

    def test_<what_it_does>(self, fixture_name):
        # <Inline comment explaining what this test verifies and why — write
        #  for a human maintainer who does not know the full context.>
        # Arrange — test-local setup only (minimal; fixtures do the heavy lifting)

        # Act — exactly one call under test
        result = function_under_test(...)

        # Assert
        assert result == expected

        # Cleanup (omit if pytest fixtures handle it)


# ---------------------------------------------------------------------------
# SECTION 3 — EDGE CASE TESTS
# Tests for boundary conditions, error paths, and invalid inputs
# surfaced by the static codepath simulation in Step 2.
# ---------------------------------------------------------------------------

class TestSubjectNameEdgeCases:
    ...
```

**Per-test rules — enforce all of these without exception:**

- **One action per test.** A single call to the function or method under test.
  Do not chain multiple calls in one test body.
- **Inline comment required on each test method.** One plain-English comment
  directly below the `def` line explaining what contract or behaviour the test
  verifies and *why* it matters. Write it for a human maintainer. Docstrings
  are also acceptable — the project uses both — but the comment must be present
  and informative. `# Verifies X` is not enough; explain the *why*.
  Fixtures must have a docstring explaining what they set up and why they avoid
  filesystem or network access.
- **Fixtures for shared setup.** If two or more tests need the same object,
  put it in a fixture in Section 1. Never copy-paste setup code across tests.
- **Patch at the use site.** When mocking, patch the name as it is imported in
  the module under test, not the name in its origin module. Example:
  `patch("ibm_watsonx_orchestrate_mcp_server.src.environment.mcp_tools.Config")`
  not `patch("ibm_watsonx_orchestrate.cli.config.Config")`.
- **Use `assert_called_once_with()` for call-contract tests.** This verifies
  both call count and every argument name and value simultaneously, catching
  silent renames between layers.
- **Group tests by subject in a class.** One `class Test<Subject>` per function
  or behaviour group. Avoid a flat list of top-level test functions.
- **No assertions in fixtures.** Fixtures set up state only.

---

## Step 4 — Run the tests

Run the requirement tests against the current implementation:

```bash
pytest tests/<path>/test_<feature>.py -v
```

If tests fail because the implementation does not exist yet, generate the
implementation now. Then re-run.

Note every failure — do not suppress or skip. Failures are the signal that
the implementation does not match the stated requirements.

---

## Step 5 — Write edge case tests

Using the state traces from Step 2 — specifically the edge cases, error paths,
and state mutation sequences already documented — write Section 3 of the test
file.

Each edge case test must also follow the one-action-per-test rule. Do not
combine "what happens with None input" and "what happens with an empty list"
into one test.

**Required edge case categories to cover (for each function traced):**

| Category | What to test |
|---|---|
| None / missing inputs | Required params omitted or explicitly `None` |
| Empty collections | Empty list, empty dict, empty string |
| Boundary values | Off-by-one, zero, negative, max length |
| Error paths | Dependency raises an exception |
| Dependency returns None | Caller handles `None` gracefully |
| Dependency returns unexpected type | Caller does not crash |
| Restore from persisted state | Round-trip: serialize → deserialize → assert parity |

Cover every category that applies to the function under test. Skip categories
that cannot apply (document why with a comment if the omission is non-obvious).

---

## Step 6 — Patch and loop

Run the full test file:

```bash
pytest tests/<path>/test_<feature>.py -v
```

For every failure:

1. Read the failure message and the failing test body.
2. Determine whether the bug is in the implementation or in the test assertion.
   - If the implementation is wrong: fix the implementation, not the test.
   - If the test assertion was wrong (genuinely incorrect expectation): fix
     the test and document why in the docstring.
3. Re-run. Repeat until all tests pass.

Do not mark a test as `xfail` or `skip` to make the suite green. Every test
must pass for real.

---

## Step 7 — Final check

Before declaring done:

- [ ] Section 1 exists and contains all shared fixtures and constants
- [ ] Section 2 exists and covers every stated requirement
- [ ] Section 3 exists and covers edge cases from the static trace
- [ ] Every test has exactly one action
- [ ] Every test has a docstring
- [ ] No setup code is duplicated across tests — it lives in fixtures
- [ ] All tests pass: `pytest tests/<path>/test_<feature>.py -v`
- [ ] No tests are skipped or marked xfail

---

## Reference

Gold-standard example in this repo:
`tests/mcp_server/test_environment_mcp_tools.py`

- Module-level `MOCK_ENVS` constant + `mock_config` fixture → Section 1 (Arrange)
- `mock_config` fixture has a docstring; test methods use inline comments
- `TestListEnvironments`, `TestAddEnvironment`, etc. → Section 2 (Requirement tests),
  one class per tool, with a class-level comment explaining the patching convention
- `test_no_active_environment`, `test_add_insecure_and_verify_raises`,
  `test_add_missing_required_name_raises` → Section 3 style (edge / error paths)
- Every test targets exactly one behaviour; inline comments explain the *why*
- `assert_called_once_with()` used to verify full call contracts including
  argument renames between layers (e.g. MCP `activate` → controller `should_activate`)
