"""
Flow Model Converter

This module handles the conversion of JSON Flow models to Flow objects and Python code.
It includes JSON preprocessing, Flow object construction, and Python code generation.
"""

import json
import sys
from typing import Any, Dict, List, Optional, TextIO, Tuple, cast

from ibm_watsonx_orchestrate.flow_builder.data_map import DataMap, DataMapSpec
from ibm_watsonx_orchestrate.flow_builder.flows.flow import CompiledFlow, Flow, UserFlow, Loop, Foreach
from ibm_watsonx_orchestrate.flow_builder.node import (
    Node, ToolNode, UserNode, AgentNode, PromptNode, ScriptNode, TimerNode, 
    DocProcNode, DocExtNode, DocClassifierNode, StartNode, EndNode, DecisionsNode
)
from ibm_watsonx_orchestrate.flow_builder.types import (
    BranchNodeSpec, Conditions, Expression, FlowSpec, ForeachPolicy, ForeachSpec, 
    LoopSpec, MatchPolicy, SchemaRef, ToolNodeSpec, UserField, UserFlowSpec, 
    UserForm, UserNodeSpec, AgentNodeSpec, PromptNodeSpec, ScriptNodeSpec, 
    TimerNodeSpec, StartNodeSpec, EndNodeSpec, DocProcSpec, DocExtSpec, 
    DocClassifierSpec, DecisionsNodeSpec, NodeIdCondition, EdgeIdCondition, 
    JsonSchemaObject
)
from ibm_watsonx_orchestrate.flow_builder.flows import Branch
from ibm_watsonx_orchestrate.flow_builder.flows.flow import FlowEdge

from flow_to_python import (
    NodePyGenerator, generate_flow_py_code, generate_schema_classes, 
    get_meaningful_classname
)


def convert_refs(obj: Any, path: str = "", verbose: bool = False) -> Any:
    """
    Convert $ref keys to ref in JSON objects.
    
    Args:
        obj: The JSON object to process
        path: Current path in the JSON structure (for debugging)
        verbose: Whether to print verbose output
        
    Returns:
        Processed object with $ref replaced by ref
    """
    if isinstance(obj, dict):
        # Create a new dict to avoid modifying during iteration
        new_obj = {}
        for key, value in obj.items():
            if key == "$ref":
                new_obj["ref"] = value
                if verbose:
                    print(f"  Converting '$ref' to 'ref' at {path}: {value}")
            else:
                new_obj[key] = convert_refs(value, f"{path}.{key}" if path else key, verbose)
        return new_obj
    elif isinstance(obj, list):
        return [convert_refs(item, f"{path}[{i}]", verbose) for i, item in enumerate(obj)]
    else:
        return obj


def extract_embedded_schemas(
    obj: Any, 
    schemas: Optional[Dict[str, Any]] = None, 
    path: str = "", 
    counter: Optional[Dict[str, int]] = None
) -> Tuple[Any, Dict[str, Any]]:
    """
    Extract embedded schemas from flow JSON and move them to the top-level schemas section.
    
    Args:
        obj: The JSON object to process
        schemas: Dictionary to store extracted schemas
        path: Current path in the JSON structure (for debugging)
        counter: Counter for generating unique schema names
        
    Returns:
        Tuple of (processed object, schemas dictionary)
    """
    if counter is None:
        counter = {"count": 0}
    
    if schemas is None:
        schemas = {}
    
    if isinstance(obj, dict):
        # Check if this is a schema object (has 'type' and 'properties')
        if "type" in obj and obj.get("type") in ["object", "array"] and "properties" in obj:
            # Process nested object properties recursively
            if obj.get("type") == "object" and "properties" in obj:
                properties_dict = obj["properties"]
                if isinstance(properties_dict, dict):
                    new_properties = {}
                    
                    for prop_name, prop_value in properties_dict.items():
                        # Check if property is an object with properties (nested schema)
                        if isinstance(prop_value, dict) and prop_value.get("type") == "object" and "properties" in prop_value:
                            # Process this nested schema recursively
                            processed_nested_schema, nested_schemas = extract_embedded_schemas(
                                prop_value, schemas, f"{path}.properties.{prop_name}", counter
                            )
                            
                            # Update schemas with any nested schemas found
                            schemas.update(nested_schemas)
                            
                            # Replace with a reference
                            new_properties[prop_name] = processed_nested_schema
                        else:
                            # Keep non-object properties as is
                            new_properties[prop_name] = prop_value
                    
                    # Update the properties with processed ones
                    obj_copy = obj.copy()
                    obj_copy["properties"] = new_properties
                    
                    # Generate a unique name for this schema
                    schema_name = f"{get_meaningful_classname(path)}_{counter['count']}"
                    counter["count"] += 1
                    schemas[schema_name] = obj_copy
                else:
                    # If properties is not a dict, treat as a regular schema
                    schema_name = f"{get_meaningful_classname(path)}_{counter['count']}"
                    counter["count"] += 1
                    schemas[schema_name] = obj
            else:
                # For non-object types or objects without nested schemas
                schema_name = f"{get_meaningful_classname(path)}_{counter['count']}"
                counter["count"] += 1
                schemas[schema_name] = obj
            
            # Replace with a reference
            return {"$ref": f"#/schemas/{schema_name}"}, schemas
        
        # Process each key-value pair
        new_obj = {}
        for key, value in obj.items():
            # Skip processing certain keys that shouldn't contain schemas
            if key in ["edges", "metadata", "position", "dimensions", "schemas"]:
                new_obj[key] = value
                continue
            
            # Process input_schema, output_schema, and other schema fields specially
            if key in ["input_schema", "output_schema", "private_schema", "item_schema"] and isinstance(value, dict) and value:
                if "type" in value and value.get("type") in ["object", "array"]:
                    # Special case: empty properties means schema is None
                    if not value.get("properties"):
                        new_obj[key] = None
                        continue
                    
                    # Process this schema recursively to handle nested schemas
                    processed_schema, nested_schemas = extract_embedded_schemas(
                        value, schemas, f"{path}.{key}", counter
                    )
                    
                    # Update schemas with any nested schemas found
                    schemas.update(nested_schemas)
                    
                    new_obj[key] = processed_schema
                else:
                    new_obj[key] = value
            else:
                # Recursively process other values
                name = key
                if key == "spec":
                    name = obj["spec"].get("name") or obj["spec"].get("display_name")
                    if name is None:
                        name = key
                elif key == "nodes":
                    name = obj["spec"].get("name") or obj["spec"].get("display_name")
                    if name is None:
                        name = key
                
                if key == "fields":
                    # Don't extract schemas from fields as they should be auto-generated later
                    new_obj[key] = value
                else:
                    new_value, schemas = extract_embedded_schemas(
                        value, schemas, f"{path}.{name}" if path else name, counter
                    )
                    new_obj[key] = new_value
        
        return new_obj, schemas
    
    elif isinstance(obj, list):
        new_list = []
        for i, item in enumerate(obj):
            new_item, schemas = extract_embedded_schemas(
                item, schemas, f"{path}[{i}]", counter
            )
            new_list.append(new_item)
        return new_list, schemas
    
    else:
        return obj, schemas


def handle_user_fields(fields: list, delete_schema: bool = True) -> list[UserField]:
    """
    Process user fields and handle their schemas.
    
    Args:
        fields: List of field dictionaries
        delete_schema: Whether to delete auto-generated schemas
        
    Returns:
        List of UserField objects
    """
    fields = [UserField.model_validate(field) for field in fields]
    # Since input and output schema for UserField are auto-generated, remove them to avoid confusion
    for field in fields:
        if delete_schema:
            if field.input_schema:
                field.input_schema = None
            if field.output_schema:
                field.output_schema = None
        if hasattr(field, "input_map") and field.input_map is not None:
            if field.input_map.spec:
                input_map = field.input_map.spec
                field.input_map.spec = DataMap.model_validate(input_map)
            else:
                field.input_map = None

    return fields


def build_flow_from_json(
    json_data: Dict[str, Any], 
    parent: Flow | None = None, 
    remove_tool_uuid: bool = False
) -> Flow:
    """
    Build a Flow object directly from JSON data.
    
    Args:
        json_data: The JSON data representing the flow
        parent: Parent flow for nested flows
        remove_tool_uuid: Whether to remove tool UUIDs
        
    Returns:
        Flow: The constructed Flow object with specialized node instances
    """
    # Create a new Flow object
    if "spec" not in json_data:
        print("Error: Invalid JSON - missing spec field", file=sys.stderr)
        raise ValueError("Invalid JSON - missing spec field")

    # Clean up schemas - empty dict means None
    raw_spec = json_data["spec"]
    if "input_schema" in raw_spec and raw_spec["input_schema"] == {}:
        raw_spec["input_schema"] = None
    if "output_schema" in raw_spec and raw_spec["output_schema"] == {}:
        raw_spec["output_schema"] = None
    if "private_schema" in raw_spec and raw_spec["private_schema"] == {}:
        raw_spec["private_schema"] = None

    # Handle different flow types
    if "kind" in raw_spec:
        if raw_spec["kind"] == "flow":
            flow2_spec: FlowSpec = FlowSpec.model_validate(raw_spec)
            flow: Flow = Flow(spec=flow2_spec)
        elif raw_spec["kind"] == "user_flow" or raw_spec["kind"] == "userflow":
            userflow_spec: UserFlowSpec = UserFlowSpec.model_validate(raw_spec)
            flow = UserFlow(spec=userflow_spec, parent=parent)
        elif raw_spec["kind"] == "loop":
            loop_spec: LoopSpec = LoopSpec.model_validate(raw_spec)
            flow = Loop(spec=loop_spec, parent=parent)
        elif raw_spec["kind"] == "foreach":
            # Fix JSON serialization for foreach policy
            if "foreach_policy" in raw_spec:
                if raw_spec["foreach_policy"].lower() == "parallel":
                    raw_spec["foreach_policy"] = ForeachPolicy.PARALLEL
                elif raw_spec["foreach_policy"].lower() == "sequential":
                    raw_spec["foreach_policy"] = ForeachPolicy.SEQUENTIAL
            foreach_spec: ForeachSpec = ForeachSpec.model_validate(raw_spec)
            flow = Foreach(spec=foreach_spec, parent=parent)
        else:
            raise ValueError(f"Invalid flow kind: {raw_spec['kind']}")
    else:
        raise ValueError("Missing flow kind")

    # Handle output map
    if "output_map" in raw_spec:
        flow.output_map = DataMapSpec.model_validate(raw_spec["output_map"])
    
    # Set the schemas
    if "schemas" in json_data:
        flow.schemas = {}
        for schema_name, schema_data in json_data["schemas"].items():
            flow.schemas[schema_name] = JsonSchemaObject.model_validate(schema_data)
    
    # Process edges
    if "edges" in json_data:
        flow.edges = []
        for edge in json_data["edges"]:
            if isinstance(edge, dict):
                start = edge.get("start")
                end = edge.get("end")
                
                if start and end:
                    flow.edges.append(FlowEdge(
                        start=start,
                        end=end,
                        id=edge.get("id", None)
                    ))
                else:
                    print(f"Warning: Skipping edge with missing start or end: {edge}", file=sys.stderr)
            else:
                flow.edges.append(edge)
    
    # Process nodes
    if "nodes" in json_data:
        flow.nodes = {}
        # Track branch nodes and their cases to populate after all nodes are created
        branch_cases_to_populate = []
        
        for node_id, node_data in json_data["nodes"].items():
            if "spec" in node_data and "kind" in node_data["spec"]:
                kind = node_data["spec"]["kind"]
                
                # Create specialized node based on kind
                if kind == "tool":
                    node_spec = ToolNodeSpec.model_validate(node_data["spec"])
                    if remove_tool_uuid and node_spec.tool and isinstance(node_spec.tool, str):
                        node_spec.tool = node_spec.tool.split(":")[0]
                    flow.nodes[node_id] = ToolNode(spec=node_spec)
                    
                elif kind == "branch":
                    evaluator = node_data["spec"]["evaluator"]
                    
                    # Determine if this is a Conditions object
                    if isinstance(evaluator, dict) and "conditions" in evaluator:
                        conditions_list = []
                        for condition in evaluator["conditions"]:
                            if "node_id" in condition:
                                conditions_list.append(NodeIdCondition.model_validate(condition))
                            elif "edge_id" in condition:
                                conditions_list.append(EdgeIdCondition.model_validate(condition))
                            else:
                                raise ValueError(f"Unknown condition type: {condition}")
                        evaluator = Conditions(conditions=conditions_list)
                    elif isinstance(evaluator, dict) and "expression" not in evaluator:
                        evaluator = Conditions.model_validate(evaluator)
                    else:
                        evaluator = Expression.model_validate(evaluator)
                    
                    # Handle match policy
                    match_policy = MatchPolicy.FIRST_MATCH
                    if "match_policy" in node_data["spec"]:
                        match_policy_str = node_data["spec"]["match_policy"]
                        if match_policy_str == "FIRST_MATCH":
                            match_policy = MatchPolicy.FIRST_MATCH
                        elif match_policy_str == "ANY_MATCH":
                            match_policy = MatchPolicy.ANY_MATCH
                    
                    # Normalize cases format - convert object format to string format
                    if "cases" in node_data["spec"]:
                        cases = node_data["spec"]["cases"]
                        normalized_cases = {}
                        for key, value in cases.items():
                            if isinstance(value, dict) and "node" in value:
                                # Object format: {"node": "nodeId", "display_name": "..."}
                                normalized_cases[key] = value["node"]
                            elif isinstance(value, str):
                                # Already in string format
                                normalized_cases[key] = value
                            else:
                                # Unknown format, keep as is
                                normalized_cases[key] = value
                        node_data["spec"]["cases"] = normalized_cases
                    
                    node_data["spec"]["evaluator"] = evaluator
                    node_data["spec"]["match_policy"] = match_policy
                    node_spec = BranchNodeSpec.model_validate(node_data["spec"])
                    branch = Branch(spec=node_spec, containing_flow=flow)
                    flow.nodes[node_id] = branch
                    branch.policy(match_policy)
                    
                    # Store branch and cases for later population (after all nodes are created)
                    if "cases" in node_data["spec"]:
                        branch_cases_to_populate.append((branch, node_data["spec"]["cases"]))
                
                elif kind == "user_flow" or kind == "userflow":
                    user_nested_flow: Flow = build_flow_from_json(node_data, parent=flow, remove_tool_uuid=remove_tool_uuid)
                    user_flow: UserFlow = cast(UserFlow, user_nested_flow)
                    flow.nodes[node_id] = user_flow
                    
                elif kind == "loop":
                    loop_nested_flow = build_flow_from_json(node_data, parent=flow, remove_tool_uuid=remove_tool_uuid)
                    loop_flow: Loop = cast(Loop, loop_nested_flow)
                    flow.nodes[node_id] = loop_flow
                    
                elif kind == "foreach":
                    foreach_nested_flow = build_flow_from_json(node_data, parent=flow, remove_tool_uuid=remove_tool_uuid)
                    foreach_flow: Foreach = cast(Foreach, foreach_nested_flow)
                    flow.nodes[node_id] = foreach_flow
                    
                elif kind == "user":
                    node_spec = UserNodeSpec.model_validate(node_data["spec"])
                    node_spec.input_schema = None
                    node_spec.output_schema = None
                    
                    if "form" in node_data["spec"]:
                        node_spec.form = UserForm.model_validate(node_data["spec"]["form"])
                        if "fields" in node_data["spec"]["form"]:
                            node_spec.form.fields = handle_user_fields(fields=node_data["spec"]["form"]["fields"])
                    
                    if "fields" in node_data["spec"]:
                        node_spec.fields = handle_user_fields(node_data["spec"]["fields"])
                    
                    flow.nodes[node_id] = UserNode(spec=node_spec)
                    
                elif kind == "agent":
                    node_spec = AgentNodeSpec.model_validate(node_data["spec"])
                    flow.nodes[node_id] = AgentNode(spec=node_spec)
                    
                elif kind == "prompt":
                    node_spec = PromptNodeSpec.model_validate(node_data["spec"])
                    flow.nodes[node_id] = PromptNode(spec=node_spec)
                    
                elif kind == "script":
                    node_spec = ScriptNodeSpec.model_validate(node_data["spec"])
                    flow.nodes[node_id] = ScriptNode(spec=node_spec)
                    
                elif kind == "timer":
                    node_spec = TimerNodeSpec.model_validate(node_data["spec"])
                    flow.nodes[node_id] = TimerNode(spec=node_spec)
                    
                elif kind == "docproc":
                    node_spec = DocProcSpec.model_validate(node_data["spec"])
                    flow.nodes[node_id] = DocProcNode(spec=node_spec)
                    
                elif kind == "docext":
                    node_spec = DocExtSpec.model_validate(node_data["spec"])
                    flow.nodes[node_id] = DocExtNode(spec=node_spec)
                    
                elif kind == "docclassifier":
                    node_spec = DocClassifierSpec.model_validate(node_data["spec"])
                    flow.nodes[node_id] = DocClassifierNode(spec=node_spec)
                    
                elif kind == "decisions":
                    node_spec = DecisionsNodeSpec.model_validate(node_data["spec"])
                    flow.nodes[node_id] = DecisionsNode(spec=node_spec)
                    
                elif kind == "start":
                    node_spec = StartNodeSpec.model_validate(node_data["spec"])
                    flow.nodes[node_id] = StartNode(spec=node_spec)
                    
                elif kind == "end":
                    node_spec = EndNodeSpec.model_validate(node_data["spec"])
                    flow.nodes[node_id] = EndNode(spec=node_spec)
                    
                else:
                    flow.nodes[node_id] = Node(spec=node_data["spec"])
            else:
                flow.nodes[node_id] = Node(spec=node_data.get("spec", {}))

            # Handle input_map
            if "input_map" in node_data:
                flow.nodes[node_id].input_map = DataMapSpec.model_validate(node_data["input_map"])
        
        # Now populate branch cases after all nodes have been created
        for branch, cases in branch_cases_to_populate:
            for key, value in cases.items():
                branch.case(key, value)
    
    # Set metadata if present
    if "metadata" in json_data:
        flow.metadata = json_data["metadata"]
    
    return flow


def generate_imports(spec: Any, out: TextIO) -> None:
    """Generate import statements based on the flow specification."""
    out.write("from typing import List, Optional, Dict, Any, Union\n")
    out.write("from pydantic import BaseModel, Field\n")
    out.write("from ibm_watsonx_orchestrate.flow_builder.flows import (\n")
    out.write("    Flow, flow, START, END")
    
    # Add all node type imports
    imports = {
        "Branch", "UserFlow", "Foreach", "Loop", "ToolNode", "AgentNode",
        "UserNode", "ScriptNode", "PromptNode", "DecisionsNode", "StartNode",
        "EndNode", "DocProcNode", "DocExtNode", "DocClassifierNode", "TimerNode"
    }
    
    if imports:
        out.write(",\n    " + ", ".join(sorted(imports)))
    out.write("\n)\n")
    
    out.write("from ibm_watsonx_orchestrate.agent_builder.tools.types import JsonSchemaObject\n")
    out.write("from ibm_watsonx_orchestrate.flow_builder.data_map import DataMap, DataMapSpec\n")
    out.write("from ibm_watsonx_orchestrate.flow_builder.types import (\n")
    out.write("    Assignment, Conditions, Expression, MatchPolicy, BranchNodeSpec, ToolNodeSpec, UserNodeSpec, AgentNodeSpec,\n")
    out.write("    PromptNodeSpec, ScriptNodeSpec, TimerNodeSpec, StartNodeSpec, EndNodeSpec, UserFlowSpec,\n")
    out.write("    DocProcSpec, DocExtSpec, DocClassifierSpec, DecisionsNodeSpec,\n")
    out.write("    DocProcInput, DocProcKVPSchema, DocProcField, DocProcOutputFormat,\n")
    out.write("    Position, Dimensions, PromptExample, PromptLLMParameters, NodeErrorHandlerConfig, EdgeIdCondition, NodeIdCondition,\n")
    out.write("    UserField, UserForm, UserFormButton, SchemaRef\n")
    out.write(")\n")
    out.write("from ibm_watsonx_orchestrate.flow_builder.types import UserFieldKind\n")
    out.write("\n\n")


def generate_helper_functions(out: TextIO) -> None:
    """Generate helper functions for creating nodes."""
    out.write("""
def create_branch_node(aflow, evaluator, name=None, display_name=None):
    \"\"\"
    Helper function to create a branch node.
    
    Args:
        aflow: The flow object
        evaluator: Expression to evaluate for branching
        name: Name of the branch node (optional)
        display_name: Display name for the node (optional)
        
    Returns:
        The created branch node
    \"\"\"
    return aflow.branch(evaluator=evaluator)

def create_data_map(assignments):
    \"\"\"
    Helper function to create a data map for variable assignments.
    
    Args:
        assignments: List of assignment dictionaries with target_variable and value_expression
        
    Returns:
        A DataMapSpec object with the specified assignments
    \"\"\"
    data_map = DataMap()
    for assignment in assignments:
        data_map.add(Assignment(
            target_variable=assignment["target_variable"],
            value_expression=assignment["value_expression"],
            default_value=assignment.get("default_value")
        ))

    return DataMapSpec(spec = data_map)

""")


def convert_to_python(
    flow: Flow,
    out: TextIO,
    include_helpers: bool = True
) -> None:
    """
    Convert a Flow model to Python code.
    
    Args:
        flow: The validated Flow model
        out: Output stream to write the generated code
        include_helpers: Whether to include helper functions
    """
    try:
        # Generate imports
        generate_imports(flow, out)
        
        # Generate schema classes
        schema_class_map = generate_schema_classes(flow.schemas, out)
        
        # Generate helper functions if requested
        if include_helpers:
            generate_helper_functions(out)
        
        # Generate flow code
        generate_flow_py_code(flow, schema_class_map, out, use_helpers=include_helpers)
        
    except Exception as e:
        out.write(f"\n# ERROR: An error occurred during code generation: {str(e)}\n")
        out.write("# Please check the JSON model and try again.\n\n")
        out.write("def build_error_flow(aflow: Flow = None) -> Flow:\n")
        out.write("    # This is a placeholder due to an error in code generation\n")
        out.write("    return aflow\n")


def convert(
    json_file: str,
    output_file: Optional[str] = None,
    flow_name: Optional[str] = None,
    display_name: Optional[str] = None,
    remove_tool_uuid: bool = False,
    include_helpers: bool = True,
    verbose: bool = False,
    debug: bool = False,
    validate_only: bool = False
) -> int:
    """
    Main conversion function that orchestrates the entire process.
    
    Args:
        json_file: Path to input JSON file
        output_file: Path to output Python file (None for stdout)
        flow_name: Optional new name for the flow
        display_name: Optional new display name for the flow
        remove_tool_uuid: Whether to remove tool UUIDs
        include_helpers: Whether to include helper functions
        verbose: Enable verbose output
        debug: Enable debug output
        validate_only: Only validate without generating code
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Read JSON file
        if verbose:
            print(f"Reading JSON file: {json_file}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        except UnicodeDecodeError:
            with open(json_file, 'r', encoding='latin-1') as f:
                json_data = json.load(f)
                if verbose:
                    print("Note: File was not UTF-8 encoded, used latin-1 instead")
        
        # Preprocess JSON
        if verbose:
            print("Preprocessing JSON data...")
        
        if debug:
            print("\nBefore conversion:")
            print(json.dumps(json_data, indent=2)[:1000] + "...")
        
        # Extract embedded schemas
        json_data, extracted_schemas = extract_embedded_schemas(json_data)
        
        # Add extracted schemas to top-level
        if extracted_schemas:
            if not isinstance(json_data, dict):
                json_data = {"spec": json_data}
            
            if "schemas" not in json_data:
                json_data["schemas"] = {}
            
            schemas_dict = json_data["schemas"]
            if isinstance(schemas_dict, dict):
                for name, schema in extracted_schemas.items():
                    if name not in schemas_dict:
                        schemas_dict[name] = schema
            
            if verbose:
                print(f"Extracted {len(extracted_schemas)} embedded schemas")
        
        # Convert $ref to ref
        json_data = convert_refs(json_data, verbose=verbose)
        
        if debug:
            print("\nAfter conversion:")
            print(json.dumps(json_data, indent=2)[:1000] + "...")
        
        # Build Flow object
        if verbose:
            print("Building Flow model...")
        
        if not isinstance(json_data, dict):
            raise ValueError("JSON data must be a dictionary")
        
        flow = build_flow_from_json(json_data, parent=None, remove_tool_uuid=remove_tool_uuid)
        
        if verbose:
            print(f"Successfully loaded flow: {flow.spec.name}")
            print(f"Flow contains {len(flow.nodes)} nodes and {len(flow.edges)} edges")
        
        # Stop if only validation requested
        if validate_only:
            print("JSON model is valid.")
            return 0
        
        # Apply name changes
        if flow_name or display_name:
            if verbose:
                print("Applying flow name changes...")
            
            if flow_name:
                if not flow_name.isidentifier():
                    print(f"Error: '{flow_name}' is not a valid Python identifier", file=sys.stderr)
                    return 1
                if verbose:
                    print(f"Renaming flow from '{flow.spec.name}' to '{flow_name}'")
                flow.spec.name = flow_name
            
            if display_name:
                if verbose:
                    print(f"Setting display name to '{display_name}'")
                flow.spec.display_name = display_name
        
        # Generate Python code
        if output_file:
            with open(output_file, 'w', encoding='UTF-8') as f:
                if verbose:
                    print(f"Generating Python code to {output_file}")
                convert_to_python(flow, f, include_helpers=include_helpers)
                if verbose:
                    print(f"Successfully generated Python code")
        else:
            if verbose:
                print("Generating Python code to stdout:")
            convert_to_python(flow, sys.stdout, include_helpers=include_helpers)
        
        # Debug: dump compiled flow
        if debug and output_file:
            import os
            compiled_flow: CompiledFlow = flow.compile()
            output_json = os.path.splitext(output_file)[0] + ".json"
            compiled_flow.dump_spec(output_json)
        
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if debug:
            import traceback
            traceback.print_exc()
        return 1