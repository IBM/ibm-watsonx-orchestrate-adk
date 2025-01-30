import os
from unittest.mock import patch
from ibm_watsonx_orchestrate.cli.commands.chat import chat_command

def test_chat_start_with_env(capsys):
    mock_env_vars = {
        "DOCKER_IAM_KEY": "test-key",
        "REGISTRY_URL": "registry.example.com",
        "WATSONX_APIKEY": "test-llm-key",
        "WXO_USER": "temp",
        "WXO_PASS": "temp",
        "HEALTH_TIMEOUT": "1",
        "ORCHESTRATOR_AGENT_NAME": "TEMP_AGENT"
    }

    with patch.dict(os.environ, mock_env_vars):
        with patch("webbrowser.open") as mock_webbrowser, \
             patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.docker_login") as mock_docker_login, \
             patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.run_compose_lite_ui") as mock_run_compose_lite_ui, \
             patch("ibm_watsonx_orchestrate.cli.commands.server.server_command.wait_for_wxo_server_health_check") as mock_health_check:
            
            mock_docker_login.return_value = None 
            mock_run_compose_lite_ui.return_value = True 
            mock_health_check.return_value = True 
            chat_command.chat_start(agent_name=None, user_env_file=None)
            captured = capsys.readouterr()
            assert "Opening chat interface at http://localhost:3000/chat-lite\n" in captured.out
            mock_webbrowser.assert_called_once_with("http://localhost:3000/chat-lite")
            mock_docker_login.assert_called_once_with("test-key", "registry.example.com")
            mock_health_check.assert_called_once() 