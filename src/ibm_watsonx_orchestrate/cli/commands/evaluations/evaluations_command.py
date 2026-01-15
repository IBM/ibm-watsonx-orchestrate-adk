import json
import logging
import typer
import os
import csv
import rich
import sys
import shutil
import tempfile
import random

from rich.panel import Panel
from pathlib import Path
from dotenv import dotenv_values
from typing import Optional
from typing_extensions import Annotated

try:
    from ibm_watsonx_orchestrate import __version__
    from ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller import EvaluationsController, EvaluateMode, USE_LEGACY_EVAL
    from ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_environment_manager import run_environment_manager
    from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentsController
    _import_error = False
except ImportError:
    _import_error = True

from ibm_watsonx_orchestrate.utils.file_manager import safe_open

logger = logging.getLogger(__name__)

HIDE_ENVIRONMENT_MGR_PANEL = os.environ.get("HIDE_ENVIRONMENT_MGR_PANEL", "true").lower() == "true"

evaluation_app = typer.Typer(no_args_is_help=True)

def _check_import_error():
    if _import_error:
        logger.error("AgentOps not found. Please install it using `pip install --upgrade \"ibm-watsonx-orchestrate[agentops]\"`")
        sys.exit(1)

def _feature_requires_legacy_eval():
    if not USE_LEGACY_EVAL:
        logger.error("Feature requires legacy evaluation. Please enable it using `export USE_LEGACY_EVAL=TRUE`")
        sys.exit(1)

def _native_agent_template():
    return {
        "spec_version": "v1",
        "style": "default",
        "llm": "watsonx/meta-llama/llama-3-405b-instruct",
        "name": "",
        "description": "Native agent for validating external agent",
        "instructions": "Use the tools and external agent(s) provided to answer the user's question.  If you do not have enough information to answer the question, say so.  If you need more information, ask follow up questions.",
        "collaborators": []
    }

def _random_native_agent_name(external_agent_name):
    """ Generate a native agent name in the following format to ensure uniqueness:

    "external_agent_validation_{external_agent_name}_{random number}

    So if the external agent name is, "QA_Agent", and the random number generated is, '100', the native agent name is:
    "external_agent_validation_QA_Agent_100"

    """
    seed = 42
    random.seed(seed)
    
    return f"external_agent_validation_{external_agent_name}_{random.randint(0, 100)}"

def read_env_file(env_path: Path|str) -> dict:
    return dotenv_values(str(env_path))

def validate_watsonx_credentials(user_env_file: str) -> bool:
    return True #Use AI Gateway with active environment and cached token by default so credentials no longer required

def read_csv(data_path: str, delimiter="\t"):
    data = []
    with safe_open(data_path, "r") as f:
        tsv_reader = csv.reader(f, delimiter=delimiter)
        for line in tsv_reader:
            data.append(line)
    
    return data

def performance_test(agent_name, data_path, output_dir = None, user_env_file = None):
    test_data = read_csv(data_path)

    controller = EvaluationsController()
    generated_performance_tests = controller.generate_performance_test(agent_name, test_data)
    
    generated_perf_test_dir = Path(output_dir) / "generated_performance_tests"
    generated_perf_test_dir.mkdir(exist_ok=True, parents=True)

    for idx, test in enumerate(generated_performance_tests):
        test_name = f"validate_external_agent_evaluation_test_{idx}.json"
        with safe_open(generated_perf_test_dir / test_name, encoding="utf-8", mode="w+") as f:
            json.dump(test, f, indent=4)

    rich.print(f"Performance test cases saved at path '{str(generated_perf_test_dir)}'")
    rich.print("[gold3]Running Performance Test")
    evaluate(output_dir=output_dir, test_paths=str(generated_perf_test_dir))

@evaluation_app.command(name="evaluate", help="Evaluate an agent against a set of test cases")
def evaluate(
    config_file: Annotated[
        Optional[str],
        typer.Option(
            "--config", "-c",
            help="Path to YAML configuration file containing evaluation settings."
        )
    ] = None,
    test_paths: Annotated[
        Optional[str],
        typer.Option(
            "--test-paths", "-p", 
            help="Paths to the test files and/or directories to evaluate, separated by commas."
        ),
    ] = None,
    output_dir: Annotated[
        Optional[str], 
        typer.Option(
            "--output-dir", "-o",
            help="Directory to save the evaluation results."
        )
    ] = None,
    user_env_file: Annotated[
        Optional[str],
        typer.Option(
            "--env-file", "-e", 
            help="Path to a .env file that overrides default.env. Then environment variables override both."
        ),
    ] = None,
    env_manager_path: Annotated[
        Optional[str],
        typer.Option(
            "--env-manager-path",
            help="""
                Path to YAML configuration file containing environment settings.\n
                See `./examples/evaluations/environment_manager` on how to create the environment manager file.
                Note: When using this feature, you must pass the `output_dir`.
            """,
            rich_help_panel="Environment Manager",
            hidden=HIDE_ENVIRONMENT_MGR_PANEL
        )
    ] = None,
):
    _check_import_error()
    validate_watsonx_credentials(user_env_file)

    if not USE_LEGACY_EVAL:
        logger.warning("Using beta evaluation. This feature is still in beta.")
        logger.warning("To use legacy evaluation, please enable it using `export USE_LEGACY_EVAL=TRUE`")

    if env_manager_path:
        if output_dir:
            return run_environment_manager(
                environment_manager_path=env_manager_path,
                output_dir=output_dir,
            )
        else:
            logger.error("Error: `--env_manager_path`, `--output_dir` must be provided to use the environment manager feature.")
            sys.exit(1)

    if not config_file:
        if not test_paths or not output_dir:
            logger.error("Error: Both --test-paths and --output-dir must be provided when not using a config file")
            exit(1)

    controller = EvaluationsController()
    controller.evaluate(config_file=config_file, test_paths=test_paths, output_dir=output_dir)


@evaluation_app.command(name="record", help="Record chat sessions and create test cases")
def record(
    output_dir: Annotated[
        Optional[str], 
        typer.Option(
            "--output-dir", "-o",
            help="Directory to save the recorded chats."
        )
    ] = None,
    user_env_file: Annotated[
        Optional[str],
        typer.Option(
            "--env-file", "-e", 
            help="Path to a .env file that overrides default.env. Then environment variables override both."
        ),
    ] = None
):
    _check_import_error()
    _feature_requires_legacy_eval()
    
    validate_watsonx_credentials(user_env_file)
    controller = EvaluationsController()
    controller.record(output_dir=output_dir)


@evaluation_app.command(name="generate", help="Generate test cases from user stories and tools")
def generate(
    stories_path: Annotated[
        str,
        typer.Option(
            "--stories-path", "-s",
            help="Path to the CSV file containing user stories for test case generation. "
                 "The file has 'story' and 'agent' columns."
        )
    ],
    tools_path: Annotated[
        str,
        typer.Option(
            "--tools-path", "-t",
            help="Path to the directory containing tool definitions."
        )
    ],
    output_dir: Annotated[
        Optional[str],
        typer.Option(
            "--output-dir", "-o",
            help="Directory to save the generated test cases."
        )
    ] = None,
    user_env_file: Annotated[
        Optional[str],
        typer.Option(
            "--env-file", "-e", 
            help="Path to a .env file that overrides default.env. Then environment variables override both."
        ),
    ] = None
):
    _check_import_error()

    validate_watsonx_credentials(user_env_file)
    controller = EvaluationsController()
    controller.generate(stories_path=stories_path, tools_path=tools_path, output_dir=output_dir)


@evaluation_app.command(name="analyze", help="Analyze the results of an evaluation run")
def analyze(data_path: Annotated[
        str,
        typer.Option(
            "--data-path", "-d",
            help="Path to the directory that has the saved results"
        )
    ],
    tool_definition_path: Annotated[
        Optional[str],
        typer.Option(
            "--tools-path", "-t",
            help="Path to the directory containing tool definitions."
        )
    ] = None,
    user_env_file: Annotated[
        Optional[str],
        typer.Option(
            "--env-file", "-e", 
            help="Path to a .env file that overrides default.env. Then environment variables override both."
        ),
    ] = None,
    mode: Annotated[
        Optional[str],
        typer.Option(
            "--mode", "-m", 
            help="""
            Either `default` or `enhanced`. `enhanced` mode optionally provides doc string enrichments for tools.
            """
        ),
    ] = "default"
):

    _check_import_error()
    _feature_requires_legacy_eval()

    validate_watsonx_credentials(user_env_file)
    controller = EvaluationsController()
    controller.analyze(
        data_path=data_path,
        tool_definition_path=tool_definition_path,
        mode=mode
    )

@evaluation_app.command(name="validate-external", help="Validate an external agent against a set of inputs")
def validate_external(
    data_path: Annotated[
        str,
        typer.Option(
            "--tsv", "-t",
            help="Path to .tsv file of inputs"
        )
    ],
    external_agent_config: Annotated[
            str,
            typer.Option(
                "--external-agent-config", "-ext",
                help="Path to the external agent json file",

            )
        ],
    credential: Annotated[
        str,
        typer.Option(
            "--credential", "-crd",
            help="credential string",
            rich_help_panel="Parameters for Validation"
        )
    ] = None,
    output_dir: Annotated[
        str,
        typer.Option(
            "--output", "-o",
            help="where to save the validation results"
        )
    ] = "./test_external_agent",
    user_env_file: Annotated[
        Optional[str],
        typer.Option(
            "--env-file", "-e", 
            help="Path to a .env file that overrides default.env. Then environment variables override both."
        ),
    ] = None,
    perf_test: Annotated[
        bool,
        typer.Option(
            "--perf", "-p",
            help="Performance test your external agent against the provide user stories.",
            rich_help_panel="Parameters for Input Evaluation",
        )
    ] = False
):
    _check_import_error()
    _feature_requires_legacy_eval()

    validate_watsonx_credentials(user_env_file)

    with safe_open(external_agent_config, 'r') as f:
        try:
            external_agent_config = json.load(f)
        except Exception:
            rich.print(
                f"[red]: Please provide a valid external agent spec in JSON format. See 'examples/evaluations/external_agent_validation/sample_external_agent_config.json' for an example."
            )
            sys.exit(1)

    eval_dir = os.path.join(output_dir, "evaluations")
    if perf_test:
        if os.path.exists(eval_dir):
            rich.print(f"[yellow]: found existing {eval_dir} in target directory. All content is removed.")
            shutil.rmtree(eval_dir)
        Path(eval_dir).mkdir(exist_ok=True, parents=True)
        # save external agent config even though its not used for evaluation
        # it can help in later debugging customer agents
        with safe_open(os.path.join(eval_dir, f"external_agent_cfg.json"), "w+") as f:
            json.dump(external_agent_config, f, indent=4)

        logger.info("Registering External Agent")
        agent_controller = AgentsController()

        external_agent_config["title"] = external_agent_config["name"]
        external_agent_config["auth_config"] = {"token": credential}
        external_agent_config["spec_version"] = external_agent_config.get("spec_version", "v1")
        external_agent_config["provider"] = "external_chat"

        with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8", suffix=".json", delete=True) as fp:
            json.dump(external_agent_config, fp, indent=4)
            fp.flush()
            agents = agent_controller.import_agent(file=os.path.abspath(fp.name), app_id=None)
            agent_controller.publish_or_update_agents(agents)

        logger.info("Registering Native Agent")

        native_agent_template = _native_agent_template()
        agent_name = _random_native_agent_name(external_agent_config["name"])
        rich.print(f"[blue][b]Generated native agent name is: [i]{agent_name}[/i][/b]")
        native_agent_template["name"] = agent_name
        native_agent_template["collaborators"] = [external_agent_config["name"]]

        with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8", suffix=".json", delete=True) as fp:
            json.dump(native_agent_template, fp, indent=4)
            fp.flush()
            agents = agent_controller.import_agent(file=os.path.abspath(fp.name), app_id=None)
            agent_controller.publish_or_update_agents(agents)

        rich.print(f"[gold3]Starting evaluation of inputs in '{data_path}' against '{agent_name}'[/gold3]")
        performance_test(
            agent_name=agent_name,
            data_path=data_path,
            output_dir=eval_dir,
            user_env_file=user_env_file
        )
    
    else:
        controller = EvaluationsController()
        test_data = []
        with safe_open(data_path, "r") as f:
            csv_reader = csv.reader(f, delimiter="\t")
            for line in csv_reader:
                test_data.append(line[0])

        # save validation results in "validate_external" sub-dir
        validation_folder = Path(output_dir) / "validate_external"
        if os.path.exists(validation_folder):
            rich.print(f"[yellow]: found existing {validation_folder} in target directory. All content is removed.")
            shutil.rmtree(validation_folder)
        validation_folder.mkdir(exist_ok=True, parents=True)
        shutil.copy(data_path, os.path.join(validation_folder, "input_sample.tsv"))

        # validate the inputs in the provided csv file
        summary = controller.external_validate(external_agent_config, test_data, credential)
        # validate sample block inputs
        rich.print("[gold3]Validating external agent against an array of messages.")
        block_input_summary = controller.external_validate(external_agent_config, test_data, credential, add_context=True)
        
        with safe_open(validation_folder / "validation_results.json", "w") as f:
            json.dump([summary, block_input_summary], f, indent=4)
        
        user_validation_successful = all([item["success"] for item in summary])
        block_validation_successful = all([item["success"] for item in block_input_summary])

        if user_validation_successful and block_validation_successful:
            msg = (
                f"[green]Validation is successful. The result is saved to '{str(validation_folder)}'.[/green]\n"
            )
        else:
            msg = f"[dark_orange]Schema validation did not succeed. See '{str(validation_folder)}' for failures.[/dark_orange]"

        rich.print(Panel(msg))

@evaluation_app.command(name="validate-native", help="Validate native agents against a set of inputs")
def validate_native(
    data_path: Annotated[
        str,
        typer.Option(
            "--tsv", "-t",
            help="Path to .tsv file of inputs. The first column of the TSV is the user story, the second column is the  expected final output from the agent, and the third column is the name of the agent"
        )
    ],
    output_dir: Annotated[
        str,
        typer.Option(
            "--output", "-o",
            help="where to save the validation results"
        )
    ] = "./test_native_agent",
    user_env_file: Annotated[
        Optional[str],
        typer.Option(
            "--env-file", "-e", 
            help="Path to a .env file that overrides default.env. Then environment variables override both."
        ),
    ] = None,
):
    _check_import_error()
    _feature_requires_legacy_eval()

    validate_watsonx_credentials(user_env_file)
    
    eval_dir = os.path.join(output_dir, "native_agent_evaluations")
    if os.path.exists(eval_dir):
        rich.print(f"[yellow]: found existing {eval_dir} in target directory. All content is removed.")
        shutil.rmtree(eval_dir)
    Path(eval_dir).mkdir(exist_ok=True, parents=True)

    test_data_path = Path(eval_dir) / "generated_test_data"
    test_data_path.mkdir(exist_ok=True, parents=True)
    
    controller = EvaluationsController()
    test_data = read_csv(data_path) # tab seperated file containing the user story, the final outcome, and the agent name
    
    for idx, row in enumerate(test_data):
        agent_name = row[2] # agent name
        dataset = [row[0:2]] # user story, expected final outcome
        generated_test_data = controller.generate_performance_test(agent_name=agent_name, test_data=dataset)
        for test_data in generated_test_data:
            test_name = f"native_agent_evaluation_test_{idx}.json"
            with safe_open(test_data_path / test_name, encoding="utf-8", mode="w+") as f:
                json.dump(test_data, f, indent=4)
    
    evaluate(output_dir=eval_dir, test_paths=str(test_data_path))

@evaluation_app.command(name="quick-eval",
                        short_help="Evaluate agent against a suite of static metrics and LLM-as-a-judge metrics",
                        help="""
                        Use the quick-eval command to evaluate your agent against a suite of static metrics and LLM-as-a-judge metrics.
                        """)
def quick_eval(
    config_file: Annotated[
        Optional[str],
        typer.Option(
            "--config", "-c",
            help="Path to YAML configuration file containing evaluation settings."
        )
    ] = None,
    test_paths: Annotated[
        Optional[str],
        typer.Option(
            "--test-paths", "-p", 
            help="Paths to the test files and/or directories to evaluate, separated by commas."
        ),
    ] = None,
    tools_path: Annotated[
        str,
        typer.Option(
            "--tools-path", "-t",
            help="Path to the directory containing tool definitions."
        )
    ] = None,
    output_dir: Annotated[
        Optional[str], 
        typer.Option(
            "--output-dir", "-o",
            help="Directory to save the evaluation results."
        )
    ] = None,
    user_env_file: Annotated[
        Optional[str],
        typer.Option(
            "--env-file", "-e", 
            help="Path to a .env file that overrides default.env. Then environment variables override both."
        ),
    ] = None
):
    _check_import_error()
    _feature_requires_legacy_eval()

    if not config_file:
        if not test_paths or not output_dir:
            logger.error("Error: Both --test-paths and --output-dir must be provided when not using a config file")
            exit(1)
    
    validate_watsonx_credentials(user_env_file)

    if tools_path is None:
        logger.error("When running `quick-eval`, please provide the path to your tools file.")
        sys.exit(1)
    
    controller = EvaluationsController()
    controller.evaluate(
        config_file=config_file,
        test_paths=test_paths,
        output_dir=output_dir,
        tools_path=tools_path, mode=EvaluateMode.referenceless
    )


red_teaming_app = typer.Typer(no_args_is_help=True)
evaluation_app.add_typer(red_teaming_app, name="red-teaming", help="Generate and run red-teaming attacks on your agents")


@red_teaming_app.command("list", help="List available red-teaming attack plans")
def list_plans():
    _check_import_error()
    _feature_requires_legacy_eval()

    controller = EvaluationsController()
    controller.list_red_teaming_attacks()


@red_teaming_app.command("plan", help="Generate red-teaming attacks")
def plan(
    attacks_list: Annotated[
        str,
        typer.Option(
            "--attacks-list",
            "-a",
            help="Comma-separated list of red-teaming attacks to generate.",
        ),
    ],
    datasets_path: Annotated[
        str,
        typer.Option(
            "--datasets-path",
            "-d",
            help="Path to datasets for red-teaming. This can also be a comma-separated list of files or directories.",
        ),
    ],
    agents_list_or_path: Annotated[
        str, typer.Option("--agents-path", "-g", help="Path to the directory containing all agent definitions or a comma-separated list of agent names.")
    ],
    target_agent_name: Annotated[
        str,
        typer.Option(
            "--target-agent-name",
            "-t",
            help="Name of the target agent to attack (should be present in agents-path).",
        ),
    ],
    output_dir: Annotated[
        Optional[str],
        typer.Option("--output-dir", "-o", help="Directory to save generated attacks.")
    ]=None,
    user_env_file: Annotated[
        Optional[str],
        typer.Option(
            "--env-file",
            "-e",
            help="Path to a .env file that overrides default.env. Then environment variables override both.",
        ),
    ] = None,
    max_variants: Annotated[
        Optional[int],
        typer.Option(
            "--max_variants",
            "-n",
            help="Number of variants to generate per attack type.",
        ),
    ] = None,

):
    _check_import_error()   
    _feature_requires_legacy_eval()

    validate_watsonx_credentials(user_env_file)
    controller = EvaluationsController()
    controller.generate_red_teaming_attacks(
        attacks_list=attacks_list,
        datasets_path=datasets_path,
        agents_list_or_path=agents_list_or_path,
        target_agent_name=target_agent_name,
        output_dir=output_dir,
        max_variants=max_variants,
    )


@red_teaming_app.command("run", help="Run red-teaming attacks")
def run(
    attack_paths: Annotated[
        str,
        typer.Option(
            "--attack-paths",
            "-a",
            help="Path or list of paths (comma-separated) to directories containing attack files.",
        ),
    ],
    output_dir: Annotated[
        Optional[str],
        typer.Option("--output-dir", "-o", help="Directory to save attack results."),
    ] = None,
    user_env_file: Annotated[
        Optional[str],
        typer.Option(
            "--env-file",
            "-e",
            help="Path to a .env file that overrides default.env. Then environment variables override both.",
        ),
    ] = None,
):  
    _check_import_error()
    _feature_requires_legacy_eval()

    validate_watsonx_credentials(user_env_file)
    controller = EvaluationsController()
    controller.run_red_teaming_attacks(attack_paths=attack_paths, output_dir=output_dir)