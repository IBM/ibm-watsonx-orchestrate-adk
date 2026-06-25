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
                    func_info: Dict[str, Any] = {
                        'decorator': decorator_name,
                        'name': node.name,
                        'decorator_args': decorator_args,
                        'parameters': [],
                        'return_type': _get_type_annotation(node.returns),
                        'docstring': ast.get_docstring(node) or '',
                    }

                    for arg in node.args.args:
                        if arg.arg != 'self':
                            func_info['parameters'].append({
                                'name': arg.arg,
                                'type': _get_type_annotation(arg.annotation),
                            })

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

    return {
        'file_type': 'yaml',
        'type': 'knowledge_base',
        'spec_version': data.get('spec_version', ''),
        'name': data.get('name', ''),
        'description': data.get('description', ''),
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

    return {
        'file_type': 'yaml',
        'type': 'mcp_toolkit',
        'spec_version': data.get('spec_version', ''),
        'name': data.get('name', ''),
        'description': data.get('description', ''),
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
    metadata: Dict[str, Any] = {
        'file_type': 'json',
        'type': 'agentic_workflow',
        'kind': spec.get('kind', 'flow'),
        'name': spec.get('name', ''),
        'display_name': spec.get('display_name', ''),
        'description': spec.get('description', ''),
        'input_schema': spec.get('input_schema', {}),
        'output_schema': spec.get('output_schema', {}),
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
    metadata: Dict[str, Any] = {
        'file_type': 'json',
        'type': 'langflow',
        'name': data.get('name', 'Unknown'),
        'description': data.get('description', ''),
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

def main():
    if len(sys.argv) < 2:
        print("Usage: extract_tool_info.py <file.py|file.json|file.yaml> [--format text|json|compact]")
        print("\nExtracts metadata from a tool file (.py, .json, or .yaml/.yml).")
        print("\nPython files: detects @tool or @flow decorators.")
        print("JSON files:   detects WxO Agentic Workflow or Langflow format.")
        print("YAML files:   detects WxO Knowledge Base (kind: knowledge_base) or MCP Toolkit (kind: mcp).")
        print("\nFormats:")
        print("  text    - Human-readable text (default)")
        print("  json    - Pretty-printed JSON")
        print("  compact - Single-line JSON")
        sys.exit(1)

    file_path = sys.argv[1]
    output_format = 'text'

    if len(sys.argv) > 2 and sys.argv[2] == '--format':
        if len(sys.argv) > 3:
            output_format = sys.argv[3]

    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    try:
        metadata = extract_tool_info(file_path)

        if output_format == 'json':
            print(format_json_output(metadata))
        elif output_format == 'compact':
            print(format_compact_output(metadata))
        else:
            print(format_text_output(metadata))

    except Exception as e:
        print(f"Error extracting tool metadata: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

# Made with Bob
