#!/usr/bin/env python3
"""
Extract structural evidence from a watsonx Orchestrate agentic workflow artefact.

Supports:
  - Workflow JSON  (.json)  — exported from Flow Builder UI or authored via ADK
  - Python @flow   (.py)   — ADK pro-code flow using the @flow decorator

Outputs a compact structural summary covering all evidence needed for the
6 agentic-workflow-advisor detection checks:

  Check 1 — Sequential nodes with no data dependency (edges + input_maps)
  Check 2 — Unmapped required input fields / phantom mappings (input_maps, required fields)
  Check 3 — LLM-based routing over deterministic result (agent nodes + preceding node kinds)
  Check 4 — Oversized input schema (top-level input_schema field count)
  Check 5 — Tool node that should be a Logic Code Block (node descriptions)
  Check 6 — Agent node that should be a Generative Prompt node (agent message, tools, output_schema)

Usage:
  python extract_flow_info.py <workflow.json>      # JSON flow
  python extract_flow_info.py <workflow.py>        # Python @flow
  python extract_flow_info.py <workflow.json> --json   # machine-readable JSON output

Output is designed to be pasted directly into Bob chat for analysis.
"""

import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


# ---------------------------------------------------------------------------
# JSON flow extraction
# ---------------------------------------------------------------------------

def _extract_maps(input_map: Dict) -> Tuple[List[str], List[str]]:
    """
    Returns (explicitly_mapped_fields, phantom_fields) from an input_map spec.
    explicitly_mapped_fields: field names with a concrete target in maps[]
    phantom_fields: map entries whose target_variable doesn't match any known field
                    (caller must cross-check against input_schema.properties)
    """
    maps = input_map.get("spec", {}).get("maps", [])
    mapped = []
    raw_targets = []
    for m in maps:
        target = m.get("target_variable", "")
        if target.startswith("self.input."):
            field = target[len("self.input."):]
            mapped.append(field)
        raw_targets.append(target)
    return mapped, raw_targets


def _summarise_node(node_id: str, node_obj: Dict, parent_id: str = "") -> Dict:
    """Produce a flat summary dict for a single node."""
    spec = node_obj.get("spec", {})
    kind = spec.get("kind", "unknown")
    display_name = spec.get("display_name", "") or node_id
    description = spec.get("description", "")

    entry: Dict[str, Any] = {
        "id": node_id,
        "kind": kind,
        "display_name": display_name,
        "description": description,
    }
    if parent_id:
        entry["parent"] = parent_id

    # Input schema — required fields and total property count
    input_schema = spec.get("input_schema", {})
    required_fields = input_schema.get("required", [])
    all_properties = list(input_schema.get("properties", {}).keys())
    entry["input_schema_field_count"] = len(all_properties)
    entry["input_schema_required"] = required_fields
    entry["input_schema_properties"] = all_properties

    # Input map
    input_map = node_obj.get("input_map", {})
    fallback = input_map.get("spec", {}).get("fallback_strategy", "")
    maps = input_map.get("spec", {}).get("maps", [])
    explicitly_mapped, raw_targets = _extract_maps(input_map)

    entry["fallback_strategy"] = fallback
    entry["explicitly_mapped_fields"] = explicitly_mapped
    entry["map_count"] = len(maps)

    # Unmapped required fields (required but not explicitly mapped)
    unmapped_required = [f for f in required_fields if f not in explicitly_mapped]
    entry["unmapped_required_fields"] = unmapped_required

    # Phantom mappings (mapped to a field not in input_schema.properties)
    phantom = [f for f in explicitly_mapped if f not in all_properties]
    entry["phantom_mapped_fields"] = phantom

    # Agent-specific
    if kind == "agent":
        entry["agent_name"] = spec.get("agent", "")
        entry["message"] = spec.get("message", "")
        entry["thread_control_policy"] = spec.get("thread_control_policy", "")
        output_schema = spec.get("output_schema", {})
        output_props = list(output_schema.get("properties", {}).keys())
        entry["output_schema_properties"] = output_props

    # Branch-specific — extract condition expressions for Check 3
    if kind == "branch":
        conditions = spec.get("evaluator", {}).get("conditions", [])
        entry["branch_conditions"] = [
            {
                "expression": c.get("expression", ""),
                "default": c.get("default", False),
                "edge_id": c.get("edge_id", ""),
            }
            for c in conditions
        ]

    # Parallel-specific — list child node ids/display_names for Check 1
    if kind == "parallel":
        child_nodes = node_obj.get("nodes", {})
        # Exclude internal start/end plumbing nodes
        entry["parallel_children"] = [
            {
                "id": cid,
                "kind": cobj.get("spec", {}).get("kind", "unknown"),
                "display_name": cobj.get("spec", {}).get("display_name", cid),
            }
            for cid, cobj in child_nodes.items()
            if cobj.get("spec", {}).get("kind") not in ("start", "end")
        ]
        # Conditional parallel — has evaluator conditions beyond a default
        # Conditions may reference edge_id (UI) or node_id (ADK)
        conditions = spec.get("evaluator", {}).get("conditions", [])
        non_default = [c for c in conditions if not c.get("default", False)]
        entry["parallel_is_conditional"] = len(non_default) > 0
        entry["parallel_conditions"] = [
            {
                "expression": c.get("expression", ""),
                "target": c.get("node_id", "") or c.get("edge_id", ""),
            }
            for c in non_default
        ]

    return entry


def _walk_nodes(nodes_dict: Dict, parent_id: str = "") -> List[Dict]:
    """Recursively extract all nodes (including inside containers)."""
    result = []
    for node_id, node_obj in nodes_dict.items():
        summary = _summarise_node(node_id, node_obj, parent_id)
        result.append(summary)
        sub_nodes = node_obj.get("nodes")
        if isinstance(sub_nodes, dict) and sub_nodes:
            result.extend(_walk_nodes(sub_nodes, parent_id=node_id))
    return result


def _resolve_schema(schema_ref: Any, schemas: Dict) -> Dict:
    """
    Resolve a schema that may be inline or a $ref pointing to data["schemas"].
    e.g. {"$ref": "#/schemas/MyInput"} -> schemas["MyInput"]
    """
    if not isinstance(schema_ref, dict):
        return {}
    ref = schema_ref.get("$ref", "")
    if ref.startswith("#/schemas/"):
        key = ref[len("#/schemas/"):]
        return schemas.get(key, {})
    return schema_ref


def extract_json_flow_from_dict(data: Dict) -> Dict:
    spec = data.get("spec", {})
    flow_meta = data.get("metadata", {})
    schemas = data.get("schemas", {})

    # Top-level flow input schema — may be inline or $ref
    raw_input_schema = spec.get("input_schema", {}) or spec.get("private_schema", {})
    top_input_schema = _resolve_schema(raw_input_schema, schemas) if raw_input_schema else {}
    top_required = top_input_schema.get("required", [])
    top_properties = list(top_input_schema.get("properties", {}).keys())

    # Output map
    output_map = data.get("output_map", {})
    output_maps = output_map.get("spec", {}).get("maps", []) if output_map else []
    output_mapped_fields = []
    for m in output_maps:
        t = m.get("target_variable", "")
        if t.startswith("self.output."):
            output_mapped_fields.append(t[len("self.output."):])

    # Edges
    edges = data.get("edges", [])
    edge_list = [
        {"from": e.get("start", ""), "to": e.get("end", ""), "label": e.get("display_name", "")}
        for e in edges
    ]

    # All nodes
    all_nodes = _walk_nodes(data.get("nodes", {}))

    # Build edge adjacency for Check 1 (sequential detection)
    # node_id -> list of successor node_ids
    successors: Dict[str, List[str]] = {}
    predecessors: Dict[str, List[str]] = {}
    for e in edges:
        s, t = e.get("start", ""), e.get("end", "")
        successors.setdefault(s, []).append(t)
        predecessors.setdefault(t, []).append(s)

    # Find sequential runs of tool nodes at top level (Check 1)
    node_kinds = {n["id"]: n["kind"] for n in all_nodes}
    node_display = {n["id"]: n["display_name"] for n in all_nodes}
    node_parents = {n["id"]: n.get("parent", "") for n in all_nodes}

    # Sequential tool pairs: A -> B where both are tool kind, no dependency
    sequential_tool_pairs = []

    # Scan with raw maps for value_expression references
    def get_referenced_upstream(node_obj: Dict) -> List[str]:
        maps = node_obj.get("input_map", {}).get("spec", {}).get("maps", [])
        refs = []
        for m in maps:
            ve = m.get("value_expression", "")
            if ve:
                refs.append(ve)
        return refs

    raw_data_nodes = data.get("nodes", {})

    def find_sequential_pairs(nodes_dict: Dict, edge_list_local: List) -> List[Dict]:
        pairs = []
        local_successors: Dict[str, List[str]] = {}
        for e in edge_list_local:
            local_successors.setdefault(e["from"], []).append(e["to"])

        for nid, nobj in nodes_dict.items():
            if nobj.get("spec", {}).get("kind") != "tool":
                continue
            for succ_id in local_successors.get(nid, []):
                succ_obj = nodes_dict.get(succ_id, {})
                if succ_obj.get("spec", {}).get("kind") != "tool":
                    continue
                # Check if succ references nid's output in its value_expressions
                refs = get_referenced_upstream(succ_obj)
                nid_display = nobj.get("spec", {}).get("display_name", nid)
                nid_name = nobj.get("spec", {}).get("name", nid)
                has_dep = any(
                    nid_display in r or nid_name in r or nid in r
                    for r in refs
                )
                if not has_dep:
                    pairs.append({
                        "node_a": nobj.get("spec", {}).get("display_name", nid),
                        "node_b": succ_obj.get("spec", {}).get("display_name", succ_id),
                        "dependency": False,
                    })
        return pairs

    sequential_pairs = find_sequential_pairs(raw_data_nodes, edge_list)

    # Agent nodes for Check 3 and Check 6
    agent_nodes = [n for n in all_nodes if n["kind"] == "agent"]

    # For each agent node, find its immediate predecessor kind
    agent_predecessor_kinds = {}
    for an in agent_nodes:
        preds = predecessors.get(an["id"], [])
        agent_predecessor_kinds[an["display_name"]] = [
            {"id": p, "kind": node_kinds.get(p, "unknown"), "display_name": node_display.get(p, p)}
            for p in preds
        ]

    # Nodes with unmapped required fields (Check 2)
    unmapped_nodes = [
        {
            "display_name": n["display_name"],
            "kind": n["kind"],
            "unmapped_required_fields": n["unmapped_required_fields"],
            "fallback_strategy": n["fallback_strategy"],
        }
        for n in all_nodes
        if n["unmapped_required_fields"] and n["kind"] not in ("start", "end", "branch", "parallel", "foreach", "loop", "user_flow")
    ]

    # Nodes with phantom mappings (Check 2)
    phantom_nodes = [
        {
            "display_name": n["display_name"],
            "kind": n["kind"],
            "phantom_mapped_fields": n["phantom_mapped_fields"],
        }
        for n in all_nodes
        if n["phantom_mapped_fields"]
    ]

    return {
        "source": "json",
        "flow_name": spec.get("display_name", spec.get("name", "")),
        "is_under_specified": flow_meta.get("is_under_specified", False),
        "top_level_input_schema": {
            "required": top_required,
            "properties": top_properties,
            "field_count": len(top_properties),
        },
        "output_map": {
            "map_count": len(output_maps),
            "mapped_fields": output_mapped_fields,
        },
        "node_count": len(all_nodes),
        "node_kinds_present": sorted(set(n["kind"] for n in all_nodes)),
        "edges": edge_list,
        "check_1_sequential_tool_pairs": sequential_pairs,
        "check_1_parallel_containers": [
            {
                "display_name": n["display_name"],
                "children": n.get("parallel_children", []),
                "is_conditional": n.get("parallel_is_conditional", False),
                "conditions": n.get("parallel_conditions", []),
            }
            for n in all_nodes if n["kind"] == "parallel"
        ],
        "check_3_branch_nodes": [
            {
                "display_name": n["display_name"],
                "conditions": n.get("branch_conditions", []),
            }
            for n in all_nodes if n["kind"] == "branch"
        ],
        "check_2_unmapped_required_fields": unmapped_nodes,
        "check_2_phantom_mappings": phantom_nodes,
        "check_3_6_agent_nodes": [
            {
                "display_name": n["display_name"],
                "message": n.get("message", ""),
                "thread_control_policy": n.get("thread_control_policy", ""),
                "output_schema_properties": n.get("output_schema_properties", []),
                "predecessors": agent_predecessor_kinds.get(n["display_name"], []),
            }
            for n in agent_nodes
        ],
        "check_4_input_schema_field_count": len(top_properties),
        "check_5_tool_nodes": [
            {"display_name": n["display_name"], "description": n["description"]}
            for n in all_nodes
            if n["kind"] == "tool"
        ],
        "all_nodes": all_nodes,
    }


def extract_json_flow(file_path: str) -> Dict:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return extract_json_flow_from_dict(data)


# ---------------------------------------------------------------------------
# Python @flow extraction
# ---------------------------------------------------------------------------

def extract_python_flow(file_path: str) -> Dict:
    """
    Extract structural metadata from a Python ADK @flow-decorated file.
    Works at the AST level — does not execute the file.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)

    flows = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            dec_name = None
            if isinstance(dec, ast.Name):
                dec_name = dec.id
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                dec_name = dec.func.id
            if dec_name != "flow":
                continue

            # Count node invocations (calls inside the function body)
            calls = [
                n for n in ast.walk(node)
                if isinstance(n, ast.Call)
            ]
            # Extract parameter names and types
            params = []
            for arg in node.args.args:
                if arg.arg == "self":
                    continue
                ann = ""
                if arg.annotation:
                    try:
                        ann = ast.unparse(arg.annotation)
                    except Exception:
                        ann = "?"
                params.append({"name": arg.arg, "type": ann})

            # Extract return type
            ret = ""
            if node.returns:
                try:
                    ret = ast.unparse(node.returns)
                except Exception:
                    ret = "?"

            flows.append({
                "function_name": node.name,
                "docstring": ast.get_docstring(node) or "",
                "parameters": params,
                "return_type": ret,
                "estimated_node_invocations": len(calls),
                "note": (
                    "Python @flow source — structural checks (Check 1, 2) require "
                    "the compiled/exported JSON for full evidence. "
                    "Check 3, 6, 7 can be partially assessed from description and parameter names."
                ),
            })

    return {
        "source": "python",
        "file": str(Path(file_path).name),
        "flow_count": len(flows),
        "flows": flows,
        "note": (
            "For full Check 1 and Check 2 analysis, export this flow to JSON "
            "using the ADK and re-run: python extract_flow_info.py <exported.json>"
        ),
    }


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def format_text(data: Dict) -> str:
    lines = []

    if data["source"] == "python":
        lines += [
            f"## Flow Extraction — Python @flow",
            f"File: {data['file']}",
            f"Flows found: {data['flow_count']}",
            "",
        ]
        for fl in data["flows"]:
            lines += [
                f"### {fl['function_name']}",
                f"Description: {fl['docstring'] or '(none)'}",
                f"Return type: {fl['return_type'] or '(none)'}",
                f"Estimated node invocations: {fl['estimated_node_invocations']}",
            ]
            if fl["parameters"]:
                lines.append("Parameters:")
                for p in fl["parameters"]:
                    lines.append(f"  - {p['name']}: {p['type']}")
            lines += ["", f"Note: {fl['note']}", ""]
        lines.append(f"ℹ️  {data['note']}")
        return "\n".join(lines)

    # JSON flow
    lines += [
        f"## Flow Extraction — {data['flow_name']}",
        f"Nodes: {data['node_count']}  |  Node kinds: {', '.join(data['node_kinds_present'])}",
        f"Under-specified: {data['is_under_specified']}",
        "",
        f"### Top-level Input Schema",
        f"Field count: {data['check_4_input_schema_field_count']}",
        f"Required: {', '.join(data['top_level_input_schema']['required']) or '(none)'}",
        "",
    ]

    lines.append("### Edges (execution order)")
    for e in data["edges"]:
        label = f"  [{e['label']}]" if e["label"] else ""
        lines.append(f"  {e['from']}  →  {e['to']}{label}")
    lines.append("")

    lines.append("### Check 1 — Sequential tool node pairs (no data dependency)")
    if data["check_1_sequential_tool_pairs"]:
        for p in data["check_1_sequential_tool_pairs"]:
            lines.append(f"  ⚠  {p['node_a']}  →  {p['node_b']}  (no dependency found)")
    else:
        lines.append("  ✓ No sequential tool pairs without dependency detected")

    if data["check_1_parallel_containers"]:
        lines.append("  Parallel containers (children already concurrent — exempt from Check 1):")
        for pc in data["check_1_parallel_containers"]:
            children = ", ".join(
                f"{c['display_name']} ({c['kind']})" for c in pc["children"]
            ) or "(empty)"
            cond_flag = " ⚠ CONDITIONAL" if pc.get("is_conditional") else ""
            lines.append(f"  ✓  {pc['display_name']}{cond_flag}: [{children}]")
            if pc.get("is_conditional") and pc.get("conditions"):
                for cond in pc["conditions"]:
                    target = f" → {cond['target']}" if cond.get("target") else ""
                    lines.append(f"      condition: {cond['expression']}{target}")
    lines.append("")

    lines.append("### Check 2 — Unmapped required fields")
    if data["check_2_unmapped_required_fields"]:
        for n in data["check_2_unmapped_required_fields"]:
            fields = ", ".join(n["unmapped_required_fields"])
            lines.append(f"  ⚠  {n['display_name']} ({n['kind']}): unmapped required fields: {fields}  [fallback: {n['fallback_strategy'] or 'none'}]")
    else:
        lines.append("  ✓ All required fields are explicitly mapped")

    if data["check_2_phantom_mappings"]:
        lines.append("  Phantom mappings (mapped to non-existent fields):")
        for n in data["check_2_phantom_mappings"]:
            fields = ", ".join(n["phantom_mapped_fields"])
            lines.append(f"  ⚠  {n['display_name']} ({n['kind']}): phantom fields: {fields}")
    lines.append("")

    lines.append("### Check 3 — Branch nodes (condition expressions)")
    if data["check_3_branch_nodes"]:
        for bn in data["check_3_branch_nodes"]:
            lines.append(f"  Branch: {bn['display_name']}")
            for c in bn["conditions"]:
                if c["default"]:
                    lines.append(f"    (default fallback)")
                else:
                    lines.append(f"    condition: {c['expression']}")
    else:
        lines.append("  ✓ No branch nodes present")
    lines.append("")

    lines.append("### Check 3 / 6 — Agent nodes")
    if data["check_3_6_agent_nodes"]:
        for an in data["check_3_6_agent_nodes"]:
            preds = ", ".join(f"{p['display_name']} ({p['kind']})" for p in an["predecessors"]) or "(none)"
            lines += [
                f"  Agent: {an['display_name']}",
                f"    Predecessor(s): {preds}",
                f"    Message: {an['message'][:120] + '...' if len(an.get('message','')) > 120 else an.get('message','(none)')}",
                f"    Thread policy: {an['thread_control_policy'] or '(default)'}",
                f"    Output schema fields: {', '.join(an['output_schema_properties']) or '(none)'}",
                "",
            ]
    else:
        lines.append("  ✓ No agent nodes present")
    lines.append("")

    lines.append("### Check 5 — Tool nodes (description for external-call assessment)")
    for tn in data["check_5_tool_nodes"]:
        desc = tn["description"][:100] + "..." if len(tn.get("description", "")) > 100 else tn.get("description", "(none)")
        lines.append(f"  - {tn['display_name']}: {desc}")
    if not data["check_5_tool_nodes"]:
        lines.append("  ✓ No tool nodes present")

    return "\n".join(lines)


def format_json(data: Dict) -> str:
    return json.dumps(data, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    output_json = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    # --stdin mode: read JSON from stdin (used when user pastes JSON in chat)
    if "--stdin" in sys.argv or not args:
        if not sys.stdin.isatty():
            try:
                raw = sys.stdin.read()
                flow_json = json.loads(raw)
                data = extract_json_flow_from_dict(flow_json)
                print(format_json(data) if output_json else format_text(data))
                return
            except json.JSONDecodeError as e:
                print(f"Error: stdin is not valid JSON: {e}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                sys.exit(1)
        print("Usage: extract_flow_info.py <workflow.json|workflow.py> [--json]")
        print("       cat flow.json | extract_flow_info.py --stdin [--json]")
        print("\nExtracts structural evidence for all 6 agentic-workflow-advisor checks.")
        print("Note: --stdin only supports JSON input; Python @flow files must be passed as a file path.")
        print("Paste the output into Bob chat for analysis.")
        sys.exit(1)

    file_path = args[0]

    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    suffix = Path(file_path).suffix.lower()
    try:
        if suffix == ".json":
            data = extract_json_flow(file_path)
        elif suffix == ".py":
            data = extract_python_flow(file_path)
        else:
            print(f"Error: Unsupported file type '{suffix}'. Expected .json or .py", file=sys.stderr)
            sys.exit(1)

        print(format_json(data) if output_json else format_text(data))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
