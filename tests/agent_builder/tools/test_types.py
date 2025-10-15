from unittest.mock import MagicMock, patch

import pytest
from ibm_watsonx_orchestrate.agent_builder.tools.types import WXOFile


def test_wxo_file_type_get_file_metadata():
    url = "https://a-mock-s3-presigned-url"
    with patch('requests.get') as mock_get:
        response = MagicMock()
        response.headers = {
            "x-amz-meta-filename": "test file name",
            "x-amz-meta-size": "10",
            "x-amz-meta-content-type": "image/png"
        }
        mock_get.return_value = response
        file_name = WXOFile.get_file_name(url)
        file_size = WXOFile.get_file_size(url)
        file_type = WXOFile.get_file_type(url)

        assert file_name == "test file name"
        assert file_size == 10
        assert file_type == "image/png"


def test_wxo_file_type_get_file_content():
    url = "https://a-mock-s3-presigned-url"
    with patch('requests.get') as mock_get:
        response = MagicMock()
        response.headers = {
            "x-amz-meta-filename": "test file name",
            "x-amz-meta-size": "10",
            "x-amz-meta-content-type": "image/png"
        }
        response.content = b"this is a mock file content"
        mock_get.return_value = response
        file_content = WXOFile.get_content(url)
        assert file_content == b"this is a mock file content"


def test_wxo_file_none_metadata():
    url = "https://a-mock-s3-presigned-url"
    with patch('requests.get') as mock_get:
        response = MagicMock()
        response.headers = {}
        mock_get.return_value = response
        file_name = WXOFile.get_file_name(url)
        file_size = WXOFile.get_file_size(url)
        file_type = WXOFile.get_file_type(url)

        assert file_name == None
        assert file_size == None
        assert file_type == None


def test_wxo_file_get_metadata_exception():
    url = "https://a-mock-s3-presigned-url"
    with patch('requests.get') as mock_get:
        mock_get.side_effect = TimeoutError("The read operation timed out")

        with pytest.raises(TimeoutError):
            WXOFile.get_file_name(url)
        with pytest.raises(TimeoutError):
            WXOFile.get_file_size(url)
        with pytest.raises(TimeoutError):
            WXOFile.get_file_type(url)


def test_wxo_file_type_get_content_exception():
    url = "https://a-mock-s3-presigned-url"
    with patch('requests.get') as mock_get:
        mock_get.side_effect = TimeoutError("The read operation timed out")
        with pytest.raises(TimeoutError) as err:
            WXOFile.get_content(url)
