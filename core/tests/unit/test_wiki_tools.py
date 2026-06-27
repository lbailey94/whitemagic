# ruff: noqa: BLE001
"""Tests for the internal wiki and external repo tools."""

import os
import tempfile

import pytest

# Isolate from production state root before importing WM modules
os.environ["WM_STATE_ROOT"] = tempfile.mkdtemp(prefix="wm_wiki_test_")

from whitemagic.tools.handlers.wiki import (  # noqa: E402
    _get_db,
    handle_wiki_generate,
    handle_wiki_query,
    handle_wiki_scan,
    handle_wiki_stats,
    handle_wiki_update,
)


@pytest.fixture(autouse=True)
def _clean_wiki_db():
    """Clear wiki table before each test."""
    conn = _get_db()
    conn.execute("DELETE FROM internal_wiki")
    conn.commit()
    conn.close()
    yield
    conn = _get_db()
    conn.execute("DELETE FROM internal_wiki")
    conn.commit()
    conn.close()


class TestWikiGenerate:
    """Tests for wiki.generate handler."""

    def test_generate_stats_only(self):
        """wiki.stats on empty db returns zeros."""
        result = handle_wiki_stats()
        assert result["status"] == "success"
        assert result["total_entries"] == 0

    def test_generate_ganas(self):
        """Generate wiki entries from PRAT Ganas."""
        result = handle_wiki_generate(scope="ganas", force=True)
        assert result["status"] == "success"
        assert result["scope"] == "ganas"
        # Should have generated at least 20+ gana entries
        assert result["generated"] > 0

    def test_generate_tools(self):
        """Generate wiki entry for tool registry."""
        result = handle_wiki_generate(scope="tools", force=True)
        assert result["status"] == "success"
        assert result["generated"] >= 1

    def test_generate_all(self):
        """Generate all wiki entries."""
        result = handle_wiki_generate(scope="all", force=True)
        assert result["status"] == "success"
        assert result["generated"] > 0
        assert result["total_entries"] > 0

    def test_generate_idempotent_without_force(self):
        """Second generate without force should skip existing entries."""
        handle_wiki_generate(scope="ganas", force=True)
        result = handle_wiki_generate(scope="ganas", force=False)
        assert result["status"] == "success"
        assert result["skipped"] > 0
        assert result["generated"] == 0


class TestWikiQuery:
    """Tests for wiki.query handler."""

    def test_query_empty(self):
        """Query on empty wiki returns no results."""
        result = handle_wiki_query(query="test")
        assert result["status"] == "success"
        assert result["count"] == 0

    def test_query_after_generate(self):
        """Query after generating ganas finds results."""
        handle_wiki_generate(scope="ganas", force=True)
        result = handle_wiki_query(category="architecture")
        assert result["status"] == "success"
        assert result["count"] > 0

    def test_query_by_tag(self):
        """Query by tag filters correctly."""
        handle_wiki_generate(scope="ganas", force=True)
        result = handle_wiki_query(tags="prat")
        assert result["status"] == "success"
        assert result["count"] > 0

    def test_query_limit(self):
        """Query respects limit parameter."""
        handle_wiki_generate(scope="ganas", force=True)
        result = handle_wiki_query(limit=3)
        assert result["status"] == "success"
        assert result["count"] <= 3


class TestWikiUpdate:
    """Tests for wiki.update handler."""

    def test_update_new_entry(self):
        """Create a new entry via update."""
        result = handle_wiki_update(
            title="Test Guide",
            content="# Test Guide\nThis is a test.",
            category="guide",
            tags="test,guide",
        )
        assert result["status"] == "success"
        assert result["action"] == "created"

    def test_update_existing_entry(self):
        """Update an existing entry."""
        handle_wiki_update(
            title="Test Guide",
            content="# Original",
            category="guide",
        )
        result = handle_wiki_update(
            title="Test Guide",
            content="# Updated",
            category="guide",
        )
        assert result["status"] == "success"
        assert result["action"] == "updated"

    def test_update_missing_content(self):
        """Update without content returns error."""
        result = handle_wiki_update(title="Test")
        assert result["status"] == "error"
        assert result["error_code"] == "missing_content"

    def test_update_invalid_category(self):
        """Update with invalid category returns error."""
        result = handle_wiki_update(
            title="Test",
            content="content",
            category="invalid",
        )
        assert result["status"] == "error"
        assert result["error_code"] == "invalid_category"


class TestWikiScan:
    """Tests for wiki.scan handler."""

    def test_scan_empty(self):
        """Scan on empty wiki returns zeros."""
        result = handle_wiki_scan()
        assert result["status"] == "success"
        assert result["total_entries"] == 0

    def test_scan_after_generate(self):
        """Scan after generate finds entries."""
        handle_wiki_generate(scope="ganas", force=True)
        result = handle_wiki_scan()
        assert result["status"] == "success"
        assert result["total_entries"] > 0


class TestWikiStats:
    """Tests for wiki.stats handler."""

    def test_stats_empty(self):
        """Stats on empty wiki."""
        result = handle_wiki_stats()
        assert result["status"] == "success"
        assert result["total_entries"] == 0

    def test_stats_after_generate(self):
        """Stats after generate shows entries."""
        handle_wiki_generate(scope="ganas", force=True)
        result = handle_wiki_stats()
        assert result["status"] == "success"
        assert result["total_entries"] > 0
        assert "architecture" in result["by_category"]


class TestExternalRepo:
    """Tests for external repo handlers."""

    def test_wiki_query_missing_params(self):
        """External wiki query without params returns error."""
        from whitemagic.tools.handlers.external_repo import (
            handle_external_wiki_query,
        )
        result = handle_external_wiki_query()
        assert result["status"] == "error"
        assert result["error_code"] == "missing_params"

    def test_wiki_query_returns_guidance(self):
        """External wiki query returns guidance when DeepWiki not configured."""
        from whitemagic.tools.handlers.external_repo import (
            handle_external_wiki_query,
        )
        result = handle_external_wiki_query(
            repo="modelcontextprotocol/python-sdk",
            question="How does the server work?",
        )
        assert result["status"] == "success"
        assert result["deepwiki_url"] == "https://deepwiki.com/modelcontextprotocol/python-sdk"

    def test_repo_scan_missing_params(self):
        """External repo scan without repo returns error."""
        from whitemagic.tools.handlers.external_repo import (
            handle_external_repo_scan,
        )
        result = handle_external_repo_scan()
        assert result["status"] == "error"
        assert result["error_code"] == "missing_params"

    def test_repo_compare_missing_params(self):
        """External repo compare without params returns error."""
        from whitemagic.tools.handlers.external_repo import (
            handle_external_repo_compare,
        )
        result = handle_external_repo_compare()
        assert result["status"] == "error"
        assert result["error_code"] == "missing_params"
