import os
import time
import logging
import requests
from enum import Enum

from pydantic import BaseModel
from typing_extensions import List, Optional

from ibm_watsonx_orchestrate_clients.common.utils import is_local_dev
from ibm_watsonx_orchestrate_clients.common.base_client import BaseWXOClient, ClientAPIException
from ibm_watsonx_orchestrate_core.utils.workspaces import (
    resolve_and_inject_workspace,
    add_workspace_query_param,
    convert_workspace_id_to_name
)


logger = logging.getLogger(__name__)

POLL_INTERVAL = 2
MAX_RETRIES = 150
try:
    MAX_RETRIES = int(os.environ.get("WXO_AGENT_DEPLOYMENT_TIMEOUT", MAX_RETRIES * 2)) // 2
except Exception as e:
    pass

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
        # Resolve workspace field and inject active workspace context
        payload = resolve_and_inject_workspace(payload)
        
        # Transform payload for API
        transformed_payload = transform_agents_from_flat_agent_spec(payload)
        
        response = self._post(self.base_endpoint, data=transformed_payload)
        return AgentUpsertResponse.model_validate(response)

    def get(self, workspace_id: Optional[str] = None, include_global: bool = True) -> dict:
        params = {'include_hidden': 'true'}
        
        # If workspace_id is explicitly provided, use it; otherwise use active workspace context
        if workspace_id is not None:
            params['workspace_id'] = workspace_id
        else:
            params = add_workspace_query_param(params)
        
        if include_global:
            params['include'] = "global"
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        agents = transform_agents_to_flat_agent_spec(self._get(f"{self.base_endpoint}?{query_string}"))
        
        # Convert workspace_id to workspace name in response
        if isinstance(agents, list):
            agents = [convert_workspace_id_to_name(agent) for agent in agents]
        else:
            agents = convert_workspace_id_to_name(agents)
        
        return agents

    def update(self, agent_id: str, data: dict, skip_workspace_injection: bool = False) -> AgentUpsertResponse:
        # Resolve workspace field and inject active workspace context
        # Skip injection for cross-workspace updates
        if not skip_workspace_injection:
            data = resolve_and_inject_workspace(data)
        
        # Transform payload for API
        transformed_payload = transform_agents_from_flat_agent_spec(data)
        
        response = self._patch(f"{self.base_endpoint}/{agent_id}", data=transformed_payload)
        return AgentUpsertResponse.model_validate(response)

    def delete(self, agent_id: str) -> dict:
        return self._delete(f"{self.base_endpoint}/{agent_id}")
    
    def get_draft_by_name(self, agent_name: str, workspace_id: Optional[str] = None, include_global: bool = True) -> List[dict]:
        return self.get_drafts_by_names([agent_name], workspace_id=workspace_id, include_global=include_global)

    def get_drafts_by_names(self, agent_names: List[str], workspace_id: Optional[str] = None, include_global: bool = True) -> List[dict]:
        formatted_agent_names = [f"names={x}" for x  in agent_names]
        params = {'include_hidden': 'true'}
        
        # If workspace_id is explicitly provided, use it; otherwise use active workspace context
        if workspace_id is not None:
            params['workspace_id'] = workspace_id
        else:
            # Add workspace filtering if applicable
            params = add_workspace_query_param(params)
        
        if include_global:
            params['include'] = "global"
        
        # Build query string with names and other params
        query_parts = formatted_agent_names + [f"{k}={v}" for k, v in params.items()]
        return transform_agents_to_flat_agent_spec(self._get(f"{self.base_endpoint}?{'&'.join(query_parts)}"))
    
    def get_draft_by_id(self, agent_id: str, workspace_id: Optional[str] = None, include_global: bool = True) -> dict | str:
        if agent_id is None:
            return ""
        else:
            try:
                # If workspace_id is explicitly provided, use it; otherwise use active workspace context
                if workspace_id is not None and not include_global:
                    params = {'workspace_id': workspace_id}

                    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
                    agent = transform_agents_to_flat_agent_spec(self._get(f"{self.base_endpoint}/{agent_id}?{query_string}"))
                else:
                    agent = transform_agents_to_flat_agent_spec(self._get(f"{self.base_endpoint}/{agent_id}"))
                return agent
            except ClientAPIException as e:
                if e.response.status_code == 404 and ("not found with the given name" in e.response.text or ("Agent" in e.response.text and "not found" in e.response.text)):
                    return ""
                raise(e)
    
    def get_drafts_by_ids(self, agent_ids: List[str], workspace_id: Optional[str] = None, include_global: bool = True) -> List[dict]:
        formatted_agent_ids = [f"ids={x}" for x  in agent_ids]
        params = {'include_hidden': 'true'}
        
        # If workspace_id is explicitly provided, use it; otherwise use active workspace context
        if workspace_id is not None:
            params['workspace_id'] = workspace_id
        else:
            params = add_workspace_query_param(params)
        
        if include_global:
            params["include"] = "global"
        
        # Build query string with ids and other params
        query_parts = formatted_agent_ids + [f"{k}={v}" for k, v in params.items()]
        return transform_agents_to_flat_agent_spec(self._get(f"{self.base_endpoint}?{'&'.join(query_parts)}"))

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
    
    def copy_agent(self, agent_id: str, destination_workspace_id: str, source_workspace_id: str) -> dict:
        """
        Copy an agent to a destination workspace asynchronously.
        
        copies all agent dependencies (tools, collaborators) automatically.
        
        Args:
            agent_id: Source agent UUID to copy
            destination_workspace_id: Destination workspace ID (use '00000000-0000-0000-0000-000000000001' for global)
            source_workspace_id: Source workspace ID (use '00000000-0000-0000-0000-000000000001' for global)
            
        Returns:
            dict with keys:
                - id: UUID of the newly created agent copy
                - message: Status message
                - status_endpoint: Endpoint to check copy operation status
        """
        payload = {
            "destination_workspace_id": destination_workspace_id,
            "source_workspace_id": source_workspace_id
        }
        
        response = self._post(f"{self.base_endpoint}/{agent_id}/copy", data=payload)
        return response
    
    def get_agent_copy_status(self, agent_id: str) -> dict:
        """
        Get the status of an agent copy operation.
        
        This endpoint is used to poll the status of an async agent copy operation.
        
        Args:
            agent_id: The ID of the newly created agent (returned from copy_agent)
        """
        return self._get(f"{self.base_endpoint}/{agent_id}/template-status")