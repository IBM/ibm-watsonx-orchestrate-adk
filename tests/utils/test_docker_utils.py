from unittest.mock import MagicMock, patch

import pytest

from ibm_watsonx_orchestrate.cli.config import Config
from ibm_watsonx_orchestrate.utils.docker_utils import DockerLoginService, DockerUtils, DockerComposeCore
from ibm_watsonx_orchestrate.utils.environment import EnvService


def skip_terms_and_conditions():
    return patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.confirm_accepts_license_agreement")


def test_docker_login_success():

    mock_vm_manager = MagicMock()
    mock_vm_manager.run_docker_command.return_value.returncode = 0

    with patch("ibm_watsonx_orchestrate.utils.docker_utils.get_vm_manager", return_value=mock_vm_manager), \
         skip_terms_and_conditions():

        DockerLoginService._DockerLoginService__docker_login("test-key", "registry.example.com")

        mock_vm_manager.run_docker_command.assert_called_once_with(
            ["login", "-u", "iamapikey", "--password-stdin", "registry.example.com"],
            input="test-key",
            capture_output=True
        )

def test_docker_login_failure():

    mock_vm_manager = MagicMock()
    mock_vm_manager.run_docker_command.return_value.returncode = 1
    mock_vm_manager.run_docker_command.return_value.stderr = b"Login failed"

    with patch("ibm_watsonx_orchestrate.utils.docker_utils.get_vm_manager", return_value=mock_vm_manager), \
         skip_terms_and_conditions():

        with pytest.raises(SystemExit) as exc:
            DockerLoginService._DockerLoginService__docker_login("bad-key", "bad-registry")

        assert exc.value.code == 1


def test_ensure_docker_installed_success():

    mock_vm_manager = MagicMock()
    mock_vm_manager.run_docker_command.return_value.returncode = 0

    with patch("ibm_watsonx_orchestrate.utils.docker_utils.get_vm_manager", return_value=mock_vm_manager), \
         skip_terms_and_conditions():


        DockerUtils.ensure_docker_installed()

        mock_vm_manager.run_docker_command.assert_called_once_with(
            ["--version"],
            capture_output=True
        )

def test_ensure_docker_installed_failure():
    mock_vm_manager = MagicMock()
    mock_vm_manager.run_docker_command.return_value.returncode = 1

    with patch("ibm_watsonx_orchestrate.utils.docker_utils.get_vm_manager", return_value=mock_vm_manager), \
         patch("subprocess.run", side_effect=FileNotFoundError), \
         skip_terms_and_conditions():

        with pytest.raises(SystemExit) as exc:
            DockerUtils.ensure_docker_installed()

        assert exc.value.code == 1

# def test_ensure_docker_compose_installed_success():
#     with patch("subprocess.run") as mock_run, skip_terms_and_conditions():
#         mock_run.return_value.returncode = 0

#         cli_config = Config()
#         env_service = EnvService(cli_config)
#         compose_core = DockerComposeCore(env_service)

#         # Call the actual method
#         compose_core._ensure_docker_compose_installed()

#         mock_run.assert_called_once_with(
#             ["docker", "compose", "version"],
#             check=True,
#             capture_output=True
#         )



# def test_ensure_docker_compose_hyphen_success():
#     with patch("subprocess.run") as mock_run, skip_terms_and_conditions():
#         def mock_failure():
#             yield FileNotFoundError
#             while True:
#                 yield 0

#         mock_run.side_effect = mock_failure()
#         cli_config = Config()
#         env_service = EnvService(cli_config)
#         compose_core = DockerComposeCore(env_service)
#         compose_core._DockerComposeCore__ensure_docker_compose_installed()
#         mock_run.assert_called_with(
#             ["docker-compose", "version"],
#             check=True,
#             capture_output=True
#         )

# def test_ensure_docker_compose_failure(capsys):
#     with patch("subprocess.run") as mock_run, skip_terms_and_conditions():

#         mock_run.side_effect = FileNotFoundError
#         with pytest.raises(SystemExit) as exc:
#             cli_config = Config()
#             env_service = EnvService(cli_config)
#             compose_core = DockerComposeCore(env_service)
#             compose_core._DockerComposeCore__ensure_docker_compose_installed()
#         assert exc.value.code == 1

#         captured = capsys.readouterr()
#         assert "Unable to find an installed docker-compose or docker compose" in captured.out
