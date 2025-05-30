import logging
import os
import sys
from typing import List

import requests
import rich
import rich.highlighter
import typer
from typing_extensions import Annotated

from ibm_watsonx_orchestrate.cli.commands.server.server_command import get_default_env_file, merge_env
from ibm_watsonx_orchestrate.client.model_policies.model_policies_client import ModelPoliciesClient
from ibm_watsonx_orchestrate.client.model_policies.types import ModelPolicy, ModelPolicyInner, \
    ModelPolicyRetry, ModelPolicyStrategy, ModelPolicyStrategyMode, ModelPolicyTarget
from ibm_watsonx_orchestrate.client.models.models_client import ModelsClient
from ibm_watsonx_orchestrate.client.models.types import CreateVirtualModel, ModelType, ANTHROPIC_DEFAULT_MAX_TOKENS
from ibm_watsonx_orchestrate.client.utils import instantiate_client

logger = logging.getLogger(__name__)
models_app = typer.Typer(no_args_is_help=True)
models_policy_app = typer.Typer(no_args_is_help=True)
# models_app.add_typer(models_policy_app, name='policy', help='Add or remove pseudo models which route traffic between multiple downstream models')

WATSONX_URL = os.getenv("WATSONX_URL")

class ModelHighlighter(rich.highlighter.RegexHighlighter):
    base_style = "model."
    highlights = [r"(?P<name>(watsonx|virtual[-]model|virtual[-]policy)\/.+\/.+):"]

@models_app.command(name="list", help="List available models")
def model_list(
    print_raw: Annotated[
        bool,
        typer.Option("--raw", "-r", help="Display the list of models in a non-tabular format"),
    ] = False,
):
    models_client: ModelsClient = instantiate_client(ModelsClient)
    model_policies_client: ModelPoliciesClient = instantiate_client(ModelPoliciesClient)
    global WATSONX_URL
    default_env_path = get_default_env_file()
    merged_env_dict = merge_env(
        default_env_path,
        None
    )

    if 'WATSONX_URL' in merged_env_dict and merged_env_dict['WATSONX_URL']:
        WATSONX_URL = merged_env_dict['WATSONX_URL']

    watsonx_url = merged_env_dict.get("WATSONX_URL")
    if not watsonx_url:
        logger.error("Error: WATSONX_URL is required in the environment.")
        sys.exit(1)

    logger.info("Retrieving virtual-model models list...")
    virtual_models = models_client.list()



    logger.info("Retrieving virtual-policies models list...")
    virtual_model_policies = model_policies_client.list()

    logger.info("Retrieving watsonx.ai models list...")
    found_models = _get_wxai_foundational_models()


    preferred_str = merged_env_dict.get('PREFERRED_MODELS', '')
    incompatible_str = merged_env_dict.get('INCOMPATIBLE_MODELS', '') 

    preferred_list = _string_to_list(preferred_str)
    incompatible_list = _string_to_list(incompatible_str)

    models = found_models.get("resources", [])
    if not models:
        logger.error("No models found.")
    else:
        # Remove incompatible models
        filtered_models = []
        for model in models:
            model_id = model.get("model_id", "")
            short_desc = model.get("short_description", "")
            if any(incomp in model_id.lower() for incomp in incompatible_list):
                continue
            if any(incomp in short_desc.lower() for incomp in incompatible_list):
                continue
            filtered_models.append(model)
        
        # Sort to put the preferred first
        def sort_key(model):
            model_id = model.get("model_id", "").lower()
            is_preferred = any(pref in model_id for pref in preferred_list)
            return (0 if is_preferred else 1, model_id)
        
        sorted_models = sorted(filtered_models, key=sort_key)
        
        if print_raw:
            theme = rich.theme.Theme({"model.name": "bold cyan"})
            console = rich.console.Console(highlighter=ModelHighlighter(), theme=theme)
            console.print("[bold]Available Models:[/bold]")

            for model in virtual_models:
                console.print(f"- ✨️ {model.name}:", model.description or 'No description provided.')

            for model in virtual_model_policies:
                console.print(f"- ✨️ {model.name}:", 'No description provided.')

            for model in sorted_models:
                model_id = model.get("model_id", "N/A")
                short_desc = model.get("short_description", "No description provided.")
                full_model_name = f"watsonx/{model_id}: {short_desc}"
                marker = "★ " if any(pref in model_id.lower() for pref in preferred_list) else ""
                console.print(f"- [yellow]{marker}[/yellow]{full_model_name}")

            console.print("[yellow]★[/yellow] [italic dim]indicates a supported and preferred model[/italic dim]\n[blue dim]✨️[/blue dim] [italic dim]indicates a model from a custom provider[/italic dim]" )
        else:
            table = rich.table.Table(
                show_header=True,
                title="[bold]Available Models[/bold]",
                caption="[yellow]★ [/yellow] indicates a supported and preferred model from watsonx\n[blue]✨️[/blue] indicates a model from a custom provider",
                show_lines=True)
            columns = ["Model", "Description"]
            for col in columns:
                table.add_column(col)

            for model in virtual_models:
                table.add_row(f"✨️ {model.name}", model.description or 'No description provided.')

            for model in virtual_model_policies:
                table.add_row(f"✨️ {model.name}", 'No description provided.')

            for model in sorted_models:
                model_id = model.get("model_id", "N/A")
                short_desc = model.get("short_description", "No description provided.")
                marker = "★ " if any(pref in model_id.lower() for pref in preferred_list) else ""
                table.add_row(f"[yellow]{marker}[/yellow]watsonx/{model_id}", short_desc)
        
            rich.print(table)



@models_app.command(name="add", help="Add an llm from a custom provider")
def models_add(
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="The name of the model to add"),
    ],
    env_file: Annotated[
        str,
        typer.Option('--env-file', '-e', help='The path to an .env file containing the credentials for your llm provider'),
    ],
    description: Annotated[
        str,
        typer.Option('--description', '-d', help='The description of the model to add'),
    ] = None,
    display_name: Annotated[
        str,
        typer.Option('--display-name', help='What name should this llm appear as within the ui'),
    ] = None,
    type: Annotated[
        ModelType,
        typer.Option('--type', help='What type of model is it'),
    ] = ModelType.CHAT,

):
    from ibm_watsonx_orchestrate.cli.commands.models.env_file_model_provider_mapper import env_file_to_model_ProviderConfig # lazily import this because the lut building is expensive

    models_client: ModelsClient = instantiate_client(ModelsClient)
    provider_config = env_file_to_model_ProviderConfig(model_name=name, env_file_path=env_file)
    if not name.startswith('virtual-model/'):
        name = f"virtual-model/{name}"
    
    config=None
    # Anthropic has no default for max_tokens
    if "anthropic" in name:
        config = {
            "max_tokens": ANTHROPIC_DEFAULT_MAX_TOKENS
        }

    model = CreateVirtualModel(
        name=name,
        display_name=display_name or name,
        description=description,
        tags=[],
        provider_config=provider_config,
        config=config,
        model_type=type
    )

    models_client.create(model)
    logger.info(f"Successfully added the model '{name}'")



@models_app.command(name="remove", help="Remove an llm from a custom provider")
def models_remove(
        name: Annotated[
            str,
            typer.Option("--name", "-n", help="The name of the model to remove"),
        ]
):
    models_client: ModelsClient = instantiate_client(ModelsClient)
    models = models_client.list()
    model = next(filter(lambda x: x.name == name or x.name == f"virtual-model/{name}", models), None)
    if not model:
        logger.error(f"No model found with the name '{name}'")
        sys.exit(1)
    
    models_client.delete(model_id=model.id)
    logger.info(f"Successfully removed the model '{name}'")
        

# @models_policy_app.command(name='add', help='Add a model policy')
# def models_policy_add(
#         name: Annotated[
#             str,
#             typer.Option("--name", "-n", help="The name of the model to remove"),
#         ],
#         models: Annotated[
#             List[str],
#             typer.Option('--model', '-m', help='The name of the model to add'),
#         ],
#         strategy: Annotated[
#             ModelPolicyStrategyMode,
#             typer.Option('--strategy', '-s', help='How to spread traffic across models'),
#         ],
#         strategy_on_code: Annotated[
#             List[int],
#             typer.Option('--strategy-on-code', help='The http status to consider invoking the strategy'),
#         ],
#         retry_on_code: Annotated[
#             List[int],
#             typer.Option('--retry-on-code', help='The http status to consider retrying the llm call'),
#         ],
#         retry_attempts: Annotated[
#             int,
#             typer.Option('--retry-attempts', help='The number of attempts to retry'),
#         ],
#         display_name: Annotated[
#             str,
#             typer.Option('--display-name', help='What name should this llm appear as within the ui'),
#         ] = None
# ):
#     model_policies_client: ModelPoliciesClient = instantiate_client(ModelPoliciesClient)
#     model_client: ModelsClient = instantiate_client(ModelsClient)
#     model_lut = {m.name: m.id for m in model_client.list()}
#     for m in models:
#         if m not in model_lut:
#             logger.error(f"No model found with the name '{m}'")
#             exit(1)

#     inner = ModelPolicyInner()
#     inner.strategy = ModelPolicyStrategy(
#         mode=strategy,
#         on_status_codes=strategy_on_code
#     )
#     inner.targets = [ModelPolicyTarget(model_id=model_lut[m], weight=1) for m in models]
#     if retry_on_code:
#         inner.retry = ModelPolicyRetry(
#             on_status_codes=retry_on_code,
#             attempts=retry_attempts
#         )

#     if not display_name:
#         display_name = name


#     policy = ModelPolicy(
#         name=name,
#         display_name=display_name,
#         policy=inner
#     )
#     model_policies_client.create(policy)
#     logger.info(f"Successfully added the model policy '{name}'")



# @models_policy_app.command(name='remove', help='Remove a model policy')
# def models_policy_remove(
#         name: Annotated[
#             str,
#             typer.Option("--name", "-n", help="The name of the model policy to remove"),
#         ]
# ):
#     model_policies_client: ModelPoliciesClient = instantiate_client(ModelPoliciesClient)
#     model_policies = model_policies_client.list()

#     policy = next(filter(lambda x: x.name == name or x.name == f"virtual-policy/{name}", model_policies), None)
#     if not policy:
#         logger.error(f"No model found with the name '{name}'")
#         exit(1)

#     model_policies_client.delete(model_policy_id=policy.id)
#     logger.info(f"Successfully removed the model '{name}'")


def _get_wxai_foundational_models():
    foundation_models_url = WATSONX_URL + "/ml/v1/foundation_model_specs?version=2024-05-01"

    try:
        response = requests.get(foundation_models_url)
    except requests.exceptions.RequestException as e:
        logger.exception(f"Exception when connecting to Watsonx URL: {foundation_models_url}")
        raise

    if response.status_code != 200:
        error_message = (
            f"Failed to retrieve foundational models from {foundation_models_url}. "
            f"Status code: {response.status_code}. Response: {response.content}"
        )
        raise Exception(error_message)
    
    json_response = response.json()
    return json_response

def _string_to_list(env_value):
    return [item.strip().lower() for item in env_value.split(",") if item.strip()]

if __name__ == "__main__":
    models_app()