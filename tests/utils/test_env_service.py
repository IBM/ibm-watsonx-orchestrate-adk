from pathlib import Path
from unittest.mock import patch

import pytest

from ibm_watsonx_orchestrate.utils.environment import EnvService


def skip_terms_and_conditions():
    return patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.confirm_accepts_license_agreement")


@pytest.fixture
def mock_env_files(tmp_path):
    default_env = tmp_path / "default.env"
    default_env.write_text("DEFAULT_VAR=default\nOVERLAP_VAR=default_val")

    user_env = tmp_path / "user.env"
    user_env.write_text("USER_VAR=user\nOVERLAP_VAR=user_val")

    return default_env, user_env


def test_merge_env_default_only(mock_env_files):
    default_env, _ = mock_env_files
    merged = EnvService.merge_env(default_env, None)
    assert merged["DEFAULT_VAR"] == "default"
    assert "USER_VAR" not in merged

def test_merge_env_with_user_file(mock_env_files):
    default_env, user_env = mock_env_files
    merged = EnvService.merge_env(default_env, user_env)
    assert merged["USER_VAR"] == "user"
    assert merged["OVERLAP_VAR"] == "user_val"

def test_merge_env_environment_override(monkeypatch, mock_env_files):
    default_env, user_env = mock_env_files
    monkeypatch.setenv("OVERLAP_VAR", "env_val")
    merged = EnvService.merge_env(default_env, user_env)
    assert merged["OVERLAP_VAR"] == "user_val"

def test_env_variable_conflict_resolution(monkeypatch, mock_env_files):
    default_env, user_env = mock_env_files
    monkeypatch.setenv("OVERLAP_VAR", "env_override")
    merged = EnvService.merge_env(default_env, user_env)
    assert merged["OVERLAP_VAR"] == "user_val"

def test_write_merged_env_file(tmp_path):
    mock_env = {"KEY1": "value1", "KEY2": "value2"}
    result_path = EnvService.write_merged_env_file(mock_env)
    content = result_path.read_text()
    assert "KEY1=value1\n" in content
    assert "KEY2=value2\n" in content
    result_path.unlink()
    assert isinstance(result_path, Path)


def test_get_dbtag_from_architecture_arm64():
    with patch("platform.machine") as mock_machine, \
            skip_terms_and_conditions(), \
            patch.object(EnvService, "get_default_env_file") as mock_default, \
            patch("os.getenv") as mock_getenv:
        mock_default.return_value = "/fake/path/.env"
        mock_machine.return_value = "arm64"
        mock_getenv.side_effect = lambda key: "arm64-db-tag" if key == "ARM64DBTAG" else "amd-db-tag"
        result = EnvService._EnvService__get_dbtag_from_architecture(merged_env_dict={'ARM64DBTAG': 'arm64-db-tag', 'AMDDBTAG': 'amd-db-tag'})

        assert result == "arm64-db-tag"


def test_get_dbtag_from_architecture_amd64():
    with patch("platform.machine") as mock_machine, \
            skip_terms_and_conditions(), \
            patch.object(EnvService, "get_default_env_file") as mock_default, \
            patch("os.getenv") as mock_getenv:
        mock_default.return_value = "/fake/path/.env"
        mock_machine.return_value = "x86_64"
        mock_getenv.side_effect = lambda key: "arm64-db-tag" if key == "ARM64DBTAG" else "amd-db-tag"
        result = EnvService._EnvService__get_dbtag_from_architecture(merged_env_dict={'ARM64DBTAG': 'arm64-db-tag', 'AMDDBTAG': 'amd-db-tag'})

        assert result == "amd-db-tag"

def test_apply_llm_defaults():
    env = {
        "WATSONX_APIKEY": "test-key",
        "WATSONX_SPACE_ID": "test-space"
    }
    EnvService.apply_llm_api_key_defaults(env)
    assert env["ASSISTANT_LLM_API_KEY"] == "test-key"
    assert env["ROUTING_LLM_SPACE_ID"] == "test-space"
    assert "ASSISTANT_EMBEDDINGS_API_KEY" in env

def test_llm_defaults_missing_keys():
    env = {}

    with pytest.raises(RuntimeError, match="Please set at least one of `GROQ_API_KEY`, `WATSONX_APIKEY` or `WO_INSTANCE`"):
        EnvService.apply_llm_api_key_defaults(env)

