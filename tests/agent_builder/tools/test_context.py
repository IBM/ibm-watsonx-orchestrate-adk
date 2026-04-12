import pytest
from types import MappingProxyType

from ibm_watsonx_orchestrate.run.context import AgentRun, RequestContext
from ibm_watsonx_orchestrate.agent_builder.tools.types import JsonSchemaObject


def test_agent_run_basic_creation():
    """Test basic AgentRun creation"""
    agent_run = AgentRun()
    assert agent_run.request_context.context == {}
    assert agent_run.dynamic_input_schema is None
    assert agent_run.dynamic_output_schema is None


def test_agent_run_with_request_context_from_dict():
    """Test AgentRun with request context created from a dict"""
    context_data = {'user_id': '123', 'session_id': 'abc'}
    agent_run = AgentRun(request_context=context_data)
    
    assert isinstance(agent_run.request_context, RequestContext)
    assert agent_run.request_context['user_id'] == '123'
    assert agent_run.request_context['session_id'] == 'abc'

def test_agent_run_with_passed_request_context():
    """Test AgentRun with request context passed during init"""
    context_data = RequestContext({'user_id': '123', 'session_id': 'abc'})
    agent_run = AgentRun(request_context=context_data)
    
    assert isinstance(agent_run.request_context, RequestContext)
    assert agent_run.request_context['user_id'] == '123'
    assert agent_run.request_context['session_id'] == 'abc'

def test_agent_run_mutability():
    """Test that AgentRun data can be modified"""
    context_data = RequestContext({'user_id': '123', 'session_id': 'abc'})
    agent_run = AgentRun(request_context=context_data)
    agent_run.request_context['user_id'] = '456'
    agent_run.request_context['session_id'] = 'defg'

    assert isinstance(agent_run.request_context, RequestContext)
    assert agent_run.request_context['user_id'] == '456'
    assert agent_run.request_context['session_id'] == 'defg'

    del agent_run.request_context['user_id']
    del agent_run.request_context['session_id']

    assert agent_run.request_context['user_id'] == '123'
    assert agent_run.request_context['session_id'] == 'abc'

def test_agent_run_get_updates():
    """Test that AgentRun data can fetch context updates"""
    context_data = RequestContext({'user_id': '123', 'session_id': 'abc'})
    agent_run = AgentRun(request_context=context_data)
    agent_run.request_context['user_id'] = '456'
    agent_run.request_context['user_id'] = '789'
    agent_run.request_context['user_id'] = 'abc'

    assert isinstance(agent_run.request_context, RequestContext)
    updates = agent_run.get_context_updates()
    assert len(updates) == 1
    assert updates['user_id'] == 'abc'

def test_agent_run_clear_updates():
    """Test that AgentRun data can clear context updates"""
    initial_data = {'user_id': '123', 'session_id': 'abc'}
    context_data = RequestContext(initial_data)
    agent_run = AgentRun(request_context=context_data)
    agent_run.request_context['user_id'] = '456'

    assert isinstance(agent_run.request_context, RequestContext)

    assert len(agent_run.get_context_updates()) == 1
    agent_run.clear_context_updates()
    assert len(agent_run.get_context_updates()) == 0
    assert agent_run.request_context.context == initial_data


def test_agent_run_with_dynamic_input_schema_dict():
    """Test AgentRun with dynamic input schema as dict"""
    schema_dict = {
        'type': 'string',
        'description': 'A dynamic field'
    }
    agent_run = AgentRun(dynamic_input_schema=schema_dict)
    
    # Should be converted to JsonSchemaObject
    assert isinstance(agent_run.dynamic_input_schema, JsonSchemaObject)
    assert agent_run.dynamic_input_schema.type == 'string'
    assert agent_run.dynamic_input_schema.description == 'A dynamic field'


def test_agent_run_with_dynamic_output_schema_dict():
    """Test AgentRun with dynamic output schema as dict"""
    schema_dict = {
        'type': 'object',
        'properties': {
            'result': {'type': 'string'}
        }
    }
    agent_run = AgentRun(dynamic_output_schema=schema_dict)
    
    # Should be converted to JsonSchemaObject
    assert isinstance(agent_run.dynamic_output_schema, JsonSchemaObject)
    assert agent_run.dynamic_output_schema.type == 'object'
    assert agent_run.dynamic_output_schema.properties
    assert 'result' in agent_run.dynamic_output_schema.properties


def test_agent_run_with_json_schema_object():
    """Test AgentRun with JsonSchemaObject directly"""
    schema_obj = JsonSchemaObject(type='string', description='Test schema')
    agent_run = AgentRun(dynamic_input_schema=schema_obj)
    
    assert isinstance(agent_run.dynamic_input_schema, JsonSchemaObject)
    assert agent_run.dynamic_input_schema.type == 'string'
    assert agent_run.dynamic_input_schema.description == 'Test schema'


def test_agent_run_with_all_fields():
    """Test AgentRun with all fields populated"""
    context_data = {'user': 'test_user'}
    input_schema = {'type': 'string'}
    output_schema = {'type': 'object'}
    
    agent_run = AgentRun(
        request_context=context_data,
        dynamic_input_schema=input_schema,
        dynamic_output_schema=output_schema
    )
    
    assert isinstance(agent_run.request_context, RequestContext)
    assert agent_run.request_context['user'] == 'test_user'
    assert isinstance(agent_run.dynamic_input_schema, JsonSchemaObject)
    assert isinstance(agent_run.dynamic_output_schema, JsonSchemaObject)


def test_agent_run_nested_context():
    """Test AgentRun with nested context data"""
    context_data = {
        'user': {
            'id': '123',
            'name': 'Test User',
            'roles': ['admin', 'user']
        },
        'session': {
            'id': 'session_123',
            'created_at': '2024-01-01'
        }
    }
    agent_run = AgentRun(request_context=context_data)
    
    assert isinstance(agent_run.request_context, RequestContext)
    assert agent_run.request_context['user']['id'] == '123'
    assert 'admin' in agent_run.request_context['user']['roles']
    assert agent_run.request_context['session']['id'] == 'session_123'


def test_agent_run_schema_with_complex_properties():
    """Test AgentRun with complex schema properties"""
    schema_dict = {
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string',
                'description': 'User name'
            },
            'age': {
                'type': 'integer',
                'minimum': 0,
                'maximum': 150
            },
            'tags': {
                'type': 'array',
                'items': {'type': 'string'}
            }
        },
        'required': ['name']
    }
    agent_run = AgentRun(dynamic_input_schema=schema_dict)
    
    assert isinstance(agent_run.dynamic_input_schema, JsonSchemaObject)
    assert agent_run.dynamic_input_schema.type == 'object'
    assert agent_run.dynamic_input_schema.properties
    assert 'name' in agent_run.dynamic_input_schema.properties
    assert 'age' in agent_run.dynamic_input_schema.properties
    assert 'tags' in agent_run.dynamic_input_schema.properties
    assert agent_run.dynamic_input_schema.required == ['name']


def test_agent_run_serialization():
    """Test AgentRun can be serialized"""
    context_data = {'key': 'value'}
    schema_dict = {'type': 'string'}
    
    agent_run = AgentRun(
        request_context=context_data,
        dynamic_input_schema=schema_dict
    )
    
    # Should be able to convert to dict
    data = agent_run.model_dump()
    assert 'request_context' in data
    assert 'dynamic_input_schema' in data
    assert 'dynamic_output_schema' in data
