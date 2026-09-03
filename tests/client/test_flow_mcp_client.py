"""
Unit tests for FlowMCPClient.mcp_url construction.

Regression tests for: FlowMCPClient.init discards the /instances/<guid>
tenant path segment when constructing mcp_url (SC TS022824170 / #84789).
"""
import sys
import types as builtin_types
from unittest.mock import MagicMock, patch


def _make_client(base_url: str, is_local: bool = False) -> "FlowMCPClient":  # noqa: F821
    """
    Instantiate FlowMCPClient while bypassing:
      - MCP SDK import guard (HAS_MCP)
      - Real authentication / HTTP session setup
    """
    # Provide a minimal stub for the mcp package so HAS_MCP becomes True
    mcp_stub = builtin_types.ModuleType("mcp")
    mcp_stub.ClientSession = MagicMock()
    mcp_stub.types = MagicMock()
    mcp_client_stub = builtin_types.ModuleType("mcp.client")
    mcp_http_stub = builtin_types.ModuleType("mcp.client.streamable_http")
    mcp_http_stub.streamable_http_client = MagicMock()
    httpx_stub = builtin_types.ModuleType("httpx")
    httpx_stub.AsyncClient = MagicMock()

    with patch.dict(
        sys.modules,
        {
            "mcp": mcp_stub,
            "mcp.client": mcp_client_stub,
            "mcp.client.streamable_http": mcp_http_stub,
            "httpx": httpx_stub,
        },
    ):
        # Reload the module so HAS_MCP is re-evaluated with our stubs present
        import importlib
        import ibm_watsonx_orchestrate.client.tools.flow_mcp_client as mod

        importlib.reload(mod)
        FlowMCPClient = mod.FlowMCPClient

        # Patch the parent __init__ so we don't need real auth / requests setup.
        # We replicate only what BaseWXOClient.__init__ does for base_url and is_local.
        with patch.object(
            FlowMCPClient.__bases__[0],  # BaseWXOClient
            "__init__",
            autospec=True,
            side_effect=_fake_base_init,
        ):
            client = FlowMCPClient.__new__(FlowMCPClient)
            # Manually drive the parts BaseWXOClient normally handles
            client.is_local = is_local
            stripped = base_url.rstrip("/")
            if not is_local:
                client.base_url = stripped + "/v1/orchestrate"
            else:
                client.base_url = stripped + "/v1"
            # Now call FlowMCPClient.__init__ directly (skip super().__init__)
            with patch.object(
                FlowMCPClient.__bases__[0],
                "__init__",
                return_value=None,
            ):
                FlowMCPClient.__init__(client, base_url=base_url, is_local=is_local)

        return client


def _fake_base_init(self, *args, **kwargs):
    pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFlowMCPClientMcpUrl:
    """Verify mcp_url is constructed correctly for all deployment types."""

    def test_saas_with_tenant_path_preserves_instances_segment(self):
        """
        Core regression: /instances/<guid> must NOT be dropped.
        base_url = https://host/instances/abc-123
        Expected mcp_url = https://host/instances/abc-123/v1/orchestrate/flows/mcp
        """
        base_url = "https://api.ca-tor.watson-orchestrate.cloud.ibm.com/instances/6a209d48-e924-4480-80b1-f5c707e15bc6"
        client = _make_client(base_url)
        expected = "https://api.ca-tor.watson-orchestrate.cloud.ibm.com/instances/6a209d48-e924-4480-80b1-f5c707e15bc6/v1/orchestrate/flows/mcp"
        assert client.mcp_url == expected, (
            f"Tenant path dropped!\n  got:      {client.mcp_url}\n  expected: {expected}"
        )

    def test_saas_without_tenant_path(self):
        """
        Plain SaaS URL without a tenant segment still produces the correct path.
        base_url = https://host
        Expected mcp_url = https://host/v1/orchestrate/flows/mcp
        """
        base_url = "https://myhost.watson.com"
        client = _make_client(base_url)
        expected = "https://myhost.watson.com/v1/orchestrate/flows/mcp"
        assert client.mcp_url == expected

    def test_saas_url_with_trailing_slash(self):
        """
        Trailing slashes in base_url must not produce double slashes.
        """
        base_url = "https://api.example.com/instances/guid-xyz/"
        client = _make_client(base_url)
        assert "//" not in client.mcp_url.split("://", 1)[1], (
            f"Double slash in mcp_url: {client.mcp_url}"
        )
        assert client.mcp_url.endswith("/flows/mcp")

    def test_bug_regression_netloc_only_url_would_drop_path(self):
        """
        Demonstrates the old (broken) behaviour and asserts it no longer occurs.
        """
        base_url = "https://myhost.watson.com/instances/abc-123-guid"
        client = _make_client(base_url)
        broken_url = "https://myhost.watson.com/v1/orchestrate/flows/mcp"
        assert client.mcp_url != broken_url, (
            "BUG REGRESSION: tenant path is still being dropped!"
        )
        assert "/instances/abc-123-guid" in client.mcp_url

    def test_local_deployment_uses_port_9044(self):
        """
        Local deployments must still use port 9044 with /mcp context root.
        The tenant-path fix must not affect local mode.
        """
        for base_url in ("http://localhost", "http://localhost/"):
            client = _make_client(base_url, is_local=True)
            assert client.mcp_url == "http://localhost:9044/mcp"

    def test_local_deployment_with_custom_hostname(self):
        """Local mode with a non-localhost hostname."""
        base_url = "http://my-local-server/"
        client = _make_client(base_url, is_local=True)
        assert client.mcp_url == "http://my-local-server:9044/mcp"
