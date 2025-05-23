from typing import List

from pydantic import ValidationError
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient, ClientAPIException

import logging

from ibm_watsonx_orchestrate.client.models.types import ListVirtualModel, CreateVirtualModel

logger = logging.getLogger(__name__)





class ModelsClient(BaseAPIClient):
    """
    Client to handle CRUD operations for Models endpoint
    """
    # POST api/v1/models
    def create(self, model: CreateVirtualModel) -> None:
        self._post("/models", data=model.model_dump())

    # DELETE api/v1/models/{model_id}
    def delete(self, model_id: str) -> dict:
        return self._delete(f"/models/{model_id}")

    # GET /api/v1/models/{app_id}
    def get(self, model_id: str):
        raise NotImplementedError


    # GET api/v1/models
    def list(self) -> List[ListVirtualModel]:
        try:
            res = self._get(f"/models")
            return [ListVirtualModel.model_validate(conn) for conn in res]
        except ValidationError as e:
            logger.error("Received unexpected response from server")
            raise e
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return []
            raise e


