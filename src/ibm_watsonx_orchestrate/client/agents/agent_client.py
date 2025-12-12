from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient, ClientAPIException
from typing_extensions import List, Optional
from enum import Enum
import os

from ibm_watsonx_orchestrate.client.utils import is_local_dev
from pydantic import BaseModel
import requests
import time
import logging

logger = logging.getLogger(__name__)

POLL_INTERVAL = 2
MAX_RETRIES = 10

class ReleaseMode(str, Enum):
    DEPLOY = "deploy"
    UNDEPLOY = "undeploy"

class ReleaseStatus(str, Enum):
    SUCCESS = "success"
    NONE = "none"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"

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
        elif key == "icon":
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
        
        elif key == "icon":
            transformed[key] = value
            
    transformed.pop("additional_properties",None)

    return transformed

class AgentUpsertResponse(BaseModel):
    id: Optional[str] = None
    warning: Optional[str] = None

class AgentClient(BaseWXOClient):
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
    
    def get_draft_by_id(self, agent_id: str) -> dict | str:
        if agent_id is None:
            return ""
        else:
            try:
                agent = transform_agents_to_flat_agent_spec(self._get(f"{self.base_endpoint}/{agent_id}"))
                return agent
            except ClientAPIException as e:
                if e.response.status_code == 404 and ("not found with the given name" in e.response.text or ("Agent" in e.response.text and "not found" in e.response.text)):
                    return ""
                raise(e)
    
    def get_drafts_by_ids(self, agent_ids: List[str]) -> List[dict]:
        formatted_agent_ids = [f"ids={x}" for x  in agent_ids]
        return transform_agents_to_flat_agent_spec(self._get(f"{self.base_endpoint}?{'&'.join(formatted_agent_ids)}&include_hidden=true"))

    def poll_release_status(self, agent_id: str, environment_id: str, mode: str = "deploy") -> bool:
        expected_status = {
            ReleaseMode.DEPLOY: ReleaseStatus.SUCCESS,
            ReleaseMode.UNDEPLOY: ReleaseStatus.NONE
        }[mode]

        for attempt in range(MAX_RETRIES):
            try:
                response = self._get(
                    f"{self.base_endpoint}/{agent_id}/releases/status?environment_id={environment_id}"
                )
            except Exception as e:
                logger.error(f"Polling for Deployment/Undeployment failed on attempt {attempt + 1}: {e}")
                return False

            if not isinstance(response, dict):
                logger.warning(f"Invalid response format: {response}")
                return False
            
            status = response.get("deployment_status")

            if status == expected_status:
                return True
            elif status == "failed":
                return False
            elif status == "in_progress":
                pass

            time.sleep(POLL_INTERVAL)

        logger.warning(f"{mode.capitalize()} status polling timed out")
        return False

    def deploy(self, agent_id: str, environment_id: str) -> bool:
        self._post(f"{self.base_endpoint}/{agent_id}/releases", data={"environment_id": environment_id})
        return self.poll_release_status(agent_id, environment_id, mode=ReleaseMode.DEPLOY)

    def undeploy(self, agent_id: str, version: str, environment_id: str) -> bool:
        self._post(f"{self.base_endpoint}/{agent_id}/releases/{version}/undeploy")
        return self.poll_release_status(agent_id, environment_id, mode=ReleaseMode.UNDEPLOY)
    
    def get_environments_for_agent(self, agent_id: str):
        return self._get(f"{self.base_endpoint}/{agent_id}/environment")

    def connect_connections(self, agent_id: str, connection_ids: List[str]) -> dict:
        """
        Connect connections to an agent using PATCH endpoint.
        
        Args:
            agent_id: The ID of the agent to connect connections to
            connection_ids: List of connection UUIDs to connect
            
        Returns:
            Response from the PATCH request
        """
        return self._patch(f"{self.base_endpoint}/{agent_id}", data={"connection_ids": connection_ids})
    
    def upload_agent_artifact(self, agent_id: str, file_path: str) -> dict:
        """
        Upload a custom file artifact for an agent.
        
        Args:
            agent_id: The ID of the agent
            file_path: Path to the file to upload
            
        Returns:
            Response from the upload endpoint
        """
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            files = {
                "file": (filename, f, "application/zip", {"Expires": "0"})
            }
            return self._post(f"{self.base_endpoint}/{agent_id}/upload", files=files)
    
    def download_agent_artifact(self, agent_id: str) -> bytes:
        """
        Download a custom agent package (zip file).
        Only works for custom agents.
        
        Args:
            agent_id: The ID of the custom agent
            
        Returns:
            The zip file content as bytes
        """
        response: requests.Response = self._get(f"{self.base_endpoint}/{agent_id}/download", return_raw=True)  # type: ignore
        return response.content
    
