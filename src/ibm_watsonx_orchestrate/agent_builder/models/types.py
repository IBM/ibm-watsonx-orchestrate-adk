from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import Field, BaseModel, ConfigDict, model_validator

class  ModelProvider(str, Enum):
    OPENAI = 'openai'
    A21 = 'a21'
    ANTHROPIC = 'anthropic'
    ANYSCALE = 'anyscale'
    AZURE_OPENAI = 'azure-openai'
    AZURE_AI = 'azure-ai'
    BEDROCK = 'bedrock'
    CEREBRAS = 'cerebras'
    COHERE = 'cohere'
    GOOGLE = 'google'
    VERTEX_AI = 'vertex-ai'
    GROQ = 'groq'
    HUGGINGFACE = 'huggingface'
    MISTRAL_AI = 'mistral-ai'
    JINA = 'jina'
    OLLAMA = 'ollama'
    OPENROUTER = 'openrouter'
    STABILITY_AI = 'stability-ai'
    TOGETHER_AI = 'together-ai'
    WATSONX = 'watsonx'
    X_AI='x-ai'

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value
    
    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_ 

class  ModelType(str, Enum):
    CHAT = 'chat'
    CHAT_VISION = 'chat_vision'
    COMPLETION = 'completion'
    EMBEDDING = 'embedding'

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value
    
class  ModelType(str, Enum):
    CHAT = 'chat'
    CHAT_VISION = 'chat_vision'
    COMPLETION = 'completion'
    EMBEDDING = 'embedding'

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

class ProviderConfig(BaseModel):
    # Required fields
    provider: Optional[str]=''


    api_key: Optional[str] = None
    url_to_fetch: Optional[str] = Field(None, alias="urlToFetch")

    # Misc
    custom_host: Optional[str] = Field(None, alias="customHost")
    forward_headers: Optional[List[str]] = Field(None, alias="forwardHeaders")
    index: Optional[int] = None
    cache: Optional[Union[str, Dict[str, Any]]] = None  # Define CacheSettings if needed
    metadata: Optional[Dict[str, str]] = None
    request_timeout: Optional[int] = Field(None, alias="requestTimeout")
    transform_to_form_data: Optional[bool] = Field(None, alias="transformToFormData")

    # Azure specific
    azure_resource_name: Optional[str] = Field(None, alias="resourceName")
    azure_deployment_id: Optional[str] = Field(None, alias="deploymentId")
    azure_api_version: Optional[str] = Field(None, alias="apiVersion")
    ad_auth: Optional[str] = Field(None, alias="adAuth")
    azure_auth_mode: Optional[str] = Field(None, alias="azureAuthMode")
    azure_managed_client_id: Optional[str] = Field(None, alias="azureManagedClientId")
    azure_entra_client_id: Optional[str] = Field(None, alias="azureEntraClientId")
    azure_entra_client_secret: Optional[str] = Field(None, alias="azureEntraClientSecret")
    azure_entra_tenant_id: Optional[str] = Field(None, alias="azureEntraTenantId")
    azure_ad_token: Optional[str] = Field(None, alias="azureAdToken")
    azure_model_name: Optional[str] = Field(None, alias="azureModelName")
    azure_inference_deployment_name: Optional[str] = Field(None, alias="azureDeploymentName")
    azure_inference_api_version: Optional[str] = Field(None, alias="azureApiVersion")
    azure_inference_extra_params: Optional[str] = Field(None, alias="azureExtraParams")
    azure_inference_foundry_url: Optional[str] = Field(None, alias="azureFoundryUrl")


    # Workers AI specific
    workers_ai_account_id: Optional[str] = Field(None, alias="workersAiAccountId")


    # AWS
    aws_secret_access_key: Optional[str] = Field(None, alias="awsSecretAccessKey")
    aws_access_key_id: Optional[str] = Field(None, alias="awsAccessKeyId")
    aws_session_token: Optional[str] = Field(None, alias="awsSessionToken")
    aws_region: Optional[str] = Field(None, alias="awsRegion")
    aws_auth_type: Optional[str] = Field(None, alias="awsAuthType")
    aws_role_arn: Optional[str] = Field(None, alias="awsRoleArn")
    aws_external_id: Optional[str] = Field(None, alias="awsExternalId")
    aws_s3_bucket: Optional[str] = Field(None, alias="awsS3Bucket")
    aws_s3_object_key: Optional[str] = Field(None, alias="awsS3ObjectKey")
    aws_bedrock_model: Optional[str] = Field(None, alias="awsBedrockModel")
    aws_server_side_encryption: Optional[str] = Field(None, alias="awsServerSideEncryption")
    aws_server_side_encryption_kms_key_id: Optional[str] = Field(None, alias="awsServerSideEncryptionKMSKeyId")

    # Sagemaker
    amzn_sagemaker_custom_attributes: Optional[str] = Field(None, alias="amznSagemakerCustomAttributes")
    amzn_sagemaker_target_model: Optional[str] = Field(None, alias="amznSagemakerTargetModel")
    amzn_sagemaker_target_variant: Optional[str] = Field(None, alias="amznSagemakerTargetVariant")
    amzn_sagemaker_target_container_hostname: Optional[str] = Field(None, alias="amznSagemakerTargetContainerHostname")
    amzn_sagemaker_inference_id: Optional[str] = Field(None, alias="amznSagemakerInferenceId")
    amzn_sagemaker_enable_explanations: Optional[str] = Field(None, alias="amznSagemakerEnableExplanations")
    amzn_sagemaker_inference_component: Optional[str] = Field(None, alias="amznSagemakerInferenceComponent")
    amzn_sagemaker_session_id: Optional[str] = Field(None, alias="amznSagemakerSessionId")
    amzn_sagemaker_model_name: Optional[str] = Field(None, alias="amznSagemakerModelName")

    # Stability AI
    stability_client_id: Optional[str] = Field(None, alias="stabilityClientId")
    stability_client_user_id: Optional[str] = Field(None, alias="stabilityClientUserId")
    stability_client_version: Optional[str] = Field(None, alias="stabilityClientVersion")

    # Hugging Face
    huggingface_base_url: Optional[str] = Field(None, alias="huggingfaceBaseUrl")

    # Google Vertex AI
    vertex_region: Optional[str] = Field(None, alias="vertexRegion")
    vertex_project_id: Optional[str] = Field(None, alias="vertexProjectId")
    vertex_service_account_json: Optional[Dict[str, Any]] = Field(None, alias="vertexServiceAccountJson")
    vertex_storage_bucket_name: Optional[str] = Field(None, alias="vertexStorageBucketName")
    vertex_model_name: Optional[str] = Field(None, alias="vertexModelName")

    filename: Optional[str] = None

    after_request_hooks: Optional[List[Dict[str, Any]]] = Field(None, alias="afterRequestHooks")
    before_request_hooks: Optional[List[Dict[str, Any]]] = Field(None, alias="beforeRequestHooks")
    default_input_guardrails: Optional[List[Dict[str, Any]]] = Field(None, alias="defaultInputGuardrails")
    default_output_guardrails: Optional[List[Dict[str, Any]]] = Field(None, alias="defaultOutputGuardrails")

    # OpenAI
    openai_project: Optional[str] = Field(None, alias="openaiProject")
    openai_organization: Optional[str] = Field(None, alias="openaiOrganization")
    openai_beta: Optional[str] = Field(None, alias="openaiBeta")

    # Azure Inference
    azure_deployment_name: Optional[str] = Field(None, alias="azureDeploymentName")
    azure_extra_params: Optional[str] = Field(None, alias="azureExtraParams")
    azure_foundry_url: Optional[str] = Field(None, alias="azureFoundryUrl")

    strict_open_ai_compliance: Optional[bool] = Field(None, alias="strictOpenAiCompliance")
    mistral_fim_completion: Optional[str] = Field(None, alias="mistralFimCompletion")

    # Anthropic
    anthropic_beta: Optional[str] = Field(None, alias="anthropicBeta")
    anthropic_version: Optional[str] = Field(None, alias="anthropicVersion")

    # Fireworks
    fireworks_account_id: Optional[str] = Field(None, alias="fireworksAccountId")

    # Cortex
    snowflake_account: Optional[str] = Field(None, alias="snowflakeAccount")

    # WatsonX
    watsonx_version: Optional[str] = Field(None, alias="watsonxVersion")
    watsonx_space_id: Optional[str] = Field(None, alias="watsonxSpaceId")
    watsonx_project_id: Optional[str] = Field(None, alias="watsonxProjectId")
    watsonx_deployment_id: Optional[str] = Field(None, alias="watsonxDeploymentId")
    watsonx_cpd_url:Optional[str] = Field(None, alias="watsonxCpdUrl")
    watsonx_cpd_username:Optional[str] = Field(None, alias="watsonxCpdUsername")
    watsonx_cpd_password:Optional[str] = Field(None, alias="watsonxCpdPassword")

    model_config = {
        "populate_by_name": True,  # Replaces allow_population_by_field_name
        "extra": "forbid",         # Same as before
        "json_schema_extra": lambda schema: schema.get("properties", {}).pop("provider", None)
    }

    def update(self, new_config: "ProviderConfig") -> "ProviderConfig":
        old_config_dict = dict(self)
        new_config_dict = dict(new_config)

        new_config_dict = {k:v for k, v in new_config_dict.items() if v is not None}
        old_config_dict.update(new_config_dict)

        return ProviderConfig.model_validate(old_config_dict)


class VirtualModel(BaseModel):
    model_config = ConfigDict(extra='allow')

    name: str
    display_name: Optional[str]
    description: Optional[str]
    config: Optional[dict] = None
    provider_config: Optional[ProviderConfig] = None
    tags: List[str] = []
    model_type: str = ModelType.CHAT
    connection_id: Optional[str] = None

    @model_validator(mode="before")
    def validate_fields(cls, values):
        if not values.get("display_name"):
            values["display_name"] = values.get("name")
        if not values.get("description"):
            values["description"] = values.get("name")
        
        return values

class ListVirtualModel(BaseModel):
    model_config = ConfigDict(extra='allow')

    id: Optional[str] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    provider: Optional[str] = None
    # model_configuration: Optional[dict] = None
    provider_config: Optional[ProviderConfig] = None
    tags: Optional[List[str]] = None
    model_type: Optional[str] = None
    connection_id: Optional[str] = None


class ModelConfig(BaseModel):
    # one difference between adk and runtime is runtime has a fixed schema for model.config attribute (`ModelConfig`)
    # for now, this class will be only used to make agent.llm_config a hidden feature
    model: str = ""
    model_config = ConfigDict(extra="allow")


class ModelListEntry(BaseModel):
    name: Optional[str] = Field(default=None, description="Name of the model")
    description: Optional[str] = Field(default=None, description="A description of the model")
    is_custom: bool = Field(default=False, description="Is the model a third party model imported into Orchestrate")
    recommended: bool = Field(default=False, description="Is the model a reccomended model in watsonx. Non-custom models only")

    def get_row_details(self):
        description = self.description or 'No description provided.'
        if self.is_custom:
            return [f"✨️ {self.name}", description]
        else:
            name = self.name or "N/A"
            marker = "★ " if self.recommended else ""
            return [f"[yellow]{marker}[/yellow]{name}", description]

ANTHROPIC_DEFAULT_MAX_TOKENS = 4096