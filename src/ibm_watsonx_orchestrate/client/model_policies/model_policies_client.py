from typing import List

from pydantic import ValidationError
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient, ClientAPIException

import logging

from ibm_watsonx_orchestrate.agent_builder.model_policies.types import ModelPolicy

logger = logging.getLogger(__name__)



class ModelPoliciesClient(BaseAPIClient):
    """
    Client to handle CRUD operations for ModelPolicies endpoint
    """
    # POST api/v1/model_policy
    def create(self, model: ModelPolicy) -> None:
        self._post("/model_policy", data=model.model_dump(exclude_none=True))
    
    # PUT api/v1/model_policy/{model_policy_id}
    def update(self, model_policy_id: str, model: ModelPolicy) -> None:
        self._put(f"/model_policy/{model_policy_id}", data=model.model_dump(exclude_none=True))

    # DELETE api/v1/model_policy/{model_policy_id}
    def delete(self, model_policy_id: str) -> dict:
        return self._delete(f"/model_policy/{model_policy_id}")

    # GET /api/v1/model_policy/{app_id}
    def get(self, model_policy_id: str):
        raise NotImplementedError


    # GET api/v1/model_policy
    def list(self) -> List[ModelPolicy]:
        try:
            res = self._get(f"/model_policy")
            return [ModelPolicy.model_validate(policy) for policy in res]
        except ValidationError as e:
            logger.error("Received unexpected response from server")
            raise e
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return []
            raise e
    
    def get_drafts_by_names(self, policy_names: List[str]) -> List[ModelPolicy]:
        try:
            formatted_policy_names = [f'name={x}' for x  in policy_names]
            res = self._get(f"/model_policy?{'&'.join(formatted_policy_names)}")
            return [ModelPolicy.model_validate(conn) for conn in res]
        except ValidationError as e:
            logger.error("Received unexpected response from server")
            raise e
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return []
            raise e
    
    def get_draft_by_name(self, policy_name: str) -> ModelPolicy:
        return self.get_drafts_by_names([policy_name])




