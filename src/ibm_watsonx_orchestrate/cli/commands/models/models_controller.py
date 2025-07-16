import logging
import os
import sys
import json
import yaml
import importlib
import inspect
from pathlib import Path
from typing import List

import requests
import rich
import rich.highlighter

from ibm_watsonx_orchestrate.cli.commands.server.server_command import get_default_env_file, merge_env
from ibm_watsonx_orchestrate.client.model_policies.model_policies_client import ModelPoliciesClient
from ibm_watsonx_orchestrate.agent_builder.model_policies.types import ModelPolicy, ModelPolicyInner, \
    ModelPolicyRetry, ModelPolicyStrategy, ModelPolicyStrategyMode, ModelPolicyTarget
from ibm_watsonx_orchestrate.client.models.models_client import ModelsClient
from ibm_watsonx_orchestrate.agent_builder.models.types import VirtualModel, ProviderConfig, ModelType, ANTHROPIC_DEFAULT_MAX_TOKENS
from ibm_watsonx_orchestrate.client.utils import instantiate_client, is_cpd_env
from ibm_watsonx_orchestrate.client.connections import get_connection_id, ConnectionType

logger = logging.getLogger(__name__)

WATSONX_URL = os.getenv("WATSONX_URL")

class ModelHighlighter(rich.highlighter.RegexHighlighter):
    base_style = "model."
    highlights = [r"(?P<name>(watsonx|virtual[-]model|virtual[-]policy)\/.+\/.+):"]

def _get_wxai_foundational_models() -> dict:
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

def _string_to_list(env_value) -> List[str]:
    return [item.strip().lower() for item in env_value.split(",") if item.strip()]

def create_model_from_spec(spec: dict) -> VirtualModel:
    return VirtualModel.model_validate(spec)

def create_policy_from_spec(spec: dict) -> ModelPolicy:
    return ModelPolicy.model_validate(spec)

def import_python_model(file: str) -> List[VirtualModel]:
    file_path = Path(file)
    file_directory = file_path.parent
    file_name = file_path.stem
    sys.path.append(str(file_directory))
    module = importlib.import_module(file_name)
    del sys.path[-1]

    models = []
    for _, obj in inspect.getmembers(module):
        if isinstance(obj, VirtualModel):
            models.append(obj)
    return models

def import_python_policy(file: str) -> List[ModelPolicy]:
    file_path = Path(file)
    file_directory = file_path.parent
    file_name = file_path.stem
    sys.path.append(str(file_directory))
    module = importlib.import_module(file_name)
    del sys.path[-1]

    models = []
    for _, obj in inspect.getmembers(module):
        if isinstance(obj, ModelPolicy):
            models.append(obj)
    return models

def validate_spec_content(content: dict) -> None:
    if not content.get("spec_version"):
        logger.error(f"Field 'spec_version' not provided. Please ensure provided spec conforms to a valid spec format")
        sys.exit(1)

def parse_model_file(file: str) -> List[VirtualModel]:
    if file.endswith('.yaml') or file.endswith('.yml') or file.endswith(".json"):
        with open(file, 'r') as f:
            if file.endswith(".json"):
                content = json.load(f)
            else:
                content = yaml.load(f, Loader=yaml.SafeLoader)
        validate_spec_content(content)
        model = create_model_from_spec(spec=content)
        return [model]
    elif file.endswith('.py'):
        models = import_python_model(file)
        return models
    else:
        raise ValueError("file must end in .json, .yaml, .yml or .py")

def parse_policy_file(file: str) -> List[ModelPolicy]:
    if file.endswith('.yaml') or file.endswith('.yml') or file.endswith(".json"):
        with open(file, 'r') as f:
            if file.endswith(".json"):
                content = json.load(f)
            else:
                content = yaml.load(f, Loader=yaml.SafeLoader)
        validate_spec_content(content)
        policy = create_policy_from_spec(spec=content)
        return [policy]
    elif file.endswith('.py'):
        policies = import_python_policy(file)
        return policies
    else:
        raise ValueError("file must end in .json, .yaml, .yml or .py")

def extract_model_names_from_policy_inner(policy_inner: ModelPolicyInner) -> List[str]:
    model_names = []
    for target in policy_inner.targets:
        if isinstance(target, ModelPolicyTarget):
            model_names.append(target.model_name)
        elif isinstance(target, ModelPolicyInner):
            model_names += extract_model_names_from_policy_inner(target)
    return model_names

def get_model_names_from_policy(policy: ModelPolicy) -> List[str]:
    return extract_model_names_from_policy_inner(policy_inner=policy.policy)

class ModelsController:
    def __init__(self):
        self.models_client = None
        self.model_policies_client = None

    def get_models_client(self) -> ModelsClient:
        if not self.models_client:
            self.models_client = instantiate_client(ModelsClient)
        return self.models_client

    def get_model_policies_client(self) -> ModelPoliciesClient:
        if not self.model_policies_client:
            self.model_policies_client = instantiate_client(ModelPoliciesClient)
        return self.model_policies_client

    def list_models(self, print_raw: bool = False) -> None:
        models_client: ModelsClient = self.get_models_client()
        model_policies_client: ModelPoliciesClient = self.get_model_policies_client()
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

                for model in (virtual_models + virtual_model_policies):
                    console.print(f"- ✨️ {model.name}:", model.description or 'No description provided.')

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

                for model in (virtual_models + virtual_model_policies):
                    table.add_row(f"✨️ {model.name}", model.description or 'No description provided.')

                for model in sorted_models:
                    model_id = model.get("model_id", "N/A")
                    short_desc = model.get("short_description", "No description provided.")
                    marker = "★ " if any(pref in model_id.lower() for pref in preferred_list) else ""
                    table.add_row(f"[yellow]{marker}[/yellow]watsonx/{model_id}", short_desc)
            
                rich.print(table)

    def import_model(self, file: str, app_id: str | None) -> List[VirtualModel]:
        from ibm_watsonx_orchestrate.cli.commands.models.model_provider_mapper import validate_ProviderConfig # lazily import this because the lut building is expensive
        models = parse_model_file(file)

        for model in models:
            if not model.name.startswith('virtual-model/'):
                model.name = f"virtual-model/{model.name}"
            
            provider = next(filter(lambda x: x not in ('virtual-policy', 'virtual-model'), model.name.split('/')))
            if not model.provider_config:   
                model.provider_config = ProviderConfig.model_validate({"provider": provider})
            else:
                model.provider_config.provider = provider

            if "anthropic" in model.name:
                if not model.config:
                    model.config = {}
                if "max_tokens" not in model.config:
                    model.config["max_tokens"] = ANTHROPIC_DEFAULT_MAX_TOKENS

            if app_id:
                model.connection_id = get_connection_id(app_id, supported_schemas={ConnectionType.KEY_VALUE})
            validate_ProviderConfig(model.provider_config, app_id=app_id)
        return models

    def create_model(self, name: str, display_name: str | None = None, description: str | None = None, provider_config_dict: dict = None, model_type: ModelType = ModelType.CHAT, app_id: str = None) -> VirtualModel:
        from ibm_watsonx_orchestrate.cli.commands.models.model_provider_mapper import validate_ProviderConfig # lazily import this because the lut building is expensive
        
        provider =next(filter(lambda x: x not in ('virtual-policy', 'virtual-model'), name.split('/')))

        provider_config = {}
        if provider_config_dict:
            provider_config = ProviderConfig.model_validate(provider_config_dict)
            provider_config.provider = provider
        else:
            provider_config = ProviderConfig.model_validate({"provider": provider})
        validate_ProviderConfig(provider_config, app_id=app_id)

        if not name.startswith('virtual-model/'):
            name = f"virtual-model/{name}"
        
        config=None
        # Anthropic has no default for max_tokens
        if "anthropic" in name:
            config = {
                "max_tokens": ANTHROPIC_DEFAULT_MAX_TOKENS
            }

        model = VirtualModel(
            name=name,
            display_name=display_name,
            description=description,
            tags=[],
            provider_config=provider_config,
            config=config,
            model_type=model_type,
            connection_id=get_connection_id(app_id, supported_schemas={ConnectionType.KEY_VALUE})
        )

        return model

    def publish_or_update_models(self, model: VirtualModel) -> None:
        models_client = self.get_models_client()

        existing_models = models_client.get_draft_by_name(model.name)
        if len(existing_models) > 1:
            logger.error(f"Multiple models with the name '{model.name}' found. Failed to update model")
            sys.exit(1)

        if len(existing_models) == 1:
            self.update_model(model_id=existing_models[0].id, model=model)
        else:
            self.publish_model(model=model)
    
    def publish_model(self, model: VirtualModel) -> None:
        self.get_models_client().create(model)
        logger.info(f"Successfully added the model '{model.name}'")

    def update_model(self, model_id: str, model: VirtualModel) -> None:
        logger.info(f"Existing model '{model.name}' found. Updating...")
        self.get_models_client().update(model_id, model)
        logger.info(f"Model '{model.name}' updated successfully")
    
    def remove_model(self, name: str) -> None:
        models_client: ModelsClient = self.get_models_client()
       
        existing_models = models_client.get_draft_by_name(name)

        if len(existing_models) > 1:
            logger.error(f"Multiple models with the name '{name}' found. Failed to remove model")
            sys.exit(1)
        if len(existing_models) == 0:
            logger.error(f"No model found with the name '{name}'")
            sys.exit(1)
        
        model = existing_models[0]

        models_client.delete(model_id=model.id)
        logger.info(f"Successfully removed the model '{name}'")

    def import_model_policy(self, file: str) -> List[ModelPolicy]:
        policies = parse_policy_file(file)
        model_client: ModelsClient = self.get_models_client()
        model_lut = {m.name: m.id for m in model_client.list()}

        for policy in policies:
            models =  get_model_names_from_policy(policy)
            for m in models:
                if m not in model_lut:
                    logger.error(f"No model found with the name '{m}'")
                    sys.exit(1)
        
            if not policy.name.startswith('virtual-policy/'):
                policy.name = f"virtual-policy/{policy.name}"

        return policies

    def create_model_policy(
        self,
        name: str,
        models: List[str],
        strategy: ModelPolicyStrategyMode, 
        strategy_on_code: List[int],
        retry_on_code: List[int],
        retry_attempts: int,
        display_name: str = None,
        description: str = None
    ) -> ModelPolicy:
        
        model_client: ModelsClient = self.get_models_client()
        model_lut = {m.name: m.id for m in model_client.list()}
        for m in models:
            if m not in model_lut:
                logger.error(f"No model found with the name '{m}'")
                sys.exit(1)
        
        if not name.startswith('virtual-policy/'):
            name = f"virtual-policy/{name}"

        inner = ModelPolicyInner()
        inner.strategy = ModelPolicyStrategy(
            mode=strategy,
            on_status_codes=strategy_on_code
        )
        inner.targets = [ModelPolicyTarget(model_name=m) for m in models]
        if retry_on_code:
            inner.retry = ModelPolicyRetry(
                on_status_codes=retry_on_code,
                attempts=retry_attempts
            )

        policy = ModelPolicy(
            name=name,
            display_name=display_name or name,
            description=description or name,
            policy=inner
        )

        return policy

    def publish_or_update_model_policies(self, policy: ModelPolicy) -> None:
        model_policies_client: ModelPoliciesClient = self.get_model_policies_client()

        existing_policies = model_policies_client.get_draft_by_name(policy.name)
        if len(existing_policies) > 1:
            logger.error(f"Multiple model policies with the name '{policy.name}' found. Failed to update model policy")
            sys.exit(1)

        if len(existing_policies) == 1:
            self.update_policy(policy_id=existing_policies[0].id, policy=policy)
        else:
            self.publish_policy(policy=policy)
    
    def publish_policy(self, policy: VirtualModel) -> None:
        self.get_model_policies_client().create(policy)
        logger.info(f"Successfully added the model policy '{policy.name}'")

    def update_policy(self, policy_id: str, policy: VirtualModel) -> None:
        logger.info(f"Existing model policy '{policy.name}' found. Updating...")
        self.get_model_policies_client().update(policy_id, policy)
        logger.info(f"Model policy '{policy.name}' updated successfully")
    
    def remove_policy(self, name: str) -> None:
        model_policies_client: ModelPoliciesClient = self.get_model_policies_client()
        existing_model_policies = model_policies_client.get_draft_by_name(name)

        if len(existing_model_policies) > 1:
            logger.error(f"Multiple model policies with the name '{name}' found. Failed to remove model policy")
            sys.exit(1)
        if len(existing_model_policies) == 0:
            logger.error(f"No model policy found with the name '{name}'")
            sys.exit(1)

        policy = existing_model_policies[0]

        model_policies_client.delete(model_policy_id=policy.id)
        logger.info(f"Successfully removed the policy '{name}'")