"""Tests for Batch 9: Root-level modules."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("WM_STATE_ROOT", str(Path(tempfile.mkdtemp())))


class TestSessionTypes:
    def test_continuation(self):
        from whitemagic.root_modules.session_types import (
            SessionType,
            detect_session_type,
        )
        result = detect_session_type(has_previous_session=True, error_count=0, new_files_accessed=2)
        assert result == SessionType.CONTINUATION

    def test_debug(self):
        from whitemagic.root_modules.session_types import (
            SessionType,
            detect_session_type,
        )
        result = detect_session_type(error_count=5)
        assert result == SessionType.DEBUG

    def test_new_contributor(self):
        from whitemagic.root_modules.session_types import (
            SessionType,
            detect_session_type,
        )
        result = detect_session_type(has_previous_session=False)
        assert result == SessionType.NEW_CONTRIBUTOR


class TestDeltaTracker:
    def test_compare(self):
        from whitemagic.root_modules.delta_tracking import DeltaTracker
        tracker = DeltaTracker()
        tracker.set_baseline({"a": 1, "b": 2})
        deltas = tracker.compare({"a": 1, "b": 3, "c": 4})
        assert len(deltas) >= 1

    def test_summary(self):
        from whitemagic.root_modules.delta_tracking import DeltaTracker
        tracker = DeltaTracker()
        tracker.set_baseline({"x": 1})
        tracker.compare({"x": 2})
        summary = tracker.summary()
        assert summary["total_deltas"] >= 1


class TestSymbolicEngine:
    def test_encode(self):
        from whitemagic.root_modules.symbolic import SymbolicEngine
        engine = SymbolicEngine()
        encoded = engine.encode("memory and wisdom")
        assert "記" in encoded
        assert "智" in encoded

    def test_decode(self):
        from whitemagic.root_modules.symbolic import SymbolicEngine
        engine = SymbolicEngine()
        decoded = engine.decode("記 and 智")
        assert "memory" in decoded
        assert "wisdom" in decoded

    def test_relate(self):
        from whitemagic.root_modules.symbolic import SymbolicEngine
        engine = SymbolicEngine()
        assert engine.relate("memory", "wisdom", "feeds") is True
        assert engine.relate("nonexist", "memory") is False


class TestWorkflowPatterns:
    def test_get_pattern(self):
        from whitemagic.root_modules.workflow_patterns import WorkflowPatterns
        wp = WorkflowPatterns()
        pattern = wp.get_pattern("test_first")
        assert pattern is not None
        assert "steps" in pattern

    def test_execute(self):
        from whitemagic.root_modules.workflow_patterns import WorkflowPatterns
        wp = WorkflowPatterns()
        result = wp.execute_pattern("lint_before_commit")
        assert result["status"] == "success"


class TestConceptMap:
    def test_add_and_neighbors(self):
        from whitemagic.root_modules.concept_map import ConceptMap
        cm = ConceptMap()
        cm.add_node("a")
        cm.add_node("b")
        cm.add_edge("a", "b")
        neighbors = cm.get_neighbors("a")
        assert "b" in neighbors

    def test_find_path(self):
        from whitemagic.root_modules.concept_map import ConceptMap
        cm = ConceptMap()
        cm.add_node("a")
        cm.add_node("b")
        cm.add_node("c")
        cm.add_edge("a", "b")
        cm.add_edge("b", "c")
        path = cm.find_path("a", "c")
        assert path == ["a", "b", "c"]

    def test_no_path(self):
        from whitemagic.root_modules.concept_map import ConceptMap
        cm = ConceptMap()
        cm.add_node("a")
        cm.add_node("b")
        path = cm.find_path("a", "b")
        assert path is None


class TestSymbolicMemory:
    def test_tag_and_find(self):
        from whitemagic.root_modules.symbolic_memory import SymbolicMemory
        sm = SymbolicMemory()
        sm.tag_memory("mem1", ["memory", "wisdom"])
        results = sm.find_by_concept("memory")
        assert "mem1" in results


class TestLazyMemoryLoader:
    def test_register_and_get(self):
        from whitemagic.root_modules.lazy_memory_loader import LazyMemoryLoader
        loader = LazyMemoryLoader()
        loader.register("1", "full content here", "summary")
        assert loader.get_summary("1") == "summary"
        assert loader.is_loaded("1") is False
        assert loader.get_full("1") == "full content here"
        assert loader.is_loaded("1") is True

    def test_summaries(self):
        from whitemagic.root_modules.lazy_memory_loader import LazyMemoryLoader
        loader = LazyMemoryLoader()
        loader.register("1", "content1", "sum1")
        loader.register("2", "content2", "sum2")
        summaries = loader.get_summaries()
        assert len(summaries) == 2


class TestSessionTemplates:
    def test_render_fast(self):
        from whitemagic.root_modules.session_templates import SessionTemplates
        templates = SessionTemplates()
        result = templates.render(SessionTemplates.TIER_FAST, {
            "last_action": "wrote code",
            "next_action": "run tests",
        })
        assert "wrote code" in result
        assert "run tests" in result


class TestComprehensiveReview:
    def test_review(self):
        from whitemagic.root_modules.comprehensive_review import ComprehensiveReview
        review = ComprehensiveReview(fast=True)
        result = review.review_codebase()
        assert "stubs" in result
        assert "tests" in result


class TestWorkspaceLoader:
    def test_load_priority(self, tmp_path):
        from whitemagic.root_modules.workspace_loader import WorkspaceLoader
        (tmp_path / "core").mkdir()
        loader = WorkspaceLoader(root=tmp_path)
        loaded = loader.load_priority()
        assert "core" in loaded


class TestBackupSystem:
    def test_backup_and_list(self, tmp_path):
        from whitemagic.root_modules.backup_system import BackupSystem
        source = tmp_path / "source"
        source.mkdir()
        (source / "test.txt").write_text("test")
        backup = BackupSystem(backup_dir=tmp_path / "backups")
        result = backup.backup(source=source, label="test")
        assert result["files_copied"] >= 1
        backups = backup.list_backups()
        assert len(backups) == 1


class TestLifecycle:
    def test_importance_score(self):
        from whitemagic.root_modules.lifecycle import calculate_importance_score
        score = calculate_importance_score({"access_count": 5, "tags": ["a", "b"]})
        assert 50 < score < 100

    def test_should_retain(self):
        from whitemagic.root_modules.lifecycle import MemoryLifecycle
        ml = MemoryLifecycle()
        assert ml.should_retain({"access_count": 10}) is True

    def test_should_delete(self):
        from whitemagic.root_modules.lifecycle import MemoryLifecycle
        ml = MemoryLifecycle()
        # With score below 10 — since baseline is 50, should_delete is for extreme cases
        assert ml.should_delete({"access_count": 0, "tags": []}) is False  # score=50, not <= 10

    def test_should_archive(self):
        from datetime import datetime, timedelta

        from whitemagic.root_modules.lifecycle import MemoryLifecycle
        ml = MemoryLifecycle()
        old_date = datetime.now() - timedelta(days=200)
        assert ml.should_archive({"access_count": 0, "tags": [], "created": old_date}) is True


class TestThreadingTiers:
    def test_recommend(self):
        from whitemagic.root_modules.threading_tiers import (
            ThreadingTier,
            recommend_tier,
        )
        assert recommend_tier(1) == ThreadingTier.QIAN
        assert recommend_tier(8) == ThreadingTier.KAN

    def test_names(self):
        from whitemagic.root_modules.threading_tiers import TIER_NAMES, ThreadingTier
        assert ThreadingTier.QIAN in TIER_NAMES


class TestEnhancedPatternDiscovery:
    def test_discover(self, tmp_path):
        from whitemagic.root_modules.pattern_discovery_enhanced import (
            EnhancedPatternDiscovery,
        )
        (tmp_path / "test.py").write_text("def foo():\n  pass\nclass Bar:\n  pass\n")
        discovery = EnhancedPatternDiscovery()
        patterns = discovery.discover_patterns(root=tmp_path)
        assert len(patterns) == 1
        assert "foo" in patterns[0]["functions"]


class TestYinSynthesis:
    def test_observe_and_synthesize(self):
        from whitemagic.root_modules.yin_synthesis import YinSynthesis
        ys = YinSynthesis()
        for i in range(3):
            ys.observe("memory", f"observation {i}")
        result = ys.synthesize()
        assert result["total_observations"] == 3
        assert len(result["insights"]) >= 1
