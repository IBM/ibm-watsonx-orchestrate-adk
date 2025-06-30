import json
import yaml
from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, model_validator, ConfigDict
from ibm_watsonx_orchestrate.agent_builder.tools import BaseTool, PythonTool
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.types import KnowledgeBaseSpec, KnowledgeBaseBuiltInVectorIndexConfig, HAPFiltering, HAPFilteringConfig, CitationsConfig, ConfidenceThresholds, QueryRewriteConfig, GenerationConfiguration
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base import KnowledgeBase
from ibm_watsonx_orchestrate.agent_builder.agents.webchat_customizations import StarterPrompts, WelcomeContent
from pydantic import Field, AliasChoices
from typing import Annotated

from ibm_watsonx_orchestrate.agent_builder.tools.types import JsonSchemaObject

# TO-DO: this is just a placeholder. Will update this later to align with backend
DEFAULT_LLM = "watsonx/meta-llama/llama-3-1-70b-instruct"

class SpecVersion(str, Enum):
    V1 = "v1"


class AgentKind(str, Enum):
    NATIVE = "native"
    EXTERNAL = "external"
    ASSISTANT = "assistant"

class ExternalAgentAuthScheme(str, Enum):
    BEARER_TOKEN = 'BEARER_TOKEN'
    API_KEY = "API_KEY"
    NONE = 'NONE'

class AgentProvider(str, Enum):
    WXAI = "wx.ai"
    EXT_CHAT = "external_chat"
    SALESFORCE = "salesforce"
    WATSONX = "watsonx"
    A2A = 'external_chat/A2A/0.2.1' #provider type returned from an assistant agent


class AssistantAgentAuthType(str, Enum):
    ICP_IAM = "ICP_IAM"
    IBM_CLOUD_IAM = "IBM_CLOUD_IAM"
    MCSP = "MCSP"
    BEARER_TOKEN = "BEARER_TOKEN"
    HIDDEN = "<hidden>"


class BaseAgentSpec(BaseModel):
    spec_version: SpecVersion = None
    kind: AgentKind
    id: Optional[Annotated[str, Field(json_schema_extra={"min_length_str": 1})]] = None
    name: Annotated[str, Field(json_schema_extra={"min_length_str":1})]
    display_name: Annotated[Optional[str], Field(json_schema_extra={"min_length_str":1})] = None
    description: Annotated[str, Field(json_schema_extra={"min_length_str":1})]
    context_access_enabled: bool = True
    context_variables: Optional[List[str]] = []

    def dump_spec(self, file: str) -> None:
        dumped = self.model_dump(mode='json', exclude_unset=True, exclude_none=True)
        with open(file, 'w') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                yaml.dump(dumped, f, sort_keys=False)
            elif file.endswith('.json'):
                json.dump(dumped, f, indent=2)
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')

    def dumps_spec(self) -> str:
        dumped = self.model_dump(mode='json', exclude_none=True)
        return json.dumps(dumped, indent=2)

# ===============================
#      NATIVE AGENT TYPES
# ===============================

class ChatWithDocsConfig(BaseModel):
    enabled: Optional[bool] = None
    vector_index: Optional[KnowledgeBaseBuiltInVectorIndexConfig] = None
    generation:  Optional[GenerationConfiguration] = None
    query_rewrite:  Optional[QueryRewriteConfig] = None
    confidence_thresholds: Optional[ConfidenceThresholds] =None
    citations:  Optional[CitationsConfig] = None
    hap_filtering: Optional[HAPFiltering] = None
    
class AgentStyle(str, Enum):
    DEFAULT = "default"
    REACT = "react"
    PLANNER = "planner"

class AgentGuideline(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    display_name: Optional[str] = None
    condition: str
    action: str
    tool: Optional[BaseTool] | Optional[str] = None

    def __init__(self, *args, **kwargs):
        if "tool" in kwargs and kwargs["tool"]:
            kwargs["tool"] = kwargs['tool'].__tool_spec__.name if isinstance(kwargs['tool'], BaseTool) else kwargs["tool"]

        super().__init__(*args, **kwargs)

class AgentSpec(BaseAgentSpec):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    kind: AgentKind = AgentKind.NATIVE
    llm: str = DEFAULT_LLM
    style: AgentStyle = AgentStyle.DEFAULT
    custom_join_tool: str | PythonTool | None = None
    structured_output: Optional[JsonSchemaObject] = None
    instructions: Annotated[Optional[str], Field(json_schema_extra={"min_length_str":1})] = None
    guidelines: Optional[List[AgentGuideline]] = None
    collaborators: Optional[List[str]] | Optional[List['BaseAgentSpec']] = []
    tools: Optional[List[str]] | Optional[List['BaseTool']] = []
    hidden: bool = False
    knowledge_base: Optional[List[str]] | Optional[List['KnowledgeBaseSpec']] = []
    chat_with_docs: Optional[ChatWithDocsConfig] = None
    starter_prompts: Optional[StarterPrompts] = None
    welcome_content: Optional[WelcomeContent] = None


    def __init__(self, *args, **kwargs):
        if "tools" in kwargs and kwargs["tools"]:
            kwargs["tools"] = [x.__tool_spec__.name if isinstance(x, BaseTool) else x for x in kwargs["tools"]]
        if "knowledge_base" in kwargs and kwargs["knowledge_base"]:
            kwargs["knowledge_base"] = [x.name if isinstance(x, KnowledgeBase) else x for x in kwargs["knowledge_base"]]
        if "collaborators" in kwargs and kwargs["collaborators"]:
            kwargs["collaborators"] = [x.name if isinstance(x, BaseAgentSpec) else x for x in kwargs["collaborators"]]
        super().__init__(*args, **kwargs)

    @model_validator(mode="before")
    def validate_fields(cls, values):
        return validate_agent_fields(values)
    
    @model_validator(mode="after")
    def validate_kind(self):
        if self.kind != AgentKind.NATIVE:
            raise ValueError(f"The specified kind '{self.kind}' cannot be used to create a native agent.")
        return self

def validate_agent_fields(values: dict) -> dict:
    # Check for empty strings or whitespace
    for field in ["id", "name", "kind", "description", "collaborators", "tools", "knowledge_base"]:
        value = values.get(field)
        if value and not str(value).strip():
            raise ValueError(f"{field} cannot be empty or just whitespace")
    
    name = values.get("name")
    collaborators = values.get("collaborators", [])  if values.get("collaborators", []) else []
    for collaborator in collaborators:
        if collaborator == name:
            raise ValueError(f"Circular reference detected. The agent '{name}' cannot contain itself as a collaborator")

    if values.get("style") == AgentStyle.PLANNER:
        if values.get("custom_join_tool") and values.get("structured_output"):
            raise ValueError("Only one of 'custom_join_tool' or 'structured_output' can be provided for planner style agents.")

    context_variables = values.get("context_variables")
    if context_variables is not None:
        if not isinstance(context_variables, list):
            raise ValueError("context_variables must be a list")
        for var in context_variables:
            if not isinstance(var, str) or not var.strip():
                raise ValueError("All context_variables must be non-empty strings")

    return values

# ===============================
#      EXTERNAL AGENT TYPES
# ===============================

class ExternalAgentConfig(BaseModel):
    hidden: bool = False
    enable_cot: bool = False

class ExternalAgentSpec(BaseAgentSpec):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    kind: AgentKind = AgentKind.EXTERNAL
    title: Annotated[str, Field(json_schema_extra={"min_length_str":1})]
    tags: Optional[List[str]] = None
    api_url: Annotated[str, Field(json_schema_extra={"min_length_str":1})]
    auth_scheme: ExternalAgentAuthScheme = ExternalAgentAuthScheme.NONE
    auth_config: dict = {}
    provider: AgentProvider = AgentProvider.EXT_CHAT
    chat_params: dict = None
    config: ExternalAgentConfig = ExternalAgentConfig()
    nickname: Annotated[str | None, Field(json_schema_extra={"min_length_str":1})] = None
    app_id: Annotated[str | None, Field(json_schema_extra={"min_length_str":1})] = None
    connection_id: Annotated[str | None, Field(json_schema_extra={"min_length_str":1})] = None

    @model_validator(mode="before")
    def validate_fields_for_external(cls, values):
        return validate_external_agent_fields(values)

    @model_validator(mode="after")
    def validate_kind_for_external(self):
        if self.kind != AgentKind.EXTERNAL:
            raise ValueError(f"The specified kind '{self.kind}' cannot be used to create an external agent.")
        return self

def validate_external_agent_fields(values: dict) -> dict:
    # Check for empty strings or whitespace
    for field in ["name", "kind", "description", "title", "tags", "api_url", "chat_params", "nickname", "app_id"]:
        value = values.get(field)
        if value and not str(value).strip():
            raise ValueError(f"{field} cannot be empty or just whitespace")

    context_variables = values.get("context_variables")
    if context_variables is not None:
        if not isinstance(context_variables, list):
            raise ValueError("context_variables must be a list")
        for var in context_variables:
            if not isinstance(var, str) or not var.strip():
                raise ValueError("All context_variables must be non-empty strings")

    return values

# # ===============================
# #      ASSISTANT AGENT TYPES
# # ===============================

class AssistantAgentConfig(BaseModel):
    api_version: Annotated[str | None, Field(json_schema_extra={"min_length_str":1})] = None
    assistant_id: Annotated[str | None, Field(json_schema_extra={"min_length_str":1})] = None
    crn: Annotated[str | None, Field(json_schema_extra={"min_length_str":1})] = None
    service_instance_url: Annotated[str | None, Field(validation_alias=AliasChoices('instance_url', 'service_instance_url'), serialization_alias='service_instance_url')] = None
    environment_id: Annotated[str | None, Field(json_schema_extra={"min_length_str":1})] = None
    auth_type: Annotated[str | None, Field(json_schema_extra={"min_length_str":1})] = None
    connection_id: Annotated[str | None, Field(json_schema_extra={"min_length_str":1})] = None
    api_key: Annotated[str | None, Field(json_schema_extra={"min_length_str":1})] = None
    authorization_url: Annotated[str | None, Field(json_schema_extra={"min_length_str":1})] = None
    auth_type: AssistantAgentAuthType = AssistantAgentAuthType.MCSP

class AssistantAgentSpec(BaseAgentSpec):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    kind: AgentKind = AgentKind.ASSISTANT
    title: Annotated[str, Field(json_schema_extra={"min_length_str":1})]
    tags: Optional[List[str]] = None
    config: AssistantAgentConfig = AssistantAgentConfig()
    nickname: Annotated[str | None, Field(json_schema_extra={"min_length_str":1})] = None
    connection_id: Annotated[str | None, Field(json_schema_extra={"min_length_str":1})] = None

    @model_validator(mode="before")
    def validate_fields_for_external(cls, values):
        return validate_assistant_agent_fields(values)

    @model_validator(mode="after")
    def validate_kind_for_external(self):
        if self.kind != AgentKind.ASSISTANT:
            raise ValueError(f"The specified kind '{self.kind}' cannot be used to create an assistant agent.")
        return self

def validate_assistant_agent_fields(values: dict) -> dict:
    # Check for empty strings or whitespace
    for field in ["name", "kind", "description", "title", "tags", "nickname", "app_id"]:
        value = values.get(field)
        if value and not str(value).strip():
            raise ValueError(f"{field} cannot be empty or just whitespace")

    # Validate context_variables if provided
    context_variables = values.get("context_variables")
    if context_variables is not None:
        if not isinstance(context_variables, list):
            raise ValueError("context_variables must be a list")
        for var in context_variables:
            if not isinstance(var, str) or not var.strip():
                raise ValueError("All context_variables must be non-empty strings")

    return values
