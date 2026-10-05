"""
<One-line description of the module under test>

All external dependencies are mocked — tests never touch the filesystem
or a live service.

    TestSubjectA  (N) — <what this group covers>
    TestSubjectB  (N) — <what this group covers>
"""

import pytest
from unittest.mock import patch, MagicMock

from your.module import function_a, function_b, __tools__


# ---------------------------------------------------------------------------
# SECTION 1 — ARRANGE
# Shared constants and fixtures. Nothing here calls the code under test.
# ---------------------------------------------------------------------------

MOCK_DATA = {
    "item_one": {"url": "https://one.example.com"},
    "item_two": {"url": "https://two.example.com"},
}


@pytest.fixture
def mock_dependency():
    """<What this fixture sets up and why it avoids filesystem/network access.>"""
    dep = MagicMock()
    dep.read.return_value = "item_one"   # active item
    dep.get.return_value = MOCK_DATA
    return dep


# ---------------------------------------------------------------------------
# SECTION 2 — REQUIREMENT TESTS
# One class per subject. Each test verifies one stated contract.
# ---------------------------------------------------------------------------

class TestFunctionA:
    # <Why the mock is patched here rather than at the origin module.>

    def test_returns_expected_shape(self, mock_dependency):
        # <What contract this verifies and why it matters.>
        with patch("your.module.Dependency", return_value=mock_dependency):
            result = function_a()

        assert isinstance(result, list)
        assert len(result) == 2

    def test_active_item_flagged(self, mock_dependency):
        with patch("your.module.Dependency", return_value=mock_dependency):
            result = function_a()

        active = [r for r in result if r["active"]]
        assert len(active) == 1
        assert active[0]["name"] == "item_one"

    def test_returns_success_message(self):
        with patch("your.module.dependency_controller.action"):
            result = function_b(name="x", url="https://x.example.com")
        assert "x" in result

    def test_missing_required_param_raises(self):
        with pytest.raises(TypeError):
            function_b(url="https://x.example.com")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# SECTION 3 — EDGE CASE TESTS
# Boundary conditions and error paths surfaced by the static trace.
# ---------------------------------------------------------------------------

class TestFunctionAEdgeCases:

    def test_no_active_item(self):
        # <What edge case this covers — e.g. None returned from dependency.>
        dep = MagicMock()
        dep.read.return_value = None
        dep.get.return_value = MOCK_DATA

        with patch("your.module.Dependency", return_value=dep):
            result = function_a()

        assert not any(r["active"] for r in result)

    def test_conflicting_params_raises(self):
        # <Why these two params are mutually exclusive.>
        with pytest.raises(ValueError, match="param_a.*param_b|param_b.*param_a"):
            function_b(name="x", url="https://x.example.com", param_a=True, param_b="value")
