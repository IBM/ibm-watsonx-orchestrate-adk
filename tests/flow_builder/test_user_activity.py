import pytest

from ibm_watsonx_orchestrate.flow_builder.flows import FlowFactory
from ibm_watsonx_orchestrate.flow_builder.types import UserNodeSpec


def _build_flow():
    return FlowFactory.create_flow(name="activity_test_flow")


def test_boolean_input_activity_matches_sample():
    """Emitted JSON must match the 'Boolean input' sample from wo-tracker issue #79123."""
    aflow = _build_flow()
    uf = aflow.userflow(name="uf1")
    node = uf.activity(name="user_64f223", display_name="Confirmation")
    node.boolean_input_field(
        name="boolean_da9645",
        label="I agree",
        agent_message="I {flow.input.myname} have read the terms and conditions",
        single_checkbox=False,
        true_label="Yes",
        false_label="No",
        required=True,
    )

    out = node.get_spec().to_json()

    assert out["kind"] == "user"
    assert out["name"] == "user_64f223"
    assert out["display_name"] == "Confirmation"
    assert "is_activity" not in out  # SDK marker must not leak

    fields = out["fields"]
    assert len(fields) == 1
    f = fields[0]
    assert f["kind"] == "boolean"
    assert f["direction"] == "input"
    assert f["spec_version"] == "2.0"
    assert f["name"] == "boolean_da9645"
    assert f["display_name"] == "I agree"
    # Stray attributes from the buggy shape must NOT be present.
    assert "text" not in f
    assert "label" not in f

    # uiSchema — label lives here as ui:title.
    assert f["uiSchema"]["ui:title"] == "I agree"
    assert f["uiSchema"]["ui:widget"] == "RadioWidget"

    # jsonSchema — agent_message lives here as description; label lives as property title.
    js = f["jsonSchema"]
    assert js["type"] == "object"
    assert js["required"] == ["boolean_da9645"]
    assert js["description"] == "I {flow.input.myname} have read the terms and conditions"
    assert js["additionalProperties"] is False
    prop = js["properties"]["boolean_da9645"]
    assert prop["type"] == "boolean"
    assert prop["title"] == "I agree"
    assert prop["oneOf"] == [
        {"const": True, "title": "Yes"},
        {"const": False, "title": "No"},
    ]


def test_present_to_user_message_activity_matches_sample():
    """Text-output activity is the Present-to-User-Message exception:
    agent_message goes to field.text, no ui:title, no jsonSchema.description."""
    aflow = _build_flow()
    uf = aflow.userflow(name="uf2")
    node = uf.activity(name="user_msg", display_name="Message 1")
    node.message_output_field(
        name="text_output_9a6461",
        text="Hello world! Today is {flow.input.day_of_week}.",
    )

    out = node.get_spec().to_json()
    f = out["fields"][0]

    assert f["kind"] == "text"
    assert f["direction"] == "output"
    assert f["spec_version"] == "2.0"
    assert f["text"] == "Hello world! Today is {flow.input.day_of_week}."

    # No display_name, no ui:title in the Present-to-User path.
    assert "display_name" not in f
    assert "ui:title" not in f["uiSchema"]
    assert f["uiSchema"]["ui:widget"] == "DataWidget"
    assert f["uiSchema"]["ui:options"]["label"] is False

    # jsonSchema has no description, property has no title.
    js = f["jsonSchema"]
    assert "description" not in js
    assert js["required"] == []
    assert js["properties"]["text_output_9a6461"] == {"type": "string"}
    assert js["additionalProperties"] is False


def test_userflow_emits_runtime_label():
    """Per User activity.md: the user_flow container carries a runtime-visible
    `label`, distinct from the build-time `display_name`."""
    aflow = _build_flow()
    uf = aflow.userflow(
        name="user_flow_bfbd73",
        display_name="User activity 1",
        label="Confirmation",
    )

    spec = uf.to_json()["spec"]
    assert spec["kind"] == "user_flow"
    assert spec["display_name"] == "User activity 1"   # build-time node name
    assert spec["label"] == "Confirmation"             # runtime chat title


def test_userflow_label_supports_variable_substitution():
    aflow = _build_flow()
    uf = aflow.userflow(name="uf_sub", label="Confirm for {flow.input.myname}")
    assert uf.to_json()["spec"]["label"] == "Confirm for {flow.input.myname}"


def test_userflow_omits_label_when_not_set():
    """Backwards compatibility: existing flows never set label, so the key
    must not appear."""
    aflow = _build_flow()
    uf = aflow.userflow(name="uf_nolabel", display_name="No label")
    assert "label" not in uf.to_json()["spec"]


def test_activity_omits_title_when_no_label():
    """The activity jsonSchema is a plain dict that bypasses the None-stripping
    in _assign_attribute, so a missing label must not emit `title: null`."""
    aflow = _build_flow()
    uf = aflow.userflow(name="uf_t")
    node = uf.activity(name="no_label")
    node.text_input_field(name="foo")

    prop = node.get_spec().to_json()["fields"][0]["jsonSchema"]["properties"]["foo"]
    assert prop == {"type": "string"}
    assert "title" not in prop


def test_activity_sets_title_when_label_given():
    aflow = _build_flow()
    uf = aflow.userflow(name="uf_t2")
    node = uf.activity(name="with_label")
    node.number_input_field(name="age", label="Age", agent_message="How old?")

    prop = node.get_spec().to_json()["fields"][0]["jsonSchema"]["properties"]["age"]
    assert prop["title"] == "Age"
    assert prop["type"] == "number"


def test_activity_never_emits_null_values_in_json_schema():
    """Guard against any future null leaking into the passthrough dict."""
    aflow = _build_flow()
    uf = aflow.userflow(name="uf_null")

    for i, method in enumerate([
        "text_input_field",
        "number_input_field",
        "date_input_field",
        "boolean_input_field",
    ]):
        node = uf.activity(name=f"n{i}")
        getattr(node, method)(name=f"f{i}")
        js = node.get_spec().to_json()["fields"][0]["jsonSchema"]
        for prop_name, prop in js["properties"].items():
            assert None not in prop.values(), f"{method} emitted a null in {prop_name}: {prop}"


def test_activity_enforces_single_widget():
    aflow = _build_flow()
    uf = aflow.userflow(name="uf3")
    node = uf.activity(name="only_one")
    node.boolean_input_field(name="agree", label="I agree", agent_message="Do you agree?")
    with pytest.raises(ValueError, match="exactly one widget"):
        node.text_input_field(name="second", label="Second", agent_message="Nope")


# --- negative cases -------------------------------------------------------

@pytest.mark.parametrize("widget", [
    "list_input_field",
    "list_output_field",
    "user_input_field",
    "field_output_field",
    "date_range_input_field",
    "datetime_range_input_field",
    "file_download_field",
])
def test_unsupported_widget_on_activity_gives_actionable_error(widget):
    """A node created via activity() must never be told to "call form() first" —
    it already has a container. The error must say the widget is unsupported
    and name the alternatives."""
    aflow = _build_flow()
    uf = aflow.userflow(name=f"uf_{widget}")
    node = uf.activity(name=f"n_{widget}")

    with pytest.raises(ValueError) as exc:
        getattr(node, widget)(name="x", label="X")

    msg = str(exc.value)
    assert "not supported on a UserActivity" in msg
    assert "text_input_field" in msg            # names the alternatives
    assert "Please call the form()" not in msg  # must NOT give the misleading advice


def test_unsupported_widget_on_bare_node_keeps_original_guidance():
    """Bare nodes (no form, no activity) should still be told to create a
    container first."""
    aflow = _build_flow()
    uf = aflow.userflow(name="uf_bare")
    from ibm_watsonx_orchestrate.flow_builder.types import UserFieldKind
    bare = uf.field(direction="input", name="bare", kind=UserFieldKind.Text, text="q")

    with pytest.raises(ValueError, match="Please call the form\\(\\) or activity\\(\\)"):
        bare.list_input_field(name="x", label="X")


def test_activity_rejects_unsupported_kind_directly():
    """_build_activity_field must reject kinds it has no schema recipe for,
    rather than emitting a malformed jsonSchema."""
    from ibm_watsonx_orchestrate.flow_builder.types import (
        _build_activity_field, UserFieldKind,
    )
    with pytest.raises(ValueError, match="does not yet support"):
        _build_activity_field(
            name="c", kind=UserFieldKind.Choice, direction="input", label="C",
        )


def test_second_widget_rejected_regardless_of_widget_type():
    """The single-widget guard must hold across differing widget types, not
    just repeats of the same one."""
    aflow = _build_flow()
    uf = aflow.userflow(name="uf_mix")
    node = uf.activity(name="mixed")
    node.number_input_field(name="age", label="Age", agent_message="How old?")

    with pytest.raises(ValueError, match="exactly one widget"):
        node.message_output_field(name="msg", text="Hi")


def test_activity_requires_name():
    aflow = _build_flow()
    uf = aflow.userflow(name="uf_noname")
    with pytest.raises((AssertionError, ValueError)):
        uf.activity(name="")


def test_example_module_runs():
    """Import the example and run its build function against a fresh Flow.

    Guards against the example rotting when the API evolves.
    """
    import importlib.util
    import os
    example_path = os.path.join(
        os.path.dirname(__file__), "..", "..",
        "examples", "flow_builder", "user_activity_nextgen", "tools",
        "user_activity_nextgen.py",
    )
    spec = importlib.util.spec_from_file_location("user_activity_nextgen_example", example_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    aflow = FlowFactory.create_flow(name="next_gen_user_activity_example")
    result = module.build(aflow)

    activity_nodes = []
    for _, node in result.nodes.items():
        if hasattr(node, "nodes"):
            for _, inner in node.nodes.items():
                spec = inner.spec
                if isinstance(spec, UserNodeSpec) and getattr(spec, "is_activity", False):
                    activity_nodes.append(spec)

    assert len(activity_nodes) == 4
    for s in activity_nodes:
        assert s.fields and len(s.fields) == 1
        assert s.fields[0].spec_version == "2.0"


def test_widget_on_bare_usernode_still_raises():
    """Legacy UserNodes (no form, no activity) should still raise with the updated
    error mentioning both form() and activity()."""
    aflow = _build_flow()
    uf = aflow.userflow(name="uf4")
    # .field() creates a legacy standalone UserNode without is_activity.
    from ibm_watsonx_orchestrate.flow_builder.types import UserFieldKind
    legacy = uf.field(direction="input", name="legacy_text", kind=UserFieldKind.Text, text="Type something")
    with pytest.raises(ValueError, match="activity\\(\\)"):
        legacy.boolean_input_field(name="foo", label="Foo")
