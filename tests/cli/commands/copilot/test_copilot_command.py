import pytest
from unittest.mock import patch
from ibm_watsonx_orchestrate.cli.commands.copilot.copilot_command import prompt_tume_command

class TestPromptTuneCommand:
    base_params = {
        "file": "test_file",
        "output_file": "test_output_file",
        "dry_run_flag": False,
        "llm": "test_llm",
        "chat_llm": "chat_llm",
        "samples": "test_samples"
    }

    def test_prompt_tune_command_create_agent(self):
        params = self.base_params.copy()
        params.pop("file", None)

        with patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_command.create_agent") as mock_create_agent, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_command.prompt_tune") as mock_prompt_tune:

            prompt_tume_command(**params)
        
            mock_create_agent.assert_called_once_with(
                llm=params.get("llm"),
                chat_llm = params.get("chat_llm"),
                output_file=params.get("output_file"),
                samples_file=params.get("samples"),
                dry_run_flag=params.get("dry_run_flag")
            )
            mock_prompt_tune.assert_not_called()

    @pytest.mark.parametrize(
        ("missing_param", "default_value"),
        [
            ("chat_llm", None),
            ("output_file", None),
            ("dry_run_flag", False),
            ("llm", None),
            ("samples", None),
        ]
    )
    def test_prompt_tune_command_create_agent_missing_optional_params(self, missing_param, default_value):
        params = self.base_params.copy()
        params.pop("file", None)
        expected_params = params.copy()

        params.pop(missing_param, None)
        expected_params[missing_param] = default_value
        expected_params["samples_file"] = expected_params["samples"]
        expected_params.pop("samples", None)

        with patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_command.create_agent") as mock_create_agent, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_command.prompt_tune") as mock_prompt_tune:
            
            prompt_tume_command(**params)
            
            mock_create_agent.assert_called_once_with(**expected_params)
            mock_prompt_tune.assert_not_called()

    def test_prompt_tune_command_prompt_tune(self):
        params = self.base_params.copy()

        with patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_command.create_agent") as mock_create_agent, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_command.prompt_tune") as mock_prompt_tune:

            prompt_tume_command(**params)
        
            mock_create_agent.assert_not_called()
            mock_prompt_tune.assert_called_once_with(
                chat_llm=params.get("chat_llm"),
                agent_spec=params.get("file"),
                output_file=params.get("output_file"),
                samples_file=params.get("samples"),
                dry_run_flag=params.get("dry_run_flag")
            )

    @pytest.mark.parametrize(
        ("missing_param", "default_value"),
        [
            ("chat_llm", None),
            ("output_file", None),
            ("dry_run_flag", False),
            ("samples", None),
        ]
    )
    def test_prompt_tune_command_prompt_tune_missing_optional_params(self, missing_param, default_value):
        params = self.base_params.copy()
        expected_params = params.copy()
        params.pop(missing_param, None)
        expected_params[missing_param] = default_value
        expected_params["samples_file"] = expected_params["samples"]
        expected_params["agent_spec"] = expected_params["file"]
        expected_params.pop("samples", None)
        expected_params.pop("file", None)
        expected_params.pop("llm", None)

        with patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_command.create_agent") as mock_create_agent, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_command.prompt_tune") as mock_prompt_tune:
            
            prompt_tume_command(**params)
            
            mock_create_agent.assert_not_called()
            mock_prompt_tune.assert_called_once_with(**expected_params)


    # base_params = {
    #     "environment": "draft",
    #     "verbose": False
    # }

    # def test_list_connection_command(self):
    #     with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.list_connections") as mock:
    #         connections_command.list_connections_command(**self.base_params)
    #         mock.assert_called_once_with(**self.base_params)
    
    # @pytest.mark.parametrize(
    #     ("missing_param", "default_value"),
    #     [
    #         ("environment", None),
    #         ("verbose", None),
    #     ]
    # )
    # def test_list_connection_command_missing_optional_parms(self, missing_param, default_value):
    #     missing_params = self.base_params.copy()
    #     missing_params.pop(missing_param, None)

    #     expected_params = self.base_params.copy()
    #     expected_params[missing_param] = default_value
    #     with patch("ibm_watsonx_orchestrate.cli.commands.connections.connections_command.list_connections") as mock:
    #         connections_command.list_connections_command(**missing_params)
    #         mock.assert_called_once_with(**expected_params)