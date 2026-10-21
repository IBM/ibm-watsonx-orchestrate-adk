import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ibm_watsonx_orchestrate.agent_builder.tools import utils as tool_utils
from ibm_watsonx_orchestrate_clients.connections.connections_client import ListConfigsResponse
from ibm_watsonx_orchestrate_core.types.connections import ConnectionType

validate = getattr(tool_utils, "__validate_python_connections")


def _tool(expected_type):
    cred = SimpleNamespace(app_id="my_app", type=expected_type)
    binding = SimpleNamespace(python=SimpleNamespace(connections={"my_app": "conn-1"}))
    spec = SimpleNamespace(name="my_tool", binding=binding)
    return SimpleNamespace(expected_credentials=[cred], __tool_spec__=spec)


def _connection(scheme, auth_type=None):
    return ListConfigsResponse.model_validate({
        "connection_id": "conn-1", "app_id": "my_app", "security_scheme": scheme,
        "auth_type": auth_type, "environment": "draft", "preference": "team",
    })


@pytest.mark.parametrize("scheme,auth_type", [("custom_schema", "apikey_token_exchange"), ("some_future_scheme", None)])
def test_unsupported_scheme_gives_clear_error_not_attribute_error(scheme, auth_type, caplog):
    client = MagicMock()
    client.list.return_value = [_connection(scheme, auth_type)]

    with patch.object(tool_utils, "get_connections_client", return_value=client), \
         patch.object(tool_utils, "get_connection_environments", return_value=["draft"]), \
         caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as e:
            validate(_tool([ConnectionType.BASIC_AUTH]))

    assert e.value.code == 1
    assert f"'{scheme}'" in caplog.text
    assert "accepts connections of the following types" in caplog.text


def test_matching_scheme_still_passes():
    client = MagicMock()
    client.list.return_value = [_connection("basic_auth")]

    with patch.object(tool_utils, "get_connections_client", return_value=client), \
         patch.object(tool_utils, "get_connection_environments", return_value=["draft"]):
        validate(_tool([ConnectionType.BASIC_AUTH]))
