from ibm_watsonx_orchestrate_clients.common.base_client import BaseWXOClient


class BaseAgenticClient(BaseWXOClient):
    """
    Base client for all Agentic SDK services
    
    Handles common URL transformations for agentic services that use /api/v1 prefix
    instead of the standard /v1/orchestrate or /v1 paths.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._transform_base_url()
    
    def _transform_base_url(self):
        """Transform base URL to use /api/v1 prefix for agentic services"""
        if self.is_local:
            self.base_url = self.base_url.replace("/v1", "/api/v1")
        else:
            self.base_url = self.base_url.replace("/v1/orchestrate", "/api/v1")
