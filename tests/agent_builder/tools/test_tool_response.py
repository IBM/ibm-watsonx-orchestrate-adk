"""Minimal regression tests for ToolResponse plain-content metadata handling."""
from ibm_watsonx_orchestrate.agent_builder.tools._internal.tool_response import ToolResponse


def test_plain_content_initializes_meta():
    """Plain-content responses should always initialize _meta."""
    response = ToolResponse(content={"result": "ok"})

    assert response._meta == {}


def test_to_dict_does_not_raise_for_plain_content_and_omits_empty_meta():
    """Serializing plain-content responses should not fail when _meta is empty."""
    response = ToolResponse(content={"result": "ok"})

    result = response.to_dict()

    assert result["content"] == {"result": "ok"}
    assert "_meta" not in result


def test_explicit_meta_is_preserved_for_plain_content():
    """Explicit _meta passed for plain content should round-trip through to_dict.

    NOTE: The dict literal {"progressToken": 42} is intentionally NOT extracted to a
    variable.  If ToolResponse.__init__ were to mutate the passed-in dict the same
    reference would be modified and the assertion below could still pass, masking the
    bug.  Keeping the literal here acts as a safeguard against unintentional mutations.
    """
    response = ToolResponse(content={"result": "ok"}, _meta={"progressToken": 42})

    assert response._meta == {"progressToken": 42}
    assert response.to_dict()["_meta"] == {"progressToken": 42}


def test_explicit_meta_none_initializes_empty_dict():
    """Passing _meta=None explicitly should still result in an empty _meta dict."""
    response = ToolResponse(content={"result": "ok"}, _meta=None)

    assert response._meta == {}
