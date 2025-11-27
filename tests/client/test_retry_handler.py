"""
Unit tests for retry_handler module.

Tests the retry decorator with exponential backoff, jitter, and error handling.
"""

import os
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import requests
from ibm_watsonx_orchestrate.client.retry_handler import (
    retry_with_backoff,
    _is_retryable_error,
    _is_retryable_status_code,
    _is_rate_limit_error,
    create_retry_decorator_from_config,
    get_env_config
)
# Import ClientAPIException from base_api_client for testing
from ibm_watsonx_orchestrate.client.base_api_client import ClientAPIException


class TestRetryWithBackoff:
    """Test the retry_with_backoff decorator."""
    
    def test_success_on_first_attempt(self):
        """Test that successful operations return immediately without retry."""
        mock_func = Mock(return_value="success", __name__="mock_func")
        decorated_func = retry_with_backoff(max_retries=3)(mock_func)
        
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_success_after_retries(self):
        """Test that operations succeed after transient failures."""
        mock_func = Mock(
            side_effect=[
                requests.Timeout("Timeout 1"),
                requests.Timeout("Timeout 2"),
                "success"
            ],
            __name__="mock_func"
        )
        decorated_func = retry_with_backoff(
            max_retries=3,
            retry_interval=100  # Short interval for testing
        )(mock_func)
        
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_max_retries_exceeded(self):
        """Test that max retries are respected and exception is raised."""
        mock_func = Mock(side_effect=requests.Timeout("Persistent timeout"), __name__="mock_func")
        decorated_func = retry_with_backoff(
            max_retries=2,
            retry_interval=50
        )(mock_func)
        
        with pytest.raises(requests.Timeout):
            decorated_func()
        
        # Should try: initial + 2 retries = 3 attempts
        assert mock_func.call_count == 3
    
    def test_exponential_backoff_timing(self):
        """Test that exponential backoff timing is approximately correct."""
        mock_func = Mock(
            side_effect=[
                requests.Timeout("Timeout 1"),
                requests.Timeout("Timeout 2"),
                requests.Timeout("Timeout 3"),
                "success"
            ],
            __name__="mock_func"
        )
        
        start_time = time.time()
        decorated_func = retry_with_backoff(
            max_retries=3,
            retry_interval=1000,  # 1 second
            backoff_multiplier=2.0,
            jitter_percentage=0.0  # No jitter for predictable timing
        )(mock_func)
        
        result = decorated_func()
        elapsed_time = time.time() - start_time
        
        assert result == "success"
        # Expected: 1s + 2s + 4s = 7s (with some tolerance)
        assert 6.5 < elapsed_time < 7.5
    
    def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness to backoff timing."""
        timings = []
        
        for _ in range(5):
            mock_func = Mock(
                side_effect=[
                    requests.Timeout("Timeout"),
                    "success"
                ],
                __name__="mock_func"
            )
            
            start_time = time.time()
            decorated_func = retry_with_backoff(
                max_retries=2,
                retry_interval=1000,
                jitter_percentage=0.2  # ±20% jitter
            )(mock_func)
            
            decorated_func()
            elapsed_time = time.time() - start_time
            timings.append(elapsed_time)
        
        # With jitter, timings should vary
        # Base timing: 1s ± 20% = 0.8s to 1.2s
        assert min(timings) < max(timings)
        assert all(0.7 < t < 1.3 for t in timings)
    
    def test_non_retryable_error_fails_immediately(self):
        """Test that non-retryable errors fail immediately without retry."""
        # Create a mock response with 400 status
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        
        # Create request mock with required attributes
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = "http://test.com"
        
        error = ClientAPIException(request=mock_request, response=mock_response)
        
        mock_func = Mock(side_effect=error, __name__="mock_func")
        decorated_func = retry_with_backoff(max_retries=3)(mock_func)
        
        with pytest.raises(ClientAPIException):
            decorated_func()
        
        # Should only try once (no retries for 400 errors)
        assert mock_func.call_count == 1
    
    def test_context_name_in_logs(self, caplog):
        """Test that context_name is used in log messages."""
        mock_func = Mock(
            side_effect=[
                requests.Timeout("Timeout"),
                "success"
            ],
            __name__="mock_func"
        )
        
        decorated_func = retry_with_backoff(
            max_retries=2,
            retry_interval=50,
            context_name="test_operation"
        )(mock_func)
        
        with caplog.at_level("WARNING"):
            decorated_func()
        
        # Check that context_name appears in logs
        assert any("test_operation" in record.message for record in caplog.records)
    
    def test_rate_limit_double_backoff(self):
        """Test that rate limit errors (429) get double backoff time."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = "http://test.com"
        
        error = ClientAPIException(request=mock_request, response=mock_response)
        
        mock_func = Mock(side_effect=[error, "success"], __name__="mock_func")
        
        start_time = time.time()
        decorated_func = retry_with_backoff(
            max_retries=2,
            retry_interval=1000,
            jitter_percentage=0.0
        )(mock_func)
        
        result = decorated_func()
        elapsed_time = time.time() - start_time
        
        assert result == "success"
        # Rate limit should get 2x backoff: 2s instead of 1s
        assert 1.8 < elapsed_time < 2.2


class TestIsRetryableError:
    """Test the _is_retryable_error function."""
    
    def test_timeout_is_retryable(self):
        """Test that Timeout errors are retryable."""
        assert _is_retryable_error(requests.Timeout("Timeout"))
    
    def test_connection_error_is_retryable(self):
        """Test that ConnectionError is retryable."""
        assert _is_retryable_error(requests.ConnectionError("Connection failed"))
    
    def test_http_500_is_retryable(self):
        """Test that HTTP 500 errors are retryable."""
        mock_response = Mock()
        mock_response.status_code = 500
        
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = "http://test.com"
        
        error = ClientAPIException(request=mock_request, response=mock_response)
        assert _is_retryable_error(error)
    
    def test_http_503_is_retryable(self):
        """Test that HTTP 503 errors are retryable."""
        mock_response = Mock()
        mock_response.status_code = 503
        
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = "http://test.com"
        
        error = ClientAPIException(request=mock_request, response=mock_response)
        assert _is_retryable_error(error)
    
    def test_http_429_is_retryable(self):
        """Test that HTTP 429 (rate limit) is retryable."""
        mock_response = Mock()
        mock_response.status_code = 429
        
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = "http://test.com"
        
        error = ClientAPIException(request=mock_request, response=mock_response)
        assert _is_retryable_error(error)
    
    def test_http_400_is_not_retryable(self):
        """Test that HTTP 400 errors are not retryable."""
        mock_response = Mock()
        mock_response.status_code = 400
        
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = "http://test.com"
        
        error = ClientAPIException(request=mock_request, response=mock_response)
        assert not _is_retryable_error(error)
    
    def test_http_404_is_not_retryable(self):
        """Test that HTTP 404 errors are not retryable."""
        mock_response = Mock()
        mock_response.status_code = 404
        
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = "http://test.com"
        
        error = ClientAPIException(request=mock_request, response=mock_response)
        assert not _is_retryable_error(error)
    
    def test_http_401_is_not_retryable(self):
        """Test that HTTP 401 (auth) errors are not retryable."""
        mock_response = Mock()
        mock_response.status_code = 401
        
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = "http://test.com"
        
        error = ClientAPIException(request=mock_request, response=mock_response)
        assert not _is_retryable_error(error)
    
    def test_unknown_error_is_not_retryable(self):
        """Test that unknown errors are not retryable by default."""
        assert not _is_retryable_error(ValueError("Some error"))
    
    def test_requests_http_error_with_500(self):
        """Test requests.HTTPError with 500 status code."""
        mock_response = Mock()
        mock_response.status_code = 500
        
        error = requests.HTTPError()
        error.response = mock_response
        
        assert _is_retryable_error(error)
    
    def test_requests_http_error_with_400(self):
        """Test requests.HTTPError with 400 status code."""
        mock_response = Mock()
        mock_response.status_code = 400
        
        error = requests.HTTPError()
        error.response = mock_response
        
        assert not _is_retryable_error(error)


class TestIsRetryableStatusCode:
    """Test the _is_retryable_status_code function."""
    
    def test_5xx_codes_are_retryable(self):
        """Test that all 5xx status codes are retryable."""
        for code in [500, 501, 502, 503, 504, 599]:
            assert _is_retryable_status_code(code)
    
    def test_429_is_retryable(self):
        """Test that 429 (rate limit) is retryable."""
        assert _is_retryable_status_code(429)
    
    def test_4xx_codes_are_not_retryable(self):
        """Test that 4xx codes (except 429) are not retryable."""
        for code in [400, 401, 403, 404, 422]:
            assert not _is_retryable_status_code(code)
    
    def test_2xx_codes_are_not_retryable(self):
        """Test that success codes are not retryable."""
        for code in [200, 201, 204]:
            assert not _is_retryable_status_code(code)
    
    def test_3xx_codes_are_not_retryable(self):
        """Test that redirect codes are not retryable."""
        for code in [301, 302, 304]:
            assert not _is_retryable_status_code(code)


class TestIsRateLimitError:
    """Test the _is_rate_limit_error function."""
    
    def test_429_client_api_exception(self):
        """Test that 429 ClientAPIException is detected."""
        mock_response = Mock()
        mock_response.status_code = 429
        
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = "http://test.com"
        
        error = ClientAPIException(request=mock_request, response=mock_response)
        assert _is_rate_limit_error(error)
    
    def test_500_is_not_rate_limit(self):
        """Test that 500 errors are not rate limit errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = "http://test.com"
        
        error = ClientAPIException(request=mock_request, response=mock_response)
        assert not _is_rate_limit_error(error)
    
    def test_429_requests_http_error(self):
        """Test that 429 requests.HTTPError is detected."""
        mock_response = Mock()
        mock_response.status_code = 429
        
        error = requests.HTTPError()
        error.response = mock_response
        
        assert _is_rate_limit_error(error)
    
    def test_non_http_error_is_not_rate_limit(self):
        """Test that non-HTTP errors are not rate limit errors."""
        assert not _is_rate_limit_error(ValueError("Some error"))


class TestCreateRetryDecoratorFromConfig:
    """Test the create_retry_decorator_from_config convenience function."""
    
    def test_default_config(self):
        """Test creating decorator with default config."""
        decorator = create_retry_decorator_from_config()
        
        mock_func = Mock(return_value="success", __name__="mock_func")
        decorated_func = decorator(mock_func)
        
        result = decorated_func()
        assert result == "success"
    
    def test_custom_max_retries(self):
        """Test creating decorator with custom max_retries."""
        decorator = create_retry_decorator_from_config(max_retries=5)
        
        mock_func = Mock(side_effect=requests.Timeout("Timeout"), __name__="mock_func")
        decorated_func = decorator(mock_func)
        
        with pytest.raises(requests.Timeout):
            decorated_func()
        
        # Should try: initial + 5 retries = 6 attempts
        assert mock_func.call_count == 6
    
    def test_custom_retry_interval(self):
        """Test creating decorator with custom retry_interval."""
        decorator = create_retry_decorator_from_config(
            max_retries=1,
            retry_interval=2000  # 2 seconds
        )
        
        mock_func = Mock(side_effect=[requests.Timeout("Timeout"), "success"], __name__="mock_func")
        
        start_time = time.time()
        decorated_func = decorator(mock_func)
        result = decorated_func()
        elapsed_time = time.time() - start_time
        
        assert result == "success"
        # Should wait ~2 seconds
        assert 1.5 < elapsed_time < 2.5
    
    def test_custom_context_name(self, caplog):
        """Test creating decorator with custom context_name."""
        decorator = create_retry_decorator_from_config(
            context_name="custom_operation"
        )
        
        mock_func = Mock(side_effect=[requests.Timeout("Timeout"), "success"], __name__="mock_func")
        decorated_func = decorator(mock_func)
        
        with caplog.at_level("WARNING"):
            decorated_func()
        
        # Check that custom context_name appears in logs
        assert any("custom_operation" in record.message for record in caplog.records)
    
    def test_all_params_custom(self):
        """Test creating decorator with all custom parameters."""
        decorator = create_retry_decorator_from_config(
            max_retries=2,
            retry_interval=500,
            context_name="test_op"
        )
        
        mock_func = Mock(
            side_effect=[
                requests.Timeout("Timeout 1"),
                requests.Timeout("Timeout 2"),
                "success"
            ],
            __name__="mock_func"
        )
        
        decorated_func = decorator(mock_func)
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 3


class TestRetryLogging:
    """Test logging behavior of retry decorator."""
    
    def test_logs_retry_attempts(self, caplog):
        """Test that retry attempts are logged."""
        mock_func = Mock(
            side_effect=[
                requests.Timeout("Timeout"),
                "success"
            ],
            __name__="mock_func"
        )
        
        decorated_func = retry_with_backoff(
            max_retries=2,
            retry_interval=50
        )(mock_func)
        
        with caplog.at_level("WARNING"):
            decorated_func()
        
        # Should have warning log for retry attempt
        assert any("Retry 1/2" in record.message for record in caplog.records)
    
    def test_logs_successful_retry(self, caplog):
        """Test that successful retries are logged."""
        mock_func = Mock(
            side_effect=[
                requests.Timeout("Timeout"),
                "success"
            ],
            __name__="mock_func"
        )
        
        decorated_func = retry_with_backoff(
            max_retries=2,
            retry_interval=50
        )(mock_func)
        
        with caplog.at_level("INFO"):
            decorated_func()
        
        # Should have info log for successful retry
        assert any("Retry 1/2 succeeded" in record.message for record in caplog.records)
    
    def test_logs_max_retries_exceeded(self, caplog):
        """Test that max retries exceeded is logged as error."""
        mock_func = Mock(side_effect=requests.Timeout("Timeout"), __name__="mock_func")
        
        decorated_func = retry_with_backoff(
            max_retries=1,
            retry_interval=50
        )(mock_func)
        
        with caplog.at_level("ERROR"):
            try:
                decorated_func()
            except requests.Timeout:
                pass
        
        # Should have error log for max retries exceeded
        assert any("Max retries (1) exceeded" in record.message for record in caplog.records)
    
    def test_logs_non_retryable_error(self, caplog):
        """Test that non-retryable errors are logged."""
        mock_response = Mock()
        mock_response.status_code = 400
        
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = "http://test.com"
        
        error = ClientAPIException(request=mock_request, response=mock_response)
        mock_func = Mock(side_effect=error, __name__="mock_func")
        
        decorated_func = retry_with_backoff(max_retries=3)(mock_func)
        
        with caplog.at_level("ERROR"):
            try:
                decorated_func()
            except ClientAPIException:
                pass
        
        # Should have error log for non-retryable error
        assert any("Non-retryable error" in record.message for record in caplog.records)


class TestEnvironmentVariableConfiguration:
    """Test environment variable configuration for retry settings."""
    
    def test_get_env_config_defaults(self):
        """Test that get_env_config returns defaults when no env vars are set."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_env_config()
            
            assert config['max_retries'] == 3
            assert config['retry_interval'] == 1000
            assert config['backoff_multiplier'] == 2.0
            assert config['jitter_percentage'] == 0.2
    
    def test_get_env_config_from_environment(self):
        """Test that get_env_config reads from environment variables."""
        with patch.dict(os.environ, {
            'ADK_MAX_RETRIES': '5',
            'ADK_RETRY_INTERVAL': '2000',
            'ADK_BACKOFF_MULTIPLIER': '3.0',
            'ADK_JITTER_PERCENTAGE': '0.3'
        }):
            config = get_env_config()
            
            assert config['max_retries'] == 5
            assert config['retry_interval'] == 2000
            assert config['backoff_multiplier'] == 3.0
            assert config['jitter_percentage'] == 0.3
    
    def test_get_env_config_invalid_values(self, caplog):
        """Test that invalid environment values fall back to defaults with warning."""
        with patch.dict(os.environ, {
            'ADK_MAX_RETRIES': 'invalid',
            'ADK_RETRY_INTERVAL': 'not_a_number',
            'ADK_BACKOFF_MULTIPLIER': 'bad_float',
            'ADK_JITTER_PERCENTAGE': 'invalid_percentage'
        }):
            with caplog.at_level("WARNING"):
                config = get_env_config()
            
            # Should fall back to defaults
            assert config['max_retries'] == 3
            assert config['retry_interval'] == 1000
            assert config['backoff_multiplier'] == 2.0
            assert config['jitter_percentage'] == 0.2
            
            # Should log warnings
            assert any("Invalid ADK_MAX_RETRIES" in record.message for record in caplog.records)
            assert any("Invalid ADK_RETRY_INTERVAL" in record.message for record in caplog.records)
    
    def test_retry_with_backoff_uses_env_defaults(self):
        """Test that retry_with_backoff uses environment variable defaults."""
        with patch.dict(os.environ, {
            'ADK_MAX_RETRIES': '2',
            'ADK_RETRY_INTERVAL': '100'
        }):
            mock_func = Mock(
                side_effect=[
                    requests.Timeout("Timeout 1"),
                    requests.Timeout("Timeout 2"),
                    "success"
                ],
                __name__="mock_func"
            )
            
            # Don't pass any arguments - should use env vars
            decorated_func = retry_with_backoff()(mock_func)
            result = decorated_func()
            
            assert result == "success"
            assert mock_func.call_count == 3  # Initial + 2 retries
    
    def test_code_overrides_environment(self):
        """Test that code parameters override environment variables."""
        with patch.dict(os.environ, {
            'ADK_MAX_RETRIES': '10',
            'ADK_RETRY_INTERVAL': '5000'
        }):
            mock_func = Mock(
                side_effect=[
                    requests.Timeout("Timeout"),
                    "success"
                ],
                __name__="mock_func"
            )
            
            # Code params should override env vars
            decorated_func = retry_with_backoff(
                max_retries=1,
                retry_interval=50
            )(mock_func)
            
            result = decorated_func()
            
            assert result == "success"
            assert mock_func.call_count == 2  # Initial + 1 retry (not 10)
    
    def test_zero_retries_from_environment(self):
        """Test that setting ADK_MAX_RETRIES=0 disables retries."""
        with patch.dict(os.environ, {'ADK_MAX_RETRIES': '0'}):
            mock_func = Mock(side_effect=requests.Timeout("Timeout"), __name__="mock_func")
            
            decorated_func = retry_with_backoff()(mock_func)
            
            with pytest.raises(requests.Timeout):
                decorated_func()
            
            # Should only try once (no retries)
            assert mock_func.call_count == 1
    
    def test_partial_env_configuration(self):
        """Test that partial environment configuration works correctly."""
        with patch.dict(os.environ, {
            'ADK_MAX_RETRIES': '7',
            # Don't set other variables - should use defaults
        }):
            config = get_env_config()
            
            assert config['max_retries'] == 7
            assert config['retry_interval'] == 1000  # Default
            assert config['backoff_multiplier'] == 2.0  # Default
            assert config['jitter_percentage'] == 0.2  # Default


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_zero_max_retries(self):
        """Test that zero max_retries means no retries."""
        mock_func = Mock(side_effect=requests.Timeout("Timeout"), __name__="mock_func")
        
        decorated_func = retry_with_backoff(max_retries=0)(mock_func)
        
        with pytest.raises(requests.Timeout):
            decorated_func()
        
        # Should only try once (no retries)
        assert mock_func.call_count == 1
    
    def test_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""
        def my_function():
            """My docstring."""
            return "result"
        
        decorated_func = retry_with_backoff()(my_function)
        
        assert decorated_func.__name__ == "my_function"
        assert decorated_func.__doc__ == "My docstring."
    
    def test_passes_args_and_kwargs(self):
        """Test that decorator passes through args and kwargs."""
        mock_func = Mock(return_value="success", __name__="mock_func")
        
        decorated_func = retry_with_backoff()(mock_func)
        result = decorated_func("arg1", "arg2", key1="value1", key2="value2")
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", "arg2", key1="value1", key2="value2")
    
    def test_very_short_interval(self):
        """Test that very short intervals work correctly."""
        mock_func = Mock(side_effect=[requests.Timeout("Timeout"), "success"], __name__="mock_func")
        
        start_time = time.time()
        decorated_func = retry_with_backoff(
            max_retries=1,
            retry_interval=10  # 10ms
        )(mock_func)
        
        result = decorated_func()
        elapsed_time = time.time() - start_time
        
        assert result == "success"
        assert elapsed_time < 0.5  # Should be very fast
