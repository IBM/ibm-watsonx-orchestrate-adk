"""
Tests for the WXO_ENABLE_ASYNC_ENFORCEMENT feature flag.

These tests document the flag's contract and guard against regressions in
both the on and off states.

REMOVAL: Delete this file when the flag is promoted to GA.
"""
import os
import sys
import textwrap
import tempfile

import pytest


# ---------------------------------------------------------------------------
# Unit tests for the flag helper itself
# ---------------------------------------------------------------------------

def test_flag_off_by_default(monkeypatch):
    """is_async_enforcement_enabled() must return False when env var is absent."""
    monkeypatch.delenv("WXO_ENABLE_ASYNC_ENFORCEMENT", raising=False)

    # Re-evaluate after env change
    from ibm_watsonx_orchestrate.agent_builder.tools import feature_flags
    import importlib
    importlib.reload(feature_flags)

    from ibm_watsonx_orchestrate.agent_builder.tools.feature_flags import is_async_enforcement_enabled
    assert is_async_enforcement_enabled() is False


def test_flag_on_when_env_var_set(monkeypatch):
    """is_async_enforcement_enabled() must return True when env var is 'true'."""
    monkeypatch.setenv("WXO_ENABLE_ASYNC_ENFORCEMENT", "true")

    from ibm_watsonx_orchestrate.agent_builder.tools.feature_flags import is_async_enforcement_enabled
    assert is_async_enforcement_enabled() is True


# ---------------------------------------------------------------------------
# Behavioural tests: flag-off (default)
# ---------------------------------------------------------------------------

def test_async_standalone_not_rejected_when_flag_off(monkeypatch):
    """Async standalone tool must NOT raise when enforcement is off (default)."""
    monkeypatch.delenv("WXO_ENABLE_ASYNC_ENFORCEMENT", raising=False)

    from ibm_watsonx_orchestrate.agent_builder.tools import tool

    @tool(name="async_standalone_flag_off")
    async def async_standalone(data: str) -> str:
        """Async standalone — must be accepted when flag is off."""
        return data

    # Simulate what extract_python_tools does: assign belongs_to_toolkit=False then validate
    async_standalone.belongs_to_toolkit = False
    async_standalone.validate_async_toolkit_requirement()  # must not raise


# ---------------------------------------------------------------------------
# Behavioural tests: flag-on
# ---------------------------------------------------------------------------

def test_async_standalone_rejected_when_flag_on(monkeypatch):
    """Async standalone tool MUST raise BadRequest when enforcement is on."""
    monkeypatch.setenv("WXO_ENABLE_ASYNC_ENFORCEMENT", "true")

    from ibm_watsonx_orchestrate.agent_builder.tools import tool
    from ibm_watsonx_orchestrate_core.utils.exceptions import BadRequest

    @tool(name="async_standalone_flag_on")
    async def async_standalone(data: str) -> str:
        """Async standalone — must be rejected when flag is on."""
        return data

    async_standalone.belongs_to_toolkit = False
    with pytest.raises(BadRequest, match="only supported within toolkits"):
        async_standalone.validate_async_toolkit_requirement()


def test_async_toolkit_always_allowed_regardless_of_flag(monkeypatch):
    """Async toolkit tools must be accepted whether the flag is on or off."""
    from ibm_watsonx_orchestrate.agent_builder.tools import tool

    @tool(name="async_toolkit_any_flag")
    async def async_toolkit(data: str) -> str:
        """Async toolkit tool."""
        return data

    async_toolkit.belongs_to_toolkit = True

    # Flag off
    monkeypatch.delenv("WXO_ENABLE_ASYNC_ENFORCEMENT", raising=False)
    async_toolkit.validate_async_toolkit_requirement()  # must not raise

    # Flag on
    monkeypatch.setenv("WXO_ENABLE_ASYNC_ENFORCEMENT", "true")
    async_toolkit.validate_async_toolkit_requirement()  # must not raise


# ---------------------------------------------------------------------------
# Integration: full extract_python_tools path with flag off (default)
# ---------------------------------------------------------------------------

def test_extract_python_tools_async_standalone_allowed_when_flag_off(monkeypatch):
    """Full extract_python_tools pipeline must not reject async standalone when flag is off."""
    monkeypatch.delenv("WXO_ENABLE_ASYNC_ENFORCEMENT", raising=False)

    from ibm_watsonx_orchestrate.agent_builder.tools.utils import extract_python_tools

    tool_src = textwrap.dedent("""\
        from ibm_watsonx_orchestrate.agent_builder.tools import tool

        @tool(name='async_flag_off', description='async standalone with flag off')
        async def async_flag_off(data: str) -> str:
            '''Should be accepted when flag is off.'''
            return data
    """)

    with tempfile.TemporaryDirectory() as tmp_dir:
        import os as _os
        init_file = _os.path.join(tmp_dir, "__init__.py")
        tool_file = _os.path.join(tmp_dir, "async_flag_off_tool.py")
        open(init_file, "w").close()
        with open(tool_file, "w") as f:
            f.write(tool_src)

        parent_dir = _os.path.dirname(tmp_dir)
        original_sys_path = sys.path.copy()
        sys.path.insert(0, parent_dir)
        try:
            tools = extract_python_tools(
                file=tool_file,
                package_root=tmp_dir,
                belongs_to_toolkit=False,
                requirements_file_required=False,
            )
            assert len(tools) == 1
        finally:
            sys.path[:] = original_sys_path
