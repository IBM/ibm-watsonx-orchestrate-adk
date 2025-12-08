import pytest
from unittest.mock import patch
from ibm_watsonx_orchestrate.cli.commands.agents.ai_builder.ai_builder_command import agent_refine, create_command, prompt_tune_command

class TestCreateCommand:
    base_params = {
        "output_file": "test_output_file",
        "dry_run_flag": False,
        "llm": "test_llm",
        "chat_llm": "chat_llm",
        "agent_description": "test_description"
    }
    def test_prompt_tune_command_create_agent(self):
        params = self.base_params.copy()

        with patch("ibm_watsonx_orchestrate.cli.commands.agents.ai_builder.ai_builder_command.create_agent") as mock_create_agent:

            create_command(**params)
        
            mock_create_agent.assert_called_once_with(
                llm=params.get("llm"),
                chat_llm = params.get("chat_llm"),
                output_file=params.get("output_file"),
                dry_run_flag=params.get("dry_run_flag"),
                description=params.get("agent_description")
            )

    @pytest.mark.parametrize(
        ("missing_param", "default_value"),
        [
            ("chat_llm", None),
            ("output_file", None),
            ("dry_run_flag", False),
            ("llm", None),
            ("agent_description", None)
        ]
    )
    def test_prompt_tune_command_create_agent_missing_optional_params(self, missing_param, default_value):
        params = self.base_params.copy()
        expected_params = params.copy()

        params.pop(missing_param, None)
        expected_params[missing_param] = default_value
        expected_params["description"] = expected_params["agent_description"]
        expected_params.pop("agent_description", None)

        with patch("ibm_watsonx_orchestrate.cli.commands.agents.ai_builder.ai_builder_command.create_agent") as mock_create_agent:
            
            create_command(**params)
            
            mock_create_agent.assert_called_once_with(**expected_params)


class TestPromptTuneCommand:
    base_params = {
        "file": "test_file",
        "output_file": "test_output_file",
        "dry_run_flag": False,
        "llm": "test_llm",
        "chat_llm": "chat_llm",
    }

    def test_prompt_tune_command_prompt_tune(self):
        params = self.base_params.copy()

        with patch("ibm_watsonx_orchestrate.cli.commands.agents.ai_builder.ai_builder_command.prompt_tune") as mock_prompt_tune:

            prompt_tune_command(**params)
        
            mock_prompt_tune.assert_called_once_with(
                chat_llm=params.get("chat_llm"),
                agent_spec=params.get("file"),
                output_file=params.get("output_file"),
                dry_run_flag=params.get("dry_run_flag"),
                llm=params.get("llm")
            )

    @pytest.mark.parametrize(
        ("missing_param", "default_value"),
        [
            ("chat_llm", None),
            ("output_file", None),
            ("dry_run_flag", False),
            ("llm", None),
        ]
    )
    def test_prompt_tune_command_prompt_tune_missing_optional_params(self, missing_param, default_value):
        params = self.base_params.copy()
        expected_params = params.copy()
        params.pop(missing_param, None)
        expected_params[missing_param] = default_value
        expected_params["agent_spec"] = expected_params["file"]
        expected_params.pop("file", None)

        with patch("ibm_watsonx_orchestrate.cli.commands.agents.ai_builder.ai_builder_command.prompt_tune") as mock_prompt_tune:
            
            prompt_tune_command(**params)
            
            mock_prompt_tune.assert_called_once_with(**expected_params)

class TestAgentRefineCommand:
    base_params = {
        "agent_name": "test_agent",
        "output_file": "test_output_file",
        "dry_run_flag": False,
        "use_last_chat": True,
        "chat_llm": "chat_llm",
    }

    def test_agent_refine_command_prompt_tune(self):
        params = self.base_params.copy()

        with patch("ibm_watsonx_orchestrate.cli.commands.agents.ai_builder.ai_builder_command.submit_refine_agent_with_chats") as mock_submit_refine_agent_with_chats:

            agent_refine(**params)
        
            mock_submit_refine_agent_with_chats.assert_called_once_with(
                chat_llm=params.get("chat_llm"),
                agent_name=params.get("agent_name"),
                output_file=params.get("output_file"),
                dry_run_flag=params.get("dry_run_flag"),
                use_last_chat=params.get("use_last_chat")
            )

    @pytest.mark.parametrize(
        ("missing_param", "default_value"),
        [
            ("chat_llm", None),
            ("output_file", None),
            ("dry_run_flag", False),
            ("use_last_chat", False),
        ]
    )
    def test_prompt_tune_command_agent_refine_missing_optional_params(self, missing_param, default_value):
        params = self.base_params.copy()
        expected_params = params.copy()
        params.pop(missing_param, None)
        expected_params[missing_param] = default_value

        with patch("ibm_watsonx_orchestrate.cli.commands.agents.ai_builder.ai_builder_command.submit_refine_agent_with_chats") as mock_submit_refine_agent_with_chats:
            
            agent_refine(**params)
            
            mock_submit_refine_agent_with_chats.assert_called_once_with(**expected_params)