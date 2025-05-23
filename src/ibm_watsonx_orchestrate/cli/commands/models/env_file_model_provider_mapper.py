# https://portkey.ai/
from dotenv import dotenv_values

from ibm_watsonx_orchestrate.client.models.types import ProviderConfig, ModelProvider

def _bpp(name: str, provider_config=None) -> dict:
    if provider_config is None:
        provider_config = {}

    name = name.upper()

    provider_config.update({
        f"{name}_API_KEY": 'api_key',
        f"{name}_CUSTOM_HOST": 'custom_host',
        f"{name}_URL_TO_FETCH": 'url_to_fetch',
        f"{name}_FORWARD_HEADERS": lambda value, config: setattr(config, 'forward_headers', list(map(lambda v: v.strip(), value.split(';')))),
        f"{name}_REQUEST_TIMEOUT": lambda value, config: setattr(config, 'request_timeout', int(value)),
        f"{name}_TRANSFORM_TO_FORM_DATA": 'transform_to_form_data'
    })

    return provider_config

# model provider prefix => ENV_VAR key => provider config key
PROVIDER_PROPERTIES_LUT = {
    ModelProvider.OPENAI: _bpp('OPENAI', {}),
    # ModelProvider.A21: _bpp('A21', {}),
    ModelProvider.ANTHROPIC: _bpp('ANTHROPIC', {
        'ANTHROPIC_BETA': 'anthropic_beta',
        'ANTHROPIC_VERSION': 'anthropic_version'
    }),
    # ModelProvider.ANYSCALE: _bpp('ANYSCALE', {}),
    # ModelProvider.AZURE_OPENAI: _bpp('AZURE_OPENAI', {}),
    # ModelProvider.AZURE_AI: _bpp('AZURE', {
    #     'AZURE_AI_RESOURCE_NAME': 'azure_resource_name',
    #     'AZURE_AI_DEPLOYMENT_ID': 'azure_deployment_id',
    #     'AZURE_AI_API_VERSION': 'azure_api_version',
    #     'AZURE_AI_AD_AUTH': 'ad_auth',
    #     'AZURE_AI_AUTH_MODE': 'azure_auth_mode',
    #     'AZURE_AI_MANAGED_CLIENT_ID': 'azure_managed_client_id',
    #     'AZURE_AI_ENTRA_CLIENT_ID': 'azure_entra_client_id',
    #     'AZURE_AI_ENTRA_CLIENT_SECRET': 'azure_entra_client_secret',
    #     'AZURE_AI_ENTRA_TENANT_ID': 'azure_entra_tenant_id',
    #     'AZURE_AI_AD_TOKEN': 'azure_ad_token',
    #     'AZURE_AI_MODEL_NAME': 'azure_model_name',
    # }),
    # ModelProvider.BEDROCK: _bpp('BEDROCK', {
    #     'AWS_SECRET_ACCESS_KEY': 'aws_secret_access_key',
    #     'AWS_ACCESS_KEY_ID': 'aws_access_key_id',
    #     'AWS_SESSION_TOKEN': 'aws_session_token',
    #     'AWS_REGION': 'aws_region',
    #     'AWS_AUTH_TYPE': 'aws_auth_type',
    #     'AWS_ROLE_ARN': 'aws_role_arn',
    #     'AWS_EXTERNAL_ID': 'aws_external_id',
    #     'AWS_S3_BUCKET': 'aws_s3_bucket',
    #     'AWS_S3_OBJECT_KEY': 'aws_s3_object_key',
    #     'AWS_BEDROCK_MODEL': 'aws_bedrock_model',
    #     'AWS_SERVER_SIDE_ENCRYPTION': 'aws_server_side_encryption',
    #     'AWS_SERVER_SIDE_ENCRYPTION_KMS_KEY_ID': 'aws_server_side_encryption_kms_key_id',
    # }),
    # ModelProvider.CEREBRAS: _bpp('COHERE', {}),
    # ModelProvider.COHERE: _bpp('COHERE', {}),
    ModelProvider.GOOGLE: _bpp('GOOGLE', {}),
    # ModelProvider.VERTEX_AI: _bpp('GOOGLE_VERTEX_AI', {
    #     'GOOGLE_VERTEX_AI_REGION': 'vertex_region',
    #     'GOOGLE_VERTEX_AI_PROJECT_ID': 'vertex_project_id',
    #     'GOOGLE_VERTEX_AI_SERVICE_ACCOUNT_JSON': 'vertex_service_account_json',
    #     'GOOGLE_VERTEX_AI_STORAGE_BUCKET_NAME': 'vertex_storage_bucket_name',
    #     'GOOGLE_VERTEX_AI_MODEL_NAME': 'vertex_model_name',
    #     'GOOGLE_VERTEX_AI_FILENAME': 'filename'
    # }),
    # ModelProvider.GROQ: _bpp('GROQ', {}),
    # ModelProvider.HUGGINGFACE: _bpp('HUGGINGFACE', {
    #     'HUGGINGFACE_BASE_URL': 'huggingfaceBaseUrl'
    # }),
    ModelProvider.MISTRAL_AI: _bpp('MISTRAL', {
        'MISTRAL_FIM_COMPLETION': 'mistral_fim_completion'
    }),
    # ModelProvider.JINA: _bpp('JINA', {}),
    ModelProvider.OLLAMA: _bpp('OLLAMA', {}),
    ModelProvider.OPENROUTER: _bpp('OPENROUTER', {}),
    # ModelProvider.STABILITY_AI: _bpp('STABILITY', {
    #     'STABILITY_CLIENT_ID': 'stability_client_id',
    #     'STABILITY_CLIENT_USER_ID': 'stability_client_user_id',
    #     'STABILITY_CLIENT_VERSION': 'stability_client_version'
    # }),
    # ModelProvider.TOGETHER_AI: _bpp('TOGETHER_AI', {}),
    ModelProvider.WATSONX: _bpp('WATSONX', {
        'WATSONX_VERSION': 'watsonx_version',
        'WATSONX_SPACE_ID': 'watsonx_space_id',
        'WATSONX_PROJECT_ID': 'watsonx_project_id',
        'WATSONX_APIKEY': 'api_key'
    })

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
PROVIDER_PROPERTIES_RLUT= {}
for provider in PROVIDER_PROPERTIES_LUT.keys():
    PROVIDER_PROPERTIES_RLUT[provider] = {v:k for k,v in PROVIDER_PROPERTIES_LUT[provider].items()}

PROVIDER_LUT = {k:k for k in PROVIDER_PROPERTIES_LUT.keys() }
PROVIDER_LUT.update({
    # any overrides for the provider prefix to provider name can be provided here on PROVIDER_LUT
})



PROVIDER_REQUIRED_FIELDS = {k:['api_key'] if k not in ['ollama']  else [] for k in PROVIDER_PROPERTIES_LUT.keys()}
PROVIDER_REQUIRED_FIELDS.update({
    # Mark the required fields for a provider
})

def env_file_to_model_ProviderConfig(model_name: str, env_file_path: str) -> ProviderConfig | None:
    provider = next(filter(lambda x: x not in ('virtual-policy', 'virtual-model'), model_name.split('/')))
    if provider not in PROVIDER_LUT:
        raise ValueError(f"Unsupported model provider {provider}")

    values = dotenv_values(str(env_file_path))

    if values is None:
        raise ValueError(f"No provider configuration in env file {env_file_path}")

    cfg = ProviderConfig()
    cfg.provider = PROVIDER_LUT[provider]

    cred_lut = PROVIDER_PROPERTIES_LUT[provider]


    consumed_credentials = []
    for key, value in values.items():
        if key in cred_lut:
            k = cred_lut[key]
            consumed_credentials.append(k)
            setattr(cfg, k, value)


    required_creds = PROVIDER_REQUIRED_FIELDS[provider]
    missing_credentials = []
    for cred in required_creds:
        if cred not in consumed_credentials:
            missing_credentials.append(cred)

    if len(missing_credentials) > 0:
        raise ValueError(f"Missing environment variable(s) {', '.join(map(lambda c: PROVIDER_PROPERTIES_RLUT[provider][c], missing_credentials))} required for the provider {provider}")

    return cfg