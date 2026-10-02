---
name: adk-unit-test-reviewer
description: >-
  Use when reviewing a contributor PR to validate that submitted unit tests
  meet the ADK project standards — three-section file structure, AAAC per test,
  one action per test, shared fixtures, human-readable docstrings, and adequate
  requirement and edge case coverage.
tags:
  - unit-testing
  - test-review
  - adk
  - wxo-clients
  - pr-review
---

# ADK Unit Test Reviewer

## Purpose

Help ADK team reviewers evaluate unit tests submitted in contributor PRs.
Produce a structured, evidence-backed review report for each test file that
identifies gaps, violations, and passing criteria — with specific, quoted,
actionable feedback.

This skill is for reviewing tests that should have been generated following
the `adk-unit-test-generator` skill. The standards here are the same standards
that skill enforces.

---

## Step 1 — Locate the test files

Find all test files added or modified in the PR. If a PR URL was provided,
read the base branch from the PR metadata first:

```bash
GH_HOST=github.ibm.com gh pr view {pr_number} --repo {org}/{repo} \
  --json headRefName,baseRefName,changedFiles
```

For github.com repos, omit `GH_HOST=github.ibm.com`. If no PR URL is
available, ask the user for it before continuing.

Then list changed test files:

```bash
git diff --name-status {baseRefName}...HEAD | grep "^[AM].*test_.*\.py"
```

If no test files are present in the PR and the PR adds or modifies source
files, flag this immediately as a **blocking gap** before continuing:

> ❌ **No tests submitted.** This PR adds/modifies source files but includes
> no test file. Tests are required for all PRs. See the `adk-unit-test-generator`
> skill for how to generate them.

If test files are present, read each one in full using `read_file` before
evaluating.

---

## Step 2 — Read the source files under test

For each test file, identify what source module it is testing. Read that source
file and build a quick map of:

- All public functions and methods
- All stated contracts (what each function is documented to do)
- All error conditions the code handles

This is the baseline for evaluating coverage in Step 3.

---

## Step 3 — Static codepath simulation

For each source file under test, perform the same static codepath simulation
used during generation. This is the ground truth for what tests *should* exist.

**For each public method:**

- Trace the happy path (valid inputs, normal flow)
- Identify edge cases: `None` inputs, empty collections, repeated calls,
  re-initialization
- Identify error paths: dependency raises, returns `None`, returns unexpected
  type
- Identify state mutation sequences for stateful classes — especially the
  restore-from-persisted-state path

Document the paths you found. You will cross-reference these against the
submitted tests in Step 4.

---

## Step 4 — Evaluate each test file

For every test file, evaluate it against each dimension below. Record a rating
and quote specific evidence from the file.

---

### Dimension 1 — File structure

**Pass:** File contains all three sections in order, separated by comment
banners:
- Section 1: Arrange (constants + fixtures)
- Section 2: Requirement tests
- Section 3: Edge case tests

**Warn:** Sections are present but not labelled with comment banners, making
the structure implicit rather than explicit.

**Fail:** One or more sections are missing entirely, or the file is a flat
list of functions with no structure.

---

### Dimension 2 — AAAC compliance per test

**Pass:** Every test method has clearly separated Arrange / Act / Assert blocks.
The Act block contains exactly one call to the function or method under test.

**Warn:** Tests have correct structure but Arrange and Act are blended (e.g.
the call under test is inside the fixture setup).

**Fail:** Any test contains more than one call to the function under test in
its body, or the Act and Assert are fused into a single expression with no
ability to inspect the intermediate result.

When flagging, quote the offending test method name and the specific lines that
violate the rule.

---

### Dimension 3 — Fixture reuse

**Pass:** All setup shared across two or more tests lives in a named
`@pytest.fixture` in Section 1. Individual test methods contain only
test-local, non-repeated setup.

**Warn:** Some shared setup is in fixtures but some is copy-pasted across
test bodies.

**Fail:** No fixtures exist and setup is duplicated inline across multiple
tests.

When flagging, identify the specific setup block that is duplicated and name
every test it appears in.

---

### Dimension 4 — Single responsibility

**Pass:** Each test method tests exactly one behaviour. The method name
and docstring describe that single behaviour precisely.

**Warn:** Test name or docstring is vague (e.g. `test_works`,
`test_add_environment`), making it unclear what single behaviour is being
verified.

**Fail:** A single test method verifies multiple distinct behaviours — e.g.
calls the function twice with different inputs and asserts on both results,
or asserts on both the return value and a side effect in the same assertion
block without a clear single claim.

---

### Dimension 5 — Human-readable context

The project convention is inline comments on test methods and docstrings on
fixtures. Both forms are acceptable; the requirement is that *something*
explains the why for every test and every fixture.

**Pass:** Every test method has an inline comment or docstring that explains
what contract it verifies and *why* — not just what it calls. Every fixture
has a docstring explaining what it sets up and why it avoids filesystem or
network access.

**Warn:** Context comments are present but only restate the function name
(e.g. `# Tests list_environments`). Informative but minimal.

**Fail:** One or more test methods have neither an inline comment nor a
docstring. Or a fixture has no docstring at all.

---

### Dimension 6 — Requirement coverage

Cross-reference the test methods in Section 2 against the stated contracts
identified in Step 2.

**Pass:** Every public function or method under test has at least one test
covering its primary contract (the happy path + expected return value or
side effect).

**Warn:** Most contracts are covered but one or two minor behaviours are
missing.

**Fail:** One or more public functions are entirely untested, or a primary
contract (documented return value, documented side effect) has no
corresponding test.

List each uncovered contract explicitly.

---

### Dimension 7 — Edge case coverage

Cross-reference the edge cases and error paths surfaced in Step 3 against
the tests in Section 3.

**Pass:** Section 3 covers all categories that apply to the functions under
test:

| Category | Covered? |
|---|---|
| None / missing required inputs | ✅ / ❌ |
| Empty collections | ✅ / ❌ / N/A |
| Boundary values (off-by-one, zero, max) | ✅ / ❌ / N/A |
| Dependency raises an exception | ✅ / ❌ / N/A |
| Dependency returns None | ✅ / ❌ / N/A |
| Restore from persisted state | ✅ / ❌ / N/A |

**Warn:** Most categories are covered but one non-trivial path is missing.

**Fail:** Section 3 is absent, or the restore-from-persisted-state path is
untested for a stateful class.

---

### Dimension 8 — Bloat signal

**Pass:** No redundant tests. Each test covers a distinct behaviour not covered
by any other test in the file.

**Warn:** Two or three tests are near-identical in structure with only minor
input variation where a single parametrized test (or a clear distinction in
what is being verified) would be cleaner.

**Fail:** The file contains tests that combine multiple unrelated assertions,
tests that duplicate what another test already covers exactly, or tests that
appear to have been generated in bulk without mapping to a specific requirement
or edge case.

---

## Step 5 — Produce the review report

Write the report as a structured markdown document. Save it to:

```
.bob_context/{repo}/{pr_number}/test-review.md
```

Use this structure:

```markdown
# Test Review — PR #{pr_number}

- PR: {url}
- Branch: {headRefName}
- Reviewed by: ADK Unit Test Reviewer skill
- Date: {date}

---

## Files Reviewed

| File | Dimensions | Overall |
|---|---|---|
| tests/path/test_foo.py | D1✅ D2✅ D3⚠️ D4✅ D5❌ D6✅ D7⚠️ D8✅ | ⚠️ Needs changes |

---

## Per-file findings

### tests/path/test_foo.py

#### ✅ Passing

- D1 — File structure: All three sections present with comment banners.
- D2 — AAAC: Every test has exactly one action.
- ...

#### ⚠️ Warnings (address before merge if possible)

#### ❌ Failures (must fix before merge)

**D5 — Context missing**
The following test methods have no inline comment or docstring:
- `TestAddEnvironment.test_add_calls_controller` (line 132)
- `TestRemoveEnvironment.test_remove_calls_controller` (line 195)

Fix: Add an inline comment below the `def` line explaining what the test
verifies and why. Example:
```python
def test_add_calls_controller(self):
    # Verifies all argument defaults when only required params are supplied —
    # catches silent renames between the MCP layer and the controller.
```

---

## Coverage gaps

List any source contracts or edge case paths that are entirely absent from
the submitted tests, sourced from the static trace in Step 3.

| Gap | Severity | Recommendation |
|---|---|---|
| `activate_environment` restore path not tested | High | Add test for round-trip serialization |
| Empty env dict not tested in `list_environments` | Medium | Add edge case test in Section 3 |

---

## Verdict

- ✅ **Approve** — all dimensions pass
- ⚠️ **Request changes (minor)** — warnings only; can merge after addressing
- ❌ **Request changes (blocking)** — one or more Fail ratings; must fix before merge
```

---

## Step 6 — Feedback principles

When writing findings, follow these rules:

- **Quote the file.** Every finding must reference the specific test method
  name, line number, or code snippet it refers to. Never give vague feedback
  like "some tests are missing docstrings."
- **One fix per finding.** Each ❌ or ⚠️ entry tells the contributor exactly
  one thing to change, with an example if the fix is non-obvious.
- **Do not fail on style.** Ratings are based on the dimensions above only —
  not on naming conventions, comment style, or personal preference beyond what
  is explicitly defined.
- **Distinguish warn from fail.** A warn is something that improves
  maintainability but does not indicate a correctness risk. A fail indicates
  a missing contract test, a structural violation, or a missing docstring.
  Do not conflate them.
- **Reference the generator skill.** If a contributor's tests are structurally
  missing (no sections, no fixtures, flat file), point them to the
  `adk-unit-test-generator` skill rather than listing every individual fix.

---

## Reference

Use the template in the generator skill as the benchmark:
`.bob_skills/adk-unit-test-generator/example_test_template.py`

When a finding is borderline, check whether the submitted tests match the
structure and specificity demonstrated in that template. If they do, that is
a pass.
