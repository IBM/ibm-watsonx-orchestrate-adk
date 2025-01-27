from unittest.mock import patch

from ibm_watsonx_orchestrate.cli.commands.chat import chat_command

def test_chat_start_call(capsys):
    with patch("webbrowser.open") as mock_webbrowser:
        chat_command.chat_start()
        captured = capsys.readouterr()
        assert captured.out == "Opening chat interface at http://localhost:3000/chat-lite\n"
        mock_webbrowser.assert_called_once_with("http://localhost:3000/chat-lite")