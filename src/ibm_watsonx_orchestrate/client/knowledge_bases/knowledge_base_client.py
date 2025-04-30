from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient
import json
from typing_extensions import List
from ibm_watsonx_orchestrate.client.utils import is_local_dev



class KnowledgeBaseClient(BaseAPIClient):
    """
    Client to handle CRUD operations for Native Knowledge Base endpoint
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_endpoint = "/orchestrate/knowledge-bases" if is_local_dev(self.base_url) else "/knowledge-bases"

    def create(self, payload: dict) -> dict:
        return self._post_form_data(f"{self.base_endpoint}/documents", data={ "knowledge_base" : json.dumps(payload) })
    
    def create_built_in(self, payload: dict, files: list) -> dict:
        return self._post_form_data(f"{self.base_endpoint}/documents", data={ "knowledge_base" : json.dumps(payload) }, files=files)

    def get(self) -> dict:
        return self._get(self.base_endpoint)
    
    def get_by_name(self, name: str) -> List[dict]:
        kbs = self.get_by_names([name])
        return None if len(kbs) == 0 else kbs[0]
    
    def get_by_id(self, knowledge_base_id: str) -> dict:
        return self._get(f"{self.base_endpoint}/{knowledge_base_id}")

    def get_by_names(self, name: List[str]) -> List[dict]:
        formatted_names = [f"names={x}" for x in name]
        return self._get(f"{self.base_endpoint}?{'&'.join(formatted_names)}")
    
    def status(self, knowledge_base_id: str) -> dict:
        return self._get(f"{self.base_endpoint}/{knowledge_base_id}/status")

    def update(self, knowledge_base_id: str, payload: dict) -> dict:
        return self._patch_form_data(f"{self.base_endpoint}/{knowledge_base_id}/documents", data={ "knowledge_base" : json.dumps(payload) })
    
    def update_with_documents(self, knowledge_base_id: str, payload: dict, files: list) -> dict:
        return self._patch_form_data(f"{self.base_endpoint}/{knowledge_base_id}/documents", data={ "knowledge_base" : json.dumps(payload) }, files=files)

    def delete(self, knowledge_base_id: str,) -> dict:
        return self._delete(f"{self.base_endpoint}/{knowledge_base_id}")
        
    

    
