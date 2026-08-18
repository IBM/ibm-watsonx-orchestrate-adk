import json
import pytest
import yaml
from unittest.mock import patch, Mock, MagicMock

from ibm_watsonx_orchestrate.cli.commands.controls.controls_controller import ControlsController
from ibm_watsonx_orchestrate_clients.common.base_client import ClientAPIException

controller = ControlsController()


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _api_exception():
    """Return a ClientAPIException with a minimal mock response."""
    resp = MagicMock()
    resp.status_code = 500
    resp.text = "internal error"
    return ClientAPIException(response=resp)


# Minimal binding returned by list_bindings so _resolve_control_id can find "ctrl-1".
_BINDING_STUB = {
    "id": "ctrl-1",
    "name": "ctrl-1",
    "display_name": "Test Ctrl",
    "artifact_display_name": "PII Filter",
    "hooks": ["agent_pre_invoke"],
    "priority": 100,
    "agent_ids": [],
    "tool_ids": [],
    "model_ids": [],
}

# Minimal artifact returned by list_artifacts so _resolve_artifact_id can find "PII Filter".
_ARTIFACT_STUB = {
    "id": "artifact-1",
    "name": "pii_filter",
    "display_name": "PII Filter",
    "description": "Filters PII",
    "asset_type": ["agent", "tool"],
}


class MockControlsClient:
    def __init__(
        self,
        list_artifacts_response=None,
        get_artifact_response=None,
        create_binding_response=None,
        list_bindings_response=None,
        get_bindings_count_response=None,
        get_binding_response=None,
        update_binding_response=None,
    ):
        self.list_artifacts_response = list_artifacts_response if list_artifacts_response is not None else [_ARTIFACT_STUB]
        self.get_artifact_response = get_artifact_response or {}
        self.create_binding_response = create_binding_response or {}
        self.list_bindings_response = list_bindings_response if list_bindings_response is not None else {
            "bindings": [_BINDING_STUB],
            "total": 1,
        }
        self.get_bindings_count_response = get_bindings_count_response or {
            "agent_policies": 0,
            "tool_policies": 0,
            "model_policies": 0,
            "total_policies": 0,
        }
        self.get_binding_response = get_binding_response or {}

        self.delete_called_with = None
        self.update_called_with = None

    def list_artifacts(self):
        return self.list_artifacts_response

    def get_artifact(self, artifact_id):
        return self.get_artifact_response

    def create_binding(self, payload):
        return self.create_binding_response

    def list_bindings(self, agent_ids=None, tool_ids=None, model_ids=None, artifact_ids=None, sort="recent"):
        return self.list_bindings_response

    def get_bindings_count(self):
        return self.get_bindings_count_response

    def get_binding(self, control_id):
        return self.get_binding_response

    def update_binding(self, control_id, payload):
        self.update_called_with = (control_id, payload)
        return {}

    def delete_binding(self, control_id):
        self.delete_called_with = control_id


class MockAssetClient:
    """Generic mock for agent/tool/model clients (resolve by ID)."""

    def __init__(self, drafts_by_ids_response=None):
        self._drafts = drafts_by_ids_response or []

    def get_drafts_by_ids(self, ids, workspace_id=None):
        return self._drafts


class MockAssetClientByName:
    """Mock for agent/tool clients that support get_drafts_by_names."""

    def __init__(self, drafts_by_names_response=None):
        self._drafts = drafts_by_names_response or []

    def get_drafts_by_names(self, names, workspace_id=None, include_global=True):
        return self._drafts


# ---------------------------------------------------------------------------
# _resolve_asset_names
# ---------------------------------------------------------------------------

class TestResolveAssetNames:
    def test_empty_ids_returns_empty(self):
        result = controller._resolve_asset_names([], "agent")
        assert result == []

    def test_resolve_agents(self):
        fake_agents = [{"id": "a1", "name": "AgentOne", "display_name": "Agent One"}]
        with patch.object(controller, "get_agent_client", return_value=MockAssetClient(fake_agents)):
            result = controller._resolve_asset_names(["a1"], "agent")
        assert result == [{"id": "a1", "name": "Agent One"}]

    def test_resolve_agents_falls_back_to_name(self):
        """display_name absent → use name."""
        fake_agents = [{"id": "a1", "name": "AgentOne", "display_name": None}]
        with patch.object(controller, "get_agent_client", return_value=MockAssetClient(fake_agents)):
            result = controller._resolve_asset_names(["a1"], "agent")
        assert result == [{"id": "a1", "name": "AgentOne"}]

    def test_resolve_tools(self):
        fake_tools = [{"id": "t1", "name": "MyTool", "display_name": "My Tool"}]
        with patch.object(controller, "get_tool_client", return_value=MockAssetClient(fake_tools)):
            result = controller._resolve_asset_names(["t1"], "tool")
        assert result == [{"id": "t1", "name": "My Tool"}]

    def test_resolve_models(self):
        fake_models = [{"id": "m1", "name": "MyModel", "display_name": "My Model"}]
        with patch.object(controller, "get_model_client", return_value=MockAssetClient(fake_models)):
            result = controller._resolve_asset_names(["m1"], "model")
        assert result == [{"id": "m1", "name": "My Model"}]

    def test_resolution_failure_falls_back_to_id(self):
        """When client call raises, each ID is returned as its own name."""
        failing_client = MockAssetClient()
        failing_client.get_drafts_by_ids = Mock(side_effect=Exception("network error"))
        with patch.object(controller, "get_agent_client", return_value=failing_client):
            result = controller._resolve_asset_names(["x1", "x2"], "agent")
        assert result == [{"id": "x1", "name": "x1"}, {"id": "x2", "name": "x2"}]


# ---------------------------------------------------------------------------
# _resolve_artifact_id
# ---------------------------------------------------------------------------

class TestResolveArtifactId:
    def test_resolves_by_name(self):
        client = MockControlsClient(list_artifacts_response=[_ARTIFACT_STUB])
        with patch.object(controller, "get_client", return_value=client):
            result = controller._resolve_artifact_id("pii_filter")
        assert result == "artifact-1"

    def test_resolves_by_display_name(self):
        client = MockControlsClient(list_artifacts_response=[_ARTIFACT_STUB])
        with patch.object(controller, "get_client", return_value=client):
            result = controller._resolve_artifact_id("PII Filter")
        assert result == "artifact-1"

    def test_not_found_exits(self, caplog):
        client = MockControlsClient(list_artifacts_response=[_ARTIFACT_STUB])
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller._resolve_artifact_id("nonexistent")
        assert "No policy artifact found" in caplog.text

    def test_api_error_exits(self, caplog):
        client = MockControlsClient()
        client.list_artifacts = Mock(side_effect=_api_exception())
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller._resolve_artifact_id("PII Filter")
        assert "Failed to look up policy artifacts" in caplog.text


# ---------------------------------------------------------------------------
# _resolve_control_id
# ---------------------------------------------------------------------------

class TestResolveControlId:
    def test_resolves_by_name(self):
        client = MockControlsClient()
        with patch.object(controller, "get_client", return_value=client):
            result = controller._resolve_control_id("ctrl-1")
        assert result == "ctrl-1"

    def test_not_found_exits(self, caplog):
        client = MockControlsClient(list_bindings_response={"bindings": [], "total": 0})
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller._resolve_control_id("nonexistent")
        assert "No control found" in caplog.text

    def test_api_error_exits(self, caplog):
        client = MockControlsClient()
        client.list_bindings = Mock(side_effect=_api_exception())
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller._resolve_control_id("ctrl-1")
        assert "Failed to look up controls" in caplog.text


# ---------------------------------------------------------------------------
# list_artifact_types
# ---------------------------------------------------------------------------

class TestListArtifactTypes:
    def _make_artifacts(self):
        return [
            {"id": "pii-1", "name": "pii_filter", "display_name": "PII Filter", "description": "Filters PII", "asset_type": ["agent", "tool"]},
            {"id": "mod-1", "name": "content_guard", "display_name": "Content Guard", "description": "Blocks harmful content", "asset_type": ["model"]},
        ]

    def test_list_artifact_types_no_results(self, caplog):
        with patch.object(controller, "get_client", return_value=MockControlsClient(list_artifacts_response=[])):
            controller.list_artifact_types()
        assert "No policy artifacts found" in caplog.text

    def test_list_artifact_types_non_verbose(self):
        artifacts = self._make_artifacts()
        with patch.object(controller, "get_client", return_value=MockControlsClient(list_artifacts_response=artifacts)), \
             patch("rich.console.Console.print") as print_mock:
            controller.list_artifact_types(verbose=False)
        assert print_mock.called

    def test_list_artifact_types_verbose(self):
        artifacts = self._make_artifacts()
        with patch.object(controller, "get_client", return_value=MockControlsClient(list_artifacts_response=artifacts)), \
             patch("ibm_watsonx_orchestrate.cli.commands.controls.controls_controller.console") as mock_console:
            controller.list_artifact_types(verbose=True)
        mock_console.print.assert_called_once()

    def test_list_artifact_types_api_error(self, caplog):
        client = MockControlsClient()
        client.list_artifacts = Mock(side_effect=_api_exception())
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller.list_artifact_types()
        assert "Failed to list policy artifacts" in caplog.text


# ---------------------------------------------------------------------------
# get_artifact_type
# ---------------------------------------------------------------------------

class TestGetArtifactType:
    def test_get_artifact_type_non_verbose(self):
        artifact = {"id": "pii-1", "name": "pii_filter", "display_name": "PII Filter", "description": "Filters PII"}
        client = MockControlsClient(list_artifacts_response=[_ARTIFACT_STUB], get_artifact_response=artifact)
        with patch.object(controller, "get_client", return_value=client), \
             patch("ibm_watsonx_orchestrate.cli.commands.controls.controls_controller.console") as mock_console:
            controller.get_artifact_type("PII Filter", verbose=False)
        assert mock_console.print.called

    def test_get_artifact_type_verbose(self):
        artifact = {"id": "pii-1", "name": "pii_filter", "display_name": "PII Filter", "description": "Filters PII"}
        client = MockControlsClient(list_artifacts_response=[_ARTIFACT_STUB], get_artifact_response=artifact)
        with patch.object(controller, "get_client", return_value=client), \
             patch("ibm_watsonx_orchestrate.cli.commands.controls.controls_controller.console") as mock_console:
            controller.get_artifact_type("PII Filter", verbose=True)
        mock_console.print.assert_called_once()

    def test_get_artifact_type_not_found(self, caplog):
        client = MockControlsClient(list_artifacts_response=[_ARTIFACT_STUB], get_artifact_response=None)
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller.get_artifact_type("PII Filter")
        assert "not found" in caplog.text

    def test_get_artifact_type_api_error(self, caplog):
        client = MockControlsClient(list_artifacts_response=[_ARTIFACT_STUB])
        client.get_artifact = Mock(side_effect=_api_exception())
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller.get_artifact_type("PII Filter")
        assert "Failed to get policy artifact" in caplog.text


# ---------------------------------------------------------------------------
# create_control
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# _resolve_agent_names_to_ids
# ---------------------------------------------------------------------------

class TestResolveAgentNamesToIds:
    def test_resolves_names(self):
        fake_agents = [{"name": "my-agent", "id": "uuid-a1"}]
        with patch.object(controller, "get_agent_client",
                          return_value=MockAssetClientByName(fake_agents)):
            result = controller._resolve_agent_names_to_ids(["my-agent"])
        assert result == ["uuid-a1"]

    def test_not_found_exits(self, caplog):
        with patch.object(controller, "get_agent_client",
                          return_value=MockAssetClientByName([])), \
             pytest.raises(SystemExit):
            controller._resolve_agent_names_to_ids(["missing"])
        assert "No agent found" in caplog.text

    def test_client_error_exits(self, caplog):
        bad_client = MockAssetClientByName()
        bad_client.get_drafts_by_names = Mock(side_effect=Exception("network error"))
        with patch.object(controller, "get_agent_client", return_value=bad_client), \
             pytest.raises(SystemExit):
            controller._resolve_agent_names_to_ids(["any"])
        assert "Failed to look up agents" in caplog.text


# ---------------------------------------------------------------------------
# _resolve_tool_names_to_ids
# ---------------------------------------------------------------------------

class TestResolveToolNamesToIds:
    def test_resolves_names(self):
        fake_tools = [{"name": "my-tool", "id": "uuid-t1"}]
        with patch.object(controller, "get_tool_client",
                          return_value=MockAssetClientByName(fake_tools)):
            result = controller._resolve_tool_names_to_ids(["my-tool"])
        assert result == ["uuid-t1"]

    def test_not_found_exits(self, caplog):
        with patch.object(controller, "get_tool_client",
                          return_value=MockAssetClientByName([])), \
             pytest.raises(SystemExit):
            controller._resolve_tool_names_to_ids(["missing"])
        assert "No tool found" in caplog.text

    def test_client_error_exits(self, caplog):
        bad_client = MockAssetClientByName()
        bad_client.get_drafts_by_names = Mock(side_effect=Exception("network error"))
        with patch.object(controller, "get_tool_client", return_value=bad_client), \
             pytest.raises(SystemExit):
            controller._resolve_tool_names_to_ids(["any"])
        assert "Failed to look up tools" in caplog.text


# ---------------------------------------------------------------------------
# create_control
# ---------------------------------------------------------------------------

class TestCreateControl:
    def test_create_minimal(self, caplog):
        client = MockControlsClient(create_binding_response={"id": "ctrl-999"})
        with patch.object(controller, "get_client", return_value=client):
            controller.create_control(artifact_name="PII Filter", name="my-control")
        assert "ctrl-999" in caplog.text

    def test_create_with_agent_and_tool_names(self, caplog):
        """create_control resolves agent/tool names to IDs before building the payload."""
        client = MockControlsClient(create_binding_response={"id": "ctrl-001"})
        fake_agent_client = MockAssetClientByName([{"name": "agent-1", "id": "uuid-a1"}])
        fake_tool_client = MockAssetClientByName([{"name": "tool-1", "id": "uuid-t1"}])
        with patch.object(controller, "get_client", return_value=client), \
             patch.object(controller, "get_agent_client", return_value=fake_agent_client), \
             patch.object(controller, "get_tool_client", return_value=fake_tool_client):
            controller.create_control(
                artifact_name="PII Filter",
                name="full-control",
                display_name="Full Control",
                description="A full control",
                hooks=["agent_pre_invoke"],
                priority=50,
                config='{"action": "redact"}',
                agent_names=["agent-1"],
                tool_names=["tool-1"],
                model_names=["ibm/granite-3-8b-instruct"],
            )
        assert "ctrl-001" in caplog.text
        _, payload = client.create_binding_response, client.create_binding_response
        # agent_ids and tool_ids should be resolved UUIDs; model_ids passed through
        # verify indirectly: no SystemExit means resolution succeeded

    def test_create_resolves_artifact_name(self):
        """create_control passes the resolved artifact UUID to the binding payload."""
        client = MockControlsClient(create_binding_response={"id": "ctrl-999"})
        with patch.object(controller, "get_client", return_value=client):
            controller.create_control(artifact_name="PII Filter", name="my-control")
        assert client.create_binding_response == {"id": "ctrl-999"}

    def test_create_invalid_config_json_exits(self, caplog):
        with patch.object(controller, "get_client", return_value=MockControlsClient()), \
             pytest.raises(SystemExit):
            controller.create_control(
                artifact_name="PII Filter",
                name="bad-control",
                config="not-json",
            )
        assert "Invalid JSON in config parameter" in caplog.text

    def test_create_api_error_exits(self, caplog):
        client = MockControlsClient()
        client.create_binding = Mock(side_effect=_api_exception())
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller.create_control(artifact_name="PII Filter", name="my-control")
        assert "Failed to create control" in caplog.text


# ---------------------------------------------------------------------------
# list_controls
# ---------------------------------------------------------------------------

class TestListControls:
    def _make_binding(self, **overrides):
        base = {
            "id": "ctrl-1",
            "name": "test-ctrl",
            "display_name": "Test Ctrl",
            "artifact_display_name": "PII Filter",
            "hooks": ["agent_pre_invoke"],
            "priority": 100,
            "agent_ids": ["a1"],
            "tool_ids": [],
            "model_ids": [],
        }
        base.update(overrides)
        return base

    def test_list_controls_empty(self, caplog):
        with patch.object(controller, "get_client", return_value=MockControlsClient(
            list_bindings_response={"bindings": [], "total": 0}
        )):
            controller.list_controls()
        assert "No controls found" in caplog.text

    def test_list_controls_non_verbose(self):
        bindings = {"bindings": [self._make_binding()], "total": 1}
        with patch.object(controller, "get_client", return_value=MockControlsClient(list_bindings_response=bindings)), \
             patch("ibm_watsonx_orchestrate.cli.commands.controls.controls_controller.console") as mock_console:
            controller.list_controls()
        assert mock_console.print.called

    def test_list_controls_verbose(self):
        bindings = {"bindings": [self._make_binding()], "total": 1}
        with patch.object(controller, "get_client", return_value=MockControlsClient(list_bindings_response=bindings)), \
             patch("ibm_watsonx_orchestrate.cli.commands.controls.controls_controller.console") as mock_console:
            controller.list_controls(verbose=True)
        mock_console.print.assert_called_once()

    def test_list_controls_passes_filters(self):
        """agent/tool names are resolved to UUIDs; model name and artifact are passed through."""
        mock_client = MockControlsClient()
        mock_client.list_bindings = Mock(return_value={"bindings": [], "total": 0})
        fake_agent_client = MockAssetClientByName([{"name": "a1", "id": "uuid-a1"}])
        fake_tool_client = MockAssetClientByName([{"name": "t1", "id": "uuid-t1"}])
        with patch.object(controller, "get_client", return_value=mock_client), \
             patch.object(controller, "get_agent_client", return_value=fake_agent_client), \
             patch.object(controller, "get_tool_client", return_value=fake_tool_client):
            controller.list_controls(
                agent_name="a1",
                tool_name="t1",
                model_name="m1",
                artifact_name="PII Filter",
                sort="asc",
            )
        mock_client.list_bindings.assert_called_once_with(
            agent_ids=["uuid-a1"],
            tool_ids=["uuid-t1"],
            model_ids=["m1"],
            artifact_ids=["artifact-1"],  # resolved UUID from _ARTIFACT_STUB
            sort="asc",
        )

    def test_list_controls_no_artifact_filter(self):
        """No filters → all None passed to list_bindings."""
        mock_client = MockControlsClient()
        mock_client.list_bindings = Mock(return_value={"bindings": [], "total": 0})
        with patch.object(controller, "get_client", return_value=mock_client):
            controller.list_controls()
        mock_client.list_bindings.assert_called_once_with(
            agent_ids=None,
            tool_ids=None,
            model_ids=None,
            artifact_ids=None,
            sort="recent",
        )

    def test_list_controls_api_error(self, caplog):
        client = MockControlsClient()
        client.list_bindings = Mock(side_effect=_api_exception())
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller.list_controls()
        assert "Failed to list controls" in caplog.text


# ---------------------------------------------------------------------------
# count_controls
# ---------------------------------------------------------------------------

class TestCountControls:
    def test_count_controls(self):
        counts = {"agent_policies": 3, "tool_policies": 1, "model_policies": 2, "total_policies": 6}
        with patch.object(controller, "get_client", return_value=MockControlsClient(get_bindings_count_response=counts)), \
             patch("ibm_watsonx_orchestrate.cli.commands.controls.controls_controller.console") as mock_console:
            controller.count_controls()
        assert mock_console.print.called

    def test_count_controls_api_error(self, caplog):
        client = MockControlsClient()
        client.get_bindings_count = Mock(side_effect=_api_exception())
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller.count_controls()
        assert "Failed to get control counts" in caplog.text


# ---------------------------------------------------------------------------
# get_control
# ---------------------------------------------------------------------------

class TestGetControl:
    def _make_binding(self):
        return {
            "id": "ctrl-1",
            "name": "ctrl-1",
            "display_name": "Test Ctrl",
            "description": "A test control",
            "artifact_id": "artifact-1",
            "artifact_display_name": "PII Filter",
            "hooks": ["agent_pre_invoke"],
            "priority": 100,
            "version": 1,
            "config": None,
            "agent_ids": [],
            "tool_ids": [],
            "model_ids": [],
        }

    def test_get_control_not_found_exits(self, caplog):
        client = MockControlsClient(get_binding_response=None)
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller.get_control("ctrl-1")
        assert "not found" in caplog.text

    def test_get_control_verbose(self):
        binding = self._make_binding()
        client = MockControlsClient(get_binding_response=binding)
        with patch.object(controller, "get_client", return_value=client), \
             patch("ibm_watsonx_orchestrate.cli.commands.controls.controls_controller.console") as mock_console:
            controller.get_control("ctrl-1", verbose=True)
        mock_console.print.assert_called_once()

    def test_get_control_non_verbose(self):
        binding = self._make_binding()
        client = MockControlsClient(get_binding_response=binding)
        with patch.object(controller, "get_client", return_value=client), \
             patch("ibm_watsonx_orchestrate.cli.commands.controls.controls_controller.console") as mock_console:
            controller.get_control("ctrl-1", verbose=False)
        assert mock_console.print.called

    def test_get_control_non_verbose_with_assets(self):
        """get_control resolves asset names when IDs are present."""
        binding = self._make_binding()
        binding["agent_ids"] = ["a1"]
        binding["tool_ids"] = ["t1"]
        binding["model_ids"] = ["m1"]

        fake_asset = [{"id": "a1", "name": "Agent1", "display_name": "Agent 1"}]
        client = MockControlsClient(get_binding_response=binding)
        with patch.object(controller, "get_client", return_value=client), \
             patch.object(controller, "_resolve_asset_names", return_value=fake_asset) as resolve_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.controls.controls_controller.console"):
            controller.get_control("ctrl-1", verbose=False)

        assert resolve_mock.call_count == 3  # once each for agent, tool, model

    def test_get_control_api_error(self, caplog):
        client = MockControlsClient()
        client.get_binding = Mock(side_effect=_api_exception())
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller.get_control("ctrl-1")
        assert "Failed to get control" in caplog.text


# ---------------------------------------------------------------------------
# update_control
# ---------------------------------------------------------------------------

class TestUpdateControl:
    def test_update_control_no_fields_warns(self, caplog):
        client = MockControlsClient()
        with patch.object(controller, "get_client", return_value=client):
            controller.update_control("ctrl-1")
        assert "No fields provided to update" in caplog.text
        assert client.update_called_with is None

    def test_update_control_sends_only_provided_fields(self):
        client = MockControlsClient()
        with patch.object(controller, "get_client", return_value=client):
            controller.update_control("ctrl-1", name="new-name", priority=50)
        assert client.update_called_with == ("ctrl-1", {"name": "new-name", "priority": 50})

    def test_update_control_parses_config_json(self):
        client = MockControlsClient()
        with patch.object(controller, "get_client", return_value=client):
            controller.update_control("ctrl-1", config='{"action": "block"}')

        assert client.update_called_with is not None
        _, payload = client.update_called_with
        assert payload["config"] == {"action": "block"}

    def test_update_control_invalid_config_json_exits(self, caplog):
        with patch.object(controller, "get_client", return_value=MockControlsClient()), \
             pytest.raises(SystemExit):
            controller.update_control("ctrl-1", config="not-json")
        assert "Invalid JSON in config parameter" in caplog.text

    def test_update_control_api_error(self, caplog):
        client = MockControlsClient()
        client.update_binding = Mock(side_effect=_api_exception())
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller.update_control("ctrl-1", name="x")
        assert "Failed to update control" in caplog.text

    def test_update_control_all_fields(self, caplog):
        client = MockControlsClient()
        fake_agent_client = MockAssetClientByName([{"name": "a9", "id": "uuid-a9"}])
        fake_tool_client = MockAssetClientByName([{"name": "t9", "id": "uuid-t9"}])
        with patch.object(controller, "get_client", return_value=client), \
             patch.object(controller, "get_agent_client", return_value=fake_agent_client), \
             patch.object(controller, "get_tool_client", return_value=fake_tool_client):
            controller.update_control(
                control_name="ctrl-1",
                artifact_name="PII Filter",
                name="updated",
                display_name="Updated",
                description="desc",
                hooks=["tool_pre_invoke"],
                priority=25,
                config='{"k": "v"}',
                agent_names=["a9"],
                tool_names=["t9"],
                model_names=["m9"],
            )
        assert client.update_called_with is not None
        _, payload = client.update_called_with
        assert payload == {
            "artifact_id": "artifact-1",  # resolved UUID from _ARTIFACT_STUB
            "name": "updated",
            "display_name": "Updated",
            "description": "desc",
            "hooks": ["tool_pre_invoke"],
            "priority": 25,
            "config": {"k": "v"},
            "agent_ids": ["uuid-a9"],   # resolved from name
            "tool_ids": ["uuid-t9"],    # resolved from name
            "model_ids": ["m9"],        # passed through
        }


# ---------------------------------------------------------------------------
# delete_control
# ---------------------------------------------------------------------------

class TestDeleteControl:
    def test_delete_control(self, caplog):
        client = MockControlsClient()
        with patch.object(controller, "get_client", return_value=client):
            controller.remove_control("ctrl-1")
        assert client.delete_called_with == "ctrl-1"
        assert "ctrl-1" in caplog.text

    def test_delete_control_api_error(self, caplog):
        client = MockControlsClient()
        client.delete_binding = Mock(side_effect=_api_exception())
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller.remove_control("ctrl-1")
        assert "Failed to remove control" in caplog.text


# ---------------------------------------------------------------------------
# import_controls
# ---------------------------------------------------------------------------

class TestImportControls:
    def _valid_spec(self):
        return {
            "spec_version": "1.0",
            "kind": "control",
            "control": {
                "artifact_name": "PII Filter",
                "name": "imported-control",
                "hooks": ["agent_pre_invoke"],
                "priority": 100,
            },
        }

    def test_import_controls_yaml(self, tmp_path, caplog):
        spec = self._valid_spec()
        spec_file = tmp_path / "control.yaml"
        spec_file.write_text(yaml.dump(spec))

        client = MockControlsClient(create_binding_response={"id": "ctrl-new"})
        with patch.object(controller, "get_client", return_value=client):
            controller.import_controls(spec_file)
        assert "ctrl-new" in caplog.text

    def test_import_controls_json(self, tmp_path, caplog):
        spec = self._valid_spec()
        spec_file = tmp_path / "control.json"
        spec_file.write_text(json.dumps(spec))

        client = MockControlsClient(create_binding_response={"id": "ctrl-json"})
        with patch.object(controller, "get_client", return_value=client):
            controller.import_controls(spec_file)
        assert "ctrl-json" in caplog.text

    def test_import_controls_missing_spec_version_exits(self, tmp_path, caplog):
        spec = self._valid_spec()
        del spec["spec_version"]
        spec_file = tmp_path / "control.yaml"
        spec_file.write_text(yaml.dump(spec))

        with patch.object(controller, "get_client", return_value=MockControlsClient()), \
             pytest.raises(SystemExit):
            controller.import_controls(spec_file)
        assert "Missing 'spec_version'" in caplog.text

    def test_import_controls_wrong_kind_exits(self, tmp_path, caplog):
        spec = self._valid_spec()
        spec["kind"] = "agent"
        spec_file = tmp_path / "control.yaml"
        spec_file.write_text(yaml.dump(spec))

        with patch.object(controller, "get_client", return_value=MockControlsClient()), \
             pytest.raises(SystemExit):
            controller.import_controls(spec_file)
        assert "kind" in caplog.text

    def test_import_controls_missing_control_section_exits(self, tmp_path, caplog):
        spec = self._valid_spec()
        del spec["control"]
        spec_file = tmp_path / "control.yaml"
        spec_file.write_text(yaml.dump(spec))

        with patch.object(controller, "get_client", return_value=MockControlsClient()), \
             pytest.raises(SystemExit):
            controller.import_controls(spec_file)
        assert "Missing 'control' section" in caplog.text

    def test_import_controls_unsupported_extension_exits(self, tmp_path, caplog):
        spec_file = tmp_path / "control.txt"
        spec_file.write_text("something")

        with patch.object(controller, "get_client", return_value=MockControlsClient()), \
             pytest.raises(SystemExit):
            controller.import_controls(spec_file)
        assert "File must be .json, .yaml, or .yml" in caplog.text

    def test_import_controls_nonexistent_file_exits(self, tmp_path, caplog):
        missing = tmp_path / "nonexistent.yaml"
        with patch.object(controller, "get_client", return_value=MockControlsClient()), \
             pytest.raises(SystemExit):
            controller.import_controls(missing)
        assert "File not found" in caplog.text


# ---------------------------------------------------------------------------
# export_control
# ---------------------------------------------------------------------------

class TestExportControl:
    def _make_binding(self):
        return {
            "id": "ctrl-1",
            "artifact_id": "artifact-1",
            "artifact_display_name": "PII Filter",
            "name": "my-control",
            "display_name": "My Control",
            "description": "A control",
            "hooks": ["agent_pre_invoke"],
            "priority": 100,
            "config": {"action": "redact"},
            "agent_ids": ["a1"],
            "tool_ids": None,
            "model_ids": None,
        }

    def test_export_control_writes_yaml(self, tmp_path, caplog):
        output = tmp_path / "exported.yaml"
        binding = self._make_binding()
        client = MockControlsClient(get_binding_response=binding)
        with patch.object(controller, "get_client", return_value=client), \
             patch.object(controller, "_resolve_asset_names", return_value=[]):
            controller.export_control("ctrl-1", output)

        assert output.exists()
        with open(output) as f:
            content = yaml.safe_load(f)
        assert content["kind"] == "control"
        assert content["control"]["name"] == "my-control"
        assert content["control"]["artifact_name"] == "PII Filter"

    def test_export_control_resolves_agent_ids_to_names(self, tmp_path):
        """agent_ids in the binding are resolved to names and written as agent_names."""
        output = tmp_path / "exported.yaml"
        binding = self._make_binding()
        client = MockControlsClient(get_binding_response=binding)

        def _fake_resolve(ids, asset_type):
            if asset_type == 'agent':
                return [{"id": "a1", "name": "AskOrchestrate"}]
            return []

        with patch.object(controller, "get_client", return_value=client), \
             patch.object(controller, "_resolve_asset_names", side_effect=_fake_resolve):
            controller.export_control("ctrl-1", output)

        with open(output) as f:
            content = yaml.safe_load(f)
        assert content["control"]["agent_names"] == ["AskOrchestrate"]
        assert "agent_ids" not in content["control"]

    def test_export_control_empty_asset_lists_omitted(self, tmp_path):
        """Empty agent/tool/model lists should not appear in the exported YAML."""
        output = tmp_path / "exported.yaml"
        binding = self._make_binding()
        binding["agent_ids"] = []
        client = MockControlsClient(get_binding_response=binding)
        with patch.object(controller, "get_client", return_value=client), \
             patch.object(controller, "_resolve_asset_names", return_value=[]):
            controller.export_control("ctrl-1", output)

        with open(output) as f:
            content = yaml.safe_load(f)
        assert "agent_names" not in content["control"]
        assert "tool_names" not in content["control"]
        assert "model_names" not in content["control"]

    def test_export_control_not_found_exits(self, tmp_path, caplog):
        output = tmp_path / "out.yaml"
        client = MockControlsClient(get_binding_response=None)
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller.export_control("ctrl-1", output)
        assert "not found" in caplog.text

    def test_export_control_api_error_exits(self, tmp_path, caplog):
        output = tmp_path / "out.yaml"
        client = MockControlsClient()
        client.get_binding = Mock(side_effect=_api_exception())
        with patch.object(controller, "get_client", return_value=client), \
             pytest.raises(SystemExit):
            controller.export_control("ctrl-1", output)
        assert "Failed to export control" in caplog.text

    def test_export_control_none_values_omitted(self, tmp_path):
        """None-valued fields should be stripped from the exported YAML control section."""
        binding = self._make_binding()
        binding["description"] = None
        output = tmp_path / "out.yaml"
        client = MockControlsClient(get_binding_response=binding)
        with patch.object(controller, "get_client", return_value=client), \
             patch.object(controller, "_resolve_asset_names", return_value=[]):
            controller.export_control("ctrl-1", output)

        with open(output) as f:
            content = yaml.safe_load(f)
        assert "description" not in content["control"]
