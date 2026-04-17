from typing import List

from pydantic import ValidationError

from ibm_watsonx_orchestrate_core.types.model_selection import GetModelSelectionResponse, ModelSelectionSettings, ModelSelectionPatch
from ibm_watsonx_orchestrate_clients.common.base_client import BaseWXOClient, ClientAPIException

import logging

logger = logging.getLogger(__name__)


class ModelSelectionClient(BaseWXOClient):
    """
    Client to handle configuring default llm and denylist
    """

    def create(self, *args, **kwargs):
        raise NotImplementedError()

    def delete(self, *args, **kwargs):
        self._delete("/model-selection")

    # GET api/v1/model-selection
    def get(self):
        return GetModelSelectionResponse.model_validate(
            self._get("/model-selection")
        )

    # PUT api/v1/model-selection
    def replace(self, settings: ModelSelectionSettings) -> dict:
        return self._put("/model-selection", data=settings.model_dump(exclude_none=True))

    # PATCH api/v1/model-selection
    def update(self, settings_patch: ModelSelectionPatch) -> dict:
        return self._patch("/model-selection", data=settings_patch.model_dump(exclude_none=True))
