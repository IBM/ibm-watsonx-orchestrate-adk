"""
Integration tests for WxOEmbeddings in standalone mode.

Tests WxOEmbeddings against both local (Developer Edition) and SaaS WxO instances
to verify end-to-end functionality through the AI Gateway.

Setup:
    1. Copy template.env to .env
    2. Fill in your API keys and URLs
    3. Adjust embedding model IDs based on your available models
    4. Run: python standalone_embeddings_test.py

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

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
if not env_path.exists():
    print("❌ Error: .env file not found!")
    print(f"   Please copy .env.template to .env and configure your credentials.")
    print(f"   Expected location: {env_path}")
    sys.exit(1)

load_dotenv(env_path)

try:
    from ibm_watsonx_orchestrate_sdk.langchain import WxOEmbeddings
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


def run_embed_query(environment: str, api_key: str, base_url: str,
                    model: str, iam_url: str | None = None,
                    auth_type: str | None = None) -> TestResult:
    """Test basic embed_query functionality."""
    start_time = datetime.now()
    test_text = "What is the capital of France?"
    
    try:
        print(f"\n{'='*80}")
        print(f"Test: Embed Query | {environment} - {model}")
        print(f"{'='*80}")
        
        embeddings = WxOEmbeddings(
            model=model,
            api_key=api_key,
            instance_url=base_url,
            iam_url=iam_url,
            auth_type=auth_type
        )
        
        embedding = embeddings.embed_query(test_text)
        duration = (datetime.now() - start_time).total_seconds()
        
        # Validate embedding
        assert isinstance(embedding, list), "Embedding should be a list"
        assert len(embedding) > 0, "Embedding should not be empty"
        assert all(isinstance(x, float) for x in embedding), "All elements should be floats"
        
        print(f"✅ SUCCESS ({duration:.2f}s)")
        print(f"Embedding dimension: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")
        
        return TestResult(
            environment=environment,
            model=model,
            test_type="embed_query",
            success=True,
            response=f"Dimension: {len(embedding)}",
            duration=duration,
            details={"dimension": len(embedding), "sample": embedding[:5]}
        )
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        print(f"❌ FAILED ({duration:.2f}s): {str(e)}")
        return TestResult(
            environment=environment,
            model=model,
            test_type="embed_query",
            success=False,
            error=str(e),
            duration=duration
        )


def run_embed_documents(environment: str, api_key: str, base_url: str,
                        model: str, iam_url: str | None = None,
                        auth_type: str | None = None) -> TestResult:
    """Test embed_documents functionality."""
    start_time = datetime.now()
    test_texts = [
        "Paris is the capital of France.",
        "Berlin is the capital of Germany.",
        "London is the capital of the United Kingdom."
    ]
    
    try:
        print(f"\n{'='*80}")
        print(f"Test: Embed Documents | {environment} - {model}")
        print(f"{'='*80}")
        
        embeddings = WxOEmbeddings(
            model=model,
            api_key=api_key,
            instance_url=base_url,
            iam_url=iam_url,
            auth_type=auth_type
        )
        
        embedding_list = embeddings.embed_documents(test_texts)
        duration = (datetime.now() - start_time).total_seconds()
        
        # Validate embeddings
        assert isinstance(embedding_list, list), "Result should be a list"
        assert len(embedding_list) == len(test_texts), f"Should have {len(test_texts)} embeddings"
        assert all(isinstance(emb, list) for emb in embedding_list), "Each embedding should be a list"
        assert all(len(emb) > 0 for emb in embedding_list), "All embeddings should be non-empty"
        
        dimensions = [len(emb) for emb in embedding_list]
        assert len(set(dimensions)) == 1, "All embeddings should have same dimension"
        
        print(f"✅ SUCCESS ({duration:.2f}s)")
        print(f"Documents embedded: {len(embedding_list)}")
        print(f"Embedding dimension: {dimensions[0]}")
        
        return TestResult(
            environment=environment,
            model=model,
            test_type="embed_documents",
            success=True,
            response=f"Embedded {len(embedding_list)} documents",
            duration=duration,
            details={"count": len(embedding_list), "dimension": dimensions[0]}
        )
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        print(f"❌ FAILED ({duration:.2f}s): {str(e)}")
        return TestResult(
            environment=environment,
            model=model,
            test_type="embed_documents",
            success=False,
            error=str(e),
            duration=duration
        )


async def run_aembed_query(environment: str, api_key: str, base_url: str,
                           model: str, iam_url: str | None = None,
                           auth_type: str | None = None) -> TestResult:
    """Test async aembed_query functionality."""
    start_time = datetime.now()
    test_text = "Machine learning is a subset of artificial intelligence."
    
    try:
        print(f"\n{'='*80}")
        print(f"Test: Async Embed Query | {environment} - {model}")
        print(f"{'='*80}")
        
        embeddings = WxOEmbeddings(
            model=model,
            api_key=api_key,
            instance_url=base_url,
            iam_url=iam_url,
            auth_type=auth_type
        )
        
        embedding = await embeddings.aembed_query(test_text)
        duration = (datetime.now() - start_time).total_seconds()
        
        # Validate embedding
        assert isinstance(embedding, list), "Embedding should be a list"
        assert len(embedding) > 0, "Embedding should not be empty"
        assert all(isinstance(x, float) for x in embedding), "All elements should be floats"
        
        print(f"✅ SUCCESS ({duration:.2f}s)")
        print(f"Embedding dimension: {len(embedding)}")
        
        return TestResult(
            environment=environment,
            model=model,
            test_type="aembed_query",
            success=True,
            response=f"Dimension: {len(embedding)}",
            duration=duration,
            details={"dimension": len(embedding)}
        )
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        print(f"❌ FAILED ({duration:.2f}s): {str(e)}")
        return TestResult(
            environment=environment,
            model=model,
            test_type="aembed_query",
            success=False,
            error=str(e),
            duration=duration
        )


async def run_aembed_documents(environment: str, api_key: str, base_url: str,
                               model: str, iam_url: str | None = None,
                               auth_type: str | None = None) -> TestResult:
    """Test async aembed_documents functionality."""
    start_time = datetime.now()
    test_texts = [
        "Natural language processing enables computers to understand human language.",
        "Deep learning uses neural networks with multiple layers.",
        "Computer vision allows machines to interpret visual information."
    ]
    
    try:
        print(f"\n{'='*80}")
        print(f"Test: Async Embed Documents | {environment} - {model}")
        print(f"{'='*80}")
        
        embeddings = WxOEmbeddings(
            model=model,
            api_key=api_key,
            instance_url=base_url,
            iam_url=iam_url,
            auth_type=auth_type
        )
        
        embedding_list = await embeddings.aembed_documents(test_texts)
        duration = (datetime.now() - start_time).total_seconds()
        
        # Validate embeddings
        assert isinstance(embedding_list, list), "Result should be a list"
        assert len(embedding_list) == len(test_texts), f"Should have {len(test_texts)} embeddings"
        assert all(isinstance(emb, list) for emb in embedding_list), "Each embedding should be a list"
        
        dimensions = [len(emb) for emb in embedding_list]
        assert len(set(dimensions)) == 1, "All embeddings should have same dimension"
        
        print(f"✅ SUCCESS ({duration:.2f}s)")
        print(f"Documents embedded: {len(embedding_list)}")
        print(f"Embedding dimension: {dimensions[0]}")
        
        return TestResult(
            environment=environment,
            model=model,
            test_type="aembed_documents",
            success=True,
            response=f"Embedded {len(embedding_list)} documents",
            duration=duration,
            details={"count": len(embedding_list), "dimension": dimensions[0]}
        )
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        print(f"❌ FAILED ({duration:.2f}s): {str(e)}")
        return TestResult(
            environment=environment,
            model=model,
            test_type="aembed_documents",
            success=False,
            error=str(e),
            duration=duration
        )


def run_similarity_search(environment: str, api_key: str, base_url: str,
                          model: str, iam_url: str | None = None,
                          auth_type: str | None = None) -> TestResult:
    """Test embeddings for similarity search use case."""
    start_time = datetime.now()
    
    # Documents about different topics
    documents = [
        "Python is a high-level programming language.",
        "Machine learning is a branch of artificial intelligence.",
        "The Eiffel Tower is located in Paris, France.",
        "Neural networks are inspired by biological neurons.",
    ]
    
    query = "What is AI and machine learning?"
    
    try:
        print(f"\n{'='*80}")
        print(f"Test: Similarity Search | {environment} - {model}")
        print(f"{'='*80}")
        
        embeddings = WxOEmbeddings(
            model=model,
            api_key=api_key,
            instance_url=base_url,
            iam_url=iam_url,
            auth_type=auth_type
        )
        
        # Embed query and documents
        query_embedding = embeddings.embed_query(query)
        doc_embeddings = embeddings.embed_documents(documents)
        duration = (datetime.now() - start_time).total_seconds()
        
        # Calculate cosine similarity
        import math
        
        def cosine_similarity(vec1, vec2):
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(b * b for b in vec2))
            return dot_product / (magnitude1 * magnitude2)
        
        similarities = [cosine_similarity(query_embedding, doc_emb) for doc_emb in doc_embeddings]
        
        # Find most similar document
        max_sim_idx = similarities.index(max(similarities))
        most_similar_doc = documents[max_sim_idx]
        
        print(f"✅ SUCCESS ({duration:.2f}s)")
        print(f"Query: {query}")
        print(f"Most similar doc: {most_similar_doc[:60]}...")
        print(f"Similarity score: {similarities[max_sim_idx]:.4f}")
        
        return TestResult(
            environment=environment,
            model=model,
            test_type="similarity_search",
            success=True,
            response=f"Most similar: {most_similar_doc[:50]}...",
            duration=duration,
            details={
                "similarities": similarities,
                "most_similar_idx": max_sim_idx
            }
        )
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        print(f"❌ FAILED ({duration:.2f}s): {str(e)}")
        return TestResult(
            environment=environment,
            model=model,
            test_type="similarity_search",
            success=False,
            error=str(e),
            duration=duration
        )


def run_integration_tests():
    """Run integration tests for WxOEmbeddings in standalone mode."""
    
    print("\n" + "="*80)
    print("WxOEmbeddings Integration Tests - Standalone Mode")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Collect test configurations
    test_configs = []
    
    # Local environment tests
    local_api_key = os.getenv("LOCAL_WXO_API_KEY")  # Optional for local
    local_base_url = os.getenv("LOCAL_WXO_BASE_URL")
    local_embedding_model = os.getenv("LOCAL_EMBEDDING_MODEL")
    
    if local_base_url and local_embedding_model:
        test_configs.append(("Local", local_api_key, local_base_url, local_embedding_model, None, None))
    else:
        print("\n⚠️  Warning: Local environment not configured (skipping local tests)")
        if not local_base_url:
            print("   Missing: LOCAL_WXO_BASE_URL")
        if not local_embedding_model:
            print("   Missing: LOCAL_EMBEDDING_MODEL")
    
    # SaaS environment tests
    saas_api_key = os.getenv("SAAS_WXO_API_KEY")
    saas_base_url = os.getenv("SAAS_WXO_BASE_URL")
    saas_iam_url = os.getenv("SAAS_IAM_URL")
    saas_auth_type = os.getenv("SAAS_AUTH_TYPE")
    saas_embedding_model = os.getenv("SAAS_EMBEDDING_MODEL")
    
    if saas_api_key and saas_base_url and saas_embedding_model:
        test_configs.append(("SaaS", saas_api_key, saas_base_url, saas_embedding_model, saas_iam_url, saas_auth_type))
    else:
        print("\n⚠️  Warning: SaaS environment not configured (skipping SaaS tests)")
        if not saas_api_key:
            print("   Missing: SAAS_WXO_API_KEY")
        if not saas_base_url:
            print("   Missing: SAAS_WXO_BASE_URL")
        if not saas_embedding_model:
            print("   Missing: SAAS_EMBEDDING_MODEL")
    
    if not test_configs:
        print("\n❌ Error: No test configurations found!")
        print("   Please configure at least one environment in .env")
        sys.exit(1)
    
    # Define test functions
    sync_test_functions = [
        run_embed_query,
        run_embed_documents,
        run_similarity_search,
    ]
    
    async_test_functions = [
        run_aembed_query,
        run_aembed_documents,
    ]
    
    # Run tests
    results = []
    for environment, api_key, base_url, model, iam_url, auth_type in test_configs:
        # Run synchronous tests
        for test_func in sync_test_functions:
            result = test_func(environment, api_key, base_url, model, iam_url, auth_type)
            results.append(result)
        
        # Run async tests
        for async_test_func in async_test_functions:
            async_result = asyncio.run(async_test_func(environment, api_key, base_url, model, iam_url, auth_type))
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
    for test_type, counts in test_types.items():
        total = counts["passed"] + counts["failed"]
        print(f"  {test_type}: {counts['passed']}/{total} passed")
    
    # Group results by environment
    environments = {}
    for result in results:
        if result.environment not in environments:
            environments[result.environment] = {"passed": 0, "failed": 0}
        if result.success:
            environments[result.environment]["passed"] += 1
        else:
            environments[result.environment]["failed"] += 1
    
    print("\nResults by Environment:")
    for env, counts in environments.items():
        total = counts["passed"] + counts["failed"]
        print(f"  {env}: {counts['passed']}/{total} passed")
    
    # Show failed tests details
    failed_results = [r for r in results if not r.success]
    if failed_results:
        print("\n" + "="*80)
        print("Failed Tests Details")
        print("="*80)
        for result in failed_results:
            print(f"\n❌ {result.test_type} | {result.environment} - {result.model}")
            print(f"   Error: {result.error}")
    
    print("\n" + "="*80)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Exit with appropriate code
    sys.exit(0 if failed_tests == 0 else 1)


if __name__ == "__main__":
    run_integration_tests()
