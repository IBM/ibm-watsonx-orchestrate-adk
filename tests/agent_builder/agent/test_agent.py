import pytest
from pydantic_core import ValidationError
from unittest.mock import patch, mock_open
from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.agent_builder.agents import Agent, SpecVersion, AgentKind, AgentStyle, AgentGuideline
from ibm_watsonx_orchestrate.agent_builder.agents.types import DEFAULT_LLM

@pytest.fixture()
def valid_native_agent_sample():
    return {
        "spec_version": SpecVersion.V1,
        "kind": AgentKind.NATIVE,
        "name": "test_native_agent",
        "description": "Test Object for native agent",
        "llm": "test_llm",
        "style": AgentStyle.DEFAULT,
        "collaborators": [
            "test_agent_1",
            "test_agent_2"
        ],
        "tools": [
            "test_tool_1",
            "test_tool_2"
        ],
        "knowledge_base": [
            "test_base_1",
            "test_base_2"
        ],
        "guidelines": [
            {
                "display_name": "test_guideline_1",
                "condition": "test_condition_1",
                "action": "test_action_1",
                "tool": "test_tool_1"
            }
        ]
    }

@pytest.fixture()
def default_values():
    return {
        "kind": AgentKind.NATIVE,
        "llm": DEFAULT_LLM,
        "collaborators": [],
        "tools": [],
        "knowledge_base": [],
        "guidelines": []
    }

@pytest.fixture(params=['kind', 'spec_version', 'llm', 'style', 'collaborators', 'tools', 'knowledge_base', 'guidelines'])
def native_agent_missing_optional_values(request, valid_native_agent_sample):
    native_spec_definition = valid_native_agent_sample
    native_spec_definition.pop(request.param, None)

    return {
        "missing" : request.param,
        "spec" : native_spec_definition
    }

@pytest.fixture(params=['name', 'description'])
def native_agent_missing_required_values(request, valid_native_agent_sample):
    native_spec_definition = valid_native_agent_sample
    native_spec_definition.pop(request.param, None)

    return {
        "missing" : request.param,
        "spec" : native_spec_definition
    }

@pytest.fixture()
def valid_agent_guideline():
    return {
        "display_name": "test_guideline_1",
        "condition": "test_condition_1",
        "action": "test_action_1",
        "tool": "test_tool_1"
    }

@pytest.fixture(params=['display_name', 'tool'])
def agent_guideline_missing_optional_values(request, valid_agent_guideline):
    guideline_spec_definition = valid_agent_guideline
    guideline_spec_definition.pop(request.param, None)

    return {
        "missing" : request.param,
        "spec" : guideline_spec_definition
    }

@pytest.fixture(params=['condition', 'action'])
def agent_guideline_missing_required_values(request, valid_agent_guideline):
    guideline_spec_definition = valid_agent_guideline
    guideline_spec_definition.pop(request.param, None)

    return {
        "missing" : request.param,
        "spec" : guideline_spec_definition
    }

class TestAgentInit:
    def test_valid_native_agent(self, valid_native_agent_sample):
        native_spec_definition = valid_native_agent_sample

        native_agent = Agent(
            spec_version = native_spec_definition["spec_version"],
            kind = native_spec_definition["kind"],
            name = native_spec_definition["name"],
            description = native_spec_definition["description"],
            llm = native_spec_definition["llm"],
            style = native_spec_definition["style"],
            collaborators = native_spec_definition["collaborators"],
            tools = native_spec_definition["tools"],
            knowledge_base = native_spec_definition["knowledge_base"],
            guidelines=native_spec_definition["guidelines"]
            )
        
        assert native_agent.spec_version == native_spec_definition["spec_version"]
        assert native_agent.kind == native_spec_definition["kind"]
        assert native_agent.name == native_spec_definition["name"]
        assert native_agent.description == native_spec_definition["description"]
        assert native_agent.llm == native_spec_definition["llm"]
        assert native_agent.style == native_spec_definition["style"]
        assert native_agent.collaborators == native_spec_definition["collaborators"]
        assert native_agent.tools == native_spec_definition["tools"]
        assert native_agent.knowledge_base == native_spec_definition["knowledge_base"]
        assert native_agent.guidelines == [AgentGuideline.model_validate(native_spec_definition["guidelines"][0])]


    def test_native_agent_missing_optional_params(self, native_agent_missing_optional_values, default_values):
        agent_spec = native_agent_missing_optional_values["spec"]
        missing_value = native_agent_missing_optional_values["missing"]

        default_value = default_values.get(missing_value, None)

        native_agent = Agent(
            **agent_spec
            )

        for key in agent_spec:
            if key == missing_value:
                assert getattr(native_agent, key) == default_value
            if key == "guidelines":
                assert getattr(native_agent, key) == [AgentGuideline.model_validate(agent_spec.get(key)[0])]
            else:
                assert getattr(native_agent, key) == agent_spec.get(key)

    def test_native_agent_missing_required_params(self, native_agent_missing_required_values):
        agent_spec = native_agent_missing_required_values["spec"]

        with pytest.raises(ValidationError) as e:
            _ = Agent(**agent_spec)

class TestAgentString:
    def test_native_agent_to_string(self, valid_native_agent_sample, capsys):
        native_spec_definition = valid_native_agent_sample

        native_agent = Agent(
            spec_version = native_spec_definition["spec_version"],
            kind = native_spec_definition["kind"],
            name = native_spec_definition["name"],
            description = native_spec_definition["description"],
            llm = native_spec_definition["llm"],
            style = native_spec_definition["style"],
            collaborators = native_spec_definition["collaborators"],
            tools = native_spec_definition["tools"],
            knowledge_base = native_spec_definition["knowledge_base"]
            )

        print(native_agent)

        captured = capsys.readouterr()

        assert f"Agent(name='{native_spec_definition['name']}', description='{native_spec_definition['description']}')" in captured.out

class TestAgentFromSpec:
    def test_native_agent_from_spec_yaml(self, valid_native_agent_sample):
        with patch("ibm_watsonx_orchestrate.agent_builder.agents.agent.yaml_safe_load") as mock_loader, \
            patch("builtins.open", mock_open()) as mock_file:
            native_spec_definition = valid_native_agent_sample
            mock_loader.return_value = native_spec_definition
            
            native_agent = Agent.from_spec("test_file.yml")

            mock_file.assert_called_with("test_file.yml", "r")
            mock_loader.assert_called_once()

            assert native_agent.spec_version == native_spec_definition["spec_version"]
            assert native_agent.kind == native_spec_definition["kind"]
            assert native_agent.name == native_spec_definition["name"]
            assert native_agent.description == native_spec_definition["description"]
            assert native_agent.llm == native_spec_definition["llm"]
            assert native_agent.style == native_spec_definition["style"]
            assert native_agent.collaborators == native_spec_definition["collaborators"]
            assert native_agent.tools == native_spec_definition["tools"]
            assert native_agent.knowledge_base == native_spec_definition["knowledge_base"]

    def test_native_agent_from_spec_json(self, valid_native_agent_sample):
        with patch("ibm_watsonx_orchestrate.agent_builder.agents.agent.json.load") as mock_loader, \
            patch("builtins.open", mock_open()) as mock_file:
            native_spec_definition = valid_native_agent_sample
            mock_loader.return_value = native_spec_definition
            
            native_agent = Agent.from_spec("test_file.json")

            mock_file.assert_called_with("test_file.json", "r")
            mock_loader.assert_called_once()

            assert native_agent.spec_version == native_spec_definition["spec_version"]
            assert native_agent.kind == native_spec_definition["kind"]
            assert native_agent.name == native_spec_definition["name"]
            assert native_agent.description == native_spec_definition["description"]
            assert native_agent.llm == native_spec_definition["llm"]
            assert native_agent.style == native_spec_definition["style"]
            assert native_agent.collaborators == native_spec_definition["collaborators"]
            assert native_agent.tools == native_spec_definition["tools"]
            assert native_agent.knowledge_base == native_spec_definition["knowledge_base"]

    def test_native_agent_from_spec_invalid_file_extentionl(self):
       with patch("builtins.open", mock_open()) as mock_file:
           with pytest.raises(ValueError) as e:
                Agent.from_spec("test_file.test")

                assert "file must end in .json, .yaml, or .yml" in str(e)

    def test_native_agent_from_spec_no_spec_version(self, valid_native_agent_sample):
        with patch("ibm_watsonx_orchestrate.agent_builder.agents.agent.yaml_safe_load") as mock_loader, \
            patch("builtins.open", mock_open()) as mock_file:
            native_spec_definition = valid_native_agent_sample
            native_spec_definition.pop("spec_version", None)
            mock_loader.return_value = native_spec_definition
            
            with pytest.raises(ValueError) as e:
                Agent.from_spec("test_file.yml")

                mock_file.assert_called_with("test_file.yml", "r")
                mock_loader.assert_called_once()

                assert "Field 'spec_version' not provided. Please ensure provided spec conforms to a valid spec format" in str(e)

class TestAgentGuidelineInit:
    def test_valid_guideline_init(self, valid_agent_guideline):
        guideline_spec_definition = valid_agent_guideline

        guideline = AgentGuideline(
            display_name=guideline_spec_definition.get("display_name"),
            condition=guideline_spec_definition.get("condition"),
            action=guideline_spec_definition.get("action"),
            tool=guideline_spec_definition.get("tool")
        )
        
        assert guideline.display_name == guideline_spec_definition["display_name"]
        assert guideline.condition == guideline_spec_definition["condition"]
        assert guideline.action == guideline_spec_definition["action"]
        assert guideline.tool == guideline_spec_definition["tool"]
    
    def test_valid_guideline_init_python_tool(self, valid_agent_guideline):
        guideline_spec_definition = valid_agent_guideline

        @tool(name=guideline_spec_definition.get("tool") ,description="test tool")
        def test_tool():
            return None

        guideline = AgentGuideline(
            display_name=guideline_spec_definition.get("display_name"),
            condition=guideline_spec_definition.get("condition"),
            action=guideline_spec_definition.get("action"),
            tool=test_tool
        )
        
        assert guideline.display_name == guideline_spec_definition["display_name"]
        assert guideline.condition == guideline_spec_definition["condition"]
        assert guideline.action == guideline_spec_definition["action"]
        assert guideline.tool == guideline_spec_definition["tool"]


    def test_guideline_missing_optional_params(self, agent_guideline_missing_optional_values):
        guideline_spec = agent_guideline_missing_optional_values["spec"]
        missing_value = agent_guideline_missing_optional_values["missing"]

        guideline = AgentGuideline(
            **guideline_spec
            )

        for key in guideline_spec:
            if key == missing_value:
                assert getattr(guideline, key) is None
            else:
                assert getattr(guideline, key) == guideline_spec.get(key)

    def test_guideline_missing_required_params(self, agent_guideline_missing_required_values):
        guideline_spec = agent_guideline_missing_required_values["spec"]

        with pytest.raises(ValidationError) as e:
            _ = AgentGuideline(**guideline_spec)