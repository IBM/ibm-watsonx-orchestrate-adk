#!/usr/bin/env python3
"""
Simulations for the backward-compat guard at utils.py lines 305-308.

Scenario
--------
Tools loaded from an older ADK version pre-date the async feature.  Those
tools are BaseTool subclasses that have neither `belongs_to_toolkit` nor
`validate_async_toolkit_requirement`.

Contract modelled by the guard
------------------------------
If `validate_async_toolkit_requirement` is absent we treat the tool as a
*guaranteed sync* tool (async didn't exist in those ADK versions) and skip
validation — the tool is allowed through unconditionally.

If the method IS present it is called normally, so new async-toolkit tools
still pass and new async-standalone tools are still rejected.
"""
import sys
import textwrap
import tempfile
import os
import pytest


# ---------------------------------------------------------------------------
# Helper — build a realistic legacy BaseTool instance
#
# We borrow the __tool_spec__ from a real @tool-decorated function so we
# never have to construct ToolSpec by hand (which is brittle against Pydantic
# schema changes).  Then we wrap it in a plain BaseTool subclass that has
# none of the new async-feature members.
# ---------------------------------------------------------------------------

def _make_legacy_tool(name: str = "legacy_old_tool"):
    """
    Return a BaseTool instance that looks like it came from an older ADK build:
      - has a valid __tool_spec__   (copied from a real PythonTool)
      - no belongs_to_toolkit attribute
      - no validate_async_toolkit_requirement method
    """
    from ibm_watsonx_orchestrate.agent_builder.tools import tool
    from ibm_watsonx_orchestrate.agent_builder.tools.base_tool import BaseTool

    @tool(name=name, description="legacy tool")
    def _fn(x: str) -> str:
        """legacy."""
        return x

    class LegacyTool(BaseTool):
        """Minimal old-ADK tool — no async feature members at all."""
        pass

    return LegacyTool(_fn.__tool_spec__)


# ---------------------------------------------------------------------------
# Unit-level simulations (no file I/O)
# ---------------------------------------------------------------------------

class TestLegacyToolAttributeSimulation:
    """Prove the guard's contract directly against a legacy-style object."""

    def test_legacy_tool_has_no_validate_method(self):
        """Confirm the simulated legacy tool genuinely lacks the method."""
        obj = _make_legacy_tool()
        assert not hasattr(obj, 'validate_async_toolkit_requirement')

    def test_legacy_tool_has_no_belongs_to_toolkit_attr(self):
        """Confirm the legacy tool has no belongs_to_toolkit at construction time."""
        obj = _make_legacy_tool()
        assert not hasattr(obj, 'belongs_to_toolkit')

    def test_line_305_sets_belongs_to_toolkit_dynamically(self):
        """Line 305: dynamic assignment must create the attr even when absent."""
        obj = _make_legacy_tool()
        obj.belongs_to_toolkit = False          # line 305 equivalent
        assert obj.belongs_to_toolkit is False

    def test_line_306_without_guard_would_raise(self):
        """Prove the *old* bare call crashes — this is exactly the bug the guard fixes."""
        obj = _make_legacy_tool()
        obj.belongs_to_toolkit = False
        with pytest.raises(AttributeError):
            obj.validate_async_toolkit_requirement()   # un-guarded, must raise

    def test_line_306_with_guard_treats_legacy_as_sync_and_passes(self):
        """
        With the guard, a legacy tool without the method is treated as guaranteed
        sync and passes through without error — no AttributeError, no rejection.
        """
        obj = _make_legacy_tool()
        obj.belongs_to_toolkit = False

        # Reproduce lines 305-308 exactly as written in utils.py after the fix
        if hasattr(obj, 'validate_async_toolkit_requirement'):
            obj.validate_async_toolkit_requirement()

        # Reaching here = treated as sync, no crash, no rejection
        assert not hasattr(obj, 'validate_async_toolkit_requirement')


# ---------------------------------------------------------------------------
# Integration-level simulations via extract_python_tools
# ---------------------------------------------------------------------------

def _make_legacy_tool_file_src(fn_name: str) -> str:
    """
    Source for a file that contains a true legacy BaseTool subclass.

    Bypasses PythonTool entirely so neither belongs_to_toolkit nor
    validate_async_toolkit_requirement are ever defined on the class —
    exactly as an old-ADK custom tool would look.

    The __tool_spec__ is bootstrapped by decorating a throwaway PythonTool
    so we never manually construct ToolSpec (avoids Pydantic schema drift).
    """
    return textwrap.dedent(f"""\
        from ibm_watsonx_orchestrate.agent_builder.tools import tool
        from ibm_watsonx_orchestrate.agent_builder.tools.base_tool import BaseTool

        @tool(name="{fn_name}", description="legacy tool")
        def _bootstrap(x: str) -> str:
            '''bootstrap.'''
            return x

        class _LegacyTool(BaseTool):
            pass  # no belongs_to_toolkit, no validate_async_toolkit_requirement

        {fn_name} = _LegacyTool(_bootstrap.__tool_spec__)
        # Remove _bootstrap so the module scanner only sees the one LegacyTool instance
        del _bootstrap
    """)


class TestLegacyToolFileImport:
    """End-to-end: extract_python_tools must import legacy tools without crashing."""

    def _run_extract(self, fn_name: str, belongs_to_toolkit: bool):
        from ibm_watsonx_orchestrate.agent_builder.tools.utils import extract_python_tools

        src = _make_legacy_tool_file_src(fn_name)
        with tempfile.TemporaryDirectory() as tmp_dir:
            tool_file = os.path.join(tmp_dir, f"{fn_name}.py")
            with open(tool_file, "w") as f:
                f.write(src)

            original_path = sys.path.copy()
            sys.path.insert(0, tmp_dir)
            try:
                return extract_python_tools(
                    file=tool_file,
                    belongs_to_toolkit=belongs_to_toolkit,
                    requirements_file_required=False,
                )
            finally:
                sys.path[:] = original_path

    def test_legacy_sync_tool_imported_standalone(self):
        """Legacy tool without the method must load as standalone without error."""
        tools = self._run_extract("legacy_sync_tool", belongs_to_toolkit=False)
        assert len(tools) == 1
        assert tools[0].__tool_spec__.name == "legacy_sync_tool"

    def test_legacy_sync_tool_imported_as_toolkit(self):
        """Same legacy tool imported as part of a toolkit must also load cleanly."""
        tools = self._run_extract("legacy_toolkit_tool", belongs_to_toolkit=True)
        assert len(tools) == 1
        assert tools[0].__tool_spec__.name == "legacy_toolkit_tool"
