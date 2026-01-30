from typing import Any
from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient, ClientAPIException
from typing_extensions import List
from urllib.parse import urlparse, urlunparse
from ibm_cloud_sdk_core.authenticators import MCSPAuthenticator

DEFAULT_TEMPUS_PORT= 9044

class TempusClient(BaseWXOClient):
    debug: bool = False # decide if debug mode should set

    """
    Client to handle CRUD operations for Tempus endpoint

    This may be temporary and may want to create a proxy API in wxo-server 
    to redirect to the internal tempus runtime, and add a new operation in the ToolClient instead
    """
    def __init__(self, base_url: str, api_key: str = None, is_local: bool = False, authenticator: MCSPAuthenticator = None, *args, **kwargs):
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
            authenticator=authenticator,
            *args,
            **kwargs
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
    
    def get_flow_model(self, flow_id: str, version: str = "TIP") -> dict:
        return self._get(f"/flow-models/{flow_id}/versions/{version}")

    def _get_headers(self) -> dict:
        '''
        if debug is True, set trace debug level 4 to get input and output data from task run
        '''
        headers: dict[Any, Any] = super()._get_headers()

        if self.debug:
            headers["x-ibm-flow-trace-debug-level"] = "4"
        
        return headers


