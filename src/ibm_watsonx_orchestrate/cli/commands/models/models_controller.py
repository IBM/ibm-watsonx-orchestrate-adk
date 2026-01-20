import logging
import os
import io
import zipfile
import sys
import json
import yaml
import importlib
import inspect
import time
from pathlib import Path
from typing import List, Optional

import requests
import rich
import rich.highlighter

from ibm_watsonx_orchestrate.cli.config import Config
from ibm_watsonx_orchestrate.client.model_policies.model_policies_client import ModelPoliciesClient
from ibm_watsonx_orchestrate.agent_builder.model_policies.types import ModelPolicy, ModelPolicyInner, \
    ModelPolicyRetry, ModelPolicyStrategy, ModelPolicyStrategyMode, ModelPolicyTarget
from ibm_watsonx_orchestrate.client.models.models_client import ModelsClient
from ibm_watsonx_orchestrate.agent_builder.models.types import VirtualModel, ProviderConfig, ModelType, ANTHROPIC_DEFAULT_MAX_TOKENS, ModelListEntry
from ibm_watsonx_orchestrate.client.utils import instantiate_client, is_local_dev, is_saas_env
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.client.connections import get_connection_id, ConnectionType
from ibm_watsonx_orchestrate.cli.commands.connections.connections_controller import export_connection, get_app_id_from_conn_id

from ibm_watsonx_orchestrate.utils.environment import EnvService
from ibm_watsonx_orchestrate.cli.common import ListFormats, rich_table_to_markdown
from ibm_watsonx_orchestrate.agent_builder.agents import SpecVersion

logger = logging.getLogger(__name__)

WATSONX_URL = os.getenv("WATSONX_URL")

class ModelHighlighter(rich.highlighter.RegexHighlighter):
    base_style = "model."
    highlights = [r"(?P<name>(watsonx|virtual[-]model|virtual[-]policy)\/.+\/.+):"]

def _get_wxai_foundational_models(max_retries=1) -> dict:
    foundation_models_url = WATSONX_URL + "/ml/v1/foundation_model_specs?version=2024-05-01"


    for attempt in range(max_retries + 1):
        try:
            response = requests.get(foundation_models_url)
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} failed. Retrying connecting to Watsonx URL {foundation_models_url}")
                time.sleep(1)
                continue
            logger.error(f"Exception when connecting to Watsonx URL: {foundation_models_url}")
            return { "resources": [] }

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
        with safe_open(file, 'r') as f:
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
        with safe_open(file, 'r') as f:
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
    
    def does_model_exist(self, model_name: str) -> bool:
        models = self.list_models(format=ListFormats.JSON)
        model_names = {model.name for model in models}
        return model_name in model_names

    def list_models(self, print_raw: bool = False, format: Optional[ListFormats] = None) -> List[ModelListEntry] | str |None:
        models_client: ModelsClient = self.get_models_client()
        model_policies_client: ModelPoliciesClient = self.get_model_policies_client()
        global WATSONX_URL
        default_env_path = EnvService.get_default_env_file()
        merged_env_dict = EnvService.merge_env(default_env_path, None)
        env_service = EnvService(Config())
        user_env = env_service.get_user_env(None)
        merged_env_dict.update(user_env)
        is_local = is_local_dev()
        is_saas = is_saas_env()
        LLM_HAS_WATSONX_APIKEY = merged_env_dict.get('LLM_HAS_WATSONX_APIKEY', False)
        LLM_HAS_WO_INSTANCE = merged_env_dict.get('LLM_HAS_WO_INSTANCE', False)
        LLM_HAS_GROQ_API_KEY = merged_env_dict.get('LLM_HAS_GROQ_API_KEY', False)


        if 'WATSONX_URL' in merged_env_dict and merged_env_dict.get('WATSONX_URL', None):
            WATSONX_URL = merged_env_dict['WATSONX_URL']

        watsonx_url = merged_env_dict.get("WATSONX_URL", None)
        if LLM_HAS_WATSONX_APIKEY and not watsonx_url:
            logger.error("Error: WATSONX_URL is required in the environment.")
            sys.exit(1)

    
        logger.info("Retrieving virtual-model models list...")
        virtual_models = models_client.list()

        logger.info("Retrieving virtual-policies models list...")
        virtual_model_policies = model_policies_client.list()

        if not is_local or (LLM_HAS_WATSONX_APIKEY or LLM_HAS_WO_INSTANCE) and watsonx_url is not None:
            logger.info("Retrieving watsonx.ai models list...")
            found_models = _get_wxai_foundational_models()
        else:
            found_models = {}


        preferred_str = merged_env_dict.get('PREFERRED_MODELS', '')
        incompatible_str = merged_env_dict.get('INCOMPATIBLE_MODELS', '') 

        preferred_list = _string_to_list(preferred_str)
        incompatible_list = _string_to_list(incompatible_str)

        wxai_models = found_models.get("resources", [])
        for model in wxai_models:
            if "model_id" in model:
                model["model_id"] = "watsonx/" + model["model_id"]
        # Remove incompatible models
        filtered_models = []
        groq_models = [
            {
                "model_id": "groq/openai/gpt-oss-120b",
                "short_description": "openai/gpt-oss-120b is an OpenAI’s open-weight models designed for powerful reasoning, agentic tasks, and versatile developer use cases."
             }
        ] if is_saas or (is_local and (LLM_HAS_GROQ_API_KEY or LLM_HAS_WO_INSTANCE)) else []

        for model in wxai_models + groq_models:
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
                full_model_name = f"{model_id}: {short_desc}"
                marker = "★ " if any(pref in model_id.lower() for pref in preferred_list) else ""
                console.print(f"- [yellow]{marker}[/yellow]{full_model_name}")

            console.print("[yellow]★[/yellow] [italic dim]indicates a supported and preferred model[/italic dim]\n[blue dim]✨️[/blue dim] [italic dim]indicates a model from a custom provider[/italic dim]" )
        else:
            model_details = []
            table = rich.table.Table(
                show_header=True,
                title="[bold]Available Models[/bold]",
                caption="[yellow]★ [/yellow] indicates a supported and preferred model from watsonx\n[blue]✨️[/blue] indicates a model from a custom provider",
                show_lines=True)
            columns = ["Model", "Description"]
            for col in columns:
                table.add_column(col)

            for model in (virtual_models + virtual_model_policies):
                entry = ModelListEntry(
                    name=model.name,
                    description=model.description,
                    is_custom=True
                )
                model_details.append(entry)
                table.add_row(*entry.get_row_details())

            for model in sorted_models:
                name = model.get("model_id", "N/A")
                entry = ModelListEntry(
                    name=name,
                    description=model.get("short_description"),
                    is_custom=False,
                    recommended=any(pref in name.lower() for pref in preferred_list)
                )
                model_details.append(entry)
                table.add_row(*entry.get_row_details())

            match format:
                case ListFormats.JSON:
                    return model_details
                case ListFormats.Table:
                    return rich_table_to_markdown(table)
                case _: 
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

    def export_model(self, name: str, output_path: str, zip_file_out: zipfile.ZipFile | None = None):
        output_file = Path(output_path)
        output_file_extension = output_file.suffix
        output_file_name = output_file.stem

        if output_file_extension != ".zip":
            logger.error(f"Output file must end with the extension '.zip'. Provided file '{output_path}' ends with '{output_file_extension}'")
            sys.exit(1)

        models_client  = self.get_models_client()
        virtual_models = models_client.get_draft_by_name(name)

        if len(virtual_models) > 1:
            logger.error(f"Multiple models with the name '{name}' found. Failed to export model")
            return
        if len(virtual_models) == 0:
            logger.error(f"No model found with the name '{name}'")
            return

        model = virtual_models[0]
        model_spec = model.model_dump(mode='json', exclude_none=True)

        connection_id = model_spec.get("connection_id")
        try:
            app_id = get_app_id_from_conn_id(connection_id) if connection_id else None
        except:
            app_id = None

        if app_id:
            model_spec["app_id"] = app_id

        model_spec.pop("id", None)
        model_spec.pop("connection_id", None)
        model_spec.pop("tenant_id", None)
        model_spec.pop("tenant_name", None)
        model_spec.pop("created_on", None)
        model_spec.pop("updated_at", None)
        model_spec["spec_version"] = SpecVersion.V1.value
        model_spec["kind"] = "model"

        close_file_flag = False
        if zip_file_out is None:
            close_file_flag = True
            zip_file_out = zipfile.ZipFile(output_path, "w")

        model_name = model_spec.get('name')
        logger.info(f"Exporting model for '{model_name}'")

        model_spec_yaml = yaml.dump(model_spec, sort_keys=False, default_flow_style=False, allow_unicode=True)

        model_spec_yaml_bytes = model_spec_yaml.encode("utf-8")
        model_spec_yaml_file = io.BytesIO(model_spec_yaml_bytes)

        model_file_name = model_name.rsplit('/', 1)[-1]
        model_file_path = f"{output_file_name}/models/{model_file_name}.yaml"

        zip_file_out.writestr(
            model_file_path,
            model_spec_yaml_file.getvalue()
        )

        if app_id:
            export_connection(output_file=f"{output_file_name}/connections", app_id=app_id, zip_file_out=zip_file_out)

        if close_file_flag:
            logger.info(f"Successfully exported model '{model_name}' to '{output_path}'")
            zip_file_out.close()

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

    def export_model_policy(self, name: str, output_path: str, zip_file_out: zipfile.ZipFile | None = None):
        output_file = Path(output_path)
        output_file_extension = output_file.suffix
        output_file_name = output_file.stem

        if output_file_extension != ".zip":
            logger.error(f"Output file must end with the extension '.zip'. Provided file '{output_path}' ends with '{output_file_extension}'")
            sys.exit(1)

        model_policies_client: ModelPoliciesClient = self.get_model_policies_client()
        model_policies = model_policies_client.get_draft_by_name(name)

        if len(model_policies) > 1:
            logger.error(f"Multiple models with the name '{name}' found. Failed to export model")
            return
        if len(model_policies) == 0:
            logger.error(f"No model found with the name '{name}'")
            return

        model_policy = model_policies[0]
        model_policy_spec = model_policy.model_dump(mode='json', exclude_none=True)

        model_policy_spec.pop("id", None)
        model_policy_spec["spec_version"] = SpecVersion.V1.value
        model_policy_spec["kind"] = "model"

        close_file_flag = False
        if zip_file_out is None:
            close_file_flag = True
            zip_file_out = zipfile.ZipFile(output_path, "w")

        model_policy_name = model_policy_spec.get('name')
        logger.info(f"Exporting model policy for '{model_policy_name}'")

        model_policy_spec_yaml = yaml.dump(model_policy_spec, sort_keys=False, default_flow_style=False, allow_unicode=True)
        model_policy_spec_yaml_bytes = model_policy_spec_yaml.encode("utf-8")
        model_policy_spec_yaml_file = io.BytesIO(model_policy_spec_yaml_bytes)

        model_policy_file_name = model_policy_name.rsplit('/', 1)[-1]
        model_policy_file_path = f"{output_file_name}/models/{model_policy_file_name}.yaml"

        zip_file_out.writestr(
            model_policy_file_path,
            model_policy_spec_yaml_file.getvalue()
        )

        # Export Models
        model_policy_dict = model_policy_spec.get('policy', {})
        for target in model_policy_dict.get('targets', []):
            model_name = target.get('model_name', None)
            if not model_name:
                continue

            self.export_model(name=model_name, output_path=output_path, zip_file_out=zip_file_out)

        if close_file_flag:
            logger.info(f"Successfully exported model policy '{model_policy_name}' to '{output_path}'")
            zip_file_out.close()

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