#!/usr/bin/env python3
"""
Smoke test for async Python tool validation.
Tests that async tools are only allowed in toolkits, not as standalone tools.
"""
import sys
import textwrap
import tempfile
import os
import pytest


def test_async_standalone_tool_decoration_succeeds():
    """Test that async standalone tools are allowed at decoration time.
    Rejection happens later at CLI import time in validate_async_toolkit_requirement()
    inside __get_python_tools_from_file when belongs_to_toolkit=False."""
    from ibm_watsonx_orchestrate.agent_builder.tools import tool

    @tool(name='async_standalone')
    async def async_standalone(data: str) -> str:
        '''Process data asynchronously.'''
        return f"Processed: {data}"

    assert async_standalone.is_async is True
    assert async_standalone.belongs_to_toolkit is False


def test_async_toolkit_tool_should_succeed():
    """Test that async toolkit tools are accepted when belongs_to_toolkit=True."""
    from ibm_watsonx_orchestrate.agent_builder.tools import tool

    @tool(name='async_toolkit')
    async def async_toolkit(data: str) -> str:
        '''Process data asynchronously in a toolkit.'''
        return f"Processed: {data}"

    async_toolkit.belongs_to_toolkit = True  # simulate toolkit import
    spec = async_toolkit.__tool_spec__
    assert spec.is_async, f"Expected is_async=True, got {spec.is_async}"


def test_sync_standalone_tool_should_succeed():
    """Test that sync standalone tools are accepted."""
    from ibm_watsonx_orchestrate.agent_builder.tools import tool
    
    @tool(name='sync_standalone')
    def sync_standalone(data: str) -> str:
        '''Process data synchronously.'''
        return f"Processed: {data}"
    
    spec = sync_standalone.__tool_spec__
    assert not spec.is_async, f"Expected is_async=False, got {spec.is_async}"


def test_async_standalone_with_package_root_should_fail(monkeypatch):
    """Regression test: async standalone tool imported with --package-root must be rejected.

    Previously, import_python_tool set belongs_to_toolkit = package_root is not None, which caused
    extract_python_tools to treat any package-root import as a toolkit import and bypass the
    async restriction.  The fix: belongs_to_toolkit is always False for standalone imports.
    """
    monkeypatch.setenv("WXO_ENABLE_ASYNC_ENFORCEMENT", "true")
    from ibm_watsonx_orchestrate.agent_builder.tools.utils import extract_python_tools

    tool_src = textwrap.dedent("""\
        from ibm_watsonx_orchestrate.agent_builder.tools import tool

        @tool(name='async_with_pkg_root', description='async standalone with package root')
        async def async_with_pkg_root(data: str) -> str:
            '''Should be rejected.'''
            return data
    """)

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a minimal package structure
        init_file = os.path.join(tmp_dir, "__init__.py")
        tool_file = os.path.join(tmp_dir, "async_tool.py")
        with open(init_file, "w") as f:
            f.write("")
        with open(tool_file, "w") as f:
            f.write(tool_src)

        parent_dir = os.path.dirname(tmp_dir)
        # Save sys.path state before modification to ensure clean restoration
        original_sys_path = sys.path.copy()
        sys.path.insert(0, parent_dir)
        try:
            with pytest.raises(Exception, match="Async tools are only supported within toolkits"):
                # belongs_to_toolkit=False — standalone import with package_root must still reject async tools
                extract_python_tools(
                    file=tool_file,
                    package_root=tmp_dir,
                    belongs_to_toolkit=False,
                    requirements_file_required=False,
                )
        finally:
            # Restore sys.path to its original state regardless of any modifications
            sys.path[:] = original_sys_path


# Made with Bob
