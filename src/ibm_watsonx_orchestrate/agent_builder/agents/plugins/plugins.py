from pydantic import BaseModel, Field, field_validator
from typing import Optional, List

class PluginRef(BaseModel):
    plugin_name: Optional[str] = None
    plugin_id: Optional[str] = None

class Plugins(BaseModel):
    agent_pre_invoke: List[PluginRef] = Field(default_factory=list)
    agent_post_invoke: List[PluginRef] = Field(default_factory=list)

    @field_validator("*", mode="before")
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
    