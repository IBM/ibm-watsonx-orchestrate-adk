"""
Unit tests for Parallel flow functionality.

Tests the parallel() and parallel_conditions() methods, ParallelSpec class,
and the Parallel flow class including condition handling and serialization.
"""

import pytest
from pydantic import BaseModel

from ibm_watsonx_orchestrate.flow_builder.flows import FlowFactory
from ibm_watsonx_orchestrate.flow_builder.types import (
    ParallelSpec,
    Conditions,
    NodeIdCondition,
)


class ParallelFlowInput(BaseModel):
    """Test input schema for parallel flows."""
    priority: str
    category: str
    value: int


class ParallelFlowOutput(BaseModel):
    """Test output schema for parallel flows."""
    result: str
    processed: bool


class TestParallelSpec:
    """Test suite for ParallelSpec class."""
    
    def test_parallel_spec_initialization(self):
        """Test ParallelSpec can be initialized with basic parameters."""
        spec = ParallelSpec(
            name="test_parallel",
            display_name="Test Parallel",
            evaluator=None
        )
        
        assert spec.name == "test_parallel"
        assert spec.display_name == "Test Parallel"
        assert spec.kind == "parallel"
        assert spec.evaluator is None
    
    def test_parallel_spec_with_evaluator(self):
        """Test ParallelSpec with Conditions evaluator."""
        conditions = Conditions(conditions=[
            NodeIdCondition(expression="flow.input.priority == 'high'", node_id="node1", default=False)
        ])
        
        spec = ParallelSpec(
            name="test_parallel",
            display_name="Test Parallel",
            evaluator=conditions
        )
        
        assert spec.evaluator is not None
        assert isinstance(spec.evaluator, Conditions)
        assert len(spec.evaluator.conditions) == 1
    
    def test_parallel_spec_to_json_without_evaluator(self):
        """Test ParallelSpec serialization when evaluator is None."""
        spec = ParallelSpec(
            name="test_parallel",
            display_name="Test Parallel",
            evaluator=None
        )
        
        json_output = spec.to_json()
        
        assert json_output["name"] == "test_parallel"
        assert json_output["kind"] == "parallel"
        # evaluator should not be in JSON when None
        assert "evaluator" not in json_output
    
    def test_parallel_spec_to_json_with_empty_conditions(self):
        """Test ParallelSpec serialization with empty Conditions."""
        conditions = Conditions(conditions=[])
        spec = ParallelSpec(
            name="test_parallel",
            display_name="Test Parallel",
            evaluator=conditions
        )
        
        json_output = spec.to_json()
        
        # evaluator should not be in JSON when conditions list is empty
        assert "evaluator" not in json_output
    
    def test_parallel_spec_to_json_with_conditions(self):
        """Test ParallelSpec serialization with actual conditions."""
        conditions = Conditions(conditions=[
            NodeIdCondition(expression="flow.input.priority == 'high'", node_id="node1", default=False),
            NodeIdCondition(expression="flow.input.category == 'billing'", node_id="node2", default=False)
        ])
        
        spec = ParallelSpec(
            name="test_parallel",
            display_name="Test Parallel",
            evaluator=conditions
        )
        
        json_output = spec.to_json()
        
        assert "evaluator" in json_output
        assert "conditions" in json_output["evaluator"]
        assert len(json_output["evaluator"]["conditions"]) == 2


class TestParallelFlow:
    """Test suite for Parallel flow functionality."""
    
    def test_parallel_basic_creation(self):
        """Test creating a basic parallel flow."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel(
            evaluator=None,
            name="test_parallel"
        )
        
        assert parallel is not None
        assert parallel.spec.name == "test_parallel"
        assert parallel.spec.kind == "parallel"
    
    def test_parallel_with_schemas(self):
        """Test creating parallel flow with input/output schemas."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel(
            evaluator=None,
            input_schema=ParallelFlowInput,
            output_schema=ParallelFlowOutput,
            name="test_parallel"
        )
        
        assert parallel.spec.input_schema is not None
        assert parallel.spec.output_schema is not None
    
    def test_parallel_auto_generated_name(self):
        """Test that parallel flow auto-generates name when not provided."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel(evaluator=None)
        
        assert parallel.spec.name.startswith("parallel_")
    
    def test_parallel_with_display_name(self):
        """Test parallel flow with custom display name."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel(
            evaluator=None,
            name="test_parallel",
            display_name="Test Parallel Flow"
        )
        
        assert parallel.spec.name == "test_parallel"
        assert parallel.spec.display_name == "Test Parallel Flow"
    
    def test_parallel_with_conditions_list(self):
        """Test creating parallel flow with list of conditions."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        conditions = Conditions(conditions=[
            NodeIdCondition(expression="flow.input.priority == 'high'", node_id="node1", default=False)
        ])
        
        parallel = flow.parallel(
            evaluator=conditions,
            name="test_parallel"
        )
        
        spec = parallel.get_spec()
        assert spec.evaluator is not None
        assert isinstance(spec.evaluator, Conditions)
        assert len(spec.evaluator.conditions) == 1


class TestParallelConditions:
    """Test suite for parallel_conditions() method."""
    
    def test_parallel_conditions_basic(self):
        """Test creating parallel flow using parallel_conditions()."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel_conditions(name="test_parallel")
        
        assert parallel is not None
        assert parallel.spec.name == "test_parallel"
        assert parallel.spec.kind == "parallel"
    
    def test_parallel_conditions_auto_name(self):
        """Test parallel_conditions auto-generates name."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel_conditions()
        
        assert parallel.spec.name.startswith("parallel_")
    
    def test_parallel_conditions_with_schemas(self):
        """Test parallel_conditions with input/output schemas."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel_conditions(
            name="test_parallel",
            input_schema=ParallelFlowInput,
            output_schema=ParallelFlowOutput
        )
        
        assert parallel.spec.input_schema is not None
        assert parallel.spec.output_schema is not None
    
    def test_parallel_conditions_starts_with_no_evaluator(self):
        """Test that parallel_conditions starts with None evaluator."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel_conditions(name="test_parallel")
        spec = parallel.get_spec()
        
        # Initially evaluator should be None
        assert spec.evaluator is None


class TestParallelConditionMethod:
    """Test suite for Parallel.condition() method."""
    
    def test_add_single_condition(self):
        """Test adding a single condition to parallel flow."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel_conditions(name="test_parallel")
        # Create node within the parallel subflow
        node1 = parallel.start(name="node1")
        
        parallel.condition(
            expression="flow.input.priority == 'high'",
            to_node=node1
        )
        
        spec = parallel.get_spec()
        assert spec.evaluator is not None
        assert isinstance(spec.evaluator, Conditions)
        assert len(spec.evaluator.conditions) == 1
    
    def test_add_multiple_conditions(self):
        """Test adding multiple conditions to parallel flow."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel_conditions(name="test_parallel")
        # Create nodes within the parallel subflow
        node1 = parallel.start(name="node1")
        node2 = parallel.start(name="node2")
        node3 = parallel.start(name="node3")
        
        parallel.condition(
            expression="flow.input.priority == 'high'",
            to_node=node1
        ).condition(
            expression="flow.input.category == 'billing'",
            to_node=node2
        ).condition(
            expression="flow.input.value > 100",
            to_node=node3
        )
        
        spec = parallel.get_spec()
        assert spec.evaluator is not None
        assert len(spec.evaluator.conditions) == 3
    
    def test_add_default_condition(self):
        """Test adding a default condition to parallel flow."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel_conditions(name="test_parallel")
        # Create nodes within the parallel subflow
        node1 = parallel.start(name="node1")
        default_node = parallel.start(name="default_node")
        
        parallel.condition(
            expression="flow.input.priority == 'high'",
            to_node=node1
        ).condition(
            default=True,
            to_node=default_node
        )
        
        spec = parallel.get_spec()
        assert spec.evaluator is not None
        assert len(spec.evaluator.conditions) == 2
        # Check that last condition is default
        assert spec.evaluator.conditions[1].default is True
    
    def test_condition_method_chaining(self):
        """Test that condition() returns self for method chaining."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel_conditions(name="test_parallel")
        # Create nodes within the parallel subflow
        node1 = parallel.start(name="node1")
        node2 = parallel.start(name="node2")
        
        result = parallel.condition(
            expression="flow.input.priority == 'high'",
            to_node=node1
        ).condition(
            expression="flow.input.category == 'billing'",
            to_node=node2
        )
        
        assert result is parallel
    
    def test_condition_creates_edge(self):
        """Test that condition() creates an edge from START to target node."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel_conditions(name="test_parallel")
        # Create node within the parallel subflow
        node1 = parallel.start(name="node1")
        
        parallel.condition(
            expression="flow.input.priority == 'high'",
            to_node=node1
        )
        
        # Verify edge was created (check in parallel's edges)
        parallel_json = parallel.to_json()
        assert "edges" in parallel_json
        # Should have at least one edge from START
        edges = parallel_json.get("edges", [])
        assert len(edges) > 0


class TestParallelSerialization:
    """Test suite for Parallel flow serialization."""
    
    def test_parallel_to_json_basic(self):
        """Test basic parallel flow serialization."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel_conditions(name="test_parallel")
        json_output = parallel.to_json()
        
        # Check spec contains the name and kind
        assert "spec" in json_output
        assert json_output["spec"]["name"] == "test_parallel"
        assert json_output["spec"]["kind"] == "parallel"
    
    def test_parallel_to_json_with_conditions(self):
        """Test parallel flow serialization with conditions."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel_conditions(name="test_parallel")
        # Create nodes within the parallel subflow
        node1 = parallel.start(name="node1")
        node2 = parallel.start(name="node2")
        
        parallel.condition(
            expression="flow.input.priority == 'high'",
            to_node=node1
        ).condition(
            expression="flow.input.category == 'billing'",
            to_node=node2
        )
        
        json_output = parallel.to_json()
        
        assert "spec" in json_output
        assert "evaluator" in json_output["spec"]
        assert len(json_output["spec"]["evaluator"]["conditions"]) == 2
    
    def test_parallel_in_parent_flow_json(self):
        """Test that parallel flow appears correctly in parent flow JSON."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel_conditions(name="test_parallel")
        flow_json = flow.to_json()
        
        # Nodes is a dictionary with node names as keys
        nodes = flow_json.get("nodes", {})
        assert "test_parallel" in nodes
        
        parallel_node = nodes["test_parallel"]
        assert parallel_node["spec"]["kind"] == "parallel"
        assert parallel_node["spec"]["name"] == "test_parallel"


class TestParallelEdgeCases:
    """Test suite for edge cases and error handling."""
    
    def test_parallel_with_none_evaluator_serializes_correctly(self):
        """Test that parallel with None evaluator serializes without evaluator field."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel(evaluator=None, name="test_parallel")
        json_output = parallel.to_json()
        
        # evaluator should not be in spec when None
        assert "evaluator" not in json_output["spec"]
    
    def test_parallel_spec_docstring_exists(self):
        """Test that ParallelSpec has proper documentation."""
        assert ParallelSpec.__doc__ is not None
        assert "ParallelSpec represents the specification of a parallel subflow" in ParallelSpec.__doc__
    
    def test_parallel_get_spec_returns_correct_type(self):
        """Test that get_spec() returns ParallelSpec instance."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel = flow.parallel_conditions(name="test_parallel")
        spec = parallel.get_spec()
        
        assert isinstance(spec, ParallelSpec)
    
    def test_multiple_parallel_flows_in_same_flow(self):
        """Test creating multiple parallel flows in the same parent flow."""
        flow = FlowFactory.create_flow(name="test_flow")
        
        parallel1 = flow.parallel_conditions(name="parallel1")
        parallel2 = flow.parallel_conditions(name="parallel2")
        
        assert parallel1.spec.name == "parallel1"
        assert parallel2.spec.name == "parallel2"
        
        flow_json = flow.to_json()
        nodes = flow_json.get("nodes", {})
        
        # Check both parallel nodes exist in the nodes dictionary
        assert "parallel1" in nodes
        assert "parallel2" in nodes
        
        # Verify they are both parallel kind
        assert nodes["parallel1"]["spec"]["kind"] == "parallel"
        assert nodes["parallel2"]["spec"]["kind"] == "parallel"

