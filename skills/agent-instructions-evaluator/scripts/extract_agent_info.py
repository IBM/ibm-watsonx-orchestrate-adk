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

Tool discovery (--tools-root):
  Recursively scans a directory for tool source files and builds the spec
  lookup inline — no separate extraction step required.
  - .py files: included when they contain at least one @tool, @flow, or
               @<any>.tool() decorator (e.g. @mcp.tool() in MCP servers)
  - .json files: included when detect_json_tool_type() returns agentic_workflow
                 or langflow (i.e. spec.kind == 'flow' or Langflow data.nodes
                 structure); other JSON files are silently skipped

  Alternatively, supply --tools-dir pointing at a directory of
  tool_*_extracted.json files already produced by
  extract_tool_info.py --output-dir.

Usage:
    python extract_agent_info.py <agent.yaml>
    python extract_agent_info.py <agent.yaml> --json
    python extract_agent_info.py <agent.yaml> --field name
    python extract_agent_info.py <agent.yaml> --field skills
    python extract_agent_info.py <agent.yaml> --field collaborators
    python extract_agent_info.py <agent.yaml> --search-root /path/to/project
    python extract_agent_info.py <agent.yaml> --tools-root /path/to/toolkit
    python extract_agent_info.py <agent.yaml> --compact
"""

import re
import sys
import ast
import yaml
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

# Import tool extraction helpers from the sibling script.  We add the script's
# directory to sys.path at import time so this works regardless of cwd.
_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
try:
    from extract_tool_info import (  # type: ignore
        extract_tool_info as _extract_tool_info,
        detect_python_tool_type as _detect_python_tool_type,
        detect_json_tool_type as _detect_json_tool_type,
    )
    _TOOL_INFO_AVAILABLE = True
except ImportError:
    _TOOL_INFO_AVAILABLE = False


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
# Tool spec loading
# ---------------------------------------------------------------------------

def _load_tool_specs(tools_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Scan *tools_dir* for ``tool_*_extracted.json`` files produced by
    ``extract_tool_info.py --output-dir`` and build a lookup keyed by the
    canonical tool name.

    For Python files the tool name is taken from the first decorated function
    entry.  For all other types it is the top-level ``name`` field.

    Returns a dict: ``{tool_name: {spec_chars, spec_est_tokens, type, file_path, …}}``.
    The dict is empty if *tools_dir* does not exist or contains no matching files.
    """
    specs: Dict[str, Dict[str, Any]] = {}
    if not tools_dir.is_dir():
        return specs

    for json_file in sorted(tools_dir.glob('tool_*_extracted.json')):
        try:
            data: Dict[str, Any] = json.loads(json_file.read_text(encoding='utf-8'))
        except Exception:
            continue

        file_type = data.get('file_type', '')
        if file_type == 'python':
            for func in data.get('functions', []):
                name = func.get('name', '')
                if name:
                    specs[name] = {
                        'spec_chars': func.get('spec_chars', 0),
                        'spec_est_tokens': func.get('spec_est_tokens', 0),
                        'type': data.get('type', 'tool'),
                        'file_path': data.get('file_path', ''),
                    }
        else:
            name = data.get('name', '')
            if name:
                specs[name] = {
                    'spec_chars': data.get('spec_chars', 0),
                    'spec_est_tokens': data.get('spec_est_tokens', 0),
                    'type': data.get('type', ''),
                    'file_path': data.get('file_path', ''),
                }

    return specs


def _scan_tools_root(tools_root: Path) -> Dict[str, Dict[str, Any]]:
    """
    Recursively scan *tools_root* for tool source files and build a spec
    lookup dict with the same shape as ``_load_tool_specs``.

    Inclusion rules:
    - ``.py`` files: included only when they contain at least one ``@tool``,
      ``@flow``, or ``@<any>.tool()`` decorated function (covers MCP servers
      that use ``@mcp.tool()``).  Files that parse successfully but have no
      such decorator are silently skipped.  Parse errors are also silently
      skipped.
    - ``.json`` files: included only when ``detect_json_tool_type()`` returns
      ``'agentic_workflow'`` or ``'langflow'``.  All other JSON (config,
      lock-files, plain data) is silently skipped.
    - All other extensions (e.g. ``.yaml``, ``.md``) are ignored.

    When ``extract_tool_info`` is not importable (sibling script missing)
    this function returns an empty dict and emits a warning to stderr.

    Returns a dict: ``{tool_name: {spec_chars, spec_est_tokens, type, file_path}}``.
    """
    specs: Dict[str, Dict[str, Any]] = {}

    if not tools_root.is_dir():
        print(
            f"Warning: --tools-root '{tools_root}' is not a directory — skipping tool scan.",
            file=sys.stderr,
        )
        return specs

    if not _TOOL_INFO_AVAILABLE:
        print(
            "Warning: extract_tool_info.py not found alongside extract_agent_info.py — "
            "--tools-root scan disabled.  Copy extract_tool_info.py to the same directory "
            "or use --tools-dir with pre-extracted JSON files instead.",
            file=sys.stderr,
        )
        return specs

    py_files = sorted(tools_root.rglob('*.py'))
    json_files = sorted(tools_root.rglob('*.json'))

    scanned = skipped_no_decorator = skipped_not_tool_json = errors = 0

    # --- Python files ---
    for py_file in py_files:
        try:
            source = py_file.read_text(encoding='utf-8')
            tree = ast.parse(source)
        except Exception:
            errors += 1
            continue

        tool_type = _detect_python_tool_type(tree)
        if tool_type == 'unknown':
            skipped_no_decorator += 1
            continue

        try:
            metadata = _extract_tool_info(str(py_file))
        except Exception:
            errors += 1
            continue

        for func in metadata.get('functions', []):
            name = func.get('name', '')
            if name:
                specs[name] = {
                    'spec_chars': func.get('spec_chars', 0),
                    'spec_est_tokens': func.get('spec_est_tokens', 0),
                    'type': metadata.get('type', tool_type),
                    'file_path': str(py_file),
                }
                scanned += 1

    # --- JSON files ---
    for json_file in json_files:
        try:
            data: Dict[str, Any] = json.loads(json_file.read_text(encoding='utf-8'))
        except Exception:
            errors += 1
            continue

        json_type = _detect_json_tool_type(data)
        if json_type not in ('agentic_workflow', 'langflow'):
            skipped_not_tool_json += 1
            continue

        try:
            metadata = _extract_tool_info(str(json_file))
        except Exception:
            errors += 1
            continue

        name = metadata.get('name', '')
        if name:
            specs[name] = {
                'spec_chars': metadata.get('spec_chars', 0),
                'spec_est_tokens': metadata.get('spec_est_tokens', 0),
                'type': metadata.get('type', json_type),
                'file_path': str(json_file),
            }
            scanned += 1
        else:
            skipped_not_tool_json += 1

    print(
        f"Tool scan: {scanned} tools loaded from '{tools_root}' "
        f"({skipped_no_decorator} .py files skipped — no @tool/@flow/@mcp.tool, "
        f"{skipped_not_tool_json} .json files skipped — not agentic workflow/langflow"
        + (f", {errors} parse errors" if errors else "")
        + ")",
        file=sys.stderr,
    )

    return specs


def _strip_namespace(name: str) -> str:
    """
    Strip a ``namespace:`` prefix from a tool name if present.

    Many watsonx Orchestrate agents reference tools with a toolkit namespace
    prefix (e.g. ``silver:calculator_tool``).  Extracted spec files are keyed
    by the bare function name (``calculator_tool``).  This helper normalises
    both sides so the lookup succeeds regardless of whether a prefix is present.
    """
    return name.split(':', 1)[-1] if ':' in name else name


def _enrich_tools(
    tool_names: List[str],
    tool_specs: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Convert a flat list of tool name strings into a list of enriched dicts::

        [
          {
            "name": "get_invoice",
            "spec_chars": 87,
            "spec_est_tokens": 22,
            "type": "tool",
            "file_path": "/path/to/get_invoice.py",
            "resolved": True,
          },
          {
            "name": "missing_tool",
            "spec_chars": 0,
            "spec_est_tokens": 200,
            "type": None,
            "file_path": None,
            "resolved": False,
          },
        ]

    Tools with no matching entry in *tool_specs* are marked ``resolved=False``
    and use a 200-token fallback estimate — a conservative approximation for a
    tool whose definition is unavailable.

    Namespace prefixes (e.g. ``silver:``) are stripped before lookup so that
    ``silver:calculator_tool`` resolves to the same spec as ``calculator_tool``.
    """
    _UNRESOLVED_FALLBACK_TOKENS = 200
    result = []
    for name in tool_names:
        bare = _strip_namespace(name)
        spec = tool_specs.get(bare) or tool_specs.get(name)
        if spec:
            result.append({
                'name': name,
                'spec_chars': spec['spec_chars'],
                'spec_est_tokens': spec['spec_est_tokens'],
                'type': spec.get('type'),
                'file_path': spec.get('file_path'),
                'resolved': True,
            })
        else:
            result.append({
                'name': name,
                'spec_chars': 0,
                'spec_est_tokens': _UNRESOLVED_FALLBACK_TOKENS,
                'type': None,
                'file_path': None,
                'resolved': False,
            })
    return result


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


def _resolve_skill(
    skill_name: str,
    search_root: Path,
    tool_specs: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Locate the SKILL.md for skill_name and extract its full metadata:
      - description, allowed_tools  (from frontmatter; allowed_tools always a list)
      - resolved_allowed_tools       (enriched list with spec_chars/spec_est_tokens per tool)
      - allowed_tools_spec_est_tokens (sum of spec tokens across all allowed tools)
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
        'resolved_allowed_tools': _enrich_tools(allowed_tools, tool_specs or {}),
        'allowed_tools_spec_est_tokens': sum(
            t['spec_est_tokens'] for t in _enrich_tools(allowed_tools, tool_specs or {})
        ),
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
    tool_specs: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Locate the agent YAML for collaborator_name and extract its key metadata:
      - display_name        (display_name field, fallback to name)
      - description         (description field)
      - kind                (kind field, e.g. 'native')
      - llm                 (llm field)
      - tools               (raw list of tool name strings)
      - resolved_tools      (enriched list with spec_chars/spec_est_tokens per tool)
      - tools_spec_est_tokens (sum of spec tokens across all tools)
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
            'resolved_tools': [],
            'tools_spec_est_tokens': 0,
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
        'resolved_tools': _enrich_tools(data.get('tools', []) or [], tool_specs or {}),
        'tools_spec_est_tokens': sum(
            ((tool_specs or {}).get(_strip_namespace(t)) or (tool_specs or {}).get(t) or {}).get('spec_est_tokens', 0)
            for t in (data.get('tools', []) or [])
        ),
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

def extract_agent_info(
    yaml_path: str,
    search_root: Optional[str] = None,
    tools_dir: Optional[str] = None,
    tools_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract agent information from a watsonx Orchestrate native agent YAML file.

    Args:
        yaml_path:   Path to the agent YAML file.
        search_root: Root directory to search for SKILL.md files and collaborator
                     agent YAML files.  Defaults to the directory containing the
                     agent YAML.
        tools_dir:   Directory containing ``tool_*_extracted.json`` files produced
                     by ``extract_tool_info.py --output-dir``.  When supplied,
                     every tool name in the agent's ``tools:`` list, each
                     collaborator's ``tools:`` list, and each skill's
                     ``allowed-tools`` is enriched with ``spec_chars`` and
                     ``spec_est_tokens`` from the matching JSON file.
        tools_root:  Root directory to scan for tool source files (.py with
                     @tool/@flow, .json agentic-workflow/langflow).  Builds
                     the spec lookup inline — no separate extraction step needed.
                     When both tools_dir and tools_root are supplied, tools_dir
                     takes priority (pre-extracted JSONs are used as-is, and
                     tools_root fills in any names not found in tools_dir).
                     When neither tools_root nor tools_dir is supplied, the scan
                     runs automatically against search_root (or the agent YAML's
                     directory if search_root is also absent).

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

    # Build tool spec lookup.
    # Priority: tools_dir (pre-extracted JSONs) > tools_root (live scan) > auto (search_root).
    # When both tools_dir and tools_root are provided, tools_dir entries win.
    # When neither is supplied, fall back to scanning search_root automatically so
    # callers get tool specs without having to know where the toolkit lives.
    tool_specs: Dict[str, Dict[str, Any]] = {}
    scan_root = Path(tools_root).resolve() if tools_root else root
    tool_specs = _scan_tools_root(scan_root)
    if tools_dir:
        # Pre-extracted JSONs take priority — merge on top, overwriting any
        # same-named entries from the live scan.
        tool_specs.update(_load_tool_specs(Path(tools_dir)))

    skill_names: List[str] = agent_data.get('skills', []) or []
    resolved_skills = [
        _resolve_skill(name, root, tool_specs) for name in skill_names
    ]

    # Instructions and guidelines text — needed before tool classification so
    # we can search them for direct agent-level tool name references.
    instructions_text: str = agent_data.get('instructions', '') or ''
    instructions_lines: int = len(instructions_text.split('\n')) if instructions_text else 0
    instructions_chars: int = len(instructions_text)
    instructions_est_tokens: int = _estimate_tokens(instructions_text)

    guidelines_list = agent_data.get('guidelines', []) or []
    guidelines_text = ' '.join(
        str(g) for g in guidelines_list
    ) if guidelines_list else ''

    agent_tools: List[str] = agent_data.get('tools', []) or []
    agent_tools_set = set(agent_tools)

    # Collect all tool names that appear in any skill's allowed-tools.
    skill_owned_tools: set = set()
    for skill in resolved_skills:
        for t in skill.get('allowed_tools', []):
            skill_owned_tools.add(_strip_namespace(t))
            skill_owned_tools.add(t)

    # Build the text corpus to search for direct agent-level tool references.
    agent_text_corpus = (instructions_text + ' ' + guidelines_text).lower()

    # Classify each agent tool to detect the tool-binding shadow reliability risk.
    #
    # wxO platform behaviour: when a skill lists a tool in its allowed-tools, that
    # tool is REMOVED from the agent's base tool set for the duration of that skill
    # context. If the same tool also appears in agent tools:, the agent loses access
    # to it whenever a skill is NOT active — a silent execution gap.
    #
    # This is purely a RELIABILITY issue, not a token issue. The spec is counted once
    # (at L1, from agent tools:). There is no double-spend.
    #
    # Subclassification — "skill-only" (stricter):
    #   A shadowed tool where the agent's instructions: and guidelines: text also
    #   contain no direct reference to calling it. This confirms the agent author
    #   did not intend to call it at the agent level — it belongs only in the skill.
    #   These are the highest-confidence candidates to remove from agent tools:.
    skill_only_tools: List[str] = []     # shadowed AND not referenced in agent text — safe to remove
    agent_callable_tools: List[str] = [] # not skill-owned, or explicitly referenced in agent text
    for t in agent_tools:
        bare = _strip_namespace(t)
        in_skill = bare in skill_owned_tools or t in skill_owned_tools
        # Check whether the bare tool name appears anywhere in agent text.
        referenced_in_agent = bare.lower() in agent_text_corpus or t.lower() in agent_text_corpus
        if in_skill and not referenced_in_agent:
            skill_only_tools.append(t)
        else:
            agent_callable_tools.append(t)

    for skill in resolved_skills:
        shadowed = [t for t in skill.get('allowed_tools', []) if t in agent_tools_set]
        skill['tool_binding_shadows'] = shadowed

    collaborator_names: List[str] = agent_data.get('collaborators', []) or []
    resolved_collaborators = [
        _resolve_collaborator(name, agent_dir, root, tool_specs)
        for name in collaborator_names
    ]

    # Skill catalog: sum of (name + description) tokens across all skills.
    # This cost is paid on EVERY agent turn regardless of which skill is loaded —
    # the agent needs all skill names+descriptions to decide which skill to load.
    skill_catalog_est_tokens: int = sum(
        s.get('catalog_est_tokens', 0) for s in resolved_skills
    )

    # Collaborator routing catalog: sum of (name + description) tokens across
    # all collaborators. Paid on every supervisor turn for routing decisions.
    # NOTE: collaborator *internals* (their instructions, tools, skills) run in
    # the collaborator's own separate context window — they are NOT additive to
    # the supervisor's context and must NOT be included in the agent floor total.
    collaborator_routing_est_tokens: int = sum(
        c.get('routing_est_tokens', 0) for c in resolved_collaborators
    )

    # Agent-level tool list and spec costs.
    #
    # wxO platform behaviour: any tool listed in a skill's allowed-tools is REMOVED
    # from the agent's base tool set when that skill is active. This means tools that
    # appear in skill_owned_tools are never actually present at L1 — the platform
    # has taken them out. Only tools NOT in skill_owned_tools are truly active at
    # the agent level and should be counted in the L1 floor.
    #
    # tool_list_est_tokens  — names of truly active agent-level tools only
    # tools_spec_est_tokens — specs of truly active agent-level tools only
    # shadowed tools are still reported for the reliability diagnostic, but their
    # token cost is NOT included in the L1 floor.
    resolved_agent_tools = _enrich_tools(agent_tools, tool_specs)
    # Tag each resolved tool with whether it is shadowed by a skill.
    for t in resolved_agent_tools:
        t['shadowed'] = (
            _strip_namespace(t['name']) in skill_owned_tools
            or t['name'] in skill_owned_tools
        )

    active_resolved_tools   = [t for t in resolved_agent_tools if not t['shadowed']]
    shadowed_resolved_tools = [t for t in resolved_agent_tools if t['shadowed']]

    agent_tools_spec_est_tokens: int = sum(
        t['spec_est_tokens'] for t in active_resolved_tools
    )
    tool_list_est_tokens: int = sum(
        _estimate_tokens(t['name']) for t in active_resolved_tools
    )

    agent_floor_est_tokens: int = (
        instructions_est_tokens
        + skill_catalog_est_tokens
        + collaborator_routing_est_tokens
        + tool_list_est_tokens
        + agent_tools_spec_est_tokens
    )
    return {
        'name': agent_data.get('name', 'unknown'),
        'display_name': agent_data.get('display_name', agent_data.get('name', 'unknown')),
        'description': agent_data.get('description', ''),
        'kind': agent_data.get('kind', 'unknown'),
        'llm': agent_data.get('llm', 'unknown'),
        'tools': agent_tools,
        'resolved_tools': resolved_agent_tools,
        'active_resolved_tools': active_resolved_tools,
        'shadowed_resolved_tools': shadowed_resolved_tools,
        'tools_spec_est_tokens': agent_tools_spec_est_tokens,
        'tool_list_est_tokens': tool_list_est_tokens,
        'skill_only_tools': skill_only_tools,
        'agent_callable_tools': agent_callable_tools,
        'agent_floor_est_tokens': agent_floor_est_tokens,
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
        f"Context Variables:   {len(info['context_variables'])}",
        "",
        f"── LEVEL 1 — Agent context (paid on every agent turn) ─────────────────────────────────────────",
        f"  Instructions:      ~{info.get('instructions_est_tokens', 0)} est. tokens",
        f"  Skill catalog:     ~{info.get('skill_catalog_est_tokens', 0)} est. tokens  (name+desc of all {len(info.get('skills', []))} skills — agent needs these to decide which skill to load)",
        f"  Collab routing:    ~{info.get('collaborator_routing_est_tokens', 0)} est. tokens  (name+desc of all {len(info.get('collaborators', []))} collaborators — routing only; collab internals run in their own context)",
        f"  Agent tool list:   ~{info.get('tool_list_est_tokens', 0)} est. tokens  ({len(info.get('active_resolved_tools', []))} active tools — {len(info.get('shadowed_resolved_tools', []))} excluded: shadowed by skill)",
        f"  Agent tool specs:  ~{info.get('tools_spec_est_tokens', 0)} est. tokens  ({len(info.get('active_resolved_tools', []))} active tools — shadowed tools not counted, their spec is removed from base set)",
        f"  ─────────────────────────────────────────────────────────────────────────────────────────────",
        f"  Agent floor total: ~{info.get('agent_floor_est_tokens', 0)} est. tokens/turn",
        f"",
        f"── LEVEL 2 — Skill context (added on top of agent context when a skill is loaded) ─────────────",
        f"  Skill body:        per-skill — see skill detail below  (body_est_tokens per skill)",
        f"  Skill tool list:   per-skill — allowed-tool names injected when skill loads",
        f"  Skill tool specs:  per-skill — allowed-tool schemas injected when skill loads",
        f"  NOTE: only one skill body is active at a time; sequential loads replace the previous body",
        f"",
        f"── LEVEL 3 — Collaborator context (separate LLM call, own context window) ─────────────────────",
        f"  Collaborator instructions, tools, and skills run in their own context window.",
        f"  These tokens are NOT part of the supervisor's context — see collaborator detail below.",
        f"",
    ]

    # --- Agent tools ---
    active_tools   = info.get('active_resolved_tools', [])
    shadowed_tools = info.get('shadowed_resolved_tools', [])
    all_tools      = info.get('resolved_tools', [])
    tools_spec_total = info.get('tools_spec_est_tokens', 0)

    if all_tools:
        lines.append(
            f"Tools:               {len(all_tools)} declared  |  "
            f"{len(active_tools)} active at L1  |  "
            f"{len(shadowed_tools)} shadowed (removed from base set by skill binding)"
        )
        if active_tools:
            lines.append(f"  Active tools ({len(active_tools)})  — counted in L1 floor  ~{tools_spec_total} est. tokens total spec")
            for t in active_tools:
                if t.get('resolved'):
                    lines.append(f"    [{t['name']}]  ~{t['spec_est_tokens']} est. tokens  ({t['spec_chars']} chars)")
                else:
                    lines.append(f"    [{t['name']}]  ~{t['spec_est_tokens']} est. tokens (fallback — definition not found)")
        if shadowed_tools:
            lines.append(f"  Shadowed tools ({len(shadowed_tools)})  — NOT in L1 floor (removed from base set; only callable when owning skill is active)")
            for t in shadowed_tools:
                if t.get('resolved'):
                    lines.append(f"    [{t['name']}]  ~{t['spec_est_tokens']} est. tokens  (spec exists but not loaded at L1)")
                else:
                    lines.append(f"    [{t['name']}]  ~{t['spec_est_tokens']} est. tokens (fallback — definition not found; not loaded at L1)")
    else:
        lines.append("Tools:               0")

    # Tool-binding shadows (SK-6 reliability risk).
    # wxO platform behaviour: when a skill's allowed-tools lists a tool, that tool
    # is removed from the agent's base tool set while a skill is active. If the same
    # tool also appears in agent tools:, the agent silently loses it the moment any
    # skill loads — it cannot call it again until the skill is unloaded.
    # This is NOT a token issue (spec is counted once at L1). It is a reliability
    # risk: the agent may attempt to call a tool it no longer has access to.
    #
    # Subclassification shown below:
    #   "skill-only" = shadowed AND not referenced in agent instructions/guidelines
    #     → highest-confidence fix: remove from agent tools: entirely
    #   regular shadow = shadowed but IS referenced in agent text
    #     → author likely intended agent-level access; moving tool out of the skill's
    #       allowed-tools (or restructuring) may be needed
    all_shadows = [
        (s['name'], t)
        for s in info.get('skills', [])
        for t in s.get('tool_binding_shadows', [])
    ]
    skill_only = info.get('skill_only_tools', [])
    skill_only_set = set(skill_only)

    if all_shadows:
        lines.append(f"Tool-binding shadows: {len(all_shadows)} detected  ← SK-6 reliability risk (silent execution gap)")
        for skill_name, tool_name in all_shadows:
            if tool_name in skill_only_set:
                lines.append(
                    f"  [{tool_name}] shadowed by skill [{skill_name}]  "
                    f"← not referenced in agent text — safe to remove from agent tools:"
                )
            else:
                lines.append(
                    f"  [{tool_name}] shadowed by skill [{skill_name}]  "
                    f"← referenced in agent text — review intent; agent loses this tool when any skill is active"
                )
    else:
        lines.append("Tool-binding shadows: none")

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
        nested_skills = len(c['skills'])
        lines.append(f"  [{c['name']}]{loc_flag}  ← {c['display_name']}")
        lines.append(f"    kind: {c['kind']}  llm: {c['llm']}")
        lines.append(
            f"    instructions: {c['instructions_length']} lines  "
            f"|  {c.get('instructions_chars', '?')} chars  "
            f"|  ~{c.get('instructions_est_tokens', '?')} est. tokens  "
            f"|  guidelines: {c['guidelines_count']}"
        )
        # Routing tokens: name + description injected on every supervisor turn
        # so the supervisor can decide whether to dispatch to this collaborator.
        lines.append(
            f"    routing tokens:  ~{c.get('routing_est_tokens', '?')} est. tokens/supervisor-turn"
            f"  (name ~{c.get('name_est_tokens', '?')} + desc ~{c.get('description_est_tokens', '?')})"
        )
        # Per-tool spec tokens: cost paid when the supervisor/collaborator
        # decides which tool to invoke.
        c_resolved_tools = c.get('resolved_tools', [])
        c_tools_spec_total = c.get('tools_spec_est_tokens', 0)
        if c_resolved_tools:
            any_c_tool_resolved = any(t.get('resolved') for t in c_resolved_tools)
            lines.append(
                f"    tools ({len(c_resolved_tools)}):  ~{c_tools_spec_total} est. tokens total spec"
                + ("" if any_c_tool_resolved else "  (unresolved tools use ~200 token fallback)")
                + f"  collaborators: {nested_collabs}  skills: {nested_skills}"
            )
            for t in c_resolved_tools:
                if t.get('resolved'):
                    lines.append(
                        f"      [{t['name']}]  ~{t['spec_est_tokens']} est. tokens  ({t['spec_chars']} chars)"
                    )
                else:
                    lines.append(f"      [{t['name']}]  ~{t['spec_est_tokens']} est. tokens (fallback — definition not found)")
        else:
            lines.append(f"    tools: 0  collaborators: {nested_collabs}  skills: {nested_skills}")
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
        flags = []
        if s.get('name_too_long'):
            flags.append(f"NAME TOO LONG ({s['name_length']} chars, limit 64)")
        if s.get('description_too_long'):
            flags.append(f"DESC TOO LONG ({s['description_length']} chars, limit 1024)")
        if s.get('unmatched_placeholders'):
            flags.append(f"UNMATCHED PLACEHOLDERS: {s['unmatched_placeholders']}")
        flag_str = ' [' + '; '.join(flags) + ']' if flags else ''
        lines.append(f"  [{s['name']}]{flag_str}")
        # Catalog cost: name+desc paid every agent turn (agent needs this to route to the skill)
        lines.append(
            f"    [L1 agent ctx]  catalog: ~{s.get('catalog_est_tokens', '?')} est. tokens/turn "
            f"(name ~{s.get('name_est_tokens', '?')} + desc ~{s.get('description_est_tokens', '?')})"
        )
        # Skill-level costs: paid only when this skill is loaded (Level 2 context)
        s_resolved_tools = s.get('resolved_allowed_tools', [])
        s_tools_spec_total = sum(t['spec_est_tokens'] for t in s_resolved_tools)
        # allowed-tool names (list) — injected when skill loads
        s_tool_list_tokens: int = sum(
            _estimate_tokens(t['name']) for t in s_resolved_tools
        )
        skill_load_total = s.get('body_est_tokens', 0) + s_tool_list_tokens + s_tools_spec_total
        lines.append(
            f"    [L2 skill load] body:    ~{s.get('body_est_tokens', '?')} est. tokens  "
            f"({s.get('body_chars', '?')} chars)"
        )
        if s_resolved_tools:
            any_s_tool_resolved = any(t.get('resolved') for t in s_resolved_tools)
            lines.append(
                f"    [L2 skill load] allowed-tools ({len(s_resolved_tools)})"
                f":  list ~{s_tool_list_tokens} tokens (names)"
                + f" + specs ~{s_tools_spec_total} tokens (schemas)"
                + ("" if any_s_tool_resolved else "  (unresolved tools use ~200 token fallback)")
            )
            for t in s_resolved_tools:
                if t.get('resolved'):
                    lines.append(
                        f"      [{t['name']}]  ~{t['spec_est_tokens']} est. tokens  ({t['spec_chars']} chars)"
                    )
                else:
                    lines.append(f"      [{t['name']}]  ~{t['spec_est_tokens']} est. tokens (fallback — definition not found)")
        else:
            lines.append("    [L2 skill load] allowed-tools: none")
        lines.append(
            f"    [L2 skill load] total:   ~{skill_load_total} est. tokens added to context when this skill is loaded"
        )
        shadows = s.get('tool_binding_shadows', [])
        if shadows:
            lines.append(
                f"    ⚠ tool-binding shadows ({len(shadows)}): {', '.join(shadows)}"
                f"  ← also in agent tools: — agent cannot call these when no skill is active (SK-6)"
            )
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

  # Save JSON extraction to the eval output directory (always written as JSON;
  # stdout output is controlled separately by --json / --compact / default)
  python extract_agent_info.py agent.yaml --output-dir eval/

  # Enrich tool specs from previously-extracted tool JSON files
  python extract_agent_info.py agent.yaml --output-dir eval/ --tools-dir eval/

  # Scan a toolkit directory directly — no pre-extraction step needed
  # (.py files with @tool/@flow + .json agentic-workflow/langflow are auto-detected)
  python extract_agent_info.py agent.yaml --tools-root /path/to/toolkit
  python extract_agent_info.py agent.yaml --search-root /project --tools-root /project/toolkit
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
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Directory to write the JSON extraction file into.  The file is named '
                             'agent_<name>_extracted.json and is always written as pretty-printed JSON, '
                             'independent of the --json / --compact stdout flag.  The directory is '
                             'created if it does not exist.')
    parser.add_argument('--tools-dir', type=str, default=None,
                        help='Directory containing tool_*_extracted.json files produced by '
                             'extract_tool_info.py --output-dir.  When supplied, every tool name '
                             'in the agent, collaborators, and skill allowed-tools lists is enriched '
                             'with spec_chars and spec_est_tokens from the matching JSON file.')
    parser.add_argument('--tools-root', type=str, default=None,
                        help='Root directory to scan for tool source files.  Recursively finds '
                             '.py files containing @tool or @flow decorators, and .json files '
                             'matching the agentic-workflow or langflow format.  Builds the spec '
                             'lookup inline — no separate extract_tool_info.py step required.  '
                             'When both --tools-dir and --tools-root are supplied, --tools-dir '
                             'entries take priority; --tools-root fills in any gaps.  '
                             'When omitted, the scan runs automatically against --search-root '
                             '(or the agent YAML directory if --search-root is also absent).')

    args = parser.parse_args()

    try:
        info = extract_agent_info(
            args.yaml_path,
            search_root=args.search_root,
            tools_dir=args.tools_dir,
            tools_root=args.tools_root,
        )

        if args.json:
            output_format = 'json'
        elif args.compact:
            output_format = 'compact'
        else:
            output_format = 'text'

        print(format_output(info, output_format, args.field))

        # --output-dir: persist the full JSON extraction to disk so evaluation
        # reports can reference it without re-running the extractor.
        if args.output_dir:
            out_dir = Path(args.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            agent_name = info.get('name', 'agent')
            # Sanitise to a safe filename component (spaces → underscores).
            safe_name = agent_name.replace(' ', '_')
            out_file = out_dir / f"agent_{safe_name}_extracted.json"
            out_file.write_text(json.dumps(info, indent=2), encoding='utf-8')
            print(f"Extraction saved: {out_file}", file=sys.stderr)

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
