from pydantic import BaseModel, Field, field_validator
from typing import Optional, List

class PluginRef(BaseModel):
    plugin_name: Optional[str] = None
    plugin_id: Optional[str] = None

# Keys under `plugins` that hold lifecycle hook references. Anything else in
# there is plain agent config (e.g. tool_shortlisting).
PLUGIN_HOOK_KEYS = ("agent_pre_invoke", "agent_post_invoke")

class ToolShortlistingConfig(BaseModel):
    """Mirrors wo_archer.schema.agents.ToolShortlistingConfig (ticket #79272)."""
    enabled: bool = False
    max_tools: Optional[int] = None

class Plugins(BaseModel):
    agent_pre_invoke: List[PluginRef] = Field(default_factory=list)
    agent_post_invoke: List[PluginRef] = Field(default_factory=list)
    tool_shortlisting: Optional[ToolShortlistingConfig] = None

    @field_validator("agent_pre_invoke", "agent_post_invoke", mode="before")
    def none_to_empty_list(cls, v):
        if v is None:
            return []
        return v

class Agent(BaseModel):
    # other fields...
    plugins: Optional[Plugins] = Field(default_factory=Plugins)

    @field_validator("plugins", mode="before")
    def ensure_plugins_object(cls, v):
        # Convert raw dicts into a Plugins instance automatically
        if isinstance(v, dict):
            return Plugins(**v)
        return v
    