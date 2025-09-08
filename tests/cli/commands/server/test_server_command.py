import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from typer.testing import CliRunner
import posixpath

from ibm_watsonx_orchestrate.cli.commands.server.server_command import (
    server_app,
    run_compose_lite,
    run_db_migration
)
from ibm_watsonx_orchestrate.cli.config import LICENSE_HEADER, ENV_ACCEPT_LICENSE, Config
from ibm_watsonx_orchestrate.utils.docker_utils import DockerComposeCore
from ibm_watsonx_orchestrate.utils.environment import EnvService
from utils.matcher import MatchesStringContaining


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
    with patch("subprocess.run") as mock_run, skip_terms_and_conditions(), \
         patch.object(Path, "unlink") as mock_unlink:
        mock_run.return_value.returncode = 0
        with patch.object(Path, "exists", return_value=True):
            run_compose_lite(mock_env_file, env_service=EnvService(Config()))
            mock_unlink.assert_called()

def test_run_compose_lite_failure():
    mock_env_file = Path("/tmp/test.env")
    with patch("subprocess.run") as mock_run, skip_terms_and_conditions(), \
         patch.object(Path, "unlink") as mock_unlink:
        mock_run.return_value.returncode = 1
        with pytest.raises(SystemExit):
            run_compose_lite(mock_env_file, env_service=EnvService(Config()))
        mock_unlink.assert_not_called()

def test_run_compose_lite_success_langfuse_true():
    mock_env_file = Path("/tmp/test.env")
    with patch("subprocess.run") as mock_run, skip_terms_and_conditions(), \
        patch.object(Path, "unlink") as mock_unlink:
        mock_run.return_value.returncode = 0
        with patch.object(Path, "exists", return_value=True):
            run_compose_lite(mock_env_file, experimental_with_langfuse=True, env_service=EnvService(Config()))
            mock_unlink.assert_called()

def test_run_compose_lite_success_langfuse_false():
    mock_env_file = Path("/tmp/test.env")
    with patch("subprocess.run") as mock_run, skip_terms_and_conditions(), \
         patch.object(Path, "unlink") as mock_unlink:
        mock_run.return_value.returncode = 0
        with patch.object(Path, "exists", return_value=True):
            run_compose_lite(mock_env_file, experimental_with_langfuse=False, env_service=EnvService(Config()))
            mock_unlink.assert_called()

def test_run_compose_lite_success_langfuse_true_commands(mock_compose_file):
    mock_env_file = Path("test.env")
    with patch("subprocess.run") as mock_run, \
        skip_terms_and_conditions(), \
        patch.object(EnvService, "get_compose_file") as mock_compose, \
        patch.object(Path, "unlink") as mock_unlink:
        mock_run.return_value.returncode = 0
        mock_compose.return_value = mock_compose_file
        with patch.object(Path, "exists", return_value=True):
            run_compose_lite(mock_env_file, experimental_with_langfuse=True, env_service=EnvService(Config()))
            mock_run.assert_called_with(
                ['docker', 'compose', '--profile', 'langfuse', '-f', posixpath.abspath(mock_compose_file), '--env-file', posixpath.basename(mock_env_file), 'up', '--scale', 'ui=0', '--scale', 'cpe=0', '-d', '--remove-orphans'],
                capture_output=False
            )

def test_run_compose_lite_success_docproc_true():
    mock_env_file = Path("/tmp/test.env")
    with patch("subprocess.run") as mock_run, skip_terms_and_conditions(), \
        patch.object(Path, "unlink") as mock_unlink:
        mock_run.return_value.returncode = 0
        with patch.object(Path, "exists", return_value=True):
            run_compose_lite(mock_env_file, with_doc_processing=True, env_service=EnvService(Config()))
            mock_unlink.assert_called()

def test_run_compose_lite_success_docproc_false():
    mock_env_file = Path("/tmp/test.env")
    with patch("subprocess.run") as mock_run, skip_terms_and_conditions(), \
        patch.object(Path, "unlink") as mock_unlink:
        mock_run.return_value.returncode = 0
        with patch.object(Path, "exists", return_value=True):
            run_compose_lite(mock_env_file, with_doc_processing=False, env_service=EnvService(Config()))
            mock_unlink.assert_called()

def test_cli_start_success(valid_user_env, mock_compose_file, caplog):
    with patch("subprocess.run") as mock_run, \
         skip_terms_and_conditions(), \
         patch.object(EnvService, "get_default_env_file") as mock_default, \
         patch.object(EnvService, "get_compose_file") as mock_compose, \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.wait_for_wxo_server_health_check") as mock_wait_for_wxo_server_health_check, \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_compose_lite") as mock_run_compose_lite:
        mock_wait_for_wxo_server_health_check.return_value = True
        mock_default.return_value = valid_user_env
        mock_compose.return_value = mock_compose_file
        mock_run.return_value.returncode = 0
        
        result = runner.invoke(
            server_app,
            ["start", "--env-file", str(valid_user_env)]
        )

        captured = caplog.text

        assert result.exit_code == 0
        assert "services initialized successfully" in captured

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
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_compose_lite_down") as mock_down, \
            skip_terms_and_conditions():
        result = runner.invoke(
            server_app,
            ["stop", "--env-file", str(valid_user_env)]
        )
        assert result.exit_code == 0
        mock_down.assert_called_once()

def test_cli_reset_command(valid_user_env):
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_compose_lite_down") as mock_down, \
         skip_terms_and_conditions(), \
         patch.object(EnvService, "write_merged_env_file") as mock_write_env:
        temp_env_path = Path("/tmp/tmpenv.env")
        mock_write_env.return_value = temp_env_path
        
        result = runner.invoke(
            server_app,
            ["reset", "--env-file", str(valid_user_env)]
        )
        assert result.exit_code == 0
        mock_down.assert_called_once_with(final_env_file=temp_env_path, is_reset=True)

def test_cli_logs_command(valid_user_env):
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_compose_lite_logs") as mock_logs, \
            skip_terms_and_conditions():
        result = runner.invoke(
            server_app,
            ["logs", "--env-file", str(valid_user_env)]
        )
        assert result.exit_code == 0
        mock_logs.assert_called_once()

def test_missing_default_env_file(caplog):
    with patch.object(EnvService, "get_default_env_file") as mock_default, \
            skip_terms_and_conditions():
        mock_default.return_value = Path("/non/existent/path")
        result = runner.invoke(server_app, ["start"])

        captured = caplog.text

        assert result.exit_code == 1
        assert "Missing required model access environment variables" in captured

def test_invalid_docker_credentials(invalid_user_env, caplog):
    with patch("subprocess.run") as mock_run, \
            skip_terms_and_conditions():
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = b"Invalid credentials"
        result = runner.invoke(
            server_app,
            ["start", "--env-file", str(invalid_user_env)]
        )

        captured = caplog.text

        assert result.exit_code == 1
        assert "Invalid credentials" in captured

def test_missing_compose_file(valid_user_env, caplog):
  with patch.object(EnvService, "get_compose_file") as mock_compose, \
          skip_terms_and_conditions(), \
          patch("subprocess.run") as mock_run:
      mock_compose.return_value = Path("/non/existent/compose.yml")
      mock_run.return_value.returncode = 1
      mock_run.return_value.stderr = b"Error response from daemon: Get \"https://registry.example.com/v2/\": dial tcp: lookup registry.example.com on 192.168.5.3:53: lame referral\n"
      result = runner.invoke(server_app, ["start", "--env-file", str(valid_user_env)])
      
      captured = caplog.text

      assert result.exit_code == 1
      assert "Error logging into Docker:" in captured

def test_cli_command_failure(caplog):
    with (patch("subprocess.run") as mock_run, skip_terms_and_conditions()):
        mock_run.return_value.returncode = 1
        result = runner.invoke(server_app, ["start"])
    
    captured = caplog.text

    assert result.exit_code == 1
    assert "Missing required model access environment variables" in captured

def test_run_db_migration_success():
    with patch.object(EnvService, "get_compose_file") as mock_compose, \
             skip_terms_and_conditions(), \
             patch.object(DockerComposeCore, "_DockerComposeCore__ensure_docker_compose_installed") as mock_docker_compose, \
             patch("subprocess.run") as mock_subprocess, \
             patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.logger") as server_command_logger, \
             patch("ibm_watsonx_orchestrate.utils.docker_utils.logger") as compose_core_logger:
        
        mock_compose.return_value = "/fake/path/docker-compose.yml"
        mock_docker_compose.return_value = ["docker-compose"]
        
        mock_subprocess.return_value = MagicMock(returncode=0, stderr=b"")

        run_db_migration()

        mock_compose.assert_called_once()
        mock_docker_compose.assert_called_once()
        mock_subprocess.assert_called_once()
        compose_core_logger.info.assert_any_call("Running Database Migration...")
        server_command_logger.info.assert_any_call("Migration ran successfully.")

def test_run_db_migration_failure():
    with patch.object(EnvService, "get_compose_file") as mock_compose, \
         patch.object(DockerComposeCore, "_DockerComposeCore__ensure_docker_compose_installed") as mock_docker_compose, \
         skip_terms_and_conditions(), \
         patch("subprocess.run") as mock_subprocess, \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.logger") as mock_logger:

        mock_compose.return_value = "/fake/path/docker-compose.yml"
        mock_docker_compose.return_value = ["docker-compose"]

        mock_subprocess.return_value = MagicMock(returncode=1, stderr=b"Mocked migration failure.")

        with pytest.raises(SystemExit) as exc_info:
            run_db_migration()

        assert exc_info.value.code == 1

        mock_logger.error.assert_called_with(
            "Error running database migration):\nMocked migration failure."
        )

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