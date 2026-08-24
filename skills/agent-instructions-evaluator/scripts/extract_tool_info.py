#!/usr/bin/env python3
"""
Extract metadata from any tool file (.py, .json, or .yaml/.yml).

Automatically detects the file type and dispatches to the appropriate logic:

Python files (.py):
  - @tool decorator  → regular Python tool
  - @flow decorator  → Python flow tool

JSON files (.json):
  - spec.kind == "flow"  → WxO Agentic Workflow
  - data.nodes (list)    → Langflow workflow

YAML files (.yaml / .yml):
  - kind == "knowledge_base"  → WxO Knowledge Base
"""

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml as _yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

# ~4 characters per token — same approximation used in extract_agent_info.py.
_CHARS_PER_TOKEN = 4.0


def _estimate_tokens(text: str) -> int:
    """Return a conservative token estimate: max(1, round(len(text) / 4))."""
    if not text:
        return 0
    return max(1, round(len(text) / _CHARS_PER_TOKEN))


def _spec_to_str(*parts: Any) -> str:
    """
    Serialise arbitrary spec parts (strings, dicts, lists) to a single string
    for character counting.  Strings are taken as-is; everything else is
    serialised to compact JSON (stable, no extra whitespace).
    """
    pieces = []
    for part in parts:
        if part is None:
            continue
        if isinstance(part, str):
            pieces.append(part)
        else:
            try:
                pieces.append(json.dumps(part, separators=(',', ':')))
            except (TypeError, ValueError):
                pieces.append(str(part))
    return ' '.join(p for p in pieces if p)


def _count_spec(spec_str: str) -> Dict[str, int]:
    """Return {'spec_chars': N, 'spec_est_tokens': N} for a serialised spec."""
    chars = len(spec_str)
    return {'spec_chars': chars, 'spec_est_tokens': _estimate_tokens(spec_str)}


# ---------------------------------------------------------------------------
# Python tool extraction
# ---------------------------------------------------------------------------

def detect_python_tool_type(tree: ast.Module) -> str:
    """
    Detect whether the Python file contains a @tool or @flow decorator.

    Returns:
        'tool' | 'flow' | 'unknown'
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                decorator_name = None
                if isinstance(decorator, ast.Name):
                    decorator_name = decorator.id
                elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                    decorator_name = decorator.func.id

                if decorator_name == 'tool':
                    return 'tool'
                elif decorator_name == 'flow':
                    return 'flow'

    return 'unknown'


def _extract_decorator_args(decorator: ast.expr) -> Dict[str, Any]:
    """Extract arguments from a decorator call."""
    args: Dict[str, Any] = {}
    if isinstance(decorator, ast.Call):
        for keyword in decorator.keywords:
            if keyword.arg:
                try:
                    value = ast.literal_eval(keyword.value)
                except (ValueError, TypeError):
                    value = None
                args[keyword.arg] = value
    return args


def _get_type_annotation(annotation: Optional[ast.expr]) -> str:
    """Convert AST type annotation to string."""
    if annotation is None:
        return 'Any'

    if isinstance(annotation, ast.Name):
        return annotation.id
    elif isinstance(annotation, ast.Constant):
        return str(annotation.value)
    elif hasattr(annotation, 's'):  # ast.Str in older Python versions
        return annotation.s  # type: ignore
    elif isinstance(annotation, ast.Subscript):
        if isinstance(annotation.value, ast.Name):
            base = annotation.value.id
            if isinstance(annotation.slice, ast.Index):
                slice_value = annotation.slice.value  # type: ignore  # Python < 3.9
            else:
                slice_value = annotation.slice

            if isinstance(slice_value, ast.Name):
                return f"{base}[{slice_value.id}]"
            elif isinstance(slice_value, ast.Tuple):
                elements = [_get_type_annotation(elt) for elt in slice_value.elts]
                return f"{base}[{', '.join(elements)}]"
        return ast.unparse(annotation) if hasattr(ast, 'unparse') else 'Any'

    return 'Any'


# Simple Python types that map directly to a JSON Schema primitive.
# These are represented compactly in the prompt (e.g. {"type":"string"}).
_SIMPLE_TYPE_MAP: Dict[str, str] = {
    'str':   'string',
    'int':   'integer',
    'float': 'number',
    'bool':  'boolean',
    'None':  'null',
}


def _annotation_to_json_schema(annotation: Optional[ast.expr]) -> Any:
    """
    Convert an AST type annotation to its JSON Schema representation.

    This approximates what the watsonx Orchestrate / OpenAI function-calling
    runtime injects into the model's context for each parameter.  The goal is
    accurate token counting, not a complete schema generator.

    Rules:
    - Simple types (str, int, float, bool, None) → {"type": "<primitive>"}
    - Optional[X] / Union[X, None]               → schema of X (nullable ignored
                                                    for counting purposes)
    - List[X] / list[X]                           → {"type":"array","items":<X schema>}
    - Dict[K,V] / dict[K,V]                       → {"type":"object"}
    - Literal["a","b"]                             → {"type":"string","enum":["a","b"]}
    - Any / unknown custom type                    → {"type":"object"} (conservative
                                                    fallback — object schemas can be
                                                    large; this avoids undercounting)
    """
    if annotation is None:
        return {'type': 'object'}

    # --- ast.Name: bare name like str, int, MyClass ---
    if isinstance(annotation, ast.Name):
        name = annotation.id
        if name in _SIMPLE_TYPE_MAP:
            return {'type': _SIMPLE_TYPE_MAP[name]}
        if name == 'Any':
            return {'type': 'object'}
        # Unknown custom class — treat as object (conservative)
        return {'type': 'object'}

    # --- ast.Constant: e.g. None literal ---
    if isinstance(annotation, ast.Constant):
        if annotation.value is None:
            return {'type': 'null'}
        return {'type': 'string'}

    # --- ast.Subscript: Generic[...] forms ---
    if isinstance(annotation, ast.Subscript):
        if isinstance(annotation.value, ast.Name):
            base = annotation.value.id

            # Unwrap slice (Python 3.8 uses ast.Index wrapper)
            if isinstance(annotation.slice, ast.Index):
                slice_node = annotation.slice.value  # type: ignore
            else:
                slice_node = annotation.slice

            # Optional[X] — treat as schema of X
            if base == 'Optional':
                return _annotation_to_json_schema(slice_node)

            # Union[X, Y, ...] — if one branch is None, treat as schema of X
            if base == 'Union':
                args = slice_node.elts if isinstance(slice_node, ast.Tuple) else [slice_node]
                non_none = [a for a in args if not (isinstance(a, ast.Constant) and a.value is None)
                            and not (isinstance(a, ast.Name) and a.id == 'None')]
                if len(non_none) == 1:
                    return _annotation_to_json_schema(non_none[0])
                return {'type': 'object'}

            # List[X] / list[X]
            if base in ('List', 'list'):
                items_schema = _annotation_to_json_schema(slice_node)
                return {'type': 'array', 'items': items_schema}

            # Dict[K, V] / dict[K, V]
            if base in ('Dict', 'dict'):
                return {'type': 'object'}

            # Literal["a", "b", ...]
            if base == 'Literal':
                values = slice_node.elts if isinstance(slice_node, ast.Tuple) else [slice_node]
                enum_vals = []
                for v in values:
                    if isinstance(v, ast.Constant):
                        enum_vals.append(v.value)
                    else:
                        enum_vals.append(str(v))
                if enum_vals:
                    # Infer JSON type from first value
                    first = enum_vals[0]
                    if isinstance(first, str):
                        return {'type': 'string', 'enum': enum_vals}
                    if isinstance(first, int):
                        return {'type': 'integer', 'enum': enum_vals}
                    return {'enum': enum_vals}

    # Fallback — unknown / complex — treat as object
    return {'type': 'object'}


def _extract_python_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from a .py tool file (@tool or @flow)."""
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()

    tree = ast.parse(source)
    tool_type = detect_python_tool_type(tree)

    metadata: Dict[str, Any] = {
        'file_type': 'python',
        'type': tool_type,
        'file_path': file_path,
        'functions': [],
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                decorator_name = None
                decorator_args: Dict[str, Any] = {}

                if isinstance(decorator, ast.Name):
                    decorator_name = decorator.id
                elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                    decorator_name = decorator.func.id
                    decorator_args = _extract_decorator_args(decorator)

                if decorator_name in ('tool', 'flow'):
                    docstring = ast.get_docstring(node) or ''
                    params = []
                    for arg in node.args.args:
                        if arg.arg != 'self':
                            type_str = _get_type_annotation(arg.annotation)
                            type_schema = _annotation_to_json_schema(arg.annotation)
                            params.append({
                                'name': arg.arg,
                                'type': type_str,
                                'type_schema': type_schema,
                            })

                    return_type = _get_type_annotation(node.returns)

                    # Spec token estimate: function name + docstring + each
                    # parameter serialised as its JSON Schema representation.
                    # Using JSON Schema (not bare type strings) matches what the
                    # runtime injects into the model's context for complex types
                    # such as Literal enums, List[X], and Optional[X].
                    # Return type is excluded — output schema is not injected.
                    param_schema_str = ' '.join(
                        f"{p['name']} {json.dumps(p['type_schema'], separators=(',', ':'))}"
                        for p in params
                    )
                    spec_str = _spec_to_str(
                        node.name, docstring, param_schema_str
                    )
                    counts = _count_spec(spec_str)

                    func_info: Dict[str, Any] = {
                        'decorator': decorator_name,
                        'name': node.name,
                        'decorator_args': decorator_args,
                        'parameters': params,
                        'return_type': return_type,
                        'docstring': docstring,
                        'spec_chars': counts['spec_chars'],
                        'spec_est_tokens': counts['spec_est_tokens'],
                    }

                    if decorator_name == 'flow':
                        func_info['estimated_node_count'] = sum(
                            1 for _ in ast.walk(node) if isinstance(_, ast.Call)
                        )

                    metadata['functions'].append(func_info)

    return metadata


# ---------------------------------------------------------------------------
# YAML tool extraction
# ---------------------------------------------------------------------------

def detect_yaml_tool_type(data: Dict[str, Any]) -> str:
    """
    Detect the kind of a YAML tool file.

    Returns:
        'knowledge_base' | 'mcp_toolkit' | 'unknown'
    """
    kind = data.get('kind')
    if kind == 'knowledge_base':
        return 'knowledge_base'
    if kind == 'mcp':
        return 'mcp_toolkit'
    return 'unknown'


def _extract_knowledge_base_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata from a WxO Knowledge Base YAML file."""
    documents = data.get('documents', [])
    doc_list = [
        {
            'path': doc.get('path', ''),
            'url': doc.get('url', ''),
        }
        for doc in documents
        if isinstance(doc, dict)
    ]

    cst = data.get('conversational_search_tool', {})
    conversational_search: Dict[str, Any] = {}
    if cst:
        conversational_search = {
            'query_source': cst.get('query_source', ''),
            'generation_enabled': cst.get('generation', {}).get('enabled', None),
        }

    name: str = data.get('name', '') or ''
    description: str = data.get('description', '') or ''
    spec_str = _spec_to_str(name, description)
    counts = _count_spec(spec_str)

    return {
        'file_type': 'yaml',
        'type': 'knowledge_base',
        'spec_version': data.get('spec_version', ''),
        'name': name,
        'description': description,
        'spec_chars': counts['spec_chars'],
        'spec_est_tokens': counts['spec_est_tokens'],
        'document_count': len(doc_list),
        'documents': doc_list,
        'conversational_search_tool': conversational_search,
    }


def _extract_mcp_toolkit_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata from a WxO MCP Toolkit YAML file."""
    tools_raw = data.get('tools', [])
    # tools can be ['*'] (wildcard), a list of names, or []
    if tools_raw == ['*'] or tools_raw == '*':
        tools_mode = 'all'
        tool_list: List[str] = []
    else:
        tools_mode = 'explicit'
        tool_list = [str(t) for t in tools_raw] if tools_raw else []

    connections = data.get('connections', [])

    name: str = data.get('name', '') or ''
    description: str = data.get('description', '') or ''
    spec_str = _spec_to_str(name, description)
    counts = _count_spec(spec_str)

    return {
        'file_type': 'yaml',
        'type': 'mcp_toolkit',
        'spec_version': data.get('spec_version', ''),
        'name': name,
        'description': description,
        'spec_chars': counts['spec_chars'],
        'spec_est_tokens': counts['spec_est_tokens'],
        'transport': data.get('transport', ''),
        'url': data.get('url', ''),
        'tools_mode': tools_mode,
        'tools': tool_list,
        'connections': connections if isinstance(connections, list) else [],
    }


def _extract_yaml_metadata(file_path: str) -> Dict[str, Any]:
    """Detect format and extract metadata from a .yaml/.yml tool file."""
    if not _YAML_AVAILABLE:
        return {
            'file_type': 'yaml',
            'type': 'unknown',
            'error': "PyYAML is not installed. Run: pip install pyyaml",
        }

    with open(file_path, 'r', encoding='utf-8') as f:
        data = _yaml.safe_load(f)

    if not isinstance(data, dict):
        return {
            'file_type': 'yaml',
            'type': 'unknown',
            'error': 'YAML root is not a mapping.',
        }

    tool_type = detect_yaml_tool_type(data)

    if tool_type == 'knowledge_base':
        return _extract_knowledge_base_metadata(data)
    if tool_type == 'mcp_toolkit':
        return _extract_mcp_toolkit_metadata(data)

    return {
        'file_type': 'yaml',
        'type': 'unknown',
        'error': "Unrecognised YAML kind: '{}'".format(data.get('kind', '<none>')),
    }


# ---------------------------------------------------------------------------
# JSON tool extraction
# ---------------------------------------------------------------------------

def detect_json_tool_type(data: Dict[str, Any]) -> str:
    """
    Detect whether the JSON is an Agentic Workflow or Langflow format.

    Returns:
        'agentic_workflow' | 'langflow' | 'unknown'
    """
    spec = data.get('spec')
    if isinstance(spec, dict) and spec.get('kind') == 'flow':
        if isinstance(data.get('nodes'), dict) and isinstance(data.get('edges'), list):
            return 'agentic_workflow'

    flow_data = data.get('data')
    if isinstance(flow_data, dict):
        nodes = flow_data.get('nodes', [])
        edges = flow_data.get('edges', [])
        if isinstance(nodes, list) and isinstance(edges, list):
            if nodes and isinstance(nodes[0].get('data', {}).get('node'), dict):
                return 'langflow'

    return 'unknown'


def _extract_aw_nodes(nodes_dict: Dict[str, Any], parent_id: str = '') -> List[Dict[str, Any]]:
    """Recursively extract node info from an Agentic Workflow nodes dict."""
    result = []
    for node_id, node_obj in nodes_dict.items():
        spec = node_obj.get('spec', {})
        kind = spec.get('kind', '')
        entry: Dict[str, Any] = {
            'id': node_id,
            'kind': kind,
            'name': spec.get('name', node_id),
            'display_name': spec.get('display_name', ''),
            'description': spec.get('description', ''),
            'parent': parent_id,
        }

        if kind == 'tool':
            entry['tool'] = spec.get('tool', '')
            entry['input_schema'] = spec.get('input_schema', {})
            entry['output_schema'] = spec.get('output_schema', {})

        if kind == 'user':
            form = spec.get('form', {})
            entry['form_display_name'] = form.get('display_name', '')
            entry['form_fields'] = [
                {
                    'name': f.get('name', ''),
                    'display_name': f.get('display_name', ''),
                    'direction': f.get('direction', ''),
                }
                for f in form.get('fields', [])
            ]

        result.append(entry)

        sub_nodes = node_obj.get('nodes')
        if isinstance(sub_nodes, dict) and sub_nodes:
            result.extend(_extract_aw_nodes(sub_nodes, parent_id=node_id))

    return result


def _extract_agentic_workflow_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata from a WxO Agentic Workflow JSON file."""
    spec = data['spec']
    name: str = spec.get('name', '') or ''
    display_name: str = spec.get('display_name', '') or ''
    description: str = spec.get('description', '') or ''
    input_schema = spec.get('input_schema', {})
    output_schema = spec.get('output_schema', {})
    # Token estimate covers only what the LLM sees in its prompt: name,
    # description, and input schema.  Output schema describes what the tool
    # returns to the runtime — it is not injected into the agent's context.
    spec_str = _spec_to_str(name, display_name, description, input_schema)
    counts = _count_spec(spec_str)

    metadata: Dict[str, Any] = {
        'file_type': 'json',
        'type': 'agentic_workflow',
        'kind': spec.get('kind', 'flow'),
        'name': name,
        'display_name': display_name,
        'description': description,
        'input_schema': input_schema,
        'output_schema': output_schema,
        'spec_chars': counts['spec_chars'],
        'spec_est_tokens': counts['spec_est_tokens'],
    }

    edges: List[Dict] = data.get('edges', [])
    metadata['edge_count'] = len(edges)
    metadata['edges'] = [
        {'id': e.get('id', ''), 'start': e.get('start', ''), 'end': e.get('end', '')}
        for e in edges
    ]

    all_nodes = _extract_aw_nodes(data.get('nodes', {}))
    metadata['node_count'] = len(all_nodes)
    metadata['nodes'] = all_nodes
    metadata['tool_nodes'] = [n for n in all_nodes if n['kind'] == 'tool']
    metadata['user_nodes'] = [n for n in all_nodes if n['kind'] == 'user']
    metadata['flow_nodes'] = [n for n in all_nodes if n['kind'] == 'user_flow']

    if 'metadata' in data:
        metadata['flow_metadata'] = data['metadata']

    return metadata


def _extract_langflow_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata from a Langflow JSON file."""
    name: str = data.get('name', 'Unknown') or 'Unknown'
    description: str = data.get('description', '') or ''
    spec_str = _spec_to_str(name, description)
    counts = _count_spec(spec_str)

    metadata: Dict[str, Any] = {
        'file_type': 'json',
        'type': 'langflow',
        'name': name,
        'description': description,
        'spec_chars': counts['spec_chars'],
        'spec_est_tokens': counts['spec_est_tokens'],
        'id': data.get('id', ''),
        'is_component': data.get('is_component', False),
        'last_tested_version': data.get('last_tested_version', ''),
        'tags': data.get('tags', []),
        'endpoint_name': data.get('endpoint_name'),
    }

    flow_data = data.get('data', {})
    nodes = flow_data.get('nodes', [])
    edges = flow_data.get('edges', [])

    metadata['node_count'] = len(nodes)
    metadata['edge_count'] = len(edges)

    node_info = []
    component_types: set = set()

    for node in nodes:
        node_data = node.get('data', {})
        node_obj = node_data.get('node', {})
        node_type = node_data.get('type', '')
        if node_type:
            component_types.add(node_type)
        node_info.append({
            'id': node_data.get('id', ''),
            'type': node_type,
            'display_name': node_obj.get('display_name', ''),
            'description': node_obj.get('description', ''),
            'icon': node_obj.get('icon', ''),
            'base_classes': node_obj.get('base_classes', []),
        })

    metadata['nodes'] = node_info
    metadata['component_types'] = sorted(component_types)
    metadata['input_nodes'] = [n for n in node_info if 'Input' in n.get('type', '')]
    metadata['output_nodes'] = [n for n in node_info if 'Output' in n.get('type', '')]

    return metadata


def _extract_json_metadata(file_path: str) -> Dict[str, Any]:
    """Detect format and extract metadata from a .json tool file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    tool_type = detect_json_tool_type(data)

    if tool_type == 'agentic_workflow':
        metadata = _extract_agentic_workflow_metadata(data)
    elif tool_type == 'langflow':
        metadata = _extract_langflow_metadata(data)
    else:
        metadata = {
            'file_type': 'json',
            'type': 'unknown',
            'error': 'Could not determine JSON tool type',
        }

    return metadata


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------

def extract_tool_info(file_path: str) -> Dict[str, Any]:
    """
    Detect file type (.py, .json, or .yaml/.yml) and extract tool metadata.

    Returns a metadata dict with a 'file_type' key ('python', 'json', or 'yaml')
    and a 'type' key indicating the specific tool subtype.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == '.py':
        metadata = _extract_python_metadata(file_path)
    elif suffix == '.json':
        metadata = _extract_json_metadata(file_path)
    elif suffix in ('.yaml', '.yml'):
        metadata = _extract_yaml_metadata(file_path)
    else:
        metadata = {
            'file_type': 'unknown',
            'type': 'unknown',
            'error': f"Unsupported file extension '{suffix}'. Expected .py, .json, .yaml, or .yml.",
        }

    metadata['file_path'] = file_path
    return metadata


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def format_text_output(metadata: Dict[str, Any]) -> str:
    """Format metadata as human-readable text."""
    file_type = metadata.get('file_type', 'unknown')
    tool_type = metadata.get('type', 'unknown')
    lines = [
        f"Tool Type: {tool_type.upper()}  (file: {file_type})",
        f"File: {metadata['file_path']}",
        "",
    ]

    if tool_type == 'unknown':
        lines.append(f"Error: {metadata.get('error', 'Unknown error')}")
        return '\n'.join(lines)

    # ---- Python tools ----
    if file_type == 'python':
        functions = metadata.get('functions', [])
        if not functions:
            lines.append("No decorated functions found.")
            return '\n'.join(lines)

        for func in functions:
            lines.append('=' * 60)
            lines.append(f"Decorator: @{func['decorator']}")
            lines.append(f"Function:  {func['name']}")
            lines.append(
                f"Spec:      {func.get('spec_chars', '?')} chars  |  "
                f"~{func.get('spec_est_tokens', '?')} est. tokens"
            )

            if func['decorator_args']:
                lines.append("Decorator Arguments:")
                for key, value in func['decorator_args'].items():
                    lines.append(f"  {key}: {value}")

            if func['docstring']:
                lines.append(f"Description: {func['docstring']}")

            if func['parameters']:
                lines.append("Parameters:")
                for param in func['parameters']:
                    lines.append(f"  - {param['name']}: {param['type']}")
            else:
                lines.append("Parameters: None")

            lines.append(f"Return Type: {func['return_type']}")

            if func['decorator'] == 'flow' and 'estimated_node_count' in func:
                lines.append(f"Estimated Node Count: {func['estimated_node_count']}")

            lines.append("")

    # ---- Agentic Workflow JSON ----
    elif tool_type == 'agentic_workflow':
        lines += [
            f"Name:         {metadata['name']}",
            f"Display Name: {metadata['display_name']}",
            f"Description:  {metadata['description']}",
            f"Spec:         {metadata.get('spec_chars', '?')} chars  |  ~{metadata.get('spec_est_tokens', '?')} est. tokens  (name + display_name + description + input_schema + output_schema)",
            "",
            "Structure:",
            f"  Nodes       : {metadata['node_count']}",
            f"  Edges       : {metadata['edge_count']}",
            f"  Tool nodes  : {len(metadata['tool_nodes'])}",
            f"  User nodes  : {len(metadata['user_nodes'])}",
            f"  Sub-flows   : {len(metadata['flow_nodes'])}",
            "",
        ]

        if metadata['input_schema'].get('properties'):
            lines.append("Input Schema Properties:")
            for prop, schema in metadata['input_schema']['properties'].items():
                lines.append(f"  - {prop}: {schema.get('type', 'any')} — {schema.get('description', '')}")
            lines.append("")

        if metadata['output_schema'].get('properties'):
            lines.append("Output Schema Properties:")
            for prop, schema in metadata['output_schema']['properties'].items():
                lines.append(f"  - {prop}: {schema.get('type', 'any')} — {schema.get('description', '')}")
            lines.append("")

        if metadata['tool_nodes']:
            lines.append("Tool Nodes:")
            for n in metadata['tool_nodes']:
                lines.append(f"  - {n['display_name'] or n['id']}  →  tool: {n['tool']}")
                if n['description']:
                    lines.append(f"    {n['description']}")
                props = n.get('input_schema', {}).get('properties', {})
                if props:
                    lines.append(f"    Inputs: {', '.join(props.keys())}")
            lines.append("")

        if metadata['user_nodes']:
            lines.append("User (Form) Nodes:")
            for n in metadata['user_nodes']:
                fields = n.get('form_fields', [])
                field_names = ', '.join(f['display_name'] or f['name'] for f in fields)
                lines.append(f"  - {n['display_name'] or n['id']}  (form: {n['form_display_name']})")
                if field_names:
                    lines.append(f"    Fields: {field_names}")
            lines.append("")

        lines.append("Edge Flow:")
        for e in metadata['edges']:
            lines.append(f"  {e['start']}  →  {e['end']}")

        if metadata.get('flow_metadata'):
            fm = metadata['flow_metadata']
            lines += [
                "",
                "Flow Metadata:",
                f"  LLM Model   : {fm.get('llm_model', '')}",
                f"  Source Kind : {fm.get('source_kind', '')}",
                f"  Under-spec  : {fm.get('is_under_specified', '')}",
            ]

    # ---- Langflow JSON ----
    elif tool_type == 'langflow':
        lines += [
            f"Name:         {metadata['name']}",
            f"Description:  {metadata['description']}",
            f"Spec:         {metadata.get('spec_chars', '?')} chars  |  ~{metadata.get('spec_est_tokens', '?')} est. tokens  (name + description)",
            f"ID:           {metadata['id']}",
            f"Version:      {metadata['last_tested_version']}",
            f"Is Component: {metadata['is_component']}",
            f"Tags:         {', '.join(metadata['tags']) if metadata['tags'] else 'None'}",
            f"Endpoint:     {metadata['endpoint_name'] or 'None'}",
            "",
            "Structure:",
            f"  Nodes: {metadata['node_count']}",
            f"  Edges: {metadata['edge_count']}",
            f"  Component Types: {', '.join(metadata['component_types'])}",
            "",
        ]

        if metadata['input_nodes']:
            lines.append("Input Nodes:")
            for node in metadata['input_nodes']:
                lines.append(f"  - {node['display_name']} ({node['type']})")
                if node['description']:
                    lines.append(f"    {node['description']}")
            lines.append("")

        if metadata['output_nodes']:
            lines.append("Output Nodes:")
            for node in metadata['output_nodes']:
                lines.append(f"  - {node['display_name']} ({node['type']})")
                if node['description']:
                    lines.append(f"    {node['description']}")
            lines.append("")

        lines.append("All Nodes:")
        for node in metadata['nodes']:
            lines.append(f"  - {node['display_name']} ({node['type']})")
            if node['description']:
                lines.append(f"    {node['description']}")

    # ---- Knowledge Base YAML ----
    elif tool_type == 'knowledge_base':
        lines += [
            f"Name:         {metadata['name']}",
            f"Description:  {metadata['description']}",
            f"Spec:         {metadata.get('spec_chars', '?')} chars  |  ~{metadata.get('spec_est_tokens', '?')} est. tokens  (name + description)",
            f"Spec Version: {metadata['spec_version']}",
            f"Documents:    {metadata['document_count']}",
            "",
        ]

        if metadata['documents']:
            lines.append("Documents:")
            for doc in metadata['documents']:
                entry = f"  - {doc['path']}"
                if doc['url']:
                    entry += f"  ({doc['url']})"
                lines.append(entry)
            lines.append("")

        cst = metadata.get('conversational_search_tool', {})
        if cst:
            lines.append("Conversational Search Tool:")
            if cst.get('query_source'):
                lines.append(f"  Query Source:       {cst['query_source']}")
            if cst.get('generation_enabled') is not None:
                lines.append(f"  Generation Enabled: {cst['generation_enabled']}")
            lines.append("")

    # ---- MCP Toolkit YAML ----
    elif tool_type == 'mcp_toolkit':
        lines += [
            f"Name:         {metadata['name']}",
            f"Description:  {metadata['description']}",
            f"Spec:         {metadata.get('spec_chars', '?')} chars  |  ~{metadata.get('spec_est_tokens', '?')} est. tokens  (name + description)",
            f"Spec Version: {metadata['spec_version']}",
            f"Transport:    {metadata['transport']}",
            f"URL:          {metadata['url']}",
            "",
        ]

        if metadata['tools_mode'] == 'all':
            lines.append("Tools:        * (all tools discovered at runtime)")
        elif metadata['tools']:
            lines.append(f"Tools ({len(metadata['tools'])}):")
            for t in metadata['tools']:
                lines.append(f"  - {t}")
        else:
            lines.append("Tools:        (none explicitly listed)")
        lines.append("")

        if metadata['connections']:
            lines.append(f"Connections ({len(metadata['connections'])}):")
            for c in metadata['connections']:
                lines.append(f"  - {c}")
            lines.append("")

    return '\n'.join(lines)


def format_json_output(metadata: Dict[str, Any]) -> str:
    return json.dumps(metadata, indent=2)


def format_compact_output(metadata: Dict[str, Any]) -> str:
    return json.dumps(metadata, separators=(',', ':'))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _safe_tool_name(metadata: Dict[str, Any]) -> str:
    """
    Derive a filesystem-safe name for the output file from the metadata dict.

    For Python files the tool may have multiple decorated functions; use the
    first function name found.  For all other types, use the top-level 'name'
    field.  Fall back to the stem of the source file_path.
    """
    file_type = metadata.get('file_type', '')
    if file_type == 'python':
        functions = metadata.get('functions', [])
        if functions:
            return functions[0].get('name', 'tool').replace(' ', '_')
    name = metadata.get('name', '') or ''
    if name:
        return name.replace(' ', '_')
    # Last resort: stem of the source file
    return Path(metadata.get('file_path', 'tool')).stem


def main():
    parser = argparse.ArgumentParser(
        description='Extract metadata from a tool file (.py, .json, or .yaml/.yml).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Human-readable text (default)
  python extract_tool_info.py tool.py

  # Pretty-printed JSON
  python extract_tool_info.py tool.py --json

  # Save JSON extraction to the eval output directory
  python extract_tool_info.py tool.py --output-dir eval/
  python extract_tool_info.py flow.json --output-dir eval/
  python extract_tool_info.py kb.yaml --output-dir eval/
        """
    )

    parser.add_argument('file_path', help='Path to the tool file (.py, .json, .yaml, or .yml)')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--compact', action='store_true', help='Single-line JSON output')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Directory to write the JSON extraction file into.  The file is named '
                             'tool_<name>_extracted.json and is always written as pretty-printed JSON, '
                             'independent of the --json / --compact stdout flag.  The directory is '
                             'created if it does not exist.')

    args = parser.parse_args()

    if not Path(args.file_path).exists():
        print(f"Error: File not found: {args.file_path}", file=sys.stderr)
        sys.exit(1)

    try:
        metadata = extract_tool_info(args.file_path)

        if args.json:
            print(format_json_output(metadata))
        elif args.compact:
            print(format_compact_output(metadata))
        else:
            print(format_text_output(metadata))

        # --output-dir: persist the full JSON extraction to disk so evaluation
        # reports can reference it without re-running the extractor.
        if args.output_dir:
            out_dir = Path(args.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            tool_name = _safe_tool_name(metadata)
            out_file = out_dir / f"tool_{tool_name}_extracted.json"
            out_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            print(f"Extraction saved: {out_file}", file=sys.stderr)

    except Exception as e:
        print(f"Error extracting tool metadata: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

# Made with Bob
