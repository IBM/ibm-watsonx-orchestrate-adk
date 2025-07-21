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

from ibm_watsonx_orchestrate import __version__
from ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller import EvaluationsController
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import AgentsController

logger = logging.getLogger(__name__)

evaluation_app = typer.Typer(no_args_is_help=True)

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
    required_sets = [
        ["WATSONX_SPACE_ID", "WATSONX_APIKEY"],
        ["WO_INSTANCE", "WO_API_KEY"]
    ]
    
    def has_valid_keys(env: dict) -> bool:
        return any(all(key in env for key in key_set) for key_set in required_sets)

    if has_valid_keys(os.environ):
        logger.info("WatsonX credentials validated successfully.")
        return
    
    if user_env_file is None:
        logger.error("WatsonX credentials are not set. Please set either WATSONX_SPACE_ID and WATSONX_APIKEY or WO_INSTANCE and WO_API_KEY in your system environment variables or include them in your environment file and pass it with --env-file option.")
        sys.exit(1)

    if not Path(user_env_file).exists():
        logger.error(f"Error: The specified environment file '{user_env_file}' does not exist.")
        sys.exit(1)
    
    user_env = read_env_file(user_env_file)
    
    if not has_valid_keys(user_env):
        logger.error("Error: The environment file does not contain the required keys: either WATSONX_SPACE_ID and WATSONX_APIKEY or WO_INSTANCE and WO_API_KEY.")
        sys.exit(1)

    # Update os.environ with whichever set is present
    for key_set in required_sets:
        if all(key in user_env for key in key_set):
            os.environ.update({key: user_env[key] for key in key_set})
            break
    logger.info("WatsonX credentials validated successfully.")

def read_csv(data_path: str, delimiter="\t"):
    data = []
    with open(data_path, "r") as f:
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
        with open(generated_perf_test_dir / test_name, encoding="utf-8", mode="w+") as f:
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
    ] = None
):
    if not config_file:
        if not test_paths or not output_dir:
            logger.error("Error: Both --test-paths and --output-dir must be provided when not using a config file")
            exit(1)
    
    validate_watsonx_credentials(user_env_file)
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
    user_env_file: Annotated[
        Optional[str],
        typer.Option(
            "--env-file", "-e", 
            help="Path to a .env file that overrides default.env. Then environment variables override both."
        ),
    ] = None):

    validate_watsonx_credentials(user_env_file)
    controller = EvaluationsController()
    controller.analyze(data_path=data_path)

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

    validate_watsonx_credentials(user_env_file)

    with open(external_agent_config, 'r') as f:
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
        with open(os.path.join(eval_dir, f"external_agent_cfg.json"), "w+") as f:
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
        with open(data_path, "r") as f:
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
        
        with open(validation_folder / "validation_results.json", "w") as f:
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
