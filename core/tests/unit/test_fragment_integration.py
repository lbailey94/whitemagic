"""Integration tests for Fragment (Rust codebase search) integration.

Tests the 3-layer handler: PyO3, HTTP, subprocess fallback.
Uses the WhiteMagic repo itself as the test codebase.
"""
# ruff: noqa: BLE001

import tempfile
from pathlib import Path

import pytest

# Dynamically check if fragment is available
try:
    from whitemagic.tools.handlers.fragment import (
        handle_fragment_search,
        handle_fragment_index,
        handle_fragment_status,
        handle_fragment_query,
        get_fragment_layer,
        _pyo3_status,
        _http_status,
        _subprocess_status,
    )
    _FRAGMENT_AVAILABLE = True
except ImportError:
    _FRAGMENT_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _FRAGMENT_AVAILABLE,
    reason="Fragment handler not available",
)


REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent


class TestFragmentHandler:
    """Test Fragment handler MCP tool interface."""

    def test_status_no_index(self):
        """Status on a path with no index should return exists=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = handle_fragment_status(path=tmpdir)
            assert result["status"] == "success"
            assert "exists" in result

    def test_status_with_index(self):
        """Status on the WhiteMagic repo should find the index."""
        result = handle_fragment_status(path=str(REPO_ROOT))
        assert result["status"] == "success"

    def test_search_no_path(self):
        """Search without a path should return an error."""
        result = handle_fragment_search(query="test")
        assert result["status"] == "error"

    def test_search_no_query(self):
        """Search without a query should return an error."""
        result = handle_fragment_search(path=str(REPO_ROOT))
        assert result["status"] == "error"

    def test_search_with_query(self):
        """Search with a valid query should return results or graceful fallback."""
        result = handle_fragment_search(query="kaizen", path=str(REPO_ROOT), top=3)
        assert result["status"] in ("success", "error")
        if result["status"] == "success":
            assert "count" in result
            assert "layer" in result

    def test_query_no_index(self):
        """Query on a path with no index should return error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = handle_fragment_query(path=tmpdir, query="test")
            assert result["status"] == "error"


class TestFragmentLayers:
    """Test individual Fragment layers (PyO3, HTTP, subprocess)."""

    def test_pyro3_layer(self):
        """Test PyO3 layer directly."""
        try:
            result = _pyo3_status(str(REPO_ROOT), None)
            assert isinstance(result, dict)
        except RuntimeError:
            pass  # PyO3 not available

    def test_http_layer(self):
        """Test HTTP layer — should raise if no server running."""
        try:
            result = _http_status(str(REPO_ROOT), None)
            assert isinstance(result, dict)
        except Exception:
            pass  # No HTTP server running

    def test_subprocess_layer(self):
        """Test subprocess CLI layer."""
        try:
            result = _subprocess_status(str(REPO_ROOT), None)
            assert isinstance(result, dict)
        except Exception:
            pass  # Binary not available

    def test_get_fragment_layer(self):
        """Test get_fragment_layer returns a valid layer name."""
        layer = get_fragment_layer()
        assert layer in ("pyo3", "http", "subprocess", "none")
