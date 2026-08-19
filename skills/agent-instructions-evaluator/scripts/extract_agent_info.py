#!/usr/bin/env python3
"""
Extract agent metadata from watsonx Orchestrate native agent YAML files.

Extracts key fields including:
- Agent name, display_name, description, kind, llm
- Tools list and collaborators list
- Context variables
- Instructions length and guidelines count
- Skills list — with each skill resolved to its SKILL.md location and metadata:
    - name, description, allowed-tools (from SKILL.md frontmatter)
    - scripts/  : Python files (.py) under <skill-dir>/scripts/ (recursively)
    - references/: any files under <skill-dir>/references/ (recursively)
    - WXO.yaml  : sibling config file if present

Discovery strategy for SKILL.md:
  1. Search <search-root> recursively for SKILL.md files whose frontmatter
     'name' field matches the skill name listed in the agent YAML.
  2. Fallback: match by parent directory name.
  The search root defaults to the directory containing the agent YAML.
  Override with --search-root to point at a project root.

Usage:
    python extract_agent_info.py <agent.yaml>
    python extract_agent_info.py <agent.yaml> --json
    python extract_agent_info.py <agent.yaml> --field name
    python extract_agent_info.py <agent.yaml> --field skills
    python extract_agent_info.py <agent.yaml> --search-root /path/to/project
    python extract_agent_info.py <agent.yaml> --compact
"""

import sys
import yaml
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional


# ---------------------------------------------------------------------------
# SKILL.md helpers
# ---------------------------------------------------------------------------

def _parse_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    """
    Parse YAML frontmatter delimited by '---' from a Markdown file.

    Returns the parsed dict, or None if no valid frontmatter is found.
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != '---':
        return None
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == '---':
            end = i
            break
    if end is None:
        return None
    try:
        return yaml.safe_load('\n'.join(lines[1:end]))
    except yaml.YAMLError:
        return None


def _find_skill_file(skill_name: str, search_root: Path) -> Optional[Path]:
    """
    Search recursively under search_root for a SKILL.md whose frontmatter
    'name' equals skill_name.  Falls back to matching by parent directory name.

    Returns the Path to the matching SKILL.md, or None if not found.
    """
    candidates = list(search_root.rglob('SKILL.md'))

    # Pass 1 — match by frontmatter 'name'
    for candidate in candidates:
        try:
            content = candidate.read_text(encoding='utf-8')
            if skill_name not in content:  # fast pre-filter
                continue
            fm = _parse_frontmatter(content)
            if fm and fm.get('name') == skill_name:
                return candidate
        except Exception:
            continue

    # Pass 2 — match by parent directory name
    for candidate in candidates:
        if candidate.parent.name == skill_name:
            return candidate

    return None


def _resolve_skill(skill_name: str, search_root: Path) -> Dict[str, Any]:
    """
    Locate the SKILL.md for skill_name and extract its full metadata:
      - description, allowed_tools  (from frontmatter)
      - has_wxo_yaml                (WXO.yaml sibling present)
      - scripts                     (list of relative paths under scripts/)
      - references                  (list of relative paths under references/)
      - skill_file                  (absolute path to SKILL.md, or None)
      - resolved                    (True if SKILL.md was found)
    """
    skill_file = _find_skill_file(skill_name, search_root)

    if not skill_file:
        return {
            'name': skill_name,
            'description': None,
            'allowed_tools': [],
            'has_wxo_yaml': False,
            'scripts': [],
            'references': [],
            'skill_file': None,
            'resolved': False,
        }

    skill_dir = skill_file.parent

    # Frontmatter
    try:
        fm = _parse_frontmatter(skill_file.read_text(encoding='utf-8')) or {}
    except Exception:
        fm = {}

    # WXO.yaml sibling
    has_wxo = (skill_dir / 'WXO.yaml').exists()

    # scripts/ — any .py files recursively
    scripts_dir = skill_dir / 'scripts'
    scripts: List[str] = []
    if scripts_dir.is_dir():
        scripts = sorted(
            str(p.relative_to(skill_dir)).replace('\\', '/')
            for p in scripts_dir.rglob('*.py')
        )

    # references/ — any files recursively
    references_dir = skill_dir / 'references'
    references: List[str] = []
    if references_dir.is_dir():
        references = sorted(
            str(p.relative_to(skill_dir)).replace('\\', '/')
            for p in references_dir.rglob('*')
            if p.is_file()
        )

    return {
        'name': skill_name,
        'description': fm.get('description', ''),
        'allowed_tools': fm.get('allowed-tools', []),
        'has_wxo_yaml': has_wxo,
        'scripts': scripts,
        'references': references,
        'skill_file': str(skill_file.absolute()),
        'resolved': True,
    }


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract_agent_info(yaml_path: str, search_root: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract agent information from a watsonx Orchestrate native agent YAML file.

    Args:
        yaml_path:   Path to the agent YAML file.
        search_root: Root directory to search for SKILL.md files.
                     Defaults to the directory containing the agent YAML.

    Returns:
        Dictionary containing agent metadata including resolved skills.

    Raises:
        FileNotFoundError: If the YAML file doesn't exist.
        yaml.YAMLError:    If the YAML file is malformed.
    """
    yaml_file = Path(yaml_path)

    if not yaml_file.exists():
        raise FileNotFoundError(f"Agent YAML file not found: {yaml_path}")

    with open(yaml_file, 'r', encoding='utf-8') as f:
        try:
            agent_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to parse YAML file: {e}")

    root = Path(search_root).resolve() if search_root else yaml_file.parent.resolve()

    skill_names: List[str] = agent_data.get('skills', []) or []
    resolved_skills = [_resolve_skill(name, root) for name in skill_names]

    return {
        'name': agent_data.get('name', 'unknown'),
        'display_name': agent_data.get('display_name', agent_data.get('name', 'unknown')),
        'description': agent_data.get('description', ''),
        'kind': agent_data.get('kind', 'unknown'),
        'llm': agent_data.get('llm', 'unknown'),
        'tools': agent_data.get('tools', []),
        'collaborators': agent_data.get('collaborators', []),
        'context_variables': agent_data.get('context_variables', []),
        'skills': resolved_skills,
        'instructions_length': (
            len(agent_data.get('instructions', '').split('\n'))
            if agent_data.get('instructions') else 0
        ),
        'guidelines_count': len(agent_data.get('guidelines', [])) if agent_data.get('guidelines') else 0,
        'file_path': str(yaml_file.absolute()),
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_output(info: Dict[str, Any], output_format: str = 'text', field: Optional[str] = None) -> str:
    """
    Format the extracted information for output.

    Args:
        info:          Dictionary containing agent metadata.
        output_format: 'text', 'json', or 'compact'.
        field:         If set, return only this field's value.

    Returns:
        Formatted string output.
    """
    if field:
        if field in info:
            return json.dumps(info[field], indent=2) if isinstance(info[field], (list, dict)) else str(info[field])
        available_fields = ', '.join(info.keys())
        return f"Error: Field '{field}' not found. Available fields: {available_fields}"

    if output_format == 'json':
        return json.dumps(info, indent=2)

    if output_format == 'compact':
        return f"{info['name']}|{info['display_name']}|{info['description']}"

    # --- text format ---
    lines = [
        f"Agent Name:          {info['name']}",
        f"Display Name:        {info['display_name']}",
        f"Kind:                {info['kind']}",
        f"LLM:                 {info['llm']}",
        f"Description:         {info['description']}",
        f"Instructions Length: {info['instructions_length']} lines",
        f"Guidelines Count:    {info['guidelines_count']}",
        f"Tools:               {len(info['tools'])} ({', '.join(info['tools']) if info['tools'] else 'none'})",
        f"Collaborators:       {len(info['collaborators'])} ({', '.join(info['collaborators']) if info['collaborators'] else 'none'})",
        f"Context Variables:   {len(info['context_variables'])}",
    ]

    skills = info.get('skills', [])
    resolved = [s for s in skills if s['resolved']]
    unresolved = [s for s in skills if not s['resolved']]
    lines.append(f"Skills:              {len(skills)} ({len(resolved)} resolved, {len(unresolved)} not found)")

    for s in resolved:
        tools_str = ', '.join(s['allowed_tools']) if s['allowed_tools'] else 'none'
        wxo_flag = ' [WXO.yaml]' if s['has_wxo_yaml'] else ''
        lines.append(f"  [{s['name']}]{wxo_flag}")
        lines.append(f"    allowed-tools: {tools_str}")
        if s['scripts']:
            lines.append(f"    scripts ({len(s['scripts'])}): {', '.join(s['scripts'])}")
        if s['references']:
            lines.append(f"    references ({len(s['references'])}): {', '.join(s['references'])}")
        lines.append(f"    file: {s['skill_file']}")

    for s in unresolved:
        lines.append(f"  [{s['name']}]  ← SKILL.md not found under {info['file_path']}")

    lines.append(f"File Path:           {info['file_path']}")
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Extract metadata from a watsonx Orchestrate native agent YAML file.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Text summary (default)
  python extract_agent_info.py agent.yaml

  # JSON output
  python extract_agent_info.py agent.yaml --json

  # Single field
  python extract_agent_info.py agent.yaml --field name
  python extract_agent_info.py agent.yaml --field skills

  # Compact pipe-separated (name|display_name|description)
  python extract_agent_info.py agent.yaml --compact

  # Override skill search root (useful when agent.yaml is nested deep)
  python extract_agent_info.py agent.yaml --search-root /path/to/project
        """
    )

    parser.add_argument('yaml_path', help='Path to the agent YAML file')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--compact', action='store_true',
                        help='Compact pipe-separated format (name|display_name|description)')
    parser.add_argument('--field', type=str,
                        help='Extract a single field (name, display_name, description, kind, llm, '
                             'tools, collaborators, context_variables, skills, …)')
    parser.add_argument('--search-root', type=str, default=None,
                        help='Root directory for SKILL.md discovery '
                             '(default: directory of the agent YAML)')

    args = parser.parse_args()

    try:
        info = extract_agent_info(args.yaml_path, search_root=args.search_root)

        if args.json:
            output_format = 'json'
        elif args.compact:
            output_format = 'compact'
        else:
            output_format = 'text'

        print(format_output(info, output_format, args.field))
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
