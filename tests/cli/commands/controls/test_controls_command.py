from pathlib import Path
from unittest.mock import patch

from ibm_watsonx_orchestrate.cli.commands.controls import controls_command


class TestCreateControl:
    def test_create_control_minimal(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.create_control"
        ) as mock:
            controls_command.create_control(
                artifact_name="PII Filter",
                name="pii-protection",
            )
            mock.assert_called_once_with(
                artifact_name="PII Filter",
                name="pii-protection",
                display_name=None,
                description=None,
                hooks=None,
                priority=100,
                config=None,
                agent_names=None,
                tool_names=None,
                model_names=None,
            )

    def test_create_control_all_params(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.create_control"
        ) as mock:
            controls_command.create_control(
                artifact_name="PII Filter",
                name="pii-protection",
                display_name="PII Protection",
                description="Redacts PII from agent responses",
                hooks=["agent_pre_invoke", "agent_post_invoke"],
                priority=50,
                config='{"action": "redact"}',
                agent_names=["agent-1", "agent-2"],
                tool_names=["tool-1"],
                model_names=["model-1"],
            )
            mock.assert_called_once_with(
                artifact_name="PII Filter",
                name="pii-protection",
                display_name="PII Protection",
                description="Redacts PII from agent responses",
                hooks=["agent_pre_invoke", "agent_post_invoke"],
                priority=50,
                config='{"action": "redact"}',
                agent_names=["agent-1", "agent-2"],
                tool_names=["tool-1"],
                model_names=["model-1"],
            )

    def test_create_control_default_priority(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.create_control"
        ) as mock:
            controls_command.create_control(
                artifact_name="Content Guardrails",
                name="my-control",
            )
            mock.assert_called_once_with(
                artifact_name="Content Guardrails",
                name="my-control",
                display_name=None,
                description=None,
                hooks=None,
                priority=100,
                config=None,
                agent_names=None,
                tool_names=None,
                model_names=None,
            )


class TestListControls:
    def test_list_controls_no_filters(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.list_controls"
        ) as mock:
            controls_command.list_controls()
            mock.assert_called_once_with(
                agent_name=None,
                tool_name=None,
                model_name=None,
                artifact_name=None,
                sort="recent",
                verbose=False,
            )

    def test_list_controls_with_agent_filter(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.list_controls"
        ) as mock:
            controls_command.list_controls(agent_name="my-agent")
            mock.assert_called_once_with(
                agent_name="my-agent",
                tool_name=None,
                model_name=None,
                artifact_name=None,
                sort="recent",
                verbose=False,
            )

    def test_list_controls_verbose(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.list_controls"
        ) as mock:
            controls_command.list_controls(verbose=True)
            mock.assert_called_once_with(
                agent_name=None,
                tool_name=None,
                model_name=None,
                artifact_name=None,
                sort="recent",
                verbose=True,
            )

    def test_list_controls_with_sort(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.list_controls"
        ) as mock:
            controls_command.list_controls(sort="asc")
            mock.assert_called_once_with(
                agent_name=None,
                tool_name=None,
                model_name=None,
                artifact_name=None,
                sort="asc",
                verbose=False,
            )

    def test_list_controls_all_filters(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.list_controls"
        ) as mock:
            controls_command.list_controls(
                agent_name="agent-1",
                tool_name="tool-1",
                model_name="model-1",
                artifact_name="PII Filter",
                sort="desc",
                verbose=True,
            )
            mock.assert_called_once_with(
                agent_name="agent-1",
                tool_name="tool-1",
                model_name="model-1",
                artifact_name="PII Filter",
                sort="desc",
                verbose=True,
            )


class TestCountControls:
    def test_count_controls(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.count_controls"
        ) as mock:
            controls_command.count_controls()
            mock.assert_called_once_with()


class TestGetControl:
    def test_get_control_non_verbose(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.get_control"
        ) as mock:
            controls_command.get_control(control_name="my_control_06650U")
            mock.assert_called_once_with("my_control_06650U", False)

    def test_get_control_verbose(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.get_control"
        ) as mock:
            controls_command.get_control(control_name="my_control_06650U", verbose=True)
            mock.assert_called_once_with("my_control_06650U", True)


class TestUpdateControl:
    def test_update_control_minimal(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.update_control"
        ) as mock:
            controls_command.update_control(control_name="my_control_06650U")
            mock.assert_called_once_with(
                control_name="my_control_06650U",
                artifact_name=None,
                name=None,
                display_name=None,
                description=None,
                hooks=None,
                priority=None,
                config=None,
                agent_names=None,
                tool_names=None,
                model_names=None,
            )

    def test_update_control_all_params(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.update_control"
        ) as mock:
            controls_command.update_control(
                control_name="my_control_06650U",
                artifact_name="Content Guardrails",
                new_name="updated-name",
                display_name="Updated Name",
                description="Updated description",
                hooks=["tool_pre_invoke"],
                priority=75,
                config='{"action": "block"}',
                agent_names=["agent-99"],
                tool_names=["tool-99"],
                model_names=["model-99"],
            )
            mock.assert_called_once_with(
                control_name="my_control_06650U",
                artifact_name="Content Guardrails",
                name="updated-name",
                display_name="Updated Name",
                description="Updated description",
                hooks=["tool_pre_invoke"],
                priority=75,
                config='{"action": "block"}',
                agent_names=["agent-99"],
                tool_names=["tool-99"],
                model_names=["model-99"],
            )


class TestDeleteControl:
    def test_delete_control(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.remove_control"
        ) as mock:
            controls_command.remove_control(control_name="my_control_06650U")
            mock.assert_called_once_with("my_control_06650U")


class TestImportControls:
    def test_import_controls(self):
        file_path = Path("controls.yaml")
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.import_controls"
        ) as mock:
            controls_command.import_controls(file=file_path)
            mock.assert_called_once_with(file_path)


class TestExportControl:
    def test_export_control(self):
        output_path = Path("exported_control.yaml")
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.export_control"
        ) as mock:
            controls_command.export_control(control_name="my_control_06650U", output=output_path)
            mock.assert_called_once_with("my_control_06650U", output_path)


class TestListArtifactTypes:
    def test_list_artifact_types_non_verbose(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.list_artifact_types"
        ) as mock:
            controls_command.list_artifact_types()
            mock.assert_called_once_with(False)

    def test_list_artifact_types_verbose(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.list_artifact_types"
        ) as mock:
            controls_command.list_artifact_types(verbose=True)
            mock.assert_called_once_with(True)


class TestGetArtifactType:
    def test_get_artifact_type_non_verbose(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.get_artifact_type"
        ) as mock:
            controls_command.get_artifact_type(artifact_name="PII Filter")
            mock.assert_called_once_with("PII Filter", False)

    def test_get_artifact_type_verbose(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.controls.controls_command.ControlsController.get_artifact_type"
        ) as mock:
            controls_command.get_artifact_type(artifact_name="PII Filter", verbose=True)
            mock.assert_called_once_with("PII Filter", True)
