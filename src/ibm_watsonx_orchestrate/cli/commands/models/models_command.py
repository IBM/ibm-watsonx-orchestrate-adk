import logging
import os
import requests
import sys
import rich.highlighter
import typer
import rich
import typer
from typing_extensions import Annotated
from ibm_watsonx_orchestrate.cli.commands.server.server_command import get_default_env_file, merge_env

logger = logging.getLogger(__name__)
models_app = typer.Typer(no_args_is_help=True)

WATSONX_URL = os.getenv("WATSONX_URL")

class ModelHighlighter(rich.highlighter.RegexHighlighter):
    base_style = "model."
    highlights = [r"(?P<name>watsonx\/.+\/.+):"]

@models_app.command(name="list")
def model_list(
    print_raw: Annotated[
        bool,
        typer.Option("--raw", "-r", help="Display the list of models in a non-tabular format"),
    ] = False,
):
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
        
        # Sort to put preferred first
        def sort_key(model):
            model_id = model.get("model_id", "").lower()
            is_preferred = any(pref in model_id for pref in preferred_list)
            return (0 if is_preferred else 1, model_id)
        
        sorted_models = sorted(filtered_models, key=sort_key)
        
        if print_raw:
            theme = rich.theme.Theme({"model.name": "bold cyan"})
            console = rich.console.Console(highlighter=ModelHighlighter(), theme=theme)
            console.print("[bold]Available Models:[/bold]")
            for model in sorted_models:
                model_id = model.get("model_id", "N/A")
                short_desc = model.get("short_description", "No description provided.")
                full_model_name = f"watsonx/{model_id}: {short_desc}"
                marker = "★ " if any(pref in model_id.lower() for pref in preferred_list) else ""
                console.print(f"- [yellow]{marker}[/yellow]{full_model_name}")

            console.print("[yellow]★[/yellow] [italic dim]indicates a supported and preferred model[/italic dim]" )
        else:
            table = rich.table.Table(
                show_header=True,
                title="[bold]Available Models[/bold]",
                caption="[yellow]★[/yellow] indicates a supported and preferred model",
                show_lines=True)
            columns = ["Model", "Description"]
            for col in columns:
                table.add_column(col)

            for model in sorted_models:
                model_id = model.get("model_id", "N/A")
                short_desc = model.get("short_description", "No description provided.")
                marker = "★ " if any(pref in model_id.lower() for pref in preferred_list) else ""
                table.add_row(f"[yellow]{marker}[/yellow]watsonx/{model_id}", short_desc)
        
            rich.print(table)

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