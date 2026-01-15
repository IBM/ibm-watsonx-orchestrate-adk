import logging
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict

from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient

logger = logging.getLogger(__name__)


class AnalyticsLLMUpsertToolIdentifier(str, Enum):
    LANGFUSE = 'langfuse'


class AnalyticsLLMResponse(BaseModel):
    status: str


class AnalyticsLLMConfig(BaseModel):
    model_config = ConfigDict(extra='allow')
    project_id: str = 'default'
    host_uri: str
    tool_identifier: AnalyticsLLMUpsertToolIdentifier = AnalyticsLLMUpsertToolIdentifier.LANGFUSE
    mask_pii: bool = False
    config_json: dict

class AnalyticsLLMClient(BaseWXOClient):
    """
    Client to handle CRUD operations for Analytics LLM Endpoint
    """
    def create(self):
        raise RuntimeError('unimplemented')

    def get(self) -> AnalyticsLLMConfig:
        response = self._get(f"/analytics/llm")

        return AnalyticsLLMConfig.model_validate(response)

    def update(self, request: AnalyticsLLMConfig) -> AnalyticsLLMResponse:
        response = self._put('/analytics/llm', request.model_dump())
        return AnalyticsLLMResponse.model_validate(response)

    def delete(self) -> AnalyticsLLMResponse:
        response = self._delete('/analytics/llm')
        return AnalyticsLLMResponse.model_validate(response)
