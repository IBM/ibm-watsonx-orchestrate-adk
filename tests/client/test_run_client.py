import pytest
from unittest.mock import Mock, patch, MagicMock
from ibm_watsonx_orchestrate_clients.chat.run_client import RunClient


@pytest.fixture
def saas_run_client():
    """Create a RunClient instance pointed at a SaaS URL with a mocked _post."""
    client = RunClient(base_url="https://api.example.watson-orchestrate.ibm.com")
    client._post = Mock(return_value=[{"fileName": "test.pdf", "statusCode": 200}])
    return client


@pytest.fixture
def local_run_client():
    """Create a RunClient instance pointed at localhost with a mocked _post."""
    client = RunClient(base_url="http://localhost:4321")
    client._post = Mock(return_value=[{"fileName": "test.pdf", "statusCode": 200}])
    return client


class TestRunClientUploadFileToS3:
    """Tests for upload_file_to_s3() — endpoint construction."""

    @patch("ibm_watsonx_orchestrate_clients.chat.run_client.uuid.uuid4", return_value="test-uuid")
    @patch("ibm_watsonx_orchestrate_clients.chat.run_client.safe_open")
    @patch("ibm_watsonx_orchestrate_clients.chat.run_client.os.path.exists", return_value=True)
    def test_upload_saas_endpoint_no_trailing_slash(self, mock_exists, mock_open, mock_uuid, saas_run_client):
        """SaaS base URL must call /upload-to-s3 without a trailing slash."""
        mock_open.return_value.__enter__ = Mock(return_value=b"file-content")
        mock_open.return_value.__exit__ = Mock(return_value=False)

        saas_run_client.upload_file_to_s3("/fake/path/test.pdf")

        call_args = saas_run_client._post.call_args
        endpoint = call_args[0][0]
        assert endpoint == "/upload-to-s3", (
            f"Expected '/upload-to-s3' but got '{endpoint}'. "
            "A trailing slash causes WXO-PROXY-14009E 404 on the API gateway."
        )

    @patch("ibm_watsonx_orchestrate_clients.chat.run_client.uuid.uuid4", return_value="test-uuid")
    @patch("ibm_watsonx_orchestrate_clients.chat.run_client.safe_open")
    @patch("ibm_watsonx_orchestrate_clients.chat.run_client.os.path.exists", return_value=True)
    def test_upload_local_dev_endpoint_no_trailing_slash(self, mock_exists, mock_open, mock_uuid, local_run_client):
        """Local-dev base URL must call /orchestrate/upload-to-s3 without a trailing slash."""
        mock_open.return_value.__enter__ = Mock(return_value=b"file-content")
        mock_open.return_value.__exit__ = Mock(return_value=False)

        local_run_client.upload_file_to_s3("/fake/path/test.pdf")

        call_args = local_run_client._post.call_args
        endpoint = call_args[0][0]
        assert endpoint == "/orchestrate/upload-to-s3", (
            f"Expected '/orchestrate/upload-to-s3' but got '{endpoint}'. "
            "A trailing slash causes WXO-PROXY-14009E 404 on the API gateway."
        )
