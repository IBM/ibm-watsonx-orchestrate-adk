import os
import pytest
import requests
from pathlib import Path
from unittest.mock import MagicMock, patch

from ibm_watsonx_orchestrate.client.runtime.arm_client import (
    ARMClient,
    _ARM_PATH,
    _DEFAULT_LOCAL_SERVER_URL,
)
from ibm_watsonx_orchestrate_clients.common.base_client import ClientAPIException


@pytest.fixture
def client():
    # ARM_SERVER_URL not set → falls back to the local default.
    return ARMClient(base_url="http://localhost:8080", api_key="test-token", is_local=True)


class TestARMClientBaseUrl:
    def test_default_local_base_url(self):
        """Without ARM_SERVER_URL the client uses the local default."""
        c = ARMClient(base_url="http://localhost:8080", api_key="tok", is_local=True)
        assert c.base_url == f"{_DEFAULT_LOCAL_SERVER_URL}/{_ARM_PATH}"

    def test_base_url_from_env_var(self):
        """ARM_SERVER_URL overrides the default server URL."""
        custom = "https://dev-conn.example.com/api"
        with patch.dict(os.environ, {"ARM_SERVER_URL": custom}):
            c = ARMClient(base_url="http://localhost:8080", api_key="tok", is_local=False)
        assert c.base_url == f"{custom}/{_ARM_PATH}"

    def test_env_var_trailing_slash_stripped(self):
        """Trailing slash on ARM_SERVER_URL is stripped before appending the path."""
        with patch.dict(os.environ, {"ARM_SERVER_URL": "https://host/api/"}):
            c = ARMClient(base_url="http://localhost:8080", api_key="tok", is_local=False)
        assert "//" not in c.base_url.replace("https://", "")

    def test_base_url_contains_arm_path(self):
        c = ARMClient(base_url="http://localhost:8080", api_key="tok", is_local=True)
        assert c.base_url.endswith(f"/{_ARM_PATH}")


class TestGetUploadUrl:
    def test_returns_response_dict(self, client):
        expected = {
            "upload_url": "https://s3.example.com/bucket/key?sig=abc",
            "upload_path": "abc123/agent.tar.gz",
            "expires_at": "2026-01-01T00:05:00Z",
            "ttl_seconds": 300,
        }
        with patch.object(client, "_post", return_value=expected) as mock_post:
            result = client.get_upload_url("agent.tar.gz")
        mock_post.assert_called_once_with("/upload_files/agent.tar.gz")
        assert result == expected

    def test_uses_only_basename(self, client):
        """Path separators must be stripped — only the basename is sent."""
        with patch.object(client, "_post", return_value={}) as mock_post:
            client.get_upload_url("/some/path/to/agent.tar.gz")
        mock_post.assert_called_once_with("/upload_files/agent.tar.gz")

    def test_propagates_client_api_exception(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "storage unavailable"
        exc = ClientAPIException(request=MagicMock(), response=mock_response)
        with patch.object(client, "_post", side_effect=exc):
            with pytest.raises(ClientAPIException):
                client.get_upload_url("agent.tar")


class TestUploadToS3:
    def test_streams_file_without_auth_header(self, client, tmp_path):
        archive = tmp_path / "agent.tar.gz"
        archive.write_bytes(b"fake-tar-content")
        presigned_url = "https://s3.example.com/bucket/key?sig=abc"

        with patch("requests.put") as mock_put:
            mock_put.return_value = MagicMock(status_code=200)
            mock_put.return_value.raise_for_status = MagicMock()
            client.upload_to_s3(presigned_url, str(archive))

        call_kwargs = mock_put.call_args
        assert call_kwargs[0][0] == presigned_url
        # No Authorization header must be sent to S3
        headers = call_kwargs[1].get("headers", {})
        assert "Authorization" not in headers

    def test_raises_file_not_found_for_missing_file(self, client):
        with pytest.raises(FileNotFoundError, match="not found"):
            client.upload_to_s3("https://s3.example.com/url", "/nonexistent/path.tar")

    def test_raises_http_error_on_s3_rejection(self, client, tmp_path):
        archive = tmp_path / "agent.tar"
        archive.write_bytes(b"data")
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)

        with patch("requests.put", return_value=mock_response):
            with pytest.raises(requests.HTTPError):
                client.upload_to_s3("https://s3.example.com/url", str(archive))


class TestRegisterWorkload:
    def test_posts_payload_to_workloads_endpoint(self, client):
        payload = {
            "workload_name": "agent-1",
            "workload_type": "agent",
            "source_type": "s3",
            "source_s3_key": "abc123/agent.tar.gz",
            "tag": "v1",
        }
        expected_response = {
            "workload_id": "d7d0acaa-00ac-45c5-acb8-d36b54cc97b0",
            "workload_name": "agent-1",
            "tag": "v1",
            "image_ref": "stg.icr.io/wxo-workloads/tenant/wid/agent-1:v1",
            "lifecycle_status": "importing",
        }
        with patch.object(client, "_post", return_value=expected_response) as mock_post:
            result = client.register_workload(payload)
        mock_post.assert_called_once_with("/workloads", data=payload)
        assert result["workload_id"] == "d7d0acaa-00ac-45c5-acb8-d36b54cc97b0"

    def test_propagates_409_tag_already_exists(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 409
        mock_response.json.return_value = {"code": "TAG_ALREADY_EXISTS"}
        exc = ClientAPIException(request=MagicMock(), response=mock_response)
        with patch.object(client, "_post", side_effect=exc):
            with pytest.raises(ClientAPIException):
                client.register_workload({"tag": "v1"})

    def test_registry_source_type_payload(self, client):
        payload = {
            "workload_name": "agent-1",
            "workload_type": "agent",
            "source_type": "registry",
            "source_image": "docker.io/myorg/agent-1:latest",
            "source_connection_id": "conn-abc",
            "tag": "v2",
        }
        with patch.object(client, "_post", return_value={"workload_id": "wid"}) as mock_post:
            client.register_workload(payload)
        mock_post.assert_called_once_with("/workloads", data=payload)
