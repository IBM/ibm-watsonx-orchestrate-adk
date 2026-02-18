# Flow UI to Python Converter - Implementation Architecture

## Overview

This converter transforms wxO Agentic Model JSON representations into equivalent Python code using the wxO ADK Flow programming model. The goal is to enable developers to continue working on flows in Python after they've been created in the UI.

## Architecture Components

### 1. Entry Point: `main.py`

The main entry point orchestrates the entire conversion process:

**Key Responsibilities:**
- Command-line argument parsing
- JSON file loading and preprocessing
- Flow model validation
- Python code generation orchestration
- Output file management

**Preprocessing Pipeline:**
1. **Reference Conversion**: Converts JSON Schema `$ref` to `ref` for compatibility with Pydantic models
2. **Embedded Schema Extraction**: Recursively extracts inline schemas and moves them to top-level `schemas` section
3. **Schema Reference Generation**: Creates references (`#/schemas/schema_name`) for extracted schemas

**Flow Construction:**
- Uses `build_flow_from_json()` to construct proper Flow objects with specialized node types
- Handles nested flows (UserFlow, Loop, Foreach)
- Processes edges and data maps
- Validates all node specifications

### 2. Code Generator: `node_py_generator.py`

The core code generation engine that converts Flow objects to Python code.

#### 2.1 Schema Generation

**Functions:**
- `generate_schema_classes()`: Generates Pydantic BaseModel classes for all schemas
- `generate_schema_class()`: Creates individual schema class with proper field types
- `get_schema_class_name()`: Converts schema names to valid Python class names
- `resolve_schema_ref()`: Resolves schema references to actual schema objects

**Schema Handling:**
- Converts JSON Schema types to Python types (string→str, number→float, etc.)
- Handles nested schemas and arrays
- Generates Field() constructors with descriptions, defaults, and titles
- Tracks required vs optional fields
- Avoids duplicate class generation

#### 2.2 Node Code Generation

**NodePyGenerator Class:**

Core method: `to_py(node, flow_var, schema_class_map, use_helpers)`
- Dispatches to specialized generators based on node type
- Returns Python code as string

**Specialized Node Generators:**

1. **Branch Nodes** (`_generate_branch_node`):
   - Handles evaluator expressions (simple or complex)
   - Generates Conditions with NodeIdCondition/EdgeIdCondition
   - Creates case statements (true/false/default/custom)
   - Supports match policies (FIRST_MATCH, ANY_MATCH)

2. **Flow Nodes** (UserFlow, Loop, Foreach):
   - `_generate_user_flow_node()`: Creates user flows with nested nodes
   - `_generate_loop_flow_node()`: Creates loop flows with evaluator
   - `_generate_foreach_flow_node()`: Creates foreach flows with item schema
   - Each generates a separate builder function for the nested flow

3. **User Nodes** (`_generate_user_node`):
   - Handles forms with multiple fields
   - Handles standalone fields
   - Generates UserField objects with proper kind, direction, text
   - Processes input_map for field data mapping

4. **Script Nodes** (`_generate_script_node`):
   - Generates script nodes with function references
   - Handles position metadata

5. **Generic Nodes** (`_generate_any_node`):
   - Handles ToolNode, AgentNode, PromptNode, DecisionsNode, TimerNode, etc.
   - Uses pattern matching to determine mandatory vs optional fields
   - Generates appropriate constructor calls

**Common Attribute Generation:**

`_generate_common_node_attributes()`:
- Generates node creation with name, display_name, description
- Handles input_schema, output_schema, private_schema references
- Processes mandatory fields specific to node type
- Calls data map generation

#### 2.3 Data Mapping

**Functions:**
- `_generate_datamap_assignment()`: Generates input/output mapping code
- Handles `map_input()` and `map_output()` calls
- Processes value expressions and default values

#### 2.4 Edge Generation

`_generate_edges()`:
- Connects nodes using `flow.edge(start, end, id=...)`
- Handles START and END constants
- Processes edge IDs for branch conditions

#### 2.5 Flow Function Generation

**Functions:**
- `generate_flow_decorator()`: Creates @flow decorator with metadata
- `generate_function_signature()`: Creates function definition
- `generate_flow_py_code()`: Main orchestrator for flow code generation

**Two-Pass Generation:**
1. **First Pass**: Generate all nodes to collect nested flow functions
2. **Second Pass**: Write main flow content and append nested flow functions

### 3. Utility: `compare_flow.py`

Simple utility for comparing JSON files using DeepDiff to validate conversion accuracy.

## Code Generation Flow

```
JSON File
    ↓
[Preprocessing]
    ├─ Convert $ref → ref
    ├─ Extract embedded schemas
    └─ Generate schema references
    ↓
[Flow Construction]
    ├─ Build Flow object hierarchy
    ├─ Create specialized node instances
    └─ Process edges and data maps
    ↓
[Code Generation]
    ├─ Generate imports
    ├─ Generate schema classes (Pydantic models)
    ├─ Generate helper functions (optional)
    ├─ Generate main flow function
    │   ├─ Flow decorator
    │   ├─ Function signature
    │   ├─ Node creation code
    │   └─ Edge connections
    └─ Generate nested flow functions
    ↓
Python File
```

## Key Design Patterns

### 1. Visitor Pattern
NodePyGenerator acts as a visitor, dispatching to specialized generators based on node type.

### 2. Two-Phase Generation
- **Phase 1**: Collect nested flow functions during node traversal
- **Phase 2**: Write main flow and append collected functions

### 3. Schema Reference Resolution
Maintains `schema_class_map` dictionary to resolve schema references to generated class names.

### 4. Safe Attribute Access
Uses `safe_getattr()` and `safe_get()` to handle missing attributes gracefully.

### 5. Variable Name Sanitization
Converts node IDs to valid Python identifiers using `get_valid_variable_name()`.

## Node Type Support

| Node Type | Generator Method | Special Handling |
|-----------|-----------------|------------------|
| Branch | `_generate_branch_node` | Evaluator, conditions, cases |
| UserFlow | `_generate_user_flow_node` | Nested flow function |
| Loop | `_generate_loop_flow_node` | Nested flow function, evaluator |
| Foreach | `_generate_foreach_flow_node` | Nested flow function, item schema |
| User | `_generate_user_node` | Forms, fields, input maps |
| Script | `_generate_script_node` | Function reference |
| Tool | `_generate_any_node` | Tool reference |
| Agent | `_generate_any_node` | Agent reference |
| Prompt | `_generate_any_node` | System/user prompts, LLM config |
| Decisions | `_generate_any_node` | Rules, default actions |
| Timer | `_generate_any_node` | Delay configuration |
| Start/End | `_generate_any_node` | Position metadata |

## Data Structures

### Flow Object Hierarchy
```
Flow
├── spec: FlowSpec
├── nodes: Dict[str, Node]
│   ├── ToolNode
│   ├── UserNode
│   ├── Branch
│   ├── UserFlow (nested Flow)
│   ├── Loop (nested Flow)
│   ├── Foreach (nested Flow)
│   └── ... other node types
├── edges: List[FlowEdge]
├── schemas: Dict[str, JsonSchemaObject]
└── metadata: Dict[str, Any]
```

### Node Specification
```
NodeSpec
├── name: str
├── display_name: Optional[str]
├── description: Optional[str]
├── kind: str
├── input_schema: Optional[SchemaRef]
├── output_schema: Optional[SchemaRef]
├── private_schema: Optional[SchemaRef]
└── ... node-specific fields
```

## Generated Code Structure

```python
# Imports
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END, ...
from ibm_watsonx_orchestrate.flow_builder.types import ...

# Schema Classes (Pydantic models)
class InputSchema(BaseModel):
    field1: str = Field(description="...")
    field2: Optional[int] = Field(default=None)

# Helper Functions (optional)
def create_data_map(assignments): ...

# Main Flow Function
@flow(
    name="my_flow",
    display_name="My Flow",
    input_schema=InputSchema,
    ...
)
def build_my_flow_flow(aflow: Flow) -> Flow:
    # Node creation
    node1: ToolNode = aflow.tool(name="node1", ...)
    node2: UserNode = aflow.field(name="node2", ...)
    
    # Data mapping
    node1.map_input("field", "expression", default)
    
    # Edge connections
    aflow.edge(START, node1)
    aflow.edge(node1, node2)
    aflow.edge(node2, END)
    
    return aflow

# Nested Flow Functions
def build_nested_flow(user_flow: UserFlow):
    # Nested flow nodes and edges
    ...
    return user_flow
```

## Command-Line Interface

```bash
python main.py -f input.json -o output.py [options]

Options:
  -f, --file              Input JSON file path
  -o, --output            Output Python file path
  -n, --name              Rename the flow
  -d, --display-name      Set new display name
  --remove-tool-uuid      Remove tool UUIDs
  -v, --verbose           Verbose output
  --validate-only         Only validate JSON
  --debug                 Debug mode
  --no-helper-functions   Exclude helper functions
```

## Error Handling

1. **JSON Validation**: Validates JSON structure before processing
2. **Schema Resolution**: Handles missing schema references gracefully
3. **Node Type Validation**: Raises errors for unsupported node types
4. **Safe Attribute Access**: Uses safe getters to avoid AttributeError
5. **Edge Validation**: Skips edges with missing start/end nodes

## Extension Points

To add support for new node types:

1. Add node class import in `main.py`
2. Add case in `build_flow_from_json()` for node construction
3. Add case in `NodePyGenerator._generate_any_node()` with mandatory/optional fields
4. Optionally create specialized generator method for complex nodes

## Testing Strategy

1. **Round-trip Testing**: JSON → Python → JSON comparison
2. **Validation Testing**: Ensure generated Python is syntactically valid
3. **Execution Testing**: Run generated flows to verify functionality
4. **Schema Testing**: Validate Pydantic models work correctly

## Limitations

1. **Custom Functions**: Script node functions must exist in target environment
2. **Tool References**: Tool UUIDs may need manual adjustment
3. **Complex Expressions**: Some complex evaluator expressions may need manual review
4. **Metadata**: Some UI-specific metadata may not translate perfectly

## Future Enhancements

1. **Type Inference**: Better type inference for schema fields
2. **Code Formatting**: Integration with black/autopep8
3. **Import Optimization**: Only import used node types
4. **Documentation Generation**: Auto-generate docstrings from descriptions
5. **Validation**: Add Python code validation before writing
6. **Interactive Mode**: CLI wizard for conversion options