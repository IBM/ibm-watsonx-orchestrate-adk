import json

import pytest
import requests

from ibm_watsonx_orchestrate_clients.agents.agent_client import AgentClient
from ibm_watsonx_orchestrate_clients.agents.assistant_agent_client import AssistantAgentClient
from ibm_watsonx_orchestrate_clients.agents.external_agent_client import ExternalAgentClient
from ibm_watsonx_orchestrate_clients.common.base_client import (
    BaseAPIClient,
    ClientAPIException,
    ResourceQuotaExceededError,
    format_client_api_error,
)
from ibm_watsonx_orchestrate_clients.knowledge_bases.knowledge_base_client import KnowledgeBaseClient
from ibm_watsonx_orchestrate_clients.toolkit.toolkit_client import ToolKitClient
from ibm_watsonx_orchestrate_clients.tools.tool_client import ToolClient


QUOTA_BODY = {
    "detail": {
        "code": "RESOURCE_QUOTA_EXCEEDED",
        "resource": "agent",
        "current": 40,
        "requested": 1,
        "limit": 40,
        "message": "Maximum agent limit (40) reached for this tenant.",
    }
}


def make_response(status_code: int, body) -> requests.Response:
    """Build a prepared JSON response for client error tests."""
    result = requests.Response()
    result.status_code = status_code
    result._content = json.dumps(body).encode()
    result.headers["Content-Type"] = "application/json"
    result.request = requests.Request("POST", "https://example.test/v1/tools").prepare()
    return result


def test_structured_quota_response_raises_typed_backward_compatible_error():
    """A structured quota response raises the typed compatible exception."""
    client = BaseAPIClient("https://example.test")

    with pytest.raises(ResourceQuotaExceededError) as caught:
        client._check_response(make_response(429, QUOTA_BODY))

    error = caught.value
    assert isinstance(error, ClientAPIException)
    assert error.status_code == 429
    assert error.resource == "agent"
    assert error.current == 40
    assert error.requested == 1
    assert error.limit == 40
    assert error.original_body == QUOTA_BODY
    assert str(error) == QUOTA_BODY["detail"]["message"]
    assert format_client_api_error(error) == (
        "Maximum agent limit (40) reached for this tenant. "
        "[resource=agent, current=40, requested=1, limit=40]"
    )


@pytest.mark.parametrize(
    "body",
    [
        {"detail": "rate limit exceeded"},
        {"detail": {"code": "SOME_OTHER_429", "message": "try later"}},
        {"message": "too many requests"},
    ],
)
def test_unrelated_or_malformed_429_remains_client_api_exception(body):
    """Unrelated HTTP 429 responses retain the generic exception type."""
    client = BaseAPIClient("https://example.test")

    with pytest.raises(ClientAPIException) as caught:
        client._check_response(make_response(429, body))

    assert not isinstance(caught.value, ResourceQuotaExceededError)


@pytest.mark.parametrize("status_code", [400, 401, 403, 409, 422, 500])
def test_existing_http_statuses_remain_client_api_exception(status_code):
    """Existing non-quota HTTP failures retain the generic exception type."""
    client = BaseAPIClient("https://example.test")

    with pytest.raises(ClientAPIException) as caught:
        client._check_response(make_response(status_code, {"detail": "existing error"}))

    assert not isinstance(caught.value, ResourceQuotaExceededError)


@pytest.mark.parametrize(
    "client_type",
    [
        ToolClient,
        ToolKitClient,
        AgentClient,
        ExternalAgentClient,
        AssistantAgentClient,
        KnowledgeBaseClient,
    ],
)
def test_all_resource_clients_share_typed_quota_detection(client_type):
    """All resource clients inherit quota detection from the base client."""
    client = client_type("https://example.test", is_local=False)

    with pytest.raises(ResourceQuotaExceededError):
        client._check_response(make_response(429, QUOTA_BODY))


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"detail": "request failed"}, "request failed"),
        ({"detail": {"message": "specific failure"}}, "specific failure"),
        ({"detail": {"code": "SOME_ERROR"}}, "SOME_ERROR"),
        ({"message": "message failure"}, "message failure"),
        ({"error": "error failure"}, "error failure"),
    ],
)
def test_format_client_api_error_extracts_supported_json_messages(body, expected):
    """The formatter extracts each supported JSON error-message shape."""
    error = ClientAPIException(response=make_response(400, body))

    assert format_client_api_error(error) == expected


def test_format_client_api_error_falls_back_to_response_text():
    """The formatter returns response text when the body is not JSON."""
    result = requests.Response()
    result.status_code = 500
    result._content = b"plain-text failure"
    error = ClientAPIException(response=result)

    assert format_client_api_error(error) == "plain-text failure"


def test_format_client_api_error_without_response_uses_exception_text():
    """The formatter uses exception text when no response is attached."""
    error = ClientAPIException("request failed", response=None)

    assert format_client_api_error(error) == "request failed"


def test_client_api_exception_without_response_has_safe_representation():
    """A client exception without a response can be safely rendered."""
    error = ClientAPIException("request failed", response=None)

    assert repr(error) == "ClientAPIException(message='request failed')"
    assert str(error) == "ClientAPIException(message='request failed')"
