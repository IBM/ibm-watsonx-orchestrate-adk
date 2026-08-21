# Agent Instructions Evaluator - Utility Scripts

This directory contains utility scripts for extracting metadata from watsonx Orchestrate artifacts to support agent instruction evaluation.

## Overview

These scripts help analyze watsonx Orchestrate components by extracting structured metadata without executing code or requiring runtime dependencies. They support the agent-instructions-evaluator skill's ability to assess tool grounding, execution capabilities, and architectural patterns.

## Available Scripts

### 1. extract_agent_info.py

Extracts metadata from agent YAML configuration files.

**Usage:**
```bash
python3 extract_agent_info.py <agent.yaml> [--json] [--compact] [--field <field>] [--search-root <path>]
```

**Extracts:**
- Agent name, display name, description
- LLM configuration
- Context variables
- Collaborator agents
- Tools and toolkits
- Guidelines count
- Instructions length
- Skills list — with each skill resolved to its SKILL.md location, `allowed-tools`, scripts, and references

**Examples:**
```bash
# Text summary (default)
python3 extract_agent_info.py agent.yaml

# JSON output
python3 extract_agent_info.py agent.yaml --json

# Single field
python3 extract_agent_info.py agent.yaml --field skills

# Override skill search root (useful when agent.yaml is nested deep)
python3 extract_agent_info.py agent.yaml --search-root /path/to/project
```

---

### 2. extract_tool_info.py

**Unified tool extractor** — auto-detects file type and dispatches to the appropriate extraction logic.

**Usage:**
```bash
python3 extract_tool_info.py <file.py|file.json|file.yaml> [--json|--compact]
```

**Detects and extracts:**

- **Python `.py`** — `@tool` decorator → regular Python tool; `@flow` decorator → Python flow tool
  - Tool name and description from decorator
  - Function parameters with type annotations
  - Return type and docstring
  - Estimated node count (flow tools)

- **JSON `.json`** — `spec.kind == "flow"` → WxO Agentic Workflow; `data.nodes` (list) → Langflow workflow
  - Flow/workflow name, description, input/output schemas
  - Node and edge counts, node details

- **YAML `.yaml/.yml`** — `kind: knowledge_base` → WxO Knowledge Base; `kind: mcp` → MCP Toolkit
  - Knowledge base documents and conversational search config
  - MCP toolkit transport, URL, and tool list

**Examples:**
```bash
# Python tool
python3 extract_tool_info.py path/to/my_tool.py

# Python flow tool (JSON output)
python3 extract_tool_info.py path/to/my_flow.py --json

# Agentic Workflow JSON
python3 extract_tool_info.py path/to/workflow.json

# Langflow JSON
python3 extract_tool_info.py path/to/flow.json --json

# Knowledge Base YAML
python3 extract_tool_info.py path/to/knowledge_base.yaml

# MCP Toolkit YAML
python3 extract_tool_info.py path/to/mcp_toolkit.yaml
```

**Output for @tool:**
```
Tool Type: TOOL  (file: python)
File: path/to/my_tool.py

============================================================
Decorator: @tool
Function: my_function
Decorator Arguments:
  name: my_tool_name
  description: What this tool does.
Parameters:
  - param_one: str
  - param_two: int
Return Type: str
```

**Output for @flow:**
```
Tool Type: FLOW  (file: python)
File: path/to/my_flow.py

============================================================
Decorator: @flow
Function: build_flow
Decorator Arguments:
  name: my_flow_name
  display_name: My Flow
  description: Extracts custom fields from a document
Parameters:
  - aflow: Flow
Return Type: Flow
Estimated Node Count: 4
```

**Output for Langflow JSON:**
```
Tool Type: LANGFLOW  (file: json)
File: path/to/flow.json

Name:         MyFlow
Description:  Search for events and news
Version:      1.5.0
Structure:
  Nodes: 8
  Edges: 7
  Component Types: ChatInput, ChatOutput, GroqModel, TavilySearchComponent
```

**Output for Agentic Workflow JSON:**
```
Tool Type: AGENTIC_WORKFLOW  (file: json)
File: path/to/workflow.json

Name:         my_workflow
Display Name: My Workflow
Description:  Processes user requests end to end
Structure:
  Nodes       : 5
  Edges       : 4
  Tool nodes  : 3
  User nodes  : 1
  Sub-flows   : 0
```

---

## Output Formats

Both scripts support three output formats:

### Text Format (default)
Human-readable output with clear sections and formatting.
```bash
python3 extract_agent_info.py agent.yaml
python3 extract_tool_info.py tool.py
```

### JSON Format
Pretty-printed JSON for programmatic processing.
```bash
python3 extract_agent_info.py agent.yaml --json
python3 extract_tool_info.py tool.py --json
```

### Compact Format
Single-line JSON for efficient storage or transmission.
```bash
python3 extract_agent_info.py agent.yaml --compact
python3 extract_tool_info.py tool.py --compact
```

---

## Integration with Agent Evaluator

These scripts are designed to be called by the agent-instructions-evaluator skill during evaluation workflows:

1. **Agent Analysis**: Use `extract_agent_info.py` to understand agent configuration, collaborators, and available tools
2. **Tool Grounding**: Use `extract_tool_info.py` to verify that tools referenced in agent instructions actually exist and match expected signatures
3. **Capability Assessment**: Analyze tool parameters and return types to assess whether the agent's instructions align with actual tool capabilities

### Example Workflow

```bash
# 1. Extract agent metadata
python3 extract_agent_info.py agent.yaml --json > agent_meta.json

# 2. Extract tool metadata for each tool referenced
python3 extract_tool_info.py tool1.py --json > tool1_meta.json
python3 extract_tool_info.py tool2.json --json > tool2_meta.json

# 3. Use metadata to evaluate instruction achievability
# (performed by the agent-instructions-evaluator skill)
```

---

## Technical Details

### Python Tool Detection

`extract_tool_info.py` uses AST (Abstract Syntax Tree) parsing for Python files to:
- Detect decorator type (`@tool` or `@flow`)
- Extract decorator arguments without executing code
- Parse type annotations safely
- Extract docstrings and function signatures

### JSON Tool Detection

`extract_tool_info.py` distinguishes between JSON formats by:
- **Langflow**: Presence of `data.nodes`, `data.edges`, `data.viewport` structure with Langflow-specific node format
- **Agentic Workflow**: Presence of `spec.kind = "flow"` or top-level `nodes`/`edges` without Langflow structure

### Dependencies

- Python 3.7+
- PyYAML (for agent YAML and YAML tool parsing)

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Error Handling

All scripts provide clear error messages and appropriate exit codes:
- **Exit 0**: Success
- **Exit 1**: Error (file not found, parse error, unsupported format, etc.)
