import json
import re

from pydantic import BaseModel

from ibm_watsonx_orchestrate.agent_builder.connections.types import ConnectionSecurityScheme
from .base_tool import BaseTool
from .types import LangflowToolBinding, ToolBinding, ToolPermission, ToolRequestBody, ToolResponseBody, ToolSpec
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

MIN_LANGFLOW_VERSION = [1,5,0]
LANGFLOW_CHAT_INPUT_LABEL = "ChatInput"
LANGFLOW_CHAT_OUTPUT_LABEL = "ChatOutput"
VALID_NAME_PATTERN = re.compile("^[a-zA-Z](\\w|_)+$")

class LangflowTool(BaseTool):
  def __init__(self,spec: ToolSpec):
    BaseTool.__init__(self,spec=spec)

    if self.__tool_spec__.binding.langflow is None:
      raise BadRequest('Missing langflow binding')
    
  
  def __repr__(self):
    return f"LangflowTool(name='{self.__tool_spec__.name}', description='{self.__tool_spec__.description}')"

  
  def __str__(self):
    return self.__repr__()
  
def validate_langflow_version(version_string: str) -> bool:
  version_nums = map(int, re.findall(r"\d+",version_string))
  for i,n in enumerate(version_nums):
    if i >= len(MIN_LANGFLOW_VERSION) or MIN_LANGFLOW_VERSION[i] < n:
      break
    if MIN_LANGFLOW_VERSION[i] > n:
      return False
  return True


def extract_langflow_nodes(tool_definition: dict, node_type: str) -> dict:
  return [n for n in tool_definition.get('data',{}).get('nodes',{}) if n.get('data',{}).get('type') == node_type]

def langflow_input_schema(tool_definition: dict = None) -> ToolRequestBody:
  
  chat_input_nodes = extract_langflow_nodes(tool_definition=tool_definition,node_type=LANGFLOW_CHAT_INPUT_LABEL)

  if len(chat_input_nodes) < 1:
    raise ValueError(f"No '{LANGFLOW_CHAT_INPUT_LABEL}' node found in langflow tool")
  if len(chat_input_nodes) > 1:
    raise ValueError(f"Too many '{LANGFLOW_CHAT_INPUT_LABEL}' nodes found in langlow tool")

  input_description = chat_input_nodes[0].get("data",{}).get("node",{}).get("description","")

  return ToolRequestBody(
    type= "object",
    properties= {
      "input": {
        "description": input_description,
        "type": "string"
      }
    },
    required= ["input"]
  )

def langflow_output_schema(tool_definition: dict = None):

  chat_output_nodes = extract_langflow_nodes(tool_definition=tool_definition,node_type=LANGFLOW_CHAT_OUTPUT_LABEL)

  if len(chat_output_nodes) < 1:
    raise ValueError(f"No '{LANGFLOW_CHAT_OUTPUT_LABEL}' node found in langflow tool")
  if len(chat_output_nodes) > 1:
    output_description = ""
  else:
    output_description = chat_output_nodes[0].get("data",{}).get("node",{}).get("description","")

  return ToolResponseBody(
    description=output_description,
    type= "string"
  )
  
def create_langflow_tool(
    tool_definition: dict,
    connections: dict = None,
    ) -> LangflowTool:

  name = tool_definition.get('name')
  if not name:
    raise ValueError('Provided tool definition does not have a name')
  
  if VALID_NAME_PATTERN.match(name) is None:
    raise ValueError(f"Langflow tool name contains unsupported characters. Only alphanumeric characters and underscores are allowed, and must not start with a number or underscore.")
  
  description = tool_definition.get('description')
  if not description:
    raise ValueError('Provided tool definition does not have a description')
  
  langflow_id = tool_definition.get('id')

  langflow_version = tool_definition.get('last_tested_version')
  if not langflow_version:
    raise ValueError('No langflow version detected in tool definition')
  if not validate_langflow_version(langflow_version):
    raise ValueError(f"Langflow version is below minimum requirements, found '{langflow_version}', miniumum required version '{'.'.join(map(str,MIN_LANGFLOW_VERSION))}'")
  
  spec = ToolSpec(
    name=name,
    description=description,
    permission=ToolPermission('read_only')
  )

  spec.input_schema = langflow_input_schema(tool_definition=tool_definition)

  spec.output_schema = langflow_output_schema(tool_definition=tool_definition)

  spec.binding = ToolBinding(
    langflow=LangflowToolBinding(
      langflow_id=langflow_id,
      langflow_version=langflow_version,
      connections=connections
    )
  )

  return LangflowTool(spec)