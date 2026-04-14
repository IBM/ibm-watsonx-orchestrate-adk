import pytest

from ibm_watsonx_orchestrate.agent_builder.tools.types import JsonSchemaObject
from ibm_watsonx_orchestrate.flow_builder.masking_utils import (
    InputPolicy,
    MaskingPolicy,
    PropertyMaskingHelper,
)

def _make_schema(schema_data: dict) -> JsonSchemaObject:
    return JsonSchemaObject.model_validate(schema_data)

def test_tokenize_path_supports_dot_and_bracket_notation():
    tokens = PropertyMaskingHelper._tokenize_path('flow["User Activity"].output.result')

    assert tokens == ["flow", "User Activity", "output", "result"]

def test_tokenize_path_supports_escaped_characters_in_brackets():
    tokens = PropertyMaskingHelper._tokenize_path(r'flow["User \"Alias\""].output.value')

    assert tokens == ["flow", 'User "Alias"', "output", "value"]


def test_tokenize_path_rejects_empty_input():
    with pytest.raises(ValueError, match="Path must be a non-empty string"):
        PropertyMaskingHelper._tokenize_path("   ")

def test_parse_property_path_for_input_scope():
    parsed = PropertyMaskingHelper.parse_property_path("flow.input.user_id")

    assert parsed == {
        "scope": "input",
        "node_path": [],
        "property_chain": ["user_id"],
    }

def test_parse_property_path_for_node_output_scope():
    parsed = PropertyMaskingHelper.parse_property_path('flow["User Activity"].output.result')

    assert parsed == {
        "scope": "node",
        "node_path": ["User Activity"],
        "property_chain": ["result"],
    }


def test_parse_property_path_without_explicit_output_treats_remaining_parts_as_node_path():
    parsed = PropertyMaskingHelper.parse_property_path("flow.userflow_1.last_name")

    assert parsed == {
        "scope": "node",
        "node_path": ["userflow_1", "last_name"],
        "property_chain": [],
    }


def test_apply_masking_extensions_writes_enum_values_to_model_extra():
    schema = _make_schema({"type": "string", "title": "secret", "in": "body"})

    PropertyMaskingHelper.apply_masking_extensions(
        schema,
        masking_policy=MaskingPolicy.MASK_ALL,
        input_policy=InputPolicy.MASK_WHILE_TYPING,
    )

    extra = schema.model_extra or {}

    assert extra["x-ibm-is-sensitive"] is True
    assert extra["x-ibm-masking-policy"] == MaskingPolicy.MASK_ALL.value
    assert extra["x-ibm-masking-input-policy"] == InputPolicy.MASK_WHILE_TYPING.value


def test_apply_masking_extensions_rejects_non_string_schema():
    schema = _make_schema({"type": "object", "title": "payload", "properties": {}, "in": "body"})

    with pytest.raises(ValueError, match="Only string properties can be masked"):
        PropertyMaskingHelper.apply_masking_extensions(
            schema,
            masking_policy=MaskingPolicy.MASK_ALL,
        )


def test_apply_masking_extensions_requires_regex_config_for_regex_policy():
    schema = _make_schema({"type": "string", "title": "card_number", "in": "body"})

    with pytest.raises(ValueError, match="regex_config is required"):
        PropertyMaskingHelper.apply_masking_extensions(
            schema,
            masking_policy=MaskingPolicy.MASK_VIA_REGEX,
        )


def test_apply_masking_extensions_rejects_invalid_regex_patterns():
    schema = _make_schema({"type": "string", "title": "card_number", "in": "body"})

    with pytest.raises(ValueError, match="Invalid regex pattern in regex_config"):
        PropertyMaskingHelper.apply_masking_extensions(
            schema,
            masking_policy=MaskingPolicy.MASK_VIA_REGEX,
            regex_config={
                "text-pattern": "(",
                "masking-pattern": "XXXX",
            },
        )