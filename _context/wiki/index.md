# Wiki Index

Quick-reference map for this repository. Read only what is relevant to your current task.

## Files

| File | Contents |
|------|----------|
| [project.md](project.md) | Project overview, goals, architecture, key modules, conventions |
| [preferences.md](preferences.md) | Working standards, style preferences, how to collaborate with AI |

## Quick Facts

- **Package name:** `ibm-watsonx-orchestrate` (ADK)
- **Language:** Python 3.11–3.14
- **Repo layout:** monorepo — main ADK in `src/`, low-level API clients in `packages/clients/`, core utilities in `packages/core/`, agentic SDK in `packages/agentic-sdk/`
- **CLI entry-point:** `src/ibm_watsonx_orchestrate/cli/main.py`
- **Tests:** `pytest` under `tests/`
- **Build:** `hatchling`
