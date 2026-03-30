from unittest.mock import MagicMock, patch
import os

import pytest
import urllib.parse
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

def test_wxo_file_type_get_file_content_with_secure_download():
    """Test that get_content uses auth headers when URL contains WXO_PATH_PREFIX"""
    import os
    os.environ["SECURE_FILE_DOWNLOAD"] = "true"
    os.environ["WXO_PATH_PREFIX"] = "v1/files/"
    os.environ["INTERNAL_REQUEST_IDENTIFIER"] = "test-identifier"
    os.environ["INTERNAL_REQUEST_HEADER_KEY"] = "x-test-key"
    os.environ["INTERNAL_REQUEST_HEADER_VALUE"] = "test-value"
    
    # Reload module to pick up env vars
    import importlib
    from ibm_watsonx_orchestrate.agent_builder.tools import types
    importlib.reload(types)
    
    url = "https://app-server.com/v1/files/document.pdf"
    with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
        response = MagicMock()
        response.content = b"test content with auth"
        mock_get.return_value = response
        
        content = types.WXOFile.get_content(url)
        
        # Verify auth headers were passed with env var values
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        headers = call_args[1]['headers']
        
        assert headers is not None
        assert headers['x-test-key'] == 'test-value'
        assert headers['Authorization'] == 'Bearer test-identifier'
        assert content == b"test content with auth"
    
    # Clean up
    del os.environ["SECURE_FILE_DOWNLOAD"]
    del os.environ["WXO_PATH_PREFIX"]
    del os.environ["INTERNAL_REQUEST_IDENTIFIER"]
    del os.environ["INTERNAL_REQUEST_HEADER_KEY"]
    del os.environ["INTERNAL_REQUEST_HEADER_VALUE"]


def test_wxo_file_type_get_file_content_without_secure_download():
    """Test that get_content does not use auth headers when SECURE_FILE_DOWNLOAD is false"""
    import os
    os.environ["SECURE_FILE_DOWNLOAD"] = "false"
    os.environ["WXO_PATH_PREFIX"] = "v1/files/"
    
    # Reload module to pick up env vars
    import importlib
    from ibm_watsonx_orchestrate.agent_builder.tools import types
    importlib.reload(types)
    
    url = "https://app-server.com/v1/files/document.pdf"
    with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
        response = MagicMock()
        response.content = b"test content without auth"
        mock_get.return_value = response
        
        content = types.WXOFile.get_content(url)
        
        # Verify no auth headers were passed
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        headers = call_args[1]['headers']
        
        assert headers is None
        assert content == b"test content without auth"
    
    # Clean up
    del os.environ["SECURE_FILE_DOWNLOAD"]
    del os.environ["WXO_PATH_PREFIX"]


def test_wxo_file_type_get_file_content_without_path_prefix():
    """Test that get_content does not use auth headers when URL doesn't contain path prefix"""
    import os
    os.environ["SECURE_FILE_DOWNLOAD"] = "true"
    os.environ["WXO_PATH_PREFIX"] = "v1/files/"
    
    # Reload module to pick up env vars
    import importlib
    from ibm_watsonx_orchestrate.agent_builder.tools import types
    importlib.reload(types)
    
    url = "http://external-storage.com/bucket/file.txt"
    with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
        response = MagicMock()
        response.content = b"external content"
        mock_get.return_value = response
        
        content = types.WXOFile.get_content(url)
        
        # Verify no auth headers for URL without path prefix
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        headers = call_args[1]['headers']
        
        assert headers is None
        assert content == b"external content"
    
    # Clean up
    del os.environ["SECURE_FILE_DOWNLOAD"]
    del os.environ["WXO_PATH_PREFIX"]


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


def test_wxo_file_type_get_filename_with_encode_method():
    url = "https://a-mock-s3-presigned-url"
    with patch('requests.get') as mock_get:
        response = MagicMock()
        response.headers = {
            "x-amz-meta-filename": "test file name",
            "x-amz-meta-size": "10",
            "x-amz-meta-content-type": "image/png",
            "x-amz-meta-filename-encode-method": "urlencode"
        }
        mock_get.return_value = response
        file_name = WXOFile.get_file_name(url)
        file_size = WXOFile.get_file_size(url)
        file_type = WXOFile.get_file_type(url)

        assert file_name == "test file name"
        assert file_size == 10
        assert file_type == "image/png"


def test_wxo_file_type_get_filename_non_ascii_with_encode_method():
    url = "https://a-mock-s3-presigned-url"
    with patch('requests.get') as mock_get:
        response = MagicMock()
        filename = "こんにちは.png"
        response.headers = {
            "x-amz-meta-filename": urllib.parse.quote(filename),
            "x-amz-meta-size": "10",
            "x-amz-meta-content-type": "image/png",
            "x-amz-meta-filename-encode-method": "urlencode"
        }
        mock_get.return_value = response
        file_name = WXOFile.get_file_name(url)
        file_size = WXOFile.get_file_size(url)
        file_type = WXOFile.get_file_type(url)

        assert file_name == filename
        assert file_size == 10
        assert file_type == "image/png"



# Test cases for SECURE_FILE_DOWNLOAD feature
class TestWXOFileSecureDownload:
    """Test cases for conditional authentication headers in WXOFile._get_headers"""

    def test_get_headers_without_secure_download_env(self, monkeypatch):
        """Test that no auth headers are added when SECURE_FILE_DOWNLOAD is false"""
        monkeypatch.setenv("SECURE_FILE_DOWNLOAD", "false")
        monkeypatch.setenv("WXO_PATH_PREFIX", "v1/files/")
        
        # Need to reload the module to pick up new env vars
        import importlib
        from ibm_watsonx_orchestrate.agent_builder.tools import types
        importlib.reload(types)
        
        url = "https://app-server.com/v1/files/document.pdf"
        with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
            response = MagicMock()
            response.headers = {"x-amz-meta-filename": "test.txt"}
            mock_get.return_value = response
            
            types.WXOFile.get_file_name(url)
            
            # Verify the call was made with only Range header (no auth headers)
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            headers = call_args[1]['headers']
            
            assert 'Range' in headers
            assert 'x-watson-service-key' not in headers
            assert 'Authorization' not in headers

    def test_get_headers_with_secure_download_with_path_prefix(self, monkeypatch):
        """Test that auth headers are added when URL contains WXO_PATH_PREFIX"""
        monkeypatch.setenv("SECURE_FILE_DOWNLOAD", "true")
        monkeypatch.setenv("WXO_PATH_PREFIX", "v1/files/")
        monkeypatch.setenv("INTERNAL_REQUEST_IDENTIFIER", "test-identifier")
        monkeypatch.setenv("INTERNAL_REQUEST_HEADER_KEY", "x-test-key")
        monkeypatch.setenv("INTERNAL_REQUEST_HEADER_VALUE", "test-value")
        
        # Need to reload the module to pick up new env vars
        import importlib
        from ibm_watsonx_orchestrate.agent_builder.tools import types
        importlib.reload(types)
        
        url = "https://app-server.com/v1/files/document.pdf"
        with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
            response = MagicMock()
            response.headers = {"x-amz-meta-filename": "test.txt"}
            mock_get.return_value = response
            
            types.WXOFile.get_file_name(url)
            
            # Verify the call was made with auth headers from env vars
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            headers = call_args[1]['headers']
            
            assert 'Range' in headers
            assert headers['x-test-key'] == 'test-value'
            assert headers['Authorization'] == 'Bearer test-identifier'

    def test_get_headers_without_path_prefix(self, monkeypatch):
        """Test that auth headers are NOT added when URL doesn't contain WXO_PATH_PREFIX"""
        monkeypatch.setenv("SECURE_FILE_DOWNLOAD", "true")
        monkeypatch.setenv("WXO_PATH_PREFIX", "v1/files/")
        
        # Need to reload the module to pick up new env vars
        import importlib
        from ibm_watsonx_orchestrate.agent_builder.tools import types
        importlib.reload(types)
        
        url = "http://external-storage.com/bucket/file.txt"
        with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
            response = MagicMock()
            response.headers = {"x-amz-meta-filename": "test.txt"}
            mock_get.return_value = response
            
            types.WXOFile.get_file_name(url)
            
            # Verify the call was made WITHOUT auth headers
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            headers = call_args[1]['headers']
            
            assert 'Range' in headers
            assert 'x-watson-service-key' not in headers
            assert 'Authorization' not in headers

    def test_get_headers_with_custom_path_prefix(self, monkeypatch):
        """Test that custom path prefix and auth values are respected"""
        monkeypatch.setenv("SECURE_FILE_DOWNLOAD", "true")
        monkeypatch.setenv("WXO_PATH_PREFIX", "api/v2/files/")
        monkeypatch.setenv("INTERNAL_REQUEST_IDENTIFIER", "custom-identifier")
        monkeypatch.setenv("INTERNAL_REQUEST_HEADER_KEY", "x-custom-key")
        monkeypatch.setenv("INTERNAL_REQUEST_HEADER_VALUE", "custom-value")
        
        # Need to reload the module to pick up new env vars
        import importlib
        from ibm_watsonx_orchestrate.agent_builder.tools import types
        importlib.reload(types)
        
        # URL matching custom prefix - should have auth headers with custom values
        url = "https://app-server.com/api/v2/files/document.pdf"
        with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
            response = MagicMock()
            response.headers = {"x-amz-meta-filename": "test.txt"}
            mock_get.return_value = response
            
            types.WXOFile.get_file_name(url)
            
            call_args = mock_get.call_args
            headers = call_args[1]['headers']
            
            assert 'Range' in headers
            assert headers['x-custom-key'] == 'custom-value'
            assert headers['Authorization'] == 'Bearer custom-identifier'

    def test_get_headers_backward_compatibility(self, monkeypatch):
        """Test backward compatibility - default behavior without env vars"""
        # Unset env vars to test default behavior
        monkeypatch.delenv("SECURE_FILE_DOWNLOAD", raising=False)
        monkeypatch.delenv("WXO_PATH_PREFIX", raising=False)
        
        # Need to reload the module to pick up new env vars
        import importlib
        from ibm_watsonx_orchestrate.agent_builder.tools import types
        importlib.reload(types)
        
        url = "https://any-url.com/file"
        with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
            response = MagicMock()
            response.headers = {"x-amz-meta-filename": "test.txt"}
            mock_get.return_value = response
            
            types.WXOFile.get_file_name(url)
            
            # Should work as before - no auth headers by default
            call_args = mock_get.call_args
            headers = call_args[1]['headers']
            
            assert 'Range' in headers
            assert 'x-watson-service-key' not in headers

    def test_get_headers_with_tenant_id(self, monkeypatch):
        """Test that TENANT_ID header is added when env var is set"""
        monkeypatch.setenv("SECURE_FILE_DOWNLOAD", "true")
        monkeypatch.setenv("WXO_PATH_PREFIX", "v1/files/")
        monkeypatch.setenv("INTERNAL_REQUEST_IDENTIFIER", "test-identifier-123")
        monkeypatch.setenv("INTERNAL_REQUEST_HEADER_KEY", "x-watson-service-key")
        monkeypatch.setenv("INTERNAL_REQUEST_HEADER_VALUE", "internal")
        monkeypatch.setenv("TENANT_ID", "test-tenant-123")
        
        # Need to reload the module to pick up new env vars
        import importlib
        from ibm_watsonx_orchestrate.agent_builder.tools import types
        importlib.reload(types)
        
        # URL matching prefix - should have auth headers including tenant ID
        url = "https://app-server.com/v1/files/document.pdf"
        with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
            response = MagicMock()
            response.headers = {"x-amz-meta-filename": "test.txt"}
            mock_get.return_value = response
            
            types.WXOFile.get_file_name(url)
            
            call_args = mock_get.call_args
            headers = call_args[1]['headers']
            
            assert 'Range' in headers
            assert headers['x-watson-service-key'] == 'internal'
            assert headers['Authorization'] == 'Bearer test-identifier-123'
            assert headers['X-Tenant-ID'] == 'test-tenant-123'

    def test_get_headers_without_tenant_id(self, monkeypatch):
        """Test that X-Tenant-ID header is not added when TENANT_ID env var is not set"""
        monkeypatch.setenv("SECURE_FILE_DOWNLOAD", "true")
        monkeypatch.setenv("WXO_PATH_PREFIX", "v1/files/")
        monkeypatch.setenv("INTERNAL_REQUEST_IDENTIFIER", "test-identifier-456")
        monkeypatch.setenv("INTERNAL_REQUEST_HEADER_KEY", "x-watson-service-key")
        monkeypatch.setenv("INTERNAL_REQUEST_HEADER_VALUE", "internal")
        monkeypatch.delenv("TENANT_ID", raising=False)
        
        # Need to reload the module to pick up new env vars
        import importlib
        from ibm_watsonx_orchestrate.agent_builder.tools import types
        importlib.reload(types)
        
        # URL matching prefix - should have auth headers but no tenant ID
        url = "https://app-server.com/v1/files/document.pdf"
        with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
            response = MagicMock()
            response.headers = {"x-amz-meta-filename": "test.txt"}
            mock_get.return_value = response
            
            types.WXOFile.get_file_name(url)
            
            call_args = mock_get.call_args
            headers = call_args[1]['headers']
            
            assert 'Range' in headers
            assert headers['x-watson-service-key'] == 'internal'
            assert headers['Authorization'] == 'Bearer test-identifier-456'
            assert 'X-Tenant-ID' not in headers

    def test_get_content_with_tenant_id(self, monkeypatch):
        """Test that TENANT_ID header is added in get_content when env var is set"""
        monkeypatch.setenv("SECURE_FILE_DOWNLOAD", "true")
        monkeypatch.setenv("WXO_PATH_PREFIX", "v1/files/")
        monkeypatch.setenv("INTERNAL_REQUEST_IDENTIFIER", "test-identifier-789")
        monkeypatch.setenv("INTERNAL_REQUEST_HEADER_KEY", "x-watson-service-key")
        monkeypatch.setenv("INTERNAL_REQUEST_HEADER_VALUE", "internal")
        monkeypatch.setenv("TENANT_ID", "test-tenant-456")
        
        # Need to reload the module to pick up new env vars
        import importlib
        from ibm_watsonx_orchestrate.agent_builder.tools import types
        importlib.reload(types)
        
        # URL matching prefix - should have auth headers including tenant ID
        url = "https://app-server.com/v1/files/document.pdf"
        with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
            response = MagicMock()
            response.content = b"file content"
            mock_get.return_value = response
            
            types.WXOFile.get_content(url)
            
            call_args = mock_get.call_args
            headers = call_args[1]['headers']
            
            assert headers['x-watson-service-key'] == 'internal'
            assert headers['Authorization'] == 'Bearer test-identifier-789'
            assert headers['X-Tenant-ID'] == 'test-tenant-456'


class TestWXOFile302Redirect:
    """Test cases for WXO URL 302 redirect handling"""

    def test_get_headers_with_302_redirect(self, monkeypatch):
        """Test that _get_headers follows 302 redirect and returns S3 headers"""
        monkeypatch.setenv("SECURE_FILE_DOWNLOAD", "true")
        monkeypatch.setenv("WXO_PATH_PREFIX", "v1/files/")
        monkeypatch.setenv("INTERNAL_REQUEST_IDENTIFIER", "test-token")
        monkeypatch.setenv("INTERNAL_REQUEST_HEADER_KEY", "x-watson-service-key")
        monkeypatch.setenv("INTERNAL_REQUEST_HEADER_VALUE", "internal")
        
        # Reload module to pick up env vars
        import importlib
        from ibm_watsonx_orchestrate.agent_builder.tools import types
        importlib.reload(types)
        
        wxo_url = "https://app-server.com/v1/files/document.pdf"
        s3_url = "https://s3.amazonaws.com/bucket/file.pdf?signature=xyz"
        
        with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
            # First call returns 302 with Location header
            redirect_response = MagicMock()
            redirect_response.status_code = 302
            redirect_response.headers = {
                'Location': s3_url,
                'x-amz-meta-filename': 'test.pdf'
            }
            
            # Second call returns actual S3 headers
            s3_response = MagicMock()
            s3_response.headers = {
                'x-amz-id-2': 'test-id-2',
                'x-amz-request-id': 'test-request-id',
                'Date': 'Sat, 28 Mar 2026 04:59:33 GMT',
                'Last-Modified': 'Sat, 28 Mar 2026 04:38:15 GMT',
                'ETag': '"test-etag"',
                'Content-Type': 'application/pdf',
                'Content-Length': '1024'
            }
            
            mock_get.side_effect = [redirect_response, s3_response]
            
            headers = types.WXOFile._get_headers(wxo_url)
            
            # Verify two calls were made
            assert mock_get.call_count == 2
            
            # First call should be to WXO URL with auth headers and no redirects
            first_call = mock_get.call_args_list[0]
            assert first_call[0][0] == wxo_url
            assert first_call[1]['allow_redirects'] == False
            assert 'Authorization' in first_call[1]['headers']
            
            # Second call should be to S3 URL with Range header only
            second_call = mock_get.call_args_list[1]
            assert second_call[0][0] == s3_url
            assert second_call[1]['headers']['Range'] == 'bytes=0-0'
            
            # Returned headers should be from S3 response
            assert headers['x-amz-id-2'] == 'test-id-2'
            assert headers['x-amz-request-id'] == 'test-request-id'
            assert headers['Content-Type'] == 'application/pdf'

    def test_get_headers_without_302_redirect(self, monkeypatch):
        """Test that _get_headers returns WXO headers when no redirect occurs"""
        monkeypatch.setenv("SECURE_FILE_DOWNLOAD", "true")
        monkeypatch.setenv("WXO_PATH_PREFIX", "v1/files/")
        monkeypatch.setenv("INTERNAL_REQUEST_IDENTIFIER", "test-token")
        
        # Reload module to pick up env vars
        import importlib
        from ibm_watsonx_orchestrate.agent_builder.tools import types
        importlib.reload(types)
        
        wxo_url = "https://app-server.com/v1/files/document.pdf"
        
        with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
            # Response with 200 status (no redirect)
            response = MagicMock()
            response.status_code = 200
            response.headers = {
                'x-amz-meta-filename': 'test.pdf',
                'Content-Type': 'application/pdf'
            }
            
            mock_get.return_value = response
            
            headers = types.WXOFile._get_headers(wxo_url)
            
            # Only one call should be made
            assert mock_get.call_count == 1
            
            # Returned headers should be from the original response
            assert headers['x-amz-meta-filename'] == 'test.pdf'
            assert headers['Content-Type'] == 'application/pdf'

    def test_get_headers_direct_s3_url(self, monkeypatch):
        """Test that direct S3 URLs use default behavior with auto-redirects"""
        monkeypatch.setenv("SECURE_FILE_DOWNLOAD", "true")
        monkeypatch.setenv("WXO_PATH_PREFIX", "v1/files/")
        
        # Reload module to pick up env vars
        import importlib
        from ibm_watsonx_orchestrate.agent_builder.tools import types
        importlib.reload(types)
        
        s3_url = "https://s3.amazonaws.com/bucket/file.pdf"
        
        with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
            response = MagicMock()
            response.headers = {
                'x-amz-id-2': 'test-id',
                'Content-Type': 'application/pdf'
            }
            
            mock_get.return_value = response
            
            headers = types.WXOFile._get_headers(s3_url)
            
            # Only one call should be made
            assert mock_get.call_count == 1
            
            # Should NOT have allow_redirects=False (uses default True)
            call_args = mock_get.call_args
            assert 'allow_redirects' not in call_args[1] or call_args[1].get('allow_redirects') != False
            
            # Should NOT have auth headers
            assert 'Authorization' not in call_args[1]['headers']


class TestWXOFileMisconfigurationWarning:
    """Test cases for misconfiguration warning when SECURE_FILE_DOWNLOAD is false but URL is WXO"""

    def test_get_headers_warns_on_misconfiguration(self, monkeypatch, caplog):
        """Test that warning is logged when WXO URL is used without SECURE_FILE_DOWNLOAD"""
        import logging
        monkeypatch.setenv("SECURE_FILE_DOWNLOAD", "false")
        monkeypatch.setenv("WXO_PATH_PREFIX", "v1/files/")
        
        # Reload module to pick up env vars
        import importlib
        from ibm_watsonx_orchestrate.agent_builder.tools import types
        importlib.reload(types)
        
        wxo_url = "https://app-server.com/v1/files/document.pdf"
        
        with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
            response = MagicMock()
            response.headers = {'Content-Type': 'application/pdf'}
            mock_get.return_value = response
            
            with caplog.at_level(logging.WARNING):
                types.WXOFile._get_headers(wxo_url)
            
            # Check that warning was logged
            assert any("SECURE_FILE_DOWNLOAD is disabled" in record.message for record in caplog.records)
            assert any("v1/files/" in record.message for record in caplog.records)

    def test_get_content_warns_on_misconfiguration(self, monkeypatch, caplog):
        """Test that warning is logged in get_content when WXO URL is used without SECURE_FILE_DOWNLOAD"""
        import logging
        monkeypatch.setenv("SECURE_FILE_DOWNLOAD", "false")
        monkeypatch.setenv("WXO_PATH_PREFIX", "v1/files/")
        
        # Reload module to pick up env vars
        import importlib
        from ibm_watsonx_orchestrate.agent_builder.tools import types
        importlib.reload(types)
        
        wxo_url = "https://app-server.com/v1/files/document.pdf"
        
        with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
            response = MagicMock()
            response.content = b"test content"
            mock_get.return_value = response
            
            with caplog.at_level(logging.WARNING):
                types.WXOFile.get_content(wxo_url)
            
            # Check that warning was logged
            assert any("SECURE_FILE_DOWNLOAD is disabled" in record.message for record in caplog.records)
            assert any("401 Unauthorized" in record.message for record in caplog.records)

    def test_no_warning_for_s3_url(self, monkeypatch, caplog):
        """Test that no warning is logged for direct S3 URLs even when SECURE_FILE_DOWNLOAD is false"""
        import logging
        monkeypatch.setenv("SECURE_FILE_DOWNLOAD", "false")
        monkeypatch.setenv("WXO_PATH_PREFIX", "v1/files/")
        
        # Reload module to pick up env vars
        import importlib
        from ibm_watsonx_orchestrate.agent_builder.tools import types
        importlib.reload(types)
        
        s3_url = "https://s3.amazonaws.com/bucket/file.pdf"
        
        with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
            response = MagicMock()
            response.headers = {'Content-Type': 'application/pdf'}
            mock_get.return_value = response
            
            with caplog.at_level(logging.WARNING):
                types.WXOFile._get_headers(s3_url)
            
            # No warning should be logged for S3 URLs
            assert not any("SECURE_FILE_DOWNLOAD is disabled" in record.message for record in caplog.records)

    def test_no_warning_when_properly_configured(self, monkeypatch, caplog):
        """Test that no warning is logged when SECURE_FILE_DOWNLOAD is true"""
        import logging
        monkeypatch.setenv("SECURE_FILE_DOWNLOAD", "true")
        monkeypatch.setenv("WXO_PATH_PREFIX", "v1/files/")
        monkeypatch.setenv("INTERNAL_REQUEST_IDENTIFIER", "test-token")
        
        # Reload module to pick up env vars
        import importlib
        from ibm_watsonx_orchestrate.agent_builder.tools import types
        importlib.reload(types)
        
        wxo_url = "https://app-server.com/v1/files/document.pdf"
        
        with patch('ibm_watsonx_orchestrate.agent_builder.tools.types.requests.get') as mock_get:
            response = MagicMock()
            response.status_code = 200
            response.headers = {'Content-Type': 'application/pdf'}
            mock_get.return_value = response
            
            with caplog.at_level(logging.WARNING):
                types.WXOFile._get_headers(wxo_url)
            
            # No warning should be logged when properly configured
            assert not any("SECURE_FILE_DOWNLOAD is disabled" in record.message for record in caplog.records)
