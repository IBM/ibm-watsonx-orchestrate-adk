import pytest
from unittest.mock import patch

from ibm_watsonx_orchestrate.cli.commands.customer_care.platform import customer_care_platform_command
from ibm_watsonx_orchestrate.cli.commands.customer_care.platform.types import PlatformType

class TestCustomerCarePlatformConfigure:
    base_params = {
        "type": PlatformType.GENESYS,
        "name": "Testing_Platform_Name",
        "client_id": "Testing_Client_ID",
        "client_secret": "Testing_Client_Secret",
        "client_secret_stdin": "Testing_Client_Secret_Stdin",
        "endpoint": "example.com"
    }

    def test_configure_customer_care_platform_command(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_command.configure_platform_customer_care") as mock:
            customer_care_platform_command.configure_platform_customer_care_command(**self.base_params)
            mock.assert_called_once_with(**self.base_params)
    
    @pytest.mark.parametrize(
        "missing_param",
        [
            "type",
            "name"
        ]
    )
    def test_configure_customer_care_platform_command_missing_required_param(self, missing_param):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        with patch("ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_command.configure_platform_customer_care") as mock:
            with pytest.raises(TypeError) as e:
                customer_care_platform_command.configure_platform_customer_care_command(**missing_params)
            mock.assert_not_called()

            assert f"configure_platform_customer_care_command() missing 1 required positional argument: '{missing_param}'" in str(e.value)
    
    @pytest.mark.parametrize(
    argnames=("missing_param", "default_value"),
    argvalues=[
            ("client_id", None),
            ("client_secret", None),
            ("client_secret_stdin", None),
            ("endpoint", None)
        ]   
    )
    def test_configure_customer_care_platform_command_missing_optional_param(self, missing_param, default_value):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        expected_params = self.base_params.copy()
        expected_params[missing_param] = default_value

        with patch("ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_command.configure_platform_customer_care") as mock:
            customer_care_platform_command.configure_platform_customer_care_command(**missing_params)
            mock.assert_called_once_with(**expected_params)

class TestListCustomerCarePlatformCommand:
    base_params = {
        "type": PlatformType.GENESYS
    }

    def test_list_customer_care_platform_command(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_command.list_platform_customer_care") as mock:
            customer_care_platform_command.list_platform_customer_care_command(**self.base_params)
            mock.assert_called_once_with(**self.base_params)

    @pytest.mark.parametrize(
        argnames=("missing_param", "default_value"),
        argvalues=[
            ("type", None)
        ]
    )
    def test_list_custome_care_platform_command_missing_optional_param(self, missing_param, default_value):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        expected_params = self.base_params.copy()
        expected_params[missing_param] = default_value
        
        with patch("ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_command.list_platform_customer_care") as mock:
            customer_care_platform_command.list_platform_customer_care_command(**missing_params)
            mock.assert_called_once_with(**expected_params)

class TestRemoveCustomerCarePlatformCommand:
    base_params = {
        "type": PlatformType.GENESYS,
        "name": "Testing_Platform_Name"
    }

    def test_remove_customer_care_platform_command(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_command.remove_platform_customer_care") as mock:
            customer_care_platform_command.remove_platform_customer_care_command(**self.base_params)
            mock.assert_called_once_with(**self.base_params)
    
    @pytest.mark.parametrize(
        "missing_param",
        [
            "name"
        ]
    )
    def test_remove_customer_care_platform_command_missing_required_param(self, missing_param):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        with patch("ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_command.remove_platform_customer_care") as mock:
            with pytest.raises(TypeError) as e:
                customer_care_platform_command.remove_platform_customer_care_command(**missing_params)
            mock.assert_not_called()

            assert f"remove_platform_customer_care_command() missing 1 required positional argument: '{missing_param}'" in str(e.value)
    
    @pytest.mark.parametrize(
    argnames=("missing_param", "default_value"),
    argvalues=[
            ("type", None)
        ]   
    )
    def test_remove_customer_care_platform_command_missing_optional_param(self, missing_param, default_value):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        expected_params = self.base_params.copy()
        expected_params[missing_param] = default_value

        
        with patch("ibm_watsonx_orchestrate.cli.commands.customer_care.platform.customer_care_platform_command.remove_platform_customer_care") as mock:
            customer_care_platform_command.remove_platform_customer_care_command(**missing_params)
            mock.assert_called_once_with(**expected_params)