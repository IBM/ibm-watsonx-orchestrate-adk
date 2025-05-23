from typing import List

from pydantic import ValidationError
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient, ClientAPIException

import logging

from ibm_watsonx_orchestrate.client.model_policies.types import ModelPolicy
from ibm_watsonx_orchestrate.client.models.types import ListVirtualModel, CreateVirtualModel

logger = logging.getLogger(__name__)





class ModelPoliciesClient(BaseAPIClient):
    """
    Client to handle CRUD operations for ModelPolicies endpoint
    """
    # POST api/v1/model_policy
    def create(self, model: ModelPolicy) -> None:
        self._post("/model_policy", data=model.model_dump())

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


