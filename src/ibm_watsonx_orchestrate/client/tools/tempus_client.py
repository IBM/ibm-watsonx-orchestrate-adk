from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient, ClientAPIException
from typing_extensions import List
from urllib.parse import urlparse, urlunparse
from ibm_cloud_sdk_core.authenticators import MCSPAuthenticator

DEFAULT_TEMPUS_PORT= 9044

class TempusClient(BaseAPIClient):
    """
    Client to handle CRUD operations for Tempus endpoint

    This may be temporary and may want to create a proxy API in wxo-server 
    to redirect to the internal tempus runtime, and add a new operation in the ToolClient instead
    """
    def __init__(self, base_url: str, api_key: str = None, is_local: bool = False, authenticator: MCSPAuthenticator = None):
        parsed_url = urlparse(base_url)
       
        # Reconstruct netloc with new port - use default above - eventually we need to open up a way through the wxo-server API
        new_netloc = f"{parsed_url.hostname}:{DEFAULT_TEMPUS_PORT}"

        # Replace netloc and rebuild the URL
        new_url = urlunparse(parsed_url._replace(netloc=new_netloc))
        # remove trailing slash

        super().__init__(
            base_url=new_url,
            api_key=api_key,
            is_local=is_local,
            authenticator=authenticator
        )
        
    def get_tempus_endpoint(self) -> str:
        """
        Returns the Tempus endpoint URL
        """
        return self.base_url
    def create_update_flow_model(self, flow_id: str, model: dict) -> dict:
        return self._post(f"/flow-models/{flow_id}", data=model)
    
    def run_flow(self, flow_id: str, input: dict) -> dict:
        return self._post(f"/flows/{flow_id}/versions/TIP/run", data=input)
    
    def arun_flow(self, flow_id: str, input: dict) -> dict:
        return self._post(f"/flows/{flow_id}/versions/TIP/run/async", data=input)

