import json

import pytest

from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.agent_builder.tools._internal.tool_response import ToolResponse
from ibm_watsonx_orchestrate.agent_builder.tools.types import (
    ToolRequestBody,
    ToolResponseBody,
    JsonSchemaObject,
)
from ibm_watsonx_orchestrate.agent_builder.tools.python_tool import TOOLS_DYNAMIC_PARAM_FLAG, TOOLS_DYNAMIC_SCHEMA_FLAG, _merge_dynamic_schema
from ibm_watsonx_orchestrate.run.context import AgentRun


def test_merge_dynamic_input_schema():
    """Test merging dynamic input schema into base schema"""
    base_schema = ToolRequestBody(
        type='object',
        properties={
            'base_field': JsonSchemaObject(type='string', description='Base field')
        },
        required=['base_field']
    )
    
    dynamic_schema = ToolRequestBody(
        type='object',
        properties={
            'dynamic_field': JsonSchemaObject(type='string', description='Dynamic field')
        },
        required=['dynamic_field']
    )
    
    _merge_dynamic_schema(base_schema, dynamic_schema)
    
    assert base_schema.properties
    assert 'base_field' in base_schema.properties
    assert 'dynamic_field' in base_schema.properties
    assert base_schema.required
    assert 'base_field' in base_schema.required
    assert 'dynamic_field' in base_schema.required
    assert hasattr(base_schema.properties['dynamic_field'], TOOLS_DYNAMIC_PARAM_FLAG )


def test_merge_dynamic_output_schema():
    """Test merging dynamic output schema into base schema"""
    base_schema = ToolResponseBody(
        type='object',
        properties={
            'base_field': JsonSchemaObject(type='string', description='Base field')
        }
    )
    
    dynamic_schema = ToolResponseBody(
        type='object',
        properties={
            'dynamic_field': JsonSchemaObject(type='integer', description='Dynamic field')
        }
    )
    
    _merge_dynamic_schema(base_schema, dynamic_schema)
    
    assert 'base_field' in base_schema.properties
    assert 'dynamic_field' in base_schema.properties
    assert hasattr(base_schema.properties['dynamic_field'], TOOLS_DYNAMIC_PARAM_FLAG)
    assert hasattr(base_schema, TOOLS_DYNAMIC_SCHEMA_FLAG)
    assert getattr(base_schema, TOOLS_DYNAMIC_SCHEMA_FLAG) == True


def test_merge_dynamic_schema_with_none():
    """Test that merging with None doesn't change base schema"""
    base_schema = ToolRequestBody(
        type='object',
        properties={
            'base_field': JsonSchemaObject(type='string')
        },
        required=['base_field']
    )
    
    assert base_schema.properties
    assert base_schema.required
    original_props = dict(base_schema.properties)
    original_required = list(base_schema.required)
    
    _merge_dynamic_schema(base_schema, None)
    
    assert base_schema.properties == original_props
    assert base_schema.required == original_required
    assert not hasattr(base_schema, TOOLS_DYNAMIC_SCHEMA_FLAG)


def test_merge_dynamic_schema_initializes_none_fields():
    """Test that merge initializes None properties and required fields"""
    base_schema = ToolRequestBody(
        type='object',
        properties=None,
        required=None
    )
    
    dynamic_schema = ToolRequestBody(
        type='object',
        properties={
            'dynamic_field': JsonSchemaObject(type='string')
        },
        required=['dynamic_field']
    )
    
    _merge_dynamic_schema(base_schema, dynamic_schema)
    
    assert base_schema.properties is not None
    assert base_schema.required is not None
    assert 'dynamic_field' in base_schema.properties
    assert 'dynamic_field' in base_schema.required
    assert hasattr(base_schema, TOOLS_DYNAMIC_SCHEMA_FLAG)
    assert getattr(base_schema, TOOLS_DYNAMIC_SCHEMA_FLAG) == True


def test_tool_with_dynamic_schema_enabled():
    """Test tool decorator with enable_dynamic_input_schema and enable_dynamic_output_schema  flags"""
    dynamic_input = ToolRequestBody(
        type='object',
        properties={
            'dynamic_param': JsonSchemaObject(type='string', description='Dynamic parameter')
        },
        required=['dynamic_param']
    )
    
    dynamic_output = ToolResponseBody(
        type='object',
        properties={
            'dynamic_result': JsonSchemaObject(type='string', description='Dynamic result')
        }
    )
    
    @tool(
        name='test_dynamic_tool',
        description='A tool with dynamic schema',
        enable_dynamic_input_schema=True,
        enable_dynamic_output_schema=True,
        dynamic_input_schema=dynamic_input,
        dynamic_output_schema=dynamic_output
    )
    def my_dynamic_tool(base_param: str) -> dict:
        """
        A tool with both base and dynamic parameters
        
        Args:
            base_param: A base parameter
            
        Returns:
            A dictionary result
        """
        return {'base_result': base_param}
    
    spec = json.loads(my_dynamic_tool.dumps_spec())
    
    # Check that both base and dynamic fields are present
    assert 'base_param' in spec['input_schema']['properties']
    assert 'dynamic_param' in spec['input_schema']['properties']
    assert 'base_param' in spec['input_schema']['required']
    assert 'dynamic_param' in spec['input_schema']['required']
    
    # Check output schema
    assert 'dynamic_result' in spec['output_schema']['properties']


def test_tool_with_agent_run_context():
    """Test tool with AgentRun context parameter"""
    @tool(name='context_tool', description='Tool with context')
    def my_context_tool(param: str, context: AgentRun) -> str:
        """
        A tool that uses agent run context
        
        Args:
            param: A parameter
            context: The agent run context
            
        Returns:
            A string result
        """
        return f"param: {param}"
    
    # The tool should be callable
    result = my_context_tool(param="test", context=AgentRun())
    assert isinstance(result,ToolResponse)
    assert result.content == "param: test"
    
    # Check that context parameter is in the spec
    spec = json.loads(my_context_tool.dumps_spec())
    assert 'param' in spec['input_schema']['properties']


def test_dynamic_schema_without_enable_flag():
    """Test that dynamic schemas are ignored when enable_dynamic_input_schema is False"""
    dynamic_input = ToolRequestBody(
        type='object',
        properties={
            'dynamic_param': JsonSchemaObject(type='string')
        }
    )
    
    @tool(
        name='no_dynamic_tool',
        enable_dynamic_input_schema=False,
        dynamic_input_schema=dynamic_input
    )
    def my_tool(base_param: str) -> str:
        """Tool without dynamic schema enabled"""
        return base_param
    
    spec = json.loads(my_tool.dumps_spec())
    
    # Dynamic field should NOT be present
    assert 'base_param' in spec['input_schema']['properties']
    assert 'dynamic_param' not in spec['input_schema']['properties']
    assert TOOLS_DYNAMIC_SCHEMA_FLAG not in spec['input_schema']


def test_merge_dynamic_schema_with_duplicate_properties(caplog):
    """Test that merging raises ValueError when duplicate property names exist"""
    base_schema = ToolRequestBody(
        type='object',
        properties={
            'shared_field': JsonSchemaObject(type='string', description='Base field'),
            'base_only': JsonSchemaObject(type='integer', description='Base only field')
        },
        required=['shared_field']
    )
    
    dynamic_schema = ToolRequestBody(
        type='object',
        properties={
            'shared_field': JsonSchemaObject(type='string', description='Dynamic field'),
            'dynamic_only': JsonSchemaObject(type='boolean', description='Dynamic only field')
        },
        required=['shared_field']
    )
    
    with pytest.raises(ValueError) as exc_info:
        _merge_dynamic_schema(base_schema, dynamic_schema)
    
    assert "Duplicate properties found" in str(exc_info.value)
    assert 'shared_field' in caplog.text


def test_merge_dynamic_schema_with_multiple_duplicates(caplog):
    """Test that all duplicate property names are reported"""
    base_schema = ToolRequestBody(
        type='object',
        properties={
            'field1': JsonSchemaObject(type='string'),
            'field2': JsonSchemaObject(type='integer'),
            'field3': JsonSchemaObject(type='boolean'),
            'unique_base': JsonSchemaObject(type='string')
        },
        required=['field1', 'field2']
    )
    
    dynamic_schema = ToolRequestBody(
        type='object',
        properties={
            'field1': JsonSchemaObject(type='string'),
            'field2': JsonSchemaObject(type='integer'),
            'unique_dynamic': JsonSchemaObject(type='string')
        },
        required=['field1']
    )
    
    with pytest.raises(ValueError) as exc_info:
        _merge_dynamic_schema(base_schema, dynamic_schema)
    
    assert "Duplicate properties found" in str(exc_info.value)
    # Both duplicates should be mentioned
    assert 'field1' in caplog.text
    assert 'field2' in caplog.text


def test_tool_with_duplicate_dynamic_properties_raises_error(caplog):
    """Test that tool decorator raises error when dynamic schema has duplicate properties"""
    dynamic_input = ToolRequestBody(
        type='object',
        properties={
            'base_param': JsonSchemaObject(type='integer', description='Duplicate parameter')
        },
        required=['base_param']
    )
    
    @tool(
        name='duplicate_tool',
        description='A tool with duplicate properties',
        enable_dynamic_input_schema=True,
        dynamic_input_schema=dynamic_input
    )
    def my_tool_with_duplicate(base_param: str) -> str:
        """
        A tool that should fail due to duplicate properties
        
        Args:
            base_param: A base parameter
            
        Returns:
            A string result
        """
        return base_param
    
    # Accessing the spec should raise ValueError due to duplicates
    with pytest.raises(ValueError) as exc_info:
        _ = my_tool_with_duplicate.__tool_spec__
    
    assert "Duplicate properties found" in str(exc_info.value)
    assert 'base_param' in caplog.text


def test_merge_dynamic_schema_no_duplicates_succeeds():
    """Test that merging succeeds when there are no duplicate properties"""
    base_schema = ToolRequestBody(
        type='object',
        properties={
            'base_field1': JsonSchemaObject(type='string'),
            'base_field2': JsonSchemaObject(type='integer')
        },
        required=['base_field1']
    )
    
    dynamic_schema = ToolRequestBody(
        type='object',
        properties={
            'dynamic_field1': JsonSchemaObject(type='boolean'),
            'dynamic_field2': JsonSchemaObject(type='string')
        },
        required=['dynamic_field1']
    )
    
    # Should not raise any exception
    _merge_dynamic_schema(base_schema, dynamic_schema)
    
    # Verify all fields are present
    assert base_schema.properties
    assert 'base_field1' in base_schema.properties
    assert 'base_field2' in base_schema.properties
    assert 'dynamic_field1' in base_schema.properties
    assert 'dynamic_field2' in base_schema.properties
    assert len(base_schema.properties) == 4
    assert hasattr(base_schema, TOOLS_DYNAMIC_SCHEMA_FLAG)
    assert getattr(base_schema, TOOLS_DYNAMIC_SCHEMA_FLAG) == True


def test_merge_dynamic_output_schema_with_duplicates(caplog):
    """Test that output schema merge also detects duplicates"""
    base_schema = ToolResponseBody(
        type='object',
        properties={
            'result': JsonSchemaObject(type='string', description='Base result')
        }
    )
    
    dynamic_schema = ToolResponseBody(
        type='object',
        properties={
            'result': JsonSchemaObject(type='integer', description='Dynamic result')
        }
    )
    
    with pytest.raises(ValueError) as exc_info:
        _merge_dynamic_schema(base_schema, dynamic_schema)
    
    assert "Duplicate properties found" in str(exc_info.value)
    assert 'result' in caplog.text


def test_kwargs_removed_when_dynamic_schema_enabled():
    """Test that kwargs parameter is removed from input schema when dynamic schema is enabled"""
    @tool(
        name='tool_with_kwargs',
        description='A tool with kwargs parameter',
        enable_dynamic_input_schema=True
    )
    def my_tool_with_kwargs(base_param: str, **kwargs) -> str:
        """
        A tool with kwargs parameter that should be removed
        
        Args:
            base_param: A base parameter
            **kwargs: Additional keyword arguments
            
        Returns:
            A string result
        """
        return base_param
    
    spec = json.loads(my_tool_with_kwargs.dumps_spec())
    
    # kwargs should be removed from the input schema
    assert 'base_param' in spec['input_schema']['properties']
    assert 'kwargs' not in spec['input_schema']['properties']
    assert 'base_param' in spec['input_schema']['required']


def test_kwargs_present_when_dynamic_schema_disabled():
    """Test that kwargs parameter is present in input schema when dynamic schema is disabled"""
    @tool(
        name='tool_with_kwargs_no_dynamic',
        description='A tool with kwargs parameter',
        enable_dynamic_input_schema=False
    )
    def my_tool_with_kwargs_no_dynamic(base_param: str, **kwargs) -> str:
        """
        A tool with kwargs parameter that should remain
        
        Args:
            base_param: A base parameter
            **kwargs: Additional keyword arguments
            
        Returns:
            A string result
        """
        return base_param
    
    spec = json.loads(my_tool_with_kwargs_no_dynamic.dumps_spec())
    
    # kwargs should be present when dynamic schema is disabled
    assert 'base_param' in spec['input_schema']['properties']
    assert 'kwargs' in spec['input_schema']['properties']