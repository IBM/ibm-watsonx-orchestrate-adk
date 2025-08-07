from ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller import (
    _validate_output_file,
    _get_progress_spinner,
    _get_incomplete_tool_from_name,
    _get_tools_from_names,
    get_cpe_client,
    gather_utterances,
    pre_cpe_step,
    find_tools_by_description,
    gather_examples,
    talk_to_cpe,
    prompt_tune,
    create_agent
    )
from ibm_watsonx_orchestrate.client.copilot.cpe.copilot_cpe_client import CPEClient
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.agent_builder.agents import Agent, AgentKind, AgentStyle, ExternalAgent, AssistantAgent
import pytest
from requests import ConnectionError
from unittest.mock import patch, mock_open, MagicMock
from rich.progress import Progress
import os

class MockCPEClient:
    def __init__(self, pre_chat_responses=[], invoke_responses=[], mock_init_response=None):
        self.pre_chat_responses = pre_chat_responses
        self.pre_chat_reponses_index = 0
        self.invoke_responses = invoke_responses
        self.invoke_responses_index = 0
        self.mock_init_response = mock_init_response
    
    def submit_pre_cpe_chat(self, **message_content):
        if not len(self.pre_chat_responses):
            return {}
        response_index = self.pre_chat_reponses_index
        self.pre_chat_reponses_index += 1

        if response_index >= len(self.pre_chat_responses):
            return self.pre_chat_responses[-1]
        else:
            return self.pre_chat_responses[response_index]
    
    def invoke(self, prompt):
        if not len(self.invoke_responses):
            return {}
        response_index = self.invoke_responses_index
        self.invoke_responses_index += 1

        if response_index >= len(self.invoke_responses):
            return self.invoke_responses[-1]
        else:
            return self.invoke_responses[response_index]
    
    def init_with_context(self, context_data):
        return self.mock_init_response

class MockToolClient:
    def __init__(self, get_response=[], get_drafts_by_names_response=[]):
        self.get_response = get_response
        self.get_drafts_by_names_response = get_drafts_by_names_response
    
    def get(self):
        return self.get_response
    
    def get_drafts_by_names(self, tool_names):
        return self.get_drafts_by_names_response

class TestValidateOutputFile:
    @pytest.mark.parametrize(
        ("output_file", "dry_run_flag"),
        [
            ("output_file.yaml", False),
            ("output_file.yml", False),
            ("output_file.json", False),
            (None, True),
        ]
    )
    def test_validate_output_file(self, output_file, dry_run_flag):
        _validate_output_file(output_file=output_file, dry_run_flag=dry_run_flag)
    
    def test_validate_output_file_missing_output(self, caplog):
        with pytest.raises(SystemExit):
             _validate_output_file(output_file=None, dry_run_flag=False)
        
        captured = caplog.text
        assert "Please provide a valid yaml output file. Or use the `--dry-run` flag to output generated agent content to terminal" in captured

    def test_validate_output_file_dry_run_with_output(self, caplog):
        with pytest.raises(SystemExit):
             _validate_output_file(output_file="output_file.yaml", dry_run_flag=True)
        
        captured = caplog.text
        assert "Cannot set output file when performing a dry run" in captured
    
    @pytest.mark.parametrize(
        "output_file",
        [
            "output_file.txt",
            "output_file.csv",
            "output_file.json.test",
            "output_file"
        ]
    )
    def test_validate_output_file_invalid_file_extention(self, output_file, caplog):
        with pytest.raises(SystemExit):
             _validate_output_file(output_file=output_file, dry_run_flag=False)
        
        captured = caplog.text
        assert "Output file must be of type '.yaml', '.yml' or '.json'" in captured

class TestGetProgressSpinner:
    def test_get_progress_spinner(self):
        spinner = _get_progress_spinner()
        assert isinstance(spinner, Progress)

class TestGetIncompleteToolFromName:
    @pytest.mark.parametrize(
        "tool_name",
        [
            "test_tool",
            "test_tool_2"
        ]
    )
    def test_get_incomplete_tool_from_name(self, tool_name):
        tool = _get_incomplete_tool_from_name(tool_name)

        assert tool.get("name") == tool_name
        assert tool.get("description") == tool_name
        assert tool.get("input_schema") is not None
        assert tool.get("input_schema").get("properties")  == {}
        assert tool.get("output_schema") is not None
        assert tool.get("output_schema").get("description")  == "None"

class TestGetToolsFromNames:
    @pytest.mark.parametrize(
        "tool_names",
        [
            ["test_tool"],
            ["test_tool", "test_tool_2"],
        ]
    )
    def test_get_tools_from_names(self, tool_names, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.get_tool_client") as mock_get_tool_client:
            mock_response = [{"name": tool_name} for tool_name in tool_names]
            mock_get_tool_client.return_value = MockToolClient(get_drafts_by_names_response=mock_response)

            tools = _get_tools_from_names(tool_names)

            captured = caplog.text

            assert len(tools) == len(tool_names)
            assert "Failed to find tool named" not in captured
            assert "Failed to fetch tools from server" not in captured
    
    def test_get_tools_from_names_no_names(self):
        tools = _get_tools_from_names(tool_names=[])
        assert tools == []

    def test_get_tools_from_names_missing_tools(self, caplog):
        tool_names = ["test_tool", "test_tool_2"]
        with patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.get_tool_client") as mock_get_tool_client:
            mock_response = [{"name": "test_tool_2"}]
            mock_get_tool_client.return_value = MockToolClient(get_drafts_by_names_response=mock_response)

            tools = _get_tools_from_names(tool_names)

            captured = caplog.text

            assert len(tools) == len(tool_names)
            assert "Failed to find tool named 'test_tool'." in captured
            assert "Failed to find tool named 'test_tool_2'." not in captured
            assert "Failed to fetch tools from server" not in captured

    def test_get_tools_from_names_server_not_started(self, caplog):
        tool_names = ["test_tool", "test_tool_2"]
        with patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.get_tool_client") as mock_get_tool_client:
            mock_reponse = MagicMock()
            mock_reponse.get_drafts_by_names.side_effect=ConnectionError()
            mock_get_tool_client.return_value = mock_reponse

            tools = _get_tools_from_names(tool_names)

            captured = caplog.text

            assert len(tools) == len(tool_names)
            assert "Failed to find tool named " not in captured
            assert "Failed to fetch tools from server" in captured

    

class TestGetCPEClient:
    def test_get_cpe_client(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.instantiate_client") as mock_instantiate_client:
            get_cpe_client()

            mock_instantiate_client.assert_called_once_with(
                client=CPEClient,
                url="http://localhost:8081"
            )

class TestGatherUtterances:
    @pytest.mark.parametrize(
        "max",
        [
            1,
            2,
            3
        ]
    )
    def test_gather_utterances(self, max):
        with patch("builtins.input") as mock_input:
            mock_input.side_effect = ["test"] * max
            utterances = gather_utterances(max)

        assert len(utterances) == max
        for item in utterances:
            assert item == "test"

class TestPreCPEStep:
    def test_pre_cpe_step(self):
        pre_chat_responses = [
            {
                "message": "Test Message"
            },
            {
                "description": "Test Description"
            },
            {
                "tools": []
            },
            {
                "collaborators": []
            },
            {
                "knowledge_bases": []
            },
            {
                "agent_name": "Test Agent",
                "agent_style": "Test Style",
            }
        ]
        cpe_client = MockCPEClient(pre_chat_responses=pre_chat_responses)
        with patch("builtins.input") as mock_input, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.get_deployed_tools_agents_and_knowledge_bases") as get_deployed_tools_agents_and_knowledge_bases:
            #, \
            # patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.find_tools_by_description") as mock_find_tools_by_description,
            # patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.") as XXX,
            # patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.") as YYY:
            mock_input.side_effect = ["test", "test","test","test"]
            # mock_find_tools_by_description.return_value=[]
            get_deployed_tools_agents_and_knowledge_bases.return_value={"tools": [], "collaborators": [], "knowledge_bases":[]}

            pre_cpe_step(cpe_client)

class TestFindToolsByDescription:
    @pytest.mark.parametrize(
        "response",
        [
            [],
            [{"name": "tool_1"}]
        ]
    )
    def test_find_tools_by_description(self, response):
        mock_tool_client = MockToolClient(get_response=response)

        tools = find_tools_by_description("", mock_tool_client)
        assert tools == response
    
    def test_find_tools_by_description_server_error(self, caplog):
        mock_tool_client = MagicMock()
        mock_tool_client.get.side_effect=ConnectionError()

        tools = find_tools_by_description("", mock_tool_client)
        
        captured = caplog.text

        assert tools == []
        assert "Failed to contact wxo server to fetch tools" in captured


class TestGatherExamples:
    def test_gather_examples_txt(self):
        sample_data = "test1\ntest2\ntest3"
        with patch('builtins.open', mock_open(read_data=sample_data)):
            examples = gather_examples("sample_file.txt")
            assert len(examples) == 3
            assert examples == sample_data.split('\n')

    def test_gather_examples_csv(self):
        sample_data = "utterance\ntest1\ntest2\ntest3"
        with patch('builtins.open', mock_open(read_data=sample_data)):
            examples = gather_examples("sample_file.csv")
            assert len(examples) == 3
            assert examples == sample_data.split('\n')[1:]

    @pytest.mark.parametrize(
        "content",
        [
            "utterance123\ntest1\ntest2\ntest3",
            "test1\ntest2\ntest3",
            "\ntest1\ntest2\ntest3"
        ]
    )
    def test_gather_examples_csv_missing_header(self, content, caplog):
        with patch('builtins.open', mock_open(read_data=content)):
            with pytest.raises(BadRequest):
                examples = gather_examples("sample_file.csv")
        
        captured = caplog.text

        assert "CSV must have a column named 'utterance'" in captured

    @pytest.mark.parametrize(
        "file_name",
        [
            "file.yaml",
            "file.json",
            "file"
        ]
    )
    def test_gather_examples_unsupported_file(self, file_name, caplog):
        with pytest.raises(BadRequest):
            examples = gather_examples(file_name)
        
        captured = caplog.text

        assert f'Unsupported samples file format: {os.path.basename(file_name)}' in captured
    
    def test_gather_examples_no_file(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.gather_utterances") as mock_gather_utterances:
            mock_gather_utterances.return_value=[]
            examples = gather_examples()

            mock_gather_utterances.assert_called_once_with(3)


class TestTalkToCPE:
    def test_talk_to_cpe(self):
        invoke_responses = [
            {
                "response":[
                    {
                        "final_zsh_prompt": "Testing"
                    }
                ]
            }
        ]
        mock_init_response = {"response": [{}]}
        cpe_client = MockCPEClient(invoke_responses=invoke_responses, mock_init_response=mock_init_response)
        with patch("builtins.input") as mock_input, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.gather_examples") as mock_gather_examples:
            mock_input.side_effect = ["test"]

            response = talk_to_cpe(cpe_client, None)

            assert response == "Testing"

class TestPromptTune:
    def test_prompt_tune(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.AgentsController.import_agent") as mock_import_agent, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.AgentsController.persist_record") as mock_persist_record, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.get_tool_client") as mock_get_tool_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.get_cpe_client") as mock_get_cpe_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.os.path.dirname") as mock_dirname, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.talk_to_cpe") as mock_talk_to_cpe:

            mock_import_agent.return_value = [Agent(
                kind=AgentKind.NATIVE,
                name="test_agent",
                description="test_agent_description"
            )]
            
            mock_get_cpe_client.return_value = MockCPEClient()
            mock_get_tool_client.return_value = MockToolClient()
            mock_talk_to_cpe.return_value = "Test Prompt"
            mock_dirname.return_value = False

            prompt_tune(
                agent_spec="test_agent_spec.yaml",
                output_file=None,
                samples_file=None,
                dry_run_flag=False
            )

            mock_persist_record.assert_called_once()

        captured = caplog.text
        assert "The new instruction is:" in captured
    
    def test_prompt_tune_dry_run(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.AgentsController.import_agent") as mock_import_agent, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.AgentsController.persist_record") as mock_persist_record, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.get_tool_client") as mock_get_tool_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.get_cpe_client") as mock_get_cpe_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.os.path.dirname") as mock_dirname, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.talk_to_cpe") as mock_talk_to_cpe:

            mock_import_agent.return_value = [Agent(
                kind=AgentKind.NATIVE,
                name="test_agent",
                description="test_agent_description"
            )]
            
            mock_get_cpe_client.return_value = MockCPEClient()
            mock_get_tool_client.return_value = MockToolClient()
            mock_talk_to_cpe.return_value = "Test Prompt"
            mock_dirname.return_value = False

            prompt_tune(
                agent_spec="test_agent_spec.yaml",
                output_file=None,
                samples_file=None,
                dry_run_flag=True
            )

            mock_persist_record.assert_not_called()

        captured = caplog.text
        assert "The new instruction is:" in captured
    
    @pytest.mark.parametrize(
        ("agent_class", "agent_kind", "agent_params"),
        [
            (ExternalAgent, AgentKind.EXTERNAL, {"title": "test", "api_url": "test"}),
            (AssistantAgent, AgentKind.ASSISTANT, {"title": "test"})
        ]
    )
    def test_prompt_tune_non_native(self, caplog, agent_class, agent_kind, agent_params):
        with patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.AgentsController.import_agent") as mock_import_agent, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.AgentsController.persist_record") as mock_persist_record, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.get_tool_client") as mock_get_tool_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.get_cpe_client") as mock_get_cpe_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.os.path.dirname") as mock_dirname, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.talk_to_cpe") as mock_talk_to_cpe:

            mock_import_agent.return_value = [agent_class(
                kind=agent_kind,
                name="test_agent",
                description="test_agent_description",
                **agent_params
            )]
            
            mock_get_cpe_client.return_value = MockCPEClient()
            mock_get_tool_client.return_value = MockToolClient()
            mock_talk_to_cpe.return_value = "Test Prompt"
            mock_dirname.return_value= False

            with pytest.raises(SystemExit):
                prompt_tune(
                    agent_spec="test_agent_spec.yaml",
                    output_file=None,
                    samples_file=None,
                    dry_run_flag=True
                )

        captured = caplog.text
        assert f"Only native agents are supported for prompt tuning. Provided agent spec is on kind '{agent_kind}'" in captured

class TestCreateAgent:
    def test_create_agent(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.AgentsController.persist_record") as mock_persist_record, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.get_cpe_client") as mock_get_cpe_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.get_tool_client") as mock_get_tool_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.pre_cpe_step") as mock_pre_cpe_step, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.os.path.dirname") as mock_dirname, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.talk_to_cpe") as mock_talk_to_cpe:

            mock_get_cpe_client.return_value = MockCPEClient()
            mock_get_tool_client.return_value = MockToolClient()

            mock_pre_cpe_step.return_value = {
                "tools": [],
                "description": "test description",
                "agent_name": "test_name",
                "agent_style": AgentStyle.DEFAULT,
                "collaborators": [],
                "knowledge_bases": []
            }

            mock_talk_to_cpe.return_value = "test instructions"
            mock_dirname.return_value = False

            create_agent(
                output_file="test.yaml",
                llm=None,
                samples_file=None,
            )

            mock_persist_record.assert_called()
    
    def test_create_agent_dry_run(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.AgentsController.persist_record") as mock_persist_record, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.get_cpe_client") as mock_get_cpe_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.get_tool_client") as mock_get_tool_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.pre_cpe_step") as mock_pre_cpe_step, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.os.path.dirname") as mock_dirname, \
            patch("ibm_watsonx_orchestrate.cli.commands.copilot.copilot_controller.talk_to_cpe") as mock_talk_to_cpe:

            mock_get_cpe_client.return_value = MockCPEClient()
            mock_get_tool_client.return_value = MockToolClient()

            mock_pre_cpe_step.return_value = {
                "tools": [],
                "description": "test description",
                "agent_name": "test_name",
                "agent_style": AgentStyle.DEFAULT,
                "collaborators": [],
                "knowledge_bases": []
            }

            mock_talk_to_cpe.return_value = "test instructions"
            mock_dirname.return_value = False

            create_agent(
                output_file=None,
                llm=None,
                samples_file=None,
                dry_run_flag=True
            )

            mock_persist_record.assert_called_once()
