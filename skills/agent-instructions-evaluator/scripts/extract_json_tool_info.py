#!/usr/bin/env python3
"""
Extract metadata from JSON-based tools (Flow and Langflow formats).

This unified script handles both:
- WxO Agentic Workflow (Flow) JSON files
- Langflow JSON workflow files
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def detect_json_tool_type(data: Dict[str, Any]) -> str:
    """
    Detect whether the JSON is a Flow or Langflow format.
    
    Returns:
        'flow' | 'langflow' | 'unknown'
    """
    # Check for Langflow indicators
    if 'data' in data and isinstance(data['data'], dict):
        data_obj = data['data']
        if 'nodes' in data_obj and 'edges' in data_obj and 'viewport' in data_obj:
            # Check for Langflow-specific node structure
            nodes = data_obj.get('nodes', [])
            if nodes and isinstance(nodes, list) and len(nodes) > 0:
                first_node = nodes[0]
                if 'data' in first_node and 'node' in first_node.get('data', {}):
                    return 'langflow'
    
    # Check for Flow indicators
    if 'spec' in data and isinstance(data['spec'], dict):
        spec = data['spec']
        if spec.get('kind') == 'flow':
            return 'flow'
    
    # Could be a Flow JSON without spec wrapper
    if 'nodes' in data and 'edges' in data and 'spec' not in data and 'data' not in data:
        return 'flow'
    
    return 'unknown'


def extract_flow_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata from a Flow JSON file."""
    metadata = {
        'type': 'flow',
    }
    
    # Check if it has a spec wrapper
    if 'spec' in data:
        spec = data['spec']
        metadata['kind'] = spec.get('kind', 'flow')
        metadata['input_schema'] = spec.get('input_schema', {})
        metadata['parameters'] = spec.get('parameters', {})
        
        # Extract nodes and edges from spec
        nodes = spec.get('nodes', [])
        edges = spec.get('edges', [])
    else:
        # Direct nodes/edges format
        nodes = data.get('nodes', [])
        edges = data.get('edges', [])
    
    metadata['node_count'] = len(nodes)
    metadata['edge_count'] = len(edges)
    
    # Extract node information
    node_info = []
    for node in nodes:
        node_info.append({
            'id': node.get('id', ''),
            'type': node.get('type', ''),
            'data': node.get('data', {}),
        })
    
    metadata['nodes'] = node_info
    
    return metadata


def extract_langflow_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata from a Langflow JSON file."""
    metadata = {
        'type': 'langflow',
        'name': data.get('name', 'Unknown'),
        'description': data.get('description', ''),
        'id': data.get('id', ''),
        'is_component': data.get('is_component', False),
        'last_tested_version': data.get('last_tested_version', ''),
        'tags': data.get('tags', []),
        'endpoint_name': data.get('endpoint_name'),
    }
    
    # Extract data structure info
    flow_data = data.get('data', {})
    nodes = flow_data.get('nodes', [])
    edges = flow_data.get('edges', [])
    
    metadata['node_count'] = len(nodes)
    metadata['edge_count'] = len(edges)
    
    # Extract node types and their display names
    node_info = []
    for node in nodes:
        node_data = node.get('data', {})
        node_obj = node_data.get('node', {})
        node_info.append({
            'id': node_data.get('id', ''),
            'type': node_data.get('type', ''),
            'display_name': node_obj.get('display_name', ''),
            'description': node_obj.get('description', ''),
            'icon': node_obj.get('icon', ''),
            'base_classes': node_obj.get('base_classes', []),
        })
    
    metadata['nodes'] = node_info
    
    # Extract component types used
    component_types = set()
    for node in nodes:
        node_type = node.get('data', {}).get('type', '')
        if node_type:
            component_types.add(node_type)
    
    metadata['component_types'] = sorted(list(component_types))
    
    # Extract input/output nodes
    input_nodes = [n for n in node_info if 'Input' in n.get('type', '')]
    output_nodes = [n for n in node_info if 'Output' in n.get('type', '')]
    
    metadata['input_nodes'] = input_nodes
    metadata['output_nodes'] = output_nodes
    
    return metadata


def extract_json_tool_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from a JSON tool file (Flow or Langflow)."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    tool_type = detect_json_tool_type(data)
    
    if tool_type == 'flow':
        metadata = extract_flow_metadata(data)
    elif tool_type == 'langflow':
        metadata = extract_langflow_metadata(data)
    else:
        metadata = {
            'type': 'unknown',
            'error': 'Could not determine JSON tool type'
        }
    
    metadata['file_path'] = file_path
    return metadata


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
    
    if tool_type == 'langflow':
        lines.extend([
            f"Name: {metadata['name']}",
            f"Description: {metadata['description']}",
            f"ID: {metadata['id']}",
            f"Version: {metadata['last_tested_version']}",
            f"Is Component: {metadata['is_component']}",
            f"Tags: {', '.join(metadata['tags']) if metadata['tags'] else 'None'}",
            f"Endpoint: {metadata['endpoint_name'] or 'None'}",
            "",
            f"Structure:",
            f"  Nodes: {metadata['node_count']}",
            f"  Edges: {metadata['edge_count']}",
            f"  Component Types: {', '.join(metadata['component_types'])}",
            "",
        ])
        
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
    
    elif tool_type == 'flow':
        lines.extend([
            f"Kind: {metadata.get('kind', 'flow')}",
            f"Nodes: {metadata['node_count']}",
            f"Edges: {metadata['edge_count']}",
            "",
        ])
        
        if 'input_schema' in metadata and metadata['input_schema']:
            lines.append("Input Schema:")
            lines.append(f"  {json.dumps(metadata['input_schema'], indent=2)}")
            lines.append("")
        
        if 'parameters' in metadata and metadata['parameters']:
            lines.append("Parameters:")
            for key, value in metadata['parameters'].items():
                lines.append(f"  {key}: {value}")
            lines.append("")
        
        if metadata['nodes']:
            lines.append("Nodes:")
            for node in metadata['nodes']:
                lines.append(f"  - {node['id']} ({node['type']})")
    
    return '\n'.join(lines)


def format_json_output(metadata: Dict[str, Any]) -> str:
    """Format metadata as JSON."""
    return json.dumps(metadata, indent=2)


def format_compact_output(metadata: Dict[str, Any]) -> str:
    """Format metadata as compact single-line JSON."""
    return json.dumps(metadata, separators=(',', ':'))


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: extract_json_tool_info.py <json_file> [--format text|json|compact]")
        print("\nExtracts metadata from JSON tools (Flow or Langflow format).")
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
