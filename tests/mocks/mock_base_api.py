from typing import List
from unittest import mock

from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient
from pydantic import BaseModel


class MockListConnectionResponse(BaseModel):
    connection_id: str

def get_application_connections_mock():
    create = mock.MagicMock()
    delete = mock.MagicMock()
    get = mock.MagicMock()
    get_draft_by_app_id = mock.MagicMock()
    get_draft_by_app_ids = mock.MagicMock()

    class ApplicationConnectionsClientMock(BaseAPIClient):
        def __init__(self, base_url: str):
            super().__init__(base_url)

        def create(self, *args, **kwargs):
            return create(*args, **kwargs)

        def delete(self, *args, **kwargs):
            return delete(*args, **kwargs)

        def update(self, *args, **kwargs):
            pass

        def get_draft_by_app_id(self, *args, **kwargs):
            return get_draft_by_app_id(*args,**kwargs)

        def get_draft_by_app_ids(self, *args, **kwargs):
            return get_draft_by_app_ids(*args,**kwargs)

        def get(self, *args, **kwargs):
            return get(*args, **kwargs)

    return ApplicationConnectionsClientMock, create, delete, get, get_draft_by_app_id, get_draft_by_app_ids


def get_analytics_llm_mock():
    get = mock.MagicMock()
    update = mock.MagicMock()
    delete = mock.MagicMock()

    class AnalyticsLLMClientMock(BaseAPIClient):
        def __init__(self, base_url: str):
            super().__init__(base_url)

        def create(self):
            raise RuntimeError('unimplemented')

        def get(self):
            return get()

        def update(self, request):
            return update(request)

        def delete(self, *args, **kwargs):
            return delete()


    return AnalyticsLLMClientMock, update, delete, get

def instantiate_client_mock(client):
    return client(base_url='/')