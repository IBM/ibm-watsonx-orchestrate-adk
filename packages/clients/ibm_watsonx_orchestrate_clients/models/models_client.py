from typing import List

from pydantic import ValidationError
from ibm_watsonx_orchestrate_clients.common.base_client import BaseWXOClient, ClientAPIException

import logging

from ibm_watsonx_orchestrate_core.types.models.types import ListVirtualModel, VirtualModel, ModelListEntry

logger = logging.getLogger(__name__)

CUSTOM_MODEL_TAG = "third party"
DEFAULT_MODEL_TAG = "default"
LLM_DISALLOWED_BY_ADMIN_TAG = "wxo-reserved-tag-admin-disallowed"
RECOMMENDED_LLM_TAG = "recommended"


class ModelsClient(BaseWXOClient):
    """
    Client to handle CRUD operations for Models endpoint
    """

    # POST api/v1/models
    def create(self, model: VirtualModel) -> None:
        self._post("/models", data=model.model_dump(exclude_none=True))

    # PUT api/v1/models/{models_id}
    def update(self, model_id: str, model: VirtualModel) -> None:
        self._put(f"/models/{model_id}", data=model.model_dump(exclude_none=True))

    # DELETE api/v1/models/{model_id}
    def delete(self, model_id: str) -> dict:
        return self._delete(f"/models/{model_id}")

    # GET /api/v1/models/{app_id}
    def get(self, model_id: str):
        raise NotImplementedError

    # GET api/v1/models
    # returns virtual models
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

    # GET api/v1/models/list
    # returns both virtual models + ootb models
    def list_all(self):
        try:
            return self._get("/models/list").get("resources", [])
        except ValidationError as e:
            logger.error("Received unexpected response from server")
            raise e
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return []
            raise e

    def get_drafts_by_names(self, model_names: List[str]) -> List[ListVirtualModel]:
        try:
            formatted_model_names = [f'name={x}' for x in model_names]
            res = self._get(f"/models?{'&'.join(formatted_model_names)}")
            return [ListVirtualModel.model_validate(conn) for conn in res]
        except ValidationError as e:
            logger.error("Received unexpected response from server")
            raise e
        except ClientAPIException as e:
            if e.response.status_code == 404:
                return []
            raise e

    def get_draft_by_name(self, model_name: str) -> List[ListVirtualModel]:
        return self.get_drafts_by_names([model_name])

