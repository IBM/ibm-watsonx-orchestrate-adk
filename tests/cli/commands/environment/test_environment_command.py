from ibm_watsonx_orchestrate.cli.commands.environment import environment_command
from unittest.mock import patch
import pytest

from ibm_watsonx_orchestrate.cli.commands.tools.types import RegistryType


class TestEnvActivate:
    base_params = {
        "name": "testing",
        "apikey": "123",
        "username":None,
        "password": None,
        "registry": str(RegistryType.LOCAL),
        'test_package_version_override': None
    }

    def test_activate(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_command.environment_controller.activate") as mock:
            environment_command.activate_env(**self.base_params)
            mock.assert_called_once_with(**self.base_params)
    
    @pytest.mark.parametrize(
            ("missing_param", "default_value"),
            [
                ("apikey", None)
            ]
    )
    def test_activate_missing_optional_parms(self, missing_param, default_value):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        expected_params = self.base_params.copy()
        expected_params[missing_param] = default_value
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_command.environment_controller.activate") as mock:
            environment_command.activate_env(**missing_params)
            mock.assert_called_once_with(**expected_params)
    
    @pytest.mark.parametrize(
            "missing_param",
            [
                "name"
            ]
    )
    def test_activate_missing_required_parms(self, missing_param):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_command.environment_controller.activate") as mock:
            with pytest.raises(TypeError) as e:
                environment_command.activate_env(**missing_params)
            mock.assert_not_called

            assert f"activate_env() missing 1 required positional argument: '{missing_param}'" in str(e.value)

class TestEnvAdd:
    base_params = {
        "name": "testing",
        "url": "testing url",
        "activate": True
    }

    expected_params = {
        "name": "testing",
        "url": "testing url",
        "should_activate": True,
        "iam_url": None,
        "type": None,
        "insecure": False,
        "verify": None
    }

    def test_add(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_command.environment_controller.add") as mock:
            environment_command.add_env(**self.base_params)
            mock.assert_called_once_with(**self.expected_params)
    
    @pytest.mark.parametrize(
            ("missing_param", "default_value", "expected_name"),
            [
                ("activate", False, "should_activate")
            ]
    )
    def test_add_missing_optional_parms(self, missing_param, default_value, expected_name):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        expected_params = self.expected_params.copy()
        expected_params[expected_name] = default_value
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_command.environment_controller.add") as mock:
            environment_command.add_env(**missing_params)
            mock.assert_called_once_with(**expected_params)
    
    @pytest.mark.parametrize(
            "missing_param",
            [
                "name",
                "url"
            ]
    )
    def test_add_missing_required_parms(self, missing_param):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_command.environment_controller.add") as mock:
            with pytest.raises(TypeError) as e:
                environment_command.add_env(**missing_params)
            mock.assert_not_called

            assert f"add_env() missing 1 required positional argument: '{missing_param}'" in str(e.value)

class TestEnvRemove:
    base_params = {
        "name": "testing",
    }

    def test_remove(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_command.environment_controller.remove") as mock:
            environment_command.remove_env(**self.base_params)
            mock.assert_called_once_with(**self.base_params)
    
    @pytest.mark.parametrize(
            "missing_param",
            [
                "name"
            ]
    )
    def test_remove_missing_required_parms(self, missing_param):
        missing_params = self.base_params.copy()
        missing_params.pop(missing_param, None)

        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_command.environment_controller.remove") as mock:
            with pytest.raises(TypeError) as e:
                environment_command.remove_env(**missing_params)
            mock.assert_not_called

            assert f"remove_env() missing 1 required positional argument: '{missing_param}'" in str(e.value)

class TestEnvList:
    def test_list(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_command.environment_controller.list_envs") as mock:
            environment_command.list_envs()
            mock.assert_called_once_with()
    