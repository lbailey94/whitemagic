# ruff: noqa: BLE001
"""Tests for the Error Pattern Library."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from whitemagic.core.patterns.error_library import (
    AntiPatternEntry,
    ErrorPattern,
    ErrorPatternLibrary,
    SolutionPattern,
    _classify_error,
    _fingerprint,
    _extract_title,
)


@pytest.fixture
def tmp_library(tmp_path):
    """Create a temporary ErrorPatternLibrary."""
    return ErrorPatternLibrary(data_dir=tmp_path)


@pytest.fixture
def sample_mine_output():
    """Sample mining output for ingestion testing."""
    return {
        "total_sessions": 3,
        "errors": {
            "total_count": 5,
            "groups": {
                "timeout": {
                    "count": 2,
                    "items": [
                        {"content": "TimeoutError: operation timed out after 30s", "title": "Session A"},
                        {"content": "subprocess timed out waiting for response", "title": "Session B"},
                    ],
                },
                "connection": {
                    "count": 1,
                    "items": [
                        {"content": "ConnectionRefusedError: connection refused on port 8080", "title": "Session A"},
                    ],
                },
                "import_error": {
                    "count": 1,
                    "items": [
                        {"content": "ImportError: No module named 'whitemagic.nonexistent'", "title": "Session C"},
                    ],
                },
                "other": {
                    "count": 1,
                    "items": [
                        {"content": "Some unknown error occurred during processing", "title": "Session B"},
                    ],
                },
            },
        },
        "recurring_errors": {
            "total_unique_errors": 5,
            "recurring_count": 2,
            "recurring": [
                {"fingerprint": "TimeoutError: operation timed out", "count": 5, "error_type": "timeout"},
                {"fingerprint": "ConnectionRefusedError: connection refused", "count": 3, "error_type": "connection"},
            ],
        },
        "breakthroughs": {
            "count": 2,
            "items": [
                {"title": "Fix Timeout Issue", "content": "Added timeout guard with select.select() 5s timeout on readline()"},
                {"title": "Fix Connection Issue", "content": "Used safe_connect() with WAL mode to prevent connection refused"},
            ],
        },
        "decision_outcomes": {
            "total_decisions": 3,
            "outcome_distribution": {"led_to_error": 2, "led_to_breakthrough": 1, "unknown": 0},
            "decisions": [
                {"decision": "Use raw sqlite3.connect() without WAL mode", "outcome": "led_to_error", "error_similarity": 0.8, "breakthrough_similarity": 0.1},
                {"decision": "Skip timeout guard on subprocess calls", "outcome": "led_to_error", "error_similarity": 0.7, "breakthrough_similarity": 0.2},
                {"decision": "Migrate to safe_connect()", "outcome": "led_to_breakthrough", "error_similarity": 0.1, "breakthrough_similarity": 0.9},
            ],
        },
        "associations": {
            "count": 1,
            "chains": [
                {"decision_title": "Fix Connection Issue", "breakthrough_title": "Fix Connection Issue", "shared_keywords": ["connection", "safe_connect", "wal"]},
            ],
        },
    }


class TestFingerprinting:
    """Test error fingerprinting and classification."""

    def test_fingerprint_stability(self):
        """Same error text produces same fingerprint."""
        text = "ImportError: No module named 'foo'"
        fp1 = _fingerprint(text)
        fp2 = _fingerprint(text)
        assert fp1 == fp2
        assert len(fp1) == 16

    def test_fingerprint_normalizes_file_paths(self):
        """File paths are normalized away in fingerprints."""
        fp1 = _fingerprint("Error in /home/user/project/src/module.py:42")
        fp2 = _fingerprint("Error in /other/path/src/module.py:42")
        assert fp1 == fp2

    def test_fingerprint_normalizes_line_numbers(self):
        """Line numbers are normalized."""
        fp1 = _fingerprint("Error at line 42: something went wrong")
        fp2 = _fingerprint("Error at line 99: something went wrong")
        assert fp1 == fp2

    def test_classify_timeout(self):
        assert _classify_error("TimeoutError: timed out") == "timeout"
        assert _classify_error("operation timed out after 30s") == "timeout"

    def test_classify_connection(self):
        assert _classify_error("ConnectionRefusedError") == "connection"
        assert _classify_error("socket connection reset") == "connection"

    def test_classify_import_error(self):
        assert _classify_error("ImportError: No module named foo") == "import_error"
        assert _classify_error("ModuleNotFoundError") == "import_error"

    def test_classify_attribute_error(self):
        assert _classify_error("AttributeError: object has no attribute") == "attribute_error"

    def test_classify_other(self):
        assert _classify_error("something weird happened") == "other"

    def test_extract_title(self):
        assert _extract_title("Error: something bad\n  detail line") == "Error: something bad"
        assert _extract_title("## summary\nall done") == "all done"


class TestErrorPatternLibrary:
    """Test the ErrorPatternLibrary class."""

    def test_learn_from_error(self, tmp_library):
        """Test learning a single error."""
        fp = tmp_library.learn_from_error("ImportError: No module named 'foo'", session="test")
        assert fp is not None
        assert fp in tmp_library.error_patterns
        assert tmp_library.error_patterns[fp].frequency == 1
        assert tmp_library.error_patterns[fp].category == "import_error"

    def test_learn_from_error_increments_frequency(self, tmp_library):
        """Learning the same error twice increments frequency."""
        text = "TimeoutError: timed out"
        tmp_library.learn_from_error(text, session="A")
        tmp_library.learn_from_error(text, session="B")
        fp = _fingerprint(text)
        assert tmp_library.error_patterns[fp].frequency == 2
        assert "A" in tmp_library.error_patterns[fp].source_sessions
        assert "B" in tmp_library.error_patterns[fp].source_sessions

    def test_learn_from_error_with_resolution(self, tmp_library):
        """Test learning an error with a resolution."""
        tmp_library.learn_from_error(
            "ConnectionRefusedError",
            resolution="Use safe_connect() with WAL mode",
            session="test",
        )
        fp = _fingerprint("ConnectionRefusedError")
        assert tmp_library.error_patterns[fp].resolution == "Use safe_connect() with WAL mode"

    def test_persistence(self, tmp_path):
        """Test that patterns persist to disk."""
        lib1 = ErrorPatternLibrary(data_dir=tmp_path)
        lib1.learn_from_error("ImportError: No module named 'foo'", session="test")

        # Create new instance — should load from disk
        lib2 = ErrorPatternLibrary(data_dir=tmp_path)
        fp = _fingerprint("ImportError: No module named 'foo'")
        assert fp in lib2.error_patterns
        assert lib2.error_patterns[fp].frequency == 1

    def test_learn_from_mining(self, tmp_library, sample_mine_output):
        """Test ingesting a full mining output."""
        stats = tmp_library.learn_from_mining(sample_mine_output)
        assert stats["errors_learned"] == 5
        assert stats["recurring_learned"] == 2
        assert stats["anti_patterns_learned"] == 2
        assert stats["solutions_learned"] == 2
        assert stats["associations_linked"] >= 0

    def test_learn_from_mining_links_resolutions(self, tmp_library, sample_mine_output):
        """Test that association chains link resolutions to error patterns."""
        tmp_library.learn_from_mining(sample_mine_output)
        # At least some error patterns should have resolutions from breakthroughs
        resolved = [ep for ep in tmp_library.error_patterns.values() if ep.resolution]
        assert len(resolved) > 0

    def test_learn_from_mining_creates_anti_patterns(self, tmp_library, sample_mine_output):
        """Test that failed decisions become anti-patterns."""
        tmp_library.learn_from_mining(sample_mine_output)
        assert len(tmp_library.anti_patterns) == 2
        for ap in tmp_library.anti_patterns.values():
            assert ap.category == "decision"
            assert ap.source == "session_mining"

    def test_learn_from_mining_creates_solutions(self, tmp_library, sample_mine_output):
        """Test that breakthroughs become solutions."""
        tmp_library.learn_from_mining(sample_mine_output)
        assert len(tmp_library.solutions) == 2

    def test_lookup_exact_match(self, tmp_library):
        """Test exact fingerprint match lookup."""
        tmp_library.learn_from_error("ImportError: No module named 'foo'", session="test")
        result = tmp_library.lookup("ImportError: No module named 'foo'")
        assert result is not None
        assert result["category"] == "import_error"

    def test_lookup_fuzzy_match(self, tmp_library):
        """Test fuzzy category+keyword match."""
        tmp_library.learn_from_error("TimeoutError: operation timed out after 30 seconds", session="test")
        # Different text but same category and some shared words
        result = tmp_library.lookup("TimeoutError: timed out waiting for response")
        assert result is not None
        assert result["match_type"] == "fuzzy"

    def test_lookup_no_match(self, tmp_library):
        """Test lookup with no matching pattern."""
        result = tmp_library.lookup("completely unrelated error message about unicorns")
        assert result is None

    def test_resolve_with_resolution(self, tmp_library):
        """Test resolve when a resolution exists."""
        tmp_library.learn_from_error(
            "ConnectionRefusedError: connection refused",
            resolution="Use safe_connect() with WAL mode",
            session="test",
        )
        result = tmp_library.resolve("ConnectionRefusedError: connection refused")
        assert result["status"] == "resolved"
        assert "safe_connect" in result["resolution"]

    def test_resolve_without_resolution(self, tmp_library):
        """Test resolve when no resolution exists."""
        tmp_library.learn_from_error("TimeoutError: timed out", session="test")
        result = tmp_library.resolve("TimeoutError: timed out")
        assert result["status"] == "unresolved"
        assert result["frequency"] == 1

    def test_resolve_not_found(self, tmp_library):
        """Test resolve when error is not in library."""
        result = tmp_library.resolve("completely unknown error about unicorns")
        assert result["status"] == "not_found"

    def test_avoid_returns_relevant_patterns(self, tmp_library):
        """Test avoid returns patterns relevant to context."""
        tmp_library.learn_from_error("TimeoutError: subprocess timed out", session="A")
        tmp_library.learn_from_error("ImportError: No module named 'foo'", session="B")
        result = tmp_library.avoid("working with subprocess calls and timeouts")
        assert result["status"] == "success"
        assert len(result["error_patterns_to_avoid"]) > 0
        # Timeout error should be more relevant than import error
        top = result["error_patterns_to_avoid"][0]
        assert "timeout" in top["category"] or "subprocess" in top["title"].lower()

    def test_list_patterns(self, tmp_library):
        """Test listing patterns."""
        tmp_library.learn_from_error("TimeoutError: timed out", session="A")
        tmp_library.learn_from_error("ImportError: no module", session="B")
        result = tmp_library.list_patterns()
        assert result["total_error_patterns"] == 2
        assert len(result["error_patterns"]) == 2

    def test_list_patterns_by_category(self, tmp_library):
        """Test listing patterns filtered by category."""
        tmp_library.learn_from_error("TimeoutError: timed out", session="A")
        tmp_library.learn_from_error("ImportError: no module", session="B")
        result = tmp_library.list_patterns(category="timeout")
        assert len(result["error_patterns"]) == 1
        assert result["error_patterns"][0]["category"] == "timeout"

    def test_summary(self, tmp_library):
        """Test summary statistics."""
        tmp_library.learn_from_error("TimeoutError: timed out", resolution="add guard", session="A")
        tmp_library.learn_from_error("ImportError: no module", session="B")
        summary = tmp_library.summary()
        assert summary["total_error_patterns"] == 2
        assert summary["resolved"] == 1
        assert summary["unresolved"] == 1

    def test_learn_from_strata(self, tmp_library):
        """Test ingesting STRATA findings."""
        findings = [
            {"category": "dead_code", "message": "Function 'foo' may be unused", "suggestion": "Remove or export", "severity": "error"},
            {"category": "structural_stub", "message": "Empty function body", "suggestion": "Implement or raise NotImplementedError", "severity": "error"},
            {"category": "todo_style", "message": "TODO found", "suggestion": "Use issue tracker", "severity": "warning"},
        ]
        count = tmp_library.learn_from_strata(findings)
        assert count == 2  # Only error severity
        assert len(tmp_library.anti_patterns) == 2

    def test_empty_text_not_learned(self, tmp_library):
        """Test that empty or tiny text is not learned."""
        fp = tmp_library.learn_from_error("", session="test")
        assert fp == ""
        assert len(tmp_library.error_patterns) == 0

    def test_category_summary(self, tmp_library):
        """Test category summary counts."""
        tmp_library.learn_from_error("TimeoutError: timed out", session="A")
        tmp_library.learn_from_error("TimeoutError: another timeout", session="B")
        tmp_library.learn_from_error("ImportError: no module", session="C")
        summary = tmp_library.summary()
        assert summary["categories"]["timeout"] == 2
        assert summary["categories"]["import_error"] == 1
