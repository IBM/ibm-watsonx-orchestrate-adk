from collections.abc import Mapping
from types import MappingProxyType
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator

from ibm_watsonx_orchestrate.agent_builder.tools.types import JsonSchemaObject

class RequestContext(Mapping):

  @property
  def context(self) -> dict:
    if self.__merge_required:
      self.__current_context = dict(**self.__initial_context)
      self.__current_context.update(self.__updated_context)
      self.__merge_required = False

    return self.__current_context

  def __init__(self, *args, **kwargs):
    self.__initial_context = {}
    [self.__initial_context.update(dict(arg)) for arg in args if hasattr(arg,'__iter__')]
    self.__initial_context.update(kwargs)
    self.__updated_context = {}
    self.__current_context = {}
    self.__merge_required = True

  # getters
  def get(self, key: str, default: Optional[any] = None):
    return self.context.get(key,default)

  def __getitem__(self, key: str):
    return self.context[key]

  # setters
  def __setitem__(self, key: str, value: any):
    self.__updated_context[key] = value
    self.__merge_required = True

  def update(self, obj: dict):
    self.__updated_context.update(obj)
    self.__merge_required = True

  def __delitem__(self, key: str = None):
    if not key:
      return
    try:
      del self.__updated_context[key]
      self.__merge_required = True
    except Exception as e:
      if self.__initial_context.get(key,None):
        raise ValueError(f"Cannot delete '{key}' from initial context")
      else:
        raise e

  # container
  def __iter__(self):
    return iter(self.context)

  def __contains__(self, key: str):
    return key in self.context

  def __str__(self):
    return str(self.context)

  def __repr__(self):
    return repr(self.context)

  def __len__(self):
    return len(self.context)

  def keys(self):
    return self.context.keys()

  def values(self):
    return self.context.values()

  def items(self):
    return self.context.items()
  
  # other
  def clear_updates(self):
    self.__updated_context = {}
    self.__merge_required = True

  def get_updates(self) -> dict:
    return self.__updated_context


  


class AgentRun(BaseModel):
  model_config = ConfigDict(arbitrary_types_allowed=True)
  request_context: Optional[RequestContext | dict] = RequestContext()
  dynamic_input_schema: Optional[JsonSchemaObject | dict] = None
  dynamic_output_schema: Optional[JsonSchemaObject | dict] = None


  @field_validator('request_context', mode="before")
  def create_context_type(cls, value):
    if isinstance(value, RequestContext):
      return value
    return RequestContext() if value is None else RequestContext(**value)

  @field_validator('dynamic_input_schema', 'dynamic_output_schema', mode="before")
  def create_schema_object(cls, value):
    if value and isinstance(value, dict):
      return JsonSchemaObject(**value)
    return value
  
  def clear_context_updates(self):
    self.request_context.clear_updates()
  
  def get_context_updates(self) -> dict:
    return self.request_context.get_updates()