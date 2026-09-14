import pytest
from unittest.mock import Mock
from ibm_watsonx_orchestrate_clients.customer_care.customer_care_config_client import (
    CustomerCareConfigClient,
)
from ibm_watsonx_orchestrate_clients.common.base_client import ClientAPIException


@pytest.fixture
def client():
    c = CustomerCareConfigClient(base_url="https://test.example.com")
    c._get = Mock()
    c._post = Mock()
    c._patch = Mock()
    c._delete = Mock()
    return c


def _make_404():
    resp = Mock()
    resp.status_code = 404
    return ClientAPIException(response=resp, request=Mock())


class TestGet:
    def test_returns_dict_when_overrides_exist(self, client):
        client._get.return_value = {
            "configuration_value": {"min_confidence": 0.7}
        }
        result = client.get()
        client._get.assert_called_once_with("/application_config/agent_assist_config")
        assert result == {"min_confidence": 0.7}

    def test_returns_none_on_404(self, client):
        client._get.side_effect = _make_404()
        result = client.get()
        assert result is None

    def test_reraises_non_404_error(self, client):
        resp = Mock()
        resp.status_code = 500
        client._get.side_effect = ClientAPIException(response=resp, request=Mock())
        with pytest.raises(ClientAPIException):
            client.get()


class TestSet:
    def test_patches_merged_overrides_when_row_exists(self, client):
        client._get.return_value = {
            "configuration_value": {"min_confidence": 0.5}
        }
        client.set({"min_confidence": 0.7, "llm_max_tokens": 512})
        client._patch.assert_called_once_with(
            "/application_config/agent_assist_config",
            data={
                "configuration_property_name": "Agent Assist Configuration",
                "configuration_value": {"min_confidence": 0.7, "llm_max_tokens": 512},
            },
        )
        client._post.assert_not_called()

    def test_posts_when_get_raises_404(self, client):
        client._get.side_effect = _make_404()
        client.set({"min_confidence": 0.7})
        client._post.assert_called_once_with(
            "/application_config",
            data={
                "configuration_property_key": "agent_assist_config",
                "configuration_property_name": "Agent Assist Configuration",
                "configuration_value": {"min_confidence": 0.7},
            },
        )
        client._patch.assert_not_called()

    def test_preserves_existing_overrides_when_row_exists(self, client):
        client._get.return_value = {
            "configuration_value": {"min_confidence": 0.5, "llm_max_tokens": 256}
        }
        client.set({"min_confidence": 0.9})
        client._patch.assert_called_once_with(
            "/application_config/agent_assist_config",
            data={
                "configuration_property_name": "Agent Assist Configuration",
                "configuration_value": {"min_confidence": 0.9, "llm_max_tokens": 256},
            },
        )


class TestRemove:
    def test_removes_key_and_patches(self, client):
        client._get.return_value = {
            "configuration_value": {"min_confidence": 0.5, "llm_max_tokens": 256}
        }
        client.remove("min_confidence")
        client._patch.assert_called_once_with(
            "/application_config/agent_assist_config",
            data={
                "configuration_property_name": "Agent Assist Configuration",
                "configuration_value": {"llm_max_tokens": 256},
            },
        )

    def test_deletes_when_last_key_removed(self, client):
        client._get.return_value = {
            "configuration_value": {"min_confidence": 0.5}
        }
        client.remove("min_confidence")
        client._delete.assert_called_once_with("/application_config/agent_assist_config")
        client._patch.assert_not_called()

    def test_noop_when_key_not_present(self, client):
        client._get.return_value = {
            "configuration_value": {"llm_max_tokens": 256}
        }
        client.remove("min_confidence")
        client._patch.assert_not_called()
        client._delete.assert_not_called()

    def test_noop_when_no_row_exists(self, client):
        client._get.side_effect = _make_404()
        client.remove("min_confidence")
        client._patch.assert_not_called()
        client._delete.assert_not_called()


class TestReset:
    def test_deletes_row(self, client):
        client.reset()
        client._delete.assert_called_once_with("/application_config/agent_assist_config")

    def test_ignores_404(self, client):
        client._delete.side_effect = _make_404()
        client.reset()  # must not raise

    def test_reraises_non_404_error(self, client):
        resp = Mock()
        resp.status_code = 500
        client._delete.side_effect = ClientAPIException(response=resp, request=Mock())
        with pytest.raises(ClientAPIException):
            client.reset()
