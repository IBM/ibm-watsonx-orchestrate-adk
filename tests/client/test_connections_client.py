"""Unit tests for ConnectionsClient response normalization."""
from unittest import mock

import pytest

from ibm_watsonx_orchestrate_clients.connections.connections_client import ConnectionsClient


@pytest.fixture
def client():
    return ConnectionsClient(base_url="https://example.com", api_key="k", is_local=False)


def test_list_accepts_wrapped_applications_shape(client):
    payload = {
        "applications": [
            {
                "connection_id": "c1",
                "app_id": "app1",
                "environment": "draft",
                "security_scheme": "key_value_creds",
            }
        ]
    }
    with mock.patch.object(client, "_get", return_value=payload):
        rows = client.list()
    assert len(rows) == 1
    assert rows[0].app_id == "app1"


def test_list_accepts_top_level_array(client):
    payload = [
        {
            "connection_id": "c1",
            "app_id": "app1",
            "environment": "draft",
            "security_scheme": "bearer_token",
        }
    ]
    with mock.patch.object(client, "_get", return_value=payload):
        rows = client.list()
    assert len(rows) == 1
    assert rows[0].security_scheme.value == "bearer_token"


def test_list_empty_for_unknown_shape(client):
    with mock.patch.object(client, "_get", return_value=None):
        rows = client.list()
    assert rows == []
