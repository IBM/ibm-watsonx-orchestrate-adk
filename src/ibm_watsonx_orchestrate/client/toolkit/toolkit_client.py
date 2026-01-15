from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient, ClientAPIException
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from typing_extensions import List
import os
import json

class ToolKitClient(BaseWXOClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get(self) -> List[dict]:
        return self._get("/toolkits")


    # POST /toolkits/prepare/list-tools
    def list_tools(self, zip_file_path: str, command: str, args: List[str]) -> List[str]:
        """
        List the available tools inside the MCP server
        """

        filename = os.path.basename(zip_file_path)

        list_toolkit_obj = {
            "source": "files",
            "command": command,
            "args": args,
        }

        with safe_open(zip_file_path, "rb") as f:
            files = {
                "list_toolkit_obj": (None, json.dumps(list_toolkit_obj), "application/json"),
                "file": (filename, f, "application/zip"),
            }

            response = self._post("/toolkits/prepare/list-tools", files=files)


        return response.get("tools", [])


    # POST /api/v1/orchestrate/toolkits
    def create_toolkit(self, payload) -> dict:
        """
        Creates new toolkit metadata
        """
        try:
            return self._post("/toolkits", data=payload)

        except ClientAPIException as e:
            if e.response.status_code == 400 and "already exists" in e.response.text:
                raise ClientAPIException(
                    status_code=400,
                    message=f"There is already a Toolkit with the same name that exists for this tenant."
                )
            raise(e)
    
    # POST /toolkits/{toolkit-id}/upload
    def upload(self, toolkit_id: str, zip_file_path: str) -> dict:
        """
        Upload zip file to the toolkit.
        """
        filename = os.path.basename(zip_file_path)
        with safe_open(zip_file_path, "rb") as f:
            files = {
                "file": (filename, f, "application/zip", {"Expires": "0"})
            }
            return self._post(f"/toolkits/{toolkit_id}/upload", files=files)
        
    # DELETE /toolkits/{toolkit-id} 
    def delete(self, toolkit_id: str) -> dict:
        return self._delete(f"/toolkits/{toolkit_id}")


    def get_draft_by_name(self, toolkit_name: str) -> List[dict]:
        return self.get_drafts_by_names([toolkit_name])

    def get_drafts_by_names(self, toolkit_names: List[str]) -> List[dict]:
        formatted_toolkit_names = [f"names={x}" for x in toolkit_names]

        return self._get(f"/toolkits?{'&'.join(formatted_toolkit_names)}")

    
    def get_draft_by_id(self, toolkit_id: str) -> dict:
        if toolkit_id is None:
            return ""
        else:
            try:
                toolkit = self._get(f"/toolkits/{toolkit_id}")
                return toolkit
            except ClientAPIException as e:
                if e.response.status_code == 404 and "not found with the given name" in e.response.text:
                    return ""
                raise(e)
    
    def download_artifact(self, toolkit_id: str) -> bytes:
        response = self._get(f"/toolkits/{toolkit_id}/download", return_raw=True)
        return response.content

