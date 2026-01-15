
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient

LANGFLOW_BASE_URL = "http://localhost:7861"

class BaseLangflowClient(BaseAPIClient):

  def __init__(self, api_key = None, verify = None, authenticator = None):
    super().__init__(base_url=LANGFLOW_BASE_URL, api_key=api_key, verify=verify, authenticator=authenticator)
    self.base_url += "/api"


class LangflowClient(BaseLangflowClient):

  def version(self):
    return self._get("/v1/version").get('version')
  
  def main_version(self):
    return self._get("/v1/version").get('main_version')
  
  def package(self):
    return self._get("/v1/version").get('package')


