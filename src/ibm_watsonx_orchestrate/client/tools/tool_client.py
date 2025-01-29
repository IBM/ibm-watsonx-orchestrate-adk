from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient


class ToolClient(BaseAPIClient):
    """
    Client to handle CRUD operations for Expert Agent endpoint
    """

    def create(self, payload: dict) -> dict:
        return self._post("/tools", data=payload)

    def get(self) -> dict:
        return self._get("/tools")

    def update(self, agent_id: str, data: dict) -> dict:
        return self._put(f"/tools/{agent_id}", data=data)

    def delete(self, agent_id: str) -> dict:
        return self._delete(f"/tools/{agent_id}")