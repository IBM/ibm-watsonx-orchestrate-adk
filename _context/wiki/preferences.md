# Working Preferences

## Code Change Standards

- **Minimal changes only.** Make the smallest diff that solves the problem. Do not refactor, rename, or clean up surrounding code unless explicitly asked.
- **No unsolicited improvements.** If a better approach is noticed, mention it briefly — do not implement it unasked.
- **Follow existing style.** Match the surrounding code's conventions (naming, spacing, import order) rather than imposing a different style.
- **All public APIs must be typed.** Every new or modified public function/method needs full type annotations.
- **Backward compatibility is mandatory.** Never remove or change the signature of a public API without a deprecation cycle.

## Validation Before Done

Before declaring a task complete, always:
1. Run `pylint` or `black --check` on changed files (or equivalent lint check)
2. Run the relevant `pytest` tests
3. Confirm no new warnings or failures were introduced

## Communication Preferences

- **Be direct and technical.** No filler phrases ("Great!", "Sure!", "Certainly!").
- **Show the diff / code first.** Explanation should be brief and follow the code, not precede it at length.
- **Don't over-explain.** If the change is obvious from the diff, no explanation is needed.
- **Flag risks concisely.** If a change has a non-obvious side effect or trade-off, note it in one sentence.

## How to Work with AI

- **Read before editing.** Never speculate about code; open the file and verify before making claims or changes.
- **Ask only when truly blocked.** Avoid unnecessary clarifying questions — use existing code patterns as the guide.
- **Prefer targeted edits.** Use `apply_diff` / `search_and_replace` over full file rewrites on existing files.
- **No extra features.** Do not add error handling, logging, or abstractions beyond what was requested.
- **Track progress on multi-step tasks.** Use a todo list for anything involving more than two steps.

## Project-Specific Notes

- New service clients go in `packages/clients/ibm_watsonx_orchestrate_clients/<domain>/` and must extend `BaseClient`
- CLI commands go in `src/ibm_watsonx_orchestrate/cli/commands/<domain>/`
- Higher-level client wrappers for the CLI/SDK go in `src/ibm_watsonx_orchestrate/client/<domain>/`
- Tests live under `tests/` and mirror the `src/` structure
