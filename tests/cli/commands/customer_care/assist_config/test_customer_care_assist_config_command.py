import pytest
from unittest.mock import patch

from ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config import (
    customer_care_assist_config_command,
)


class TestListAssistConfigCommand:
    def test_delegates_to_controller(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config"
            ".customer_care_assist_config_command.list_assist_config"
        ) as mock:
            customer_care_assist_config_command.list_assist_config_command()
            mock.assert_called_once_with()


class TestSetAssistConfigCommand:
    base_params = {
        "property_name": "min_confidence",
        "value": "0.7",
    }

    def test_delegates_to_controller(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config"
            ".customer_care_assist_config_command.set_assist_config"
        ) as mock:
            customer_care_assist_config_command.set_assist_config_command(**self.base_params)
            mock.assert_called_once_with(**self.base_params)

    @pytest.mark.parametrize("missing_param", ["property_name", "value"])
    def test_raises_on_missing_required_param(self, missing_param):
        params = self.base_params.copy()
        params.pop(missing_param)

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config"
            ".customer_care_assist_config_command.set_assist_config"
        ) as mock:
            with pytest.raises(TypeError):
                customer_care_assist_config_command.set_assist_config_command(**params)
            mock.assert_not_called()


class TestRemoveAssistConfigCommand:
    base_params = {"property_name": "min_confidence"}

    def test_delegates_to_controller(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config"
            ".customer_care_assist_config_command.remove_assist_config"
        ) as mock:
            customer_care_assist_config_command.remove_assist_config_command(**self.base_params)
            mock.assert_called_once_with(**self.base_params)

    def test_raises_on_missing_required_param(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config"
            ".customer_care_assist_config_command.remove_assist_config"
        ) as mock:
            with pytest.raises(TypeError):
                customer_care_assist_config_command.remove_assist_config_command()
            mock.assert_not_called()


class TestResetAssistConfigCommand:
    def test_delegates_to_controller(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.customer_care.assist_config"
            ".customer_care_assist_config_command.reset_assist_config"
        ) as mock:
            customer_care_assist_config_command.reset_assist_config_command()
            mock.assert_called_once_with()
