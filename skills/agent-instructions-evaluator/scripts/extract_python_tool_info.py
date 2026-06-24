#!/usr/bin/env python3
"""
Extract metadata from Python-based tools (regular @tool and @flow decorators).

This unified script handles both:
- Regular Python tools decorated with @tool
- Agentic workflow tools decorated with @flow
"""

import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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


def extract_decorator_args(decorator: ast.expr) -> Dict[str, Any]:
    """Extract arguments from a decorator call."""
    args = {}
    
    if isinstance(decorator, ast.Call):
        # Extract keyword arguments
        for keyword in decorator.keywords:
            if keyword.arg:
                try:
                    # Try to evaluate literal values
                    value = ast.literal_eval(keyword.value)
                except (ValueError, TypeError):
                    # If it's not a literal, just store None
                    value = None
                args[keyword.arg] = value
    
    return args


def get_type_annotation(annotation: Optional[ast.expr]) -> str:
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
        # Handle generic types like List[str], Optional[int], etc.
        if isinstance(annotation.value, ast.Name):
            base = annotation.value.id
            if isinstance(annotation.slice, ast.Index):
                # Python < 3.9
                slice_value = annotation.slice.value  # type: ignore
            else:
                # Python >= 3.9
                slice_value = annotation.slice
            
            if isinstance(slice_value, ast.Name):
                return f"{base}[{slice_value.id}]"
            elif isinstance(slice_value, ast.Tuple):
                elements = [get_type_annotation(elt) for elt in slice_value.elts]
                return f"{base}[{', '.join(elements)}]"
        return ast.unparse(annotation) if hasattr(ast, 'unparse') else 'Any'
    
    return 'Any'


def extract_tool_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from a Python tool file (either @tool or @flow)."""
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    tree = ast.parse(source)
    tool_type = detect_python_tool_type(tree)
    
    metadata = {
        'type': tool_type,
        'file_path': file_path,
        'functions': []
    }
    
    # Extract all decorated functions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                decorator_name = None
                decorator_args = {}
                
                if isinstance(decorator, ast.Name):
                    decorator_name = decorator.id
                elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                    decorator_name = decorator.func.id
                    decorator_args = extract_decorator_args(decorator)
                
                if decorator_name in ('tool', 'flow'):
                    # Extract function metadata
                    func_info = {
                        'decorator': decorator_name,
                        'name': node.name,
                        'decorator_args': decorator_args,
                        'parameters': [],
                        'return_type': get_type_annotation(node.returns),
                        'docstring': ast.get_docstring(node) or '',
                    }
                    
                    # Extract parameters
                    for arg in node.args.args:
                        if arg.arg != 'self':
                            param_info = {
                                'name': arg.arg,
                                'type': get_type_annotation(arg.annotation),
                            }
                            func_info['parameters'].append(param_info)
                    
                    # For @flow, estimate node count from function body
                    if decorator_name == 'flow':
                        node_count = sum(1 for _ in ast.walk(node) if isinstance(_, ast.Call))
                        func_info['estimated_node_count'] = node_count
                    
                    metadata['functions'].append(func_info)
    
    return metadata


def format_text_output(metadata: Dict[str, Any]) -> str:
    """Format metadata as human-readable text."""
    lines = [
        f"Python Tool Type: {metadata['type'].upper()}",
        f"File: {metadata['file_path']}",
        "",
    ]
    
    if not metadata['functions']:
        lines.append("No decorated functions found.")
        return '\n'.join(lines)
    
    for func in metadata['functions']:
        lines.append(f"{'='*60}")
        lines.append(f"Decorator: @{func['decorator']}")
        lines.append(f"Function: {func['name']}")
        
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
        print("Usage: extract_python_tool_info.py <python_file> [--format text|json|compact]")
        print("\nExtracts metadata from Python tools decorated with @tool or @flow.")
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
        metadata = extract_tool_metadata(file_path)
        
        if output_format == 'json':
            print(format_json_output(metadata))
        elif output_format == 'compact':
            print(format_compact_output(metadata))
        else:
            print(format_text_output(metadata))
            
    except Exception as e:
        print(f"Error extracting Python tool metadata: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

# Made with Bob
