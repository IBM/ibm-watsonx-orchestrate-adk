import json
import logging
import typer
import os
import yaml
import csv
import rich
import sys
import shutil

from rich.panel import Panel
from pathlib import Path
from dotenv import dotenv_values
from typing import Optional
from typing_extensions import Annotated

from ibm_watsonx_orchestrate import __version__
from ibm_watsonx_orchestrate.cli.commands.evaluations.evaluations_controller import EvaluationsController

logger = logging.getLogger(__name__)

evaluation_app = typer.Typer(no_args_is_help=True)

def read_env_file(env_path: Path|str) -> dict:
    return dotenv_values(str(env_path))

def validate_watsonx_credentials(user_env_file: str) -> bool:
    required_keys = ["WATSONX_SPACE_ID", "WATSONX_APIKEY"]
    
    if all(key in os.environ for key in required_keys):
        logger.info("WatsonX credentials validated successfully.")
        return
    
    if user_env_file is None:
        logger.error("WatsonX credentials are not set. Please set WATSONX_SPACE_ID and WATSONX_APIKEY in your system environment variables or include them in your enviroment file and pass it with --env-file option.")
        sys.exit(1)

    if not Path(user_env_file).exists():
        logger.error(f"Error: The specified environment file '{user_env_file}' does not exist.")
        sys.exit(1)
    
    user_env = read_env_file(user_env_file)
    
    if not all(key in user_env for key in required_keys):
        logger.error("Error: The environment file does not contain the required keys: WATSONX_SPACE_ID and WATSONX_APIKEY.")
        sys.exit(1)

    os.environ.update({key: user_env[key] for key in required_keys})
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
                help="Path to the external agent yaml",

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
    agent_name: Annotated[
        str,
        typer.Option(
            "--agent_name", "-a",
            help="Name of the native agent which has the external agent to test registered as a collaborater. See: https://developer.watson-orchestrate.ibm.com/agents/build_agent#native-agents)." \
            " If this parameter is pased, validation of the external agent is not run.",
            rich_help_panel="Parameters for Input Evaluation"
        )
    ] = None
):

    validate_watsonx_credentials(user_env_file)
    Path(output_dir).mkdir(exist_ok=True)
    shutil.copy(data_path, os.path.join(output_dir, "input_sample.tsv"))

    if agent_name is not None:
        eval_dir = os.path.join(output_dir, "evaluation")
        if os.path.exists(eval_dir):
            rich.print(f"[yellow]: found existing {eval_dir} in target directory. All content is removed.")
            shutil.rmtree(os.path.join(output_dir, "evaluation"))
        Path(eval_dir).mkdir(exist_ok=True)
        # save external agent config even though its not used for evaluation
        # it can help in later debugging customer agents
        with open(os.path.join(eval_dir, "external_agent_cfg.yaml"), "w+") as f:
            with open(external_agent_config, "r") as cfg:
                external_agent_config = yaml.safe_load(cfg)
            yaml.safe_dump(external_agent_config, f, indent=4)

        rich.print(f"[gold3]Starting evaluation of inputs in '{data_path}' against '{agent_name}'[/gold3]")
        performance_test(
            agent_name=agent_name,
            data_path=data_path,
            output_dir=eval_dir,
            user_env_file=user_env_file
        )
    
    else:
        with open(external_agent_config, "r") as f:
            external_agent_config = yaml.safe_load(f)
        controller = EvaluationsController()
        test_data = []
        with open(data_path, "r") as f:
            csv_reader = csv.reader(f, delimiter="\t")
            for line in csv_reader:
                test_data.append(line[0])

        # save validation results in "validation_results" sub-dir
        validation_folder = Path(output_dir) / "validation_results"
        if os.path.exists(validation_folder):
            rich.print(f"[yellow]: found existing {validation_folder} in target directory. All content is removed.")
            shutil.rmtree(validation_folder)
        validation_folder.mkdir(exist_ok=True, parents=True)

        # validate the inputs in the provided csv file
        summary = controller.external_validate(external_agent_config, test_data, credential)
        with open(validation_folder / "validation_results.json", "w") as f:
            json.dump(summary, f, indent=4)
        
        # validate sample block inputs
        rich.print("[gold3]Validating external agent to see if it can handle an array of messages.")
        block_input_summary = controller.external_validate(external_agent_config, test_data, credential, add_context=True)
        with open(validation_folder / "sample_block_validation_results.json", "w") as f:
            json.dump(block_input_summary, f, indent=4)

        user_validation_successful = all([item["success"] for item in summary])
        block_validation_successful = all([item["success"] for item in block_input_summary])

        if user_validation_successful and block_validation_successful:
            msg = (
                f"[green]Validation is successful. The result is saved to '{str(validation_folder)}'.[/green]\n"
                "You can add the external agent as a collaborator agent. See: https://developer.watson-orchestrate.ibm.com/agents/build_agent#native-agents."
            )
        else:
            msg = f"[dark_orange]Schema validation did not succeed. See '{str(validation_folder)}' for failures.[/dark_orange]"

        rich.print(Panel(msg))
