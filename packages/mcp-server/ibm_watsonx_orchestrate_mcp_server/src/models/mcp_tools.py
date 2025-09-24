from typing import Any, List, Literal, Optional
from ibm_watsonx_orchestrate.agent_builder.model_policies.types import ModelPolicy
from ibm_watsonx_orchestrate.cli.common import ListFormats
from ibm_watsonx_orchestrate_mcp_server.src.connections.helpers import ConnectionsHelper
from ibm_watsonx_orchestrate_mcp_server.utils.common import silent_call
from ibm_watsonx_orchestrate_mcp_server.utils.files.files import get_working_directory_path
from ibm_watsonx_orchestrate.agent_builder.models.types import ModelListEntry, VirtualModel, ListVirtualModel, ModelType
from ibm_watsonx_orchestrate.cli.commands.models.models_controller import ModelsController
from ibm_watsonx_orchestrate_mcp_server.src.models.types import CreateModelOptions, CreateModelPolicyOptions

def __format_model_name(model_name: str) -> str:
    return f"virtual-model/{model_name}" if not model_name.startswith("virtual-model/") else model_name

def __format_model_policy_name(policy_name: str) -> str:
    return f"virtual-policy/{policy_name}" if not policy_name.startswith("virtual-policy/") else policy_name

def list_models() -> List[ModelListEntry]:
    """
    List all models and model policies in the watsonx Orchestrate platform.
    Custom models will being with the prefix "virtual-model/".
    Model policies will being with the prefix "virtual-policy/"

    Returns:
        List[ModelListEntry]: A list of models configurations.
    """
    mc: ModelsController = ModelsController()
    models = silent_call(fn=mc.list_models, format=ListFormats.JSON)
    return models

def import_model(file_path: str, app_id: Optional[str]=None) -> List[VirtualModel]:
    """
    Import a model in the watsonx Orchestrate platform
    Args:
        file_path (str): Path to the model file.
        app_id (str, optional): The app_id of a key_value connection containing secrets for model authentication such as api_key. These values are merged with the provider_config field in the spec and provide a secure way of passing secret data to the model config. Defaults to None.
    Returns:
        List[VirtualModel]: The response from the watsonx Orchestrate platform.
    """
    working_directory_path = get_working_directory_path(file_path)
    mc: ModelsController = ModelsController()
    models = silent_call(
        fn=mc.import_model,
        file=working_directory_path,
        app_id=app_id
    )
    for model in models:
        silent_call(
            fn=mc.publish_or_update_models,
            model=model,
        )
    return models

def create_or_update_model(options: CreateModelOptions) -> VirtualModel:
    """
    Create a model in the watsonx Orchestrate platform. If a model with the same name already exists update it instead.
    Args:
        options (CreateModelOptions): The options for creating the model.
    Returns:
        VirtualModel: The created model.
    """
    mc: ModelsController = ModelsController()
    models_client = silent_call(fn=mc.get_models_client)
    existing_name: str = __format_model_name(options.name)
    existing_models = silent_call(fn=models_client.get_draft_by_name, model_name=existing_name)
    provider_config_dict: dict[str, Any] | None = options.provider_config.model_dump() if options.provider_config else None

    existing_model_data: ListVirtualModel | None = None
    if len(existing_models) == 1:
        existing_model_data = existing_models[0]
    elif len(existing_models) > 1:
        raise Exception(f"Multiple models found with name {options.name}. Update is ambiguous. Please delete the duplicate and try again.")

    if not existing_model_data:
        model = silent_call(
            fn=mc.create_model,
            name=options.name,
            description=options.description,
            display_name=options.display_name,
            provider_config_dict=provider_config_dict,
            model_type=options.type,
            app_id=options.app_id
        )
    else:
        connections_helper: ConnectionsHelper = ConnectionsHelper()
        existing_app_id: str | None = None
        if existing_model_data.connection_id:
            existing_app_id = connections_helper.get_app_id_by_connection_id(existing_model_data.connection_id)
        existing_model_provider_config: dict[str, Any] | None = existing_model_data.provider_config.model_dump() if existing_model_data.provider_config else None
        existing_model_type: str | Literal[ModelType.CHAT] = existing_model_data.model_type if existing_model_data.model_type else ModelType.CHAT
        existing_model = silent_call(
            fn=mc.create_model,
            name=existing_model_data.name,
            description=existing_model_data.description,
            display_name=existing_model_data.display_name,
            provider_config_dict=existing_model_provider_config,
            model_type=existing_model_type,
            app_id=existing_app_id
        )

        options.name = existing_name
        
        model = existing_model.model_copy(update=options.model_dump(exclude_unset=True))


    silent_call(
        fn=mc.publish_or_update_models,
        model=model,
    )
    return model

def remove_model(name: str) -> str:
    """
    Remove a model from the watsonx Orchestrate platform.

    Args:
        name (str): The name of the model to remove.

    Returns:
        str: A message indicating the success of the removal operation.
    """
    model_name: str = __format_model_name(model_name=name)
    mc: ModelsController = ModelsController()
    silent_call(fn=mc.remove_model, name=model_name)
    return f"Successfully removed model '{model_name}'."

def import_model_policy(file_path: str) -> List[ModelPolicy]:
    """
    Import a model policy from a file into the watsonx Orchestrate platform.

    Args:
        file_path (str): The path to the file containing the model policy.

    Returns:
        List[ModelPolicy]: A list of ModelPolicy objects representing the imported model policy.
    """
    working_directory_path = get_working_directory_path(file_path)
    mc: ModelsController = ModelsController()
    policies = silent_call(
        fn=mc.import_model_policy,
        file=working_directory_path
    )
    for policy in policies:
        silent_call(
            fn=mc.publish_or_update_model_policies,
            policy=policy,
        )
    return policies

def create_or_update_model_policy(options: CreateModelPolicyOptions) -> ModelPolicy:
    """
    Create or update a model policy in the watsonx Orchestrate platform. If a model policy with the name is found it will update else it will create a new one.
    
    Args:
        options (CreateModelPolicyOptions): The options for creating or updating the model policy.

    Returns:
        ModelPolicy: The created or updated model policy.
    """
    mc: ModelsController = ModelsController()
    model_policies_client = silent_call(fn=mc.get_model_policies_client)
    existing_name: str = __format_model_policy_name(options.name)
    existing_policies = silent_call(fn=model_policies_client.get_draft_by_name, policy_name=existing_name)

    existing_policy: ModelPolicy | None = None
    if len(existing_policies) == 1:
        existing_policy = existing_policies[0]
    elif len(existing_policies) > 1:
        raise Exception(f"Multiple model policies found with name {options.name}. Update is ambiguous. Please delete the duplicate and try again.")

    if not existing_policy:
        model = silent_call(
            fn=mc.create_model_policy,
            name=options.name,
            description=options.description,
            display_name=options.display_name,
            models=options.models,
            strategy=options.strategy,
            strategy_on_code=options.strategy_on_code,
            retry_on_code=options.retry_on_code,
            retry_attempts=options.retry_attempts
        )
    else:
        model: ModelPolicy = existing_policy.model_copy(update=options.model_dump(exclude_unset=True))


    silent_call(
        fn=mc.publish_or_update_models,
        model=model,
    )
    return model

def remove_model_policy(name: str) -> str:
    """
    Remove a model policy from the watsonx Orchestrate platform

    Args:
        name (str): The name of the model policy to remove.

    Returns:
        str: A message indicating the success of the removal operation.
    """
    policy_name: str = __format_model_policy_name(policy_name=name)
    mc: ModelsController = ModelsController()
    silent_call(fn=mc.remove_policy, name=policy_name)
    return f"Successfully removed model policy '{policy_name}'."

__tools__ = [list_models, import_model, create_or_update_model, remove_model, import_model_policy, create_or_update_model_policy, remove_model_policy]
