from unittest.mock import patch, MagicMock
import re
import pytest
from requests import Response
from ibm_watsonx_orchestrate.cli.commands.environment import environment_controller
from ibm_watsonx_orchestrate.client.base_api_client import ClientAPIException
from ibm_watsonx_orchestrate.cli.config import PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, \
    PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT

tokens = {
    "valid_token_w_expiry": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjk5OTk5OTk5OTl9.Vg30C57s3l90JNap_VgMhKZjfc-p7SoBXaSAy8c28HA",
    "valid_token_wo_expiry": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
    "invalid_token_expired": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjEwMDAwMDAwMDB9.9oF3tWEwFMK-0ut1pNLF0tOfZ-onpT5upqOCX58xlko",
    "invalid_token": "not a real token",
}

@pytest.fixture(autouse=True)
def patch_getpass():
    with patch("getpass.getpass", return_value="mock-api-key"):
        yield

class MockConfig():
    def __init__(self, read_value=None, expected_write=None, expected_save=None):
        self.read_value = read_value
        self.expected_write = expected_write if isinstance(expected_write, list) else [expected_write]
        self.expected_save = expected_save if isinstance(expected_save, list) else [expected_save]

    def read(self, section, option):
        return self.read_value.get(section, {}).get(option)
    
    def get(self, *args):
        nested_value = self.read_value.copy()
        for arg in args:
            nested_value = nested_value[arg]
        return nested_value

    def write(self, section, option, value):
        assert value == (self.expected_write.pop(0) if len(self.expected_write) > 1 else self.expected_write[0])

    def save(self, data):
        assert data == (self.expected_save.pop(0) if len(self.expected_save) > 1 else self.expected_save[0])
    
    def delete(self, *args, **kwargs):
        pass

class MockConfig2():
    def __init__(self):
        self.config = {}

    def read(self, section, option):
        return self.config.get(section, {}).get(option)

    def get(self, *args):
        nested_value = self.config.copy()
        for arg in args:
            nested_value = nested_value[arg]
        return nested_value

    def write(self, section, option, value):
        if not section in self.config:
            self.config[section] = {}
        self.config[section][option] = value

    def save(self, data):
        self.config.update(data)

    def delete(self, *args, **kwargs):
        pass

class MockClient:
    def __init__(self, credentials):
        self.token = tokens["valid_token_w_expiry"]

class MockCredentials:
    def __init__(self, url, api_key, iam_url, auth_type, username, password):
        pass

@pytest.fixture
def mock_read_value():
    yield {
            "context": {
                "active_environment": "testing"
            },
            "environments": {
                "testing": {"wxo_url": "testing", "auth_type": None },
                "anothertesting": {"wxo_url": "another testing"},
            },
            "auth": {
                "testing": {
                    "wxo_mcsp_token": "token",
                    "wxo_mcsp_token_expiry": 999999999
                }
            },
            "python_registry": {
                "type": "pypi"
            }
        }

class TestActivate:

    @pytest.mark.parametrize(
            ("url", "token", "token_expiry", "auth_type"),
            [
                ("https://www.testing.com", tokens["valid_token_w_expiry"], 9999999999, None)
            ]
    )
    def test_activate_valid_token(self, mock_read_value, url, token, token_expiry, caplog, auth_type):
        read_value = mock_read_value.copy()
        read_value['environments']['testing']['wxo_url'] = url
        read_value['environments']['testing']['auth_type'] = auth_type
        read_value['auth']['testing']['wxo_mcsp_token'] = token
        read_value['auth']['testing']['wxo_mcsp_token_expiry'] = token

        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg, \
            patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Client", MockClient) as mock_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Credentials", MockCredentials) as mock_credentials, \
            patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.AgentClient", MagicMock):
            
            mock_cfg.return_value = MockConfig(read_value=mock_read_value, expected_write="testing", expected_save={
                "auth": {
                    "testing":{
                        "wxo_mcsp_token": "test_token",
                        "wxo_mcsp_token_expiry": 0
                    }
                }
            })

            environment_controller.activate(name="testing", apikey="123")

            captured = caplog.text
            assert "Environment 'testing' is now active" in captured


    @pytest.mark.parametrize(
        ('registry', 'test_package_version_override'),
        [
            (None, None),
            ('pypi', None),
            ('testpypi', None),
            ('testpypi', '1.2.3.rc20'),
            ('local', None),
        ]
    )
    def test_change_registry(self, mock_read_value, caplog, registry, test_package_version_override):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg, \
                patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Client", MockClient) as mock_client, \
                patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Credentials", MockCredentials) as mock_credentials, \
                patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.AgentClient", MagicMock):

            cfg = MockConfig2()
            cfg.save(mock_read_value)
            cfg.write('environments', 'local', {"wxo_url": "http://localhost:4321", "auth_type": None })
            mock_cfg.return_value = cfg
            environment_controller.activate(name="local", registry=registry, test_package_version_override=test_package_version_override)

            if registry is None:
                assert cfg.config.get(PYTHON_REGISTRY_HEADER).get(PYTHON_REGISTRY_TYPE_OPT) == 'pypi'
            else:
                assert cfg.config.get(PYTHON_REGISTRY_HEADER).get(PYTHON_REGISTRY_TYPE_OPT) == registry
                assert cfg.config.get(PYTHON_REGISTRY_HEADER).get(PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT) == test_package_version_override

            captured = caplog.text
            assert "Environment 'local' is now active" in captured

    @pytest.mark.parametrize(
            ("url", "token", "token_expiry", "auth_type"),
            [
                ("http://localhost:1234", tokens["invalid_token"], None, None),
                ("http://localhost:1234", tokens["valid_token_wo_expiry"], None, None),
                ("https://www.testing.com", tokens["invalid_token_expired"], 9999999999, None)
            ]
    )
    def test_activate_invalid_token(self, mock_read_value, url, token, token_expiry, caplog, auth_type ):
        read_value = mock_read_value.copy()
        read_value['environments']['testing']['wxo_url'] = url
        read_value['environments']['testing']['auth_type'] = auth_type
        read_value['auth']['testing']['wxo_mcsp_token'] = token
        read_value['auth']['testing']['wxo_mcsp_token_expiry'] = token

        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg, \
            patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Client", MockClient) as mock_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Credentials", MockCredentials) as mock_credentials, \
            patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.AgentClient", MagicMock):
            
            expected_save = {
                "auth": {
                    "testing":{
                        "wxo_mcsp_token": tokens["valid_token_w_expiry"],
                    }
                }
            }

            if token_expiry:
                expected_save["auth"]["testing"]["wxo_mcsp_token_expiry"] = token_expiry

            mock_cfg.return_value = MockConfig(read_value=mock_read_value, expected_write="testing", expected_save=expected_save)

            environment_controller.activate(name="testing", apikey="123")

            captured = caplog.text
            assert "Environment 'testing' is now active" in captured

    @pytest.mark.parametrize(
            ("url", "token", "token_expiry", "auth_type"),
            [
                ("https://www.testing.com", tokens["invalid_token_expired"], 0, None)
            ]
    )
    def test_activate_token_rejected(self,  mock_read_value, url, token, token_expiry, caplog, auth_type):
        read_value = mock_read_value.copy()
        read_value['environments']['testing']['wxo_url'] = url
        read_value['environments']['testing']['auth_type'] = auth_type
        read_value['auth']['testing']['wxo_mcsp_token'] = token
        read_value['auth']['testing']['wxo_mcsp_token_expiry'] = token

        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg, \
            patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Client", MockClient) as mock_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Credentials", MockCredentials) as mock_credentials, \
            patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.AgentClient", MagicMock) as mock_agent_client:
            
            mock_http_error_response = Response()
            mock_http_error_response.status_code = 401
            mock_agent_client.get = MagicMock()
            mock_agent_client.get.side_effect = ClientAPIException(response=mock_http_error_response)

            expected_save = {
                "auth": {
                    "testing":{
                        "wxo_mcsp_token": tokens["valid_token_w_expiry"],
                    }
                }
            }

            if token_expiry:
                expected_save["auth"]["testing"]["wxo_mcsp_token_expiry"] = token_expiry

            mock_cfg.return_value = MockConfig(read_value=mock_read_value, expected_write="testing", expected_save=expected_save)

            with pytest.raises(SystemExit):
                environment_controller.activate(name="testing", apikey="123")

            captured = caplog.text
            assert "Environment 'testing' is now active" not in captured
            assert f"Failed to authenticate to provided instance '{url}'. Reason: 'None'. Please ensure provider URL and API key are valid."
    
class TestAdd:
    def test_add(self, mock_read_value, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg:
            mock_cfg.return_value = MockConfig(read_value=mock_read_value, expected_write={"wxo_url": "test url"})

            environment_controller.add(name="testing123", url="test url")

            captured = caplog.text
            assert "Environment 'testing123' has been created" in captured
        
    def test_add_local(self, mock_read_value, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg:
            mock_cfg.return_value = MockConfig(read_value=mock_read_value, expected_write={"wxo_url": "test url"})

            environment_controller.add(name="local", url="test url")

            captured = caplog.text
            assert "The name 'local' is a reserved environment name" in captured

    def test_add_existing_confirm(self, mock_read_value, caplog, monkeypatch):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg:
            mock_cfg.return_value = MockConfig(read_value=mock_read_value, expected_write={"wxo_url": "test url"})
            monkeypatch.setattr('builtins.input', lambda _: "y")
            
            environment_controller.add(name="testing", url="test url")

            captured = caplog.text

            assert "Environment 'testing' has been created" in captured
            assert "Existing environment with name 'testing' found" in captured
    
    def test_add_existing_reject(self, mock_read_value, caplog, monkeypatch):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg:
            mock_cfg.return_value = MockConfig(read_value=mock_read_value, expected_write={"wxo_url": "test url"})
            monkeypatch.setattr('builtins.input', lambda _: "n")
            
            environment_controller.add(name="testing", url="test url")

            captured = caplog.text

            assert "Environment 'testing' has been created" not in captured
            assert "Existing environment with name 'testing' found" in captured
            assert "No changes made to environments" in captured

    def test_add_activate(self, mock_read_value, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg,\
            patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.activate") as mock_activate:
            mock_cfg.return_value = MockConfig(read_value=mock_read_value, expected_write={"wxo_url": "test url"})

            environment_controller.add(name="testing123", url="test url", should_activate=True)

            mock_activate.assert_called_once

            captured = caplog.text
            assert "Environment 'testing123' has been created" in captured
        
class TestRemove:
    def test_remove(self, mock_read_value, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg:
            mock_cfg.return_value = MockConfig(read_value=mock_read_value)

            environment_controller.remove(name="anothertesting")

            captured = caplog.text
            assert "Successfully removed environment 'anothertesting'" in captured
        
    def test_remove_local(self, mock_read_value, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg:
            mock_cfg.return_value = MockConfig(read_value=mock_read_value)

            environment_controller.remove(name="local")

            captured = caplog.text
            assert "The environment 'local' is a default environment and cannot be removed" in captured

    def test_remove_non_existant(self, mock_read_value, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg:
            mock_cfg.return_value = MockConfig(read_value=mock_read_value)
            
            environment_controller.remove(name="testing123")

            captured = caplog.text

            assert "No environment named 'testing123' exists" in captured

    def test_remove_activate_confirm(self, mock_read_value, caplog, monkeypatch):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg:
            mock_cfg.return_value = MockConfig(read_value=mock_read_value, expected_write=None)

            monkeypatch.setattr('builtins.input', lambda _: "y")

            environment_controller.remove(name="testing")

            captured = caplog.text
            assert "Successfully removed environment 'testing'" in captured
    
    def test_remove_activate_reject(self, mock_read_value, caplog, monkeypatch):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg:
            mock_cfg.return_value = MockConfig(read_value=mock_read_value, expected_write=None)

            monkeypatch.setattr('builtins.input', lambda _: "n")

            environment_controller.remove(name="testing")

            captured = caplog.text
            assert "No changes made to environments" in captured
            assert "Successfully removed environment 'testing'" not in captured

class TestList:
    def test_list(self, mock_read_value, capsys):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg:
            mock_cfg.return_value = MockConfig(read_value=mock_read_value)
            
            environment_controller.list_envs()

            captured = capsys.readouterr()

            testing_env_regex = re.compile(r"testing\s*testing\s*\(active\)")
            anothertesting_env_regex = re.compile(r"anothertesting\s*another testing\s*$")

            assert len(testing_env_regex.findall(captured.out)) != 0
            assert len(anothertesting_env_regex.findall(captured.out)) != 0

    def test_list_no_active(self, mock_read_value, capsys, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.environment.environment_controller.Config") as mock_cfg:
            read_value = mock_read_value.copy()
            read_value["context"]["active_environment"] = None

            mock_cfg.return_value = MockConfig(read_value=read_value)
            
            environment_controller.list_envs()

            captured = capsys.readouterr()

            active_testing_env_regex = re.compile(r"testing\s*testing\s*\(active\)")
            testing_env_regex = re.compile(r"testing\s*testing\s*$")
            anothertesting_env_regex = re.compile(r"anothertesting\s*another testing\s*\n")

            assert "No active environment is currently set" in caplog.text
            assert len(active_testing_env_regex.findall(captured.out)) == 0
            assert len(testing_env_regex.findall(captured.out)) != 0
            assert len(anothertesting_env_regex.findall(captured.out)) != 0