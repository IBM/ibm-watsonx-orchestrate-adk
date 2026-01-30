import json
from typing import Any, Optional, List, Dict

from pydantic import BaseModel

from ibm_watsonx_orchestrate.agent_builder.tools import ToolPermission, tool
from ibm_watsonx_orchestrate.agent_builder.tools._internal.tool_response import ToolResponse
from ibm_watsonx_orchestrate.agent_builder.tools.types import PythonToolKind, WXOFile


def test_should_allow_naked_decorators(snapshot):
    @tool
    def my_tool():
        """
        The description
        """
        return 3

    spec = json.loads(my_tool.dumps_spec())
    spec['binding']['python']['function'] = spec['binding']['python']['function'].split('.')[-1]
    snapshot.assert_match(spec)
    result = my_tool()
    assert spec['name'] == 'my_tool'
    assert spec.get('description') == "The description"
    assert spec['permission'] == 'read_only'
    assert spec['binding']['python']['function'] == 'test_python_tool:my_tool'
    assert isinstance(result,ToolResponse)
    assert result.content == 3

def test_should_use_correct_defaults(snapshot):
    description = "test python description"
    @tool(description=description)
    def my_tool():
        pass

    spec = json.loads(my_tool.dumps_spec())
    spec['binding']['python']['function'] = spec['binding']['python']['function'].split('.')[-1]
    snapshot.assert_match(spec)
    assert spec['name'] == 'my_tool'
    assert spec.get('description') == description
    assert spec['permission'] == 'read_only'
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
    assert spec['permission'] == 'admin'
    assert spec['binding']['python']['function'] == 'test_python_tool:my_tool'


def test_should_support_wxo_file_format_inputs_and_outputs(snapshot):
    @tool(name='myName', description='the description', permission=ToolPermission.ADMIN)
    def my_tool(input: WXOFile) -> WXOFile:
        pass

    spec = json.loads(my_tool.dumps_spec())
    assert spec['input_schema']['properties']['input']['type'] == 'string'
    assert spec['input_schema']['properties']['input']['format'] == 'wxo-file'
    assert spec['output_schema']['type'] == 'string'
    assert spec['output_schema']['format'] == 'wxo-file'
    snapshot.assert_match(spec)


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
    description = "test python description"
    @tool(description=description)
    def sample_tool(sampleA: SampleParamA, b: Optional[SampleParamA]) -> SampleParamA:
        pass

    spec = json.loads(sample_tool.dumps_spec())
    spec['binding']['python']['function'] = spec['binding']['python']['function'].split('.')[-1]
    snapshot.assert_match(spec)


def test_should_work_with_lists(snapshot):
    description = "test python description"
    @tool(description=description)
    def sample_tool(sampleA: List[str], b: Optional[List[str]]) -> List[str]:
        pass

    spec = json.loads(sample_tool.dumps_spec())
    spec['binding']['python']['function'] = spec['binding']['python']['function'].split('.')[-1]
    snapshot.assert_match(spec)


def test_should_work_with_dicts(snapshot):
    description = "test python description"
    @tool(description=description)
    def sample_tool(sampleA: Dict[str, str], b: Optional[Dict[str, str]]) -> List[Dict[str, str]]:
        pass

    spec = json.loads(sample_tool.dumps_spec())
    spec['binding']['python']['function'] = spec['binding']['python']['function'].split('.')[-1]
    snapshot.assert_match(spec)

# Note: this is very flaky
# def test_should_work_with_custom_join_tool(snapshot):
#     description = "test python description"
#     @tool(description=description, kind=PythonToolKind.JOIN_TOOL)
#     def sample_tool(original_query: str, task_results: Dict[str, Any], messages: List[Dict[str, Any]]) -> str:
#         return ''
#
#     spec = json.loads(sample_tool.dumps_spec())
#     spec['binding']['python']['function'] = spec['binding']['python']['function'].split('.')[-1]
#     snapshot.assert_match(spec)
    
def test_should_reject_custom_join_tool_without_required_args():
    description = "test python description"
    try:
        @tool(description=description, kind=PythonToolKind.JOIN_TOOL)
        def sample_tool():
            return ''
        sample_tool.__tool_spec__
    except Exception as e:
        assert 'incorrect parameter names or order' in str(e)
    else:
        assert False, "Expected error was not raised"
        
def test_should_reject_custom_join_tool_with_incorrect_param_types():
    description = "test python description"
    try:
        @tool(description=description, kind=PythonToolKind.JOIN_TOOL)
        def sample_tool(original_query: str, task_results: Dict[str, int], messages: List[Dict[str, Any]]) -> str:
            return ''
        sample_tool.__tool_spec__
    except Exception as e:
        assert "incorrect type for parameter 'task_results'" in str(e)
    else:
        assert False, "Expected error was not raised"