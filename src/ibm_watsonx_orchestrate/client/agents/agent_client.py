from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient, ClientAPIException
from typing_extensions import List, Optional
from ibm_watsonx_orchestrate.client.utils import is_local_dev
from pydantic import BaseModel

def transform_agents_from_flat_agent_spec(agents: dict | list[dict] ) -> dict | list[dict]:
    if isinstance(agents,list):
        new_agents = []
        for agent in agents:
            new_agents.append(_transform_agent_from_flat_agent_spec(agent))
        agents = new_agents
    else:
        agents = _transform_agent_from_flat_agent_spec(agents)
    
    return agents


def _transform_agent_from_flat_agent_spec(agent_spec: dict ) -> dict:
    transformed = {"additional_properties": {}}
    for key,value in agent_spec.items():
        if key == "starter_prompts":
            if value:
                value.pop("is_default_prompts",None)
                value["customize"] = value.pop("prompts", [])

            transformed["additional_properties"] |= { key: value }
            
        elif key == "welcome_content":
            if value:
                value.pop("is_default_message", None)

            transformed["additional_properties"] |= { key: value }

        else:
            transformed |= { key: value }

    return transformed

def transform_agents_to_flat_agent_spec(agents: dict | list[dict] ) -> dict | list[dict]:
    if isinstance(agents,list):
        new_agents = []
        for agent in agents:
            new_agents.append(_transform_agent_to_flat_agent_spec(agent))
        agents = new_agents
    else:
        agents = _transform_agent_to_flat_agent_spec(agents)

    return agents

def _transform_agent_to_flat_agent_spec(agent_spec: dict ) -> dict:
    additional_properties = agent_spec.get("additional_properties", None)
    if not additional_properties:
        return agent_spec
    
    transformed = agent_spec
    for key,value in additional_properties.items():
        if key == "starter_prompts":
            if value:
                value["is_default_prompts"] = False
                value["prompts"] = value.pop("customize", [])

            transformed[key] = value
            
        elif key == "welcome_content":
            if value:
             value["is_default_message"] = False
            
            transformed[key] = value
            
    transformed.pop("additional_properties",None)

    return transformed

class AgentUpsertResponse(BaseModel):
    id: Optional[str] = None
    warning: Optional[str] = None

class AgentClient(BaseAPIClient):
    """
    Client to handle CRUD operations for Native Agent endpoint
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_endpoint = "/orchestrate/agents" if is_local_dev(self.base_url) else "/agents"


    def create(self, payload: dict) -> AgentUpsertResponse:
        response = self._post(self.base_endpoint, data=transform_agents_from_flat_agent_spec(payload))
        return AgentUpsertResponse.model_validate(response)

    def get(self) -> dict:
        return transform_agents_to_flat_agent_spec(self._get(f"{self.base_endpoint}?include_hidden=true"))

    def update(self, agent_id: str, data: dict) -> AgentUpsertResponse:
        response = self._patch(f"{self.base_endpoint}/{agent_id}", data=transform_agents_from_flat_agent_spec(data))
        return AgentUpsertResponse.model_validate(response)

    def delete(self, agent_id: str) -> dict:
        return self._delete(f"{self.base_endpoint}/{agent_id}")
    
    def get_draft_by_name(self, agent_name: str) -> List[dict]:
        return self.get_drafts_by_names([agent_name])

    def get_drafts_by_names(self, agent_names: List[str]) -> List[dict]:
        formatted_agent_names = [f"names={x}" for x  in agent_names]
        return transform_agents_to_flat_agent_spec(self._get(f"{self.base_endpoint}?{'&'.join(formatted_agent_names)}&include_hidden=true"))
    
    def get_draft_by_id(self, agent_id: str) -> List[dict]:
        if agent_id is None:
            return ""
        else:
            try:
                agent = transform_agents_to_flat_agent_spec(self._get(f"{self.base_endpoint}/{agent_id}"))
                return agent
            except ClientAPIException as e:
                if e.response.status_code == 404 and "not found with the given name" in e.response.text:
                    return ""
                raise(e)
    
    def get_drafts_by_ids(self, agent_ids: List[str]) -> List[dict]:
        formatted_agent_ids = [f"ids={x}" for x  in agent_ids]
        return transform_agents_to_flat_agent_spec(self._get(f"{self.base_endpoint}?{'&'.join(formatted_agent_ids)}&include_hidden=true"))
    
