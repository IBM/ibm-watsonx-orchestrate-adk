import json
import logging
import typer
import os
import yaml
import csv
import rich
from pathlib import Path
import sys
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
            "--stories_path", "-s",
            help="Path to the CSV file containing user stories for test case generation. "
                 "The file has 'story' and 'agent' columns."
        )
    ],
    tools_path: Annotated[
        str,
        typer.Option(
            "--tools_path", "-t",
            help="Path to the directory containing tool definitions."
        )
    ],
    output_dir: Annotated[
        Optional[str],
        typer.Option(
            "--output_dir", "-o",
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
            "--data_path", "-d",
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


@evaluation_app.command(name="validate_external", help="Validate an external agent against a set of inputs")
def validate_external(
    data_path: Annotated[
        str,
        typer.Option(
            "--csv", "-c",
            help="Path to .csv file of inputs"
        )
    ],
    config: Annotated[
            str,
            typer.Option(
                "--config", "-cf",
                help="Path to the external agent yaml"
            )
        ],
    credential: Annotated[
        str,
        typer.Option(
            "--credential", "-crd",
            help="credential string"
        )
    ],
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
    ] = None
):
    
    validate_watsonx_credentials(user_env_file)
    with open(config, "r") as f:
        config = yaml.safe_load(f)
    controller = EvaluationsController()
    test_data = []
    with open(data_path, "r") as f:
        csv_reader = csv.reader(f)
        for line in csv_reader:
            test_data.append(line[0])
    results = controller.external_validate(config, test_data, credential)
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "validation_results.json"), "w") as f:
        json.dump(results, f)

    rich.print(f"[green] validation result is saved to {output_dir} [/green]")
