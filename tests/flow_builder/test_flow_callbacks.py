"""
Unit tests for Flow callback functionality.

Tests the add_callback() method and callback serialization in flow specifications.
"""

from unittest.mock import patch

import pytest

from ibm_watsonx_orchestrate.agent_builder.tools.types import JsonSchemaObject, ToolPermission, ToolRequestBody, ToolSpec
from ibm_watsonx_orchestrate.flow_builder.flows import FlowFactory
from ibm_watsonx_orchestrate.flow_builder.flow_callback_types import FlowCallbackEventKind
from ibm_watsonx_orchestrate.flow_builder.utils import validate_callback_tool_schema


class TestFlowCallbacks:
    """Test suite for Flow callback functionality."""

    def setup_method(self):
        """Setup for each test method — disable tool-client so no HTTP calls are made."""
        self._instantiate_client_patch = patch(
            "ibm_watsonx_orchestrate.flow_builder.flows.flow.instantiate_client",
            return_value=None,
        )
        self._instantiate_client_patch.start()

    def teardown_method(self):
        """Cleanup after each test method."""
        self._instantiate_client_patch.stop()
    
    def test_add_callback_basic(self):
        """Test adding a single callback to a flow."""
        flow = FlowFactory.create_flow(name="test_flow")
        flow.add_callback(
            tool="my_callback_tool",
            events=[FlowCallbackEventKind.ON_FLOW_START]
        )
        
        flow_json = flow.to_json()
        assert len(flow_json["spec"]["callbacks"]) == 1
        assert flow_json["spec"]["callbacks"][0]["tool"] == "my_callback_tool"
        assert flow_json["spec"]["callbacks"][0]["events"] == ["flow:on_flow_start"]
    
    def test_add_callback_multiple_events(self):
        """Test callback with multiple event types."""
        flow = FlowFactory.create_flow(name="test_flow")
        flow.add_callback(
            tool="monitoring_tool",
            events=[
                FlowCallbackEventKind.ON_FLOW_START,
                FlowCallbackEventKind.ON_FLOW_END,
                FlowCallbackEventKind.ON_FLOW_ERROR
            ]
        )
        
        flow_json = flow.to_json()
        callback = flow_json["spec"]["callbacks"][0]
        assert len(callback["events"]) == 3
        assert "flow:on_flow_start" in callback["events"]
        assert "flow:on_flow_end" in callback["events"]
        assert "flow:on_flow_error" in callback["events"]
    
    def test_add_callback_with_batch_interval(self):
        """Test callback with custom batch interval."""
        flow = FlowFactory.create_flow(name="test_flow")
        flow.add_callback(
            tool="batch_tool",
            events=[FlowCallbackEventKind.ON_TASK_MESSAGE],
            batch_interval=5000
        )
        
        flow_json = flow.to_json()
        callback = flow_json["spec"]["callbacks"][0]
        assert callback["batch_interval"] == 5000
    
    def test_add_callback_without_batch_interval(self):
        """Test callback without batch interval (should be None/omitted)."""
        flow = FlowFactory.create_flow(name="test_flow")
        flow.add_callback(
            tool="no_batch_tool",
            events=[FlowCallbackEventKind.ON_FLOW_START]
        )
        
        flow_json = flow.to_json()
        callback = flow_json["spec"]["callbacks"][0]
        # batch_interval should either be None or not present in the JSON
        assert callback.get("batch_interval") is None
    
    def test_add_multiple_callbacks(self):
        """Test adding multiple callbacks to the same flow."""
        flow = FlowFactory.create_flow(name="test_flow")
        flow.add_callback(
            tool="callback1",
            events=[FlowCallbackEventKind.ON_FLOW_START]
        )
        flow.add_callback(
            tool="callback2",
            events=[FlowCallbackEventKind.ON_FLOW_END]
        )
        
        flow_json = flow.to_json()
        assert len(flow_json["spec"]["callbacks"]) == 2
        assert flow_json["spec"]["callbacks"][0]["tool"] == "callback1"
        assert flow_json["spec"]["callbacks"][1]["tool"] == "callback2"
    
    def test_add_callback_method_chaining(self):
        """Test that add_callback returns self for method chaining."""
        flow = FlowFactory.create_flow(name="test_flow")
        result = flow.add_callback(
            tool="tool1",
            events=[FlowCallbackEventKind.ON_FLOW_START]
        ).add_callback(
            tool="tool2",
            events=[FlowCallbackEventKind.ON_FLOW_END]
        )
        
        assert result is flow
        flow_json = flow.to_json()
        assert len(flow_json["spec"]["callbacks"]) == 2
    
    def test_add_callback_tool_formats(self):
        """Test different tool identifier formats."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        # Simple tool name
        flow.add_callback(
            tool="simple_tool",
            events=[FlowCallbackEventKind.ON_FLOW_START]
        )
        
        # Toolkit:tool format
        flow.add_callback(
            tool="my_toolkit:my_tool",
            events=[FlowCallbackEventKind.ON_FLOW_END]
        )
        
        # Toolkit:tool:uuid format
        flow.add_callback(
            tool="my_toolkit:my_tool:123e4567-e89b-12d3-a456-426614174000",
            events=[FlowCallbackEventKind.ON_FLOW_ERROR]
        )
        
        flow_json = flow.to_json()
        assert len(flow_json["spec"]["callbacks"]) == 3
        assert flow_json["spec"]["callbacks"][0]["tool"] == "simple_tool"
        assert flow_json["spec"]["callbacks"][1]["tool"] == "my_toolkit:my_tool"
        assert "123e4567-e89b-12d3-a456-426614174000" in flow_json["spec"]["callbacks"][2]["tool"]
    
    def test_add_callback_all_event_types(self):
        """Test callback with all available event types."""
        flow = FlowFactory.create_flow(name="test_flow")
        flow.add_callback(
            tool="comprehensive_tool",
            events=[
                FlowCallbackEventKind.ON_FLOW_START,
                FlowCallbackEventKind.ON_FLOW_END,
                FlowCallbackEventKind.ON_FLOW_ERROR,
                FlowCallbackEventKind.ON_TASK_WAIT,
                FlowCallbackEventKind.ON_TASK_ERROR,
                FlowCallbackEventKind.ON_TASK_MESSAGE
            ]
        )
        
        flow_json = flow.to_json()
        callback = flow_json["spec"]["callbacks"][0]
        assert len(callback["events"]) == 6
        # Verify all event types are present
        expected_events = [
            "flow:on_flow_start",
            "flow:on_flow_end",
            "flow:on_flow_error",
            "task:on_task_wait",
            "task:on_task_error",
            "task:on_task_message"
        ]
        for event in expected_events:
            assert event in callback["events"]
    
    def test_callback_serialization(self):
        """Test that callbacks are properly serialized in flow spec."""
        flow = FlowFactory.create_flow(name="test_flow")
        flow.add_callback(
            tool="test_tool",
            events=[FlowCallbackEventKind.ON_FLOW_START],
            batch_interval=1000
        )
        
        # Test to_json
        flow_json = flow.to_json()
        assert "callbacks" in flow_json["spec"]
        
        # Test that FlowCallback.to_json() is called correctly
        callback = flow_json["spec"]["callbacks"][0]
        assert isinstance(callback, dict)
        assert "tool" in callback
        assert "events" in callback
        assert "batch_interval" in callback
    
    def test_add_callback_task_events(self):
        """Test callback with task-specific events."""
        flow = FlowFactory.create_flow(name="test_flow")
        flow.add_callback(
            tool="task_monitor",
            events=[
                FlowCallbackEventKind.ON_TASK_WAIT,
                FlowCallbackEventKind.ON_TASK_ERROR,
                FlowCallbackEventKind.ON_TASK_MESSAGE
            ]
        )
        
        flow_json = flow.to_json()
        callback = flow_json["spec"]["callbacks"][0]
        assert len(callback["events"]) == 3
        assert "task:on_task_wait" in callback["events"]
        assert "task:on_task_error" in callback["events"]
        assert "task:on_task_message" in callback["events"]
    
    def test_add_callback_flow_events(self):
        """Test callback with flow-specific events."""
        flow = FlowFactory.create_flow(name="test_flow")
        flow.add_callback(
            tool="flow_monitor",
            events=[
                FlowCallbackEventKind.ON_FLOW_START,
                FlowCallbackEventKind.ON_FLOW_END,
                FlowCallbackEventKind.ON_FLOW_ERROR
            ]
        )
        
        flow_json = flow.to_json()
        callback = flow_json["spec"]["callbacks"][0]
        assert len(callback["events"]) == 3
        assert "flow:on_flow_start" in callback["events"]
        assert "flow:on_flow_end" in callback["events"]
        assert "flow:on_flow_error" in callback["events"]
    
    def test_callbacks_empty_by_default(self):
        """Test that a flow has no callbacks by default."""
        flow = FlowFactory.create_flow(name="test_flow")
        flow_json = flow.to_json()
        
        # Callbacks may not be present in spec if empty, or be an empty list
        # This is acceptable behavior - callbacks are only serialized when present
        callbacks = flow_json["spec"].get("callbacks", [])
        assert isinstance(callbacks, list)
        assert len(callbacks) == 0
    
    def test_add_callback_with_nodes(self):
        """Test that callbacks work correctly when flow has nodes."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        # Add some nodes to the flow
        flow.start(name="start_node")
        flow.end(name="end_node")
        
        # Add callback
        flow.add_callback(
            tool="callback_with_nodes",
            events=[FlowCallbackEventKind.ON_FLOW_START]
        )
        
        flow_json = flow.to_json()
        assert len(flow_json["spec"]["callbacks"]) == 1
        assert flow_json["spec"]["callbacks"][0]["tool"] == "callback_with_nodes"
        # Verify nodes are still present
        assert "nodes" in flow_json
    
    def test_add_callback_preserves_order(self):
        """Test that callbacks are added in the order they are called."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        flow.add_callback(tool="first", events=[FlowCallbackEventKind.ON_FLOW_START])
        flow.add_callback(tool="second", events=[FlowCallbackEventKind.ON_FLOW_END])
        flow.add_callback(tool="third", events=[FlowCallbackEventKind.ON_FLOW_ERROR])
        
        flow_json = flow.to_json()
        assert len(flow_json["spec"]["callbacks"]) == 3
        assert flow_json["spec"]["callbacks"][0]["tool"] == "first"
        assert flow_json["spec"]["callbacks"][1]["tool"] == "second"
        assert flow_json["spec"]["callbacks"][2]["tool"] == "third"
    
    def test_add_callback_single_event(self):
        """Test callback with a single event in the list."""
        flow = FlowFactory.create_flow(name="test_flow")
        flow.add_callback(
            tool="single_event_tool",
            events=[FlowCallbackEventKind.ON_FLOW_END]
        )
        
        flow_json = flow.to_json()
        callback = flow_json["spec"]["callbacks"][0]
        assert len(callback["events"]) == 1
        assert callback["events"][0] == "flow:on_flow_end"
    
    def test_add_callback_with_batch_interval_zero(self):
        """Test callback with batch_interval set to 0."""
        flow = FlowFactory.create_flow(name="test_flow")
        flow.add_callback(
            tool="zero_batch_tool",
            events=[FlowCallbackEventKind.ON_TASK_MESSAGE],
            batch_interval=0
        )
        
        flow_json = flow.to_json()
        callback = flow_json["spec"]["callbacks"][0]
        assert callback["batch_interval"] == 0


def test_validate_callback_tool_schema_accepts_items_without_event():
    tool_spec = ToolSpec(
        name="callback_tool",
        description="callback tool",
        permission=ToolPermission.READ_ONLY,
        binding={"openapi": {"http_method": "POST", "http_path": "/callback", "servers": ["test"]}},
        input_schema=ToolRequestBody(
            type="object",
            properties={
                "events": JsonSchemaObject(
                    type="array",
                    items=JsonSchemaObject(
                        type="object",
                        properties={
                            "output": JsonSchemaObject(type="object")
                        }
                    )
                )
            }
        )
    )

    validate_callback_tool_schema(tool_spec, "callback_tool")


def test_validate_callback_tool_schema_accepts_event_object_with_empty_properties():
    tool_spec = ToolSpec(
        name="callback_tool",
        description="callback tool",
        permission=ToolPermission.READ_ONLY,
        binding={"openapi": {"http_method": "POST", "http_path": "/callback", "servers": ["test"]}},
        input_schema=ToolRequestBody(
            type="object",
            properties={
                "events": JsonSchemaObject(
                    type="array",
                    description="Array of event objects for batched delivery",
                    items=JsonSchemaObject(
                        type="object",
                        properties={
                            "event": JsonSchemaObject(
                                type="object",
                                description="",
                                properties={}
                            )
                        }
                    )
                )
            }
        )
    )

    validate_callback_tool_schema(tool_spec, "callback_tool")


def test_validate_callback_tool_schema_accepts_event_items_with_additional_properties():
    tool_spec = ToolSpec(
        name="callback_tool",
        description="callback tool",
        permission=ToolPermission.READ_ONLY,
        binding={"openapi": {"http_method": "POST", "http_path": "/callback", "servers": ["test"]}},
        input_schema=ToolRequestBody(
            type="object",
            properties={
                "events": JsonSchemaObject(
                    type="array",
                    title="Events",
                    items=JsonSchemaObject(
                        type="object",
                        additionalProperties=True
                    )
                )
            },
            required=["events"]
        )
    )

    validate_callback_tool_schema(tool_spec, "callback_tool")


def test_validate_callback_tool_schema_rejects_non_object_event_when_present():
    tool_spec = ToolSpec(
        name="callback_tool",
        description="callback tool",
        permission=ToolPermission.READ_ONLY,
        binding={"openapi": {"http_method": "POST", "http_path": "/callback", "servers": ["test"]}},
        input_schema=ToolRequestBody(
            type="object",
            properties={
                "events": JsonSchemaObject(
                    type="array",
                    items=JsonSchemaObject(
                        type="object",
                        properties={
                            "event": JsonSchemaObject(type="string")
                        }
                    )
                )
            }
        )
    )

    with pytest.raises(ValueError, match="event field must be an object schema"):
        validate_callback_tool_schema(tool_spec, "callback_tool")


def test_validate_callback_tool_schema_rejects_event_missing_required_fields():
    tool_spec = ToolSpec(
        name="callback_tool",
        description="callback tool",
        permission=ToolPermission.READ_ONLY,
        binding={"openapi": {"http_method": "POST", "http_path": "/callback", "servers": ["test"]}},
        input_schema=ToolRequestBody(
            type="object",
            properties={
                "events": JsonSchemaObject(
                    type="array",
                    items=JsonSchemaObject(
                        type="object",
                        properties={
                            "event": JsonSchemaObject(
                                type="object",
                                properties={
                                    "kind": JsonSchemaObject(type="string")
                                }
                            )
                        }
                    )
                )
            }
        )
    )

    with pytest.raises(ValueError, match="event metadata is missing required fields"):
        validate_callback_tool_schema(tool_spec, "callback_tool")
