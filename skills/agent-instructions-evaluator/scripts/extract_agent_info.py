#!/usr/bin/env python3
"""
Extract agent metadata from watsonx Orchestrate native agent YAML files.

Extracts key fields including:
- Agent name, display_name, description, kind, llm
- Tools list and collaborators list (with each collaborator resolved)
- Context variables
- Instructions length and guidelines count
- Skills list — with each skill resolved to its SKILL.md location and metadata:
    - name, description, allowed-tools (from SKILL.md frontmatter)
    - name_length, description_length, name_too_long, description_too_long (frontmatter validation)
    - unmatched_placeholders: list of {{identifier}} tokens with no matching param
    - scripts/  : Python files (.py) under <skill-dir>/scripts/ (recursively)
    - references/: any files under <skill-dir>/references/ (recursively)

Discovery strategy for SKILL.md:
  1. Search <search-root> recursively for SKILL.md files whose frontmatter
     'name' field matches the skill name listed in the agent YAML.
  2. Fallback: match by parent directory name.
  The search root defaults to the directory containing the agent YAML.
  Override with --search-root to point at a project root.

Discovery strategy for collaborator agent YAML:
  1. Check the directory co-located with the agent YAML first (fastest, most
     common case — collaborators are often in the same native/ folder).
  2. If not found there, search <search-root> recursively for any *.yaml or
     *.yml file whose top-level 'name' field matches the collaborator name.
  Co-located matches always take priority over search-root matches.

Usage:
    python extract_agent_info.py <agent.yaml>
    python extract_agent_info.py <agent.yaml> --json
    python extract_agent_info.py <agent.yaml> --field name
    python extract_agent_info.py <agent.yaml> --field skills
    python extract_agent_info.py <agent.yaml> --field collaborators
    python extract_agent_info.py <agent.yaml> --search-root /path/to/project
    python extract_agent_info.py <agent.yaml> --compact
"""

import re
import sys
import yaml
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

# Character-based token estimation: ~4 characters per token is a reasonable
# approximation for English instruction prose with mixed punctuation and
# parameter names. It is more accurate than a lines-based estimate because
# line length varies significantly across instruction styles.
_CHARS_PER_TOKEN = 4.0

def _estimate_tokens(text: str) -> int:
    """Return a conservative token estimate for the given text string."""
    if not text:
        return 0
    return max(1, round(len(text) / _CHARS_PER_TOKEN))


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
      - description, allowed_tools  (from frontmatter; allowed_tools always a list)
      - name_length, name_est_tokens
      - description_length, description_est_tokens
      - name_too_long, description_too_long (hard-limit validation)
      - catalog_est_tokens          (name + description tokens — cost paid every turn)
      - body_chars, body_est_tokens (skill body load cost)
      - unmatched_placeholders      (list of {{identifier}} tokens with no matching param)
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
            'name_est_tokens': _estimate_tokens(skill_name),
            'description_est_tokens': 0,
            'catalog_est_tokens': _estimate_tokens(skill_name),
            'allowed_tools': [],
            'body_chars': 0,
            'body_est_tokens': 0,
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

    # Normalise allowed-tools: YAML may give us a space-separated string or a list
    raw_tools = fm.get('allowed-tools')
    allowed_tools: List[str] = raw_tools.split() if isinstance(raw_tools, str) else list(raw_tools or [])

    description: str = fm.get('description', '') or ''
    name_val: str = fm.get('name', skill_name) or skill_name

    # Frontmatter validation signals
    name_length: int = len(name_val)
    description_length: int = len(description)

    # Catalog token cost: name + description are injected every turn regardless
    # of which skill is loaded — this is the permanent per-turn routing overhead.
    name_est_tokens: int = _estimate_tokens(name_val)
    description_est_tokens: int = _estimate_tokens(description)
    catalog_est_tokens: int = name_est_tokens + description_est_tokens

    # Body token estimate — read the full SKILL.md text (excluding frontmatter)
    skill_raw = skill_file.read_text(encoding='utf-8')
    # Strip YAML frontmatter block (--- ... ---) to get only the body
    body_text = re.sub(r'^---\n.*?\n---\n', '', skill_raw, count=1, flags=re.DOTALL)
    body_chars: int = len(body_text)
    body_est_tokens: int = _estimate_tokens(body_text)

    # Detect {{placeholder}} tokens with no matching param
    params = set(fm.get('params', {}).keys()) if isinstance(fm.get('params'), dict) else set()
    placeholder_pattern = re.compile(r'\{\{(\w+)\}\}')
    all_text = description + '\n' + skill_raw
    unmatched_placeholders: List[str] = [
        m for m in placeholder_pattern.findall(all_text) if m not in params
    ]

    return {
        'name': skill_name,
        'description': description,
        'name_length': name_length,
        'name_est_tokens': name_est_tokens,
        'description_length': description_length,
        'description_est_tokens': description_est_tokens,
        'catalog_est_tokens': catalog_est_tokens,
        'name_too_long': name_length > 64,
        'description_too_long': description_length > 1024,
        'unmatched_placeholders': sorted(set(unmatched_placeholders)),
        'allowed_tools': allowed_tools,
        'body_chars': body_chars,
        'body_est_tokens': body_est_tokens,
        'scripts': scripts,
        'references': references,
        'skill_file': str(skill_file.absolute()),
        'resolved': True,
    }


# ---------------------------------------------------------------------------
# Collaborator agent helpers
# ---------------------------------------------------------------------------

def _find_collaborator_file(
    collaborator_name: str,
    agent_dir: Path,
    search_root: Path,
) -> Optional[Path]:
    """
    Locate the YAML file for a collaborator agent.

    Discovery order (co-located takes priority):
      1. Look in agent_dir for <collaborator_name>.yaml or <collaborator_name>.yml
      2. Recursively search search_root for any *.yaml / *.yml whose top-level
         'name' field equals collaborator_name.

    Returns the Path to the matching file, or None if not found.
    """
    # Pass 1 — co-located directory (exact filename match)
    for ext in ('.yaml', '.yml'):
        candidate = agent_dir / f"{collaborator_name}{ext}"
        if candidate.exists():
            return candidate

    # Pass 2 — recursive search-root scan by 'name' field
    for ext in ('*.yaml', '*.yml'):
        for candidate in search_root.rglob(ext):
            # Skip the agent's own directory to avoid re-matching already
            # checked files (minor optimisation, not strictly necessary)
            try:
                data = yaml.safe_load(candidate.read_text(encoding='utf-8'))
                if isinstance(data, dict) and data.get('name') == collaborator_name:
                    return candidate
            except Exception:
                continue

    return None


def _resolve_collaborator(
    collaborator_name: str,
    agent_dir: Path,
    search_root: Path,
) -> Dict[str, Any]:
    """
    Locate the agent YAML for collaborator_name and extract its key metadata:
      - display_name        (display_name field, fallback to name)
      - description         (description field)
      - kind                (kind field, e.g. 'native')
      - llm                 (llm field)
      - tools               (tools list)
      - collaborators       (collaborators list — nested collaborators)
      - skills              (skills list — skill names)
      - instructions_length (line count of instructions field)
      - guidelines_count    (number of guidelines entries)
      - collocated          (True if found in the same directory as the parent agent)
      - collaborator_file   (absolute path to the YAML, or None)
      - resolved            (True if the YAML was found)
    """
    collab_file = _find_collaborator_file(collaborator_name, agent_dir, search_root)

    if not collab_file:
        return {
            'name': collaborator_name,
            'display_name': collaborator_name,
            'name_est_tokens': _estimate_tokens(collaborator_name),
            'description': None,
            'description_est_tokens': 0,
            'routing_est_tokens': _estimate_tokens(collaborator_name),
            'kind': None,
            'llm': None,
            'tools': [],
            'collaborators': [],
            'skills': [],
            'instructions_length': 0,
            'instructions_chars': 0,
            'instructions_est_tokens': 0,
            'guidelines_count': 0,
            'collocated': False,
            'collaborator_file': None,
            'resolved': False,
        }

    try:
        data = yaml.safe_load(collab_file.read_text(encoding='utf-8')) or {}
    except Exception:
        data = {}

    collocated = collab_file.parent.resolve() == agent_dir.resolve()

    display_name: str = data.get('display_name', data.get('name', collaborator_name)) or collaborator_name
    description: str = data.get('description', '') or ''
    instructions_text: str = data.get('instructions', '') or ''
    instructions_lines: int = len(instructions_text.split('\n')) if instructions_text else 0
    instructions_chars: int = len(instructions_text)
    instructions_est_tokens: int = _estimate_tokens(instructions_text)

    # Routing overhead: name + description are used by the supervisor to select
    # this collaborator — these tokens are paid on every supervisor turn.
    name_est_tokens: int = _estimate_tokens(collaborator_name)
    description_est_tokens: int = _estimate_tokens(description)
    routing_est_tokens: int = name_est_tokens + description_est_tokens

    return {
        'name': collaborator_name,
        'display_name': display_name,
        'name_est_tokens': name_est_tokens,
        'description': description,
        'description_est_tokens': description_est_tokens,
        'routing_est_tokens': routing_est_tokens,
        'kind': data.get('kind', None),
        'llm': data.get('llm', None),
        'tools': data.get('tools', []) or [],
        'collaborators': data.get('collaborators', []) or [],
        'skills': data.get('skills', []) or [],
        'instructions_length': instructions_lines,
        'instructions_chars': instructions_chars,
        'instructions_est_tokens': instructions_est_tokens,
        'guidelines_count': (
            len(data.get('guidelines', [])) if data.get('guidelines') else 0
        ),
        'collocated': collocated,
        'collaborator_file': str(collab_file.absolute()),
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
        search_root: Root directory to search for SKILL.md files and collaborator
                     agent YAML files.  Defaults to the directory containing the
                     agent YAML.

    Returns:
        Dictionary containing agent metadata including resolved skills and
        resolved collaborators.

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

    agent_dir = yaml_file.parent.resolve()
    root = Path(search_root).resolve() if search_root else agent_dir

    skill_names: List[str] = agent_data.get('skills', []) or []
    resolved_skills = [_resolve_skill(name, root) for name in skill_names]

    collaborator_names: List[str] = agent_data.get('collaborators', []) or []
    resolved_collaborators = [
        _resolve_collaborator(name, agent_dir, root)
        for name in collaborator_names
    ]

    instructions_text: str = agent_data.get('instructions', '') or ''
    instructions_lines: int = len(instructions_text.split('\n')) if instructions_text else 0
    instructions_chars: int = len(instructions_text)
    instructions_est_tokens: int = _estimate_tokens(instructions_text)

    # Skill catalog: sum of (name + description) tokens across all skills.
    # This cost is paid on EVERY turn regardless of which skill is loaded.
    skill_catalog_est_tokens: int = sum(
        s.get('catalog_est_tokens', 0) for s in resolved_skills
    )

    # Collaborator routing catalog: sum of (name + description) tokens across
    # all collaborators. Paid on every supervisor turn for routing decisions.
    collaborator_routing_est_tokens: int = sum(
        c.get('routing_est_tokens', 0) for c in resolved_collaborators
    )

    return {
        'name': agent_data.get('name', 'unknown'),
        'display_name': agent_data.get('display_name', agent_data.get('name', 'unknown')),
        'description': agent_data.get('description', ''),
        'kind': agent_data.get('kind', 'unknown'),
        'llm': agent_data.get('llm', 'unknown'),
        'tools': agent_data.get('tools', []),
        'collaborators': agent_data.get('collaborators', []),
        'resolved_collaborators': resolved_collaborators,
        'context_variables': agent_data.get('context_variables', []),
        'skills': resolved_skills,
        'instructions_length': instructions_lines,
        'instructions_chars': instructions_chars,
        'instructions_est_tokens': instructions_est_tokens,
        'skill_catalog_est_tokens': skill_catalog_est_tokens,
        'collaborator_routing_est_tokens': collaborator_routing_est_tokens,
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
        f"Instructions Length: {info['instructions_length']} lines  |  {info.get('instructions_chars', '?')} chars  |  ~{info.get('instructions_est_tokens', '?')} est. tokens",
        f"Guidelines Count:    {info['guidelines_count']}",
        f"Tools:               {len(info['tools'])} ({', '.join(info['tools']) if info['tools'] else 'none'})",
        f"Context Variables:   {len(info['context_variables'])}",
        f"Skill catalog:       ~{info.get('skill_catalog_est_tokens', 0)} est. tokens (name+desc of all skills, paid every turn)",
        f"Collab routing:      ~{info.get('collaborator_routing_est_tokens', 0)} est. tokens (name+desc of all collaborators, paid every turn)",
    ]

    # --- Collaborators ---
    rc = info.get('resolved_collaborators', [])
    raw_collabs = info.get('collaborators', [])
    resolved_c = [c for c in rc if c['resolved']]
    unresolved_c = [c for c in rc if not c['resolved']]
    collocated_c = [c for c in resolved_c if c['collocated']]
    remote_c = [c for c in resolved_c if not c['collocated']]

    lines.append(
        f"Collaborators:       {len(raw_collabs)} "
        f"({len(resolved_c)} resolved [{len(collocated_c)} co-located, "
        f"{len(remote_c)} remote], {len(unresolved_c)} not found)"
    )

    for c in resolved_c:
        loc_flag = ' [co-located]' if c['collocated'] else ' [remote]'
        nested_collabs = len(c['collaborators'])
        nested_tools = len(c['tools'])
        nested_skills = len(c['skills'])
        lines.append(f"  [{c['name']}]{loc_flag}  ← {c['display_name']}")
        lines.append(f"    kind: {c['kind']}  llm: {c['llm']}")
        lines.append(
            f"    instructions: {c['instructions_length']} lines  "
            f"|  {c.get('instructions_chars', '?')} chars  "
            f"|  ~{c.get('instructions_est_tokens', '?')} est. tokens  "
            f"|  guidelines: {c['guidelines_count']}"
        )
        lines.append(
            f"    routing overhead: ~{c.get('routing_est_tokens', '?')} est. tokens "
            f"(name ~{c.get('name_est_tokens', '?')} + desc ~{c.get('description_est_tokens', '?')}, paid every supervisor turn)"
        )
        lines.append(
            f"    tools: {nested_tools}  collaborators: {nested_collabs}  skills: {nested_skills}"
        )
        if c['description']:
            # Truncate long descriptions for readability
            desc = c['description'].replace('\n', ' ').strip()
            if len(desc) > 120:
                desc = desc[:117] + '...'
            lines.append(f"    description: {desc}")
        lines.append(f"    file: {c['collaborator_file']}")

    for c in unresolved_c:
        lines.append(f"  [{c['name']}]  ← YAML not found")

    # --- Skills ---
    skills = info.get('skills', [])
    resolved_s = [s for s in skills if s['resolved']]
    unresolved_s = [s for s in skills if not s['resolved']]
    lines.append(f"Skills:              {len(skills)} ({len(resolved_s)} resolved, {len(unresolved_s)} not found)")

    for s in resolved_s:
        tools_str = ', '.join(s['allowed_tools']) if s['allowed_tools'] else 'none'
        flags = []
        if s.get('name_too_long'):
            flags.append(f"NAME TOO LONG ({s['name_length']} chars, limit 64)")
        if s.get('description_too_long'):
            flags.append(f"DESC TOO LONG ({s['description_length']} chars, limit 1024)")
        if s.get('unmatched_placeholders'):
            flags.append(f"UNMATCHED PLACEHOLDERS: {s['unmatched_placeholders']}")
        flag_str = ' [' + '; '.join(flags) + ']' if flags else ''
        lines.append(f"  [{s['name']}]{flag_str}")
        lines.append(
            f"    catalog: ~{s.get('catalog_est_tokens', '?')} est. tokens/turn "
            f"(name ~{s.get('name_est_tokens', '?')} + desc ~{s.get('description_est_tokens', '?')})"
        )
        lines.append(
            f"    body:    ~{s.get('body_est_tokens', '?')} est. tokens/load "
            f"({s.get('body_chars', '?')} chars)"
        )
        lines.append(f"    allowed-tools: {tools_str}")
        if s['scripts']:
            lines.append(f"    scripts ({len(s['scripts'])}): {', '.join(s['scripts'])}")
        if s['references']:
            lines.append(f"    references ({len(s['references'])}): {', '.join(s['references'])}")
        lines.append(f"    file: {s['skill_file']}")

    for s in unresolved_s:
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

  # JSON output (includes resolved_collaborators)
  python extract_agent_info.py agent.yaml --json

  # Single field
  python extract_agent_info.py agent.yaml --field name
  python extract_agent_info.py agent.yaml --field skills
  python extract_agent_info.py agent.yaml --field resolved_collaborators

  # Compact pipe-separated (name|display_name|description)
  python extract_agent_info.py agent.yaml --compact

  # Override search root (useful when agent.yaml is nested deep and
  # collaborators / SKILL.md files live in sibling directories)
  python extract_agent_info.py agent.yaml --search-root /path/to/project
        """
    )

    parser.add_argument('yaml_path', help='Path to the agent YAML file')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--compact', action='store_true',
                        help='Compact pipe-separated format (name|display_name|description)')
    parser.add_argument('--field', type=str,
                        help='Extract a single field (name, display_name, description, kind, llm, '
                             'tools, collaborators, resolved_collaborators, context_variables, skills, …)')
    parser.add_argument('--search-root', type=str, default=None,
                        help='Root directory for SKILL.md and collaborator YAML discovery '
                             '(default: directory of the agent YAML). Co-located files always '
                             'take priority over search-root matches.')

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
