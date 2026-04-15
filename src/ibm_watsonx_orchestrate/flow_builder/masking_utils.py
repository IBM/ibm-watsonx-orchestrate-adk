"""
Utility classes and functions for property masking in flow schemas.

This module provides functionality to mark properties as sensitive/confidential
by adding IBM-specific masking extensions to JSON schemas.
"""

import re
from enum import Enum
from typing import List, Tuple, Union, Optional
from ibm_watsonx_orchestrate.agent_builder.tools.types import (
    JsonSchemaObject, ToolRequestBody, ToolResponseBody
)
from ibm_watsonx_orchestrate.flow_builder.types import SchemaRef, JsonSchemaObjectRef


class MaskingPolicy(str, Enum):
    """
    Enum for valid masking policies.
    
    Attributes:
        MASK_ALL: Mask the entire value
        MASK_LAST4: Mask the last 4 characters
        MASK_FIRST4: Mask the first 4 characters
        MASK_VIA_REGEX: Mask using a regex pattern
    """
    MASK_ALL = "mask-all"
    MASK_LAST4 = "mask-last4"
    MASK_FIRST4 = "mask-first4"
    MASK_VIA_REGEX = "mask-via-regex"


class InputPolicy(str, Enum):
    """
    Enum for valid input masking policies.
    
    Attributes:
        MASK_WHILE_TYPING: Mask the input while the user is typing
    """
    MASK_WHILE_TYPING = "mask-while-typing"


class PropertyMaskingHelper:
    """
    Helper class for parsing property paths and applying masking to schemas.
    
    This class provides utilities to:
    - Parse dot-notation property paths (e.g., "flow.input.property_name")
    - Navigate through nested schemas and flows
    - Apply IBM masking extensions to properties
    """
    
    @staticmethod
    def _parse_bracket_content(path: str, start_index: int) -> Tuple[str, int]:
        """
        Parse bracketed quoted content starting just after the opening '['.

        Returns:
            Tuple of (parsed_content, next_index_after_closing_bracket)
        """
        i = start_index
        if i >= len(path):
            raise ValueError(f"Unclosed bracket in path: {path}")

        if path[i] not in ['"', "'"]:
            raise ValueError(
                f"Bracket notation must use quotes: {path}. "
                f"Expected '\"' or \"'\" after '[' at position {i}"
            )

        quote_char = path[i]
        i += 1
        bracket_content = ""

        while i < len(path) and path[i] != quote_char:
            if path[i] == '\\' and i + 1 < len(path):
                i += 1
                bracket_content += path[i]
            else:
                bracket_content += path[i]
            i += 1

        if i >= len(path):
            raise ValueError(f"Unclosed quote in bracket notation: {path}")

        i += 1

        if i >= len(path) or path[i] != ']':
            raise ValueError(
                f"Expected ']' after closing quote in bracket notation: {path} at position {i}"
            )

        return bracket_content, i + 1

    @staticmethod
    def _tokenize_path(path: str) -> List[str]:
        """
        Tokenize a path string into parts, handling both dot notation and bracket notation.
        
        Supports:
        - Dot notation: flow.node.output.property
        - Bracket notation: flow["node name"].output.property
        - Mixed: flow["node 1"].subnode.output.property
        
        Args:
            path: Path string to tokenize
        
        Returns:
            List of path components
        
        Raises:
            ValueError: If path has invalid syntax (unclosed brackets, etc.)
        
        Examples:
            "flow.input.user" -> ["flow", "input", "user"]
            'flow["User Activity"].output' -> ["flow", "User Activity", "output"]
            'flow["a"]["b"].c' -> ["flow", "a", "b", "c"]
        """
        if not isinstance(path, str) or not path.strip():
            raise ValueError("Path must be a non-empty string")

        tokens = []
        i = 0
        current_token = ""
        
        while i < len(path):
            char = path[i]
            
            if char == '[':
                # Save any accumulated token from dot notation
                if current_token:
                    tokens.append(current_token)
                    current_token = ""

                bracket_content, i = PropertyMaskingHelper._parse_bracket_content(path, i + 1)
                tokens.append(bracket_content)
                
            elif char == '.':
                # End of current token
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
                i += 1
                
            else:
                # Regular character - add to current token
                current_token += char
                i += 1
        
        # Add any remaining token
        if current_token:
            tokens.append(current_token)
        
        return tokens
    
    @staticmethod
    def _validate_path_tokens(path: str, parts: List[str]) -> None:
        """
        Validate the top-level structure of a parsed property path.
        """
        if len(parts) < 3 or parts[0] != 'flow':
            raise ValueError(
                f"Invalid path '{path}'. Must start with 'flow.' or 'flow[' and have at least 3 parts"
            )

    @staticmethod
    def _split_node_path_and_property_chain(parts: List[str]) -> Tuple[List[str], List[str]]:
        """
        Split parsed path parts into node path and property chain using a single pass.

        Preserves current behavior by treating the first occurrence of 'output'
        after 'flow' as the delimiter.
        """
        node_path = []
        property_chain = []
        found_output = False

        for part in parts[1:]:
            if not found_output and part == 'output':
                found_output = True
                continue
            if found_output:
                property_chain.append(part)
            else:
                node_path.append(part)

        return node_path, property_chain

    @staticmethod
    def parse_property_path(path: str) -> dict:
        """
        Parse property path into components, handling nested flows and node names with spaces.
        
        Supports two syntaxes:
        1. Dot notation for simple names: flow.node_name.output.property
        2. Bracket notation for names with spaces/special chars: flow["Node Name"].output.property
        
        The '.output' part is optional for node paths - if omitted, the entire node schema is targeted.
        
        Examples:
            "flow.input.user_id" -> {
                'scope': 'input',
                'node_path': [],
                'property_chain': ['user_id']
            }
            
            "flow.triage_agent.output.steps_taken" -> {
                'scope': 'node',
                'node_path': ['triage_agent'],
                'property_chain': ['steps_taken']
            }
            
            "flow.userflow_1.last_name" -> {
                'scope': 'node',
                'node_path': ['userflow_1', 'last_name'],
                'property_chain': []  # Empty means get schema for the node itself
            }
            
            'flow["User Activity 1"].output.result' -> {
                'scope': 'node',
                'node_path': ['User Activity 1'],
                'property_chain': ['result']
            }
            
            'flow["User Activity 1"].result' -> {
                'scope': 'node',
                'node_path': ['User Activity 1', 'result'],
                'property_chain': []  # Empty means get schema for the node itself
            }
            
            'flow["nested flow"]["inner node"].output.value' -> {
                'scope': 'node',
                'node_path': ['nested flow', 'inner node'],
                'property_chain': ['value']
            }
        
        Args:
            path: Path to property using dot notation and/or bracket notation
        
        Returns:
            Dictionary with 'scope', 'node_path', and 'property_chain'
        
        Raises:
            ValueError: If path format is invalid
        """
        # Parse the path into tokens, handling both dot notation and bracket notation
        parts = PropertyMaskingHelper._tokenize_path(path)
        PropertyMaskingHelper._validate_path_tokens(path, parts)

        second_part = parts[1]

        # Check if it's a direct flow schema (input/output/private)
        if second_part in ['input', 'output', 'private']:
            return {
                'scope': second_part,
                'node_path': [],
                'property_chain': parts[2:]  # Everything after flow.input/output/private
            }

        # Otherwise, it's a node path - need to split where 'output' first appears.
        # The pattern is: flow.node1.node2...nodeN.output.property1.property2...
        # OR: flow.node1.node2...nodeN (output is optional, property_chain will be empty)
        node_path, property_chain = PropertyMaskingHelper._split_node_path_and_property_chain(parts)
        
        if not node_path:
            raise ValueError(
                f"Invalid path '{path}'. Must specify at least one node name"
            )
        
        # Note: property_chain can be empty for primitive outputs (e.g., flow.node.output)
        # In this case, we'll mask the output schema itself rather than a property within it
        
        return {
            'scope': 'node',
            'node_path': node_path,
            'property_chain': property_chain
        }
    
    @staticmethod
    def _validate_maskable_string_schema(
        property_schema: Union[JsonSchemaObject, ToolResponseBody, ToolRequestBody]
    ) -> None:
        """
        Validate that the target schema is a string schema and therefore maskable.
        """
        if not hasattr(property_schema, 'type') or property_schema.type != 'string':
            property_type = getattr(property_schema, 'type', 'unknown')
            raise ValueError(
                f"Only string properties can be masked. "
                f"Property type is '{property_type}'. "
                f"Arrays, objects, numbers, and booleans cannot be masked."
            )

    @staticmethod
    def _validate_regex_config(regex_config: Optional[dict]) -> dict:
        """
        Validate regex configuration for the mask-via-regex policy.
        """
        if not regex_config:
            raise ValueError(
                "regex_config is required when using 'mask-via-regex' policy. "
                "Must include 'text-pattern' and 'masking-pattern'."
            )

        if "text-pattern" not in regex_config or "masking-pattern" not in regex_config:
            raise ValueError(
                "regex_config must include both 'text-pattern' and 'masking-pattern'"
            )

        text_pattern = regex_config["text-pattern"]
        masking_pattern = regex_config["masking-pattern"]

        if not isinstance(text_pattern, str) or not isinstance(masking_pattern, str):
            raise ValueError(
                "regex_config values for 'text-pattern' and 'masking-pattern' must be strings"
            )

        try:
            re.compile(text_pattern)
            re.compile(masking_pattern)
        except re.error as exc:
            raise ValueError(f"Invalid regex pattern in regex_config: {exc}") from exc

        return regex_config

    @staticmethod
    def apply_masking_extensions(
        property_schema: Union[JsonSchemaObject, ToolResponseBody, ToolRequestBody],
        masking_policy: MaskingPolicy,
        regex_config: Optional[dict] = None,
        input_policy: Optional[InputPolicy] = None
    ) -> None:
        """
        Apply IBM masking extensions to a property schema.
        
        Only string/text type properties can be masked. Arrays and objects cannot be masked.
        
        Modifies the schema in-place by adding:
        - x-ibm-is-sensitive: true
        - x-ibm-masking-policy: <masking_policy>
        - x-ibm-masking-regex-config: <regex_config> (if policy is mask-via-regex)
        - x-ibm-masking-input-policy: <input_policy> (optional)
        
        Args:
            property_schema: The schema to modify (JsonSchemaObject, ToolResponseBody, or ToolRequestBody)
            masking_policy: The masking policy to apply
            regex_config: Regex configuration for mask-via-regex policy (optional)
            input_policy: Input masking behavior (optional)
        
        Raises:
            ValueError: If property is not a string type
        """
        PropertyMaskingHelper._validate_maskable_string_schema(property_schema)

        validated_regex_config = None
        if masking_policy == MaskingPolicy.MASK_VIA_REGEX:
            validated_regex_config = PropertyMaskingHelper._validate_regex_config(regex_config)

        # Build the complete extra fields dictionary
        extra_fields = {}
        if hasattr(property_schema, '__pydantic_extra__') and property_schema.__pydantic_extra__:
            extra_fields = dict(property_schema.__pydantic_extra__)
        
        extra_fields["x-ibm-is-sensitive"] = True
        extra_fields["x-ibm-masking-policy"] = masking_policy.value

        if validated_regex_config is not None:
            extra_fields["x-ibm-masking-regex-config"] = validated_regex_config

        if input_policy:
            extra_fields["x-ibm-masking-input-policy"] = input_policy.value
        
        # Assign the complete dictionary at once
        property_schema.__pydantic_extra__ = extra_fields
