from __future__ import annotations

from ibm_watsonx_orchestrate_sdk import Client
from ibm_watsonx_orchestrate_sdk.common.base_client import BaseAgenticClient
from ibm_watsonx_orchestrate_sdk.prompt.prompt_client import PromptClient


TEST_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJmMjQyZWFkZi0wZGM5LTRlYWUtYjJkNy02NWIwOWI0YjRiMTYiLCJ1c2VybmFtZSI6"
    "Ind4by5hcmNoZXJAaWJtLmNvbSIsImF1ZCI6ImF1dGhlbnRpY2F0ZWQiLCJ0ZW5hbnRfaWQiOiIx"
    "YjI5N2I0OC1hOWZhLTQ4MWQtOGVhYi1hZmRlMzI0NGZhNzUiLCJ3b1RlbmFudElkIjoiMWIyOTdi"
    "NDgtYTlmYS00ODFkLThlYWItYWZkZTMyNDRmYTc1Iiwid29Vc2VySWQiOiJmMjQyZWFkZi0wZGM5"
    "LTRlYWUtYjJkNy02NWIwOWI0YjRiMTYifQ."
    "iv0jmxpo3gC_WlzeoQKCcmHHqEoMpOla3K8oKuBakBw"
)

AGENT_ID = "ae90579a-1234-5678-9abc-def012345678"


def _make_client():
    return Client(
        execution_context={
            "access_token": TEST_TOKEN,
            "api_proxy_url": "http://example.local/api/v1",
            "thread_id": "thread-123",
        }
    )


def _make_prompt_client(monkeypatch):
    monkeypatch.setattr(BaseAgenticClient, "_post", lambda *a, **kw: {}, raising=False)
    monkeypatch.setattr(BaseAgenticClient, "_get", lambda *a, **kw: {}, raising=False)
    client = _make_client()
    return PromptClient(client.session, AGENT_ID)


def test_base_url_strips_api_v1():
    client = _make_client()
    pc = PromptClient.__new__(PromptClient)
    pc.base_url = "http://example.local/api/v1"
    pc.session = client.session
    BaseAgenticClient.__init__(pc, client.session)
    pc.__init__(client.session, AGENT_ID)
    assert "/api/v1" not in pc.base_url
    assert pc.base_url == "http://example.local"


def test_base_url_strips_v1_only(monkeypatch):
    monkeypatch.setattr(BaseAgenticClient, "_post", lambda *a, **kw: {}, raising=False)
    monkeypatch.setattr(BaseAgenticClient, "_get", lambda *a, **kw: {}, raising=False)
    client = Client(
        execution_context={
            "access_token": TEST_TOKEN,
            "api_proxy_url": "http://example.local/v1",
            "thread_id": "thread-123",
        }
    )
    pc = PromptClient(client.session, AGENT_ID)
    assert pc.base_url == "http://example.local"


def test_connect_sets_connected_on_success(monkeypatch):
    def fake_post(self, path, data=None, files=None):
        return {"status": "connected", "agent_id": AGENT_ID}

    monkeypatch.setattr(BaseAgenticClient, "_post", fake_post, raising=False)
    monkeypatch.setattr(BaseAgenticClient, "_get", lambda *a, **kw: {}, raising=False)
    client = _make_client()
    pc = PromptClient(client.session, AGENT_ID)

    pc.connect()
    assert pc.connected is True


def test_connect_stays_disconnected_on_failure(monkeypatch):
    def fake_post(self, path, data=None, files=None):
        raise ConnectionError("unreachable")

    monkeypatch.setattr(BaseAgenticClient, "_post", fake_post, raising=False)
    monkeypatch.setattr(BaseAgenticClient, "_get", lambda *a, **kw: {}, raising=False)
    client = _make_client()
    pc = PromptClient(client.session, AGENT_ID)

    pc.connect()
    assert pc.connected is False


def test_load_active_prompt_stores_and_returns(monkeypatch):
    def fake_get(self, path, **kw):
        return {"instructions": "You are a helpful agent.", "guidelines": []}

    monkeypatch.setattr(BaseAgenticClient, "_get", fake_get, raising=False)
    monkeypatch.setattr(BaseAgenticClient, "_post", lambda *a, **kw: {}, raising=False)
    client = _make_client()
    pc = PromptClient(client.session, AGENT_ID)

    result = pc.load_active_prompt()
    assert result == "You are a helpful agent."
    assert pc.active_prompt == "You are a helpful agent."


def test_load_active_prompt_returns_none_on_empty(monkeypatch):
    def fake_get(self, path, **kw):
        return {"instructions": "", "guidelines": []}

    monkeypatch.setattr(BaseAgenticClient, "_get", fake_get, raising=False)
    monkeypatch.setattr(BaseAgenticClient, "_post", lambda *a, **kw: {}, raising=False)
    client = _make_client()
    pc = PromptClient(client.session, AGENT_ID)

    result = pc.load_active_prompt()
    assert result is None
    assert pc.active_prompt is None


def test_load_active_prompt_returns_none_on_error(monkeypatch):
    def fake_get(self, path, **kw):
        raise Exception("404")

    monkeypatch.setattr(BaseAgenticClient, "_get", fake_get, raising=False)
    monkeypatch.setattr(BaseAgenticClient, "_post", lambda *a, **kw: {}, raising=False)
    client = _make_client()
    pc = PromptClient(client.session, AGENT_ID)

    result = pc.load_active_prompt()
    assert result is None


def test_fetch_candidate_caches_and_acks(monkeypatch):
    captured = []

    def fake_get(self, path, **kw):
        return {"instructions": "candidate prompt", "version": 3}

    def fake_post(self, path, data=None, files=None):
        captured.append({"path": path, "data": data})
        return {}

    monkeypatch.setattr(BaseAgenticClient, "_get", fake_get, raising=False)
    monkeypatch.setattr(BaseAgenticClient, "_post", fake_post, raising=False)
    client = _make_client()
    pc = PromptClient(client.session, AGENT_ID)

    result = pc.fetch_candidate("run-42")
    assert result == "candidate prompt"
    assert any("prompt-ack" in c["path"] for c in captured)
    assert any(c["data"] == {"version": 3} for c in captured)

    # Second call should return from cache without another GET
    captured.clear()
    result2 = pc.fetch_candidate("run-42")
    assert result2 == "candidate prompt"
    assert len(captured) == 0


def test_fetch_candidate_returns_none_on_error(monkeypatch):
    def fake_get(self, path, **kw):
        raise Exception("network error")

    monkeypatch.setattr(BaseAgenticClient, "_get", fake_get, raising=False)
    monkeypatch.setattr(BaseAgenticClient, "_post", lambda *a, **kw: {}, raising=False)
    client = _make_client()
    pc = PromptClient(client.session, AGENT_ID)

    result = pc.fetch_candidate("run-99")
    assert result is None
