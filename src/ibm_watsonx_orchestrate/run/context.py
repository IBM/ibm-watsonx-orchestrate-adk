from types import MappingProxyType
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator

from ibm_watsonx_orchestrate.agent_builder.tools.types import JsonSchemaObject


class AgentRun(BaseModel):
  model_config = ConfigDict(arbitrary_types_allowed=True)
  request_context: Optional[MappingProxyType | dict] = None
  dynamic_input_schema: Optional[JsonSchemaObject | dict] = None
  dynamic_output_schema: Optional[JsonSchemaObject | dict] = None

  @field_validator('request_context', mode="before")
  def create_mutable_type(cls, value):
    return dict(value) if value else value

  @field_validator('request_context', mode="after")
  def create_immutable_type(cls, value):
    return MappingProxyType(value) if value else value

  @field_validator('dynamic_input_schema', 'dynamic_output_schema', mode="before")
  def create_schema_object(cls, value):
    if value and isinstance(value, dict):
      return JsonSchemaObject(**value)
    return value