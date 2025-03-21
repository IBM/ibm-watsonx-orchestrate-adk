# from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient, ClientAPIException
# from typing_extensions import List


# class AssistantAgentClient(BaseAPIClient):
#     """
#     Client to handle CRUD operations for Assistant Agent endpoint
#     """

#     def create(self, payload: dict) -> dict:
#         return self._post("/assistants/watsonx", data=payload)

#     def get(self) -> dict:
#         return self._get("/assistants/watsonx")

#     def update(self, agent_id: str, data: dict) -> dict:
#         return self._patch(f"/assistants/watsonx/{agent_id}", data=data)

#     def delete(self, agent_id: str) -> dict:
#         return self._delete(f"/assistants/watsonx/{agent_id}")
    
#     def get_draft_by_name(self, agent_name: str) -> List[dict]:
#         try:
#             return self._get(f"/assistants/watsonx/?name={agent_name}")
#         except ClientAPIException as e:
#             if e.response.status_code == 404 and "watsonx assistant not found with the given name" in e.response.text:
#                 return None
#             raise(e)

#     def get_drafts_by_names(self, agent_names: List[str]) -> List[dict]:
#         agents = []
#         for name in agent_names:
#             draft_agent = self.get_draft_by_name(name)
#             if draft_agent:
#                 agents.append(self.get_draft_by_name(name))
#         return agents
