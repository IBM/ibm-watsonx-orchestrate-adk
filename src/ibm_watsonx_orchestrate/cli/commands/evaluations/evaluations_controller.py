import logging
import os.path
from typing import List, Dict, Optional, Tuple
from enum import StrEnum
import csv
from pathlib import Path
import sys
import json

# Suppresses fuzzywuzzy warning coming from eval
from warnings import filterwarnings
filterwarnings("ignore", category=UserWarning, module=r"fuzzywuzzy\.fuzz")

from agentops import main as evaluate
from agentops import quick_eval
from agentops.tool_planner import build_snapshot
from agentops.analyze_run import run as run_analyze
from agentops.batch_annotate import generate_test_cases_from_stories
from agentops.arg_configs import TestConfig, AuthConfig, LLMUserConfig, ChatRecordingConfig, AnalyzeConfig, ProviderConfig, AttackConfig, QuickEvalConfig, AnalyzeMode
from agentops.record_chat import record_chats
from agentops.external_agent.external_validate import ExternalAgentValidation
from agentops.external_agent.performance_test import ExternalAgentPerformanceTest
from agentops.red_teaming.attack_list import print_attacks
from agentops.red_teaming import attack_generator
from agentops.red_teaming.attack_runner import run_attacks
from agentops.arg_configs import AttackGeneratorConfig
from agentops.automatic_eval_generation.data_generator import AutomaticEvalDataGenerator
from agentops.service_provider import get_provider
from agentops.wxo_client import get_wxo_client
from agentops.runtime_adapter.wxo_runtime_adapter import WXORuntimeAdapter

from ibm_watsonx_orchestrate import __version__
from ibm_watsonx_orchestrate.cli.config import (
    Config,
    ENV_WXO_URL_OPT,
    AUTH_CONFIG_FILE,
    AUTH_CONFIG_FILE_FOLDER,
    AUTH_SECTION_HEADER,
    AUTH_MCSP_TOKEN_OPT,
    PROTECTED_ENV_NAME,
    DEFAULT_LOCAL_SERVICE_URL,
)
from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentsController
from ibm_watsonx_orchestrate.agent_builder.agents import AgentKind
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
import uuid
import pandas as pd

logger = logging.getLogger(__name__)
USE_LEGACY_EVAL = os.environ.get("USE_LEGACY_EVAL", "TRUE").upper() == "TRUE"

class EvaluateMode(StrEnum):
    default = "default" # referenceFUL evaluation
    referenceless = "referenceless"

class EvaluationsController:
    def __init__(self):
        pass

    def _get_env_config(self) -> tuple[str, str, str | None]:
        cfg = Config()

        try:
            url = cfg.get_active_env_config(ENV_WXO_URL_OPT)
        except Exception as e:
            logger.error(f"Error retrieving service url: {e}")
            url = None

        try:
            tenant_name = cfg.get_active_env()
        except Exception as e:
            logger.error(f"Error retrieving active environment: {e}")
            tenant_name = None
        
        if url is None:
            logger.warning(
                "No active service URL found in config. Falling back to local URL '%s'.",
                DEFAULT_LOCAL_SERVICE_URL,
            )
            url = DEFAULT_LOCAL_SERVICE_URL
        if tenant_name is None:
            logger.warning(
                "No active tenant/environment found in config. Falling back to local environment '%s'.",
                PROTECTED_ENV_NAME,
            )
            tenant_name = PROTECTED_ENV_NAME

        auth_cfg = Config(AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE)
        existing_auth_config = auth_cfg.get(AUTH_SECTION_HEADER).get(tenant_name, {})
        token = existing_auth_config.get(AUTH_MCSP_TOKEN_OPT) if existing_auth_config else None

        return url, tenant_name, token

    def evaluate(self, config_file: Optional[str] = None, test_paths: Optional[str] = None, output_dir: Optional[str] = None, tools_path: str = None, mode: str = EvaluateMode.default) -> None:
        url, tenant_name, token = self._get_env_config()

        if "WATSONX_SPACE_ID" in os.environ and "WATSONX_APIKEY" in os.environ:
            provider = "watsonx"
        elif "WO_INSTANCE" in os.environ and ("WO_API_KEY" in os.environ or "WO_PASSWORD" in os.environ):
            provider = "model_proxy"
        else:
            provider = "gateway"
        
        config_data = {
            "wxo_lite_version": __version__,
            "auth_config": AuthConfig(
                url=url,
                tenant_name=tenant_name,
                token=token
            ),
            "provider_config": ProviderConfig(
                provider=provider,
                model_id="meta-llama/llama-3-405b-instruct",
            ),
            "skip_legacy_evaluation": not USE_LEGACY_EVAL,
        }

        if config_file:
            logger.info(f"Loading configuration from {config_file}")
            with safe_open(config_file, 'r') as f:
                file_config = yaml_safe_load(f) or {}
                
                if "auth_config" in file_config:
                    auth_config_data = file_config.pop("auth_config")
                    config_data["auth_config"] = AuthConfig(**auth_config_data)
                
                if "llm_user_config" in file_config:
                    llm_config_data = file_config.pop("llm_user_config")
                    config_data["llm_user_config"] = LLMUserConfig(**llm_config_data)

                if "provider_config" in file_config:
                    provider_config_data = file_config.pop("provider_config")
                    config_data["provider_config"] = ProviderConfig(**provider_config_data)
                
                config_data.update(file_config)

        if test_paths:
            config_data["test_paths"] = test_paths.split(",")
            logger.info(f"Using test paths: {config_data['test_paths']}")
        if output_dir:
            config_data["output_dir"] = output_dir
            logger.info(f"Using output directory: {config_data['output_dir']}")

        if mode == EvaluateMode.default:
            config = TestConfig(**config_data)
            evaluate.main(config)
        elif mode == EvaluateMode.referenceless:
            config_data["tools_path"] = tools_path
            config = QuickEvalConfig(**config_data)
            quick_eval.main(config)

    def record(self, output_dir) -> None:


        random_uuid = str(uuid.uuid4())

        url, tenant_name, token = self._get_env_config()
        config_data = {
            "output_dir": Path(os.path.join(Path.cwd(), random_uuid)) if output_dir is None else Path(os.path.join(output_dir,random_uuid)),
            "service_url": url,
            "tenant_name": tenant_name,
            "token": token
        }

        config_data["output_dir"].mkdir(parents=True, exist_ok=True)
        logger.info(f"Recording chat sessions to {config_data['output_dir']}")

        record_chats(ChatRecordingConfig(**config_data))

    def generate(self, stories_path: str, tools_path: str, output_dir: str) -> None:
        """
        Generate evaluation test cases from user stories.
        
        When USE_LEGACY_EVAL is True: Uses the legacy implementation with build_snapshot
        and generate_test_cases_from_stories.
        
        When USE_LEGACY_EVAL is False: Uses AutomaticEvalDataGenerator for a more
        comprehensive evaluation data generation approach.
        
        Args:
            stories_path: Path to CSV file containing user stories
            tools_path: Path to tools definition file (Python or JSON)
            output_dir: Directory where generated test cases will be stored
        """
        stories_path_obj = Path(stories_path)
        tools_path_obj = Path(tools_path)

        if output_dir is None:
            output_dir_obj = stories_path_obj.parent
        else:
            output_dir_obj = Path(output_dir)

        output_dir_obj.mkdir(parents=True, exist_ok=True)

        stories_by_agent = {}
        with stories_path_obj.open("r", encoding="utf-8", newline='') as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                agent_name = row["agent"]
                if agent_name not in stories_by_agent:
                    stories_by_agent[agent_name] = []
                stories_by_agent[agent_name].append(row["story"])

        if USE_LEGACY_EVAL:
            logger.info("Using legacy evaluation data generation")
            self._generate_legacy(stories_by_agent, tools_path_obj, output_dir_obj)
        else:
            logger.info("Using AutomaticEvalDataGenerator for evaluation data generation")
            self._generate(stories_by_agent, tools_path_obj, output_dir_obj)

        logger.info("Test cases stored at: %s", output_dir_obj)

    def _generate_legacy(self, stories_by_agent: Dict[str, List[str]], tools_path: Path, output_dir: Path) -> None:
        """
        Legacy implementation of generate using build_snapshot and generate_test_cases_from_stories.
        
        Args:
            stories_by_agent: Dictionary mapping agent names to lists of user stories
            tools_path: Path to tools definition file
            output_dir: Output directory for generated test cases
        """
        for agent_name, stories in stories_by_agent.items():
            logger.info(f"Found {len(stories)} stories for agent '{agent_name}'")
            try:
                agent_controller = AgentsController()
                agent = agent_controller.get_agent(agent_name, AgentKind.NATIVE)
                allowed_tools = agent_controller.get_agent_tool_names(agent.tools)
            except Exception as e:
                logger.warning(f"Could not get tools for agent {agent_name}: {str(e)}")
                allowed_tools = []

            logger.info(f"Running tool planner for agent {agent_name}")
            agent_snapshot_path = output_dir / f"{agent_name}_snapshot_llm.json"
            build_snapshot(agent_name, tools_path, stories, agent_snapshot_path)

            logger.info(f"Running batch annotate for agent {agent_name}")
            generate_test_cases_from_stories(
                agent_name=agent_name,
                stories=stories,
                tools_path=tools_path,
                snapshot_path=agent_snapshot_path,
                output_dir=output_dir / f"{agent_name}_test_cases",
                allowed_tools=allowed_tools,
                num_variants=2
            )

    def _generate(self, stories_by_agent: Dict[str, List[str]], tools_path: Path, output_dir: Path) -> None:
        """
        New implementation using AutomaticEvalDataGenerator.
        
        This approach:
        1. Creates a runtime adapter for the agent
        2. Loads/converts OpenAPI specification from tools
        3. Uses AutomaticEvalDataGenerator to create comprehensive evaluation data
        4. Saves results in a format compatible with the evaluation framework
        
        Args:
            stories_by_agent: Dictionary mapping agent names to lists of user stories
            tools_path: Path to tools definition file (Python or JSON)
            output_dir: Output directory for generated test cases
        """
        url, tenant_name, token = self._get_env_config()
        
        if "WATSONX_SPACE_ID" in os.environ and "WATSONX_APIKEY" in os.environ:
            provider = "watsonx"
            model_id = "meta-llama/llama-3-405b-instruct"
        elif "WO_INSTANCE" in os.environ and ("WO_API_KEY" in os.environ or "WO_PASSWORD" in os.environ):
            provider = "model_proxy"
            model_id = "meta-llama/llama-3-405b-instruct"
        else:
            provider = "gateway"
            model_id = "meta-llama/llama-3-405b-instruct"
        
        logger.info(f"Using LLM provider: {provider}, model: {model_id}")
        
        # Get path to user simulator template
        # Try to find the template in the agentops package
        try:
            import agentops
            agentops_path = Path(agentops.__file__).parent
            template_path = agentops_path / "prompt" / "universal_user_template.jinja2"
            if not template_path.exists():
                logger.warning(f"Template not found at {template_path}, using default")
                template_path = None
        except Exception as e:
            logger.warning(f"Could not locate user template: {e}")
            template_path = None
        
        # Initialize LLM clients for user simulation and tool sequence generation
        user_client = get_provider(model_id=model_id)
        tool_sequence_client = get_provider(model_id=model_id)
        
        # Process each agent
        for agent_name, stories in stories_by_agent.items():
            logger.info(f"Processing {len(stories)} stories for agent '{agent_name}' with AutomaticEvalDataGenerator")
            
            try:
                # Create WXO client and runtime adapter
                wxo_client = get_wxo_client(url, tenant_name, token)
                wxo_runtime_adapter = WXORuntimeAdapter(wxo_client)
                
                # Load or convert OpenAPI specification
                openapi_spec = self._load_openapi_spec(tools_path)
                
                # Initialize AutomaticEvalDataGenerator
                generator_kwargs = {
                    "runtime_adapted_agent": wxo_runtime_adapter,
                    "user_client": user_client,
                    "tool_sequence_client": tool_sequence_client,
                    "openapi_spec": openapi_spec,
                }
                
                if template_path:
                    generator_kwargs["user_prompt_path"] = str(template_path)
                
                generator = AutomaticEvalDataGenerator(**generator_kwargs)
                
                # Convert stories to DataFrame format expected by AutomaticEvalDataGenerator
                user_stories_df = pd.DataFrame({
                    "story": stories
                })
                
                # Generate evaluation data
                logger.info(f"Generating evaluation data for agent '{agent_name}'...")
                results = generator.generate_eval_data(
                    user_stories_df=user_stories_df,
                    max_turns=10,  # Maximum conversation turns per evaluation
                    agent_name=agent_name,
                )
                
                # Save results to output directory
                agent_output_dir = output_dir / f"{agent_name}_test_cases"
                agent_output_dir.mkdir(parents=True, exist_ok=True)
                
                for session_id, eval_data in results.items():
                    output_file = agent_output_dir / f"{session_id}.json"
                    with output_file.open('w') as f:
                        json.dump(eval_data, f, indent=2)
                
                logger.info(f"Generated {len(results)} evaluation cases for agent '{agent_name}'")
                
            except Exception as e:
                logger.error(f"Error generating evaluation data for agent '{agent_name}': {str(e)}")
                logger.exception(e)
                # Fall back to legacy approach for this agent if AutomaticEvalDataGenerator fails
                logger.warning(f"Falling back to legacy generation for agent '{agent_name}'")
                self._generate_legacy({agent_name: stories}, tools_path, output_dir)
    
    def _load_openapi_spec(self, tools_path: Path) -> Dict:
        """
        Load or convert tools definition to OpenAPI specification format.
        
        Supports:
        - JSON files with OpenAPI specification
        - Python files with @tool decorated functions
        
        Args:
            tools_path: Path to tools definition file (Python or JSON)
            
        Returns:
            OpenAPI specification dictionary
        """
        # Check if tools_path is a JSON file with OpenAPI spec
        if tools_path.suffix == '.json':
            try:
                with tools_path.open('r') as f:
                    spec = json.load(f)
                    # Validate it looks like an OpenAPI spec
                    if 'openapi' in spec or 'swagger' in spec or 'paths' in spec:
                        logger.info(f"Loaded OpenAPI specification from {tools_path}")
                        return spec
            except Exception as e:
                logger.warning(f"Could not load JSON as OpenAPI spec: {e}")
        
        # If it's a Python file, try to load tools and convert to OpenAPI
        if tools_path.suffix == '.py':
            try:
                logger.info(f"Loading Python tools from {tools_path} and converting to OpenAPI spec")
                return self._convert_python_tools_to_openapi(tools_path)
            except Exception as e:
                logger.warning(f"Could not convert Python tools to OpenAPI spec: {e}")
                logger.exception(e)
        
        # If not a valid OpenAPI JSON or Python file, return minimal spec
        logger.warning(f"OpenAPI spec not found or invalid at {tools_path}. Using minimal spec.")
        logger.warning("For best results, provide an OpenAPI specification JSON file or Python tools file.")
        
        # Return minimal OpenAPI spec structure
        return {
            "openapi": "3.0.0",
            "info": {
                "title": "Agent Tools API",
                "version": "1.0.0"
            },
            "paths": {}
        }
    
    def _convert_python_tools_to_openapi(self, tools_path: Path) -> Dict:
        """
        Convert Python tools (with @tool decorators) to OpenAPI specification.
        
        Args:
            tools_path: Path to Python file containing tool definitions
            
        Returns:
            OpenAPI specification dictionary
        """
        import importlib.util
        import sys
        from ibm_watsonx_orchestrate.agent_builder.tools import get_all_python_tools
        
        # Clear any previously loaded tools
        from ibm_watsonx_orchestrate.agent_builder.tools.python_tool import _all_tools
        _all_tools.clear()
        
        # Load the Python module
        spec = importlib.util.spec_from_file_location("tools_module", tools_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Could not load module from {tools_path}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules["tools_module"] = module
        spec.loader.exec_module(module)
        
        # Get all tools that were registered via @tool decorator
        tools = get_all_python_tools()
        
        if not tools:
            logger.warning(f"No tools found in {tools_path}")
            return {
                "openapi": "3.1.0",
                "info": {
                    "title": "Agent Tools API",
                    "version": "1.0.0"
                },
                "paths": {}
            }
        
        # Convert tools to OpenAPI paths and schemas
        paths = {}
        schemas = {}
        
        for tool in tools:
            tool_spec = tool.__tool_spec__
            tool_name = tool_spec.name
            path = f"/tools/{tool_name}"
            
            # Create request schema name (capitalize and format)
            request_schema_name = self._format_schema_name(tool_name, "Request")
            
            # Build request body schema from input schema
            request_schema = {
                "type": "object",
                "properties": {},
                "required": [],
                "title": request_schema_name,
                "description": f"Request model for the {tool_name} tool"
            }
            
            if tool_spec.input_schema and tool_spec.input_schema.properties:
                for param_name, param_schema in tool_spec.input_schema.properties.items():
                    param_dict = param_schema.model_dump(exclude_none=True)
                    # Clean up the schema - remove internal fields
                    param_dict.pop('in_field', None)
                    param_dict.pop('aliasName', None)
                    param_dict.pop('wrap_data', None)
                    request_schema["properties"][param_name] = param_dict
                
                if tool_spec.input_schema.required:
                    request_schema["required"] = tool_spec.input_schema.required
            
            # Store the schema in components
            schemas[request_schema_name] = request_schema
            
            # Build the path operation
            operation_id = f"{tool_name}_tools_{tool_name}_post"
            
            paths[path] = {
                "post": {
                    "tags": ["Tools"],
                    "summary": self._format_summary(tool_name),
                    "description": tool_spec.description or f"Execute {tool_name}",
                    "operationId": operation_id,
                    "parameters": [
                        {
                            "name": "tool_name",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "string",
                                "default": tool_name,
                                "title": "Tool Name"
                            }
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{request_schema_name}"
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful Response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "title": f"Response {self._format_summary(tool_name)} Tools {self._format_summary(tool_name)} Post"
                                    }
                                }
                            }
                        },
                        "422": {
                            "description": "Validation Error",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/HTTPValidationError"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        
        # Add standard validation error schemas
        schemas["ValidationError"] = {
            "properties": {
                "loc": {
                    "items": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "integer"}
                        ]
                    },
                    "type": "array",
                    "title": "Location"
                },
                "msg": {
                    "type": "string",
                    "title": "Message"
                },
                "type": {
                    "type": "string",
                    "title": "Error Type"
                }
            },
            "type": "object",
            "required": ["loc", "msg", "type"],
            "title": "ValidationError"
        }
        
        schemas["HTTPValidationError"] = {
            "properties": {
                "detail": {
                    "items": {
                        "$ref": "#/components/schemas/ValidationError"
                    },
                    "type": "array",
                    "title": "Detail"
                }
            },
            "type": "object",
            "title": "HTTPValidationError"
        }
        
        openapi_spec = {
            "openapi": "3.1.0",
            "info": {
                "title": "Agent API",
                "description": "API for Python Tools",
                "version": "1.0.0"
            },
            "servers": [
                {
                    "url": "https://api.example.com/v1",
                    "description": "Production server"
                }
            ],
            "paths": paths,
            "components": {
                "schemas": schemas
            }
        }
        
        logger.info(f"Converted {len(tools)} Python tools to OpenAPI specification")
        return openapi_spec
    
    def _format_schema_name(self, tool_name: str, suffix: str) -> str:
        """Format tool name into schema name (e.g., 'get_user_info' -> 'Get_User_InfoRequest')"""
        parts = tool_name.split('_')
        formatted = '_'.join(part.capitalize() for part in parts)
        return f"{formatted}{suffix}"
    
    def _format_summary(self, tool_name: str) -> str:
        """Format tool name into summary (e.g., 'get_user_info' -> 'Get User Info')"""
        parts = tool_name.split('_')
        return ' '.join(part.capitalize() for part in parts)

    def analyze(self, data_path: str, tool_definition_path: str, mode: AnalyzeMode) -> None:
        if mode not in AnalyzeMode.__members__:
            logger.error(
                f"Invalid mode '{mode}' passed. `mode` must be either `enhanced` or `default`."
            )
            sys.exit(1)

        config = AnalyzeConfig(
            data_path=data_path,
            tool_definition_path=tool_definition_path,
            mode=mode
        )
        run_analyze(config)

    def summarize(self) -> None:
        pass

    def external_validate(self, config: Dict, data: List[str], credential:str, add_context: bool = False):
        validator = ExternalAgentValidation(credential=credential,
                                auth_scheme=config["auth_scheme"],
                                service_url=config["api_url"])
        
        summary = []
        for entry in data:
            results = validator.call_validation(entry, add_context)
            summary.append(results)

        return summary
    
    def generate_performance_test(self, agent_name: str, test_data: List[Tuple[str, str]]):
        performance_test = ExternalAgentPerformanceTest(
            agent_name=agent_name,
            test_data=test_data
        )
        generated_performance_tests = performance_test.generate_tests()

        return generated_performance_tests
    
    def list_red_teaming_attacks(self):
        print_attacks()

    def generate_red_teaming_attacks(
        self,
        attacks_list: str,
        datasets_path: str,
        agents_list_or_path: str,
        target_agent_name: str,
        output_dir: Optional[str] = None,
        max_variants: Optional[int] = None,
    ):
        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), "red_teaming_attacks")
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"No output directory specified. Using default: {output_dir}")

        url, tenant_name, token = self._get_env_config()

        results = attack_generator.main(
            AttackGeneratorConfig(
                attacks_list=attacks_list.split(","),
                datasets_path=datasets_path.split(","),
                agents_list_or_path=agents_list_or_path
                if os.path.exists(agents_list_or_path)
                else agents_list_or_path.split(","),
                target_agent_name=target_agent_name,
                output_dir=output_dir,
                max_variants=max_variants,
                auth_config=AuthConfig(
                    url=url,
                    tenant_name=tenant_name,
                    token=token,
                ),
            )
        )
        logger.info(f"Generated {len(results)} attacks and saved to {output_dir}")

    def run_red_teaming_attacks(self, attack_paths: str, output_dir: Optional[str] = None) -> None:
        url, tenant_name, token = self._get_env_config()

        if "WATSONX_SPACE_ID" in os.environ and "WATSONX_APIKEY" in os.environ:
            provider = "watsonx"
        elif "WO_INSTANCE" in os.environ and "WO_API_KEY" in os.environ:
            provider = "model_proxy"
        else:
            provider = "gateway"

        config_data = {
            "auth_config": AuthConfig(
                url=url,
                tenant_name=tenant_name,
                token=token,
            ),
            "provider_config": ProviderConfig(
                provider=provider,
                model_id="meta-llama/llama-3-405b-instruct",
            ),
        }

        config_data["attack_paths"] = attack_paths.split(",")
        if output_dir:
            config_data["output_dir"] = output_dir
        else:
            config_data["output_dir"] = os.path.join(os.getcwd(), "red_teaming_results")
            os.makedirs(config_data["output_dir"], exist_ok=True)
            logger.info(f"No output directory specified. Using default: {config_data['output_dir']}")
            

        config = AttackConfig(**config_data)

        run_attacks(config)
