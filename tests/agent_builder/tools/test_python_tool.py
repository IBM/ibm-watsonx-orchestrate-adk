import json
from typing import Optional, List, Dict

from pydantic import BaseModel

from ibm_watsonx_orchestrate.agent_builder.tools import ToolPermission, tool


def test_should_use_correct_defaults(snapshot):
    @tool()
    def my_tool():
        pass

    spec = json.loads(my_tool.dumps_spec())
    spec['binding']['python']['function'] = spec['binding']['python']['function'].split('.')[-1]
    snapshot.assert_match(spec)
    assert spec['name'] == 'my_tool'
    assert spec['description'] == None
    assert spec['permission'] == 'READ_ONLY'
    assert spec['binding']['python']['function'] == 'test_python_tool:my_tool'


def test_should_be_possible_to_override_defaults(snapshot):
    @tool(name='myName', description='the description', permission=ToolPermission.ADMIN)
    def my_tool():
        pass

    spec = json.loads(my_tool.dumps_spec())
    # we do this because the module name will change based on the root folder you run it from
    assert 'tools.test_python_tool' in spec['binding']['python']['function']
    spec['binding']['python']['function'] = spec['binding']['python']['function'].split('.')[-1]
    snapshot.assert_match(spec)
    assert spec['name'] == 'myName'
    assert spec['description'] == 'the description'
    assert spec['permission'] == 'ADMIN'
    assert spec['binding']['python']['function'] == 'test_python_tool:my_tool'


def test_should_support_typed_typings_inputs_and_outputs(snapshot):
    @tool(name='myName', description='the description', permission=ToolPermission.ADMIN)
    def my_tool(input: str) -> str:
        pass

    spec = json.loads(my_tool.dumps_spec())
    spec['binding']['python']['function'] = spec['binding']['python']['function'].split('.')[-1]
    snapshot.assert_match(spec)


def test_should_support_typed_none_args(snapshot):
    @tool(name='myName', description='the description', permission=ToolPermission.ADMIN)
    def my_tool(input: None) -> None:
        pass

    spec = json.loads(my_tool.dumps_spec())
    spec['binding']['python']['function'] = spec['binding']['python']['function'].split('.')[-1]
    snapshot.assert_match(spec)


def test_should_support_typed_optional_args(snapshot):
    @tool(name='myName', description='the description', permission=ToolPermission.ADMIN)
    def my_tool(input: Optional[str]) -> Optional[str]:
        pass

    spec = json.loads(my_tool.dumps_spec())
    spec['binding']['python']['function'] = spec['binding']['python']['function'].split('.')[-1]
    snapshot.assert_match(spec)


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
    @tool()
    def sample_tool(sampleA: SampleParamA, b: Optional[SampleParamA]) -> SampleParamA:
        pass

    spec = json.loads(sample_tool.dumps_spec())
    spec['binding']['python']['function'] = spec['binding']['python']['function'].split('.')[-1]
    snapshot.assert_match(spec)


def test_should_work_with_lists(snapshot):
    @tool()
    def sample_tool(sampleA: List[str], b: Optional[List[str]]) -> List[str]:
        pass

    spec = json.loads(sample_tool.dumps_spec())
    spec['binding']['python']['function'] = spec['binding']['python']['function'].split('.')[-1]
    snapshot.assert_match(spec)


def test_should_work_with_dicts(snapshot):
    @tool()
    def sample_tool(sampleA: Dict[str, str], b: Optional[Dict[str, str]]) -> List[Dict[str, str]]:
        pass

    spec = json.loads(sample_tool.dumps_spec())
    spec['binding']['python']['function'] = spec['binding']['python']['function'].split('.')[-1]
    snapshot.assert_match(spec)
