"""
JSON Flow Model to Python Code Converter

This module converts JSON Flow models back to equivalent Python code.
It handles various node types, schemas, and edge connections to generate
a complete Python implementation of a Flow.

Usage:
    python main.py -f input.json -o output.py [-n new_name] [-d "New Display Name"]

Options:
    -f, --file          Path to input JSON file
    -o, --output        Path to output Python file
    -n, --name          Rename the top-level flow (must be a valid Python identifier)
    -d, --display-name  Set a new display name for the top-level flow
    -v, --verbose       Enable verbose output
    --validate-only     Only validate the JSON model without generating code
    --no-helper-functions  Don't include helper functions in the generated code
"""

import argparse


import json
import os
import re
import sys
from typing import Any, Dict, List, Set, TextIO, Tuple, Union, Optional, cast, TypedDict


from ibm_watsonx_orchestrate.flow_builder.data_map import DataMap
from ibm_watsonx_orchestrate.flow_builder.flows.flow import CompiledFlow, Flow, UserFlow, Loop, Foreach
from ibm_watsonx_orchestrate.flow_builder.node import (
    Node, ToolNode, UserNode, AgentNode, PromptNode, ScriptNode, TimerNode, DocProcNode, DocExtNode, DocClassifierNode, StartNode, EndNode, DecisionsNode
)
from ibm_watsonx_orchestrate.flow_builder.types import (
    BranchNodeSpec, Conditions, Expression, FlowSpec, ForeachPolicy, ForeachSpec, LoopSpec, MatchPolicy, SchemaRef, ToolNodeSpec, UserField, UserFlowSpec, UserForm, UserNodeSpec, AgentNodeSpec,
    PromptNodeSpec, ScriptNodeSpec, TimerNodeSpec, StartNodeSpec, EndNodeSpec,
    DocProcSpec, DocExtSpec, DocClassifierSpec, DecisionsNodeSpec, UserFlowSpec,
    NodeIdCondition, EdgeIdCondition, JsonSchemaObject
)
from ibm_watsonx_orchestrate.flow_builder.flows import Branch, Loop, Foreach
from ibm_watsonx_orchestrate.flow_builder.flows.flow import FlowEdge

# Import the NodePyGenerator for code generation
from node_py_generator import NodePyGenerator, generate_flow_py_code, safe_getattr, generate_schema_classes, get_meaningful_classname


# Version information
__version__ = "1.0.0"

# Global variables to store branch node information
branch_evaluators = {}
branch_cases = {}


def sanitize_name(name: str) -> str:
    """Convert a string to a valid Python identifier."""
    # Replace non-alphanumeric characters with underscores
    name = re.sub(r'[^0-9a-zA-Z_]', '_', name)
    # Ensure it doesn't start with a digit
    if name and name[0].isdigit():
        name = f"_{name}"
    return name


def get_valid_variable_name(node_id: str) -> str:
    """Generate a valid Python variable name from a node ID."""
    if node_id == "__start__":
        return "START"
    elif node_id == "__end__":
        return "END"
    else:
        return sanitize_name(node_id) + "_node"


def get_valid_json_schema_name(input_str: str) -> str:
    # Replace periods with double underscores to preserve nesting
    name = input_str.replace('.', '__')
    # Replace spaces with underscores
    name = name.replace(' ', '_')
    # Remove any characters that are not alphanumeric or underscore
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)
    # Optionally, convert to lowercase
    name = name.lower()
    return name

def generate_imports(spec: Any, out: TextIO) -> None:
    """Generate import statements based on the flow specification."""
    # Basic imports
    out.write("from typing import List, Optional, Dict, Any\n")
    out.write("from pydantic import BaseModel, Field\n")
    out.write("from ibm_watsonx_orchestrate.flow_builder.flows import (\n")
    out.write("    Flow, flow, START, END")
    
    # Determine additional imports based on node types
    imports = set()
    imports.add("Branch")
    imports.add("UserFlow")
    imports.add("Foreach")
    imports.add("Loop")
    imports.add("ToolNode")
    imports.add("AgentNode")
    imports.add("UserNode")
    imports.add("ScriptNode")
    imports.add("PromptNode")
    imports.add("DecisionsNode")
    imports.add("StartNode")
    imports.add("EndNode")
    imports.add("DocProcNode")
    imports.add("DocExtNode")
    imports.add("DocClassifierNode")
    imports.add("TimerNode")
    
    # Add additional imports if needed
    if imports:
        out.write(",\n    " + ", ".join(sorted(imports)))
    out.write("\n)\n")
    
    # Always include DataMap and Assignment imports since they're used in helper functions
    out.write("from ibm_watsonx_orchestrate.agent_builder.tools.types import JsonSchemaObject\n")
    out.write("from ibm_watsonx_orchestrate.flow_builder.data_map import DataMap, DataMapSpec\n")
    out.write("from ibm_watsonx_orchestrate.flow_builder.types import (\n")
    out.write("    Assignment, Conditions, Expression, MatchPolicy, BranchNodeSpec, ToolNodeSpec, UserNodeSpec, AgentNodeSpec,\n")
    out.write("    PromptNodeSpec, ScriptNodeSpec, TimerNodeSpec, StartNodeSpec, EndNodeSpec, UserFlowSpec,\n")
    out.write("    DocProcSpec, DocExtSpec, DocClassifierSpec, DecisionsNodeSpec, Position, Dimensions, PromptExample,\n")
    out.write("    PromptLLMParameters, NodeErrorHandlerConfig, EdgeIdCondition, NodeIdCondition, UserField, UserForm, UserFormButton, SchemaRef\n")
    out.write(")\n")
    
    # Check if we need UserFieldKind
    has_user_fields = False
    for node_id, node in spec.nodes.items():
        if node.spec.kind == "user" and hasattr(node.spec, "fields") and node.spec.fields:
            has_user_fields = True
            break
    
    if has_user_fields:
        out.write("from ibm_watsonx_orchestrate.flow_builder.types import UserFieldKind\n")
    else:
        # Always import UserFieldKind since we need it for user flow fields
        out.write("from ibm_watsonx_orchestrate.flow_builder.types import UserFieldKind\n")
    
    out.write("\n\n")


def generate_node_helper_functions(out: TextIO) -> None:
    """Generate helper functions for creating different node types."""
    # Tool node helper
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


def convert_spec(spec, out, include_helpers=True):
    """
    Convert a Flow model to Python code.
    
    Args:
        spec: The validated Flow model
        out: Output stream to write the generated code
        include_helpers: Whether to include helper functions in the generated code
    """
    try:
        # Generate imports
        generate_imports(spec, out)
        
        # Generate schema classes
        schema_class_map = generate_schema_classes(spec.schemas, out)
        
        # Generate helper functions if requested
        if include_helpers:
            generate_node_helper_functions(out)
        
        # Use the NodePyGenerator to generate code for all nodes and edges
        # This will handle user flow functions correctly
        generate_flow_py_code(spec, schema_class_map, out, use_helpers=include_helpers)
        
    except Exception as e:
        out.write(f"\n# ERROR: An error occurred during code generation: {str(e)}\n")
        out.write("# Please check the JSON model and try again.\n\n")
        # Still provide a minimal valid function that returns a Flow
        out.write("def build_error_flow(aflow: Flow = None) -> Flow:\n")
        out.write("    # This is a placeholder due to an error in code generation\n")
        out.write("    return aflow\n")


def main() -> int:
    """
    Main function to convert JSON flow model to Python code.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(
        description="Generate Python code from JSON Flow model",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-f", "--file", required=False, help="Path to input JSON file")
    parser.add_argument("-o", "--output", required=False, help="Path to output Python file")
    parser.add_argument("-n", "--name", help="Rename the top-level flow (must be a valid Python identifier)")
    parser.add_argument("-d", "--display-name", help="Set a new display name for the top-level flow (can be any string)")
    parser.add_argument("--remove-tool-uuid", action="store_true", help="Remove the tool UUID from the generated code")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--validate-only", action="store_true", help="Only validate the JSON model without generating code")
    parser.add_argument("--debug", action="store_true", help="Enable debug output for troubleshooting")
    parser.add_argument("-V", "--version", action="store_true", help="Show version information and exit")
    parser.add_argument("--no-helper-functions", action="store_true",
                        help="Don't include helper functions in the generated code")
    args = parser.parse_args()
    
    # Handle version flag
    if args.version:
        print_version()
        return 0
        
    # Check for required file argument
    if not args.file:
        parser.error("the following arguments are required: -f/--file")
        return 1  # This line won't be reached due to parser.error, but added for clarity

    try:
        # Read the JSON file
        if args.verbose:
            print(f"Reading JSON file: {args.file}")
            
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        except UnicodeDecodeError:
            # Try with a different encoding if UTF-8 fails
            with open(args.file, 'r', encoding='latin-1') as f:
                json_data = json.load(f)
                if args.verbose:
                    print("Note: File was not UTF-8 encoded, used latin-1 instead")
        
        # Preprocess JSON data to convert "$ref" to "ref" for schema references
        def convert_refs(obj: Any, path: str = "") -> Any:
            """
            Convert $ref keys to ref in JSON objects.
            
            Args:
                obj: The JSON object to process
                path: Current path in the JSON structure (for debugging)
                
            Returns:
                Processed object with $ref replaced by ref
            """
            if isinstance(obj, dict):
                # Create a new dict to avoid modifying during iteration
                new_obj = {}
                for key, value in obj.items():
                    if key == "$ref":
                        new_obj["ref"] = value
                        if args.verbose:
                            print(f"  Converting '$ref' to 'ref' at {path}: {value}")
                    else:
                        new_obj[key] = convert_refs(value, f"{path}.{key}" if path else key)
                return new_obj
            elif isinstance(obj, list):
                return [convert_refs(item, f"{path}[{i}]") for i, item in enumerate(obj)]
            else:
                return obj
        
        def extract_embedded_schemas(obj: Any, schemas: Optional[Dict[str, Any]] = None, path: str = "", counter: Optional[Dict[str, int]] = None) -> Tuple[Any, Dict[str, Any]]:
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
                            # use the last part of the path as the schema name
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
                    return { "$ref": f"#/schemas/{schema_name}" }, schemas
                
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
                            # There is a special case when the object properties is empty, it actually means the schema is None
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
                            name = key
                            name = obj["spec"].get("name") or obj["spec"].get("display_name")
                            if name is None:
                                name = key
                        
                        if key == "fields":
                            # we don't need to extract schemas from fields as they should be auto generated later
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
        
        # Apply the conversions
        if args.verbose:
            print("Preprocessing JSON data to convert '$ref' to 'ref' and extract embedded schemas...")
        
        if args.debug:
            print("\nBefore conversion:")
            print(json.dumps(json_data, indent=2)[:1000] + "..." if len(json.dumps(json_data)) > 1000 else json.dumps(json_data, indent=2))
        
        # First extract embedded schemas
        json_data, extracted_schemas = extract_embedded_schemas(json_data)
        
        # Add extracted schemas to the top-level schemas section
        if extracted_schemas:
            # Ensure json_data is a dictionary
            if not isinstance(json_data, dict):
                json_data = {"spec": json_data}
                
            if "schemas" not in json_data:
                json_data["schemas"] = {}
            
            # Merge extracted schemas with existing schemas
            schemas_dict = json_data["schemas"]
            if isinstance(schemas_dict, dict):
                for name, schema in extracted_schemas.items():
                    if name not in schemas_dict:
                        schemas_dict[name] = schema
            
            if args.verbose:
                print(f"Extracted {len(extracted_schemas)} embedded schemas to top-level schemas section")
        
        # Then convert $ref to ref
        json_data = convert_refs(json_data)
        
        if args.debug:
            print("\nAfter conversion:")
            print(json.dumps(json_data, indent=2)[:1000] + "..." if len(json.dumps(json_data)) > 1000 else json.dumps(json_data, indent=2))
        
        # Validate the JSON model
        if args.verbose:
            print("Validating JSON model...")
        
        remove_tool_uuid = False
        if args.remove_tool_uuid:
            remove_tool_uuid = True

        try:
            # Instead of using model_validate_json, directly build the Flow object from the JSON data
            # Ensure json_data is a dictionary before passing to build_flow_from_json
            if not isinstance(json_data, dict):
                raise ValueError("JSON data must be a dictionary")
            data = build_flow_from_json(json_data, parent=None, remove_tool_uuid=remove_tool_uuid)
        except Exception as e:
            if args.debug:
                import traceback
                print(f"Validation error details:", file=sys.stderr)
                traceback.print_exc()
            raise ValueError(f"Invalid Flow model: {str(e)}")
        
        if args.verbose:
            print(f"Successfully loaded and validated flow: {data.spec.name}")
            print(f"Flow contains {len(data.nodes)} nodes and {len(data.edges)} edges")
        
        # Stop here if only validation is requested
        if args.validate_only:
            print("JSON model is valid.")
            return 0  # Success
        
        # Apply name and display_name changes if specified
        if args.name or args.display_name:
            if args.verbose:
                print("Applying flow name changes...")
            
            if args.name:
                # Validate that the name is a valid Python identifier
                if not args.name.isidentifier():
                    print(f"Error: '{args.name}' is not a valid Python identifier", file=sys.stderr)
                    return 1
                
                if args.verbose:
                    print(f"Renaming flow from '{data.spec.name}' to '{args.name}'")
                data.spec.name = args.name
            
            if args.display_name:
                if args.verbose:
                    print(f"Setting display name to '{args.display_name}'")
                data.spec.display_name = args.display_name

        # Generate Python code
        include_helpers = not args.no_helper_functions
        
        if args.output:
            try:
                with open(args.output, 'w', encoding='UTF-8') as f:
                    if args.verbose:
                        print(f"Generating Python code to {args.output}")
                        if not include_helpers:
                            print("Helper functions will not be included")
                    convert_spec(data, f, include_helpers=include_helpers)
                    if args.verbose:
                        print(f"Successfully generated Python code to {args.output}")
            except IOError as e:
                print(f"Error writing to output file: {str(e)}", file=sys.stderr)
                return 1
        else:
            # If no output file is specified, print to stdout
            if args.verbose:
                print("Generating Python code to stdout:")
                if not include_helpers:
                    print("Helper functions will not be included")
            convert_spec(data, sys.stdout, include_helpers=include_helpers)

        if args.debug and args.output:
            compiled_flow: CompiledFlow = data.compile()
            # create an output file based on the file name specified in the args.output
            output_file = os.path.splitext(args.output)[0] + ".json"
            compiled_flow.dump_spec(output_file)
        
        return 0  # Success
    
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}", file=sys.stderr)
        print(f"Check that the file contains valid JSON syntax", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            print("\nDebug information:", file=sys.stderr)
            traceback.print_exc()
        return 1

def handle_user_fields(fields: list, delete_schema: bool = True) -> list[UserField]:
    fields = [UserField.model_validate(field) for field in fields]
    # since input and output schema for UserField are auto generated, we should remove them here or it will create confusion
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

def build_flow_from_json(json_data: Dict[str, Any], parent: Flow | None = None, remove_tool_uuid: bool = False) -> Flow:
    """
    Build a Flow object directly from JSON data without using model_validate_json.
    
    Args:
        json_data: The JSON data representing the flow
        
    Returns:
        Flow: The constructed Flow object with specialized node instances
    """
    # Create a new Flow object
    if "spec" not in json_data:
        print("Error: Invalid JSON - missing spec field", file=sys.stderr)
        raise ValueError("Invalid JSON - missing spec field")

    # we need to clean up the input_schema, output_schema and private_schema. If the schema is an empty dict, need to remove the key
    raw_spec = json_data["spec"]
    if "input_schema" in raw_spec and raw_spec["input_schema"] == {}:
        raw_spec["input_schema"] = None
    if "output_schema" in raw_spec and raw_spec["output_schema"] == {}:
        raw_spec["output_schema"] = None
    if "private_schema" in raw_spec and raw_spec["private_schema"] == {}:
        raw_spec["private_schema"] = None

    # new special handling for nested Flow object
    if "kind" in raw_spec:
        if raw_spec["kind"] == "flow":
            flow2_spec: FlowSpec = FlowSpec.model_validate(raw_spec)
            flow: Flow = Flow(spec=flow2_spec)
        elif raw_spec["kind"] == "user_flow" or raw_spec["kind"] == "userflow":
            userflow_spec: UserFlowSpec = UserFlowSpec.model_validate(raw_spec)
            flow = UserFlow(spec=userflow_spec, parent = parent)
        elif raw_spec["kind"] == "loop":
            loop_spec: LoopSpec = LoopSpec.model_validate(raw_spec)
            flow = Loop(spec=loop_spec, parent = parent)
        elif raw_spec["kind"] == "foreach":
            # we need to fix the JSON serialization for the foreach policy so it convert from string to enum
            if "foreach_policy" in raw_spec:
                if raw_spec["foreach_policy"].lower() == "parallel":
                    raw_spec["foreach_policy"] = ForeachPolicy.PARALLEL
                elif raw_spec["foreach_policy"].lower() == "sequential":
                    raw_spec["foreach_policy"] = ForeachPolicy.SEQUENTIAL
            foreach_spec: ForeachSpec = ForeachSpec.model_validate(raw_spec)
            flow = Foreach(spec=foreach_spec, parent = parent)
        else:
            raise ValueError(f"Invalid flow kind: {raw_spec['kind']}")
    else:
        raise ValueError("Missing flow kind")

    # handle output map
    from ibm_watsonx_orchestrate.flow_builder.data_map import DataMapSpec
    
    if "output_map" in raw_spec:
        flow.output_map = DataMapSpec.model_validate(raw_spec["output_map"])       
    
    # Set the schemas
    if "schemas" in json_data:
        flow.schemas = {}
        for schema_name, schema_data in json_data["schemas"].items():
            # Convert each schema to a JsonSchemaObject
            flow.schemas[schema_name] = JsonSchemaObject.model_validate(schema_data)
    
    # Process edges
    if "edges" in json_data:
        flow.edges = []
        for edge in json_data["edges"]:
            if isinstance(edge, dict):
                start = edge.get("start")
                end = edge.get("end")
                
                # Ensure we have valid start and end values
                if start and end:
                    flow.edges.append(FlowEdge(
                        start=start,
                        end=end,
                        id=edge.get("id", None)
                    ))
                else:
                    print(f"Warning: Skipping edge with missing start or end: {edge}", file=sys.stderr)
            else:
                # If it's already a FlowEdge object, just append it
                flow.edges.append(edge)
    
    # Process nodes
    if "nodes" in json_data:
        flow.nodes = {}
        for node_id, node_data in json_data["nodes"].items():
            # Create the appropriate node type based on the kind
            if "spec" in node_data and "kind" in node_data["spec"]:
                kind = node_data["spec"]["kind"]
                
                # Create specialized node based on kind
                if kind == "tool":
                    node_spec = ToolNodeSpec.model_validate(node_data["spec"])
                    if remove_tool_uuid and node_spec.tool and isinstance(node_spec.tool, str):
                        # check if there is an uuid specified in the "tool" field - e.g. "name:uuid"
                        node_spec.tool = node_spec.tool.split(":")[0]

                    flow.nodes[node_id] = ToolNode(spec=node_spec)
                elif kind == "branch":
                    # Check the 'evaluator' field to decide if it is an Expression or Conditions
                    evaluator = node_data["spec"]["evaluator"]
                    
                    # First, determine if this is a Conditions object with NodeIdCondition or EdgeIdCondition
                    if isinstance(evaluator, dict) and "conditions" in evaluator:
                        conditions_list = []
                        for condition in evaluator["conditions"]:
                            if "node_id" in condition:
                                # This is a NodeIdCondition
                                conditions_list.append(NodeIdCondition.model_validate(condition))
                            elif "edge_id" in condition:
                                # This is an EdgeIdCondition
                                conditions_list.append(EdgeIdCondition.model_validate(condition))
                            else:
                                # Unknown condition type
                                raise ValueError(f"Unknown condition type: {condition}")
                        
                        evaluator = Conditions(conditions=conditions_list)
                    elif isinstance(evaluator, dict) and "expression" not in evaluator:
                        # This is a regular Conditions object
                        evaluator = Conditions.model_validate(evaluator)
                    else:
                        # This is an Expression
                        evaluator = Expression.model_validate(evaluator)
                    
                    # now check match policy
                    match_policy = MatchPolicy.FIRST_MATCH
                    if "match_policy" in node_data["spec"]:
                        match_policy = node_data["spec"]["match_policy"]
                        if match_policy == "FIRST_MATCH":
                            match_policy = MatchPolicy.FIRST_MATCH
                        elif match_policy == "ANY_MATCH":
                            match_policy = MatchPolicy.ANY_MATCH
                    node_data["spec"]["evaluator"] = evaluator
                    node_data["spec"]["match_policy"] = match_policy

                    node_spec = BranchNodeSpec.model_validate(node_data["spec"])
                    branch = Branch(spec=node_spec, containing_flow=flow)

                    flow.nodes[node_id] = branch

                    branch.policy(match_policy)

                    # populate cases only if it exists
                    if "cases" in node_data["spec"]:
                        cases = node_data["spec"]["cases"]
                        for key, value in cases.items():
                            branch.case(key, value) 

                elif kind == "user_flow" or kind == "userflow":
                    # If the user flow has nodes, recursively process them
                    user_nested_flow: Flow = build_flow_from_json(node_data, parent=flow, remove_tool_uuid=remove_tool_uuid)
                    user_flow: UserFlow = cast(UserFlow, user_nested_flow)
                    
                    flow.nodes[node_id] = user_flow   
                elif kind == "loop":
                    # Recursively build the nested flow
                    loop_nested_flow = build_flow_from_json(node_data, parent=flow, remove_tool_uuid=remove_tool_uuid)
                    loop_flow: Loop = cast(Loop, loop_nested_flow)

                    flow.nodes[node_id] = loop_flow
                elif kind == "foreach":
                    # Recursively build the nested flow
                    foreach_nested_flow = build_flow_from_json(node_data, parent=flow, remove_tool_uuid=remove_tool_uuid)
                    foreach_flow: Foreach = cast(Foreach, foreach_nested_flow)
                    
                    flow.nodes[node_id] = foreach_flow
                elif kind == "user":
                    node_spec = UserNodeSpec.model_validate(node_data["spec"])
                    # since input and output schema for UserNode are auto generated, we should remove them here or it will create confusion
                    node_spec.input_schema = None
                    node_spec.output_schema = None

                    # we need special handling for forms
                    if "form" in node_data["spec"]:
                        node_spec.form = UserForm.model_validate(node_data["spec"]["form"])
                        if "fields" in node_data["spec"]["form"]:
                            node_spec.form.fields = handle_user_fields(fields=node_data["spec"]["form"]["fields"])

                    # we will need to also deserialize the UserField properly
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
                    # For unknown node types, use a generic Node
                    flow.nodes[node_id] = Node(spec=node_data["spec"])
            else:
                # If no kind is specified, use a generic Node
                flow.nodes[node_id] = Node(spec=node_data.get("spec", {}))

            # handle input_map 
            if "input_map" in node_data:
                flow.nodes[node_id].input_map = DataMapSpec.model_validate(node_data["input_map"])
    
    # Set metadata if present
    if "metadata" in json_data:
        flow.metadata = json_data["metadata"]
    
    return flow

def print_version():
    """Print version information."""
    print(f"JSON Flow Model to Python Code Converter v{__version__}")
    print("Copyright (c) IBM Corporation")
    print("Licensed under the Apache License, Version 2.0")


if __name__ == "__main__":
    import sys
    
    # Run the main function and exit with its return code
    sys.exit(main() or 0)
