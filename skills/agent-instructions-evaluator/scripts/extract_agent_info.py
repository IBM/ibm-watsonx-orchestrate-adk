#!/usr/bin/env python3
"""
Extract agent name and description from watsonx Orchestrate agent YAML files.

This script parses agent YAML files and extracts key metadata including:
- Agent name
- Display name
- Description
- Tools list
- Collaborators list
- Context variables

Usage:
    python extract_agent_info.py <path_to_agent.yaml>
    python extract_agent_info.py <path_to_agent.yaml> --json
    python extract_agent_info.py <path_to_agent.yaml> --field name
"""

import sys
import yaml
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional


def extract_agent_info(yaml_path: str) -> Dict[str, Any]:
    """
    Extract agent information from a YAML file.
    
    Args:
        yaml_path: Path to the agent YAML file
        
    Returns:
        Dictionary containing agent metadata
        
    Raises:
        FileNotFoundError: If the YAML file doesn't exist
        yaml.YAMLError: If the YAML file is malformed
    """
    yaml_file = Path(yaml_path)
    
    if not yaml_file.exists():
        raise FileNotFoundError(f"Agent YAML file not found: {yaml_path}")
    
    with open(yaml_file, 'r', encoding='utf-8') as f:
        try:
            agent_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to parse YAML file: {e}")
    
    # Extract key fields with defaults
    info = {
        'name': agent_data.get('name', 'unknown'),
        'display_name': agent_data.get('display_name', agent_data.get('name', 'unknown')),
        'description': agent_data.get('description', ''),
        'kind': agent_data.get('kind', 'unknown'),
        'llm': agent_data.get('llm', 'unknown'),
        'tools': agent_data.get('tools', []),
        'collaborators': agent_data.get('collaborators', []),
        'context_variables': agent_data.get('context_variables', []),
        'instructions_length': len(agent_data.get('instructions', '').split('\n')) if agent_data.get('instructions') else 0,
        'guidelines_count': len(agent_data.get('guidelines', [])) if agent_data.get('guidelines') else 0,
        'file_path': str(yaml_file.absolute())
    }
    
    return info


def format_output(info: Dict[str, Any], output_format: str = 'text', field: Optional[str] = None) -> str:
    """
    Format the extracted information for output.
    
    Args:
        info: Dictionary containing agent metadata
        output_format: Output format ('text', 'json', or 'compact')
        field: Specific field to extract (if any)
        
    Returns:
        Formatted string output
    """
    if field:
        # Return specific field value
        if field in info:
            return str(info[field])
        else:
            available_fields = ', '.join(info.keys())
            return f"Error: Field '{field}' not found. Available fields: {available_fields}"
    
    if output_format == 'json':
        return json.dumps(info, indent=2)
    
    elif output_format == 'compact':
        return f"{info['name']}|{info['display_name']}|{info['description']}"
    
    else:  # text format
        output = []
        output.append(f"Agent Name: {info['name']}")
        output.append(f"Display Name: {info['display_name']}")
        output.append(f"Kind: {info['kind']}")
        output.append(f"LLM: {info['llm']}")
        output.append(f"Description: {info['description']}")
        output.append(f"Instructions Length: {info['instructions_length']} lines")
        output.append(f"Guidelines Count: {info['guidelines_count']}")
        output.append(f"Tools: {len(info['tools'])} ({', '.join(info['tools']) if info['tools'] else 'none'})")
        output.append(f"Collaborators: {len(info['collaborators'])} ({', '.join(info['collaborators']) if info['collaborators'] else 'none'})")
        output.append(f"Context Variables: {len(info['context_variables'])}")
        output.append(f"File Path: {info['file_path']}")
        return '\n'.join(output)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Extract agent name and description from watsonx Orchestrate agent YAML files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all information in text format
  python extract_agent_info.py agent.yaml
  
  # Extract all information in JSON format
  python extract_agent_info.py agent.yaml --json
  
  # Extract specific field
  python extract_agent_info.py agent.yaml --field name
  python extract_agent_info.py agent.yaml --field description
  
  # Compact format (pipe-separated)
  python extract_agent_info.py agent.yaml --compact
        """
    )
    
    parser.add_argument(
        'yaml_path',
        help='Path to the agent YAML file'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )
    
    parser.add_argument(
        '--compact',
        action='store_true',
        help='Output in compact pipe-separated format (name|display_name|description)'
    )
    
    parser.add_argument(
        '--field',
        type=str,
        help='Extract specific field (name, display_name, description, kind, llm, tools, collaborators, etc.)'
    )
    
    args = parser.parse_args()
    
    try:
        # Extract agent information
        info = extract_agent_info(args.yaml_path)
        
        # Determine output format
        if args.json:
            output_format = 'json'
        elif args.compact:
            output_format = 'compact'
        else:
            output_format = 'text'
        
        # Format and print output
        output = format_output(info, output_format, args.field)
        print(output)
        
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except yaml.YAMLError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

# Made with Bob
