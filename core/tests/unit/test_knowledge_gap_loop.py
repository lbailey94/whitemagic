"""Tests for Knowledge Gap Action Loop — self-directed gap filling."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp())
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")
os.environ.setdefault("WM_SILENT_INIT", "1")


from whitemagic.core.consciousness.knowledge_gap_loop import (
    KnowledgeGap,
    KnowledgeGapActionLoop,
)


class TestKnowledgeGapActionLoop:
    def test_classify_gap(self):
        loop = KnowledgeGapActionLoop()
        assert loop._classify_gap("Galaxy 'citta' is empty") == "missing_memory"
        assert loop._classify_gap("Galaxy 'codex' is stale") == "missing_memory"
        assert loop._classify_gap("Need code implementation for X") == "missing_code"
        assert loop._classify_gap("Strategic vision needed") == "missing_strategy"
        assert loop._classify_gap("Unknown topic Y") == "missing_knowledge"

    def test_extract_galaxy(self):
        loop = KnowledgeGapActionLoop()
        assert loop._extract_galaxy("Galaxy 'citta' is empty") == "citta"
        assert loop._extract_galaxy("Galaxy 'self_learning' needs work") == "self_learning"
        assert loop._extract_galaxy("Something about unknown stuff") == "universal"

    def test_propose_action(self):
        loop = KnowledgeGapActionLoop()
        gap = KnowledgeGap(gap_id="test", description="test", gap_type="missing_memory")
        assert loop._propose_action(gap) == "seed_memory_from_template"

        gap.gap_type = "missing_code"
        assert loop._propose_action(gap) == "generate_code_from_vault"

        gap.gap_type = "missing_strategy"
        assert loop._propose_action(gap) == "synthesize_strategy_from_meta_galaxy"

        gap.gap_type = "missing_knowledge"
        assert loop._propose_action(gap) == "search_and_ingest"

    def test_get_status(self):
        loop = KnowledgeGapActionLoop()
        status = loop.get_status()
        assert "total_gaps" in status
        assert "open" in status
        assert "filled" in status
        assert "failed" in status
        assert "success_rate" in status

    def test_detect_gaps_returns_list(self):
        loop = KnowledgeGapActionLoop()
        gaps = loop.detect_gaps()
        assert isinstance(gaps, list)

    def test_run_returns_results(self):
        loop = KnowledgeGapActionLoop()
        results = loop.run(max_gaps=1)
        assert isinstance(results, list)
        assert len(results) <= 1

    def test_knowledge_gap_dataclass(self):
        gap = KnowledgeGap(gap_id="test_1", description="Test gap", gap_type="missing_memory")
        assert gap.status == "open"
        assert gap.priority == 0.5
        assert gap.created_at > 0
