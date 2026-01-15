
import logging

from ibm_watsonx_orchestrate.cli.commands.langflow.utils import requires_langflow
from ibm_watsonx_orchestrate.client.langflow import LangflowFlowsClient
from ibm_watsonx_orchestrate.client.langflow.langflow_base_client import LangflowClient
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

logger = logging.getLogger(__name__)


def _is_langflow_tool(tool: dict):
  return not not tool.get('binding', {}).get('langflow')

class LangflowController:
  def __init__(self,**kwargs):
    self.__langflow_client = kwargs.get('langflow_client', None)
    self.__flows_client = kwargs.get('flows_client', None)
    self.__langflow_id_map = None

  @property
  def langflow_client(self):
    if not self.__langflow_client:
      self.__langflow_client = LangflowClient()
    return self.__langflow_client

  @property
  def flows_client(self):
    if not self.__flows_client:
      self.__flows_client = LangflowFlowsClient()
    return self.__flows_client
  
  @property
  def langflow_id_map(self):
    if not self.__langflow_id_map:
      self.__langflow_id_map = { tool.get('name'):tool.get('id') for tool in self._get_tools_from_langflow() }
    return self.__langflow_id_map

  ## Helpers
    
  def _get_langflow_version(self):
    return self.langflow_client.version()
      
  def _get_tools_from_langflow(self):
    return self.flows_client.get()

  def _get_tool_from_langflow(self, name: str):
    langflow_id = self._get_langflow_id_from_name(name)
    if langflow_id:
      langflow_tool = self.flows_client.get_flow_by_id(langflow_id)
      langflow_tool['last_tested_version'] = self._get_langflow_version()
      return langflow_tool

  def _get_langflow_id_from_name(self, name: str):
    return self.langflow_id_map.get(name)
  
  ## Controller 

  @requires_langflow
  def export_tool_from_langflow(self, name: str):
    if not name:
      raise BadRequest(f"Name is required to export a tools from langflow")
    
    langflow_tool_json = self._get_tool_from_langflow(name)

    if not langflow_tool_json:      
      raise BadRequest(f"Tool '{name}' was not found in langflow")
    else:
      logger.info(f"Tool '{name}' exported from langflow")

    return langflow_tool_json

