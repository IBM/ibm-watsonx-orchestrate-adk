"""
Unit tests for the schedulable_by_role field on Flow.

Covers FlowSpec field defaults, serialization behaviour, FlowFactory pass-through,
and the @flow decorator parameter.
"""

from unittest.mock import patch

import pytest

from ibm_watsonx_orchestrate.flow_builder.flows import FlowFactory
from ibm_watsonx_orchestrate.flow_builder.flows.flow import Flow
from ibm_watsonx_orchestrate.flow_builder.flows.decorators import flow
from ibm_watsonx_orchestrate.flow_builder.types import FlowSpec, UserRole


class TestSchedulableByRoleFlowSpec:
    """Tests for schedulable_by_role on FlowSpec directly."""

    def test_default_is_none(self):
        """schedulable_by_role defaults to None when not specified."""
        spec = FlowSpec(name="test")
        assert spec.schedulable_by_role is None

    def test_accepts_user(self):
        spec = FlowSpec(name="test", schedulable=True, schedulable_by_role="user")
        assert spec.schedulable_by_role == "user"

    def test_accepts_builder(self):
        spec = FlowSpec(name="test", schedulable=True, schedulable_by_role="builder")
        assert spec.schedulable_by_role == "builder"

    def test_accepts_admin(self):
        spec = FlowSpec(name="test", schedulable=True, schedulable_by_role="admin")
        assert spec.schedulable_by_role == "admin"

    def test_rejects_invalid_role(self):
        """Invalid role values should be rejected by Pydantic."""
        with pytest.raises(Exception):
            FlowSpec(name="test", schedulable_by_role="superuser")

    def test_serialized_when_set(self):
        """schedulable_by_role appears in to_json() output when set."""
        spec = FlowSpec(name="test", schedulable=True, schedulable_by_role="builder")
        result = spec.to_json()
        assert result["schedulable_by_role"] == "builder"

    def test_not_serialized_when_none(self):
        """schedulable_by_role is absent from to_json() output when None."""
        spec = FlowSpec(name="test", schedulable=True)
        result = spec.to_json()
        assert "schedulable_by_role" not in result

    @pytest.mark.parametrize("role", ["user", "builder", "admin"])
    def test_all_valid_roles_serialize_correctly(self, role):
        spec = FlowSpec(name="test", schedulable=True, schedulable_by_role=role)
        result = spec.to_json()
        assert result["schedulable_by_role"] == role


class TestSchedulableByRoleFlowFactory:
    """Tests for schedulable_by_role via FlowFactory.create_flow."""

    def setup_method(self):
        self._patch = patch(
            "ibm_watsonx_orchestrate.flow_builder.flows.flow.instantiate_client",
            return_value=None,
        )
        self._patch.start()

    def teardown_method(self):
        self._patch.stop()

    def test_default_is_none(self):
        flow = FlowFactory.create_flow(name="test_flow")
        assert flow.spec.schedulable_by_role is None

    def test_passes_through_builder(self):
        flow = FlowFactory.create_flow(
            name="test_flow", schedulable=True, schedulable_by_role="builder"
        )
        assert flow.spec.schedulable_by_role == "builder"

    def test_passes_through_admin(self):
        flow = FlowFactory.create_flow(
            name="test_flow", schedulable=True, schedulable_by_role="admin"
        )
        assert flow.spec.schedulable_by_role == "admin"

    def test_serialized_in_flow_json(self):
        f = FlowFactory.create_flow(
            name="test_flow", schedulable=True, schedulable_by_role="admin"
        )
        flow_json = f.to_json()
        assert flow_json["spec"]["schedulable_by_role"] == "admin"

    def test_absent_from_flow_json_when_not_set(self):
        f = FlowFactory.create_flow(name="test_flow", schedulable=True)
        flow_json = f.to_json()
        assert "schedulable_by_role" not in flow_json["spec"]

    def test_independent_of_schedulable_flag(self):
        """schedulable_by_role can be stored even if schedulable=False (no constraint in spec)."""
        f = FlowFactory.create_flow(
            name="test_flow", schedulable=False, schedulable_by_role="builder"
        )
        assert f.spec.schedulable_by_role == "builder"


class TestSchedulableByRoleDecorator:
    """Tests for schedulable_by_role via the @flow decorator."""

    def setup_method(self):
        self._patch = patch(
            "ibm_watsonx_orchestrate.flow_builder.flows.flow.instantiate_client",
            return_value=None,
        )
        self._patch.start()

    def teardown_method(self):
        self._patch.stop()

    def test_decorator_default_is_none(self):
        @flow(name="my_flow")
        def build(f: Flow) -> Flow:
            return f

        assert build.a_model.spec.schedulable_by_role is None

    def test_decorator_passes_builder_role(self):
        @flow(name="my_flow", schedulable=True, schedulable_by_role="builder")
        def build(f: Flow) -> Flow:
            return f

        assert build.a_model.spec.schedulable_by_role == "builder"

    def test_decorator_passes_admin_role(self):
        @flow(name="my_flow", schedulable=True, schedulable_by_role="admin")
        def build(f: Flow) -> Flow:
            return f

        assert build.a_model.spec.schedulable_by_role == "admin"

    def test_decorator_serialized_in_spec(self):
        @flow(name="my_flow", schedulable=True, schedulable_by_role="admin")
        def build(f: Flow) -> Flow:
            return f

        flow_json = build.a_model.to_json()
        assert flow_json["spec"]["schedulable_by_role"] == "admin"

    def test_decorator_absent_when_not_set(self):
        @flow(name="my_flow", schedulable=True)
        def build(f: Flow) -> Flow:
            return f

        flow_json = build.a_model.to_json()
        assert "schedulable_by_role" not in flow_json["spec"]
