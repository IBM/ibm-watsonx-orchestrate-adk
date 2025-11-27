"""
Integration tests for retry mechanism.

Tests the full retry flow with simulated ADK server scenarios.
"""

import os
import pytest
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from unittest.mock import Mock, patch
import requests
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient, ClientAPIException


class MockADKServerHandler(BaseHTTPRequestHandler):
    """Mock HTTP server handler for simulating ADK server behavior."""
    
    # Shared state across requests
    request_counts = {}
    response_configs = {}
    
    def log_message(self, format, *args):
        """Suppress default logging for cleaner test output."""
        pass
    
    def do_GET(self):
        """Handle GET requests."""
        self._handle_request()
    
    def do_POST(self):
        """Handle POST requests."""
        self._handle_request()
    
    def _handle_request(self):
        """Handle requests based on configured behavior."""
        path = self.path
        
        # Track request count for this path
        if path not in self.request_counts:
            self.request_counts[path] = 0
        self.request_counts[path] += 1
        
        # Get response configuration for this path
        config = self.response_configs.get(path, {"type": "success"})
        request_num = self.request_counts[path]
        
        if config["type"] == "timeout_then_success":
            # Fail first N requests, then succeed
            fail_count = config.get("fail_count", 2)
            if request_num <= fail_count:
                # Simulate timeout by delaying and not responding
                time.sleep(0.1)
                # For testing, we'll close connection to simulate timeout
                self.send_response(504)
                self.end_headers()
                return
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "success", "data": "test_result"}')
        
        elif config["type"] == "rate_limit_then_success":
            # Return 429, then succeed
            fail_count = config.get("fail_count", 1)
            if request_num <= fail_count:
                self.send_response(429)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "Rate limit exceeded"}')
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "success"}')
        
        elif config["type"] == "server_error_then_success":
            # Return 500, then succeed
            fail_count = config.get("fail_count", 1)
            if request_num <= fail_count:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "Internal server error"}')
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "success"}')
        
        elif config["type"] == "always_fail":
            # Always return error
            error_code = config.get("error_code", 500)
            self.send_response(error_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Persistent failure"}')
        
        elif config["type"] == "client_error":
            # Return 400 (non-retryable)
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Bad request"}')
        
        else:  # "success"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "success"}')


@pytest.fixture
def mock_server():
    """Fixture to start and stop mock ADK server."""
    # Reset shared state
    MockADKServerHandler.request_counts = {}
    MockADKServerHandler.response_configs = {}
    
    # Find available port
    server = HTTPServer(("localhost", 0), MockADKServerHandler)
    port = server.server_address[1]
    
    # Start server in background thread
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    yield {"server": server, "port": port, "base_url": f"http://localhost:{port}"}
    
    # Cleanup
    server.shutdown()
    server.server_close()


class TestRetryIntegration:
    """Integration tests for retry mechanism with mock server."""
    
    def test_successful_request_no_retry(self, mock_server):
        """Test that successful requests don't trigger retries."""
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/test"] = {"type": "success"}
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=3,
            retry_interval=100,
            timeout=5,
            is_local=True
        )
        
        response = client._get("/api/test")
        
        # BaseAPIClient returns parsed JSON dict, not Response object
        assert response["status"] == "success"
        # Should only make 1 request
        assert MockADKServerHandler.request_counts.get("/v1/api/test", 0) == 1
    
    def test_timeout_retry_then_success(self, mock_server, caplog):
        """Test that timeouts are retried and eventually succeed."""
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/timeout"] = {
            "type": "timeout_then_success",
            "fail_count": 2
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=3,
            retry_interval=500,  # Short interval for testing
            timeout=1,  # Short timeout to trigger faster
            is_local=True
        )
        
        with caplog.at_level("WARNING"):
            response = client._get("/api/timeout")
        
        assert response["status"] == "success"
        # Should make 3 attempts (2 failures + 1 success)
        assert MockADKServerHandler.request_counts.get("/v1/api/timeout", 0) == 3
        
        # Verify retry attempts were logged
        assert any("Retry" in record.message for record in caplog.records)
    
    def test_server_error_retry_then_success(self, mock_server, caplog):
        """Test that server errors (500) are retried."""
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/error"] = {
            "type": "server_error_then_success",
            "fail_count": 1
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=3,
            retry_interval=200,
            timeout=5,
            is_local=True
        )
        
        with caplog.at_level("WARNING"):
            response = client._get("/api/error")
        
        assert response["status"] == "success"
        # Should make 2 attempts (1 failure + 1 success)
        assert MockADKServerHandler.request_counts.get("/v1/api/error", 0) == 2
        
        # Verify retry was logged
        assert any("Retry 1/" in record.message for record in caplog.records)
    
    def test_rate_limit_retry_with_longer_backoff(self, mock_server):
        """Test that rate limit errors (429) get special handling."""
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/ratelimit"] = {
            "type": "rate_limit_then_success",
            "fail_count": 1
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=3,
            retry_interval=1000,  # 1 second base
            timeout=5,
            is_local=True
        )
        
        start_time = time.time()
        response = client._get("/api/ratelimit")
        elapsed_time = time.time() - start_time
        
        assert response["status"] == "success"
        # Rate limit should trigger ~2s wait (doubled backoff)
        # Allow some tolerance for timing
        assert 1.5 < elapsed_time < 3.0
    
    def test_max_retries_exceeded(self, mock_server, caplog):
        """Test that max retries limit is enforced."""
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/fail"] = {
            "type": "always_fail",
            "error_code": 500
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=2,
            retry_interval=100,
            timeout=5,
            is_local=True
        )
        
        with caplog.at_level("ERROR"):
            with pytest.raises(ClientAPIException):
                client._get("/api/fail")
        
        # Should make 3 attempts (initial + 2 retries)
        assert MockADKServerHandler.request_counts.get("/v1/api/fail", 0) == 3
        
        # Verify max retries exceeded was logged
        assert any("Max retries" in record.message for record in caplog.records)
    
    def test_client_error_no_retry(self, mock_server):
        """Test that client errors (400) are not retried."""
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/badrequest"] = {
            "type": "client_error"
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=3,
            retry_interval=100,
            timeout=5,
            is_local=True
        )
        
        with pytest.raises(ClientAPIException):
            client._get("/api/badrequest")
        
        # Should only make 1 attempt (no retries for 400)
        assert MockADKServerHandler.request_counts.get("/v1/api/badrequest", 0) == 1
    
    def test_post_request_with_retry(self, mock_server):
        """Test that POST requests support retry."""
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/post"] = {
            "type": "server_error_then_success",
            "fail_count": 1
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=3,
            retry_interval=200,
            timeout=5,
            is_local=True
        )
        
        response = client._post("/api/post", data={"data": "test"})
        
        assert response["status"] == "success"
        # Should retry once
        assert MockADKServerHandler.request_counts.get("/v1/api/post", 0) == 2
    
    def test_exponential_backoff_timing(self, mock_server):
        """Test that exponential backoff timing is approximately correct."""
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/backoff"] = {
            "type": "server_error_then_success",
            "fail_count": 3
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=3,
            retry_interval=1000,  # 1 second
            timeout=5,
            is_local=True
        )
        
        start_time = time.time()
        response = client._get("/api/backoff")
        elapsed_time = time.time() - start_time
        
        assert response["status"] == "success"
        # Expected: 1s + 2s + 4s = 7s (with jitter ±20%)
        # Allow broader range due to jitter and server processing
        assert 5.0 < elapsed_time < 9.0
    
    def test_concurrent_requests_independent_retries(self, mock_server):
        """Test that concurrent requests have independent retry counters."""
        base_url = mock_server["base_url"]
        
        # Configure different endpoints
        MockADKServerHandler.response_configs["/v1/api/endpoint1"] = {
            "type": "server_error_then_success",
            "fail_count": 1
        }
        MockADKServerHandler.response_configs["/v1/api/endpoint2"] = {
            "type": "server_error_then_success",
            "fail_count": 2
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=3,
            retry_interval=100,
            timeout=5,
            is_local=True
        )
        
        # Make concurrent requests
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(client._get, "/api/endpoint1")
            future2 = executor.submit(client._get, "/api/endpoint2")
            
            response1 = future1.result()
            response2 = future2.result()
        
        assert response1["status"] == "success"
        assert response2["status"] == "success"
        
        # Each endpoint should have independent retry counts
        assert MockADKServerHandler.request_counts.get("/v1/api/endpoint1", 0) == 2
        assert MockADKServerHandler.request_counts.get("/v1/api/endpoint2", 0) == 3


class TestEnvironmentVariableIntegration:
    """Test environment variable configuration in integration context."""
    
    def test_environment_variables_respected(self, mock_server):
        """Test that BaseAPIClient respects environment variables."""
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/env-test"] = {
            "type": "server_error_then_success",
            "fail_count": 2
        }
        
        with patch.dict(os.environ, {
            'ADK_MAX_RETRIES': '5',
            'ADK_RETRY_INTERVAL': '100',
            'ADK_TIMEOUT': '10'
        }):
            # Don't pass any retry config - should use env vars
            client = BaseAPIClient(base_url=base_url, is_local=True)
            
            # Verify environment values were used
            assert client.max_retries == 5
            assert client.retry_interval == 100
            assert client.timeout == 10
            
            # Test that retry works with env config
            response = client._get("/api/env-test")
            assert response["status"] == "success"
            
            # Should have made 3 attempts (1 initial + 2 retries)
            assert MockADKServerHandler.request_counts.get("/v1/api/env-test", 0) == 3
    
    def test_code_overrides_environment_variables(self, mock_server):
        """Test that code parameters override environment variables."""
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/override-test"] = {
            "type": "server_error_then_success",
            "fail_count": 1
        }
        
        with patch.dict(os.environ, {
            'ADK_MAX_RETRIES': '10',
            'ADK_RETRY_INTERVAL': '5000',
            'ADK_TIMEOUT': '300'
        }):
            # Code params should override env vars
            client = BaseAPIClient(
                base_url=base_url,
                max_retries=2,
                retry_interval=50,
                timeout=5,
                is_local=True
            )
            
            assert client.max_retries == 2  # Not 10 from env
            assert client.retry_interval == 50  # Not 5000 from env
            assert client.timeout == 5  # Not 300 from env
            
            response = client._get("/api/override-test")
            assert response["status"] == "success"
    
    def test_zero_retries_from_environment(self, mock_server):
        """Test that ADK_MAX_RETRIES=0 disables retries in integration."""
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/no-retry-env"] = {
            "type": "always_fail",
            "error_code": 500
        }
        
        with patch.dict(os.environ, {'ADK_MAX_RETRIES': '0'}):
            client = BaseAPIClient(base_url=base_url, is_local=True)
            
            with pytest.raises(ClientAPIException):
                client._get("/api/no-retry-env")
            
            # Should only try once (no retries)
            assert MockADKServerHandler.request_counts.get("/v1/api/no-retry-env", 0) == 1
    
    def test_invalid_environment_values_use_defaults(self, mock_server, caplog):
        """Test that invalid environment values fall back to defaults."""
        base_url = mock_server["base_url"]
        
        with patch.dict(os.environ, {
            'ADK_MAX_RETRIES': 'not_a_number',
            'ADK_RETRY_INTERVAL': 'invalid',
            'ADK_TIMEOUT': 'bad'
        }):
            with caplog.at_level("WARNING"):
                client = BaseAPIClient(base_url=base_url, is_local=True)
            
            # Should use defaults
            assert client.max_retries == 3
            assert client.retry_interval == 1000
            assert client.timeout == 300


class TestBaseAPIClientConfiguration:
    """Test BaseAPIClient configuration and initialization."""
    
    def test_default_configuration(self, mock_server):
        """Test that default configuration values work."""
        base_url = mock_server["base_url"]
        
        client = BaseAPIClient(base_url=base_url, is_local=True)
        
        # Default values should be set
        assert client.max_retries == 3
        assert client.retry_interval == 1000
        assert client.timeout == 300
    
    def test_custom_configuration(self, mock_server):
        """Test that custom configuration is respected."""
        base_url = mock_server["base_url"]
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=5,
            retry_interval=2000,
            timeout=120,
            is_local=True
        )
        
        assert client.max_retries == 5
        assert client.retry_interval == 2000
        assert client.timeout == 120
    
    def test_zero_retries(self, mock_server):
        """Test that zero retries means no retry attempts."""
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/noretry"] = {
            "type": "always_fail",
            "error_code": 500
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=0,
            retry_interval=100,
            timeout=5,
            is_local=True
        )
        
        with pytest.raises(ClientAPIException):
            client._get("/api/noretry")
        
        # Should only try once
        assert MockADKServerHandler.request_counts.get("/v1/api/noretry", 0) == 1


class TestRealWorldScenarios:
    """Test scenarios that mimic real-world ADK usage."""
    
    def test_document_processing_timeout_scenario(self, mock_server):
        """
        Simulate document processing timeout in email_writer_agent.
        
        This is the scenario where PDF processing takes longer than expected,
        causing a timeout that should be retried.
        """
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/agents/email-writer/process"] = {
            "type": "timeout_then_success",
            "fail_count": 1
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=3,
            retry_interval=1000,
            timeout=2,  # Short timeout to simulate processing delay
            is_local=True
        )
        
        # Should succeed after retry
        response = client._post(
            "/api/agents/email-writer/process",
            data={"profile_pdf": "base64_data..."}
        )
        
        assert response["status"] == "success"
        # Should have retried once
        assert MockADKServerHandler.request_counts.get(
            "/v1/api/agents/email-writer/process", 0
        ) == 2
    
    def test_information_gatherer_formalization_retry(self, mock_server, caplog):
        """
        Simulate information_gatherer_agent formalization error.
        
        This represents the "Cannot formalize agent response" error that
        requires retry.
        """
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/agents/information-gatherer/execute"] = {
            "type": "server_error_then_success",
            "fail_count": 2
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=3,
            retry_interval=500,
            timeout=10,
            is_local=True
        )
        
        with caplog.at_level("INFO"):
            response = client._post(
                "/api/agents/information-gatherer/execute",
                data={"company": "Comcast", "product": "IBM ASK HR"}
            )
        
        assert response["status"] == "success"
        # Should have retried twice
        assert MockADKServerHandler.request_counts.get(
            "/v1/api/agents/information-gatherer/execute", 0
        ) == 3
        
        # Verify successful retry was logged
        assert any("succeeded" in record.message for record in caplog.records)
    
    def test_multiple_agents_sequential_execution(self, mock_server):
        """
        Test multiple agents executing sequentially with retries.
        
        Simulates main_prospecting_flow_with_product_v2 executing multiple agents.
        """
        base_url = mock_server["base_url"]
        
        # Configure different agents with different failure patterns
        MockADKServerHandler.response_configs["/v1/api/agents/information-gatherer"] = {
            "type": "timeout_then_success",
            "fail_count": 1
        }
        MockADKServerHandler.response_configs["/v1/api/agents/mapper"] = {
            "type": "success"
        }
        MockADKServerHandler.response_configs["/v1/api/agents/boolean-query"] = {
            "type": "server_error_then_success",
            "fail_count": 1
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=3,
            retry_interval=300,
            timeout=5,
            is_local=True
        )
        
        # Execute agents sequentially
        response1 = client._post("/api/agents/information-gatherer", data={})
        response2 = client._post("/api/agents/mapper", data={})
        response3 = client._post("/api/agents/boolean-query", data={})
        
        # All should succeed
        assert response1["status"] == "success"
        assert response2["status"] == "success"
        assert response3["status"] == "success"
        
        # Verify retry counts
        assert MockADKServerHandler.request_counts.get("/v1/api/agents/information-gatherer", 0) == 2
        assert MockADKServerHandler.request_counts.get("/v1/api/agents/mapper", 0) == 1
        assert MockADKServerHandler.request_counts.get("/v1/api/agents/boolean-query", 0) == 2
    
    def test_persistent_network_issue_max_retries(self, mock_server, caplog):
        """
        Test handling of persistent network/server issues.
        
        When max retries are exceeded, should fail gracefully with clear error.
        """
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/agents/failing-agent"] = {
            "type": "always_fail",
            "error_code": 503
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=2,
            retry_interval=100,
            timeout=5,
            is_local=True
        )
        
        with caplog.at_level("ERROR"):
            with pytest.raises(ClientAPIException) as exc_info:
                client._post("/api/agents/failing-agent", data={})
        
        # Should have tried 3 times
        assert MockADKServerHandler.request_counts.get("/v1/api/agents/failing-agent", 0) == 3
        
        # Error should be clear
        assert exc_info.value.response.status_code == 503
        
        # Max retries exceeded should be logged
        assert any("Max retries (2) exceeded" in record.message for record in caplog.records)


class TestLoggingAndObservability:
    """Test logging and observability features of retry mechanism."""
    
    def test_retry_attempts_logged(self, mock_server, caplog):
        """Test that all retry attempts are logged with details."""
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/log-test"] = {
            "type": "server_error_then_success",
            "fail_count": 2
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=3,
            retry_interval=200,
            timeout=5,
            is_local=True
        )
        
        with caplog.at_level("WARNING"):
            client._get("/api/log-test")
        
        # Should have logs for retry attempts
        warning_logs = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warning_logs) >= 2  # At least 2 retry warnings
        
        # Check log content
        log_messages = [r.message for r in warning_logs]
        assert any("Retry 1/" in msg for msg in log_messages)
        assert any("Retry 2/" in msg for msg in log_messages)
    
    def test_successful_retry_logged_as_info(self, mock_server, caplog):
        """Test that successful retries are logged at INFO level."""
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/info-test"] = {
            "type": "server_error_then_success",
            "fail_count": 1
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=2,
            retry_interval=100,
            timeout=5,
            is_local=True
        )
        
        with caplog.at_level("INFO"):
            client._get("/api/info-test")
        
        # Should have info log for successful retry
        info_logs = [r for r in caplog.records if r.levelname == "INFO"]
        assert any("succeeded" in r.message for r in info_logs)
    
    def test_error_details_in_logs(self, mock_server, caplog):
        """Test that error details are included in logs."""
        base_url = mock_server["base_url"]
        MockADKServerHandler.response_configs["/v1/api/error-detail"] = {
            "type": "always_fail",
            "error_code": 500
        }
        
        client = BaseAPIClient(
            base_url=base_url,
            max_retries=1,
            retry_interval=50,
            timeout=5,
            is_local=True
        )
        
        with caplog.at_level("ERROR"):
            try:
                client._get("/api/error-detail")
            except ClientAPIException:
                pass
        
        # Check that error logs contain useful information
        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_logs) > 0
        
        # Should mention status code and error details
        log_text = " ".join([r.message for r in error_logs])
        assert "500" in log_text or "error" in log_text.lower()
