"""
Integration tests for ChatWxO in standalone mode.

Tests ChatWxO against both local (Developer Edition) and SaaS WxO instances
to verify end-to-end functionality through the AI Gateway.

Setup:
    1. Copy template.env to .env
    2. Fill in your API keys and URLs
    3. Adjust model IDs based on your available models
    4. Run: python standalone_test.py

Requirements:
    - Local WxO instance running (for local tests)
    - SaaS WxO instance with API access (for SaaS tests)
    - Valid API keys for both environments
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
if not env_path.exists():
    print("❌ Error: .env file not found!")
    print(f"   Please copy .env.template to .env and configure your credentials.")
    print(f"   Expected location: {env_path}")
    sys.exit(1)

load_dotenv(env_path)

try:
    from ibm_watsonx_orchestrate_sdk.langchain import ChatWxO
except ImportError:
    print("❌ Error: ibm-watsonx-orchestrate-sdk not installed!")
    print("   Install with: pip install ibm-watsonx-orchestrate-sdk")
    print("   Or from source: pip install -e packages/agentic-sdk/ibm-watsonx-orchestrate-sdk")
    sys.exit(1)


class TestResult:
    """Container for test results."""
    
    def __init__(self, environment: str, model: str, test_type: str, success: bool, 
                 response: str | None = None, error: str | None = None,
                 duration: float | None = None, details: dict | None = None):
        self.environment = environment
        self.model = model
        self.test_type = test_type
        self.success = success
        self.response = response
        self.error = error
        self.duration = duration
        self.details = details or {}


# Tool definitions for bind_tools test
class GetWeather(BaseModel):
    """Get the current weather in a given location."""
    location: str = Field(..., description="The city and state, e.g. San Francisco, CA")
    unit: str = Field(default="celsius", description="Temperature unit (celsius or fahrenheit)")


class Calculator(BaseModel):
    """Perform a mathematical calculation."""
    operation: str = Field(..., description="The operation to perform: add, subtract, multiply, divide")
    a: float = Field(..., description="First number")
    b: float = Field(..., description="Second number")


# Structured output schema
class JokeResponse(BaseModel):
    """A joke with setup and punchline."""
    setup: str = Field(description="The setup of the joke")
    punchline: str = Field(description="The punchline to the joke")
    rating: Optional[int] = Field(default=None, description="How funny the joke is, from 1 to 10")


def test_basic_invoke(environment: str, api_key: str, base_url: str,
                      model: str, iam_url: str | None = None,
                      auth_type: str | None = None) -> TestResult:
    """Test basic invoke functionality."""
    start_time = datetime.now()
    test_question = "What is the capital of France? Answer in one sentence."
    
    try:
        print(f"\n{'='*80}")
        print(f"Test: Basic Invoke | {environment} - {model}")
        print(f"{'='*80}")
        
        llm = ChatWxO(
            model=model,
            api_key=api_key,
            instance_url=base_url,
            iam_url=iam_url,
            auth_type=auth_type,
            temperature=0.7,
            max_tokens=200
        )
        
        response = llm.invoke(test_question)
        duration = (datetime.now() - start_time).total_seconds()
        
        print(f"✅ SUCCESS ({duration:.2f}s)")
        print(f"Response: {response.content[:100]}...")
        
        return TestResult(
            environment=environment,
            model=model,
            test_type="basic_invoke",
            success=True,
            response=response.content,
            duration=duration,
            details={"token_usage": response.usage_metadata}
        )
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        print(f"❌ FAILED ({duration:.2f}s): {str(e)}")
        return TestResult(
            environment=environment,
            model=model,
            test_type="basic_invoke",
            success=False,
            error=str(e),
            duration=duration
        )


def test_bind_tools(environment: str, api_key: str, base_url: str,
                    model: str, iam_url: str | None = None,
                    auth_type: str | None = None) -> TestResult:
    """Test bind_tools functionality."""
    start_time = datetime.now()
    
    try:
        print(f"\n{'='*80}")
        print(f"Test: Bind Tools | {environment} - {model}")
        print(f"{'='*80}")
        
        llm = ChatWxO(
            model=model,
            api_key=api_key,
            instance_url=base_url,
            iam_url=iam_url,
            auth_type=auth_type,
            temperature=0
        )
        
        # Bind tools
        llm_with_tools = llm.bind_tools([GetWeather, Calculator])
        
        # Invoke with a question that should trigger tool use
        response = llm_with_tools.invoke("What's the weather in San Francisco?")
        duration = (datetime.now() - start_time).total_seconds()
        
        # Check if tools were called
        tool_calls = response.tool_calls if hasattr(response, 'tool_calls') else []
        
        print(f"✅ SUCCESS ({duration:.2f}s)")
        print(f"Tool calls: {len(tool_calls)}")
        if tool_calls:
            print(f"First tool: {tool_calls[0].get('name', 'N/A')}")
        
        return TestResult(
            environment=environment,
            model=model,
            test_type="bind_tools",
            success=True,
            response=f"Tool calls: {len(tool_calls)}",
            duration=duration,
            details={"tool_calls": tool_calls}
        )
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        print(f"❌ FAILED ({duration:.2f}s): {str(e)}")
        return TestResult(
            environment=environment,
            model=model,
            test_type="bind_tools",
            success=False,
            error=str(e),
            duration=duration
        )


def test_structured_output(environment: str, api_key: str, base_url: str,
                          model: str, iam_url: str | None = None,
                          auth_type: str | None = None) -> TestResult:
    """Test with_structured_output functionality."""
    start_time = datetime.now()
    
    try:
        print(f"\n{'='*80}")
        print(f"Test: Structured Output | {environment} - {model}")
        print(f"{'='*80}")
        
        llm = ChatWxO(
            model=model,
            api_key=api_key,
            instance_url=base_url,
            iam_url=iam_url,
            auth_type=auth_type,
            temperature=0.7
        )
        
        # Get structured output
        structured_llm = llm.with_structured_output(JokeResponse)
        response = structured_llm.invoke("Tell me a joke about programming")
        duration = (datetime.now() - start_time).total_seconds()
        
        print(f"✅ SUCCESS ({duration:.2f}s)")
        print(f"Setup: {response.setup[:50]}...")
        print(f"Punchline: {response.punchline[:50]}...")
        
        return TestResult(
            environment=environment,
            model=model,
            test_type="structured_output",
            success=True,
            response=f"Setup: {response.setup}",
            duration=duration,
            details={"joke": {"setup": response.setup, "punchline": response.punchline}}
        )
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        print(f"❌ FAILED ({duration:.2f}s): {str(e)}")
        return TestResult(
            environment=environment,
            model=model,
            test_type="structured_output",
            success=False,
            error=str(e),
            duration=duration
        )


def test_batch(environment: str, api_key: str, base_url: str,
               model: str, iam_url: str | None = None,
               auth_type: str | None = None) -> TestResult:
    """Test batch functionality."""
    start_time = datetime.now()
    
    try:
        print(f"\n{'='*80}")
        print(f"Test: Batch | {environment} - {model}")
        print(f"{'='*80}")
        
        llm = ChatWxO(
            model=model,
            api_key=api_key,
            instance_url=base_url,
            iam_url=iam_url,
            auth_type=auth_type,
            temperature=0.7,
            max_tokens=50
        )
        
        # Batch invoke
        questions = [
            "What is 2+2?",
            "What is the capital of Japan?",
            "Name one planet in our solar system."
        ]
        responses = llm.batch(questions)
        duration = (datetime.now() - start_time).total_seconds()
        
        print(f"✅ SUCCESS ({duration:.2f}s)")
        print(f"Processed {len(responses)} questions")
        for i, resp in enumerate(responses):
            print(f"  Q{i+1}: {resp.content[:40]}...")
        
        return TestResult(
            environment=environment,
            model=model,
            test_type="batch",
            success=True,
            response=f"Processed {len(responses)} questions",
            duration=duration,
            details={"batch_size": len(responses)}
        )
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        print(f"❌ FAILED ({duration:.2f}s): {str(e)}")
        return TestResult(
            environment=environment,
            model=model,
            test_type="batch",
            success=False,
            error=str(e),
            duration=duration
        )


async def test_astream(environment: str, api_key: str, base_url: str,
                       model: str, iam_url: str | None = None,
                       auth_type: str | None = None) -> TestResult:
    """Test async streaming functionality."""
    start_time = datetime.now()
    
    try:
        print(f"\n{'='*80}")
        print(f"Test: Async Stream | {environment} - {model}")
        print(f"{'='*80}")
        
        llm = ChatWxO(
            model=model,
            api_key=api_key,
            instance_url=base_url,
            iam_url=iam_url,
            auth_type=auth_type,
            temperature=0.7,
            max_tokens=100
        )
        
        # Async stream
        chunks = []
        async for chunk in llm.astream("Count from 1 to 5"):
            chunks.append(chunk.content)
        
        duration = (datetime.now() - start_time).total_seconds()
        full_response = "".join(chunks)
        
        print(f"✅ SUCCESS ({duration:.2f}s)")
        print(f"Received {len(chunks)} chunks")
        print(f"Response: {full_response[:60]}...")
        
        return TestResult(
            environment=environment,
            model=model,
            test_type="astream",
            success=True,
            response=full_response,
            duration=duration,
            details={"chunk_count": len(chunks)}
        )
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        print(f"❌ FAILED ({duration:.2f}s): {str(e)}")
        return TestResult(
            environment=environment,
            model=model,
            test_type="astream",
            success=False,
            error=str(e),
            duration=duration
        )


def test_logprobs(environment: str, api_key: str, base_url: str,
                  model: str, iam_url: str | None = None,
                  auth_type: str | None = None) -> TestResult:
    """Test logprobs functionality."""
    start_time = datetime.now()
    
    try:
        print(f"\n{'='*80}")
        print(f"Test: Logprobs | {environment} - {model}")
        print(f"{'='*80}")
        
        llm = ChatWxO(
            model=model,
            api_key=api_key,
            instance_url=base_url,
            iam_url=iam_url,
            auth_type=auth_type,
            temperature=0,
            max_tokens=20,
            logprobs=True,
            top_logprobs=3
        )
        
        response = llm.invoke("Say 'hello'")
        duration = (datetime.now() - start_time).total_seconds()
        
        # Check for logprobs in response
        logprobs_data = response.response_metadata.get('logprobs')
        has_logprobs = logprobs_data is not None
        
        print(f"✅ SUCCESS ({duration:.2f}s)")
        print(f"Logprobs present: {has_logprobs}")
        if has_logprobs and logprobs_data.get('content'):
            print(f"Token count: {len(logprobs_data['content'])}")
        
        return TestResult(
            environment=environment,
            model=model,
            test_type="logprobs",
            success=True,
            response=response.content,
            duration=duration,
            details={"has_logprobs": has_logprobs}
        )
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        print(f"❌ FAILED ({duration:.2f}s): {str(e)}")
        return TestResult(
            environment=environment,
            model=model,
            test_type="logprobs",
            success=False,
            error=str(e),
            duration=duration
        )


def run_integration_tests():
    """Run integration tests for ChatWxO in standalone mode."""
    
    print("\n" + "="*80)
    print("ChatWxO Integration Tests - Standalone Mode")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Collect test configurations
    test_configs = []
    
    # Local environment tests
    local_api_key = os.getenv("LOCAL_WXO_API_KEY")  # Optional for local
    local_base_url = os.getenv("LOCAL_WXO_BASE_URL")
    local_model_1 = os.getenv("LOCAL_CHAT_MODEL_1")
    local_model_2 = os.getenv("LOCAL_CHAT_MODEL_2")
    
    if local_base_url:
        if local_model_1:
            test_configs.append(("Local", local_api_key, local_base_url, local_model_1, None, None))
        if local_model_2:
            test_configs.append(("Local", local_api_key, local_base_url, local_model_2, None, None))
    else:
        print("\n⚠️  Warning: Local environment not configured (skipping local tests)")
    
    # SaaS environment tests
    saas_api_key = os.getenv("SAAS_WXO_API_KEY")
    saas_base_url = os.getenv("SAAS_WXO_BASE_URL")
    saas_iam_url = os.getenv("SAAS_IAM_URL")
    saas_auth_type = os.getenv("SAAS_AUTH_TYPE")
    saas_model_1 = os.getenv("SAAS_CHAT_MODEL_1")
    saas_model_2 = os.getenv("SAAS_CHAT_MODEL_2")
    
    if saas_api_key and saas_base_url:
        if saas_model_1:
            test_configs.append(("SaaS", saas_api_key, saas_base_url, saas_model_1, saas_iam_url, saas_auth_type))
        if saas_model_2:
            test_configs.append(("SaaS", saas_api_key, saas_base_url, saas_model_2, saas_iam_url, saas_auth_type))
    else:
        print("\n⚠️  Warning: SaaS environment not configured (skipping SaaS tests)")
    
    if not test_configs:
        print("\n❌ Error: No test configurations found!")
        print("   Please configure at least one environment in .env")
        sys.exit(1)
    
    # Define test functions
    test_functions = [
        test_basic_invoke,
        test_bind_tools,
        test_structured_output,
        test_batch,
        test_logprobs,
    ]
    
    # Run tests
    results = []
    for environment, api_key, base_url, model, iam_url, auth_type in test_configs:
        # Run synchronous tests
        for test_func in test_functions:
            result = test_func(environment, api_key, base_url, model, iam_url, auth_type)
            results.append(result)
        
        # Run async test
        async_result = asyncio.run(test_astream(environment, api_key, base_url, model, iam_url, auth_type))
        results.append(async_result)
    
    # Print summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.success)
    failed_tests = total_tests - passed_tests
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    
    # Group results by test type
    test_types = {}
    for result in results:
        if result.test_type not in test_types:
            test_types[result.test_type] = {"passed": 0, "failed": 0}
        if result.success:
            test_types[result.test_type]["passed"] += 1
        else:
            test_types[result.test_type]["failed"] += 1
    
    print("\nResults by Test Type:")
    print("-" * 80)
    for test_type, counts in test_types.items():
        total = counts["passed"] + counts["failed"]
        print(f"{test_type:20s}: {counts['passed']}/{total} passed")
    
    if failed_tests > 0:
        print("\nFailed Tests:")
        for result in results:
            if not result.success:
                print(f"  - {result.test_type} | {result.environment} / {result.model}")
                print(f"    Error: {result.error}")
    
    print("\nDetailed Results:")
    print("-" * 80)
    for result in results:
        status = "✅ PASS" if result.success else "❌ FAIL"
        print(f"{status} | {result.test_type:20s} | {result.environment:10s} | {result.model}")
        if result.duration:
            print(f"       Duration: {result.duration:.2f}s")
    
    print("\n" + "="*80)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    # Exit with appropriate code
    sys.exit(0 if failed_tests == 0 else 1)


if __name__ == "__main__":
    run_integration_tests()
