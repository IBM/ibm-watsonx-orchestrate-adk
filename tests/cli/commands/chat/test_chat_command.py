import tempfile
import pytest

from pathlib import Path
from unittest.mock import patch
from ibm_watsonx_orchestrate.cli.commands.chat import chat_command

class TestChatStart:
    def test_chat_start_with_env(self, caplog):
        env_content = (
            "DOCKER_IAM_KEY=test-key\n"
            "REGISTRY_URL=registry.example.com\n"
            "WATSONX_APIKEY=test-llm-key\n"
            "WXO_USER=temp\n"
            "WXO_PASS=temp\n"
            "HEALTH_TIMEOUT=1\n"
        )
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".env", delete=False) as tmp:
            tmp.write(env_content)
            tmp.flush()
            env_file_path = tmp.name

        try:
            with patch("webbrowser.open") as mock_webbrowser, \
               patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_command.run_compose_lite_ui") as mock_run_compose_lite_ui:
                
                mock_run_compose_lite_ui.return_value = True
                
                chat_command.chat_start(user_env_file=env_file_path)
                captured = caplog.text
                
                assert "Opening chat interface at http://localhost:3000/chat-lite" in captured
                mock_webbrowser.assert_called_once_with("http://localhost:3000/chat-lite")
        finally:
            Path(env_file_path).unlink()
    
    def test_chat_start_with_env_error(self, caplog):
        env_content = (
            "DOCKER_IAM_KEY=test-key\n"
            "REGISTRY_URL=registry.example.com\n"
            "WATSONX_APIKEY=test-llm-key\n"
            "WXO_USER=temp\n"
            "WXO_PASS=temp\n"
            "HEALTH_TIMEOUT=1\n"
        )
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".env", delete=False) as tmp:
            tmp.write(env_content)
            tmp.flush()
            env_file_path = tmp.name

        try:
            with patch("webbrowser.open") as mock_webbrowser, \
                patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_command.run_compose_lite_ui") as mock_run_compose_lite_ui:
                
                mock_run_compose_lite_ui.return_value = False
                
                chat_command.chat_start(user_env_file=env_file_path)
                captured = caplog.text
                
                assert "Opening chat interface at http://localhost:3000/chat-lite" not in captured
                mock_webbrowser.assert_not_called
                assert "Unable to start orchestrate UI chat service.  Please check error messages and logs" in captured

        finally:
            Path(env_file_path).unlink()

    def test_chat_start_without_env(self, caplog):
        with patch("webbrowser.open") as mock_webbrowser, \
            patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_command.run_compose_lite_ui") as mock_run_compose_lite_ui:
            
            mock_run_compose_lite_ui.return_value = True
            
            chat_command.chat_start("")
            captured = caplog.text
            
            assert "Opening chat interface at http://localhost:3000/chat-lite" in captured
            mock_webbrowser.assert_called_once_with("http://localhost:3000/chat-lite")

class TestChatStop:
    def test_chat_stop_with_env(self, caplog):
        env_content = (
            "DOCKER_IAM_KEY=test-key\n"
            "REGISTRY_URL=registry.example.com\n"
            "WATSONX_APIKEY=test-llm-key\n"
            "WXO_USER=temp\n"
            "WXO_PASS=temp\n"
            "HEALTH_TIMEOUT=1\n"
        )
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".env", delete=False) as tmp:
            tmp.write(env_content)
            tmp.flush()
            env_file_path = tmp.name

        try:
            with patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_command.run_compose_lite_down_ui") as mock_run_compose_lite_down_ui:
                
                chat_command.chat_stop(user_env_file=env_file_path)
                mock_run_compose_lite_down_ui.assert_called_once_with(user_env_file=Path(env_file_path))
                
                
               
        finally:
            Path(env_file_path).unlink()

class TestChatAsk:
    """Tests for the interactive chat ask command."""
    
    def test_chat_ask_single_exchange(self):
        """Test a single question-answer exchange."""
        with patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.create_run_client") as mock_create_client, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.create_threads_client") as mock_create_threads, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.Prompt.ask") as mock_prompt, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.get_agent_id_by_name") as mock_get_agent_id:
            
            mock_run_client = mock_create_client.return_value
            mock_threads_client = mock_create_threads.return_value
            mock_get_agent_id.return_value = "agent-789"
            
            # Mock one question and exit
            mock_prompt.side_effect = ["What is the weather?", "exit"]
            mock_run_client.create_run.return_value = {
                "run_id": "run-123",
                "thread_id": "thread-456"
            }
            mock_run_client.wait_for_run_completion.return_value = {
                "status": "completed",
                "run_id": "run-123"
            }
            mock_threads_client.get_thread_messages.return_value = {
                "data": [
                    {"role": "user", "content": "What is the weather?"},
                    {"role": "assistant", "content": "It's sunny today!"}
                ]
            }
            
            chat_command.chat_ask(agent_name="test-agent", include_reasoning=False)
            
            mock_get_agent_id.assert_called_once_with("test-agent")
            mock_run_client.create_run.assert_called_once_with(
                message="What is the weather?",
                agent_id="agent-789",
                thread_id=None
            )
            mock_run_client.wait_for_run_completion.assert_called_once_with("run-123")
            mock_threads_client.get_thread_messages.assert_called_once_with("thread-456")
    
    def test_chat_ask_with_two_questions(self):
        """Test that thread_id is maintained across multiple exchanges."""
        with patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.create_run_client") as mock_create_client, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.create_threads_client") as mock_create_threads, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.Prompt.ask") as mock_prompt, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.get_agent_id_by_name") as mock_get_agent_id:
            
            mock_run_client = mock_create_client.return_value
            mock_threads_client = mock_create_threads.return_value
            mock_get_agent_id.return_value = "agent-789"
            
            # Mock two questions and exit
            mock_prompt.side_effect = ["First question", "Second question", "quit"]
            mock_run_client.create_run.side_effect = [
                {"run_id": "run-1", "thread_id": "thread-123"},
                {"run_id": "run-2", "thread_id": "thread-123"}
            ]
            mock_run_client.wait_for_run_completion.side_effect = [
                {"status": "completed", "run_id": "run-1"},
                {"status": "completed", "run_id": "run-2"}
            ]
            mock_threads_client.get_thread_messages.side_effect = [
                {"data": [
                    {"role": "user", "content": "First question"},
                    {"role": "assistant", "content": "First answer"}
                ]},
                {"data": [
                    {"role": "user", "content": "First question"},
                    {"role": "assistant", "content": "First answer"},
                    {"role": "user", "content": "Second question"},
                    {"role": "assistant", "content": "Second answer"}
                ]}
            ]
            
            chat_command.chat_ask(agent_name="test-agent", include_reasoning=False)
            
            mock_get_agent_id.assert_called_once_with("test-agent")
            # Verify first call has no thread_id
            first_call = mock_run_client.create_run.call_args_list[0]
            assert first_call[1]["thread_id"] is None
            
            # Verify second call uses the thread_id from first response
            second_call = mock_run_client.create_run.call_args_list[1]
            assert second_call[1]["thread_id"] == "thread-123"
    
    def test_chat_ask_with_reasoning_trace(self):
        """Test chat with reasoning trace enabled."""
        with patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.create_run_client") as mock_create_client, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.create_threads_client") as mock_create_threads, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.Prompt.ask") as mock_prompt, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.get_agent_id_by_name") as mock_get_agent_id:
            
            mock_run_client = mock_create_client.return_value
            mock_threads_client = mock_create_threads.return_value
            mock_get_agent_id.return_value = "agent-789"
            
            # Mock a question and exit
            mock_prompt.side_effect = ["Test question", "q"]
            mock_run_client.create_run.return_value = {
                "run_id": "run-123",
                "thread_id": "thread-456"
            }
            mock_run_client.wait_for_run_completion.return_value = {
                "status": "completed",
                "run_id": "run-123"
            }
            
            # Mock response with step_history
            mock_threads_client.get_thread_messages.return_value = {
                "data": [
                    {"role": "user", "content": "Test question"},
                    {
                        "role": "assistant",
                        "content": "Here's the answer",
                        "step_history": [
                            {
                                "step_details": [{
                                    "type": "tool_calls",
                                    "tool_calls": [{
                                        "name": "search_tool",
                                        "args": {"query": "test"}
                                    }],
                                    "agent_display_name": "Test Agent"
                                }]
                            },
                            {
                                "step_details": [{
                                    "type": "tool_response",
                                    "name": "search_tool",
                                    "content": "Search results"
                                }]
                            }
                        ]
                    }
                ]
            }

            chat_command.chat_ask(agent_name="test-agent", include_reasoning=True)
            
            mock_get_agent_id.assert_called_once_with("test-agent")
            assert mock_run_client.create_run.called
    
    def test_chat_ask_handles_failed_run(self, caplog):
        """Test handling of failed run status."""
        with patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.create_run_client") as mock_create_client, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.Prompt.ask") as mock_prompt, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.get_agent_id_by_name") as mock_get_agent_id:
            
            mock_run_client = mock_create_client.return_value
            mock_get_agent_id.return_value = "agent-789"
            
            # Mock a question and exit
            mock_prompt.side_effect = ["Test question", "exit"]
            mock_run_client.create_run.return_value = {
                "run_id": "run-123",
                "thread_id": "thread-456"
            }
            # Failed run
            mock_run_client.wait_for_run_completion.return_value = {
                "status": "failed",
                "error": "Agent not found",
                "run_id": "run-123"
            }
            
            chat_command.chat_ask(agent_name="test-agent", include_reasoning=False)
            
            mock_get_agent_id.assert_called_once_with("test-agent")
            captured = caplog.text
            assert "Run failed with status" in captured
    
    def test_chat_ask_handles_structured_content(self):
        """Test handling of structured content (list of response objects)."""
        with patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.create_run_client") as mock_create_client, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.create_threads_client") as mock_create_threads, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.Prompt.ask") as mock_prompt, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.get_agent_id_by_name") as mock_get_agent_id:
            
            mock_run_client = mock_create_client.return_value
            mock_threads_client = mock_create_threads.return_value
            mock_get_agent_id.return_value = "agent-789"
            
            # Mock a question and exit
            mock_prompt.side_effect = ["Test question", "exit"]
            
            mock_run_client.create_run.return_value = {
                "run_id": "run-123",
                "thread_id": "thread-456"
            }
            mock_run_client.wait_for_run_completion.return_value = {
                "status": "completed",
                "run_id": "run-123"
            }
            
            # Mock structured content response
            mock_threads_client.get_thread_messages.return_value = {
                "data": [
                    {"role": "user", "content": "Test question"},
                    {
                        "role": "assistant",
                        "content": [
                            {"response_type": "text", "text": "First part"},
                            {"response_type": "text", "text": "Second part"}
                        ]
                    }
                ]
            }
            
            chat_command.chat_ask(agent_name="test-agent", include_reasoning=False)
            
            mock_get_agent_id.assert_called_once_with("test-agent")
            assert mock_run_client.create_run.called
    
    def test_chat_ask_empty_input(self):
        """Test that empty input is skipped."""
        with patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.create_run_client") as mock_create_client, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.create_threads_client") as mock_create_threads, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.Prompt.ask") as mock_prompt, \
             patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.get_agent_id_by_name") as mock_get_agent_id:
            
            mock_run_client = mock_create_client.return_value
            mock_threads_client = mock_create_threads.return_value
            mock_get_agent_id.return_value = "agent-789"
            
            # Mock empty input, then valid input, then exit
            mock_prompt.side_effect = ["  ", "Valid question", "q"]
            mock_run_client.create_run.return_value = {
                "run_id": "run-123",
                "thread_id": "thread-456"
            }
            mock_run_client.wait_for_run_completion.return_value = {
                "status": "completed",
                "run_id": "run-123"
            }
            mock_threads_client.get_thread_messages.return_value = {
                "data": [
                    {"role": "user", "content": "Valid question"},
                    {"role": "assistant", "content": "Answer"}
                ]
            }
            
            chat_command.chat_ask(agent_name="test-agent", include_reasoning=False)
            
            mock_get_agent_id.assert_called_once_with("test-agent")
            # Verify create_run was only called once - only for the second input
            assert mock_run_client.create_run.call_count == 1
    
    def test_chat_ask_agent_not_found(self):
        """Test handling when agent name doesn't exist."""
        with patch("ibm_watsonx_orchestrate.cli.commands.chat.chat_controller.get_agent_id_by_name") as mock_get_agent_id:
            
            # Mock the helper to raise SystemExit (which it does when agent not found)
            mock_get_agent_id.side_effect = SystemExit(1)
            
            # Verify that SystemExit is raised when agent doesn't exist
            with pytest.raises(SystemExit) as exc_info:
                chat_command.chat_ask(agent_name="nonexistent-agent", include_reasoning=False)
            