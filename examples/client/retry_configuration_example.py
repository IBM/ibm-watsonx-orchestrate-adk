#!/usr/bin/env python
"""
Example: Retry Configuration for IBM watsonx Orchestrate ADK

This example demonstrates how to configure and use the automatic retry functionality
with exponential backoff for handling transient errors.

Requirements:
    pip install ibm-watsonx-orchestrate python-dotenv
"""

import os
import logging
from dotenv import load_dotenv
from ibm_watsonx_orchestrate.client.base_api_client import BaseAPIClient
from ibm_watsonx_orchestrate.client.retry_handler import retry_with_backoff
import requests

# Setup logging to see retry behavior
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Example 1: Default Retry Configuration
# =============================================================================
def example_default_configuration():
    """Use default retry settings (3 retries, 1s initial interval)."""
    print("\n" + "="*60)
    print("Example 1: Default Retry Configuration")
    print("="*60)
    
    # Create client with defaults - will retry automatically on transient errors
    client = BaseAPIClient(
        base_url="https://api.example.com",
        api_key="your-api-key",
        is_local=True
    )
    
    print(f"Max retries: {client.max_retries}")
    print(f"Initial retry interval: {client.retry_interval}ms")
    print(f"Timeout: {client.timeout}s")
    
    # All HTTP operations are automatically protected with retry logic
    # If a timeout or 500 error occurs, it will retry with exponential backoff
    try:
        # This would automatically retry on failure
        # response = client._get("/api/endpoint")
        print("✓ Client configured with default retry settings")
    except Exception as e:
        logger.error(f"Request failed after retries: {e}")

# =============================================================================
# Example 2: Environment Variable Configuration
# =============================================================================
def example_environment_configuration():
    """Configure retry behavior using environment variables."""
    print("\n" + "="*60)
    print("Example 2: Environment Variable Configuration")
    print("="*60)
    
    # Set environment variables
    os.environ['ADK_MAX_RETRIES'] = '5'
    os.environ['ADK_RETRY_INTERVAL'] = '2000'  # 2 seconds
    os.environ['ADK_TIMEOUT'] = '120'  # 2 minutes
    
    print("Environment variables set:")
    print(f"  ADK_MAX_RETRIES={os.environ['ADK_MAX_RETRIES']}")
    print(f"  ADK_RETRY_INTERVAL={os.environ['ADK_RETRY_INTERVAL']}")
    print(f"  ADK_TIMEOUT={os.environ['ADK_TIMEOUT']}")
    
    # Client will automatically use environment variables
    client = BaseAPIClient(
        base_url="https://api.example.com",
        is_local=True
    )
    
    print(f"\nClient configuration from environment:")
    print(f"  Max retries: {client.max_retries}")
    print(f"  Retry interval: {client.retry_interval}ms")
    print(f"  Timeout: {client.timeout}s")

# =============================================================================
# Example 3: Custom Code Configuration
# =============================================================================
def example_custom_configuration():
    """Override retry settings in code for specific requirements."""
    print("\n" + "="*60)
    print("Example 3: Custom Code Configuration")
    print("="*60)
    
    # Create different clients for different use cases
    
    # Fast-failing client for quick operations
    fast_client = BaseAPIClient(
        base_url="https://api.example.com",
        max_retries=1,
        retry_interval=500,  # 500ms
        timeout=10,  # 10 seconds
        is_local=True
    )
    print("Fast client configuration:")
    print(f"  Max retries: {fast_client.max_retries}")
    print(f"  Retry interval: {fast_client.retry_interval}ms")
    print(f"  Timeout: {fast_client.timeout}s")
    
    # Patient client for long-running operations
    patient_client = BaseAPIClient(
        base_url="https://api.example.com",
        max_retries=5,
        retry_interval=3000,  # 3 seconds
        timeout=600,  # 10 minutes
        is_local=True
    )
    print("\nPatient client configuration:")
    print(f"  Max retries: {patient_client.max_retries}")
    print(f"  Retry interval: {patient_client.retry_interval}ms")
    print(f"  Timeout: {patient_client.timeout}s")

# =============================================================================
# Example 4: Using .env File
# =============================================================================
def example_dotenv_configuration():
    """Load retry configuration from .env file."""
    print("\n" + "="*60)
    print("Example 4: Using .env File Configuration")
    print("="*60)
    
    # Create a sample .env content
    env_content = """
# Retry Configuration
ADK_MAX_RETRIES=3
ADK_RETRY_INTERVAL=1500
ADK_TIMEOUT=300
ADK_BACKOFF_MULTIPLIER=2.5
ADK_JITTER_PERCENTAGE=0.3
"""
    print("Sample .env file content:")
    print(env_content)
    
    # In real usage, load from .env file
    # load_dotenv()  # This would load from .env file
    
    print("✓ Configuration would be loaded from .env file")
    print("✓ All ADK clients would use these settings by default")

# =============================================================================
# Example 5: Custom Retry Decorator
# =============================================================================
def example_custom_decorator():
    """Use retry decorator for specific functions."""
    print("\n" + "="*60)
    print("Example 5: Custom Retry Decorator")
    print("="*60)
    
    @retry_with_backoff(
        max_retries=3,
        retry_interval=1000,
        backoff_multiplier=2.0,
        jitter_percentage=0.2,
        context_name="critical_operation"
    )
    def critical_api_operation():
        """A critical operation that should retry on failure."""
        print("  Executing critical operation...")
        # Simulate an operation that might fail
        # raise requests.Timeout("Simulated timeout")
        return {"status": "success", "data": "operation completed"}
    
    # Execute the decorated function
    try:
        result = critical_api_operation()
        print(f"✓ Operation successful: {result}")
    except Exception as e:
        print(f"✗ Operation failed after retries: {e}")

# =============================================================================
# Example 6: Retry Behavior Demonstration
# =============================================================================
def example_retry_behavior():
    """Demonstrate actual retry behavior with timing."""
    print("\n" + "="*60)
    print("Example 6: Retry Behavior Demonstration")
    print("="*60)
    
    from unittest.mock import Mock
    import time
    
    # Create a mock function that fails twice, then succeeds
    call_count = 0
    def flaky_operation():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            print(f"  Attempt {call_count}: Simulating failure...")
            raise requests.Timeout(f"Timeout on attempt {call_count}")
        print(f"  Attempt {call_count}: Success!")
        return "Success"
    
    # Wrap with retry decorator
    @retry_with_backoff(
        max_retries=3,
        retry_interval=1000,  # 1 second
        jitter_percentage=0.0  # No jitter for predictable demo
    )
    def retryable_operation():
        return flaky_operation()
    
    print("Executing operation that fails twice, then succeeds:")
    print("Expected timing: ~3 seconds (immediate + 1s wait + 2s wait)")
    
    start_time = time.time()
    try:
        result = retryable_operation()
        elapsed = time.time() - start_time
        print(f"✓ Operation succeeded after {elapsed:.1f} seconds")
        print(f"  Total attempts: {call_count}")
    except Exception as e:
        print(f"✗ Operation failed: {e}")

# =============================================================================
# Example 7: Understanding Retry vs Non-Retry Errors
# =============================================================================
def example_error_classification():
    """Demonstrate which errors trigger retries and which don't."""
    print("\n" + "="*60)
    print("Example 7: Error Classification")
    print("="*60)
    
    print("Retryable Errors (will trigger automatic retry):")
    print("  • Network errors: Timeout, ConnectionError")
    print("  • Server errors: HTTP 500, 502, 503, 504")
    print("  • Rate limiting: HTTP 429")
    
    print("\nNon-Retryable Errors (fail immediately):")
    print("  • Client errors: HTTP 400, 401, 403, 404")
    print("  • Authentication failures")
    print("  • Invalid request data")
    
    # Example: Handling different error types
    @retry_with_backoff(max_retries=3, retry_interval=500)
    def api_call_example(simulate_error=None):
        if simulate_error == "timeout":
            raise requests.Timeout("Network timeout")  # Will retry
        elif simulate_error == "server":
            raise requests.HTTPError(response=Mock(status_code=500))  # Will retry
        elif simulate_error == "auth":
            raise requests.HTTPError(response=Mock(status_code=401))  # Won't retry
        return "Success"
    
    print("\n✓ Retry logic automatically classifies and handles errors")

# =============================================================================
# Main Execution
# =============================================================================
def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("IBM watsonx Orchestrate ADK - Retry Configuration Examples")
    print("="*60)
    
    # Run examples
    example_default_configuration()
    example_environment_configuration()
    example_custom_configuration()
    example_dotenv_configuration()
    example_custom_decorator()
    example_retry_behavior()
    example_error_classification()
    
    print("\n" + "="*60)
    print("Examples Complete!")
    print("="*60)
    print("\nKey Takeaways:")
    print("1. Retry functionality is automatic for all BaseAPIClient operations")
    print("2. Configure via environment variables for global settings")
    print("3. Override in code for specific use cases")
    print("4. Use exponential backoff to avoid overwhelming servers")
    print("5. Only transient errors are retried (network/server issues)")

if __name__ == "__main__":
    main()