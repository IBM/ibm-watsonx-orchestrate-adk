# https://portkey.ai/
from dotenv import dotenv_values
import sys
import logging
from ibm_watsonx_orchestrate.agent_builder.models.types import  ProviderConfig, ModelProvider

logger = logging.getLogger(__name__)

_BASIC_PROVIDER_CONFIG_KEYS = {'provider', 'api_key', 'custom_host', 'url_to_fetch', 'forward_headers', 'request_timeout', 'transform_to_form_data'}

PROVIDER_EXTRA_PROPERTIES_LUT = {
    ModelProvider.ANTHROPIC: {'anthropic_beta', 'anthropic_version'},
    ModelProvider.AZURE_AI: {
        'azure_resource_name',
        'azure_deployment_id',
        'azure_api_version',
        'ad_auth',
        'azure_auth_mode',
        'azure_managed_client_id',
        'azure_entra_client_id',
        'azure_entra_client_secret',
        'azure_entra_tenant_id',
        'azure_ad_token',
        'azure_model_name',
        'azure_inference_deployment_name',
        'azure_inference_api_version',
        'azure_inference_extra_params',
        'azure_inference_foundry_url'
    },
    ModelProvider.AZURE_OPENAI: {
        'azure_resource_name',
        'azure_deployment_id',
        'azure_api_version',
        'azure_model_name'
    },
    ModelProvider.BEDROCK: {
        'aws_secret_access_key',
        'aws_access_key_id',
        'aws_session_token',
        'aws_region',
        'aws_auth_type',
        'aws_role_arn',
        'aws_external_id',
        'aws_s3_bucket',
        'aws_s3_object_key',
        'aws_bedrock_model',
        'aws_server_side_encryption',
        'aws_server_side_encryption_kms_key_id'
    },
    ModelProvider.VERTEX_AI: {
        'vertex_region',
        'vertex_project_id',
        'vertex_service_account_json',
        'vertex_storage_bucket_name',
        'vertex_model_name',
        'filename'
    },
    # ModelProvider.HUGGINGFACE: {'huggingfaceBaseUrl'},
    ModelProvider.MISTRAL_AI: {'mistral_fim_completion'},
    # ModelProvider.STABILITY_AI: {'stability_client_id', 'stability_client_user_id', 'stability_client_version'},
    ModelProvider.WATSONX: {'watsonx_version', 'watsonx_space_id', 'watsonx_project_id', 'api_key', 'watsonx_deployment_id', 'watsonx_cpd_url', 'watsonx_cpd_username', 'watsonx_cpd_password'},

    # 'palm': _bpp('PALM', {}),
    # 'nomic': _bpp('NOMIC', {}),
    # 'perplexity-ai': _bpp('PERPLEXITY_AI', {}),
    # 'segmind': _bpp('SEGMIND', {}),
    # 'deepinfra': _bpp('DEEPINFRA', {}),
    # 'novita-ai': _bpp('NOVITA_AI', {}),
    # 'fireworks-ai': _bpp('FIREWORKS',{
    #     'FIREWORKS_ACCOUNT_ID': 'fireworks_account_id'
    # }),
    # 'deepseek': _bpp('DEEPSEEK', {}),
    # 'voyage': _bpp('VOYAGE', {}),
    # 'moonshot': _bpp('MOONSHOT', {}),
    # 'lingyi': _bpp('LINGYI', {}),
    # 'zhipu': _bpp('ZHIPU', {}),
    # 'monsterapi': _bpp('MONSTERAPI', {}),
    # 'predibase': _bpp('PREDIBASE', {}),

    # 'github': _bpp('GITHUB', {}),
    # 'deepbricks': _bpp('DEEPBRICKS', {}),
    # 'sagemaker': _bpp('AMZN_SAGEMAKER', {
    #     'AMZN_SAGEMAKER_CUSTOM_ATTRIBUTES': 'amzn_sagemaker_custom_attributes',
    #     'AMZN_SAGEMAKER_TARGET_MODEL': 'amzn_sagemaker_target_model',
    #     'AMZN_SAGEMAKER_TARGET_VARIANT': 'amzn_sagemaker_target_variant',
    #     'AMZN_SAGEMAKER_TARGET_CONTAINER_HOSTNAME': 'amzn_sagemaker_target_container_hostname',
    #     'AMZN_SAGEMAKER_INFERENCE_ID': 'amzn_sagemaker_inference_id',
    #     'AMZN_SAGEMAKER_ENABLE_EXPLANATIONS': 'amzn_sagemaker_enable_explanations',
    #     'AMZN_SAGEMAKER_INFERENCE_COMPONENT': 'amzn_sagemaker_inference_component',
    #     'AMZN_SAGEMAKER_SESSION_ID': 'amzn_sagemaker_session_id',
    #     'AMZN_SAGEMAKER_MODEL_NAME': 'amzn_sagemaker_model_name'
    # }),
    # '@cf': _bpp('WORKERS_AI', { # workers ai
    #     'WORKERS_AI_ACCOUNT_ID': 'workers_ai_account_id'
    # }),
    # 'snowflake': _bpp('SNOWFLAKE', { # no provider prefix found
    #     'SNOWFLAKE_ACCOUNT': 'snowflake_account'
    # })
}

PROVIDER_REQUIRED_FIELDS = {k:['api_key'] for k in ModelProvider}
# Update required fields for each provider
# Use sets to denote when a requirement is 'or'
# Tuples denote combined requirements like 'and'
PROVIDER_REQUIRED_FIELDS.update({
    ModelProvider.WATSONX: PROVIDER_REQUIRED_FIELDS[ModelProvider.WATSONX] + [{'watsonx_space_id', 'watsonx_project_id', 'watsonx_deployment_id'}],
    ModelProvider.OLLAMA: PROVIDER_REQUIRED_FIELDS[ModelProvider.OLLAMA] + ['custom_host'],
    ModelProvider.BEDROCK: [{'api_key', ('aws_secret_access_key', 'aws_access_key_id')}],
})

# def env_file_to_model_ProviderConfig(model_name: str, env_file_path: str) -> ProviderConfig | None:
#     provider = next(filter(lambda x: x not in ('virtual-policy', 'virtual-model'), model_name.split('/')))
#     if provider not in ModelProvider:
#         logger.error(f"Unsupported model provider {provider}")
#         sys.exit(1)

#     values = dotenv_values(str(env_file_path))

#     if values is None:
#         logger.error(f"No provider configuration in env file {env_file_path}")
#         sys.exit(1)

#     cfg = ProviderConfig()
#     cfg.provider = PROVIDER_LUT[provider]

#     cred_lut = PROVIDER_PROPERTIES_LUT[provider]


#     consumed_credentials = []
#     # Ollama requires some apikey but its content don't matter
#     # Default it to 'ollama' to avoid users needing to specify
#     if cfg.provider == ModelProvider.OLLAMA:
#         consumed_credentials.append('api_key')
#         setattr(cfg, 'api_key', ModelProvider.OLLAMA)
    
#     for key, value in values.items():
#         if key in cred_lut:
#             k = cred_lut[key]
#             consumed_credentials.append(k)
#             setattr(cfg, k, value)

#     return cfg

def _validate_provider(provider: str | ModelProvider) -> None:
    if not ModelProvider.has_value(provider):
        logger.error(f"Unsupported model provider {provider}")
        sys.exit(1)

def _validate_extra_fields(provider: ModelProvider, cfg: ProviderConfig) -> None:
    accepted_fields = _BASIC_PROVIDER_CONFIG_KEYS.copy()
    extra_accepted_fields = PROVIDER_EXTRA_PROPERTIES_LUT.get(provider)
    if extra_accepted_fields:
        accepted_fields = accepted_fields.union(extra_accepted_fields)
    
    for attr in cfg.__dict__:
        if attr.startswith("__"):
            continue

        if  cfg.__dict__.get(attr) is not None and attr not in accepted_fields:
            logger.warning(f"The config option '{attr}' is not used by provider '{provider}'")

def _check_credential_provided(cred: str | tuple, provided_creds: set) -> bool:
    if isinstance(cred, tuple):
        return all(item in provided_creds for item in cred)
    else:
        return cred in provided_creds

def _format_missing_credential(missing_credential: set) -> str:
    parts = []
    for cred in missing_credential:
        if isinstance(cred, tuple):
            formatted = " and ".join(f"{x}" for x in cred)
            parts.append(f"({formatted})")
        else:
            parts.append(f"{cred}")

    return " or ".join(parts)


def _validate_requirements(provider: ModelProvider, cfg: ProviderConfig, app_id: str = None) -> None:
    provided_credentials = set([k for k,v in dict(cfg).items() if v is not None])
    required_creds = PROVIDER_REQUIRED_FIELDS[provider]
    missing_credentials = []
    for cred in required_creds:
        if isinstance(cred, set):
            if not any(_check_credential_provided(c, provided_credentials) for c in cred):
                missing_credentials.append(cred)
        else:
            if not _check_credential_provided(cred, provided_credentials):
                missing_credentials.append(cred)

    if len(missing_credentials) > 0:
        if not app_id:
            missing_credentials_string = f"Missing configuration variable(s) required for the provider {provider}:"
        else:
            missing_credentials_string = f"Be sure to include the following required fields for provider '{provider}' in the connection '{app_id}':"
        for cred in missing_credentials:
            if isinstance(cred, set):
                cred_str = _format_missing_credential(cred)
            else:
                cred_str = cred
            missing_credentials_string += f"\n\t  - {cred_str}"
        
        if not app_id:
            logger.error(missing_credentials_string)
            logger.error("Please provide the above values in the provider config. For secret values (e.g. 'api_key') create a key_value connection `orchestrate connections add` then bind it to the model with `--app-id`")
            sys.exit(1)
        else:
            logger.info(missing_credentials_string)


def validate_ProviderConfig(cfg: ProviderConfig, app_id: str)-> None:
    if not cfg:
        return

    provider = cfg.provider

    _validate_provider(provider)
    _validate_extra_fields(provider=provider, cfg=cfg)
    _validate_requirements(provider=provider, cfg=cfg, app_id=app_id)