# Skills Tools for IBM watsonx Orchestrate MCP Server

This module provides tools to access and manage skills bundled with the IBM watsonx Orchestrate ADK MCP server.

## Overview

The skills tools allow you to access pre-bundled skills that ship with this package. Skills are included at build time from the [IBM watsonx Orchestrate ADK repository](https://github.com/IBM/ibm-watsonx-orchestrate-adk) — no network access or git is required at runtime.

## Available Tools

### 1. `fetch_skill`

Copies a specific skill from the bundled skills to your project directory.

**Parameters:**

- `skill_name` (str, required): The name of the skill to fetch
- `output_directory` (str, optional): The directory where the skill should be saved. Auto-detected from IDE if not provided.

**Example Usage:**

```python
# Fetch a skill (auto-detects IDE folder)
result = fetch_skill("watsonx-orchestrate-agent-builder")

# Fetch a skill to a custom directory
result = fetch_skill("watsonx-orchestrate-agent-builder", "./my_skills")
```

### 2. `list_available_skills`

Lists all skills bundled with this package, including their name and description metadata parsed from each skill's `SKILL.md` frontmatter.

**Example Usage:**

```python
skills_list = list_available_skills()
```

### 3. `fetch_all_skills`

Copies all bundled skills to your project directory at once.

**Parameters:**

- `output_directory` (str, optional): The directory where skills should be saved. Auto-detected from IDE if not provided.

**Example Usage:**

```python
result = fetch_all_skills()
result = fetch_all_skills("./my_skills")
```

## IDE Auto-Detection

When `output_directory` is not provided, skills are placed in the appropriate IDE-specific folder:

| IDE      | Skills Folder      |
| -------- | ------------------ |
| IBM Bob  | `.bob/skills`      |
| OpenCode | `.opencode/skills` |
| Claude   | `.claude/skills`   |
| Cursor   | `.cursor/skills`   |
| Codex    | `.codex/skills`    |

## Typical Workflow

1. **Discover available skills:**
   ```python
   skills = list_available_skills()
   print(skills)
   ```

2. **Fetch a specific skill:**
   ```python
   result = fetch_skill("watsonx-orchestrate-python-tools", "./my_project/skills")
   ```

3. **Use the skill in your agent** — import the skill's toolkit into your watsonx Orchestrate environment.

## Example Prompt

Use this as a starting prompt with Bob, Claude, Cursor, or any AI assistant that has the MCP server connected:

> List the available watsonx Orchestrate skills, then fetch the ones needed to build a banking customer care agent. The agent should handle account inquiries, transaction lookups, and complaint routing. Use the skill documentation to guide the implementation.

## Troubleshooting

### Skill not found error

Verify the skill name is correct using `list_available_skills()`.

### No bundled skills found

The package may not have been built correctly. Reinstall with `pip install ibm-watsonx-orchestrate-mcp-server`.

### Permission errors

Ensure you have write permissions to the output directory, or try a different `output_directory`.

## Additional Resources

- [IBM watsonx Orchestrate ADK Repository](https://github.com/IBM/ibm-watsonx-orchestrate-adk)
- [IBM watsonx Orchestrate Documentation](https://www.ibm.com/docs/en/watsonx/watson-orchestrate)
- [MCP Server Documentation](../../README.md)

---

## How Skills Are Bundled

Skills are sourced from the top-level `skills/` directory in the repository and bundled into the Python package at build time using Hatchling's `force-include` directive in `pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel.force-include]
"../../skills" = "ibm_watsonx_orchestrate_mcp_server/src/skills/bundled"
```

### Building the package

```bash
cd packages/mcp-server
hatch build -t wheel
```

This produces a `.whl` file in `dist/` that contains the skills under `ibm_watsonx_orchestrate_mcp_server/src/skills/bundled/`.

### Development mode

When running from source (e.g., `python server.py`), the `bundled/` directory does not exist automatically. Create a symlink to the repo-level skills:

```bash
ln -s /absolute/path/to/skills packages/mcp-server/ibm_watsonx_orchestrate_mcp_server/src/skills/bundled
```

### Adding or updating skills

1. Add or edit skill files in the top-level `skills/` directory
2. Each skill should be in its own subdirectory with a `SKILL.md` file containing YAML frontmatter (`name` and `description`) and optionally an `examples.md`
3. Rebuild the wheel — the updated skills will be included automatically
