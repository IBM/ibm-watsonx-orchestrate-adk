#!/usr/bin/env python3
"""
Extract metadata from JSON-based tools (Agentic Workflow and Langflow formats).

This unified script handles both:
- WxO Agentic Workflow JSON files  (spec.kind == "flow", nodes is a dict)
- Langflow JSON workflow files      (data.nodes is a list with Langflow node structure)
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def detect_json_tool_type(data: Dict[str, Any]) -> str:
    """
    Detect whether the JSON is an Agentic Workflow or Langflow format.

    Agentic Workflow indicators:
      - top-level "spec" with kind == "flow"
      - top-level "nodes" is a dict (keyed by node ID)
      - top-level "edges" is a list

    Langflow indicators:
      - top-level "data" dict containing "nodes" (list) and "edges" (list)
      - first node has data.node structure (Langflow-specific)

    Returns:
        'agentic_workflow' | 'langflow' | 'unknown'
    """
    # --- Agentic Workflow ---
    spec = data.get('spec')
    if isinstance(spec, dict) and spec.get('kind') == 'flow':
        if isinstance(data.get('nodes'), dict) and isinstance(data.get('edges'), list):
            return 'agentic_workflow'

    # --- Langflow ---
    flow_data = data.get('data')
    if isinstance(flow_data, dict):
        nodes = flow_data.get('nodes', [])
        edges = flow_data.get('edges', [])
        if isinstance(nodes, list) and isinstance(edges, list):
            if nodes and isinstance(nodes[0].get('data', {}).get('node'), dict):
                return 'langflow'

    return 'unknown'


# ---------------------------------------------------------------------------
# Agentic Workflow extraction
# ---------------------------------------------------------------------------

def _extract_aw_nodes(nodes_dict: Dict[str, Any], parent_id: str = '') -> List[Dict[str, Any]]:
    """
    Recursively extract node info from an Agentic Workflow nodes dict.
    Sub-flows (user_flow nodes) contain their own nested nodes dicts.
    """
    result = []
    for node_id, node_obj in nodes_dict.items():
        spec = node_obj.get('spec', {})
        kind = spec.get('kind', '')
        entry = {
            'id': node_id,
            'kind': kind,
            'name': spec.get('name', node_id),
            'display_name': spec.get('display_name', ''),
            'description': spec.get('description', ''),
            'parent': parent_id,
        }

        # Tool nodes carry input/output schema and the tool reference
        if kind == 'tool':
            entry['tool'] = spec.get('tool', '')
            entry['input_schema'] = spec.get('input_schema', {})
            entry['output_schema'] = spec.get('output_schema', {})

        # User nodes carry a form definition
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

        # Recurse into sub-flow nodes
        sub_nodes = node_obj.get('nodes')
        if isinstance(sub_nodes, dict) and sub_nodes:
            result.extend(_extract_aw_nodes(sub_nodes, parent_id=node_id))

    return result


def extract_agentic_workflow_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata from a WxO Agentic Workflow JSON file."""
    spec = data['spec']

    metadata: Dict[str, Any] = {
        'type': 'agentic_workflow',
        'kind': spec.get('kind', 'flow'),
        'name': spec.get('name', ''),
        'display_name': spec.get('display_name', ''),
        'description': spec.get('description', ''),
        'input_schema': spec.get('input_schema', {}),
        'output_schema': spec.get('output_schema', {}),
    }

    # Top-level edges
    edges: List[Dict] = data.get('edges', [])
    metadata['edge_count'] = len(edges)
    metadata['edges'] = [
        {'id': e.get('id', ''), 'start': e.get('start', ''), 'end': e.get('end', '')}
        for e in edges
    ]

    # All nodes (recursive, includes sub-flow children)
    nodes_dict: Dict = data.get('nodes', {})
    all_nodes = _extract_aw_nodes(nodes_dict)
    metadata['node_count'] = len(all_nodes)
    metadata['nodes'] = all_nodes

    # Derived views
    metadata['tool_nodes'] = [n for n in all_nodes if n['kind'] == 'tool']
    metadata['user_nodes'] = [n for n in all_nodes if n['kind'] == 'user']
    metadata['flow_nodes'] = [n for n in all_nodes if n['kind'] == 'user_flow']

    # Flow-level metadata block (llm_model, source_kind, etc.)
    if 'metadata' in data:
        metadata['flow_metadata'] = data['metadata']

    return metadata


# ---------------------------------------------------------------------------
# Langflow extraction
# ---------------------------------------------------------------------------

def extract_langflow_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata from a Langflow JSON file."""
    metadata: Dict[str, Any] = {
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


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def extract_json_tool_metadata(file_path: str) -> Dict[str, Any]:
    """Detect format and extract metadata from a JSON tool file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    tool_type = detect_json_tool_type(data)

    if tool_type == 'agentic_workflow':
        metadata = extract_agentic_workflow_metadata(data)
    elif tool_type == 'langflow':
        metadata = extract_langflow_metadata(data)
    else:
        metadata = {
            'type': 'unknown',
            'error': 'Could not determine JSON tool type',
        }

    metadata['file_path'] = file_path
    return metadata


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def format_text_output(metadata: Dict[str, Any]) -> str:
    """Format metadata as human-readable text."""
    tool_type = metadata.get('type', 'unknown')
    lines = [
        f"JSON Tool Type: {tool_type.upper()}",
        f"File: {metadata['file_path']}",
        "",
    ]

    if tool_type == 'unknown':
        lines.append(f"Error: {metadata.get('error', 'Unknown error')}")
        return '\n'.join(lines)

    if tool_type == 'agentic_workflow':
        lines += [
            f"Name:         {metadata['name']}",
            f"Display Name: {metadata['display_name']}",
            f"Description:  {metadata['description']}",
            "",
            f"Structure:",
            f"  Top-level nodes : {metadata['node_count']}",
            f"  Top-level edges : {metadata['edge_count']}",
            f"  Tool nodes      : {len(metadata['tool_nodes'])}",
            f"  User (form) nodes: {len(metadata['user_nodes'])}",
            f"  Sub-flow nodes  : {len(metadata['flow_nodes'])}",
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

    elif tool_type == 'langflow':
        lines += [
            f"Name:        {metadata['name']}",
            f"Description: {metadata['description']}",
            f"ID:          {metadata['id']}",
            f"Version:     {metadata['last_tested_version']}",
            f"Is Component: {metadata['is_component']}",
            f"Tags:        {', '.join(metadata['tags']) if metadata['tags'] else 'None'}",
            f"Endpoint:    {metadata['endpoint_name'] or 'None'}",
            "",
            f"Structure:",
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
        print("Usage: extract_json_tool_info.py <json_file> [--format text|json|compact]")
        print("\nExtracts metadata from JSON tools (Agentic Workflow or Langflow format).")
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
        metadata = extract_json_tool_metadata(file_path)

        if output_format == 'json':
            print(format_json_output(metadata))
        elif output_format == 'compact':
            print(format_compact_output(metadata))
        else:
            print(format_text_output(metadata))

    except Exception as e:
        print(f"Error extracting JSON tool metadata: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

# Made with Bob
