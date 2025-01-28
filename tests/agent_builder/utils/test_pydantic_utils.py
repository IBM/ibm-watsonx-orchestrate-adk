import json
from typing import Optional, List, Dict

from pydantic import BaseModel

from ibm_watsonx_orchestrate.agent_builder.tools import ToolPermission, tool
from ibm_watsonx_orchestrate.agent_builder.utils.pydantic_utils import generate_schema_only_base_model


def test_should_use_correct_defaults(snapshot):
    description = "test python description"
    @tool(description=description)
    def my_tool():
        pass

    spec = json.loads(my_tool.dumps_spec())
    InputBaseModel = generate_schema_only_base_model(schema=my_tool.__tool_spec__.input_schema)
    assert spec['input_schema'] == InputBaseModel.model_json_schema()
    assert spec['input_schema'] == InputBaseModel.schema()
    assert spec['input_schema'] == json.loads(InputBaseModel.schema_json())

    OutputBaseModel = generate_schema_only_base_model(schema=my_tool.__tool_spec__.output_schema)
    assert spec['output_schema'] == OutputBaseModel.model_json_schema()
    assert spec['output_schema'] == OutputBaseModel.schema()
    assert spec['output_schema'] == json.loads(OutputBaseModel.schema_json())


def test_should_be_possible_to_override_defaults(snapshot):
    @tool(name='myName', description='the description', permission=ToolPermission.ADMIN)
    def my_tool():
        pass

    spec = json.loads(my_tool.dumps_spec())
    InputBaseModel = generate_schema_only_base_model(schema=my_tool.__tool_spec__.input_schema)
    assert spec['input_schema'] == InputBaseModel.model_json_schema()
    assert spec['input_schema'] == InputBaseModel.schema()
    assert spec['input_schema'] == json.loads(InputBaseModel.schema_json())

    OutputBaseModel = generate_schema_only_base_model(schema=my_tool.__tool_spec__.output_schema)
    assert spec['output_schema'] == OutputBaseModel.model_json_schema()
    assert spec['output_schema'] == OutputBaseModel.schema()
    assert spec['output_schema'] == json.loads(OutputBaseModel.schema_json())


def test_should_support_typed_typings_inputs_and_outputs(snapshot):
    @tool(name='myName', description='the description', permission=ToolPermission.ADMIN)
    def my_tool(input: str) -> str:
        pass

    spec = json.loads(my_tool.dumps_spec())
    InputBaseModel = generate_schema_only_base_model(schema=my_tool.__tool_spec__.input_schema)
    assert spec['input_schema'] == InputBaseModel.model_json_schema()
    assert spec['input_schema'] == InputBaseModel.schema()
    assert spec['input_schema'] == json.loads(InputBaseModel.schema_json())

    OutputBaseModel = generate_schema_only_base_model(schema=my_tool.__tool_spec__.output_schema)
    assert spec['output_schema'] == OutputBaseModel.model_json_schema()
    assert spec['output_schema'] == OutputBaseModel.schema()
    assert spec['output_schema'] == json.loads(OutputBaseModel.schema_json())

    assert OutputBaseModel.model_validate('potato').model_dump() == 'potato'
    assert OutputBaseModel.model_validate('potato').model_dump_json() == '"potato"'


def test_should_support_typed_none_args(snapshot):
    @tool(name='myName', description='the description', permission=ToolPermission.ADMIN)
    def my_tool(input: None) -> None:
        pass

    spec = json.loads(my_tool.dumps_spec())
    InputBaseModel = generate_schema_only_base_model(schema=my_tool.__tool_spec__.input_schema)
    assert spec['input_schema'] == InputBaseModel.model_json_schema()
    assert spec['input_schema'] == InputBaseModel.schema()
    assert spec['input_schema'] == json.loads(InputBaseModel.schema_json())

    OutputBaseModel = generate_schema_only_base_model(schema=my_tool.__tool_spec__.output_schema)
    assert spec['output_schema'] == OutputBaseModel.model_json_schema()
    assert spec['output_schema'] == OutputBaseModel.schema()
    assert spec['output_schema'] == json.loads(OutputBaseModel.schema_json())


def test_should_support_typed_optional_args(snapshot):
    @tool(name='myName', description='the description', permission=ToolPermission.ADMIN)
    def my_tool(input: Optional[str]) -> Optional[str]:
        pass

    spec = json.loads(my_tool.dumps_spec())
    InputBaseModel = generate_schema_only_base_model(schema=my_tool.__tool_spec__.input_schema)
    assert spec['input_schema'] == InputBaseModel.model_json_schema()
    assert spec['input_schema'] == InputBaseModel.schema()
    assert spec['input_schema'] == json.loads(InputBaseModel.schema_json())

    OutputBaseModel = generate_schema_only_base_model(schema=my_tool.__tool_spec__.output_schema)
    assert spec['output_schema'] == OutputBaseModel.model_json_schema()
    assert spec['output_schema'] == OutputBaseModel.schema()
    assert spec['output_schema'] == json.loads(OutputBaseModel.schema_json())


class Nested(BaseModel):
    na: int

class SampleParamA(BaseModel):
    a: str
    b: Optional[str]
    c: str = None
    d: Nested
    e: Optional[Nested]
    f: Nested = None


def test_should_support_pydantic_typed_args(snapshot):
    description = "test python description"
    @tool(description=description)
    def sample_tool(sampleA: SampleParamA, b: Optional[SampleParamA]) -> SampleParamA:
        pass

    spec = json.loads(sample_tool.dumps_spec())
    InputBaseModel = generate_schema_only_base_model(schema=sample_tool.__tool_spec__.input_schema)
    assert spec['input_schema'] == InputBaseModel.model_json_schema()
    assert spec['input_schema'] == InputBaseModel.schema()
    assert spec['input_schema'] == json.loads(InputBaseModel.schema_json())

    OutputBaseModel = generate_schema_only_base_model(schema=sample_tool.__tool_spec__.output_schema)
    assert spec['output_schema'] == OutputBaseModel.model_json_schema()
    assert spec['output_schema'] == OutputBaseModel.schema()
    assert spec['output_schema'] == json.loads(OutputBaseModel.schema_json())


def test_should_work_with_lists(snapshot):
    description = "test python description"
    @tool(description=description)
    def sample_tool(sampleA: List[str], b: Optional[List[str]]) -> List[str]:
        pass

    spec = json.loads(sample_tool.dumps_spec())
    InputBaseModel = generate_schema_only_base_model(schema=sample_tool.__tool_spec__.input_schema)
    assert spec['input_schema'] == InputBaseModel.model_json_schema()
    assert spec['input_schema'] == InputBaseModel.schema()
    assert spec['input_schema'] == json.loads(InputBaseModel.schema_json())

    OutputBaseModel = generate_schema_only_base_model(schema=sample_tool.__tool_spec__.output_schema)
    assert spec['output_schema'] == OutputBaseModel.model_json_schema()
    assert spec['output_schema'] == OutputBaseModel.schema()
    assert spec['output_schema'] == json.loads(OutputBaseModel.schema_json())


def test_should_work_with_dicts(snapshot):
    description = "test python description"
    @tool(description=description)
    def sample_tool(sampleA: Dict[str, str], b: Optional[Dict[str, str]]) -> List[Dict[str, str]]:
        pass

    spec = json.loads(sample_tool.dumps_spec())
    InputBaseModel = generate_schema_only_base_model(schema=sample_tool.__tool_spec__.input_schema)
    assert spec['input_schema'] == InputBaseModel.model_json_schema()
    assert spec['input_schema'] == InputBaseModel.schema()
    assert spec['input_schema'] == json.loads(InputBaseModel.schema_json())

    OutputBaseModel = generate_schema_only_base_model(schema=sample_tool.__tool_spec__.output_schema)
    assert spec['output_schema'] == OutputBaseModel.model_json_schema()
    assert spec['output_schema'] == OutputBaseModel.schema()
    assert spec['output_schema'] == json.loads(OutputBaseModel.schema_json())

    sample = {'potato': 'tomato'}
    assert OutputBaseModel.model_validate([sample]).model_dump() == [sample]
    assert OutputBaseModel.model_validate([sample]).model_dump_json() == json.dumps([sample])
