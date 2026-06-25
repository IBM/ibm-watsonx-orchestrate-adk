# Agent Instructions Evaluator - Utility Scripts

This directory contains utility scripts for extracting metadata from watsonx Orchestrate artifacts to support agent instruction evaluation.

## Overview

These scripts help analyze watsonx Orchestrate components by extracting structured metadata without executing code or requiring runtime dependencies. They support the agent-instructions-evaluator skill's ability to assess tool grounding, execution capabilities, and architectural patterns.

## Available Scripts

### 1. extract_agent_info.py

Extracts metadata from agent YAML configuration files.

**Usage:**
```bash
python3 extract_agent_info.py <agent.yaml> [--format text|json|compact]
```

**Extracts:**
- Agent name, display name, description
- LLM configuration
- Context variables
- Collaborator agents
- Tools and toolkits
- Guidelines and restrictions
- Starter prompts
- Knowledge base configuration

**Example:**
```bash
python3 extract_agent_info.py path/to/agent.yaml
python3 extract_agent_info.py path/to/agent.yaml --format json
```

---

### 2. extract_python_tool_info.py

**Unified Python tool extractor** - handles both regular Python tools and Flow Python tools.

**Usage:**
```bash
python3 extract_python_tool_info.py <tool.py> [--format text|json|compact]
```

**Detects and extracts:**
- **Regular Python tools** (`@tool` decorator):
  - Tool name and description from decorator
  - Function parameters with type annotations
  - Return type
  - Docstrings
  
- **Flow Python tools** (`@flow` decorator):
  - Flow name, display name, description
  - Input schema
  - Function parameters
  - Estimated node count

**Examples:**
```bash
# Regular Python tool
python3 extract_python_tool_info.py path/to/convert_to_base64.py

# Flow Python tool
python3 extract_python_tool_info.py path/to/document_extractor_flow.py --format json
```

**Output for @tool:**
```
Python Tool Type: TOOL
File: path/to/tool.py

============================================================
Decorator: @tool
Function: convert_base64_test
Decorator Arguments:
  name: convert_to_base64
  description: Convert document bytes to base64-encoded string.
Parameters:
  - document_bytes: bytes
Return Type: str
```

**Output for @flow:**
```
Python Tool Type: FLOW
File: path/to/flow.py

============================================================
Decorator: @flow
Function: build_docext_flow
Decorator Arguments:
  name: custom_flow_docext_example
  display_name: custom_flow_docext_example
  description: Extraction of custom fields from a document
Parameters:
  - aflow: Flow
Return Type: Flow
Estimated Node Count: 4
```

---

### 3. extract_json_tool_info.py

**Unified JSON tool extractor** - handles both WxO Agentic Workflow (Flow) JSON and Langflow JSON formats.

**Usage:**
```bash
python3 extract_json_tool_info.py <tool.json> [--format text|json|compact]
```

**Detects and extracts:**
- **Flow JSON** (WxO Agentic Workflows):
  - Flow kind and specification
  - Input schema
  - Parameters
  - Node and edge counts
  - Node details
  
- **Langflow JSON**:
  - Tool name, description, ID
  - Version information
  - Component types used
  - Input/output nodes
  - Node details with display names and descriptions
  - Edge connections

**Examples:**
```bash
# Langflow tool
python3 extract_json_tool_info.py path/to/CityNews.json

# Flow JSON tool
python3 extract_json_tool_info.py path/to/email_update_flow.json --format json
```

**Output for Langflow:**
```
JSON Tool Type: LANGFLOW
File: path/to/CityNews.json

Name: CityNews
Description: Search for events and news in a city
Version: 1.5.0.post2
Structure:
  Nodes: 8
  Edges: 7
  Component Types: ChatInput, ChatOutput, GroqModel, TavilySearchComponent
```

**Output for Flow:**
```
JSON Tool Type: FLOW
File: path/to/flow.json

Kind: flow
Nodes: 5
Edges: 4
Input Schema:
  {
    "type": "object",
    "required": ["user_input"],
    "properties": {...}
  }
```

---

## Output Formats

All scripts support three output formats:

### Text Format (default)
Human-readable output with clear sections and formatting.
```bash
python3 extract_agent_info.py agent.yaml
```

### JSON Format
Pretty-printed JSON for programmatic processing.
```bash
python3 extract_agent_info.py agent.yaml --format json
```

### Compact Format
Single-line JSON for efficient storage or transmission.
```bash
python3 extract_agent_info.py agent.yaml --format compact
```

---

## Integration with Agent Evaluator

These scripts are designed to be called by the agent-instructions-evaluator skill during evaluation workflows:

1. **Agent Analysis**: Use `extract_agent_info.py` to understand agent configuration, collaborators, and available tools
2. **Tool Grounding**: Use `extract_python_tool_info.py` and `extract_json_tool_info.py` to verify that tools referenced in agent instructions actually exist and match expected signatures
3. **Capability Assessment**: Analyze tool parameters and return types to assess whether the agent's instructions align with actual tool capabilities

### Example Workflow

```bash
# 1. Extract agent metadata
python3 extract_agent_info.py agent.yaml --format json > agent_meta.json

# 2. Extract tool metadata for each tool referenced
python3 extract_python_tool_info.py tool1.py --format json > tool1_meta.json
python3 extract_json_tool_info.py tool2.json --format json > tool2_meta.json

# 3. Use metadata to evaluate instruction achievability
# (performed by the agent-instructions-evaluator skill)
```

---

## Technical Details

### Python Tool Detection

The `extract_python_tool_info.py` script uses AST (Abstract Syntax Tree) parsing to:
- Detect decorator type (`@tool` or `@flow`)
- Extract decorator arguments without executing code
- Parse type annotations safely
- Extract docstrings and function signatures

### JSON Tool Detection

The `extract_json_tool_info.py` script distinguishes between formats by:
- **Langflow**: Presence of `data.nodes`, `data.edges`, `data.viewport` structure with Langflow-specific node format
- **Flow**: Presence of `spec.kind = "flow"` or top-level `nodes`/`edges` without Langflow structure

### Dependencies

- Python 3.7+
- PyYAML (for agent YAML parsing)

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Error Handling

All scripts provide clear error messages and appropriate exit codes:
- **Exit 0**: Success
- **Exit 1**: Error (file not found, parse error, etc.)
- **Exit 2**: Low confidence detection (for type detection scripts)

---

## Testing

Test the scripts with example files:

```bash
# Test agent extraction
python3 extract_agent_info.py ../../../examples/local/P4AG_Annie-dev/agents/supervisor_agent/anniex_dev.yaml

# Test Python tool extraction (regular tool)
python3 extract_python_tool_info.py ../../../examples/local/P4AG_Annie-dev/tools/python/employee_data_management/convert_to_base64/convert_file_to_base64.py

# Test Python tool extraction (flow tool)
python3 extract_python_tool_info.py ../../../examples/flow_builder/document_extractor/tools/document_extractor_flow.py

# Test JSON tool extraction (Langflow)
python3 extract_json_tool_info.py ../../../examples/langflow/travel_advice/tools/CityNews.json

# Test JSON tool extraction (Flow)
python3 extract_json_tool_info.py ../../../examples/local/P4AG_Annie-dev/tools/flow/email_update_flow/email_update_teams_test.json
```

---

## Future Enhancements

Potential additions:
- OpenAPI tool metadata extraction
- Toolkit metadata extraction
- Cross-reference validation (verify all referenced tools exist)
- Dependency graph generation
- Tool compatibility checking