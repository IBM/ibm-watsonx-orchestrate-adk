from __future__ import annotations

from ibm_watsonx_orchestrate_sdk import Client
from ibm_watsonx_orchestrate_sdk.common.base_client import BaseAgenticClient


TEST_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJmMjQyZWFkZi0wZGM5LTRlYWUtYjJkNy02NWIwOWI0YjRiMTYiLCJ1c2VybmFtZSI6"
    "Ind4by5hcmNoZXJAaWJtLmNvbSIsImF1ZCI6ImF1dGhlbnRpY2F0ZWQiLCJ0ZW5hbnRfaWQiOiIx"
    "YjI5N2I0OC1hOWZhLTQ4MWQtOGVhYi1hZmRlMzI0NGZhNzUiLCJ3b1RlbmFudElkIjoiMWIyOTdi"
    "NDgtYTlmYS00ODFkLThlYWItYWZkZTMyNDRmYTc1Iiwid29Vc2VySWQiOiJmMjQyZWFkZi0wZGM5"
    "LTRlYWUtYjJkNy02NWIwOWI0YjRiMTYifQ."
    "iv0jmxpo3gC_WlzeoQKCcmHHqEoMpOla3K8oKuBakBw"
)


def test_from_execution_context_hydrates_identity_from_jwt():
    client = Client(
        execution_context={
            "access_token": TEST_TOKEN,
            "api_proxy_url": "http://example.local/api/v1",
            "thread_id": "thread-123",
        }
    )

    assert client.session.mode == "runs-on"
    assert client.session.base_url == "http://example.local/api/v1"
    assert client.session.identity is not None
    assert client.session.identity.thread_id == "thread-123"
    assert client.session.identity.tenant_id == "1b297b48-a9fa-481d-8eab-afde3244fa75"
    assert client.session.identity.user_id == "f242eadf-0dc9-4eae-b2d7-65b09b4b4b16"


def test_memory_client_uses_managed_routes_and_run_context(monkeypatch):
    captured: dict[str, object] = {}

    def fake_post(self, path: str, data=None, files=None):
        captured["path"] = path
        captured["data"] = data
        if path == "/memories":
            return {
                "memories": [
                    {
                        "mem0_id": "mem-1",
                        "content": "prefers coffee",
                        "memory_type": "preference",
                    }
                ],
                "count": 1,
            }
        return {
            "results": [
                {
                    "mem0_id": "mem-1",
                    "content": "prefers coffee",
                    "memory_type": "preference",
                    "score": 0.99,
                }
            ],
            "total": 1,
            "query": data["query"],
        }

    monkeypatch.setattr(BaseAgenticClient, "_post", fake_post, raising=False)

    client = Client(
        execution_context={
            "access_token": TEST_TOKEN,
            "api_proxy_url": "http://example.local/api/v1",
            "thread_id": "thread-123",
            "run_id": "run-789",
        }
    )

    create_response = client.memory.add_messages(
        messages=[{"role": "user", "content": "I prefer coffee"}],
        metadata={"source": "test"},
    )
    assert captured["path"] == "/memories"
    assert captured["data"] == {
        "messages": [{"role": "user", "content": "I prefer coffee"}],
        "metadata": {"source": "test"},
        "run_id": "run-789",
    }
    assert create_response.count == 1

    search_response = client.memory.search(query="coffee preference", limit=2)
    assert captured["path"] == "/memories/search"
    assert captured["data"] == {"query": "coffee preference", "limit": 2}
    assert search_response.total == 1


def test_memory_type_alias_is_normalized(monkeypatch):
    captured: dict[str, object] = {}

    def fake_post(self, path: str, data=None, files=None):
        captured["path"] = path
        captured["data"] = data
        return {"memories": [], "count": 0}

    monkeypatch.setattr(BaseAgenticClient, "_post", fake_post, raising=False)

    client = Client(
        execution_context={
            "access_token": TEST_TOKEN,
            "api_proxy_url": "http://example.local/api/v1",
            "thread_id": "thread-123",
        }
    )

    client.memory.add_messages(
        messages=[{"role": "user", "content": "I prefer coffee"}],
        memory_type="conversation",
    )

    assert captured["path"] == "/memories"
    assert captured["data"] == {
        "messages": [{"role": "user", "content": "I prefer coffee"}],
        "memory_type": "conversational",
    }


def test_runs_on_constructor_uses_env_defaults(monkeypatch):
    monkeypatch.setenv("WXO_AGENTIC_MODE", "runs-on")
    monkeypatch.setenv("WXO_API_PROXY_URL", "http://env.example.local/api/v1")
    monkeypatch.setenv("DEPLOYMENT_PLATFORM", "lite-laptop")

    client = Client(
        execution_context={
            "access_token": TEST_TOKEN,
            "thread_id": "thread-456",
        }
    )

    assert client.session.mode == "runs-on"
    assert client.session.base_url == "http://env.example.local/api/v1"
    assert client.session.identity is not None
    assert client.session.identity.thread_id == "thread-456"
    assert client.session.identity.deployment_platform == "lite-laptop"


def test_runs_on_without_execution_context_has_clear_error(monkeypatch):
    monkeypatch.setenv("WXO_AGENTIC_MODE", "runs-on")
    monkeypatch.delenv("WXO_USER_TOKEN", raising=False)
    monkeypatch.delenv("WXO_AUTH_URL", raising=False)

    try:
        Client()
    except ValueError as exc:
        assert "runs-on mode requires request-scoped execution_context" in str(exc)
    else:
        raise AssertionError("Expected ValueError when runs-on mode lacks execution_context")
