from unittest import mock

from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient


def get_application_connections_mock():
    create = mock.MagicMock()
    delete = mock.MagicMock()

    class ApplicationConnectionsClientMock(BaseAPIClient):
        def __init__(self, base_url: str):
            super().__init__(base_url)


        def create(self, *args, **kwargs):
            return create(*args, **kwargs)

        def delete(self, *args, **kwargs):
            return delete(*args, **kwargs)

        def update(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            pass

    return ApplicationConnectionsClientMock, create, delete

def instantiate_client_mock(client):
    return client(base_url='/')