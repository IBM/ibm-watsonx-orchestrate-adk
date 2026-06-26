"""
Tests for ToolResponse.__init__ attribute initialisation.

Regression coverage for: _meta attribute missing from the else-branch of
ToolResponse.__init__, causing AttributeError on any tool that returns plain
content (non-ToolResult).
"""
import pytest
from ibm_watsonx_orchestrate.agent_builder.tools._internal.tool_response import ToolResponse


def test_meta_initialised_for_plain_content():
    """_meta must exist on ToolResponse built from plain content."""
    response = ToolResponse(content={"result": "ok"})
    assert response._meta == {}


def test_meta_initialised_for_plain_string_content():
    """_meta must exist when content is a plain string."""
    response = ToolResponse(content="hello")
    assert response._meta == {}


def test_meta_initialised_for_none_content():
    """_meta must exist even when content is None."""
    response = ToolResponse(content=None)
    assert response._meta == {}


def test_repr_does_not_raise_for_plain_content():
    """__repr__ must not raise AttributeError for plain content."""
    response = ToolResponse(content={"result": "ok"})
    # Would raise AttributeError: 'ToolResponse' object has no attribute '_meta'
    # before the fix
    repr_str = repr(response)
    assert "_meta" in repr_str


def test_to_dict_does_not_raise_for_plain_content():
    """to_dict must not raise AttributeError for plain content."""
    response = ToolResponse(content={"result": "ok"})
    result = response.to_dict()
    assert result["content"] == {"result": "ok"}
    assert "_meta" not in result  # empty _meta should be omitted


def test_getitem_meta_does_not_raise_for_plain_content():
    """response['_meta'] must not raise AttributeError for plain content."""
    response = ToolResponse(content={"result": "ok"})
    assert response["_meta"] == {}


def test_meta_passed_explicitly_is_preserved():
    """_meta value passed to constructor must be stored on the instance."""
    meta = {"progressToken": 42}
    response = ToolResponse(content={"result": "ok"}, _meta=meta)
    assert response._meta == {"progressToken": 42}
    result = response.to_dict()
    assert result["_meta"] == {"progressToken": 42}
