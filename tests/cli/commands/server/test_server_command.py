import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import sys
from typer.testing import CliRunner

from ibm_watsonx_orchestrate.cli.commands.server.server_command import (
    server_app,
    run_compose_lite,
    run_db_migration
)
from ibm_watsonx_orchestrate.cli.config import LICENSE_HEADER, ENV_ACCEPT_LICENSE, Config
from ibm_watsonx_orchestrate.developer_edition.vm_host.native import NativeDockerManager
from ibm_watsonx_orchestrate.utils.docker_utils import DockerComposeCore
from ibm_watsonx_orchestrate.utils.environment import EnvService
from utils.matcher import MatchesStringContaining

from ibm_watsonx_orchestrate.utils.docker_utils import DockerUtils
from subprocess import CompletedProcess


def skip_terms_and_conditions():
    return patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.confirm_accepts_license_agreement")

runner = CliRunner()


@pytest.fixture(params=["internal", "myibm"])
def valid_user_env(tmp_path, request):
    env_file = tmp_path / "user_valid.env"

    if request.param == "internal":
        env_file.write_text(
            "WO_DEVELOPER_EDITION_SOURCE=internal\n"
            "DOCKER_IAM_KEY=test-key\n"
            "REGISTRY_URL=registry.example.com\n"
            "WATSONX_APIKEY=test-llm-key\n"
            "WATSONX_SPACE_ID=test-wxai-space_id\n"
            "WXO_USER=temp\n"
            "WXO_PASS=temp\n"
            "HEALTH_TIMEOUT=1\n"
        )
    elif request.param == "myibm":
        env_file.write_text(
            "WO_DEVELOPER_EDITION_SOURCE=myibm\n"
            "WO_ENTITLEMENT_KEY=test-key\n"
            "REGISTRY_URL=registry.example.com\n"
            "WATSONX_APIKEY=test-llm-key\n"
            "WATSONX_SPACE_ID=test-wxai-space_id\n"
            "WXO_USER=temp\n"
            "WXO_PASS=temp\n"
            "HEALTH_TIMEOUT=1\n"
        )
    # TODO: add test case for orchestrate
    return env_file

@pytest.fixture(params=["internal", "myibm"])
def invalid_user_env(tmp_path, request):
    env_file = tmp_path / "user_invalid.env"
    if request.param == "internal":
        env_file.write_text(
            "WO_DEVELOPER_EDITION_SOURCE=internal\n"
            "DOCKER_IAM_KEY=invalid-key\n"
            "REGISTRY_URL=registry.example.com\n"
            "WATSONX_APIKEY=test-llm-key\n"
            "WATSONX_SPACE_ID=test-wxai-space_id\n"
            "WXO_USER=temp\n"
            "WXO_PASS=temp\n"
            "HEALTH_TIMEOUT=1\n"
        )
    elif request.param == "myibm":
        env_file.write_text(
        "WO_DEVELOPER_EDITION_SOURCE=myibm\n"
        "WO_ENTITLEMENT_KEY=invalid-key\n"
        "REGISTRY_URL=registry.example.com\n"
        "WATSONX_APIKEY=test-llm-key\n"
        "WATSONX_SPACE_ID=test-wxai-space_id\n"
        "WXO_USER=temp\n"
        "WXO_PASS=temp\n"
        "HEALTH_TIMEOUT=1\n"
    )
    # TODO: add test case for orchestrate

    return env_file

# Fixture for a valid compose file.
@pytest.fixture
def mock_compose_file(tmp_path):
    compose = tmp_path / "compose-lite.yml"
    compose.write_text("services:\n  web:\n    image: nginx")
    return compose

# Tests

def test_run_compose_lite_success():
    mock_env_file = Path("/tmp/test.env")

    with patch.object(EnvService, "prepare_clean_env") as mock_prepare, \
         patch.object(EnvService, "read_env_file", return_value={"DBTAG": None}) as mock_read, \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.DockerComposeCore") as mock_compose, \
         patch.object(Path, "unlink") as mock_unlink, \
         patch.object(Path, "exists", return_value=True):

        mock_compose_instance = mock_compose.return_value

        mock_service_result = MagicMock()
        mock_service_result.returncode = 0
        mock_service_result.stderr = b""
        mock_compose_instance.service_up.return_value = mock_service_result
        mock_compose_instance.services_up.return_value = mock_service_result

        run_compose_lite(mock_env_file, env_service=EnvService(Config()))

        mock_prepare.assert_called_once_with(mock_env_file)
        mock_read.assert_called_once_with(mock_env_file)
        mock_compose_instance.service_up.assert_called_once()
        mock_compose_instance.services_up.assert_called_once()
        mock_unlink.assert_called_once() 


def test_run_compose_lite_failure():
    mock_env_file = Path("/tmp/test.env")

    # Patch EnvService methods and DockerComposeCore to simulate failure
    with patch.object(EnvService, "prepare_clean_env") as mock_prepare, \
         patch.object(EnvService, "read_env_file", return_value={"DBTAG": None}) as mock_read, \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.DockerComposeCore") as mock_compose, \
         patch.object(Path, "unlink") as mock_unlink, \
         patch.object(Path, "exists", return_value=True):

        mock_compose_instance = mock_compose.return_value
        mock_service_result = MagicMock()
        mock_service_result.returncode = 1
        mock_service_result.stderr = b"DB container failed"
        mock_compose_instance.service_up.return_value = mock_service_result
        mock_compose_instance.services_up.return_value = mock_service_result

        with pytest.raises(SystemExit):
            run_compose_lite(mock_env_file, env_service=EnvService(Config()))

        mock_prepare.assert_called_once_with(mock_env_file)
        mock_read.assert_called_once_with(mock_env_file)
        mock_compose_instance.service_up.assert_called_once()
        mock_unlink.assert_not_called()

def test_run_compose_lite_success_langfuse_true():
    mock_env_file = Path("/tmp/test.env")

    with patch("subprocess.run") as mock_run, \
         skip_terms_and_conditions(), \
         patch.object(Path, "unlink") as mock_unlink, \
         patch.object(Path, "exists", return_value=True), \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.DockerComposeCore") as mock_docker_compose_core, \
         patch("ibm_watsonx_orchestrate.utils.docker_utils.get_vm_manager") as mock_get_vm_manager:

        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"tag_name": "v1.0.0"}'

        # Mock DockerComposeCore instance
        mock_compose_instance = mock_docker_compose_core.return_value

        # Mock successful DB start
        mock_service_up_result = MagicMock(returncode=0, stderr="")
        mock_compose_instance.service_up.return_value = mock_service_up_result

        # Mock successful services_up
        mock_services_up_result = MagicMock(returncode=0, stderr=b"")
        mock_compose_instance.services_up.return_value = mock_services_up_result

        run_compose_lite(
            mock_env_file,
            experimental_with_langfuse=True,
            env_service=EnvService(Config())
        )

        mock_docker_compose_core.assert_called_once()
        mock_compose_instance.service_up.assert_called_once_with(
            service_name="wxo-server-db",
            friendly_name="WxO Server DB",
            final_env_file=mock_env_file,
            compose_env=os.environ
        )
        mock_compose_instance.services_up.assert_called_once()
        mock_unlink.assert_called()

def test_run_compose_lite_success_langfuse_false():
    mock_env_file = Path("/tmp/test.env")

    with patch("subprocess.run") as mock_run, \
         skip_terms_and_conditions(), \
         patch.object(Path, "unlink") as mock_unlink, \
         patch.object(Path, "exists", return_value=True), \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.DockerComposeCore") as mock_docker_compose_core, \
         patch("ibm_watsonx_orchestrate.utils.docker_utils.get_vm_manager") as mock_get_vm_manager:

        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"tag_name": "v1.0.0"}'

        mock_compose_instance = mock_docker_compose_core.return_value

        # DB container
        mock_service_up_result = MagicMock()
        mock_service_up_result.returncode = 0
        mock_service_up_result.stderr = ""
        mock_compose_instance.service_up.return_value = mock_service_up_result

        # remaining services
        mock_services_up_result = MagicMock()
        mock_services_up_result.returncode = 0
        mock_services_up_result.stderr = b""
        mock_compose_instance.services_up.return_value = mock_services_up_result

        run_compose_lite(
            mock_env_file,
            experimental_with_langfuse=False,
            env_service=EnvService(Config())
        )

        # Ensure the temporary env file was removed
        mock_unlink.assert_called()

def test_run_compose_lite_success_langfuse_true_commands(mock_compose_file):
    """Test run_compose_lite executes correct docker compose commands under Lima or WSL."""
    mock_env_file = Path("test.env")

    with patch("subprocess.run") as mock_run, \
         skip_terms_and_conditions(), \
         patch.object(EnvService, "get_compose_file") as mock_get_compose_file, \
         patch.object(Path, "unlink") as mock_unlink, \
         patch.object(Path, "exists", return_value=True), \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.DockerComposeCore") as mock_docker_compose_core, \
         patch("ibm_watsonx_orchestrate.utils.docker_utils.get_vm_manager") as mock_get_vm_manager:

        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"tag_name": "v1.0.0"}'
        mock_get_compose_file.return_value = mock_compose_file

        mock_compose_instance = mock_docker_compose_core.return_value

        # DB container
        mock_service_up_result = MagicMock()
        mock_service_up_result.returncode = 0
        mock_service_up_result.stderr = ""
        mock_compose_instance.service_up.return_value = mock_service_up_result

        mock_services_up_result = MagicMock()
        mock_services_up_result.returncode = 0
        mock_services_up_result.stderr = b""
        mock_compose_instance.services_up.return_value = mock_services_up_result

        run_compose_lite(
            mock_env_file,
            experimental_with_langfuse=True,
            env_service=EnvService(Config())
        )

        # Assert DB container started
        mock_compose_instance.service_up.assert_called_once_with(
            service_name="wxo-server-db",
            friendly_name="WxO Server DB",
            final_env_file=mock_env_file,
            compose_env=os.environ
        )

        # Assert other services started with the correct profiles
        expected_profiles = ["langfuse"]
        mock_compose_instance.services_up.assert_called_once_with(
            expected_profiles,
            mock_env_file,
            ["--scale", "ui=0"]
        )

        mock_unlink.assert_called_once()

def test_run_compose_lite_success_docproc_true():
    mock_env_file = Path("/tmp/test.env")

    with patch("subprocess.run") as mock_run, \
         skip_terms_and_conditions(), \
         patch.object(Path, "unlink") as mock_unlink, \
         patch.object(Path, "exists", return_value=True), \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.DockerComposeCore") as mock_docker_compose_core, \
         patch("ibm_watsonx_orchestrate.utils.docker_utils.get_vm_manager") as mock_get_vm_manager:

        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"tag_name": "v1.0.0"}'

        mock_compose_instance = mock_docker_compose_core.return_value

        mock_service_up_result = MagicMock()
        mock_service_up_result.returncode = 0
        mock_service_up_result.stderr = ""
        mock_compose_instance.service_up.return_value = mock_service_up_result

        mock_services_up_result = MagicMock()
        mock_services_up_result.returncode = 0
        mock_services_up_result.stderr = b""
        mock_compose_instance.services_up.return_value = mock_services_up_result

        run_compose_lite(
            mock_env_file,
            with_doc_processing=True,
            env_service=EnvService(Config())
        )

        mock_compose_instance.service_up.assert_called_once_with(
            service_name="wxo-server-db",
            friendly_name="WxO Server DB",
            final_env_file=mock_env_file,
            compose_env=os.environ
        )

        # Assert services_up called with docproc profile
        expected_profiles = ["docproc"]
        mock_compose_instance.services_up.assert_called_once_with(
            expected_profiles,
            mock_env_file,
            ["--scale", "ui=0"]
        )

        mock_unlink.assert_called_once()


def test_run_compose_lite_success_docproc_false():
    mock_env_file = Path("/tmp/test.env")
    with patch("subprocess.run") as mock_run, \
         skip_terms_and_conditions(), \
         patch.object(Path, "unlink") as mock_unlink, \
         patch.object(Path, "exists", return_value=True), \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.DockerComposeCore") as mock_docker_compose_core, \
         patch("ibm_watsonx_orchestrate.utils.docker_utils.get_vm_manager") as mock_get_vm_manager:

        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"tag_name": "v1.0.0"}'

        mock_compose_instance = mock_docker_compose_core.return_value

        mock_service_up_result = MagicMock()
        mock_service_up_result.returncode = 0
        mock_service_up_result.stderr = ""
        mock_compose_instance.service_up.return_value = mock_service_up_result

        mock_services_up_result = MagicMock()
        mock_services_up_result.returncode = 0
        mock_services_up_result.stderr = b""
        mock_compose_instance.services_up.return_value = mock_services_up_result

        run_compose_lite(
            mock_env_file,
            with_doc_processing=False,
            env_service=EnvService(Config())
        )

        mock_compose_instance.service_up.assert_called_once_with(
            service_name="wxo-server-db",
            friendly_name="WxO Server DB",
            final_env_file=mock_env_file,
            compose_env=os.environ
        )

        mock_compose_instance.services_up.assert_called_once_with(
            [],
            mock_env_file,
            ["--scale", "ui=0"]
        )

        mock_unlink.assert_called_once()

def test_run_compose_lite_success_ai_builder_true():
    mock_env_file = Path("/tmp/test.env")

    with patch("subprocess.run") as mock_run, \
        skip_terms_and_conditions(), \
        patch.object(Path, "unlink") as mock_unlink, \
        patch.object(Path, "exists", return_value=True), \
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.DockerComposeCore") as mock_docker_compose_core, \
        patch("ibm_watsonx_orchestrate.utils.docker_utils.get_vm_manager") as mock_get_vm_manager:

        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"tag_name": "v1.0.0"}'

        mock_compose_instance = mock_docker_compose_core.return_value

        mock_service_up_result = MagicMock()
        mock_service_up_result.returncode = 0
        mock_service_up_result.stderr = ""
        mock_compose_instance.service_up.return_value = mock_service_up_result

        mock_services_up_result = MagicMock()
        mock_services_up_result.returncode = 0
        mock_services_up_result.stderr = b""
        mock_compose_instance.services_up.return_value = mock_services_up_result

        run_compose_lite(
            mock_env_file,
            with_ai_builder=True,
            env_service=EnvService(Config())
        )

        mock_compose_instance.service_up.assert_called_once_with(
            service_name="wxo-server-db",
            friendly_name="WxO Server DB",
            final_env_file=mock_env_file,
            compose_env=os.environ
        )

        # Assert services_up called with docproc profile
        expected_profiles = ["agent-builder"]
        mock_compose_instance.services_up.assert_called_once_with(
            expected_profiles,
            mock_env_file,
            ["--scale", "ui=0"]
        )

        mock_unlink.assert_called_once()


def test_run_compose_lite_success_ai_builder_false():
    mock_env_file = Path("/tmp/test.env")
    with patch("subprocess.run") as mock_run, \
        skip_terms_and_conditions(), \
        patch.object(Path, "unlink") as mock_unlink, \
        patch.object(Path, "exists", return_value=True), \
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.DockerComposeCore") as mock_docker_compose_core, \
        patch("ibm_watsonx_orchestrate.utils.docker_utils.get_vm_manager") as mock_get_vm_manager:

        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"tag_name": "v1.0.0"}'

        mock_compose_instance = mock_docker_compose_core.return_value

        mock_service_up_result = MagicMock()
        mock_service_up_result.returncode = 0
        mock_service_up_result.stderr = ""
        mock_compose_instance.service_up.return_value = mock_service_up_result

        mock_services_up_result = MagicMock()
        mock_services_up_result.returncode = 0
        mock_services_up_result.stderr = b""
        mock_compose_instance.services_up.return_value = mock_services_up_result

        run_compose_lite(
            mock_env_file,
            with_ai_builder=False,
            env_service=EnvService(Config())
        )

        mock_compose_instance.service_up.assert_called_once_with(
            service_name="wxo-server-db",
            friendly_name="WxO Server DB",
            final_env_file=mock_env_file,
            compose_env=os.environ
        )

        mock_compose_instance.services_up.assert_called_once_with(
            [],
            mock_env_file,
            ["--scale", "ui=0"]
        )

        mock_unlink.assert_called_once()


# def test_cli_start_success(valid_user_env, mock_compose_file, caplog):
#     with (
#         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.wait_for_wxo_server_health_check", return_value=True),
#         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_compose_lite", return_value={"status": "ok"}),
#         patch("ibm_watsonx_orchestrate.developer_edition.vm_host.lima._ensure_lima_installed", return_value=None),
#         patch("ibm_watsonx_orchestrate.developer_edition.vm_host.lima.subprocess.run"),
#         patch("ibm_watsonx_orchestrate.utils.docker_utils.subprocess.run"),
#         patch("sys.exit", side_effect=lambda code=None: None),
#         patch.object(EnvService, "get_default_env_file", return_value=valid_user_env),
#         patch.object(EnvService, "get_compose_file", return_value=mock_compose_file),
#         skip_terms_and_conditions()
#     ):
#         result = runner.invoke(server_app, ["start", "--env-file", str(valid_user_env)])

#         assert result.exit_code == 0
#         assert "ok" in str(result.output) or "ok" in caplog.text

def test_cli_start_success_simple(tmp_path, caplog): # Add caplog here
    env_file = tmp_path / "user_valid.env"
    env_file.write_text("SOME_VAR=some_value\nWXO_USER=testuser\nWXO_PASS=testpass\nHEALTH_TIMEOUT=1")

    mock_vm_manager = MagicMock()
    mock_vm_manager.start_server.return_value = None

    with (
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.confirm_accepts_license_agreement"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.EnvService"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager", return_value=mock_vm_manager),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_compose_lite"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_db_migration"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.wait_for_wxo_server_health_check", return_value=True),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.refresh_local_credentials"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.DockerLoginService"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.copy_files_to_cache"),
        patch("sys.exit", side_effect=lambda code: None if code == 0 else sys.exit(code)),
    ):
        mock_env_service_instance = MagicMock()
        mock_env_service_instance.get_user_env.return_value = {"WXO_USER": "testuser", "WXO_PASS": "testpass", "HEALTH_TIMEOUT": "1"}
        mock_env_service_instance.get_dev_edition_source_core.return_value = "local"
        mock_env_service_instance.prepare_server_env_vars.return_value = {"WXO_USER": "testuser", "WXO_PASS": "testpass", "HEALTH_TIMEOUT": "1"}
        mock_env_service_instance.write_merged_env_file.return_value = env_file

        with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.EnvService", return_value=mock_env_service_instance):
            result = runner.invoke(server_app, ["start", "--env-file", str(env_file), "--accept-terms-and-conditions"])

        assert result.exit_code == 0
        assert "Orchestrate services initialized successfully" in caplog.text
        assert "Running docker compose-up..." in caplog.text


def test_cli_start_missing_credentials(caplog):
    with skip_terms_and_conditions():
        result = runner.invoke(
            server_app,
            ["start"],
            env={"PATH": os.environ.get("PATH", "")}
        )

        captured = caplog.text


        assert result.exit_code == 1
        assert "Missing required model access environment variables" in captured

def test_cli_stop_command(valid_user_env):
    with patch.object(DockerUtils, "ensure_docker_installed", return_value=None), \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_compose_lite_down") as mock_down, \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager") as mock_get_vm, \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.stop_virtual_machine") as stop_virtual_machine, \
         skip_terms_and_conditions():
        
        dummy_vm = MagicMock()
        dummy_vm.is_server_running.return_value = True
        mock_get_vm.return_value = dummy_vm

        result = runner.invoke(
            server_app,
            ["stop", "--env-file", str(valid_user_env)]
        )

        assert result.exit_code == 0
        stop_virtual_machine.assert_called_once_with(keep_vm=False)
        mock_down.assert_called_once()

def test_cli_reset_command(valid_user_env):
    with patch.object(DockerUtils, "ensure_docker_installed", return_value=None), \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_compose_lite_down") as mock_down, \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager") as mock_get_vm, \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.stop_virtual_machine") as stop_virtual_machine, \
         skip_terms_and_conditions(), \
         patch.object(EnvService, "write_merged_env_file") as mock_write_env:
        
        dummy_vm = MagicMock()
        dummy_vm.start_server.return_value = MagicMock()
        mock_get_vm.return_value = dummy_vm

        temp_env_path = Path("/tmp/tmpenv.env")
        mock_write_env.return_value = temp_env_path
        
        result = runner.invoke(
            server_app,
            ["reset", "--env-file", str(valid_user_env)]
        )
        assert result.exit_code == 0
        stop_virtual_machine.assert_called_once_with(keep_vm=False)
        mock_down.assert_called_once_with(final_env_file=temp_env_path, is_reset=True)

def test_missing_default_env_file(caplog):
    with patch.object(EnvService, "get_default_env_file") as mock_default, \
            skip_terms_and_conditions():
        mock_default.return_value = Path("/non/existent/path")
        result = runner.invoke(server_app, ["start"])

        captured = caplog.text

        assert result.exit_code == 1
        assert "Missing required model access environment variables" in captured

def test_invalid_docker_credentials(invalid_user_env):
    """
    Test that the CLI handles invalid Docker credentials correctly.
    """
    # Patch subprocess.run to simulate Docker login failure
    with patch("subprocess.run") as mock_run, skip_terms_and_conditions():
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = b"Invalid credentials"

        result = runner.invoke(
            server_app,
            ["start", "--env-file", str(invalid_user_env)],
            catch_exceptions=True
        )

        assert result.exit_code == 1

        assert b"Invalid credentials" in mock_run.return_value.stderr


def test_missing_compose_file(valid_user_env):
    with patch("ibm_watsonx_orchestrate.developer_edition.vm_host.lima._ensure_lima_installed"), \
         patch.object(EnvService, "get_compose_file", return_value=Path("/non/existent/compose.yml")), \
         patch("sys.exit", side_effect=lambda code=None: None), \
         skip_terms_and_conditions():

        result = runner.invoke(
            server_app,
            ["start", "--env-file", str(valid_user_env)]
        )

        # Only check exit code
        assert result.exit_code == 1


def test_cli_command_failure(caplog):
    with (patch("subprocess.run") as mock_run, skip_terms_and_conditions()):
        mock_run.return_value.returncode = 1
        result = runner.invoke(server_app, ["start"])
    
    captured = caplog.text

    assert result.exit_code == 1
    assert "Missing required model access environment variables" in captured

def test_run_db_migration_success():
    with skip_terms_and_conditions(), \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.MigrationsManager") as mock_migration_manager, \
         patch("sys.exit") as mock_exit:

        dummy_manager = MagicMock()
        dummy_manager.run_orchestrate_migrations.return_value = None
        dummy_manager.run_observabilty_migrations.return_value = None        
        dummy_manager.run_langflow_migrations.return_value = None
        dummy_manager.run_architect_migrations.return_value = None
        dummy_manager.run_mcp_gateway_migrations.return_value = None
        mock_migration_manager.return_value = dummy_manager

        run_db_migration()

        assert mock_migration_manager.called
        assert dummy_manager.run_orchestrate_migrations.called
        assert dummy_manager.run_observability_migrations.called
        assert dummy_manager.run_mcp_gateway_migrations.called
        assert not dummy_manager.run_langflow_migrations.called
        assert not dummy_manager.run_architect_migrations.called
        mock_exit.assert_not_called()

def test_run_db_migration_with_ai_builder():
    with skip_terms_and_conditions(), \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.MigrationsManager") as mock_migration_manager,\
         patch("sys.exit") as mock_exit:

        dummy_manager = MagicMock()
        dummy_manager.run_orchestrate_migrations.return_value = None
        dummy_manager.run_observabilty_migrations.return_value = None        
        dummy_manager.run_langflow_migrations.return_value = None
        dummy_manager.run_architect_migrations.return_value = None
        dummy_manager.run_mcp_gateway_migrations.return_value = None
        mock_migration_manager.return_value = dummy_manager

        run_db_migration(with_ai_builder=True)

        assert mock_migration_manager.called
        assert dummy_manager.run_orchestrate_migrations.called
        assert dummy_manager.run_observability_migrations.called
        assert dummy_manager.run_mcp_gateway_migrations.called
        assert not dummy_manager.run_langflow_migrations.called
        assert dummy_manager.run_architect_migrations.called
        mock_exit.assert_not_called()

# Purge VM
def test_server_purge_success(monkeypatch):
    """Test `server purge` CLI command when VM exists and deletion succeeds."""
    mock_vm = MagicMock()
    mock_vm.delete_server.return_value = True
    monkeypatch.setattr("ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager", lambda **kwargs: mock_vm)

    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.logger") as mock_logger:
        result = runner.invoke(server_app, ["purge"], catch_exceptions=True)

        assert result.exit_code == 0

        mock_vm.delete_server.assert_called_once()

        mock_logger.info.assert_any_call("VM and associated directories deleted successfully.")

def test_server_purge_failure(monkeypatch):
    mock_vm = MagicMock()
    mock_vm.delete_server.return_value = False
    monkeypatch.setattr(
        "ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager",
        lambda **kwargs: mock_vm
    )

    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.logger") as mock_logger:
        result = runner.invoke(server_app, ["purge"], catch_exceptions=True)
        assert result.exit_code == 1
        mock_logger.error.assert_any_call("Failed to Delete VM.")

def test_server_purge_native():
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager", return_value=NativeDockerManager()):
        result = runner.invoke(server_app, ["purge"], catch_exceptions=True)
        assert result.exit_code == 1
        assert str(result.exception) == "Cannot delete VM host when using user managed docker"

# Edit VM
def test_server_edit_success(monkeypatch):
    """Test `server edit` CLI command when VM edit succeeds."""
    mock_vm = MagicMock()
    mock_vm.edit_server.return_value = True
    monkeypatch.setattr(
        "ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager",
        lambda **kwargs: mock_vm
    )

    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.logger") as mock_logger, \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.Progress") as mock_progress, \
         patch("rich.console.Console") as mock_console:
        
        result = runner.invoke(server_app, ["edit", "--cpus", "4", "--memory", "8"], catch_exceptions=True)
        assert result.exit_code == 0
        mock_vm.edit_server.assert_called_once_with(4, 8, None)
        mock_logger.info.assert_any_call("VM updated successfully.")


def test_server_edit_failure(monkeypatch):
    """Test `server edit` CLI command when VM edit fails."""
    mock_vm = MagicMock()
    mock_vm.edit_server.return_value = False
    monkeypatch.setattr(
        "ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager",
        lambda **kwargs: mock_vm
    )

    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.logger") as mock_logger, \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.Progress") as mock_progress, \
         patch("rich.console.Console") as mock_console:
        
        result = runner.invoke(server_app, ["edit", "--cpus", "2"], catch_exceptions=True)
        assert result.exit_code == 1
        mock_vm.edit_server.assert_called_once_with(2, None, None)
        mock_logger.error.assert_any_call("Failed to Update VM.")


def test_server_edit_native():
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager", return_value=NativeDockerManager()):
        result = runner.invoke(server_app, ["edit", "--memory", "4"], catch_exceptions=True)
        assert result.exit_code == 1
        assert str(result.exception) == "Cannot edit VM host configs when using user managed docker"

# Attach Docker
def test_server_attach_docker_success(monkeypatch):
    """Test `server attach-docker` when VM attaches successfully."""
    mock_vm = MagicMock()
    mock_vm.attach_docker_context.return_value = True

    monkeypatch.setattr(
        "ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager",
        lambda **kwargs: mock_vm
    )

    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.logger") as mock_logger:
        result = runner.invoke(server_app, ["attach-docker"], catch_exceptions=True)
        assert result.exit_code == 0
        mock_vm.attach_docker_context.assert_called_once()
        mock_logger.info.assert_any_call("Docker context successfully switched to ibm-watsonx-orchestrate.")


def test_server_attach_docker_failure(monkeypatch):
    """Test `server attach-docker` when VM attach fails."""
    mock_vm = MagicMock()
    mock_vm.attach_docker_context.return_value = False

    monkeypatch.setattr(
        "ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager",
        lambda **kwargs: mock_vm
    )

    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.logger") as mock_logger:
        result = runner.invoke(server_app, ["attach-docker"], catch_exceptions=True)
        assert result.exit_code == 1
        mock_vm.attach_docker_context.assert_called_once()
        mock_logger.error.assert_any_call("Failed to switch Docker context.")


def test_server_attach_docker_native():
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager", return_value=NativeDockerManager()):
        result = runner.invoke(server_app, ["attach-docker"], catch_exceptions=True)
        assert result.exit_code == 1
        assert str(result.exception) == "Cannot switch docker context when using user managed docker"

# Release Docker
def test_server_release_docker_success(monkeypatch):
    mock_vm = MagicMock()
    mock_vm.release_docker_context.return_value = True

    monkeypatch.setattr(
        "ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager",
        lambda **kwargs: mock_vm
    )

    monkeypatch.setattr(
        "ibm_watsonx_orchestrate.cli.commands.server.server_command.Config.read",
        lambda self, section, key: "default"
    )

    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.logger") as mock_logger:
        result = runner.invoke(server_app, ["release-docker"], catch_exceptions=True)

        assert result.exit_code == 0
        mock_vm.release_docker_context.assert_called_once()

        mock_logger.info.assert_any_call("Docker context successfully switched to default.")

def test_server_release_docker_failure(monkeypatch):
    """Test `server release-docker` when VM release fails."""
    mock_vm = MagicMock()
    mock_vm.release_docker_context.return_value = False

    monkeypatch.setattr(
        "ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager",
        lambda **kwargs: mock_vm
    )

    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.logger") as mock_logger:
        result = runner.invoke(server_app, ["release-docker"], catch_exceptions=True)
        assert result.exit_code == 1
        mock_vm.release_docker_context.assert_called_once()
        mock_logger.error.assert_any_call("Failed to switch Docker context.")


def test_server_release_docker_native():    
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager", return_value=NativeDockerManager()):
        result = runner.invoke(server_app, ["release-docker"], catch_exceptions=True)
        assert result.exit_code == 1
        assert str(result.exception) == "Cannot switch docker context when using user managed docker"

# Server logs
def test_server_logs_success(monkeypatch):
    """Test `server logs` CLI command when VM exists and logs are retrieved."""
    mock_vm = MagicMock()
    monkeypatch.setattr(
        "ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager",
        lambda **kwargs: mock_vm
    )

    result = runner.invoke(server_app, ["logs", "--id", "abc123"], catch_exceptions=True)
    assert result.exit_code == 0
    mock_vm.get_container_logs.assert_called_once_with("abc123", None)


def test_server_logs_with_name(monkeypatch):
    """Test `server logs` CLI command with container name instead of ID."""
    mock_vm = MagicMock()
    monkeypatch.setattr(
        "ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager",
        lambda **kwargs: mock_vm
    )

    result = runner.invoke(server_app, ["logs", "--name", "my-container"], catch_exceptions=True)
    assert result.exit_code == 0
    mock_vm.get_container_logs.assert_called_once_with(None, "my-container")


# SSH VM
def test_server_ssh_success(monkeypatch):
    """Test `server ssh` CLI command when VM exists."""
    mock_vm = MagicMock()
    monkeypatch.setattr(
        "ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager",
        lambda **kwargs: mock_vm
    )

    result = runner.invoke(server_app, ["ssh"], catch_exceptions=True)
    assert result.exit_code == 0
    mock_vm.ssh.assert_called_once()


def test_server_ssh_native():    
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager", return_value=NativeDockerManager()):
        result = runner.invoke(server_app, ["ssh"], catch_exceptions=True)
        assert result.exit_code == 1
        assert str(result.exception) == "Cannot ssh into VM when using user managed docker"



def test_server_start_with_doc_processing_checks_memory(monkeypatch, tmp_path):
    """Test that server start with -d flag checks and ensures sufficient memory for WSL. """
    # Create a mock .wslconfig with insufficient memory (16GB) in the temp directory, and mock the USERPROFILE environment variable
    mock_wslconfig = tmp_path / ".wslconfig"
    mock_wslconfig.write_text(
        "[wsl2]\n"
        "memory=16GB\n"
        "processors=4\n"
    )
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    
    # Create a real temporary env file for the test
    env_file = tmp_path / "test.env"
    env_file.write_text("WATSONX_APIKEY=test-key\nWATSONX_SPACE_ID=test-space")
    
    mock_vm_manager = MagicMock()
    mock_vm_manager.check_and_ensure_memory_for_doc_processing = MagicMock()
    mock_vm_manager.start_server = MagicMock()
    
    with (
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.confirm_accepts_license_agreement"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.EnvService"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager", return_value=mock_vm_manager),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_compose_lite"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_db_migration"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.wait_for_wxo_server_health_check", return_value=True),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.DockerLoginService"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.copy_files_to_cache", return_value=env_file),
    ):
        mock_env_service_instance = MagicMock()
        mock_env_service_instance.get_user_env.return_value = {
            "WATSONX_APIKEY": "test-key",
            "WATSONX_SPACE_ID": "test-space",
            "WXO_USER": "testuser", 
            "WXO_PASS": "testpass"  
        }
        mock_env_service_instance.get_dev_edition_source_core.return_value = "internal"
        mock_env_service_instance.prepare_server_env_vars.return_value = {
            "WATSONX_APIKEY": "test-key",
            "WATSONX_SPACE_ID": "test-space",
            "WXO_USER": "testuser",  
            "WXO_PASS": "testpass",  
            "HEALTH_TIMEOUT": "1"    
        }
        mock_env_service_instance.write_merged_env_file.return_value = env_file
        
        with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.EnvService", return_value=mock_env_service_instance):
            # Import and call server_start with doc processing flag
            from ibm_watsonx_orchestrate.cli.commands.server.server_command import server_start
            
            server_start(
                user_env_file=None,
                experimental_with_langfuse=False,
                experimental_with_ibm_telemetry=False,
                persist_env_secrets=False,
                accept_terms_and_conditions=False,
                with_doc_processing=True,
                custom_compose_file=None,
                with_voice=False,
                with_connections_ui=False,
                with_langflow=False,
                with_ai_builder=False
            )
        
        # Verify that check_and_ensure_memory_for_doc_processing was called with min_memory_gb=24 and that start_server was called
        mock_vm_manager.check_and_ensure_memory_for_doc_processing.assert_called_once_with(min_memory_gb=24)
        mock_vm_manager.start_server.assert_called_once()

def test_server_start_with_doc_processing_checks_memory_lima(monkeypatch, tmp_path):
    """Test that server start with -d flag checks and ensures sufficient memory for Lima (macOS/Linux)."""
    # Create a mock lima.yaml with insufficient memory (16GB) in the temp directory
    lima_dir = tmp_path / ".lima" / "orchestrate"
    lima_dir.mkdir(parents=True)
    lima_yaml = lima_dir / "lima.yaml"
    lima_yaml.write_text(
        "memory: 16GiB\n"
        "cpus: 4\n"
        "disk: 100GiB\n"
    )

    # Create the .cache/orchestrate directory that cleanup_orchestrate_cache expects
    cache_dir = tmp_path / ".cache" / "orchestrate"
    cache_dir.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path))
    
    # Create a real temporary env file for the test
    env_file = tmp_path / "test.env"
    env_file.write_text("WATSONX_APIKEY=test-key\nWATSONX_SPACE_ID=test-space")
    
    mock_vm_manager = MagicMock()
    mock_vm_manager.check_and_ensure_memory_for_doc_processing = MagicMock()
    mock_vm_manager.start_server = MagicMock()
    
    with (
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.confirm_accepts_license_agreement"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.EnvService"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.get_vm_manager", return_value=mock_vm_manager),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_compose_lite"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_db_migration"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.wait_for_wxo_server_health_check", return_value=True),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.DockerLoginService"),
        patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.copy_files_to_cache", return_value=env_file),
    ):
        mock_env_service_instance = MagicMock()
        mock_env_service_instance.get_user_env.return_value = {
            "WATSONX_APIKEY": "test-key",
            "WATSONX_SPACE_ID": "test-space",
            "WXO_USER": "testuser",
            "WXO_PASS": "testpass"
        }
        mock_env_service_instance.get_dev_edition_source_core.return_value = "internal"
        mock_env_service_instance.prepare_server_env_vars.return_value = {
            "WATSONX_APIKEY": "test-key",
            "WATSONX_SPACE_ID": "test-space",
            "WXO_USER": "testuser",
            "WXO_PASS": "testpass",
            "HEALTH_TIMEOUT": "1"
        }
        mock_env_service_instance.write_merged_env_file.return_value = env_file
        
        with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.EnvService", return_value=mock_env_service_instance):
            # Import and call server_start with doc processing flag
            from ibm_watsonx_orchestrate.cli.commands.server.server_command import server_start
            
            server_start(
                user_env_file=None,
                experimental_with_langfuse=False,
                experimental_with_ibm_telemetry=False,
                persist_env_secrets=False,
                accept_terms_and_conditions=False,
                with_doc_processing=True,  # This is the key flag we're testing
                custom_compose_file=None,
                with_voice=False,
                with_connections_ui=False,
                with_langflow=False,
                with_ai_builder=False
            )
        
        # Verify that check_and_ensure_memory_for_doc_processing was called with min_memory_gb=24 and start_server was called
        mock_vm_manager.check_and_ensure_memory_for_doc_processing.assert_called_once_with(min_memory_gb=24)
        mock_vm_manager.start_server.assert_called_once()



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

def test_server_start_asks_for_tc_interactively():
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.confirm_accepts_license_agreement") as tc_mock:
        tc_mock.side_effect = lambda accepts, cli_config: exit(1)
        from ibm_watsonx_orchestrate.cli.commands.server.server_command import server_start
        with pytest.raises(SystemExit):
            server_start(accept_terms_and_conditions=False)
        tc_mock.assert_called_once()
        assert tc_mock.call_args[0][0] == False


def test_server_start_asks_for_tc_via_args():
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.confirm_accepts_license_agreement") as tc_mock:
        tc_mock.side_effect = lambda accepts, cli_config: exit(1)
        from ibm_watsonx_orchestrate.cli.commands.server.server_command import server_start
        with pytest.raises(SystemExit):
            server_start(accept_terms_and_conditions=True)
        tc_mock.assert_called_once()
        assert tc_mock.call_args[0][0] == True


def test_confirm_accepts_license_agreement_asks_if_not_already_accepted(capsys, monkeypatch):
    from ibm_watsonx_orchestrate.cli.commands.server.server_command import confirm_accepts_license_agreement
    cfg = MockConfig2()
    monkeypatch.setattr('builtins.input', lambda _: "I accept")
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.logger") as mock_logger, \
         patch('ibm_watsonx_orchestrate.cli.commands.server.server_command.Config', lambda: cfg):
        cfg.write(LICENSE_HEADER, ENV_ACCEPT_LICENSE, False)
        confirm_accepts_license_agreement(accepts_by_argument=False, cfg=cfg)
        mock_logger.warning.assert_any_call(MatchesStringContaining('license agreement'))

        assert cfg.read(LICENSE_HEADER, ENV_ACCEPT_LICENSE) == True


def test_confirm_accepts_license_agreement_skips_if_already_accepted():
    from ibm_watsonx_orchestrate.cli.commands.server.server_command import confirm_accepts_license_agreement
    cfg = MockConfig2()
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.logger") as mock_logger, \
            patch('ibm_watsonx_orchestrate.cli.commands.server.server_command.Config', lambda: cfg):
        cfg.write(LICENSE_HEADER, ENV_ACCEPT_LICENSE, True)
        confirm_accepts_license_agreement(accepts_by_argument=False, cfg=cfg)
        mock_logger.warning.assert_not_called()

        assert cfg.read(LICENSE_HEADER, ENV_ACCEPT_LICENSE) == True

def test_confirm_exits_license_agreement_exist_if_not_accepted(capsys, monkeypatch):
    from ibm_watsonx_orchestrate.cli.commands.server.server_command import confirm_accepts_license_agreement
    cfg = MockConfig2()
    monkeypatch.setattr('builtins.input', lambda _: "no")
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.logger") as mock_logger, \
            patch('ibm_watsonx_orchestrate.cli.commands.server.server_command.Config', lambda: cfg):
        cfg.write(LICENSE_HEADER, ENV_ACCEPT_LICENSE, False)
        with pytest.raises(SystemExit):
            confirm_accepts_license_agreement(accepts_by_argument=False, cfg=cfg)
        mock_logger.warning.assert_any_call(MatchesStringContaining('license agreement'))

        assert cfg.read(LICENSE_HEADER, ENV_ACCEPT_LICENSE) == False

def test_confirm_accepts_license_agreement_skips_if_accepted_via_args():
    from ibm_watsonx_orchestrate.cli.commands.server.server_command import confirm_accepts_license_agreement
    cfg = MockConfig2()
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.logger") as mock_logger, \
            patch('ibm_watsonx_orchestrate.cli.commands.server.server_command.Config', lambda: cfg):
        cfg.write(LICENSE_HEADER, ENV_ACCEPT_LICENSE, False)
        confirm_accepts_license_agreement(accepts_by_argument=True, cfg=cfg)
        mock_logger.warning.assert_any_call(MatchesStringContaining('license agreement')) # it still prints to the user, just no input

        assert cfg.read(LICENSE_HEADER, ENV_ACCEPT_LICENSE) == True