from __future__ import annotations

from ibm_watsonx_orchestrate_sdk import Client
from ibm_watsonx_orchestrate_sdk.common.base_client import BaseAgenticClient
from ibm_watsonx_orchestrate_clients.common.base_client import BaseAPIClient
import requests
import warnings
from urllib3.exceptions import InsecureRequestWarning


TEST_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJmMjQyZWFkZi0wZGM5LTRlYWUtYjJkNy02NWIwOWI0YjRiMTYiLCJ1c2VybmFtZSI6"
    "Ind4by5hcmNoZXJAaWJtLmNvbSIsImF1ZCI6ImF1dGhlbnRpY2F0ZWQiLCJ0ZW5hbnRfaWQiOiIx"
    "YjI5N2I0OC1hOWZhLTQ4MWQtOGVhYi1hZmRlMzI0NGZhNzUiLCJ3b1RlbmFudElkIjoiMWIyOTdi"
    "NDgtYTlmYS00ODFkLThlYWItYWZkZTMyNDRmYTc1Iiwid29Vc2VySWQiOiJmMjQyZWFkZi0wZGM5"
    "LTRlYWUtYjJkNy02NWIwOWI0YjRiMTYifQ."
    "iv0jmxpo3gC_WlzeoQKCcmHHqEoMpOla3K8oKuBakBw"
)


class DummyAPIClient(BaseAPIClient):
    def create(self, *args, **kwargs):
        raise NotImplementedError

    def delete(self, *args, **kwargs):
        raise NotImplementedError

    def update(self, *args, **kwargs):
        raise NotImplementedError

    def get(self, *args, **kwargs):
        raise NotImplementedError


def _build_response(url: str) -> requests.Response:
    response = requests.Response()
    response.status_code = 200
    response._content = b"{}"
    response.url = url
    response.request = requests.Request("GET", url).prepare()
    return response


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
    assert client.session.verify is False
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


def test_memory_client_supports_list_and_delete_routes(monkeypatch):
    captured: list[tuple[str, str, object]] = []

    def fake_get(self, path: str, params=None, data=None, return_raw=False):
        captured.append(("get", path, params))
        return {
            "memories": [
                {
                    "mem0_id": "mem-1",
                    "content": "prefers coffee",
                    "memory_type": "preference",
                }
            ],
            "total": 1,
            "limit": params["limit"],
            "offset": params["offset"],
        }

    def fake_delete(self, path: str, data=None):
        captured.append(("delete", path, data))
        if path == "/memories/user":
            return {"deleted_count": 3}
        return {}

    monkeypatch.setattr(BaseAgenticClient, "_get", fake_get, raising=False)
    monkeypatch.setattr(BaseAgenticClient, "_delete", fake_delete, raising=False)

    client = Client(
        execution_context={
            "access_token": TEST_TOKEN,
            "api_proxy_url": "http://example.local/api/v1",
            "thread_id": "thread-123",
        }
    )

    list_response = client.memory.list(limit=20, offset=5)
    assert captured[0] == ("get", "/memories/user", {"limit": 20, "offset": 5})
    assert list_response.total == 1
    assert list_response.limit == 20
    assert list_response.offset == 5
    assert list_response.memories[0].mem0_id == "mem-1"

    delete_all_response = client.memory.delete_all()
    assert captured[1] == ("delete", "/memories/user", None)
    assert delete_all_response.deleted_count == 3

    delete_response = client.memory.delete(memory_id="mem-1")
    assert captured[2] == ("delete", "/memories/mem-1", None)
    assert delete_response is True


def test_memory_client_retrieve_compatibility_helper_delegates_to_search(monkeypatch):
    captured: dict[str, object] = {}

    def fake_post(self, path: str, data=None, files=None):
        captured["path"] = path
        captured["data"] = data
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
        }
    )

    response = client.memory.retrieve("coffee preference", limit=3)

    assert captured["path"] == "/memories/search"
    assert captured["data"] == {"query": "coffee preference", "limit": 3}
    assert response.total == 1
    assert not hasattr(client.memory, "store")


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


def test_memory_type_service_aliases_are_normalized(monkeypatch):
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
        messages=[{"role": "user", "content": "I like text follow-up"}],
        memory_type="profile",
    )

    assert captured["path"] == "/memories"
    assert captured["data"] == {
        "messages": [{"role": "user", "content": "I like text follow-up"}],
        "memory_type": "profile_fact",
    }


def test_invalid_memory_type_fails_fast_with_clear_error(monkeypatch):
    called: dict[str, object] = {}

    def fake_post(self, path: str, data=None, files=None):
        called["path"] = path
        return {"memories": [], "count": 0}

    monkeypatch.setattr(BaseAgenticClient, "_post", fake_post, raising=False)

    client = Client(
        execution_context={
            "access_token": TEST_TOKEN,
            "api_proxy_url": "http://example.local/api/v1",
            "thread_id": "thread-123",
        }
    )

    try:
        client.memory.add_messages(
            messages=[{"role": "user", "content": "remember this"}],
            memory_type="banana",
        )
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid memory_type")

    assert "Invalid memory_type 'banana'" in message
    assert "Supported values: conversational, profile_fact, preference, tool, outcome." in message
    assert "Accepted aliases:" in message
    assert "path" not in called


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
    assert client.session.verify is False
    assert client.session.identity is not None
    assert client.session.identity.thread_id == "thread-456"
    assert client.session.identity.deployment_platform == "lite-laptop"


def test_runs_on_env_api_proxy_url_overrides_execution_context(monkeypatch):
    monkeypatch.setenv("WXO_AGENTIC_MODE", "runs-on")
    monkeypatch.setenv("WXO_API_PROXY_URL", "http://env.example.local/api/v1")

    client = Client(
        execution_context={
            "access_token": TEST_TOKEN,
            "api_proxy_url": "http://context.example.local/api/v1",
            "thread_id": "thread-456",
        }
    )

    assert client.session.mode == "runs-on"
    assert client.session.base_url == "http://env.example.local/api/v1"


def test_runs_on_from_runnable_config_disables_tls_verification_by_default():
    client = Client.from_runnable_config(
        {
            "configurable": {
                "execution_context": {
                    "access_token": TEST_TOKEN,
                    "api_proxy_url": "https://wo-api.example.svc.cluster.local:8000",
                    "thread_id": "thread-789",
                }
            }
        }
    )

    assert client.session.mode == "runs-on"
    assert client.session.verify is False


def test_runs_on_explicit_verify_override_is_preserved():
    client = Client(
        execution_context={
            "access_token": TEST_TOKEN,
            "api_proxy_url": "https://wo-api.example.svc.cluster.local:8000",
            "thread_id": "thread-999",
        },
        verify=True,
    )

    assert client.session.mode == "runs-on"
    assert client.session.verify is True


def test_base_api_client_suppresses_insecure_request_warning_when_not_in_debug(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "info")

    def fake_request(self, method, url, **kwargs):
        warnings.warn("unverified https request", InsecureRequestWarning)
        return _build_response(url)

    monkeypatch.setattr(requests.Session, "request", fake_request)

    client = DummyAPIClient(base_url="https://example.local", verify=False)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        response = client._get("/memories", return_raw=True)

    assert response.status_code == 200
    assert not any(issubclass(w.category, InsecureRequestWarning) for w in caught)


def test_base_api_client_keeps_insecure_request_warning_visible_in_debug(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "debug")

    def fake_request(self, method, url, **kwargs):
        warnings.warn("unverified https request", InsecureRequestWarning)
        return _build_response(url)

    monkeypatch.setattr(requests.Session, "request", fake_request)

    client = DummyAPIClient(base_url="https://example.local", verify=False)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        response = client._get("/memories", return_raw=True)

    assert response.status_code == 200
    assert any(issubclass(w.category, InsecureRequestWarning) for w in caught)


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
