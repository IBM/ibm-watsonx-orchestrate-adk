# Project Overview

## What This Project Is

The **IBM watsonx Orchestrate Agent Development Kit (ADK)** is a Python library and CLI tool that enables developers to build, configure, and deploy AI agents on the IBM watsonx Orchestrate platform.

It supports:
- Local development via **watsonx Orchestrate Developer Edition** (fully self-contained, runs via Docker Compose)
- Connecting to a **production watsonx Orchestrate instance** for team-scale deployment
- Integrating agents and tools built on third-party frameworks (e.g., LangFlow, LangChain)

**Audience:** Both internal IBM developers and external customers.

## Main Goals and Objectives

- Provide a clean, typed Python SDK for all watsonx Orchestrate services
- Expose a CLI (`ibm_watsonx_orchestrate.cli`) covering the same surface area as the SDK
- Keep the `packages/clients` layer thin (raw API clients) and let `src/` layer add higher-level abstractions
- Support both hosted (SaaS/cloud) and local (Developer Edition) deployment targets

## Key Stakeholders / Users

- **External customers** building agents and tools on the watsonx Orchestrate platform
- **Internal IBM developers** contributing features, maintaining the SDK, and building integrations

## Repository Layout

```
wxo-clients/
├── src/ibm_watsonx_orchestrate/    # Main ADK package (published as ibm-watsonx-orchestrate)
│   ├── agent_builder/              # Agent construction helpers
│   ├── cli/                        # Typer-based CLI
│   │   └── commands/               # One sub-folder per command domain
│   ├── client/                     # High-level client wrappers (per service)
│   ├── flow_builder/               # Flow/workflow construction
│   ├── run/                        # Runtime execution helpers
│   └── utils/                      # Shared ADK utilities
├── packages/
│   ├── clients/                    # Low-level REST API clients (ibm-watsonx-orchestrate-clients)
│   │   └── ibm_watsonx_orchestrate_clients/
│   │       ├── common/             # BaseClient, credentials, errors, utils
│   │       ├── agents/             # Agents API client
│   │       ├── tools/              # Tools API client
│   │       ├── connections/        # Connections API client
│   │       ├── knowledge_bases/    # Knowledge bases API client
│   │       ├── chat/               # Chat/threads API client
│   │       └── ...                 # (channels, models, toolkit, etc.)
│   ├── core/                       # Shared core utilities (ibm-watsonx-orchestrate-core)
│   ├── agentic-sdk/                # Agentic SDK sub-package
│   └── mcp-server/                 # MCP server integration
├── tests/                          # pytest test suite
├── examples/                       # Usage examples
└── agents/, tools/, skills/, ...   # Example/template resource definitions
```

## Key Service Domains (clients + CLI commands)

| Domain | packages/clients path | CLI command |
|---|---|---|
| Agents | `agents/` | `wxo agents` |
| Tools | `tools/` | `wxo tools` |
| Connections | `connections/` | `wxo connections` |
| Knowledge Bases | `knowledge_bases/` | `wxo knowledge-bases` |
| Chat / Threads | `chat/`, `threads/` | `wxo chat` |
| Channels | `channels/` | `wxo channels` |
| Models | `models/` | `wxo models` |
| Toolkit | `toolkit/` | `wxo toolkit` |
| LangFlow | `langflow/` | `wxo langflow` |
| Phone / Voice | `phone/`, `voice_configurations/` | `wxo phone` |
| Analytics | `analytics/` | — |
| AI Builder | `ai_builder/` | — |

## Important Conventions

- **Base class pattern:** all service clients extend a shared `BaseClient` in `packages/clients/ibm_watsonx_orchestrate_clients/common/base_client.py`
- **Typed public APIs:** all public methods and return values must have full type annotations
- **Backward compatibility:** never break a public API without a deprecation cycle first
- **Versioning:** version is sourced from `src/ibm_watsonx_orchestrate/__init__.py` and mirrored to sub-packages via `hatch_build.py`
- **Build system:** `hatchling` with a custom `hatch_build.py` hook for dependency injection

## Tech Stack

| Concern | Tool |
|---|---|
| Language | Python 3.11–3.14 |
| Build | hatchling + custom hatch_build.py |
| HTTP client | httpx |
| CLI framework | Typer + Click |
| Validation | Pydantic v2 |
| Testing | pytest, pytest-cov, pytest-mock, pytest-asyncio |
| Linting / Formatting | pylint, black |
| Auth | ibm-cloud-sdk-core, PyJWT |
