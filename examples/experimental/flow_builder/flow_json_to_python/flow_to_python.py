"""
Flow to Python Code Generator

This module provides code generation functionality to convert Flow objects
and their nodes into equivalent Python code using the wxO ADK Flow programming model.
"""

import json
from io import StringIO
from platform import node
from typing import Any, Dict, List, TextIO, Optional, Union, cast, Tuple

from click.core import V
from pydantic import BaseModel

from ibm_watsonx_orchestrate.agent_builder.tools.types import ToolRequestBody, ToolResponseBody, JsonSchemaObject
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, Branch, UserFlow, Loop, Foreach
)
from ibm_watsonx_orchestrate.flow_builder.flows.constants import START, END
from ibm_watsonx_orchestrate.flow_builder.node import (
    Node, ToolNode, UserNode, AgentNode, PromptNode, ScriptNode, TimerNode,
    DocProcNode, DocExtNode, DocClassifierNode, StartNode, EndNode, DecisionsNode
)
from ibm_watsonx_orchestrate.flow_builder.types import (
    BranchNodeSpec, NodeSpec, SchemaRef, ToolNodeSpec, UserField, UserFieldKind, UserNodeSpec, AgentNodeSpec,
    PromptNodeSpec, ScriptNodeSpec, TimerNodeSpec, StartNodeSpec, EndNodeSpec,
    DocProcSpec, DocExtSpec, DocClassifierSpec, DecisionsNodeSpec,
    NodeIdCondition, EdgeIdCondition, Conditions, Expression
)

def normalize_identifier(name: str) -> str:
    """
    Normalize a name to be a valid Python identifier.
    Converts hyphens and other invalid characters to underscores.
    
    Args:
        name: The name to normalize
        
    Returns:
        A valid Python identifier
    """
    import re
    # Replace hyphens and other non-alphanumeric characters with underscores
    normalized = re.sub(r'[^0-9a-zA-Z_]', '_', name)
    # Ensure it doesn't start with a digit
    if normalized and normalized[0].isdigit():
        normalized = f"_{normalized}"
    return normalized


def get_valid_variable_name(node_id: Any, append_node: bool = False) -> str:
    """Generate a valid Python variable name from a node ID."""
    # Convert to string if not already
    if not isinstance(node_id, str):
        node_id = str(node_id)
        
    if node_id == "__start__":
        return "START"
    elif node_id == "__end__":
        return "END"
    else:
        # Use normalize_identifier for consistency
        name = normalize_identifier(node_id)
        if append_node:
            return name + "_node"
        else:
            return name


def get_meaningful_variable_name(node: Any, node_id: str, var_name_counts: Optional[Dict[str, Union[int, str]]] = None) -> str:
    """
    Generate a meaningful Python variable name from a node.
    Uses display_name if available and meaningful, otherwise falls back to node_id.
    
    Args:
        node: The node object (or None if not available)
        node_id: The node ID as fallback
        var_name_counts: Optional dictionary tracking variable name usage for collision detection
                        (stores int for counts, str for cached names with __cache__ prefix)
        
    Returns:
        A valid Python variable name with collision handling
    """
    import re
    
    # Memoization: Check if we've already generated a name for this node_id
    if var_name_counts is not None:
        cache_key = f"__cache__{node_id}"
        if cache_key in var_name_counts:
            return var_name_counts[cache_key]
    
    # Handle special cases
    if node_id in ["__start__", "__end__"]:
        return get_valid_variable_name(node_id)
    
    # Try to get display_name from node
    display_name = None
    if node is not None and hasattr(node, 'spec') and hasattr(node.spec, 'display_name'):
        display_name = node.spec.display_name
    
    # Use display_name if it's meaningful (not empty, not same as ID, not generic)
    base_name = None
    if display_name and display_name.strip() and display_name != node_id:
        # Check if it's not a generic name like "Form 1", "Text Output", etc.
        if not re.match(r'^(Form|Text|Input|Output|Field)\s+\d+$', display_name, re.IGNORECASE):
            # Clean up the display name
            name = display_name.strip()
            # Remove special characters and convert to snake_case
            name = re.sub(r'[^\w\s-]', '', name)  # Remove special chars except word chars, spaces, hyphens
            name = re.sub(r'[-\s]+', '_', name)  # Replace spaces/hyphens with underscores
            name = name.lower()
            # Remove leading/trailing underscores
            name = name.strip('_')
            
            # If we got a valid name, use it
            if name and not name[0].isdigit():
                base_name = name
    
    # Fallback to node_id with cleanup if no meaningful display name
    if base_name is None:
        # Remove UUID patterns from node_id
        cleaned_id = re.sub(r'_[a-f0-9]{8}_[a-f0-9]{4}_[a-f0-9]{4}_[a-f0-9]{4}_[a-f0-9]{12}', '', node_id)
        # Remove other long hex patterns
        cleaned_id = re.sub(r'_[a-f0-9]{8,}', '', cleaned_id)
        base_name = normalize_identifier(cleaned_id)
    
    # Handle collisions if tracking dictionary provided
    final_name = base_name
    if var_name_counts is not None:
        if base_name in var_name_counts:
            # Collision detected - append number
            var_name_counts[base_name] += 1
            final_name = f"{base_name}{var_name_counts[base_name]}"
        else:
            # First occurrence - track it
            var_name_counts[base_name] = 1
        
        # Cache the result for this node_id
        cache_key = f"__cache__{node_id}"
        var_name_counts[cache_key] = final_name
    
    return final_name

def safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get an attribute from an object."""
    try:
        return getattr(obj, attr) if hasattr(obj, attr) else default
    except (AttributeError, TypeError):
        return default


def safe_get(obj, key, default=None, value_kind: str = "str") -> Any:
    """Safely get a key from a dictionary-like object."""
    try:
        if isinstance(obj, dict):
            value = obj.get(key, default)
        else:
            value = getattr(obj, key) if hasattr(obj, key) else default
        if isinstance(value, str):
            if value_kind == "str":
                return value
            elif value_kind == "int":
                return int(value)
            elif value_kind == "float":
                return float(value)
            elif value_kind == "bool":
                return bool(value)
            else:
                # Try to parse as JSON, but return the string if it fails
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    return value
        else:
            return value

    except (AttributeError, TypeError, KeyError):
        return default


def get_meaningful_classname(path: str) -> str:
    # Given a path like 'flow_name.private_schema.properties.name1' return 'flow_name.name1'
    # Given a path like 'flow_name.private_schema' return 'flow_name.private_schema'
    # Given a path like 'flow_name' return 'flow_name'
    # Given a path like 'flow_name.private_schema.properties.name1.name2' return 'flow_name.name2'
    # Given a path like 'flow_name.private_schema.properties.name1.name2.name3' return 'flow_name.name3'

    # Split the path into its components
    parts: list[str] = path.split(".")
    if len(parts) == 1:
        return get_valid_variable_name(parts[0])
    elif len(parts) == 2:
        return get_valid_variable_name(f"{parts[0]}_{parts[1]}")
    elif len(parts) >= 3:
        if parts[-1] == "input_schema" or parts[-1] == "output_schema" or parts[-1] == "private_schema":
            return get_valid_variable_name(f"{parts[0]}_{parts[-2]}_{parts[-1]}")
        else:
            return get_valid_variable_name(f"{parts[0]}_{parts[-2]}_{parts[-1]}")
    else:
        return path


def capitalize_preserve_camel(s):
    return s[0].upper() + s[1:] if s else s


def get_schema_class_name(schema_name: str) -> str:
    """
    Generate a valid Python class name from a schema name.
    Simplifies names by removing flow IDs, UUIDs, and redundant suffixes.
    """
    import re
    
    # Store original for reference
    original_name = schema_name
    
    # Remove numeric suffixes at the end (e.g., _0, _1, _2)
    schema_name = re.sub(r'_\d+$', '', schema_name)
    
    # Remove flow ID patterns (e.g., _7958SB, _ABC123)
    schema_name = re.sub(r'_[A-Z0-9]{5,}(?=_|$)', '', schema_name)
    
    # Remove UUID patterns (e.g., _7b80bcc2_0393_45fd_b924_0aa5c022ebea)
    schema_name = re.sub(r'_[a-f0-9]{8}_[a-f0-9]{4}_[a-f0-9]{4}_[a-f0-9]{4}_[a-f0-9]{12}', '', schema_name)
    
    # Simplify ONLY top-level flow schemas (those that start with flow name and end with schema type)
    # Pattern: flow_name_input_schema (no node name in between)
    if re.match(r'^[^_]+_input_schema$', schema_name):
        return 'FlowInput'
    if re.match(r'^[^_]+_output_schema$', schema_name):
        return 'FlowOutput'
    if re.match(r'^[^_]+_private_schema$', schema_name):
        return 'FlowPrivate'
    
    # For node schemas, extract meaningful parts
    # Pattern: flow_name_CodeBlock_1_output_schema -> CodeBlock1Output
    match = re.search(r'_([A-Z][^_]+(?:_\d+)?)_(?:output|input)_schema$', schema_name)
    if match:
        node_part = match.group(1)
        schema_type = 'Output' if '_output_schema' in schema_name else 'Input'
        # Convert node_part to CamelCase (CodeBlock_1 -> CodeBlock1)
        node_part = re.sub(r'_(\d+)', r'\1', node_part)  # Remove underscore before numbers
        parts = node_part.split('_')
        camel_node = ''.join(capitalize_preserve_camel(part) for part in parts)
        return f"{camel_node}{schema_type}"
    
    # For prompt schemas with UUIDs or display names
    # Pattern: flow_name_prompt_xxx_input_schema -> PromptXxxInput
    match = re.search(r'_prompt_([^_]+(?:_[^_]+)?)_(?:output|input)_schema$', schema_name)
    if match:
        prompt_part = match.group(1)
        schema_type = 'Output' if '_output_schema' in schema_name else 'Input'
        # Try to extract meaningful name from display name if available
        # For now, just use a generic name with first part
        parts = prompt_part.split('_')
        if len(parts) > 0:
            # Use first meaningful part
            first_part = parts[0] if parts[0] not in ['get', 'set', 'update'] else '_'.join(parts[:2])
            camel_prompt = capitalize_preserve_camel(first_part)
            return f"{camel_prompt}Prompt{schema_type}"
        return f"Prompt{schema_type}"
    
    # For nested property schemas (e.g., properties_initialValues)
    match = re.search(r'properties_([^_]+)$', schema_name)
    if match:
        prop_name = match.group(1)
        return capitalize_preserve_camel(prop_name)
    
    # Fallback: Remove flow name prefix and convert to CamelCase
    # Remove first component (flow name)
    parts = schema_name.split('_')
    if len(parts) > 1:
        parts = parts[1:]  # Remove first part (flow name)
    
    # Remove _input/_output/_schema suffixes
    schema_name = '_'.join(parts)
    schema_name = re.sub(r'_(input|output|schema)$', '', schema_name)
    
    # Convert to CamelCase
    parts = schema_name.split('_')
    return ''.join(capitalize_preserve_camel(part) for part in parts)


def resolve_schema_ref(ref: str, schemas: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve a schema reference to the actual schema."""
    if not ref.startswith("#/schemas/"):
        return None
    
    schema_name = ref[len("#/schemas/"):]
    return schemas.get(schema_name)

def get_schema_class_from_ref(schema_ref: Any, schema_class_map: Dict[str, str]) -> Optional[str]:
    """Get schema class name from a schema reference."""
    # Handle objects with ref attribute
    if hasattr(schema_ref, "ref") and schema_ref.ref:
        ref = schema_ref.ref
        if isinstance(ref, str) and ref.startswith("#/schemas/"):
            schema_name = ref[len("#/schemas/"):]
            return schema_class_map.get(schema_name)
    
    # Handle dictionary with $ref key
    if isinstance(schema_ref, dict) and ("$ref" in schema_ref or "ref" in schema_ref):
        ref = schema_ref["$ref"] if "$ref" in schema_ref else schema_ref["ref"]
        if isinstance(ref, str):
            schema_name = ref.split('/')[-1]
            return schema_class_map.get(schema_name)
    
    # Handle direct string reference
    if isinstance(schema_ref, str):
        schema_name = schema_ref.split('/')[-1]
        return schema_class_map.get(schema_name)
    
    return None


def generate_schema_class(name: str, schema: Any, out: TextIO, schema_class_map: Dict[str, str], all_schemas: Optional[Dict[str, Any]] = None)-> None:
    """Generate a Pydantic model class for a schema."""
    class_name = get_schema_class_name(name)
    
    # Start class definition
    out.write(f"class {class_name}(BaseModel):\n")
    
    # Add docstring - use the cleaned class name instead of the original encoded name
    description = f"Schema for {class_name}"
    schema_description = safe_get(schema, "description")
    if schema_description:
        description = schema_description
        
    out.write(f'    """\n')
    out.write(f'    {description}\n')
    out.write(f'    """\n')
    
    # Add fields
    properties = {}
    
    # Handle different schema object types
    schema_properties = safe_get(schema, "properties")
    if schema_properties:
        properties = schema_properties
    
    if properties and isinstance(properties, dict):
        for prop_name, prop_schema in properties.items():
            # Normalize the property name to be a valid Python identifier
            normalized_prop_name = normalize_identifier(prop_name)
            
            field_type = "str"  # Default type
            
            # Check if this is a reference to another schema ($ref or ref after preprocessing)
            has_ref = (hasattr(prop_schema, "ref") and prop_schema.ref) or isinstance(prop_schema, SchemaRef) or safe_get(prop_schema, "$ref") is not None or safe_get(prop_schema, "ref") is not None
            
            if has_ref:
                field_type = get_schema_class_from_ref(prop_schema, schema_class_map)
            else:
                # Check for anyOf (union types)
                any_of = safe_get(prop_schema, "anyOf")
                if any_of and isinstance(any_of, list):
                    # Handle union types
                    union_types = []
                    for union_schema in any_of:
                        union_type = safe_get(union_schema, "type")
                        if union_type == "string":
                            union_types.append("str")
                        elif union_type == "number":
                            union_types.append("float")
                        elif union_type == "integer":
                            union_types.append("int")
                        elif union_type == "boolean":
                            union_types.append("bool")
                        elif union_type == "array":
                            # Handle array items in union
                            items = safe_get(union_schema, "items")
                            if items:
                                item_type = "Any"
                                items_type = safe_get(items, "type")
                                if items_type == "string":
                                    item_type = "str"
                                elif items_type == "number":
                                    item_type = "float"
                                elif items_type == "integer":
                                    item_type = "int"
                                elif items_type == "boolean":
                                    item_type = "bool"
                                union_types.append(f"List[{item_type}]")
                            else:
                                union_types.append("List[Any]")
                        elif union_type == "object":
                            union_types.append("Dict[str, Any]")
                        elif union_type == "null":
                            union_types.append("None")
                    
                    if union_types:
                        field_type = f"Union[{', '.join(union_types)}]"
                else:
                    # Determine field type
                    prop_type = safe_get(prop_schema, "type")
                    if prop_type:
                        if prop_type == "string":
                            field_type = "str"
                        elif prop_type == "number":
                            field_type = "float"
                        elif prop_type == "integer":
                            field_type = "int"
                        elif prop_type == "boolean":
                            field_type = "bool"
                        elif prop_type == "array":
                            # Handle array items
                            items = safe_get(prop_schema, "items")
                            if items:
                                item_type = "Any"
                                items_type = safe_get(items, "type")
                                
                                if items_type:
                                    if items_type == "string":
                                        item_type = "str"
                                    elif items_type == "number":
                                        item_type = "float"
                                    elif items_type == "integer":
                                        item_type = "int"
                                    elif items_type == "boolean":
                                        item_type = "bool"
                                        
                                field_type = f"List[{item_type}]"
                            else:
                                field_type = "List[Any]"
                        elif prop_type == "object":
                            field_type = "Dict[str, Any]"
            
            # Check if field is required
            required_fields = safe_get(schema, "required", [])
            is_required = prop_name in required_fields if required_fields else False
            
            # Add Field constructor if needed
            field_params = []
            
            # If the normalized name differs from original, add alias to preserve JSON compatibility
            if normalized_prop_name != prop_name:
                field_params.append(f'alias={repr(prop_name)}')
            
            # Get description
            description = f"{prop_name} field"
            prop_description = safe_get(prop_schema, "description", value_kind = "str")
            if prop_description is not None and isinstance(prop_description, str) and len(prop_description):
                description = prop_description
                field_params.append(f'description={repr(description)}')
            
            # Get default value - prefer schema-level default over field-level default
            default_value = None
            schema_level_default = safe_get(schema, "default")
            # Check if this field references another schema (has $ref or ref after preprocessing)
            is_ref_field = (hasattr(prop_schema, "ref") and prop_schema.ref) or isinstance(prop_schema, SchemaRef) or safe_get(prop_schema, "$ref") is not None or safe_get(prop_schema, "ref") is not None
            
            # First check if there's a schema-level default for this property
            if schema_level_default and isinstance(schema_level_default, dict) and prop_name in schema_level_default:
                default_value = schema_level_default[prop_name]
            else:
                # Fall back to field-level default
                default_value = safe_get(prop_schema, "default", value_kind=field_type if isinstance(field_type, str) else "str")
            
            # For fields with $ref, check if the referenced schema has a default
            ref_schema_default = None
            if is_ref_field and all_schemas:
                # Get the referenced schema name
                ref_value = None
                if hasattr(prop_schema, "ref") and prop_schema.ref:
                    ref_value = prop_schema.ref
                elif isinstance(prop_schema, dict):
                    ref_value = prop_schema.get("$ref") or prop_schema.get("ref")
                
                if ref_value and isinstance(ref_value, str):
                    ref_schema_name = ref_value.split('/')[-1]
                    ref_schema = all_schemas.get(ref_schema_name)
                    if ref_schema:
                        ref_schema_default = safe_get(ref_schema, "default")
            
            if default_value is not None:
                # Validate that default value is appropriate for the field type
                is_valid_default = True
                if isinstance(field_type, str):
                    # For list types, empty string is not a valid default
                    if field_type.startswith("List[") or field_type.startswith("Optional[List["):
                        if isinstance(default_value, str) and default_value == '':
                            is_valid_default = False
                
                if is_valid_default:
                    if isinstance(default_value, str):
                        field_params.append(f'default={repr(default_value)}')
                    else:
                        field_params.append(f'default={default_value}')
                elif not is_required:
                    # Invalid default for optional field, use None
                    field_params.append('default=None')
            elif not is_required:
                # For fields with $ref, check if we should generate a default
                if is_ref_field:
                    ref_class_name = get_schema_class_from_ref(prop_schema, schema_class_map)
                    if ref_class_name:
                        # Always use default_factory for custom class instantiation
                        field_params.append(f'default_factory={ref_class_name}')
                    else:
                        field_params.append('default=None')
                # For optional fields with custom class types and no explicit default,
                # generate a default by instantiating the referenced class
                elif isinstance(field_type, str) and "Optional[" in field_type:
                    # Extract the inner type from Optional[Type]
                    if field_type.startswith("Optional[") and field_type.endswith("]"):
                        class_name = field_type[9:-1]  # Remove "Optional[" and "]"
                    else:
                        class_name = field_type
                    # Check if this is a custom class (not a built-in type like List, Dict, str, int, etc.)
                    is_custom_class = (
                        not class_name.startswith("List[") and
                        not class_name.startswith("Dict[") and
                        not class_name.startswith("Union[") and
                        class_name not in ["str", "int", "float", "bool", "Any"]
                    )
                    if is_custom_class:
                        # Generate default by instantiating the class using default_factory
                        field_params.append(f'default_factory={class_name}')
                    else:
                        field_params.append('default=None')
                else:
                    field_params.append('default=None')
            
            # Get title
            title = safe_get(prop_schema, "title")
            if title:
                field_params.append(f'title={repr(title)}')
            
            # Determine if field should be Optional based on whether it has a non-None default
            has_non_none_default = any(
                param.startswith('default=') and not param.startswith('default=None')
                or param.startswith('default_factory=')
                for param in field_params
            )
            
            # Generate field definition using normalized name
            field_def = f"    {normalized_prop_name}: "
            # Check if field_type is already a Union containing None
            is_union_with_none = isinstance(field_type, str) and field_type.startswith("Union[") and "None" in field_type
            
            # Wrap in Optional if:
            # 1. Field is not required AND
            # 2. Field doesn't have a non-None default (fields with default=None still need Optional) AND
            # 3. Field type is not already a Union with None
            if not is_required and not has_non_none_default and not is_union_with_none:
                field_def += f"Optional[{field_type}]"
            else:
                field_def += str(field_type)
            
            # Always use Field constructor for consistency
            field_def += f" = Field({', '.join(field_params)})"
            
            out.write(field_def + "\n")
    else:
        # If no properties defined, add a default field
        if name.lower().endswith("input"):
            out.write(f'    input_data: Dict[str, Any] = Field(description={repr("Input data")})\n')
        elif name.lower().endswith("output"):
            out.write(f'    output_data: Dict[str, Any] = Field(description={repr("Output data")})\n')
        else:
            out.write(f'    data: Dict[str, Any] = Field(description={repr("Schema data")})\n')
    
    out.write("\n\n")


def generate_schema_classes(schemas: Dict[str, Any], out: TextIO) -> Dict[str, str]:
    """Generate Pydantic model classes for all schemas."""
    schema_class_map = {}
    generated_classes = set()  # Track already generated class names
    class_name_counts = {}  # Track how many times each base name is used
    
    # First pass: map all schema names to class names, handling collisions
    for name, schema in schemas.items():
        base_class_name = get_schema_class_name(name)
        
        # Handle collisions by appending a number
        if base_class_name in class_name_counts:
            class_name_counts[base_class_name] += 1
            class_name = f"{base_class_name}{class_name_counts[base_class_name]}"
        else:
            class_name_counts[base_class_name] = 1
            class_name = base_class_name
        
        schema_class_map[name] = class_name
    
    # Second pass: generate classes
    for name, schema in schemas.items():
        class_name = schema_class_map[name]
        
        # Skip if we've already generated this class (shouldn't happen now, but keep as safety)
        if class_name in generated_classes:
            continue
            
        generate_schema_class(name, schema, out, schema_class_map, schemas)
        generated_classes.add(class_name)
    
    return schema_class_map

class FlowPythonGenerator:
    """Base class for generating Python code for nodes."""

    @staticmethod
    def _generate_common_node_attributes(node: Node, var_name: str, flow_var: str,
                                        schema_class_map: Dict[str, str], out: TextIO,
                                        include_creation: bool = True,
                                        func_name: Optional[str] = None,
                                        mandatory_fields: list[str] = []) -> None:
        """
        Generate common attributes for all node types.
        
        Args:
            node: The node to generate code for
            var_name: The variable name for the node
            flow_var: The variable name for the flow
            schema_class_map: Dictionary mapping schema names to class names
            out: Output stream to write the generated code
            include_creation: Whether to include node creation code
            func_name: Optional function name to use instead of node.spec.kind
            mandatory_fields: List of mandatory field names
        """
        from enum import Enum
        # Determine the node type to use
        kind = func_name if func_name else node.spec.kind
        
        params: list[str] = []
        if include_creation:
            # Write the node creation line
            out.write(f"    {var_name}: {node.__class__.__name__} = {flow_var}.{kind}(\n")
            params.append(f'        name={repr(node.spec.name)}')
        
        # Add common attributes
        # Display name
        display_name = safe_getattr(node.spec, "display_name")
        if display_name:
            params.append(f'        display_name={repr(display_name)}')
        
        # Description
        description = safe_getattr(node.spec, "description")
        if description:
            params.append(f'        description={repr(description)}')
        
        # Handle input schema
        input_schema = safe_getattr(node.spec, "input_schema")
        if input_schema:
            input_schema_class = get_schema_class_from_ref(input_schema, schema_class_map)
            if input_schema_class:
                params.append(f'        input_schema={input_schema_class}')
        
        # Handle output schema
        output_schema = safe_getattr(node.spec, "output_schema")
        if output_schema:
            output_schema_class = get_schema_class_from_ref(output_schema, schema_class_map)
            if output_schema_class:
                params.append(f'        output_schema={output_schema_class}')

        # Handle private schema
        private_schema = safe_getattr(node.spec, "private_schema")
        if private_schema:
            private_schema_class = get_schema_class_from_ref(private_schema, schema_class_map)
            if private_schema_class:
                params.append(f'        private_schema={private_schema_class}')

        for field_name in mandatory_fields:
            field = safe_getattr(node.spec, field_name)
            if field:
                param: str = (f"        {field_name}=")
                if isinstance(field, str):
                    param += f'{repr(field)}'
                elif isinstance(field, SchemaRef):
                    schema_class = get_schema_class_from_ref(field, schema_class_map)
                    if schema_class:
                        param += (f"{schema_class}")
                elif isinstance(field, BaseModel):
                    param += f"{field.__class__.__name__}("
                    for field_key, field_value in field.__dict__.items():
                        if field_value:
                            if isinstance(field_value, str):
                                param += (f"{field_key}={repr(field_value)}, ")
                            else:
                                param += (f"{field_key}={field_value}, ")
                    param += (")")
                elif isinstance(field, Enum):
                    # For enums, use the class name and value
                    param += f"{field.__class__.__name__}.{field.name}"
                else:
                    param += (f"{field}")
                params.append(param)

        out.write(",\n".join(params))
        # Close the node creation
        if include_creation:
            out.write("\n    )\n")

        FlowPythonGenerator._generate_datamap_assignment(node, var_name, schema_class_map, out)

    @staticmethod
    def to_py(node: Node, flow_var: str, schema_class_map: Dict[str, str], edge_map: Optional[Dict[str, str]] = None,
              var_name_counts: Optional[Dict[str, Any]] = None, node_vars: Optional[Dict[str, str]] = None) -> str:
        """
        Generate Python code for a node.
        
        Args:
            node: The node to generate code for
            flow_var: The variable name for the flow
            schema_class_map: Dictionary mapping schema names to class names
            edge_map: Optional mapping of edge IDs to target node IDs (for branch conditions)
            var_name_counts: Optional dictionary tracking variable name usage for collision detection
            node_vars: Optional dictionary mapping node IDs to their variable names (to avoid regenerating names)
            
        Returns:
            String containing the Python code for the node
        """
        FlowPythonGenerator._new_schema_map = {} # initialize

        # Use a StringIO buffer to capture the output
        buffer = StringIO()
        
        # Get the node ID and variable name
        node_id = node.spec.name
        # Normalize the node ID to match keys in node_vars (hyphens -> underscores)
        normalized_node_id = normalize_identifier(node_id) if isinstance(node_id, str) else node_id
        # Use the variable name from node_vars if available, otherwise generate it
        # Try both normalized and original node_id as keys
        if node_vars and (normalized_node_id in node_vars or node_id in node_vars):
            var_name = node_vars.get(normalized_node_id) or node_vars.get(node_id) or get_meaningful_variable_name(node, node_id, var_name_counts)
        else:
            var_name = get_meaningful_variable_name(node, node_id, var_name_counts)
        
        # Skip start and end nodes - use predefined START and END constants
        if node_id in ["__start__", "__end__"]:
            return ""
        
        node_name = node_id if node.spec.display_name is None else node.spec.display_name
        # Dispatch based on node type
        #if isinstance(node, ToolNode):
        #    FlowPythonGenerator._generate_tool_node(node, var_name, flow_var, schema_class_map, buffer)
        if isinstance(node, Branch):
            FlowPythonGenerator._generate_branch_node(node, var_name, flow_var, schema_class_map, buffer, edge_map)
        elif isinstance(node, Loop):
            FlowPythonGenerator._generate_loop_flow_node(node, var_name, flow_var, schema_class_map, buffer, var_name_counts)
        elif isinstance(node, Foreach):
            FlowPythonGenerator._generate_foreach_flow_node(node, var_name, flow_var, schema_class_map, buffer, var_name_counts)
        elif isinstance(node, UserFlow):
            FlowPythonGenerator._generate_user_flow_node(node, var_name, flow_var, schema_class_map, buffer, var_name_counts)
        elif isinstance(node, UserNode):
            FlowPythonGenerator._generate_user_node(node, var_name, flow_var, schema_class_map, buffer)
        elif isinstance(node, ScriptNode):
            FlowPythonGenerator._generate_script_node(node, var_name, flow_var, schema_class_map, buffer)
        elif isinstance(node, DocProcNode):
            FlowPythonGenerator._generate_docproc_node(node, var_name, flow_var, schema_class_map, buffer)
        else:
            # Generic fallback for other node types
            FlowPythonGenerator._generate_any_node(node, var_name, flow_var, schema_class_map, buffer)

        return buffer.getvalue()
    
    @staticmethod
    def _generate_branch_node(node: Branch, var_name: str, flow_var: str, schema_class_map: Dict[str, str],
                             out: TextIO, edge_map: Optional[Dict[str, str]] = None) -> None:
        """Generate Python code for a branch node using the fluent conditions API."""
        
        # Try to get the evaluator expression
        evaluator = safe_getattr(node.spec, "evaluator")
        has_edge_conditions = False
        
        if evaluator:
            expression = safe_getattr(evaluator, "expression")
            if expression:
                # Simple expression - use the old approach
                FlowPythonGenerator._generate_any_node(node, var_name, flow_var, schema_class_map, out)
                FlowPythonGenerator._generate_node_field(node, var_name, ["evaluator"], schema_class_map, out, declare_spec=False)
            else:
                # Complex expression with conditions - check if we have EdgeIdConditions
                conditions = safe_getattr(evaluator, "conditions")
                if conditions:
                    # Check if any condition is an EdgeIdCondition
                    has_edge_conditions = any(isinstance(c, EdgeIdCondition) for c in conditions)
                    
                    if has_edge_conditions and edge_map:
                        # Use the new fluent API with .condition() calls
                        out.write(f"    # Create branch with conditions using fluent API\n")
                        out.write(f"    {var_name}: Branch = {flow_var}.conditions(\n")
                        out.write(f"        name={repr(node.spec.name)},\n")
                        if node.spec.display_name:
                            out.write(f"        display_name={repr(node.spec.display_name)}\n")
                        out.write(f"    )\n")
                        out.write(f"    \n")
                        
                        # Store conditions for later generation (after all nodes are defined)
                        if not hasattr(FlowPythonGenerator, '_branch_conditions'):
                            FlowPythonGenerator._branch_conditions = {}
                        FlowPythonGenerator._branch_conditions[var_name] = (conditions, edge_map)
                        
                        # Generate spec configuration
                        out.write(f"\n")
                        out.write(f"    {var_name}_spec: BranchNodeSpec = {var_name}.get_spec()\n")
                        
                        # Generate other spec attributes (position, match_policy, etc.)
                        if hasattr(node.spec, "position") and node.spec.position:
                            pos = node.spec.position
                            out.write(f"    {var_name}_spec.position = Position(x={pos.x}, y={pos.y})\n")
                        if hasattr(node.spec, "match_policy") and node.spec.match_policy:
                            out.write(f"    {var_name}_spec.match_policy = MatchPolicy.{node.spec.match_policy.name}\n")
                        out.write(f"\n")
                    else:
                        # Fall back to old approach for NodeIdCondition or when no edge_map
                        FlowPythonGenerator._generate_any_node(node, var_name, flow_var, schema_class_map, out)
                        
                        # Generate code for conditions
                        comment_name = node.spec.display_name if node.spec.display_name else var_name
                        out.write(f"    # Create branch conditions for node: {comment_name}\n")
                        out.write(f"    {var_name}_conditions = Conditions(conditions=[\n")
                        
                        for condition in conditions:
                            if isinstance(condition, NodeIdCondition):
                                out.write(f"        NodeIdCondition(\n")
                                condition_buffer = []
                                if hasattr(condition, "expression") and condition.expression:
                                    condition_buffer.append(f'            expression={repr(condition.expression)}')
                                condition_buffer.append(f'            node_id={repr(condition.node_id)}')
                                condition_buffer.append(f'            default={bool(condition.default)}')
                                if hasattr(condition, "metadata") and condition.metadata:
                                    metadata = condition.metadata
                                    if isinstance(metadata, dict):
                                        python_code = repr(metadata)
                                        condition_buffer.append(f'            metadata={python_code}')
                                out.write(",\n".join(condition_buffer))
                                out.write(f"\n        ),\n")
                            elif isinstance(condition, EdgeIdCondition):
                                out.write(f"        EdgeIdCondition(\n")
                                condition_buffer = []
                                if hasattr(condition, "expression") and condition.expression:
                                    condition_buffer.append(f'            expression={repr(condition.expression)}')
                                condition_buffer.append(f'            edge_id={repr(condition.edge_id)}')
                                condition_buffer.append(f'            default={bool(condition.default)}')
                                if hasattr(condition, "metadata") and condition.metadata:
                                    metadata = condition.metadata
                                    if isinstance(metadata, dict):
                                        python_code = repr(metadata)
                                        condition_buffer.append(f'            metadata={python_code}')
                                out.write(",\n".join(condition_buffer))
                                out.write(f"\n        ),\n")
                            else:
                                raise ValueError(f"Unknown condition type: {type(condition)}")
                        
                        out.write(f"    ])\n")
                        out.write(f"    {var_name}_spec.evaluator = {var_name}_conditions\n\n")
                else:
                    # No conditions, use standard node generation
                    FlowPythonGenerator._generate_any_node(node, var_name, flow_var, schema_class_map, out)
        else:
            # No evaluator, use standard node generation
            FlowPythonGenerator._generate_any_node(node, var_name, flow_var, schema_class_map, out)

        # Note: Condition calls are now generated separately after all nodes are defined
    
    @staticmethod
    def _generate_branch_cases(node: Branch, var_name: str, out: TextIO) -> None:
        """Generate Python code for branch cases after all nodes are defined."""
        # Process cases if we found any
        cases = safe_getattr(node.spec, "cases", {}) or {}
            
        if cases:
            # Track processed cases to avoid duplicates
            processed_cases = set()
            
            # Handle true case
            if "true" in cases:
                true_node = None
                if isinstance(cases["true"], dict) and "node" in cases["true"]:
                    true_node = cases["true"]["node"]
                else:
                    true_node = safe_get(cases["true"], "node")
                    
                if true_node:
                    true_node_var = get_valid_variable_name(true_node)
                    out.write(f"    {var_name}.case(True, {true_node_var})\n")
                    processed_cases.add(("true", true_node))
            
            # Handle false case
            if "false" in cases:
                false_node = None
                if isinstance(cases["false"], dict) and "node" in cases["false"]:
                    false_node = cases["false"]["node"]
                else:
                    false_node = safe_get(cases["false"], "node")
                    
                if false_node:
                    false_node_var = get_valid_variable_name(false_node)
                    out.write(f"    {var_name}.case(False, {false_node_var})\n")
                    processed_cases.add(("false", false_node))
            
            # Handle other cases
            for case_key, case_value in cases.items():
                if case_key not in ["true", "false"]:
                    case_node = None
                    if isinstance(case_value, dict) and "node" in case_value:
                        case_node = case_value["node"]
                    else:
                        case_node = safe_get(case_value, "node")
                        
                    if case_node and (case_key, case_node) not in processed_cases:
                        case_node_var = get_valid_variable_name(case_node)
                        if case_key == "__default__":
                            out.write(f"    {var_name}.default({case_node_var})\n")
                        else:
                            out.write(f'    {var_name}.case({repr(case_key)}, {case_node_var})\n')
                            processed_cases.add((case_key, case_node))
        
    @staticmethod
    def _generate_branch_condition_calls(var_name: str, conditions: List[Any], edge_map: Dict[str, str],
                                        node_vars: Dict[str, str], out: TextIO) -> List[str]:
        """
        Generate .condition() calls for a branch node using the fluent API.
        Returns a list of edge IDs that were handled by conditions (to skip in edge generation).
        """
        handled_edges = []
        out.write(f"    # Define conditional routing\n")
        
        first_condition = True
        for condition in conditions:
            if isinstance(condition, EdgeIdCondition):
                edge_id = condition.edge_id
                target_node_id = edge_map.get(edge_id)
                
                if target_node_id:
                    handled_edges.append(edge_id)
                    target_var = node_vars.get(target_node_id, f'"{target_node_id}"')
                    
                    # Handle START/END special cases
                    if target_var == '"__end__"':
                        target_var = node_vars.get("__end__", "END")
                    elif target_var == '"__start__"':
                        target_var = node_vars.get("__start__", "START")
                    
                    if first_condition:
                        out.write(f"    {var_name}.condition(\n")
                        first_condition = False
                    else:
                        out.write(f"    ).condition(\n")
                    
                    # Add expression if present
                    if hasattr(condition, "expression") and condition.expression:
                        out.write(f"        expression={repr(condition.expression)},\n")
                    
                    # Add to_node
                    out.write(f"        to_node={target_var}")
                    
                    # Add default if true
                    if hasattr(condition, "default") and condition.default:
                        out.write(f",\n        default=True")
                    
                    out.write(f"\n")
        
        if not first_condition:
            out.write(f"    )\n\n")
        
        return handled_edges
    
    @staticmethod
    def _generate_flow_attributes(flow: Flow, flow_var: str, schema_class_map: Dict[str, str],
                                 out: TextIO, var_name_counts: Optional[Dict[str, Any]] = None) -> None:
            """
            Generate code for common Flow attributes like nodes and edges.
            
            Args:
                flow: The Flow object to generate code for
                flow_var: The variable name for the flow
                schema_class_map: Dictionary mapping schema names to class names
                out: Output stream to write the generated code
            """
            # Generate node variables
            node_vars = {}
            for node_id, node in flow.nodes.items():
                if node_id == "__start__":
                    node_vars[node_id] = "START"
                elif node_id == "__end__":
                    node_vars[node_id] = "END"
                else:
                    # Get the node object to extract display_name
                    node = flow.nodes.get(node_id)
                    # Use node.spec.name as the key (not the dict key) to match what to_py() uses
                    spec_name = node.spec.name if node and hasattr(node, 'spec') else node_id
                    var_name = get_meaningful_variable_name(node, spec_name, var_name_counts)
                    node_vars[spec_name] = var_name  # Store with spec.name as key
            
            # Build edge_id to target_node_id mapping from edges
            edge_map = {}
            if hasattr(flow, "edges") and flow.edges:
                for edge in flow.edges:
                    try:
                        if hasattr(edge, "id") and hasattr(edge, "end"):
                            edge_map[edge.id] = edge.end
                        elif isinstance(edge, dict):
                            edge_id = edge.get("id")
                            target_id = edge.get("end") or edge.get("target_id")
                            if edge_id and target_id:
                                edge_map[edge_id] = target_id
                    except Exception:
                        pass
            
            # Store branch nodes to process their cases and conditions later
            branch_nodes = []
            
            # Initialize branch conditions storage
            if not hasattr(FlowPythonGenerator, '_branch_conditions'):
                FlowPythonGenerator._branch_conditions = {}
            FlowPythonGenerator._branch_conditions = {}
            
            # Generate nodes (but defer branch cases and conditions)
            for node_id, node in flow.nodes.items():
                if isinstance(node, Branch):
                    # Store branch node for later processing
                    branch_nodes.append((node_id, node))
                node_code = FlowPythonGenerator.to_py(node, flow_var, schema_class_map, edge_map, var_name_counts, node_vars)
                out.write(node_code)
            
            # Now generate branch condition calls after all nodes are defined
            handled_edges = set()
            for node_id, branch_node in branch_nodes:
                var_name = get_valid_variable_name(node_id)
                if var_name in FlowPythonGenerator._branch_conditions:
                    conditions, cond_edge_map = FlowPythonGenerator._branch_conditions[var_name]
                    edges_handled = FlowPythonGenerator._generate_branch_condition_calls(
                        var_name, conditions, cond_edge_map, node_vars, out
                    )
                    handled_edges.update(edges_handled)
                else:
                    # Fall back to old case-based approach
                    FlowPythonGenerator._generate_branch_cases(branch_node, var_name, out)
            
            # Generate edges (skip edges handled by branch conditions)
            if hasattr(flow, "edges") and flow.edges:
                FlowPythonGenerator._generate_edges(flow.edges, node_vars, flow_var, out, flow.nodes, handled_edges)
    
    @staticmethod
    def _generate_datamap_assignment(node: Node, var_name: str, schema_class_map: Dict[str, str], out: TextIO) -> None:
        """Generate Python code for a DataMap assignment."""
        if hasattr(node, "input_map") and node.input_map is not None:
            # Generate input_map code
            maps = node.input_map.spec.maps
            if maps:
                map_items = []
                for map_item in maps:
                    if map_item.target_variable:
                        if map_item.target_variable.startswith("self.input."):
                            input_variable = map_item.target_variable[len("self.input."):]
                        else:
                            raise ValueError(
                                f"Invalid target_variable '{map_item.target_variable}'. "
                                "Target_variable must start with'self.input.'."
                            )
                    else:
                        raise ValueError("Missing target_variable") 

                    if map_item.value_expression is not None:
                        out.write(f"    {var_name}.map_input({repr(input_variable)}, {repr(map_item.value_expression)}, {repr(map_item.default_value)})\n")
                    else:
                        out.write(f"    {var_name}.map_node_input_with_none({repr(input_variable)})\n")

        if hasattr(node, "output_map") and isinstance(node, Flow) and node.output_map is not None:
            # Generate output_map code
            maps = node.output_map.spec.maps
            if maps:
                map_items = []
                for map_item in maps:
                    if map_item.target_variable:
                        if map_item.target_variable.startswith("self.output."):
                            output_variable = map_item.target_variable[len("self.output."):]
                        else:
                            raise ValueError(
                                f"Invalid target_variable '{map_item.target_variable}'. "
                                "Target_variable must start with'self.output.'."
                            )
                    else:
                        raise ValueError("Missing target_variable") 

                    if map_item.value_expression is not None:
                        out.write(f"    {var_name}.map_output({repr(output_variable)}, {repr(map_item.value_expression)}, {repr(map_item.default_value)})\n")
                    else:
                        out.write(f"    {var_name}.map_flow_ouput_with_none({repr(output_variable)})\n")



    @staticmethod
    def _generate_foreach_flow_node(node: Foreach, var_name: str, flow_var: str, schema_class_map: Dict[str, str],
                                   out: TextIO, var_name_counts: Optional[Dict[str, int]] = None) -> None:
        """Generate Python code for a foreach flow node."""
        # Create a function name for this foreach flow
        normalized_name = normalize_identifier(node.spec.name)
        foreach_flow_func_name = f"build_{normalized_name}_flow"
        
        # Create the foreach flow node using common attributes
        comment_name = node.spec.display_name if node.spec.display_name else var_name
        out.write(f"    # Create foreach flow node: {comment_name}\n")
        FlowPythonGenerator._generate_common_node_attributes(
            node, var_name, flow_var, schema_class_map, out, True, "foreach", mandatory_fields=["item_schema"]
        )
        
        # Call the function to build the foreach flow
        out.write(f"\n    # Build the {node.spec.name} foreach flow\n")
        out.write(f"    {foreach_flow_func_name}({var_name})\n")
        
        # Generate a separate function to build this foreach flow
        # This will be added to a list of foreach flow functions to be defined at the top level
        if hasattr(node, "nodes") and node.nodes:
            # Create a StringIO buffer to capture the function definition
            function_buffer = StringIO()
            
            # Generate the function to build the foreach flow
            FlowPythonGenerator._generate_foreach_flow_function(node, foreach_flow_func_name, schema_class_map, function_buffer, var_name_counts)
            
            # Add the function definition to the global scope
            # We'll prepend this to the output in the main generate_flow_py_code function
            if not hasattr(FlowPythonGenerator, "_user_flow_functions"):
                FlowPythonGenerator._user_flow_functions = []
            
            # Check if this function is already in the list to avoid duplicates
            function_content = function_buffer.getvalue()
            if function_content not in FlowPythonGenerator._user_flow_functions:
                FlowPythonGenerator._user_flow_functions.append(function_content)
    
    @staticmethod
    def _generate_user_flow_node(node: UserFlow, var_name: str, flow_var: str, schema_class_map: Dict[str, str],
                                out: TextIO, var_name_counts: Optional[Dict[str, int]] = None) -> None:
        """Generate Python code for a user flow node."""
        # Create a function name for this user flow
        normalized_name = normalize_identifier(node.spec.name)
        user_flow_func_name = f"build_{normalized_name}_flow"
        
        # Create the user flow node without name/display_name parameters
        comment_name = node.spec.display_name if node.spec.display_name else var_name
        out.write(f"    # Create user flow node: {comment_name}\n")
        out.write(f"    {var_name} = {flow_var}.userflow()\n")
        
        # Call the function to build the user flow
        out.write(f"\n    # Build the {node.spec.name} user flow\n")
        out.write(f"    {user_flow_func_name}({var_name})\n")
        
        # Generate a separate function to build this user flow
        # This will be added to a list of user flow functions to be defined at the top level
        if hasattr(node, "nodes") and node.nodes:
            # Create a StringIO buffer to capture the function definition
            function_buffer = StringIO()
            
            # Generate the function to build the user flow
            FlowPythonGenerator._generate_user_flow_function(node, user_flow_func_name, schema_class_map, function_buffer, var_name_counts)
            
            # Add the function definition to the global scope
            # We'll prepend this to the output in the main generate_flow_py_code function
            if not hasattr(FlowPythonGenerator, "_user_flow_functions"):
                FlowPythonGenerator._user_flow_functions = []
            
            # Check if this function is already in the list to avoid duplicates
            function_content = function_buffer.getvalue()
            if function_content not in FlowPythonGenerator._user_flow_functions:
                FlowPythonGenerator._user_flow_functions.append(function_content)
    
    @staticmethod
    def _generate_loop_flow_node(node: Loop, var_name: str, flow_var: str, schema_class_map: Dict[str, str],
                                out: TextIO, var_name_counts: Optional[Dict[str, int]] = None) -> None:
        """Generate Python code for a loop flow node."""
        # Create a function name for this loop flow
        normalized_name = normalize_identifier(node.spec.name)
        loop_flow_func_name = f"build_{normalized_name}_flow"
        
        # Create the loop flow node using common attributes
        comment_name = node.spec.display_name if node.spec.display_name else var_name
        out.write(f"    # Create loop flow node: {comment_name}\n")
        FlowPythonGenerator._generate_common_node_attributes(
            node, var_name, flow_var, schema_class_map, out, True, "loop", mandatory_fields=["evaluator"]
        )
        
        # Call the function to build the loop flow
        out.write(f"\n    # Build the {node.spec.name} loop flow\n")
        out.write(f"    {loop_flow_func_name}({var_name})\n")
        
        # Generate a separate function to build this loop flow
        # This will be added to a list of loop flow functions to be defined at the top level
        if hasattr(node, "nodes") and node.nodes:
            # Create a StringIO buffer to capture the function definition
            function_buffer = StringIO()
            
            # Generate the function to build the loop flow
            FlowPythonGenerator._generate_loop_flow_function(node, loop_flow_func_name, schema_class_map, function_buffer, var_name_counts)
            
            # Add the function definition to the global scope
            # We'll prepend this to the output in the main generate_flow_py_code function
            if not hasattr(FlowPythonGenerator, "_user_flow_functions"):
                FlowPythonGenerator._user_flow_functions = []
            
            # Check if this function is already in the list to avoid duplicates
            function_content = function_buffer.getvalue()
            if function_content not in FlowPythonGenerator._user_flow_functions:
                FlowPythonGenerator._user_flow_functions.append(function_content)
    
    @staticmethod
    def _generate_loop_flow_function(node: Loop, function_name: str, schema_class_map: Dict[str, str],
                                    out: TextIO, var_name_counts: Optional[Dict[str, Any]] = None) -> None:
        """Generate a function to build a loop flow with all its nodes and edges."""
        # First, generate the function definition
        out.write(f"\n\ndef {function_name}(loop_flow: Loop):\n")
        out.write(f'    """\n')
        out.write(f'    Build the {node.spec.name} loop flow\n')
        out.write(f'    """\n')
        
        # Use the common flow attributes generator to handle nodes and edges
        # Pass through the parent's var_name_counts to maintain consistency across the flow hierarchy
        FlowPythonGenerator._generate_flow_attributes(node, "loop_flow", schema_class_map, out, var_name_counts)
        
        # Return the loop flow
        out.write("\n    return loop_flow\n")
    
    @staticmethod
    def _generate_foreach_flow_function(node: Foreach, function_name: str, schema_class_map: Dict[str, str],
                                       out: TextIO, var_name_counts: Optional[Dict[str, Any]] = None) -> None:
        """Generate a function to build a foreach flow with all its nodes and edges."""
        # First, generate the function definition
        out.write(f"\n\ndef {function_name}(foreach_flow: Foreach):\n")
        out.write(f'    """\n')
        out.write(f'    Build the {node.spec.name} foreach flow\n')
        out.write(f'    """\n')
        
        # Use the common flow attributes generator to handle nodes and edges
        # Pass through the parent's var_name_counts to maintain consistency across the flow hierarchy
        FlowPythonGenerator._generate_flow_attributes(node, "foreach_flow", schema_class_map, out, var_name_counts)
        
        # Return the foreach flow
        out.write("\n    return foreach_flow\n")
    
    @staticmethod
    def _generate_user_flow_function(node: UserFlow, function_name: str, schema_class_map: Dict[str, str],
                                    out: TextIO, var_name_counts: Optional[Dict[str, Any]] = None) -> None:
        """Generate a function to build a user flow with all its nodes and edges."""
        # First, generate the function definition
        out.write(f"\n\ndef {function_name}(user_flow: UserFlow):\n")
        out.write(f'    """\n')
        out.write(f'    Build the {node.spec.name} user flow\n')
        out.write(f'    """\n')
        
        # Use the common flow attributes generator to handle nodes and edges
        # Pass through the parent's var_name_counts to maintain consistency across the flow hierarchy
        FlowPythonGenerator._generate_flow_attributes(node, "user_flow", schema_class_map, out, var_name_counts)
        
        # Return the user flow
        out.write("\n    return user_flow\n")
    
    @staticmethod
    def _detect_form_field_method(field: UserField) -> str:
        """
        Detect which form field method to use based on field properties.
        Returns the method name (e.g., 'text_input_field', 'boolean_input_field').
        """
        kind = field.kind
        direction = field.direction
        ui_widget = None
        
        # Extract ui:widget from uiSchema if available
        if hasattr(field, 'uiSchema') and field.uiSchema:
            ui_widget = safe_get(field.uiSchema, 'ui:widget')
        
        # Map based on kind, direction, and ui:widget
        if kind == "any" and direction == "input":
            if ui_widget in ["SelectWidget", "ComboboxWidget"]:
                return "single_choice_input_field"
            elif ui_widget == "Table":
                return "single_choice_input_field"  # table view for single choice
        elif kind == "boolean" and direction == "input":
            return "boolean_input_field"
        elif kind == "text" and direction == "input":
            return "text_input_field"
        elif kind == "number" and direction == "input":
            return "number_input_field"
        elif kind == "date" and direction == "input":
            return "date_input_field"
        elif kind == "file" and direction == "input":
            return "file_upload_field"
        elif kind == "user" and direction == "input":
            return "user_input_field"
        elif kind == "array" and direction == "output":
            # Check if it's a table or bullet list
            if ui_widget == "Table":
                return "list_output_field"  # with columns
            else:
                return "list_output_field"  # simple list
        elif kind == "array" and direction == "input":
            if ui_widget == "MultiselectDropdown":
                return "multi_choice_input_field"
            elif ui_widget == "Table":
                return "multi_choice_input_field"  # table view
            elif ui_widget == "EditableTable":
                return "list_input_field"
        elif kind == "text" and direction == "output":
            # Text output field - check if it has a text property (message) or value (field)
            if hasattr(field, 'text') and field.text:
                return "message_output_field"
            elif ui_widget == "DataWidget":
                return "field_output_field"
            return "message_output_field"
        elif kind == "field" and direction == "output":
            return "field_output_field"
        elif kind == "message" and direction == "output":
            return "message_output_field"
        
        # Fallback - shouldn't reach here
        return "unknown_field"
    
    @staticmethod
    def _extract_columns_from_display_items(field: UserField) -> Dict[str, str] | None:
        """
        Extract columns parameter from display_items in input_map.
        
        display_items format: ["item.first_name", "item.last_name"]
        Returns: {"first_name": "First_name", "last_name": "Last_name"}
        
        Note: Display labels are lost during JSON compilation, so we generate
        capitalized field names as labels.
        """
        import json
        
        if not hasattr(field, 'input_map') or not field.input_map:
            return None
        
        # Find display_items assignment
        for assignment in field.input_map.spec.maps:
            if assignment.target_variable == "self.input.display_items":
                # Parse the value_expression which is a JSON array string
                try:
                    display_items = json.loads(assignment.value_expression)
                    if not display_items or not isinstance(display_items, list):
                        return None
                    
                    # Extract field names from "item.field_name" format
                    columns = {}
                    for item in display_items:
                        if isinstance(item, str) and item.startswith("item."):
                            field_name = item[5:]  # Remove "item." prefix
                            # Capitalize first letter and replace underscores for label
                            label = field_name.replace("_", " ").title()
                            columns[field_name] = label
                    
                    return columns if columns else None
                except (json.JSONDecodeError, AttributeError):
                    return None
        
        return None
    
    @staticmethod
    def _extract_dropdown_item_column(field: UserField) -> str | None:
        """
        Extract dropdown_item_column parameter from display_text in input_map.
        
        display_text format: "item.field_name"
        Returns: "field_name"
        """
        if not hasattr(field, 'input_map') or not field.input_map:
            return None
        
        # Find display_text assignment
        for assignment in field.input_map.spec.maps:
            if assignment.target_variable == "self.input.display_text":
                # Extract field name from "item.field_name" format
                value = assignment.value_expression
                if isinstance(value, str) and value.startswith("item."):
                    return value[5:]  # Remove "item." prefix
        
        return None
    
    @staticmethod
    def _extract_form_field_parameters(field: UserField, method_name: str, form_json_schema: Optional[JsonSchemaObject] = None) -> Dict[str, Any]:
        """
        Extract parameters for a form field method call.
        Returns a dictionary of parameter names to values.
        
        Args:
            field: The user field to extract parameters from
            method_name: The method name being called
            form_json_schema: The form's jsonSchema containing field definitions
        """
        params = {}
        
        # Common parameters
        params['name'] = field.name
        
        # Get field-specific schema from form's jsonSchema if available
        field_json_schema = None
        if form_json_schema and isinstance(form_json_schema, JsonSchemaObject):
            properties = form_json_schema.properties
            if properties and field.name in properties:
                field_json_schema = properties[field.name]
        
        # Label from display_name or uiSchema
        if field.display_name:
            params['label'] = field.display_name
        elif hasattr(field, 'uiSchema') and field.uiSchema:
            ui_title = safe_get(field.uiSchema, 'ui:title')
            if ui_title:
                params['label'] = ui_title
        
        # Required - check if field name is in input_schema.required
        if hasattr(field, 'input_schema') and field.input_schema:
            required_fields = safe_get(field.input_schema, 'required', [])
            if field.name in required_fields:
                params['required'] = True
        
        # Help text
        if hasattr(field, 'uiSchema') and field.uiSchema:
            ui_help = safe_get(field.uiSchema, 'ui:help')
            if ui_help:
                params['help_text'] = ui_help
            
            # Placeholder text
            ui_placeholder = safe_get(field.uiSchema, 'ui:placeholder')
            if ui_placeholder:
                params['placeholder_text'] = ui_placeholder
        
        # Method-specific parameters
        if method_name == "single_choice_input_field":
            # show_as_dropdown
            if hasattr(field, 'uiSchema') and field.uiSchema:
                ui_widget = safe_get(field.uiSchema, 'ui:widget')
                if ui_widget in ["SelectWidget", "ComboboxWidget"]:
                    params['show_as_dropdown'] = True
                elif ui_widget == "Table":
                    params['show_as_dropdown'] = False
            
            # columns - extract from input_map display_items (for table view)
            columns = FlowPythonGenerator._extract_columns_from_display_items(field)
            if columns:
                params['columns'] = columns
            
            # dropdown_item_column - extract from input_map display_text
            dropdown_item_column = FlowPythonGenerator._extract_dropdown_item_column(field)
            if dropdown_item_column:
                params['dropdown_item_column'] = dropdown_item_column
        
        elif method_name == "boolean_input_field":
            # single_checkbox
            if hasattr(field, 'uiSchema') and field.uiSchema:
                ui_options = safe_get(field.uiSchema, 'ui:options', {})
                label_option = safe_get(ui_options, 'label')
                if label_option == False:
                    params['single_checkbox'] = True
            # TODO: Extract true_label and false_label if available
        
        elif method_name == "text_input_field":
            # regex and regex_error_message
            if hasattr(field, 'regex') and field.regex:
                params['regex'] = field.regex
            if hasattr(field, 'regex_error_msg') and field.regex_error_msg:
                params['regex_error_message'] = field.regex_error_msg
        
        elif method_name == "number_input_field":
            # is_integer
            if hasattr(field, 'output_schema') and field.output_schema:
                value_type = safe_get(field.output_schema, 'properties', {}).get('value', {}).get('type')
                if value_type == 'integer':
                    params['is_integer'] = True
        
        elif method_name == "file_upload_field":
            # allow_multiple_files - check field_json_schema for "multi" or "type": "array"
            if field_json_schema:
                # Check for "multi" field (extra field in JsonSchemaObject)
                multi = getattr(field_json_schema, 'multi', None)
                if multi is True:
                    params['allow_multiple_files'] = True
                # Also check type
                elif field_json_schema.type == 'array':
                    params['allow_multiple_files'] = True
            # Fallback to output_schema
            elif hasattr(field, 'output_schema') and field.output_schema:
                value_type = safe_get(field.output_schema, 'properties', {}).get('value', {}).get('type')
                if value_type == 'array':
                    params['allow_multiple_files'] = True
            
            # file_max_size - check field_json_schema (extra field in JsonSchemaObject)
            if field_json_schema:
                file_max_size = getattr(field_json_schema, 'file_max_size', None)
                if file_max_size is not None:
                    params['file_max_size'] = file_max_size
        
        elif method_name == "list_output_field":
            # columns - extract from input_map display_items
            columns = FlowPythonGenerator._extract_columns_from_display_items(field)
            if columns:
                params['columns'] = columns
        
        elif method_name == "multi_choice_input_field":
            # show_as_dropdown
            if hasattr(field, 'uiSchema') and field.uiSchema:
                ui_widget = safe_get(field.uiSchema, 'ui:widget')
                if ui_widget == "MultiselectDropdown":
                    params['show_as_dropdown'] = True
                elif ui_widget == "Table":
                    params['show_as_dropdown'] = False
            
            # dropdown_item_column - extract from input_map display_text
            dropdown_item_column = FlowPythonGenerator._extract_dropdown_item_column(field)
            if dropdown_item_column:
                params['dropdown_item_column'] = dropdown_item_column
            
            # columns - extract from input_map display_items (for table view)
            columns = FlowPythonGenerator._extract_columns_from_display_items(field)
            if columns:
                params['columns'] = columns
            
            # TODO: Extract minItems, maxItems
        
        elif method_name == "list_input_field":
            # columns - extract from input_map display_items
            columns = FlowPythonGenerator._extract_columns_from_display_items(field)
            if columns:
                params['columns'] = columns
        
        elif method_name == "message_output_field":
            # message - extract from field.text
            if hasattr(field, 'text') and field.text:
                params['message'] = field.text
        
        elif method_name == "user_input_field":
            # multiple_users
            if hasattr(field, 'output_schema') and field.output_schema:
                value_type = safe_get(field.output_schema, 'properties', {}).get('value', {}).get('type')
                if value_type == 'array':
                    params['multiple_users'] = True
                else:
                    params['multiple_users'] = False
        
        elif method_name == "message_output_field":
            # message - TODO: extract from field metadata
            pass
        
        return params
    
    @staticmethod
    def _gather_field_parameters(field: UserField) -> list[str]:
        """Gather the parameters of a field."""
        # Get the field type
        params: list[str] = []

        for param_key, param_value in field.__dict__.items():
            if param_value is None:
                continue
            if param_key == "kind":
                # Handle field kind
                kind_value = UserFieldKind.str_to_code(field.kind)
                params.append(f"kind={kind_value}")
            else:
                params.append(f"{param_key}={repr(param_value)}")
        return params

    @staticmethod
    def _generate_user_node(node: UserNode, var_name: str, flow_var: str, schema_class_map: Dict[str, str],
                           out: TextIO) -> None:
        """Generate Python code for a user node."""
        # First generate the common node attributes
        # FlowPythonGenerator._generate_common_node_attributes(
        #     node, var_name, flow_var, schema_class_map, out, use_helpers, "field"
        # )

        params: list[str] = []

        form = safe_getattr(node.spec, "form")
        if form:
            # generate the form first
            form_name = form.name
            form_display_name = form.display_name

            # Extract cancel_button_label if present
            cancel_button_label = None
            custom_buttons = []
            if form.buttons:
                for button in form.buttons:
                    if button.name == "cancel" and button.kind == "cancel":
                        # Extract cancel button label
                        cancel_button_label = button.display_name
                    elif button.name != "submit" or button.kind != "submit":
                        # Custom button (not the default submit button)
                        custom_buttons.append(button)
            
            # Generate form() call with cancel_button_label if present
            user_node_var = var_name
            form_params = [f"name={repr(form_name)}", f"display_name={repr(form_display_name)}"]
            if cancel_button_label:
                form_params.append(f"cancel_button_label={repr(cancel_button_label)}")
            out.write(f"    # Create form node: {form_display_name}\n")
            out.write(f"    {user_node_var}: UserNode = {flow_var}.form({', '.join(form_params)})\n")
            
            # Generate add_button() calls for custom buttons
            # Note: edge_id is NOT passed to add_button() - edges are created separately using edge() function
            if custom_buttons:
                out.write("\n")
                for button in custom_buttons:
                    # Generate add_button() call - only pass display_name
                    out.write(f"    # Add custom button: {button.display_name}\n")
                    out.write(f"    {flow_var}.add_button({repr(button.display_name)})\n")
            
            # Handle form instructions if present
            if form.instructions:
                form_var = f"{user_node_var}_form"
                out.write(f"\n    # Set form instructions\n")
                out.write(f"    {form_var} = {user_node_var}.get_spec().form\n")
                out.write(f"    if {form_var}:\n")
                out.write(f"        {form_var}.instructions = {repr(form.instructions)}\n")
            
            out.write("\n")
            # Note: form.jsonSchema is auto-generated by field methods, so we skip it
            # DO NOT call set_form_schema() - the schema is built automatically when
            # you call methods like text_input_field(), single_choice_input_field(), etc.

            # Generate form fields using appropriate method calls
            for field in form.fields:
                field_name = field.name
                # Normalize field name for variable names (replace hyphens with underscores)
                normalized_field_name = normalize_identifier(field_name)
                
                # Detect which method to use
                method_name = FlowPythonGenerator._detect_form_field_method(field)
                
                if method_name == "unknown_field":
                    # Log detailed warning about unsupported field
                    field_kind = field.kind if hasattr(field, 'kind') else 'unknown'
                    field_direction = field.direction if hasattr(field, 'direction') else 'unknown'
                    ui_widget = None
                    if hasattr(field, 'uiSchema') and field.uiSchema:
                        ui_widget = safe_get(field.uiSchema, 'ui:widget')
                    out.write(f"    # Warning: Unsupported field '{field_name}' (kind={field_kind}, direction={field_direction}, ui:widget={ui_widget})\n")
                    out.write(f"    # TODO: Add support for this field type or manually implement it\n")
                    continue
                
                # Get form's jsonSchema for field lookups
                form_json_schema = None
                if hasattr(form, 'jsonSchema') and form.jsonSchema:
                    form_json_schema = form.jsonSchema
                
                # Extract parameters
                field_params = FlowPythonGenerator._extract_form_field_parameters(field, method_name, form_json_schema)
                
                # Handle input_map - generate DataMap for parameters that need it
                datamap_params = {}
                if hasattr(field, "input_map") and field.input_map is not None:
                    maps = field.input_map.spec.maps
                    if maps:
                        for map_item in maps:
                            target_var = map_item.target_variable if hasattr(map_item, "target_variable") else None
                            value_expr = map_item.value_expression if hasattr(map_item, "value_expression") else None
                            
                            if target_var and value_expr is not None:
                                # Skip display_items assignments (they map to columns parameter, not DataMap)
                                # Skip display_text assignments (they map to dropdown_item_column parameter)
                                param_name = target_var.split('.')[-1]
                                if param_name in ["display_items", "display_text"]:
                                    continue
                                
                                # Create DataMap variable name (use normalized field name)
                                datamap_var = f"{normalized_field_name}_{param_name}_map"
                                
                                # Generate DataMap code
                                if datamap_var not in datamap_params:
                                    out.write(f"    # Create DataMap for {param_name} parameter of field '{field_name}'\n")
                                    out.write(f"    {datamap_var} = DataMap()\n")
                                    datamap_params[datamap_var] = param_name
                                
                                out.write(f"    {datamap_var}.add(Assignment(")
                                out.write(f"target_variable={repr(target_var)}, ")
                                out.write(f"value_expression={repr(value_expr)}")
                                out.write(f"))\n")
                        
                        if datamap_params:
                            out.write("\n")
                
                # Add DataMap parameters to field_params
                for datamap_var, param_name in datamap_params.items():
                    field_params[param_name] = datamap_var
                
                # For user_input_field: if min_num_users or max_num_users are present, ensure multiple_users=True
                if method_name == "user_input_field":
                    if 'min_num_users' in field_params or 'max_num_users' in field_params:
                        if 'multiple_users' not in field_params:
                            field_params['multiple_users'] = True
                
                # Generate the method call
                out.write(f"    # Add form field: {field_name} (type: {method_name})\n")
                out.write(f"    {user_node_var}.{method_name}(")
                
                # Write parameters
                param_strs = []
                for param_name, param_value in field_params.items():
                    if isinstance(param_value, str) and param_value in datamap_params:
                        # It's a DataMap variable, don't quote it
                        param_strs.append(f"{param_name}={param_value}")
                    elif isinstance(param_value, bool):
                        param_strs.append(f"{param_name}={param_value}")
                    elif isinstance(param_value, (int, float)):
                        param_strs.append(f"{param_name}={param_value}")
                    else:
                        param_strs.append(f"{param_name}={repr(param_value)}")
                
                if param_strs:
                    out.write("\n        ")
                    out.write(",\n        ".join(param_strs))
                    out.write("\n    ")
                
                out.write(")\n\n")

        # Handle user node standalone fields
        fields = safe_getattr(node.spec, "fields")
        if fields:
            # there can be only 1 field
            field: UserField = fields[0]
            if field:
                # Get field name
                field_name = field.name
                
                # Handle input_map first - generate DataMap if needed
                data_map_var = None
                if hasattr(field, "input_map") and field.input_map is not None:
                    maps = field.input_map.spec.maps
                    if maps:
                        data_map_var = f"{var_name}_data_map"
                        out.write(f"    # Create DataMap for user field '{field_name}'\n")
                        out.write(f"    {data_map_var} = DataMap()\n")
                        for map_item in maps:
                            target_var = map_item.target_variable if hasattr(map_item, "target_variable") else None
                            value_expr = map_item.value_expression if hasattr(map_item, "value_expression") else None
                            
                            if target_var and value_expr is not None:
                                out.write(f"    {data_map_var}.add(Assignment(")
                                out.write(f"target_variable={repr(target_var)}, ")
                                out.write(f"value_expression={repr(value_expr)}")
                                out.write(f"))\n")
                        out.write("\n")
                
                # Now generate the field() call
                comment_name = node.spec.display_name if node.spec.display_name else var_name
                out.write(f"    # Create user field node: {comment_name}\n")
                out.write(f"    {var_name}: {node.__class__.__name__} = {flow_var}.field(\n")
                params.append(f'        direction={repr(field.direction)}')
                params.append(f'        name={repr(field_name)}')
                
                # Handle field display name
                if field.display_name is not None:
                    params.append(f'        display_name={repr(field.display_name)}')
                
                # Handle field kind
                kind_value = UserFieldKind.str_to_code(field.kind)
                params.append(f"        kind={kind_value}")
                
                # Handle text
                if field.text is not None:
                    params.append(f'        text={repr(field.text)}')
                
                # Add input_map if we generated one
                if data_map_var:
                    params.append(f"        input_map={data_map_var}")
                
                # Write all parameters
                if params:
                    out.write(",\n".join(params))
                
                out.write("\n    )\n")
        
        # generate optional properties
        FlowPythonGenerator._generate_node_field(node, var_name, fields = ["position"], schema_class_map=schema_class_map, out=out)


    @staticmethod
    def _generate_node_field(node: Node, var_name: str, fields: list[str],
                            schema_class_map: Dict[str, str], out: TextIO, declare_spec: bool = True) -> None:
        from enum import Enum
        spec_class = node.spec.__class__
        node_class = node.__class__

        # handle spec fields
        if len(fields) > 0:
            # let's check how many of these optional fields are actually set
            fields_set = [field for field in fields if safe_getattr(node.spec, field)]

            if (len(fields_set) == 0):
                return

            spec_var_name = f"{var_name}_spec"
            
            # Only declare the spec variable if requested
            if declare_spec:
                out.write(f"\n    {spec_var_name}: {spec_class.__name__} = {var_name}.get_spec()")

            for field_name in fields:
                field = safe_getattr(node.spec, field_name)
                if field:
                    out.write(f"\n    {spec_var_name}.{field_name} = ")
                    if isinstance(field, str):
                        # Use multi-line string format for strings with newlines
                        if '\n' in field:
                            # Use triple-quoted string for multi-line content
                            out.write(f'"""{field}"""')
                        else:
                            out.write(f'{repr(field)}')
                    elif isinstance(field, BaseModel):
                        out.write(f'{repr(field)}')
                        '''
                        out.write(f"{field.__class__.__name__}(")
                        for field_key, field_value in field.__dict__.items():
                            if field_value is not None:
                                if isinstance(field_value, float):
                                    out.write(f"{field_key} = {field}, ")
                                elif isinstance(field_value, str):
                                    out.write(f"{field_key} = {repr(field_value)}, ")
                                else:
                                    out.write(f"{field_key} = {field_value}, ")
                        out.write(")")
                        '''
                    elif isinstance(field, Enum):
                        # For enums, use the class name and value
                        out.write(f"{field.__class__.__name__}.{field.name}")
                    else:
                        out.write(f"{field}")

            out.write("\n")


    @staticmethod
    def _generate_script_node(node: ScriptNode, var_name: str, flow_var: str, schema_class_map: Dict[str, str],
                           out: TextIO) -> None:
        """Generate Python code for a script node."""
        # Get the script content
        script_content = safe_getattr(node.spec, "fn")
        script_var_name = f"{var_name}_script"
        
        # Generate the script variable if there's content
        if script_content:
            out.write(f"    # Script for {node.spec.name}\n")
            out.write(f"    {script_var_name} = ")
            
            # Use triple-quoted string for multi-line content
            if '\n' in script_content:
                out.write(f'"""{script_content}"""\n')
            else:
                out.write(f'{repr(script_content)}\n')
        
        # Generate the node creation with script parameter
        comment_name = node.spec.display_name if node.spec.display_name else var_name
        out.write(f"    # Create script node: {comment_name}\n")
        out.write(f"    {var_name}: {node.__class__.__name__} = {flow_var}.script(\n")
        
        params: list[str] = []
        params.append(f'        name={repr(node.spec.name)}')
        
        # Add common attributes
        display_name = safe_getattr(node.spec, "display_name")
        if display_name:
            params.append(f'        display_name={repr(display_name)}')
        
        description = safe_getattr(node.spec, "description")
        if description:
            params.append(f'        description={repr(description)}')
        
        # Handle input schema
        input_schema = safe_getattr(node.spec, "input_schema")
        if input_schema:
            input_schema_class = get_schema_class_from_ref(input_schema, schema_class_map)
            if input_schema_class:
                params.append(f'        input_schema={input_schema_class}')
        
        # Handle output schema
        output_schema = safe_getattr(node.spec, "output_schema")
        if output_schema:
            output_schema_class = get_schema_class_from_ref(output_schema, schema_class_map)
            if output_schema_class:
                params.append(f'        output_schema={output_schema_class}')
        
        # Handle private schema
        private_schema = safe_getattr(node.spec, "private_schema")
        if private_schema:
            private_schema_class = get_schema_class_from_ref(private_schema, schema_class_map)
            if private_schema_class:
                params.append(f'        private_schema={private_schema_class}')
        
        # Add the script parameter
        if script_content:
            params.append(f'        script={script_var_name}')
        
        out.write(",\n".join(params))
        out.write("\n    )\n")
        
        # Generate datamap assignment
        FlowPythonGenerator._generate_datamap_assignment(node, var_name, schema_class_map, out)
        
        # Handle position field separately if it exists
        position = safe_getattr(node.spec, "position")
        if position:
            spec_var_name = f"{var_name}_spec"
            out.write(f"\n    {spec_var_name}: {node.spec.__class__.__name__} = {var_name}.get_spec()")
            out.write(f"\n    {spec_var_name}.position = ")
            if isinstance(position, BaseModel):
                out.write(f'{repr(position)}')
            else:
                out.write(f"{position}")
            out.write("\n")

    @staticmethod
    def _generate_docproc_node(node: DocProcNode, var_name: str, flow_var: str, schema_class_map: Dict[str, str],
                              out: TextIO) -> None:
        """Generate Python code for a DocProc node in the original ADK style."""
        from ibm_watsonx_orchestrate.flow_builder.types import DocProcField, DocProcKVPSchema, DocProcOutputFormat
        
        # Generate the node creation with minimal parameters
        comment_name = node.spec.display_name if node.spec.display_name else var_name
        out.write(f"    # Create document processing node: {comment_name}\n")
        out.write(f"    {var_name}: DocProcNode = {flow_var}.docproc(\n")
        out.write(f"        name={repr(node.spec.name)}")
        
        # Add task parameter as a string
        if hasattr(node.spec, 'task') and node.spec.task:
            task_value = node.spec.task
            if hasattr(task_value, 'value'):
                task_value = task_value.value
            out.write(f",\n        task={repr(task_value)}")
        
        # Add document_structure if True
        if hasattr(node.spec, 'document_structure') and node.spec.document_structure:
            out.write(f",\n        document_structure={node.spec.document_structure}")
        
        # Add enable_hw if True
        if hasattr(node.spec, 'enable_hw') and node.spec.enable_hw:
            out.write(f",\n        enable_hw={node.spec.enable_hw}")
        
        # Add output_format as enum reference
        if hasattr(node.spec, 'output_format') and node.spec.output_format:
            output_format = node.spec.output_format
            if hasattr(output_format, 'value'):
                # It's an enum, use the enum reference
                out.write(f",\n        output_format=DocProcOutputFormat.{output_format.name}")
            else:
                out.write(f",\n        output_format={repr(output_format)}")
        
        # Add kvp_schemas - generate as a constant reference
        if hasattr(node.spec, 'kvp_schemas') and node.spec.kvp_schemas:
            kvp_schemas = node.spec.kvp_schemas
            if isinstance(kvp_schemas, list) and len(kvp_schemas) > 0:
                # Generate a constant name based on the node name
                schema_const_name = f"{var_name.upper()}_KVP_SCHEMA"
                
                # We'll generate the constant before the flow function
                # Store it for later generation
                if not hasattr(FlowPythonGenerator, "_kvp_schema_constants"):
                    FlowPythonGenerator._kvp_schema_constants = []
                
                schema_def = f"\n# Define KVP Schema for {node.spec.name}\n"
                schema_def += f"{schema_const_name} = DocProcKVPSchema(\n"
                
                kvp_schema = kvp_schemas[0]
                if hasattr(kvp_schema, 'document_type'):
                    schema_def += f'    document_type={repr(kvp_schema.document_type)},\n'
                if hasattr(kvp_schema, 'document_description'):
                    schema_def += f'    document_description={repr(kvp_schema.document_description)},\n'
                if hasattr(kvp_schema, 'additional_prompt_instructions'):
                    schema_def += f'    additional_prompt_instructions={repr(kvp_schema.additional_prompt_instructions)},\n'
                
                # Add fields
                if hasattr(kvp_schema, 'fields') and kvp_schema.fields:
                    schema_def += '    fields={\n'
                    for field_name, field_value in kvp_schema.fields.items():
                        schema_def += f'        {repr(field_name)}: DocProcField(\n'
                        if hasattr(field_value, 'description'):
                            schema_def += f'            description={repr(field_value.description)},\n'
                        if hasattr(field_value, 'default'):
                            schema_def += f'            default={repr(field_value.default)},\n'
                        if hasattr(field_value, 'example'):
                            schema_def += f'            example={repr(field_value.example)},\n'
                        schema_def += '        ),\n'
                    schema_def += '    }\n'
                
                schema_def += ')\n'
                
                FlowPythonGenerator._kvp_schema_constants.append(schema_def)
                
                out.write(f",\n        kvp_schemas=[{schema_const_name}]")
        
        # Add kvp_force_schema_name if present
        if hasattr(node.spec, 'kvp_force_schema_name') and node.spec.kvp_force_schema_name:
            out.write(f",\n        kvp_force_schema_name={repr(node.spec.kvp_force_schema_name)}")
        
        out.write("\n    )\n")
        
        # Generate input mappings using map_input
        FlowPythonGenerator._generate_datamap_assignment(node, var_name, schema_class_map, out)
        
        out.write("\n    \n")

    @staticmethod
    def _generate_any_node(node: Node, var_name: str, flow_var: str, schema_class_map: Dict[str, str],
                           out: TextIO):
        """Generate Python code for any node."""
        optional_fields: list[str] = []
        mandatory_fields: list[str] = []
        match node.__class__.__name__:
            case "ScriptNode":
                func_name = "script"
                optional_fields = ['position', 'fn']
            case "PromptNode":
                func_name = "prompt"
                mandatory_fields = ['system_prompt', "user_prompt"]
                optional_fields = ['position', "prompt_examples", "llm", "llm_parameters", "error_handler_config", "metadata", "test_input_data"]
            case "DecisionsNode":
                func_name = "decisions"
                optional_fields = ['position', 'rules', 'default_actions', 'locale']
            case "TimerNode":
                func_name = "timer"
                mandatory_fields = ['delay']
                optional_fields = ['position']
            case "StartNode":
                func_name = "start"
                optional_fields = ["position"]
            case "EndNode":
                func_name = "end"
                optional_fields = ["position"]
            case "Branch":
                func_name = "branch"
                optional_fields = ['position', 'match_policy']
            case "Loop":
                func_name = "loop"
                mandatory_fields = ["evaluator"]
                optional_fields = ['position', 'dimensions', 'evaluator']
            case "Foreach":
                func_name = "foreach"
                mandatory_fields = ["item_schema"]
                optional_fields = ['position', 'dimensions', 'foreach_policy']
            case "ToolNode":
                func_name = "tool"
                mandatory_fields = ["tool"]
                optional_fields = ['position']
            case "AgentNode":
                func_name = "agent"
                mandatory_fields = ["agent"]
                optional_fields = ['position']
            case "DocProcNode":
                func_name = "docproc"
                mandatory_fields = []
                optional_fields = ['position']
            case "DocExtNode":
                func_name = "docext"
                mandatory_fields = ["config"]
                optional_fields = ['position']
            case "DocClassifierNode":
                func_name = "docclassifier"
                mandatory_fields = ["config"]
                optional_fields = ['position']
            case _:
                raise ValueError(f"TODO: python conversion not available for node type: {node.__class__.__name__}")


        # First generate the common node attributes
        FlowPythonGenerator._generate_common_node_attributes(
            node, var_name, flow_var, schema_class_map, out, include_creation=True, func_name=func_name,
            mandatory_fields=mandatory_fields
        )

        FlowPythonGenerator._generate_node_field(node = node, var_name = var_name, fields = optional_fields,
                    schema_class_map = schema_class_map, out = out)
        out.write("\n    \n")

    @staticmethod
    def _generate_edges(edges: List[Any], node_vars: Dict[str, str], flow_var: str,
                       out: TextIO, nodes: Optional[Dict[str, Any]] = None,
                       handled_edges: Optional[set] = None) -> None:
        """
        Generate code for edges between nodes.
        
        Args:
            edges: List of edges in the flow
            node_vars: Dictionary mapping node IDs to variable names
            flow_var: Variable name for the flow
            out: Output stream to write the generated code
            nodes: Dictionary of nodes in the flow (used to identify branch nodes)
            handled_edges: Set of edge IDs that were already handled by branch conditions
        """
        if not edges:
            out.write(f"    # No edges defined in the flow\n")
            return
        
        if handled_edges is None:
            handled_edges = set()
        
        # Generate code for each edge
        for edge in edges:
            try:
                # Check if this edge was already handled by a branch condition
                edge_id = None
                if hasattr(edge, "id"):
                    edge_id = edge.id
                elif isinstance(edge, dict):
                    edge_id = edge.get("id")
                
                if edge_id and edge_id in handled_edges:
                    # Skip this edge as it's handled by a branch condition
                    continue
                
                # Handle both dictionary and FlowEdge objects
                if hasattr(edge, "start") and hasattr(edge, "end"):
                    start = edge.start
                    end = edge.end
                elif isinstance(edge, dict):
                    start = edge.get("start") or edge.get("source_id")
                    end = edge.get("end") or edge.get("target_id")
                else:
                    out.write(f"    # Warning: Skipping edge with unknown format: {edge}\n")
                    continue
                    
                if not start or not end:
                    out.write(f"    # Warning: Edge missing start or end node\n")
                    continue
                
                # Normalize node IDs to match the keys in node_vars (hyphens -> underscores)
                start_normalized = normalize_identifier(start) if isinstance(start, str) else start
                end_normalized = normalize_identifier(end) if isinstance(end, str) else end
                
                start_ref = node_vars.get(start_normalized, node_vars.get(start, f'"{start}"'))
                end_ref = node_vars.get(end_normalized, node_vars.get(end, f'"{end}"'))

                # Special handling for START and END
                if (start_ref.endswith(START)):
                    start_ref = "START"
                if (end_ref.endswith(END)):
                    end_ref = "END"
                
                # Generate edge connection (id is omitted as it will be auto-generated during flow import)
                out.write(f"    # Connect: {start_ref} -> {end_ref}\n")
                out.write(f"    {flow_var}.edge({start_ref}, {end_ref})\n")
            except Exception as e:
                out.write(f"    # Error processing edge: {str(e)}\n")


def generate_flow_decorator(flow_spec: Any, schema_class_map: Dict[str, str], out: TextIO) -> None:
    """Generate the flow decorator."""
    out.write("@flow(\n")
    out.write(f'    name={repr(flow_spec.name)},\n')
    
    if flow_spec.display_name and flow_spec.display_name != flow_spec.name:
        out.write(f'    display_name={repr(flow_spec.display_name)},\n')
    
    if flow_spec.description:
        out.write(f'    description={repr(flow_spec.description)},\n')
    
    # Handle input schema - use DocProcInput for docproc flows
    if hasattr(flow_spec, "input_schema") and flow_spec.input_schema:
        if hasattr(flow_spec.input_schema, "ref"):
            schema_ref = flow_spec.input_schema.ref
            if schema_ref.startswith("#/schemas/"):
                schema_name = schema_ref[len("#/schemas/"):]
                # Check if this is a DocProc input schema
                if "docproc" in schema_name.lower():
                    # Use DocProcInput for docproc flows
                    out.write(f"    input_schema=DocProcInput,\n")
                elif schema_name in schema_class_map:
                    out.write(f"    input_schema={schema_class_map[schema_name]},\n")
    
    # Handle output schema
    if hasattr(flow_spec, "output_schema") and flow_spec.output_schema:
        if hasattr(flow_spec.output_schema, "ref"):
            schema_ref = flow_spec.output_schema.ref
            if schema_ref.startswith("#/schemas/"):
                schema_name = schema_ref[len("#/schemas/"):]
                if schema_name in schema_class_map:
                    out.write(f"    output_schema={schema_class_map[schema_name]},\n")
    
    # Handle private schema
    if hasattr(flow_spec, "private_schema") and flow_spec.private_schema:
        if hasattr(flow_spec.private_schema, "ref"):
            schema_ref = flow_spec.private_schema.ref
            if schema_ref.startswith("#/schemas/"):
                schema_name = schema_ref[len("#/schemas/"):]
                if schema_name in schema_class_map:
                    out.write(f"    private_schema={schema_class_map[schema_name]},\n")

    # Handle schedulable
    if hasattr(flow_spec, "schedulable") and flow_spec.schedulable:
        out.write(f"    schedulable={str(flow_spec.schedulable).lower()},\n")
    
    out.write(")\n")


def generate_function_signature(flow_spec: Any, out: TextIO) -> None:
    """Generate the flow function signature."""
    function_name = f"build_{flow_spec.name}_flow"
    out.write(f"def {function_name}(aflow: Flow | None = None) -> Flow:\n")
    
    # Add docstring
    if flow_spec.description:
        out.write(f'    """\n')
        out.write(f'    {flow_spec.description}\n')
        out.write(f'    """\n')
    else:
        out.write(f'    """\n')
        out.write(f'    Build the {flow_spec.name} flow\n')
        out.write(f'    """\n')
    
    # Add validation check for aflow parameter
    out.write(f'    if aflow is None:\n')
    out.write(f'        raise ValueError("aflow parameter cannot be None")\n')

def generate_flow_py_code(flow: Flow, schema_class_map: Dict[str, str], out: TextIO) -> None:
    """
    Generate Python code for a Flow object.
    
    Args:
        flow: The Flow object to generate code for
        schema_class_map: Dictionary mapping schema names to class names
        out: Output stream to write the generated code
    """

    # Reset the KVP schema constants list
    if hasattr(FlowPythonGenerator, "_kvp_schema_constants"):
        delattr(FlowPythonGenerator, "_kvp_schema_constants")
    FlowPythonGenerator._kvp_schema_constants = []
    
    # Reset the user flow functions list
    if hasattr(FlowPythonGenerator, "_user_flow_functions"):
        delattr(FlowPythonGenerator, "_user_flow_functions")
    FlowPythonGenerator._user_flow_functions = []
    
    # First pass: collect variable names and detect collisions
    var_name_counts: Dict[str, Any] = {}
    for node_id, node in flow.nodes.items():
        if node_id not in ["__start__", "__end__"]:
            # Pre-generate variable names to detect collisions
            get_meaningful_variable_name(node, node_id, var_name_counts)
    
    # Second pass: collect user flow functions
    for node_id, node in flow.nodes.items():
        FlowPythonGenerator.to_py(node, "aflow", schema_class_map, None, var_name_counts)
        #if node_id not in ["__start__", "__end__"]:
        #    # This will populate FlowPythonGenerator._user_flow_functions
        #    FlowPythonGenerator.to_py(node, "aflow", schema_class_map, None, var_name_counts)
    
    # Write KVP schema constants before the flow decorator
    if hasattr(FlowPythonGenerator, "_kvp_schema_constants") and FlowPythonGenerator._kvp_schema_constants:
        for const_def in FlowPythonGenerator._kvp_schema_constants:
            out.write(const_def)
        out.write("\n")
    
    # Generate the function signature
    generate_flow_decorator(flow.spec, schema_class_map, out)
    generate_function_signature(flow.spec, out)
    
    # Create a buffer for the main flow content
    main_flow_buffer = StringIO()
    
    # Use the common flow attributes generator to handle nodes and edges
    FlowPythonGenerator._generate_flow_attributes(flow, "aflow", schema_class_map, main_flow_buffer, var_name_counts)
        
    # Then write the main flow function content
    out.write(main_flow_buffer.getvalue())
    
    # Generate return statement
    out.write("    return aflow\n")

    # Write user flow function definitions at the top level after the main flow definition
    if hasattr(FlowPythonGenerator, "_user_flow_functions") and FlowPythonGenerator._user_flow_functions:
        for func_def in FlowPythonGenerator._user_flow_functions:
            out.write(func_def)
            out.write("\n")


# Made with Bob
