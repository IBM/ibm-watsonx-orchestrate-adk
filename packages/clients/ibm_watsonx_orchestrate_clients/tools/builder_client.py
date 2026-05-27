from typing import Optional, Dict, Any, List, cast
import requests
from pydantic import BaseModel
from ibm_watsonx_orchestrate_clients.common.base_client import BaseWXOClient
from urllib.parse import urlparse, urlunparse
from ibm_cloud_sdk_core.authenticators import MCSPAuthenticator

DEFAULT_BUILDER_PORT = 4025


class TranslationExportResponse(BaseModel):
    content: str
    content_type: str
    url: str
    status_code: int


class BuilderClient(BaseWXOClient):
    """
    Client to handle translation operations for flow tools via the Builder API.
    
    This client provides methods to export and import translations for flows.
    Local: The Builder service runs on port 4025 (http://wxo-builder:4025)
    Remote: Uses api proxy endpoint (e.g., https://api.staging-wa.watson-orchestrate.ibm.com/{instance}/v1/)
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        is_local: bool = False,
        authenticator: Optional[MCSPAuthenticator] = None,
        *args,
        **kwargs
    ):
        parsed_url = urlparse(base_url)
       
        if is_local:
            new_netloc = f"{parsed_url.hostname}:{DEFAULT_BUILDER_PORT}"
            new_url = urlunparse(parsed_url._replace(netloc=new_netloc))
        else:
            new_url = base_url

        init_kwargs = {
            "base_url": new_url,
            "is_local": is_local,
            **kwargs
        }
        if api_key is not None:
            init_kwargs["api_key"] = api_key
        if authenticator is not None:
            init_kwargs["authenticator"] = authenticator

        super().__init__(**init_kwargs)
        
        # BaseWXOClient appends:
        # - Local: /v1 → we need /api/v1
        # - Remote: /v1/orchestrate → keep as is
        if self.is_local:
            # Change from /v1 to /api/v1 for local builder service
            self.base_url = self.base_url.replace('/v1', '/api/v1')

    
    def _get_csv(self, path: str, params: Optional[dict] = None, data=None) -> TranslationExportResponse:
        """Perform a GET request and require a CSV/text response."""
        url = f"{self.base_url}{path}"
        headers = self._get_headers()
        headers["Accept"] = "text/csv"

        from ibm_watsonx_orchestrate_clients.common.base_client import ssl_handler
        with ssl_handler():
            response = requests.get(url, headers=headers, params=params, data=data, verify=self.verify)

        self._check_response(response)

        content_type = response.headers.get('Content-Type', '')
        if 'text/csv' in content_type or 'text/plain' in content_type:
            return TranslationExportResponse(
                content=response.text,
                content_type=content_type,
                url=url,
                status_code=response.status_code
            )

        response_preview = response.text[:200].replace("\n", "\\n")
        raise ValueError(
            f"Expected CSV response from {url}, got Content-Type '{content_type}' "
            f"(status {response.status_code}). Response preview: {response_preview}"
        )
    
    def _post_csv(self, path: str, data: Optional[dict] = None, files: Optional[dict] = None) -> TranslationExportResponse:
        """Perform a POST request and require a CSV/text response."""
        url = f"{self.base_url}{path}"
        headers = self._get_headers()
        headers["Accept"] = "text/csv"

        from ibm_watsonx_orchestrate_clients.common.base_client import ssl_handler
        with ssl_handler():
            response = requests.post(url, headers=headers, json=data, files=files, verify=self.verify)

        self._check_response(response)

        content_type = response.headers.get('Content-Type', '')
        if 'text/csv' in content_type or 'text/plain' in content_type:
            return TranslationExportResponse(
                content=response.text,
                content_type=content_type,
                url=url,
                status_code=response.status_code
            )

        response_preview = response.text[:200].replace("\n", "\\n")
        raise ValueError(
            f"Expected CSV response from {url}, got Content-Type '{content_type}' "
            f"(status {response.status_code}). Response preview: {response_preview}"
        )
    
    def export_translations(
        self,
        flow_model: Optional[Dict[str, Any]] = None,
        flow_identifier: Optional[str] = None
    ) -> TranslationExportResponse:
        """
        Export translations for a flow tool.
        
        Full URLs:
        Local:
        - POST http://wxo-builder:4025/api/v1/flow-model/translations/export
        - POST http://wxo-builder:4025/api/v1/tools/{id}/flow/translations/export
        
        Remote (via API proxy):
        - POST https://.../instances/{id}/v1/orchestrate/flow-model/translations/export
        - POST https://.../instances/{id}/v1/orchestrate/flow-model/{id}/translations/export
        
        Args:
            flow_model: The flow model dictionary (when file is provided)
            flow_identifier: The identifier for the flow (name, ID, etc.) (when name is provided)
            
        Returns:
            Translation export response including CSV content and response metadata
        """
        if flow_model:
            # POST endpoint for flow_model - sends JSON, receives CSV
            if self.is_local:
                # Local: base_url = http://wxo-builder:4025/api/v1
                endpoint = "/flow-model/translations/export"
            else:
                # Remote: base_url = https://.../instances/{id}/v1/orchestrate
                endpoint = "/flow-model/translations/export"
            full_url = f"{self.base_url}{endpoint}"
            print(f"[DEBUG] export_translations (flow_model): POST {full_url}")
            return self._post_csv(endpoint, data=flow_model)
        elif flow_identifier:
            # POST endpoint for flow_identifier - receives CSV
            if self.is_local:
                # Local: base_url = http://wxo-builder:4025/api/v1
                endpoint = f"/tools/{flow_identifier}/flow/translations/export"
                full_url = f"{self.base_url}{endpoint}"
            else:
                # Remote: base_url = https://.../instances/{id}/v1/orchestrate
                # API proxy routes /flow-model/{id}/... to backend /tools/{id}/flow/...
                endpoint = f"/flow-model/{flow_identifier}/translations/export"
                full_url = f"{self.base_url}{endpoint}"
            print(f"[DEBUG] export_translations (flow_identifier): GET {full_url}")

            return self._get_csv(endpoint)
        else:
            raise ValueError("Either flow_model or flow_identifier must be provided")
    
    def import_translations(
        self,
        tool_identifier: str,
        csv_contents: List[str]
    ) -> Dict[str, Any]:
        """
        Import translations for a flow tool from CSV content.
        
        Full URLs:
        Local:
        - PUT http://wxo-builder:4025/api/v1/tools/{id}/flow/translations/import
        
        Remote (via API proxy):
        - PUT https://.../instances/{id}/v1/orchestrate/flow-model/{id}/translations/import
        
        Args:
            tool_identifier: The tool ID for the flow
            csv_contents: List of CSV content strings (each string is a row)
            
        Returns:
            Dictionary containing the result of the import operation
        """
        # Construct the endpoint
        if self.is_local:
            # Local: base_url = http://wxo-builder:4025/api/v1
            endpoint = f"/tools/{tool_identifier}/flow/translations/import"
        else:
            # Remote: base_url = https://.../instances/{id}/v1/orchestrate
            # API proxy routes /flow-model/{id}/... to backend /tools/{id}/flow/...
            endpoint = f"/flow-model/{tool_identifier}/translations/import"
        
        full_url = f"{self.base_url}{endpoint}"
        print(f"[DEBUG] import_translations: PUT {full_url}")
        
        # Prepare the payload matching the API specification
        payload = {
            "csvContents": csv_contents
        }
        
        # Use the parent class _put method
        return self._put(endpoint, data=payload)
