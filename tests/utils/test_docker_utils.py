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
            capture_output=True,
            check=True
        )

def test_docker_login_failure():

    mock_vm_manager = MagicMock()
    mock_vm_manager.run_docker_command.return_value.returncode = 1
    mock_vm_manager.run_docker_command.return_value.stderr = b"Login failed"

    with patch("ibm_watsonx_orchestrate.utils.docker_utils.get_vm_manager", return_value=mock_vm_manager), \
         skip_terms_and_conditions():

        result = DockerLoginService._DockerLoginService__docker_login("bad-key", "bad-registry")
        assert result is False


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


# ---------------------------------------------------------------------------
# DockerLoginService.login_by_dev_edition_source — fallback key tests
# ---------------------------------------------------------------------------

def _make_login_service():
    return DockerLoginService(env_service=EnvService(Config()))


def test_fallback_key_succeeds_when_primary_fails():
    """Primary DOCKER_IAM_KEY fails, fallback key succeeds — no sys.exit."""
    env_dict = {
        "WO_DEVELOPER_EDITION_SOURCE": "internal",
        "DOCKER_IAM_KEY": "bad-primary-key",
        "DOCKER_FALLBACK_IAM_KEY": "good-fallback-key",
        "REGISTRY_URL": "registry.example.com/myorg",
    }

    login_results = [False, True]

    with patch.object(
        DockerLoginService,
        "_DockerLoginService__docker_login",
        side_effect=login_results,
    ) as mock_login:
        _make_login_service().login_by_dev_edition_source(env_dict)

    assert mock_login.call_count == 2
    mock_login.assert_any_call("bad-primary-key", "registry.example.com", "iamapikey")
    mock_login.assert_any_call("good-fallback-key", "registry.example.com", "iamapikey")


def test_primary_succeeds_fallback_never_tried():
    """Primary DOCKER_IAM_KEY succeeds — fallback key is never consulted."""
    env_dict = {
        "WO_DEVELOPER_EDITION_SOURCE": "internal",
        "DOCKER_IAM_KEY": "good-primary-key",
        "DOCKER_FALLBACK_IAM_KEY": "fallback-key",
        "REGISTRY_URL": "registry.example.com/myorg",
    }

    with patch.object(
        DockerLoginService,
        "_DockerLoginService__docker_login",
        return_value=True,
    ) as mock_login:
        _make_login_service().login_by_dev_edition_source(env_dict)

    assert mock_login.call_count == 1
    mock_login.assert_called_once_with("good-primary-key", "registry.example.com", "iamapikey")


def test_primary_fails_no_fallback_key_exits():
    """Primary DOCKER_IAM_KEY fails and no DOCKER_FALLBACK_IAM_KEY is set — sys.exit(1)."""
    env_dict = {
        "WO_DEVELOPER_EDITION_SOURCE": "internal",
        "DOCKER_IAM_KEY": "bad-primary-key",
        "REGISTRY_URL": "registry.example.com/myorg",
    }

    with patch.object(
        DockerLoginService,
        "_DockerLoginService__docker_login",
        return_value=False,
    ):
        with pytest.raises(SystemExit) as exc:
            _make_login_service().login_by_dev_edition_source(env_dict)

    assert exc.value.code == 1


def test_both_keys_fail_exits():
    """Both DOCKER_IAM_KEY and DOCKER_FALLBACK_IAM_KEY fail — sys.exit(1)."""
    env_dict = {
        "WO_DEVELOPER_EDITION_SOURCE": "internal",
        "DOCKER_IAM_KEY": "bad-primary-key",
        "DOCKER_FALLBACK_IAM_KEY": "bad-fallback-key",
        "REGISTRY_URL": "registry.example.com/myorg",
    }

    with patch.object(
        DockerLoginService,
        "_DockerLoginService__docker_login",
        return_value=False,
    ) as mock_login:
        with pytest.raises(SystemExit) as exc:
            _make_login_service().login_by_dev_edition_source(env_dict)

    assert exc.value.code == 1
    assert mock_login.call_count == 2


def test_non_internal_source_not_affected_by_fallback():
    """MYIBM source with a failing login still exits — no fallback attempted."""
    env_dict = {
        "WO_DEVELOPER_EDITION_SOURCE": "myibm",
        "WO_ENTITLEMENT_KEY": "bad-entitlement-key",
        "DOCKER_FALLBACK_IAM_KEY": "some-fallback-key",
        "REGISTRY_URL": "registry.example.com/myorg",
    }

    with patch.object(
        DockerLoginService,
        "_DockerLoginService__docker_login",
        return_value=False,
    ) as mock_login:
        with pytest.raises(SystemExit) as exc:
            _make_login_service().login_by_dev_edition_source(env_dict)

    assert exc.value.code == 1
    assert mock_login.call_count == 1  # fallback never tried for MYIBM
