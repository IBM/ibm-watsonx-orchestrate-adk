import os
from pathlib import Path
from unittest.mock import patch, Mock, mock_open
import pytest
from typer.testing import CliRunner
from dotenv import dotenv_values

from ibm_watsonx_orchestrate.cli.commands.server.server_command import (
    server_app,
    ensure_docker_installed,
    docker_login,
    merge_env,
    apply_llm_api_key_defaults,
    write_merged_env_file,
    run_compose_lite,
    run_compose_lite_down,
    run_compose_lite_logs,
    get_default_env_file,
    get_compose_file
)

runner = CliRunner()

@pytest.fixture
def mock_env_files(tmp_path):
    default_env = tmp_path / "default.env"
    default_env.write_text("DEFAULT_VAR=default\nOVERLAP_VAR=default_val")
    
    user_env = tmp_path / "user.env"
    user_env.write_text("USER_VAR=user\nOVERLAP_VAR=user_val")
    
    return default_env, user_env

@pytest.fixture
def mock_compose_file(tmp_path):
    compose = tmp_path / "compose-lite.yml"
    compose.write_text("services:\n  web:\n    image: nginx")
    return compose

# Tests
def test_ensure_docker_installed_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        ensure_docker_installed()
        mock_run.assert_called_once_with(
            ["docker", "--version"],
            check=True,
            capture_output=True
        )

def test_ensure_docker_installed_failure():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError
        with pytest.raises(SystemExit) as exc:
            ensure_docker_installed()
        assert exc.value.code == 1

def test_docker_login_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        docker_login("test-key", "registry.example.com")
        mock_run.assert_called_once_with(
            ["docker", "login", "-u", "iamapikey", "--password-stdin", "registry.example.com"],
            input="test-key".encode("utf-8"),
            capture_output=True
        )

def test_docker_login_failure():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = b"Login failed"
        with pytest.raises(SystemExit) as exc:
            docker_login("bad-key", "bad-registry")
        assert exc.value.code == 1

def test_merge_env_default_only(mock_env_files):
    default_env, _ = mock_env_files
    merged = merge_env(default_env, None)
    assert merged["DEFAULT_VAR"] == "default"
    assert "USER_VAR" not in merged

def test_merge_env_with_user_file(mock_env_files):
    default_env, user_env = mock_env_files
    merged = merge_env(default_env, user_env)
    assert merged["USER_VAR"] == "user"
    assert merged["OVERLAP_VAR"] == "user_val"

def test_merge_env_environment_override(monkeypatch, mock_env_files):
    default_env, user_env = mock_env_files
    monkeypatch.setenv("OVERLAP_VAR", "env_val")
    merged = merge_env(default_env, user_env)
    assert merged["OVERLAP_VAR"] == "env_val"

def test_apply_llm_defaults():
    env = {
        "WATSONX_APIKEY": "test-key",
        "WATSONX_SPACE_ID": "test-space"
    }
    apply_llm_api_key_defaults(env)
    assert env["ASSISTANT_LLM_API_KEY"] == "test-key"
    assert env["ROUTING_LLM_SPACE_ID"] == "test-space"
    assert "ASSISTANT_EMBEDDINGS_API_KEY" in env

def test_write_merged_env_file(tmp_path):
    mock_env = {"KEY1": "value1", "KEY2": "value2"}
    with patch("tempfile.NamedTemporaryFile", new=mock_open()) as mock_temp:
        result = write_merged_env_file(mock_env)
        mock_temp().write.assert_any_call("KEY1=value1\n")
        mock_temp().write.assert_any_call("KEY2=value2\n")
        assert isinstance(result, Path)

def test_run_compose_lite_success():
    mock_env_file = Path("/tmp/test.env")
    with patch("subprocess.run") as mock_run, \
         patch.object(Path, "unlink") as mock_unlink:
        mock_run.return_value.returncode = 0
        run_compose_lite(mock_env_file)

def test_run_compose_lite_failure():
    mock_env_file = Path("/tmp/test.env")
    with patch("subprocess.run") as mock_run, \
         patch("pathlib.Path.unlink") as mock_unlink:
        mock_run.return_value.returncode = 1
        with pytest.raises(SystemExit):
            run_compose_lite(mock_env_file)
        mock_unlink.assert_not_called()

def test_cli_start_success(mock_env_files, mock_compose_file):
    default_env, user_env = mock_env_files
    with patch("subprocess.run") as mock_run, \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.get_default_env_file") as mock_default, \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.get_compose_file") as mock_compose:
        mock_default.return_value = default_env
        mock_compose.return_value = mock_compose_file
        mock_run.return_value.returncode = 0
        
        result = runner.invoke(
            server_app,
            ["start", "--env-file", str(user_env)],
            env={
                "DOCKER_IAM_KEY": "test-key",
                "REGISTRY_URL": "registry.example.com",
                "WATSONX_APIKEY": "test-llm-key"
            }
        )

        assert result.exit_code == 0
        assert "Successfully logged in" in result.output
        assert "Services started" in result.output

def test_cli_start_missing_credentials():
    result = runner.invoke(
        server_app,
        ["start"],
        env={"PATH": os.environ["PATH"]}
    )
    assert result.exit_code == 1
    assert "DOCKER_IAM_KEY is required" in result.output

def test_cli_stop_command(mock_env_files):
    default_env, user_env = mock_env_files
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_compose_lite_down") as mock_down:
        result = runner.invoke(
            server_app,
            ["stop"]
        )
        assert result.exit_code == 0
        mock_down.assert_called_once()

def test_cli_reset_command(mock_env_files):
    default_env, user_env = mock_env_files
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_compose_lite_down") as mock_down, \
         patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.write_merged_env_file") as mock_write_env:
        
        mock_write_env.return_value = Path("/var/folders/ln/ndmmgvfj5j14pc32x4t0rxmm0000gn/T/tmpod5lu281.env")
        
        result = runner.invoke(
            server_app,
            ["reset"]
        )
        
        assert result.exit_code == 0
        mock_down.assert_called_once_with(final_env_file=mock_write_env.return_value, is_reset=True)

def test_cli_logs_command(mock_env_files):
    default_env, user_env = mock_env_files
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_compose_lite_logs") as mock_logs:
        result = runner.invoke(
            server_app,
            ["logs"]
        )
        assert result.exit_code == 0
        mock_logs.assert_called_once()

def test_missing_default_env_file():
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.get_default_env_file") as mock_default:
        mock_default.return_value = Path("/non/existent/path")
        result = runner.invoke(server_app, ["start"])
        assert result.exit_code == 1
        assert "Error: DOCKER_IAM_KEY is required but not set in the environment." in result.output

def test_invalid_docker_credentials():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = b"Invalid credentials"
        result = runner.invoke(
            server_app,
            ["start"],
            env={"DOCKER_IAM_KEY": "invalid-key", "REGISTRY_URL": "registry.example.com"}
        )
        assert result.exit_code == 1
        assert "Invalid credentials" in result.output

def test_missing_compose_file():
    with patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.get_compose_file") as mock_compose:
        mock_compose.return_value = Path("/non/existent/compose.yml")
        result = runner.invoke(server_app, ["start"])
        assert result.exit_code == 1
        assert "Error: DOCKER_IAM_KEY is required but not set in the environment." in result.output

def test_env_variable_conflict_resolution(monkeypatch, mock_env_files):
    default_env, user_env = mock_env_files
    monkeypatch.setenv("OVERLAP_VAR", "env_override")
    merged = merge_env(default_env, user_env)
    assert merged["OVERLAP_VAR"] == "env_override"

def test_llm_defaults_missing_keys():
    env = {}
    apply_llm_api_key_defaults(env)
    assert "ASSISTANT_LLM_API_KEY" not in env
    assert "ROUTING_LLM_SPACE_ID" not in env

def test_cli_command_failure():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        result = runner.invoke(server_app, ["start"])
    assert result.exit_code == 1
    assert "Error: DOCKER_IAM_KEY is required but not set in the environment." in result.output