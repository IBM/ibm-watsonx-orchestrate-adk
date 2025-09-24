from typing import Any, TypeAlias
from ibm_watsonx_orchestrate.agent_builder.agents.agent import Agent
from ibm_watsonx_orchestrate.agent_builder.agents.external_agent import ExternalAgent
from ibm_watsonx_orchestrate.agent_builder.agents.assistant_agent import AssistantAgent
from ibm_watsonx_orchestrate.cli.commands.agents.agents_controller import (
    AgentKind
)
from ibm_watsonx_orchestrate.agent_builder.agents.types import (
    ExternalAgentAuthScheme,
    AgentProvider,
    AgentStyle,
    DEFAULT_LLM
)

from typing_extensions import Optional, List
from pydantic import BaseModel, Field

class ListAgents:
    native: List[dict] = []
    assistant: List[dict] = []
    external: List[dict] = []

class ExternalAgentAuthConfig(BaseModel):
    token: str = Field(
        description="The apikey, bearer token or client secret required to auth to an external agent"
    )
    grant_type: Optional[str] = Field(
        default=None,
        description="Used when the provider is Salesforce. Defaults to 'client_credentials' if None is passed"
    )

class AgentConfig(BaseModel):
    hidden: bool = Field(
        default=False,
        description="Should the agent be hidden in the UI"
    )
    enable_cot: bool = Field(
        default=False,
        description="Should the agent display chain of thought reasoning"
    )

class CreateAgentOptions(BaseModel):
    name: str = Field(
        description="Name of the agent you wish to create"
    )
    description: str = Field(
        description="Description of the agent you wish to create. Should be descriptive of what capabilites an agent has to assist in routing from a parent agent"
    )
    title: Optional[str] = Field(
        default=None,
        description="Title of the agent you wish to create. Required for External and Assistant Agents"
    )
    kind: Optional[AgentKind] = Field(
        default=None,
        description="Kind of agent you wish to create"
    )
    instructions: Optional[str] = Field(
        default=None,
        description="Used for native agents. Controls the behaviour of the agent. Should include tool calling directions, collaborator routing instructions, output format requirements and any other guidance the agent should follow"
    )
    api_url: Optional[str] = Field(
        default=None,
        description="Required for External Agents. The API URL of the external agent"
    )
    auth_scheme: ExternalAgentAuthScheme = Field(
        default=ExternalAgentAuthScheme.NONE,
        description="Used for External Agents to control the auth scheme used when authenticating to the api"
    )
    provider: AgentProvider = Field(
        default=AgentProvider.EXT_CHAT,
        description="Used for External Agents to control the provider type of the external agent"
    )
    auth_config: Optional[ExternalAgentAuthConfig] = Field(
        default=None,
        description="Used for External Agents when 'auth_scheme' is not 'None' to pass is secret values like API key, bearer token or client_secret"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Optional tags that will appear in the UI."
    )
    chat_params: Optional[dict[str, Any]] = Field(
        default=None,
        description="Chat parameters in JSON format (e.g., '{\"stream\": true}'). Only needed for External and Assistant Agents"
    )
    config: Optional[AgentConfig] = Field(
        default=None,
        description="Used to configure options on the agent such as if it should appear in the UI or not"
    )
    app_id: Optional[str] = Field(
        default=None,
        description="The name of a connection that contains authentication secrets. Used for external and assistant agents only"
    )
    llm: str = Field(
        default=DEFAULT_LLM,
        description="The LLM model to use for this agent. If not specified, the default will be used. The value provided must be a model in the watsonx Orchestrate platform"
    )
    style: AgentStyle = Field(
        default=AgentStyle.DEFAULT,
        description="The style of the agent. This is used to control the behavior of the agent. Only used for native agents"
    )
    custom_join_tool: Optional[str] = Field(
        default=None,
        description="Used only when style is 'planner'. The name of the custom join tool to use for this agent. Only used for native agents"
    )
    structured_output: Optional[dict] = Field(
        default=None,
        description="Used only when style is 'planner'. A JSON Schema object that defines the desired structure of the agent\'s final output. Only used for native agents"
    )
    collaborators: Optional[List[str]] = Field(
        default=None,
        description="The names of agents that this agent should be able to call as collaborators. Only used for native agents"
    )
    tools: Optional[List[str]] = Field(
        default=None,
        description="The names of tools that this agent should be able to call. Only used for native agents"
    )
    knowledge_base: Optional[List[str]] = Field(
        default=None,
        description="The names of knowledge bases that this agent should be able to access. Only used for native agents"
    )

AnyAgent: TypeAlias = Agent | ExternalAgent | AssistantAgent