from enum import Enum
import json
import re

from pydantic import BaseModel
import rich

from ibm_watsonx_orchestrate.agent_builder.connections.types import ConnectionSecurityScheme
from ibm_watsonx_orchestrate.langflow.langflow_utils import parse_langflow_model
from .base_tool import BaseTool
from .types import LangflowToolBinding, ToolBinding, ToolPermission, ToolRequestBody, ToolResponseBody, ToolSpec
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

MIN_LANGFLOW_VERSION = [1,5,0]
LANGFLOW_CHAT_INPUT_LABEL = "ChatInput"
LANGFLOW_CHAT_OUTPUT_LABEL = "ChatOutput"
VALID_NAME_PATTERN = re.compile("^[a-zA-Z](\\w|_)+$")

class LangflowToolSource(str,Enum):
  ORCHESTRATE = 'orchestrate'
  LANGFLOW = 'langflow'

class LangflowTool(BaseTool):
  # additional python module requirements for langflow based tools
  requirements: list[str] = []

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
    show_details: bool = True
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
  
  # find all the component in Langflow and display its credential
  langflow_spec = parse_langflow_model(tool_definition)
  if langflow_spec:

    if show_details:
      rich.print(f"[bold white]Langflow version used: {langflow_version}[/bold white]")
      rich.print("Please ensure this flow is compatible with the Langflow version bundled in ADK.")
      rich.print("\nLangflow components:")

    table = rich.table.Table(show_header=True, header_style="bold white", show_lines=True)
    column_args = {
      "ID": {},
      "Name": {},
      "Credentials": {},
      "Requirements": {}
    }
    for column in column_args:
        table.add_column(column,**column_args[column])

    requirements = set()
    api_key_not_set = False
    for component in langflow_spec.components:
      if component.credentials and len(component.credentials) > 0:
        # create a command separated list with newline
        component_creds = None
        for k, v in component.credentials.items():
          if v is None or v == "":
            v = 'NOT SET'
            api_key_not_set = True
          if component_creds is None:
            component_creds = f"{k} {v}"
          else:
            component_creds += "\n" + f"{k} {v}"
      else:
        component_creds = "N/A"

      if component.requirements and len(component.requirements) > 0:
        # create a command separated list with newline
        component_req = "\n".join([f"{k}" for k in component.requirements])
        for r in component.requirements:
          requirements.add(r)
      else:
        component_req = "N/A"
      table.add_row(component.id,component.name,component_creds,component_req)
      
    if show_details:
      rich.print(table)

      rich.print("[bold yellow]Tip:[/bold yellow] Langflow tool might require additional python modules.  Identified requirements will be added.")
      rich.print("[bold yellow]Tip:[/bold yellow] Avoid hardcoding sensitive values. Use Orchestrate connections to manage secrets securely.")
      if api_key_not_set:
        rich.print("[bold yellow]Warning:[/bold yellow] Some required api key(s) were not set in the flow. Please adjust the flow to include them.")
      rich.print("Ensure each credential follows the <app-id>_<variable> naming convention within the Langflow model.")

      for connection in connections:
          rich.print(f"* Connection: {connection} → Suggested naming: {connection}_<variable>")

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

  tool = LangflowTool(spec=spec)
  tool.requirements = requirements
  return tool