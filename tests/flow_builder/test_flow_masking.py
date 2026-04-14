import pytest
from pydantic import BaseModel

from ibm_watsonx_orchestrate.flow_builder.flows import FlowFactory
from ibm_watsonx_orchestrate.flow_builder.masking_utils import MaskingPolicy


class MaskingFlowInput(BaseModel):
    secret: str
    age: float


class MaskingFlowOutput(BaseModel):
    result: str


def _build_masking_test_flow():
    return FlowFactory.create_flow(
        name="masking_test_flow",
        input_schema=MaskingFlowInput,
        output_schema=MaskingFlowOutput,
    )


def test_mask_property_applies_masking_to_flow_input_string_property():
    aflow = _build_masking_test_flow()

    aflow.mask_property("flow.input.secret", MaskingPolicy.MASK_ALL)

    input_schema_ref = aflow.spec.input_schema
    input_schema = aflow._resolve_schema_ref(input_schema_ref)
    assert input_schema is not None
    properties = input_schema.properties or {}
    secret_schema = properties["secret"]
    extra = secret_schema.model_extra or {}

    assert extra["x-ibm-is-sensitive"] is True
    assert extra["x-ibm-masking-policy"] == MaskingPolicy.MASK_ALL.value


def test_mask_property_rejects_flow_output_path():
    aflow = _build_masking_test_flow()

    with pytest.raises(ValueError, match="Cannot mask flow output properties"):
        aflow.mask_property("flow.output.result", MaskingPolicy.MASK_ALL)


def test_mask_property_rejects_non_string_property():
    aflow = _build_masking_test_flow()

    with pytest.raises(ValueError, match="Only string properties can be masked"):
        aflow.mask_property("flow.input.age", MaskingPolicy.MASK_ALL)

# Made with Bob


def test_mask_property_serializes_masking_extensions_in_flow_json():
    aflow = _build_masking_test_flow()

    aflow.mask_property("flow.input.secret", MaskingPolicy.MASK_ALL)
    flow_json = aflow.to_json()

    input_schema_ref = flow_json["spec"]["input_schema"]["$ref"]
    input_schema_name = input_schema_ref.split("/")[-1]
    secret_schema = flow_json["schemas"][input_schema_name]["properties"]["secret"]

    assert secret_schema["x-ibm-is-sensitive"] is True
    assert secret_schema["x-ibm-masking-policy"] == MaskingPolicy.MASK_ALL.value
