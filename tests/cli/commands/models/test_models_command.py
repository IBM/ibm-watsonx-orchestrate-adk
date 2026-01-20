import pytest
from unittest.mock import patch

from ibm_watsonx_orchestrate.cli.commands.models import models_command
from ibm_watsonx_orchestrate.agent_builder.models.types import ModelType

class TestModelList:
    def test_model_list(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.list_models") as list_models_mock:
            models_command.model_list()
            list_models_mock.assert_called_once_with(
                print_raw=False
            )
    
    def test_model_list_print_raw(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.list_models") as list_models_mock:
            models_command.model_list(print_raw=True)
            list_models_mock.assert_called_once_with(
                print_raw=True
            )

class TestModelsImport:
    def test_models_import(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.import_model") as import_model_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.publish_or_update_models") as publish_mock:
            import_model_mock.return_value = ["Model"]

            models_command.models_import(
                file="test.yaml",
                app_id="test_app_id"
            )
            import_model_mock.assert_called_once_with(
                file="test.yaml",
                app_id="test_app_id"
            )
            publish_mock.assert_called_once_with(
                model="Model"
            )

class TestModelsExport:
    def test_models_export(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.export_model") as export_model_mock:
            models_command.models_export(
                name="virtual-model/test",
                output_path="test_output.zip"
            )

            export_model_mock.assert_called_once_with(
                name="virtual-model/test",
                output_path="test_output.zip"
            )

class TestModelsAdd:
    def test_models_add(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.create_model") as create_model_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.publish_or_update_models") as publish_mock:
            create_model_mock.return_value = "Model"

            models_command.models_add(
                name="test_name",
                description="test_description",
                display_name="test_display_name",
                provider_config="{}",
                app_id="test_app_id",
                type=ModelType.CHAT
            )
            create_model_mock.assert_called_once_with(
                name="test_name",
                description="test_description",
                display_name="test_display_name",
                provider_config_dict={},
                app_id="test_app_id",
                model_type=ModelType.CHAT
            )
            publish_mock.assert_called_once_with(
                model="Model"
            )
    
    def test_models_add_invalid_provider_config(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.create_model") as create_model_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.publish_or_update_models") as publish_mock:
            create_model_mock.return_value = "Model"

            with pytest.raises(SystemExit):
                models_command.models_add(
                    name="test_name",
                    description="test_description",
                    display_name="test_display_name",
                    provider_config="test",
                    app_id="test_app_id",
                    type=ModelType.CHAT
                )

            captured = caplog.text

            assert f"Failed to parse provider config. 'test' is not valid json" in captured

            create_model_mock.assert_not_called()
            publish_mock.assert_not_called()

class TestModelsRemove:
    def test_models_remove(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.remove_model") as remove_model_mock:

            models_command.models_remove(
                name="test_name",
            )
            remove_model_mock.assert_called_once_with(
                name="test_name",
            )

class TestModelsPolicyImport:
    def test_models_policy_import(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.import_model_policy") as import_model_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.publish_or_update_model_policies") as publish_mock:
            import_model_mock.return_value = ["Policy"]

            models_command.models_policy_import(
                file="test.yaml",
            )
            import_model_mock.assert_called_once_with(
                file="test.yaml",
            )
            publish_mock.assert_called_once_with(
                policy="Policy"
            )

class TestModelsPolicyExport:
    def test_models_policy_export(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.export_model_policy") as export_model_policy_mock:

            models_command.models_policy_export(
                name="test_name",
                output_path="test_output.zip"
            )

            export_model_policy_mock.assert_called_once_with(
                name="test_name",
                output_path="test_output.zip"
            )

class TestModelsPolicyAdd:
    def test_models_policy_add(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.create_model_policy") as create_model_mock, \
            patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.publish_or_update_model_policies") as publish_mock:
            create_model_mock.return_value = "Policy"

            models_command.models_policy_add(
                name="test_name",
                models="test_models",
                strategy="test_strategy",
                strategy_on_code="test_strategy_on_code",
                retry_on_code="test_retry_on_code",
                retry_attempts="test_retry_attempts",
                display_name="test_display_name",
                description="test_description"
            )
            create_model_mock.assert_called_once_with(
                name="test_name",
                models="test_models",
                strategy="test_strategy",
                strategy_on_code="test_strategy_on_code",
                retry_on_code="test_retry_on_code",
                retry_attempts="test_retry_attempts",
                display_name="test_display_name",
                description="test_description"
            )
            publish_mock.assert_called_once_with(
                policy="Policy"
            )

class TestModelsPolicyRemove:
    def test_models_policy_remove(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.models.models_controller.ModelsController.remove_policy") as remove_policy_mock:

            models_command.models_policy_remove(
                name="test_name",
            )
            remove_policy_mock.assert_called_once_with(
                name="test_name",
            )