from types import MappingProxyType
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class AgentRun(BaseModel):
  model_config = ConfigDict(arbitrary_types_allowed=True)
  request_context: Optional[MappingProxyType | dict] = None

  @field_validator('request_context', mode="before")
  def create_mutable_type(cls, value):
    return dict(value) if value else value

  @field_validator('request_context', mode="after")
  def create_immutable_type(cls, value):
    return MappingProxyType(value) if value else value