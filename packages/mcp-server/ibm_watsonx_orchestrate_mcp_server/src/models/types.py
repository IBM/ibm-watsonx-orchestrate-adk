from pydantic import BaseModel, Field
from typing import Optional, List
from ibm_watsonx_orchestrate.agent_builder.models.types import ProviderConfig, ModelType
from ibm_watsonx_orchestrate.agent_builder.model_policies.types import  ModelPolicyStrategyMode

class CreateModelOptions(BaseModel):
    name: str = Field(
        description="Name of the model you wish to create. Must be in the format '<provider>/<model_name>'"
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the model you wish to create."
    )
    display_name: Optional[str] = Field(
        default=None,
        description="A human readable name for the model."
    )
    provider_config: Optional[ProviderConfig] = Field(
        default=None,
        description="Provider specific configuration for the model such as connection details or cloud resource identifiers."
    )
    app_id: Optional[str] = Field(
        default=None,
        description="The app_id of a key_value connection containing secrets for model authentication such as api_key. These values are merged with the provider_config and provide a secure way of passing secret data to the model config"
    )
    type: ModelType = Field(
        default=ModelType.CHAT,
        description="The type of model being created. Defaults to 'chat'"
    )

class CreateModelPolicyOptions(BaseModel):
    name: str = Field(
        description="Name of the model policy you wish to create."
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the model policy you wish to create."
    )
    display_name: Optional[str] = Field(
        default=None,
        description="A human readable display name for the model policy."
    )
    models: List[str] = Field(
        description="List of models to be used by the policy."
    )
    strategy: ModelPolicyStrategyMode = Field(
        description="How the policy will handle model selection. 'fallback' will select the first model in the list and move down the list if that errors. 'loadbalance' will share request between all the models."
    )
    retry_attempts: Optional[int] = Field(
        default=None,
        description="Number of times a model will be retried before failing."
    )
    strategy_on_code: Optional[List[int]] = Field(
        default=None,
        description="List of HTTP status codes to envoke the strategy on. Primarily used by fallback to specify what HTTP codes trigger a different model to be called."
    )
    retry_on_code: Optional[List[int]] = Field(
        default=None,
        description="List of HTTP status codes that should trigger a retry."
    )
