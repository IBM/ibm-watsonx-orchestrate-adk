"""
Tests for dereference_refs and create_schema_from_function inlined in utils.py.
dereference_refs tests ported from:
https://github.com/langchain-ai/langchain/blob/master/libs/core/tests/unit_tests/utils/test_json_schema.py
"""
from typing import Optional

import pytest
from pydantic import BaseModel

from ibm_watsonx_orchestrate.agent_builder.tools.utils import (
    create_schema_from_function,
    dereference_refs,
)


# ---------------------------------------------------------------------------
# dereference_refs
# ---------------------------------------------------------------------------

def test_dereference_refs_no_refs() -> None:
    schema = {
        "type": "object",
        "properties": {
            "first_name": {"type": "string"},
        },
    }
    assert dereference_refs(schema) == schema


def test_dereference_refs_one_ref() -> None:
    schema = {
        "type": "object",
        "properties": {"first_name": {"$ref": "#/$defs/name"}},
        "$defs": {"name": {"type": "string"}},
    }
    expected = {
        "type": "object",
        "properties": {"first_name": {"type": "string"}},
        "$defs": {"name": {"type": "string"}},
    }
    assert dereference_refs(schema) == expected


def test_dereference_refs_multiple_refs() -> None:
    schema = {
        "type": "object",
        "properties": {
            "first_name": {"$ref": "#/$defs/name"},
            "other": {"$ref": "#/$defs/other"},
        },
        "$defs": {
            "name": {"type": "string"},
            "other": {"type": "object", "properties": {"age": "int", "height": "int"}},
        },
    }
    expected = {
        "type": "object",
        "properties": {
            "first_name": {"type": "string"},
            "other": {"type": "object", "properties": {"age": "int", "height": "int"}},
        },
        "$defs": {
            "name": {"type": "string"},
            "other": {"type": "object", "properties": {"age": "int", "height": "int"}},
        },
    }
    assert dereference_refs(schema) == expected


def test_dereference_refs_nested_refs_skip() -> None:
    schema = {
        "type": "object",
        "properties": {"info": {"$ref": "#/$defs/info"}},
        "$defs": {
            "name": {"type": "string"},
            "info": {
                "type": "object",
                "properties": {"age": "int", "name": {"$ref": "#/$defs/name"}},
            },
        },
    }
    expected = {
        "type": "object",
        "properties": {
            "info": {
                "type": "object",
                "properties": {"age": "int", "name": {"type": "string"}},
            },
        },
        "$defs": {
            "name": {"type": "string"},
            "info": {
                "type": "object",
                "properties": {"age": "int", "name": {"$ref": "#/$defs/name"}},
            },
        },
    }
    assert dereference_refs(schema) == expected


def test_dereference_refs_nested_refs_no_skip() -> None:
    schema = {
        "type": "object",
        "properties": {"info": {"$ref": "#/$defs/info"}},
        "$defs": {
            "name": {"type": "string"},
            "info": {
                "type": "object",
                "properties": {"age": "int", "name": {"$ref": "#/$defs/name"}},
            },
        },
    }
    expected = {
        "type": "object",
        "properties": {
            "info": {
                "type": "object",
                "properties": {"age": "int", "name": {"type": "string"}},
            },
        },
        "$defs": {
            "name": {"type": "string"},
            "info": {
                "type": "object",
                "properties": {"age": "int", "name": {"type": "string"}},
            },
        },
    }
    assert dereference_refs(schema, skip_keys=()) == expected


def test_dereference_refs_missing_ref() -> None:
    schema = {
        "type": "object",
        "properties": {"first_name": {"$ref": "#/$defs/name"}},
        "$defs": {},
    }
    with pytest.raises(KeyError):
        dereference_refs(schema)


def test_dereference_refs_remote_ref() -> None:
    schema = {
        "type": "object",
        "properties": {"first_name": {"$ref": "https://somewhere/else/name"}},
    }
    with pytest.raises(ValueError, match="ref paths are expected to be URI fragments"):
        dereference_refs(schema)


def test_dereference_refs_cyclical_refs() -> None:
    schema = {
        "type": "object",
        "properties": {
            "user": {"$ref": "#/$defs/user"},
            "customer": {"$ref": "#/$defs/user"},
        },
        "$defs": {
            "user": {
                "type": "object",
                "properties": {
                    "friends": {"type": "array", "items": {"$ref": "#/$defs/user"}}
                },
            }
        },
    }
    expected = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {"friends": {"type": "array", "items": {}}},
            },
            "customer": {
                "type": "object",
                "properties": {"friends": {"type": "array", "items": {}}},
            },
        },
        "$defs": {
            "user": {
                "type": "object",
                "properties": {
                    "friends": {"type": "array", "items": {"$ref": "#/$defs/user"}}
                },
            }
        },
    }
    assert dereference_refs(schema) == expected


def test_dereference_refs_mixed_ref_with_properties() -> None:
    schema = {
        "type": "object",
        "properties": {
            "data": {
                "$ref": "#/$defs/BaseType",
                "description": "Additional description",
                "example": "some example",
            }
        },
        "$defs": {"BaseType": {"type": "string", "minLength": 1}},
    }
    expected = {
        "type": "object",
        "properties": {
            "data": {
                "type": "string",
                "minLength": 1,
                "description": "Additional description",
                "example": "some example",
            }
        },
        "$defs": {"BaseType": {"type": "string", "minLength": 1}},
    }
    assert dereference_refs(schema) == expected


def test_dereference_refs_mixed_ref_overrides_property() -> None:
    schema = {
        "type": "object",
        "properties": {
            "data": {
                "$ref": "#/$defs/Base",
                "type": "number",
                "description": "Overridden description",
            }
        },
        "$defs": {"Base": {"type": "string", "description": "Original description"}},
    }
    expected = {
        "type": "object",
        "properties": {
            "data": {"type": "number", "description": "Overridden description"}
        },
        "$defs": {"Base": {"type": "string", "description": "Original description"}},
    }
    assert dereference_refs(schema) == expected


def test_dereference_refs_nested_mixed_refs() -> None:
    schema = {
        "type": "object",
        "properties": {
            "outer": {
                "type": "object",
                "properties": {
                    "inner": {"$ref": "#/$defs/Base", "title": "Custom Title"}
                },
            }
        },
        "$defs": {"Base": {"type": "string", "minLength": 1}},
    }
    expected = {
        "type": "object",
        "properties": {
            "outer": {
                "type": "object",
                "properties": {
                    "inner": {"type": "string", "minLength": 1, "title": "Custom Title"}
                },
            }
        },
        "$defs": {"Base": {"type": "string", "minLength": 1}},
    }
    assert dereference_refs(schema) == expected


def test_dereference_refs_array_with_mixed_refs() -> None:
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {"$ref": "#/$defs/Item", "description": "An item"},
            }
        },
        "$defs": {"Item": {"type": "string", "enum": ["a", "b", "c"]}},
    }
    expected = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["a", "b", "c"],
                    "description": "An item",
                },
            }
        },
        "$defs": {"Item": {"type": "string", "enum": ["a", "b", "c"]}},
    }
    assert dereference_refs(schema) == expected


# ---------------------------------------------------------------------------
# create_schema_from_function
# ---------------------------------------------------------------------------

def test_create_schema_simple_types() -> None:
    def fn(name: str, count: int = 5) -> str:
        return name

    model = create_schema_from_function("fn", fn)
    schema = model.model_json_schema()
    assert schema["properties"]["name"]["type"] == "string"
    assert schema["properties"]["count"]["type"] == "integer"
    assert schema["properties"]["count"]["default"] == 5
    assert "name" in schema["required"]
    assert "count" not in schema.get("required", [])


def test_create_schema_optional_arg() -> None:
    def fn(name: str, tag: Optional[str] = None) -> str:
        return name

    model = create_schema_from_function("fn", fn)
    schema = dereference_refs(model.model_json_schema())
    props = schema["properties"]
    assert "name" in schema["required"]
    assert "tag" not in schema.get("required", [])
    # Optional[str] produces anyOf with null
    any_of_types = {s.get("type") for s in props["tag"].get("anyOf", [])}
    assert "null" in any_of_types


def test_create_schema_parse_docstring() -> None:
    def fn(name: str, count: int = 5) -> str:
        """Do something.

        Args:
            name: The name to use.
            count: How many times.
        """
        return name

    model = create_schema_from_function("fn", fn, parse_docstring=True)
    schema = model.model_json_schema()
    assert schema["properties"]["name"]["description"] == "The name to use."
    assert schema["properties"]["count"]["description"] == "How many times."


def test_create_schema_no_docstring() -> None:
    def fn(x: int) -> int:
        return x

    model = create_schema_from_function("fn", fn, parse_docstring=False)
    schema = model.model_json_schema()
    assert schema["properties"]["x"]["type"] == "integer"


def test_create_schema_pydantic_arg() -> None:
    class Address(BaseModel):
        street: str
        city: str

    def fn(address: Address) -> str:
        return address.city

    model = create_schema_from_function("fn", fn)
    schema = dereference_refs(model.model_json_schema())
    assert "address" in schema["properties"]
    assert schema["properties"]["address"]["type"] == "object"


def test_create_schema_filters_run_manager() -> None:
    """run_manager and callbacks should be excluded from the schema."""
    def fn(name: str, run_manager: object = None, callbacks: object = None) -> str:
        return name

    model = create_schema_from_function("fn", fn)
    schema = model.model_json_schema()
    assert "run_manager" not in schema.get("properties", {})
    assert "callbacks" not in schema.get("properties", {})


def test_create_schema_model_name() -> None:
    def fn(x: int) -> int:
        return x

    model = create_schema_from_function("MyToolSchema", fn)
    assert model.__name__ == "MyToolSchema"
