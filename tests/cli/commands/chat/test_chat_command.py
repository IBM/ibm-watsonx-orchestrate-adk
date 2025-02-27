import tempfile
from pathlib import Path
from unittest.mock import patch
from ibm_watsonx_orchestrate.cli.commands.chat import chat_command

def test_chat_start_with_env(caplog):
  env_content = (
      "DOCKER_IAM_KEY=test-key\n"
      "REGISTRY_URL=registry.example.com\n"
      "WATSONX_APIKEY=test-llm-key\n"
      "WXO_USER=temp\n"
      "WXO_PASS=temp\n"
      "HEALTH_TIMEOUT=1\n"
      "ORCHESTRATOR_AGENT_NAME=TEMP_AGENT\n"
  )
  with tempfile.NamedTemporaryFile(mode="w+", suffix=".env", delete=False) as tmp:
      tmp.write(env_content)
      tmp.flush()
      env_file_path = tmp.name

  try:
      with patch("webbrowser.open") as mock_webbrowser, \
           patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_command.run_compose_lite_down_ui"), \
           patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_command.run_compose_lite_ui") as mock_run_compose_lite_ui:
          mock_run_compose_lite_ui.return_value = True

          chat_command.chat_start(agent_name=None, user_env_file=env_file_path)
          captured = caplog.text
          
          assert "Opening chat interface at http://localhost:3000/chat-lite" in captured
          mock_webbrowser.assert_called_once_with("http://localhost:3000/chat-lite")
  finally:
      Path(env_file_path).unlink()