import logging
from typing import List
import json
import sys

import typer
from typing_extensions import Annotated

from ibm_watsonx_orchestrate.agent_builder.models.types import ModelType
from ibm_watsonx_orchestrate.agent_builder.model_policies.types import  ModelPolicyStrategyMode
from ibm_watsonx_orchestrate.cli.commands.models.models_controller import ModelsController


logger = logging.getLogger(__name__)
models_app = typer.Typer(no_args_is_help=True)
models_policy_app = typer.Typer(no_args_is_help=True)
models_app.add_typer(models_policy_app, name='policy', help='Add or remove pseudo models which route traffic between multiple downstream models')

@models_app.command(name="list", help="List available models")
def model_list(
    print_raw: Annotated[
        bool,
        typer.Option("--raw", "-r", help="Display the list of models in a non-tabular format"),
    ] = False,
):
    models_controller = ModelsController()
    models_controller.list_models(print_raw=print_raw)

@models_app.command(name="import", help="Import models from spec file")
def models_import(
     file: Annotated[
        str,
        typer.Option(
            "--file",
            "-f",
            help="Path to spec file containing model details.",
        ),
    ],
    app_id: Annotated[
        str, typer.Option(
            '--app-id', '-a',
            help='The app id of a key_value connection containing authentications details for the model provider.'
        )
    ] = None,
):
    models_controller = ModelsController()
    models = models_controller.import_model(
        file=file,
        app_id=app_id
    )
    for model in models:
        models_controller.publish_or_update_models(model=model)

@models_app.command(name="add", help="Add an llm from a custom provider")
def models_add(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="The name of the model to add"),
    ],
    description: Annotated[
        str,
        typer.Option('--description', '-d', help='The description of the model to add'),
    ] = None,
    display_name: Annotated[
        str,
        typer.Option('--display-name', help='What name should this llm appear as within the ui'),
    ] = None,
    provider_config: Annotated[
        str,
        typer.Option(
            "--provider-config",
            help="LLM provider configuration in JSON format (e.g., '{\"customHost\": \"xyz\"}')",
        ),
    ] = None,
    app_id: Annotated[
        str, typer.Option(
            '--app-id', '-a',
            help='The app id of a key_value connection containing authentications details for the model provider.'
        )
    ] = None,
    type: Annotated[
        ModelType,
        typer.Option('--type', help='What type of model is it'),
    ] = ModelType.CHAT,
):
    provider_config_dict = {}
    if provider_config:
        try:
            provider_config_dict = json.loads(provider_config)
        except:
            logger.error(f"Failed to parse provider config. '{provider_config}' is not valid json")
            sys.exit(1)

    models_controller = ModelsController()
    model = models_controller.create_model(
        name=name,
        description=description,
        display_name=display_name,
        provider_config_dict = provider_config_dict,
        model_type=type,
        app_id=app_id,
    )
    models_controller.publish_or_update_models(model=model)



@models_app.command(name="remove", help="Remove an llm from a custom provider")
def models_remove(
        name: Annotated[
            str,
            typer.Option("--name", "-n", help="The name of the model to remove"),
        ]
):
    models_controller = ModelsController()
    models_controller.remove_model(name=name)

@models_app.command(name="export", help="Export a model and its dependencies to a zip file or yaml")
def models_export(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the model you wish to export"),
    ],
    output_path: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Path to where the file containing the exported data should be saved",
        ),
    ],
):
    models_controller = ModelsController()
    models_controller.export_model(name=name, output_path=output_path)

@models_policy_app.command(name='import', help='Add a model policy')
def models_policy_import(
    file: Annotated[
        str,
        typer.Option(
            "--file",
            "-f",
            help="Path to spec file containing model details.",
        ),
    ],
):
    models_controller = ModelsController()
    policies = models_controller.import_model_policy(
        file=file
    )
    for policy in policies:
        models_controller.publish_or_update_model_policies(policy=policy)

@models_policy_app.command(name='export', help='Export a model policy')
def models_policy_export(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name of the model policy you wish to export"),
    ],
    output_path: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Path to where the file containing the data should be saved",
        )
    ],
):
    models_controller = ModelsController()
    models_controller.export_model_policy(name=name, output_path=output_path)

@models_policy_app.command(name='add', help='Add a model policy')
def models_policy_add(
        name: Annotated[
            str,
            typer.Option("--name", "-n", help="The name of the model policy to add"),
        ],
        models: Annotated[
            List[str],
            typer.Option('--model', '-m', help='A list of model names the policy should contain'),
        ],
        strategy: Annotated[
            ModelPolicyStrategyMode,
            typer.Option('--strategy', '-s', help='How to spread traffic across models'),
        ],
        retry_attempts: Annotated[
            int,
            typer.Option('--retry-attempts', help='The number of attempts to retry'),
        ] = None,
        strategy_on_code: Annotated[
            List[int],
            typer.Option('--strategy-on-code', help='The http status to consider invoking the strategy'),
        ] = None,
        retry_on_code: Annotated[
            List[int],
            typer.Option('--retry-on-code', help='The http status to consider retrying the llm call'),
        ] = None,
        display_name: Annotated[
            str,
            typer.Option('--display-name', help='What name should this llm appear as within the ui'),
        ] = None,
        description: Annotated[
            str,
            typer.Option('--description', help='Description of the policy for display in the ui'),
        ] = None
):
    models_controller = ModelsController()
    policy = models_controller.create_model_policy(
        name=name,
        models=models,
        strategy=strategy,
        strategy_on_code=strategy_on_code,
        retry_on_code=retry_on_code,
        retry_attempts=retry_attempts,
        display_name=display_name,
        description=description
    )
    models_controller.publish_or_update_model_policies(policy=policy)



@models_policy_app.command(name='remove', help='Remove a model policy')
def models_policy_remove(
        name: Annotated[
            str,
            typer.Option("--name", "-n", help="The name of the model policy to remove"),
        ]
):
    models_controller = ModelsController()
    models_controller.remove_policy(name=name)

if __name__ == "__main__":
    models_app()