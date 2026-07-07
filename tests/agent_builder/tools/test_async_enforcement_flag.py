"""
Tests for the EXPERIMENTAL_ASYNC_TOOLKITS feature flag.

The flag is checked in extract_python_tools (utils.py) — it gates the entire
belongs_to_toolkit assignment + validate_async_toolkit_requirement call.
validate_async_toolkit_requirement() itself is unconditional; the flag
controls whether it is ever called.

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
    monkeypatch.delenv("EXPERIMENTAL_ASYNC_TOOLKITS", raising=False)

    from ibm_watsonx_orchestrate.agent_builder.tools.feature_flags import is_async_enforcement_enabled
    assert is_async_enforcement_enabled() is False


def test_flag_on_when_env_var_set(monkeypatch):
    """is_async_enforcement_enabled() must return True when env var is 'true'."""
    monkeypatch.setenv("EXPERIMENTAL_ASYNC_TOOLKITS", "true")

    from ibm_watsonx_orchestrate.agent_builder.tools.feature_flags import is_async_enforcement_enabled
    assert is_async_enforcement_enabled() is True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_async_standalone_tool(tmp_dir: str, name: str = "async_tool") -> str:
    """Write a minimal async @tool file into tmp_dir, return its path."""
    tool_src = textwrap.dedent(f"""\
        from ibm_watsonx_orchestrate.agent_builder.tools import tool

        @tool(name='{name}', description='async standalone')
        async def {name}(data: str) -> str:
            '''Async standalone.'''
            return data
    """)
    tool_file = os.path.join(tmp_dir, f"{name}.py")
    open(os.path.join(tmp_dir, "__init__.py"), "w").close()
    with open(tool_file, "w") as f:
        f.write(tool_src)
    return tool_file


# ---------------------------------------------------------------------------
# Integration tests: flag controls what extract_python_tools does
# ---------------------------------------------------------------------------

def test_async_standalone_not_rejected_when_flag_off(monkeypatch):
    """Full extract_python_tools pipeline must accept async standalone when flag is off."""
    monkeypatch.delenv("EXPERIMENTAL_ASYNC_TOOLKITS", raising=False)

    from ibm_watsonx_orchestrate.agent_builder.tools.utils import extract_python_tools

    with tempfile.TemporaryDirectory() as tmp_dir:
        tool_file = _write_async_standalone_tool(tmp_dir, "async_flag_off")
        parent_dir = os.path.dirname(tmp_dir)
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


def test_async_standalone_rejected_when_flag_on(monkeypatch):
    """Full extract_python_tools pipeline must reject async standalone when flag is on."""
    monkeypatch.setenv("EXPERIMENTAL_ASYNC_TOOLKITS", "true")

    from ibm_watsonx_orchestrate.agent_builder.tools.utils import extract_python_tools

    with tempfile.TemporaryDirectory() as tmp_dir:
        tool_file = _write_async_standalone_tool(tmp_dir, "async_flag_on")
        parent_dir = os.path.dirname(tmp_dir)
        original_sys_path = sys.path.copy()
        sys.path.insert(0, parent_dir)
        try:
            with pytest.raises(Exception, match="only supported within toolkits"):
                extract_python_tools(
                    file=tool_file,
                    package_root=tmp_dir,
                    belongs_to_toolkit=False,
                    requirements_file_required=False,
                )
        finally:
            sys.path[:] = original_sys_path


def test_async_toolkit_always_allowed_regardless_of_flag(monkeypatch):
    """Async toolkit tools must be accepted whether the flag is on or off."""
    from ibm_watsonx_orchestrate.agent_builder.tools.utils import extract_python_tools

    for flag_value in (None, "true"):
        if flag_value is None:
            monkeypatch.delenv("EXPERIMENTAL_ASYNC_TOOLKITS", raising=False)
        else:
            monkeypatch.setenv("EXPERIMENTAL_ASYNC_TOOLKITS", flag_value)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tool_file = _write_async_standalone_tool(tmp_dir, "async_toolkit_tool")
            parent_dir = os.path.dirname(tmp_dir)
            original_sys_path = sys.path.copy()
            sys.path.insert(0, parent_dir)
            try:
                # belongs_to_toolkit=True — must always pass
                tools = extract_python_tools(
                    file=tool_file,
                    package_root=tmp_dir,
                    belongs_to_toolkit=True,
                    requirements_file_required=False,
                )
                assert len(tools) == 1
            finally:
                sys.path[:] = original_sys_path
