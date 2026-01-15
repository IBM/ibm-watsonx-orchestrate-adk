from typing import Literal
from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient, ClientAPIException
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from typing_extensions import List

class ToolClient(BaseWXOClient):
    """
    Client to handle CRUD operations for Tool endpoint
    """

    def create(self, payload: dict) -> dict:
        return self._post("/tools", data=payload)

    def get(self) -> dict:        
        return self._get("/tools")

    def update(self, agent_id: str, data: dict) -> dict:
        return self._put(f"/tools/{agent_id}", data=data)

    def delete(self, tool_id: str) -> dict:
        return self._delete(f"/tools/{tool_id}")

    def upload_tools_artifact(self, tool_id: str, file_path: str) -> dict:
        return self._post(f"/tools/{tool_id}/upload", files={"file": (f"{tool_id}.zip", safe_open(file_path, "rb"), "application/zip", {"Expires": "0"})})

    def download_tools_artifact(self, tool_id: str) -> bytes:
        response = self._get(f"/tools/{tool_id}/download", return_raw=True)
        return response.content
    
    def download_tools_json(self, tool_id: str) -> dict:
        return self.download_tools_artifact(tool_id)

    def get_draft_by_name(self, tool_name: str) -> List[dict]:
        return self.get_drafts_by_names([tool_name])

    def get_drafts_by_names(self, tool_names: List[str]) -> List[dict]:
        formatted_tool_names = [f"names={x}" for x in tool_names]
        return self._get(f"/tools?{'&'.join(formatted_tool_names)}")
    
    def get_draft_by_id(self, tool_id: str) -> dict | Literal[""]:
        if tool_id is None:
            return ""
        else:
            try:
                tool = self._get(f"/tools/{tool_id}")
                return tool
            except ClientAPIException as e:
                if e.response.status_code == 404 and "not found with the given name" in e.response.text:
                    return ""
                raise(e)
    
    def get_drafts_by_ids(self, tool_ids: List[str]) -> List[dict]:
        formatted_tool_ids = [f"ids={x}" for x in tool_ids]
        return self._get(f"/tools?{'&'.join(formatted_tool_ids)}")
