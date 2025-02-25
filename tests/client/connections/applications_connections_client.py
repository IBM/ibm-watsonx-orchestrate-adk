from unittest.mock import patch, MagicMock

import requests

from ibm_watsonx_orchestrate.client.connections import ApplicationConnectionsClient, CreateBasicAuthConnection, \
    ConnectionType, BasicAuthCredentials, CreateConnectionResponse, DeleteConnectionResponse
from utils.matcher import MatchesObject


def test_create_should_call_create_connections_endpoint():
    mock = MagicMock()
    resp = requests.Response()
    resp.status_code = 200
    resp_content = CreateConnectionResponse(
        status='success',
        message='success',
        connection_id='1234'
    )
    setattr(resp, '_content', resp_content.model_dump_json().encode('utf-8'))
    mock.return_value = resp
    with patch('requests.post', mock):
        client = ApplicationConnectionsClient(base_url='/')
        conn = CreateBasicAuthConnection(
            appid='app_id',
            connection_type=ConnectionType.BASIC_AUTH,
            credentials=BasicAuthCredentials(username='username', password='password'),
            shared=True
        )
        res = client.create(connection=conn)
        mock.assert_called_once_with(
            '/connections/applications',
            headers={'Content-Type': 'application/json'},
            json=conn.model_dump()
        )
        assert res == resp_content


def test_delete_should_call_delete_connections_endpoint():
    mock = MagicMock()
    resp = requests.Response()
    resp.status_code = 200
    resp_content = DeleteConnectionResponse(
        status='success',
        message='success',
        connection_id='1234'
    )
    setattr(resp, '_content', resp_content.model_dump_json().encode('utf-8'))
    mock.return_value = resp
    with patch('requests.delete', mock):
        client = ApplicationConnectionsClient(base_url='/')
        res = client.delete(app_id='le_app_id')
        mock.assert_called_once_with(
            '/connections/applications/le_app_id',
            headers={'Content-Type': 'application/json'}
        )
        assert res == resp_content