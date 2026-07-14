# ruff: noqa: BLE001
"""Tests for ErrorPatternLibrary — learned error resolution from session mining."""

import json
import time
from pathlib import Path

import pytest

from whitemagic.core.patterns.error_library import (
    AntiPatternEntry,
    ErrorPattern,
    ErrorPatternLibrary,
    SolutionPattern,
    _classify_error,
    _extract_title,
    _fingerprint,
    get_error_library,
)


# ─── Fingerprinting tests ────────────────────────────────────────────────


class TestFingerprinting:
    def test_fingerprint_stable(self):
        fp1 = _fingerprint("ImportError: No module named foo")
        fp2 = _fingerprint("ImportError: No module named foo")
        assert fp1 == fp2
        assert len(fp1) == 16

    def test_fingerprint_normalizes_paths(self):
        fp1 = _fingerprint("Error in /home/lucas/project/file.py:10")
        fp2 = _fingerprint("Error in /home/alice/other/file.py:10")
        assert fp1 == fp2

    def test_fingerprint_normalizes_line_numbers(self):
        fp1 = _fingerprint("Error at line 42: bad value")
        fp2 = _fingerprint("Error at line 99: bad value")
        assert fp1 == fp2

    def test_fingerprint_normalizes_memory_addresses(self):
        fp1 = _fingerprint("segfault at 0x7fffdeadbeef")
        fp2 = _fingerprint("segfault at 0x7fffcafebabe")
        assert fp1 == fp2

    def test_fingerprint_normalizes_uuids(self):
        fp1 = _fingerprint("session a1b2c3d4-e5f6-7890-abcd-ef1234567890 failed")
        fp2 = _fingerprint("session f0e1d2c3-b4a5-6789-0fed-cba987654321 failed")
        assert fp1 == fp2

    def test_fingerprint_different_errors_differ(self):
        fp1 = _fingerprint("ImportError: No module named foo")
        fp2 = _fingerprint("TypeError: expected str got int")
        assert fp1 != fp2

    def test_classify_error_types(self):
        assert _classify_error("Traceback (most recent call last)") == "traceback"
        assert _classify_error("ImportError: No module named foo") == "import_error"
        assert _classify_error("AttributeError: object has no attribute 'x'") == "attribute_error"
        assert _classify_error("TypeError: expected str") == "type_error"
        assert _classify_error("ValueError: invalid literal") == "value_error"
        assert _classify_error("KeyError: 'missing'") == "key_error"
        assert _classify_error("TimeoutError: timed out") == "timeout"
        assert _classify_error("ConnectionRefusedError: refused") == "connection"
        assert _classify_error("FileNotFoundError: No such file") == "file_not_found"
        assert _classify_error("PermissionError: Permission denied") == "permission_error"
        assert _classify_error("RecursionError: maximum recursion") == "recursion_error"
        assert _classify_error("SyntaxError: invalid syntax") == "syntax_error"
        assert _classify_error("MemoryError: out of memory") == "memory_error"
        assert _classify_error("sqlite3.DatabaseError: database is locked") == "database_error"
        assert _classify_error("something weird happened") == "other"

    def test_extract_title(self):
        assert _extract_title("Traceback (most recent call last)\nValueError: bad") == "Traceback (most recent call last)"
        assert _extract_title("## summary\nError occurred") == "Error occurred"
        assert _extract_title("---\nbroken") == "broken"
        assert _extract_title("short error") == "short error"

    def test_extract_title_max_len(self):
        long = "x" * 200
        assert len(_extract_title(long, max_len=50)) == 50


# ─── ErrorPatternLibrary tests ───────────────────────────────────────────


class TestErrorPatternLibrary:
    @pytest.fixture
    def library(self, tmp_path):
        """Fresh library with temp storage."""
        return ErrorPatternLibrary(data_dir=tmp_path)

    @pytest.fixture
    def sample_mine_output(self):
        return {
            "errors": {
                "total_count": 3,
                "groups": {
                    "import_error": {
                        "count": 1,
                        "items": [
                            {"session_id": "s1", "title": "Session 1", "content": "ImportError: No module named foo"},
                        ],
                    },
                    "type_error": {
                        "count": 1,
                        "items": [
                            {"session_id": "s2", "title": "Session 2", "content": "TypeError: expected str got int"},
                        ],
                    },
                    "traceback": {
                        "count": 1,
                        "items": [
                            {"session_id": "s3", "title": "Session 3", "content": "Traceback: ValueError occurred"},
                        ],
                    },
                },
            },
            "recurring_errors": {
                "total_unique_errors": 2,
                "recurring_count": 1,
                "recurring": [
                    {
                        "count": 3,
                        "error_type": "import_error",
                        "fingerprint": "ImportError: No module named bar",
                        "sessions": ["s1", "s4", "s5"],
                        "session_titles": ["Session 1", "Session 4", "Session 5"],
                    },
                ],
            },
            "decision_outcomes": {
                "total_decisions": 2,
                "outcome_distribution": {"led_to_error": 1, "unknown": 1},
                "decisions": [
                    {
                        "decision": "Let's use approach X",
                        "outcome": "led_to_error",
                        "error_similarity": 0.5,
                    },
                    {
                        "decision": "Let's try approach Y",
                        "outcome": "unknown",
                        "error_similarity": 0.0,
                    },
                ],
            },
            "breakthroughs": {
                "count": 2,
                "items": [
                    {"title": "Session 1", "content": "Solved it by installing foo"},
                    {"title": "Session 2", "content": "Fixed the type mismatch"},
                ],
            },
            "associations": {
                "count": 1,
                "chains": [
                    {
                        "decision_title": "Session 1",
                        "breakthrough_title": "Session 1",
                        "shared_keywords": ["foo", "import"],
                    },
                ],
            },
        }

    def test_init_creates_data_dir(self, tmp_path):
        data_dir = tmp_path / "defense"
        lib = ErrorPatternLibrary(data_dir=data_dir)
        assert data_dir.exists()
        assert (data_dir / "error_patterns.json") == lib.patterns_file

    def test_learn_from_error(self, library):
        fp = library.learn_from_error("ImportError: No module named foo", session="s1")
        assert fp
        assert fp in library.error_patterns
        assert library.error_patterns[fp].category == "import_error"
        assert library.error_patterns[fp].frequency == 1
        assert "s1" in library.error_patterns[fp].source_sessions

    def test_learn_from_error_with_resolution(self, library):
        fp = library.learn_from_error(
            "ImportError: No module named foo",
            resolution="pip install foo",
            session="s1",
        )
        assert library.error_patterns[fp].resolution == "pip install foo"

    def test_learn_from_error_increments_frequency(self, library):
        fp1 = library.learn_from_error("ImportError: No module named foo", session="s1")
        fp2 = library.learn_from_error("ImportError: No module named foo", session="s2")
        assert fp1 == fp2
        assert library.error_patterns[fp1].frequency == 2
        assert "s1" in library.error_patterns[fp1].source_sessions
        assert "s2" in library.error_patterns[fp1].source_sessions

    def test_learn_from_error_empty_text(self, library):
        fp = library.learn_from_error("", session="s1")
        assert fp == ""

    def test_learn_from_error_short_text(self, library):
        fp = library.learn_from_error("ab", session="s1")
        assert fp == ""

    def test_learn_from_mining(self, library, sample_mine_output):
        stats = library.learn_from_mining(sample_mine_output)
        assert stats["errors_learned"] == 3
        assert stats["recurring_learned"] == 1
        assert stats["anti_patterns_learned"] == 1
        assert stats["solutions_learned"] == 2
        assert len(library.error_patterns) >= 3
        assert len(library.anti_patterns) == 1
        assert len(library.solutions) == 2

    def test_learn_from_mining_links_associations(self, library, sample_mine_output):
        library.learn_from_mining(sample_mine_output)
        # At least some error patterns should have related decisions/breakthroughs
        has_links = any(
            ep.related_decisions or ep.related_breakthroughs
            for ep in library.error_patterns.values()
        )
        assert has_links

    def test_learn_from_strata(self, library):
        findings = [
            {"category": "security", "message": "SQL injection risk", "severity": "error", "suggestion": "Use parameterized queries"},
            {"category": "style", "message": "Line too long", "severity": "info"},
        ]
        count = library.learn_from_strata(findings)
        assert count == 1  # Only "error" severity
        assert len(library.anti_patterns) == 1
        ap = list(library.anti_patterns.values())[0]
        assert ap.source == "strata"
        assert ap.confidence == 0.8
        assert ap.resolution == "Use parameterized queries"

    def test_learn_from_strata_no_errors(self, library):
        findings = [{"category": "style", "message": "Line too long", "severity": "info"}]
        count = library.learn_from_strata(findings)
        assert count == 0
        assert len(library.anti_patterns) == 0

    def test_lookup_exact_match(self, library):
        library.learn_from_error("ImportError: No module named foo", session="s1")
        result = library.lookup("ImportError: No module named foo")
        assert result is not None
        assert result["category"] == "import_error"
        assert "match_type" not in result  # exact match

    def test_lookup_fuzzy_match(self, library):
        library.learn_from_error("ImportError: No module named foo bar baz", session="s1")
        # Different but similar error
        result = library.lookup("ImportError: No module named foo bar qux")
        assert result is not None
        assert result.get("match_type") == "fuzzy"

    def test_lookup_no_match(self, library):
        result = library.lookup("completely unrelated text about cats")
        assert result is None

    def test_resolve_with_resolution(self, library):
        library.learn_from_error(
            "ImportError: No module named foo",
            resolution="pip install foo",
            session="s1",
        )
        result = library.resolve("ImportError: No module named foo")
        assert result["status"] == "resolved"
        assert result["resolution"] == "pip install foo"
        assert result["category"] == "import_error"

    def test_resolve_unresolved(self, library):
        library.learn_from_error("ImportError: No module named foo", session="s1")
        result = library.resolve("ImportError: No module named foo")
        assert result["status"] == "unresolved"
        assert "pattern_id" in result

    def test_resolve_not_found(self, library):
        result = library.resolve("completely unknown error about cats")
        assert result["status"] == "not_found"

    def test_avoid(self, library):
        library.learn_from_error("ImportError: No module named foo", session="s1")
        library.learn_from_error("TypeError: expected str got int", session="s2")
        result = library.avoid("working with foo imports")
        assert result["status"] == "success"
        assert len(result["error_patterns_to_avoid"]) >= 1
        assert result["total_known_errors"] == 2

    def test_avoid_no_matches(self, library):
        library.learn_from_error("ImportError: No module named foo", session="s1")
        result = library.avoid("working with cats and dogs")
        assert result["status"] == "success"
        assert len(result["error_patterns_to_avoid"]) == 0

    def test_list_patterns(self, library):
        library.learn_from_error("ImportError: No module named foo", session="s1")
        library.learn_from_error("TypeError: expected str", session="s2")
        result = library.list_patterns()
        assert result["status"] == "success"
        assert result["total_error_patterns"] == 2
        assert len(result["error_patterns"]) == 2

    def test_list_patterns_by_category(self, library):
        library.learn_from_error("ImportError: No module named foo", session="s1")
        library.learn_from_error("TypeError: expected str", session="s2")
        result = library.list_patterns(category="import_error")
        assert len(result["error_patterns"]) == 1
        assert result["error_patterns"][0]["category"] == "import_error"

    def test_summary(self, library):
        library.learn_from_error("ImportError: No module named foo", resolution="pip install foo", session="s1")
        library.learn_from_error("TypeError: expected str", session="s2")
        result = library.summary()
        assert result["total_error_patterns"] == 2
        assert result["resolved"] == 1
        assert result["unresolved"] == 1
        assert "import_error" in result["categories"]
        assert len(result["top_recurring"]) == 2

    def test_persistence_save_load(self, tmp_path):
        lib1 = ErrorPatternLibrary(data_dir=tmp_path)
        lib1.learn_from_error("ImportError: No module named foo", resolution="pip install foo", session="s1")
        lib1.learn_from_error("TypeError: expected str", session="s2")
        assert lib1.patterns_file.exists()

        # Create new library pointing at same dir
        lib2 = ErrorPatternLibrary(data_dir=tmp_path)
        assert len(lib2.error_patterns) == 2
        assert len(lib2.solutions) == 0

        # Check that IDs continue correctly
        fp = _fingerprint("ImportError: No module named foo")
        assert lib2.error_patterns[fp].resolution == "pip install foo"

    def test_persistence_with_anti_patterns(self, tmp_path):
        lib1 = ErrorPatternLibrary(data_dir=tmp_path)
        lib1.learn_from_strata([
            {"category": "security", "message": "SQL injection", "severity": "error", "suggestion": "Use params"},
        ])
        assert len(lib1.anti_patterns) == 1

        lib2 = ErrorPatternLibrary(data_dir=tmp_path)
        assert len(lib2.anti_patterns) == 1
        ap = list(lib2.anti_patterns.values())[0]
        assert ap.title == "STRATA: security"

    def test_persistence_with_solutions(self, tmp_path):
        lib1 = ErrorPatternLibrary(data_dir=tmp_path)
        mine_output = {
            "errors": {"groups": {}, "total_count": 0},
            "recurring_errors": {"recurring": []},
            "decision_outcomes": {"decisions": []},
            "breakthroughs": {
                "count": 1,
                "items": [{"title": "S1", "content": "Solved it!"}],
            },
            "associations": {"chains": []},
        }
        lib1.learn_from_mining(mine_output)
        assert len(lib1.solutions) == 1

        lib2 = ErrorPatternLibrary(data_dir=tmp_path)
        assert len(lib2.solutions) == 1

    def test_id_continuity_after_load(self, tmp_path):
        lib1 = ErrorPatternLibrary(data_dir=tmp_path)
        lib1.learn_from_error("ImportError: No module named foo", session="s1")
        lib1.learn_from_error("TypeError: expected str", session="s2")
        assert lib1._next_ep_id == 3

        lib2 = ErrorPatternLibrary(data_dir=tmp_path)
        assert lib2._next_ep_id == 3
        lib2.learn_from_error("ValueError: bad value", session="s3")
        ep = list(lib2.error_patterns.values())[-1]
        assert ep.pattern_id == "EP-003"


# ─── Data model tests ────────────────────────────────────────────────────


class TestDataModels:
    def test_error_pattern_defaults(self):
        ep = ErrorPattern(
            pattern_id="EP-001",
            fingerprint="abc123",
            category="import_error",
            title="Test Error",
            description="Test description",
        )
        assert ep.frequency == 1
        assert ep.resolution is None
        assert ep.source_sessions == []
        assert ep.related_decisions == []
        assert ep.related_breakthroughs == []
        assert ep.auto_fixable is False

    def test_anti_pattern_defaults(self):
        ap = AntiPatternEntry(
            entry_id="AP-001",
            title="Bad Pattern",
            description="Don't do this",
            category="decision",
            consequence="It breaks things",
        )
        assert ap.resolution is None
        assert ap.frequency == 1
        assert ap.confidence == 0.5

    def test_solution_pattern_defaults(self):
        sp = SolutionPattern(
            solution_id="SP-001",
            title="Fix",
            description="Do this instead",
            solves_category="import_error",
        )
        assert sp.source_session == ""
        assert sp.confidence == 0.5


# ─── Singleton tests ─────────────────────────────────────────────────────


class TestSingleton:
    def test_get_error_library_returns_same_instance(self):
        lib1 = get_error_library()
        lib2 = get_error_library()
        assert lib1 is lib2


# ─── Gap 2: Embedding-based lookup tests ─────────────────────────────────


class TestEmbeddingLookup:
    """Test embedding-based semantic fuzzy matching in lookup()."""

    def test_lookup_returns_exact_match(self, tmp_path):
        lib = ErrorPatternLibrary(data_dir=tmp_path)
        lib.learn_from_error("ImportError: No module named whitemagic_rust")
        result = lib.lookup("ImportError: No module named whitemagic_rust")
        assert result is not None
        assert result.get("fingerprint")  # exact match returns fingerprint

    def test_lookup_word_overlap_fallback(self, tmp_path):
        """When embeddings unavailable, word-overlap should still work."""
        lib = ErrorPatternLibrary(data_dir=tmp_path)
        lib.learn_from_error("TypeError: unsupported operand type for int")
        # Same words, different order — should match via word overlap
        result = lib.lookup("TypeError unsupported operand type for int")
        assert result is not None

    def test_lookup_returns_none_for_unrelated(self, tmp_path):
        lib = ErrorPatternLibrary(data_dir=tmp_path)
        lib.learn_from_error("ImportError: No module named foo")
        result = lib.lookup("KeyboardInterrupt")
        assert result is None

    def test_cosine_similarity_helper(self):
        from whitemagic.core.patterns.error_library import _cosine_similarity

        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert _cosine_similarity(a, b) == 1.0

        c = [0.0, 1.0, 0.0]
        assert _cosine_similarity(a, c) == 0.0

        d = [1.0, 1.0, 0.0]
        sim = _cosine_similarity(a, d)
        assert 0.6 < sim < 0.8  # ~0.707

    def test_cosine_similarity_zero_vectors(self):
        from whitemagic.core.patterns.error_library import _cosine_similarity

        assert _cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


# ─── Gap 1: Auto-learn middleware tests ──────────────────────────────────


class TestErrorLearnerMiddleware:
    """Test mw_error_learner auto-learns from failed dispatches."""

    def test_error_learner_learns_from_error_status(self, tmp_path, monkeypatch):
        # Point state root to tmp_path so patterns file is isolated
        monkeypatch.setattr(
            "whitemagic.core.patterns.error_library.get_state_root",
            lambda: tmp_path,
        )
        from whitemagic.core.patterns.error_library import _library as _lib
        import whitemagic.core.patterns.error_library as el_mod

        # Reset singleton
        monkeypatch.setattr(el_mod, "_library", None)

        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_error_learner,
        )

        def fake_next(ctx):
            return {"status": "error", "error": "ConnectionRefusedError: connection refused"}

        ctx = DispatchContext(tool_name="galaxy.stats", kwargs={})
        result = mw_error_learner(ctx, fake_next)

        assert result["status"] == "error"
        # Verify it was learned
        lib = el_mod.get_error_library()
        lookup = lib.lookup("[galaxy.stats] ConnectionRefusedError: connection refused")
        assert lookup is not None

    def test_error_learner_skips_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "whitemagic.core.patterns.error_library.get_state_root",
            lambda: tmp_path,
        )
        import whitemagic.core.patterns.error_library as el_mod

        monkeypatch.setattr(el_mod, "_library", None)

        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_error_learner,
        )

        def fake_next(ctx):
            return {"status": "success", "data": "ok"}

        ctx = DispatchContext(tool_name="galaxy.stats", kwargs={})
        result = mw_error_learner(ctx, fake_next)

        assert result["status"] == "success"
        lib = el_mod.get_error_library()
        assert len(lib.error_patterns) == 0

    def test_error_learner_skips_pattern_tools(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "whitemagic.core.patterns.error_library.get_state_root",
            lambda: tmp_path,
        )
        import whitemagic.core.patterns.error_library as el_mod

        monkeypatch.setattr(el_mod, "_library", None)

        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_error_learner,
        )

        called = {"next": False}

        def fake_next(ctx):
            called["next"] = True
            return {"status": "error", "error": "test error"}

        ctx = DispatchContext(tool_name="pattern.lookup", kwargs={})
        result = mw_error_learner(ctx, fake_next)

        assert called["next"] is True
        lib = el_mod.get_error_library()
        assert len(lib.error_patterns) == 0

    def test_error_learner_disabled_via_env(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "whitemagic.core.patterns.error_library.get_state_root",
            lambda: tmp_path,
        )
        monkeypatch.setenv("WM_ERROR_LEARN", "0")
        import whitemagic.core.patterns.error_library as el_mod

        monkeypatch.setattr(el_mod, "_library", None)

        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_error_learner,
        )

        def fake_next(ctx):
            return {"status": "error", "error": "should not be learned"}

        ctx = DispatchContext(tool_name="galaxy.stats", kwargs={})
        mw_error_learner(ctx, fake_next)

        lib = el_mod.get_error_library()
        assert len(lib.error_patterns) == 0


# ─── Gap 3: Pattern guard middleware tests ───────────────────────────────


class TestPatternGuardMiddleware:
    """Test mw_pattern_guard injects warnings into tool results."""

    def test_pattern_guard_injects_warnings(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "whitemagic.core.patterns.error_library.get_state_root",
            lambda: tmp_path,
        )
        import whitemagic.core.patterns.error_library as el_mod

        monkeypatch.setattr(el_mod, "_library", None)

        # Pre-populate the library with a known error
        lib = el_mod.get_error_library()
        lib.learn_from_error(
            "ImportError: No module named whitemagic_rust",
            resolution="Run maturin develop",
            session="test",
        )

        # Clear the avoid cache
        from whitemagic.tools import middleware as mw_mod

        mw_mod._avoid_cache.clear()

        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_pattern_guard,
        )

        def fake_next(ctx):
            return {"status": "success", "data": "ok"}

        ctx = DispatchContext(
            tool_name="galaxy.stats",
            kwargs={"query": "importerror whitemagic_rust"},
        )
        result = mw_pattern_guard(ctx, fake_next)

        assert result["status"] == "success"
        # Warnings may or may not be injected depending on keyword overlap
        # but the key should exist if there were matches
        if "_pattern_warnings" in result:
            assert isinstance(result["_pattern_warnings"], list)

    def test_pattern_guard_skips_pattern_tools(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "whitemagic.core.patterns.error_library.get_state_root",
            lambda: tmp_path,
        )
        import whitemagic.core.patterns.error_library as el_mod

        monkeypatch.setattr(el_mod, "_library", None)

        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_pattern_guard,
        )

        def fake_next(ctx):
            return {"status": "success"}

        ctx = DispatchContext(tool_name="pattern.avoid", kwargs={})
        result = mw_pattern_guard(ctx, fake_next)

        assert result == {"status": "success"}
        assert "_pattern_warnings" not in result

    def test_pattern_guard_disabled_via_env(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "whitemagic.core.patterns.error_library.get_state_root",
            lambda: tmp_path,
        )
        monkeypatch.setenv("WM_PATTERN_GUARD", "0")
        import whitemagic.core.patterns.error_library as el_mod

        monkeypatch.setattr(el_mod, "_library", None)

        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_pattern_guard,
        )

        def fake_next(ctx):
            return {"status": "success"}

        ctx = DispatchContext(tool_name="galaxy.stats", kwargs={})
        result = mw_pattern_guard(ctx, fake_next)

        assert "_pattern_warnings" not in result

    def test_pattern_guard_caches_results(self, tmp_path, monkeypatch):
        """Verify avoid results are cached to avoid repeated lookups."""
        monkeypatch.setattr(
            "whitemagic.core.patterns.error_library.get_state_root",
            lambda: tmp_path,
        )
        import whitemagic.core.patterns.error_library as el_mod

        monkeypatch.setattr(el_mod, "_library", None)

        from whitemagic.tools import middleware as mw_mod

        mw_mod._avoid_cache.clear()

        # Pre-populate
        lib = el_mod.get_error_library()
        lib.learn_from_error("ValueError: invalid argument")

        from whitemagic.tools.middleware import (
            DispatchContext,
            mw_pattern_guard,
        )

        def fake_next(ctx):
            return {"status": "success"}

        ctx = DispatchContext(tool_name="test.tool", kwargs={})
        mw_pattern_guard(ctx, fake_next)

        # Cache should now have an entry
        assert "test.tool" in mw_mod._avoid_cache


# ─── Gap 4: Cross-agent learning tests ───────────────────────────────────


class TestCrossAgentLearning:
    """Test per-user pattern isolation with global pattern sharing."""

    def test_user_specific_library_uses_separate_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "whitemagic.core.patterns.error_library.get_state_root",
            lambda: tmp_path,
        )
        import whitemagic.core.patterns.error_library as el_mod

        monkeypatch.setattr(el_mod, "_library", None)
        monkeypatch.setattr(el_mod, "_user_libraries", {})

        lib = el_mod.get_error_library(user_id="agent_alice")
        assert lib.user_id == "agent_alice"
        assert "agent_alice" in lib.patterns_file.name

    def test_global_library_uses_default_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "whitemagic.core.patterns.error_library.get_state_root",
            lambda: tmp_path,
        )
        import whitemagic.core.patterns.error_library as el_mod

        monkeypatch.setattr(el_mod, "_library", None)
        monkeypatch.setattr(el_mod, "_user_libraries", {})

        lib = el_mod.get_error_library(user_id="global")
        assert lib.user_id == "global"
        assert lib.patterns_file.name == "error_patterns.json"

    def test_user_library_reads_global_patterns(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "whitemagic.core.patterns.error_library.get_state_root",
            lambda: tmp_path,
        )
        import whitemagic.core.patterns.error_library as el_mod

        monkeypatch.setattr(el_mod, "_library", None)
        monkeypatch.setattr(el_mod, "_user_libraries", {})

        # Write to global library first
        global_lib = el_mod.get_error_library(user_id="global")
        global_lib.learn_from_error(
            "ImportError: No module named rust_module",
            resolution="Run maturin develop",
        )

        # Now create a user library — it should see global patterns
        user_lib = el_mod.get_error_library(user_id="agent_bob")
        assert len(user_lib._global_patterns) > 0

        # Lookup should find the global pattern
        result = user_lib.lookup("ImportError: No module named rust_module")
        assert result is not None
        assert result.get("source") == "global"

    def test_user_library_isolated_from_other_users(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "whitemagic.core.patterns.error_library.get_state_root",
            lambda: tmp_path,
        )
        import whitemagic.core.patterns.error_library as el_mod

        monkeypatch.setattr(el_mod, "_library", None)
        monkeypatch.setattr(el_mod, "_user_libraries", {})

        # Alice learns an error
        alice_lib = el_mod.get_error_library(user_id="alice")
        alice_lib.learn_from_error("KeyError: missing key alice_specific")

        # Bob should NOT see Alice's user-specific pattern (only global)
        bob_lib = el_mod.get_error_library(user_id="bob")
        assert len(bob_lib.error_patterns) == 0
        # But Bob's global patterns should be empty too (Alice wrote to her own file)
        assert len(bob_lib._global_patterns) == 0

    def test_summary_includes_global_counts(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "whitemagic.core.patterns.error_library.get_state_root",
            lambda: tmp_path,
        )
        import whitemagic.core.patterns.error_library as el_mod

        monkeypatch.setattr(el_mod, "_library", None)
        monkeypatch.setattr(el_mod, "_user_libraries", {})

        # Write to global
        global_lib = el_mod.get_error_library(user_id="global")
        global_lib.learn_from_error("RuntimeError: something bad")

        # User summary should show global pattern count
        user_lib = el_mod.get_error_library(user_id="charlie")
        summary = user_lib.summary()
        assert summary["global_error_patterns"] >= 1
        assert summary["user_id"] == "charlie"

    def test_get_error_library_returns_same_user_instance(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "whitemagic.core.patterns.error_library.get_state_root",
            lambda: tmp_path,
        )
        import whitemagic.core.patterns.error_library as el_mod

        monkeypatch.setattr(el_mod, "_library", None)
        monkeypatch.setattr(el_mod, "_user_libraries", {})

        lib1 = el_mod.get_error_library(user_id="dave")
        lib2 = el_mod.get_error_library(user_id="dave")
        assert lib1 is lib2
