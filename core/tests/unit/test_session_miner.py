# ruff: noqa: BLE001,SLF001
"""Unit tests for the SessionMiner WindsurfRips integration module."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from whitemagic.archaeology.session_miner import (
    CATEGORY_KEYWORDS,
    ExportComparator,
    LanguageServerClient,
    PatternMiner,
    ProtobufFallback,
    SessionIngestor,
    SessionInfo,
    SessionMiner,
    TranscriptParser,
    Turn,
)


# ── TranscriptParser tests ──────────────────────────────────────────────────


class TestTranscriptParser:
    """Tests for TranscriptParser."""

    SAMPLE_TRANSCRIPT = """=== MESSAGE 0 - User ===
Let's implement the new feature.

=== MESSAGE 1 - Assistant ===
I'll help you implement that. Here's the plan:

```python
def new_feature():
    pass
```

=== MESSAGE 2 - Tool ===
File written successfully.

=== MESSAGE 3 - User ===
Great, that works! Breakthrough - we solved the issue.
"""

    def test_parse_transcript_basic(self):
        turns = TranscriptParser.parse_transcript(self.SAMPLE_TRANSCRIPT)
        assert len(turns) == 4
        assert turns[0].role == "user"
        assert turns[0].message_num == 0
        assert "implement" in turns[0].content
        assert turns[1].role == "assistant"
        assert turns[2].role == "tool"
        assert turns[3].role == "user"

    def test_parse_transcript_empty(self):
        turns = TranscriptParser.parse_transcript("")
        assert len(turns) == 0

    def test_parse_transcript_char_counts(self):
        turns = TranscriptParser.parse_transcript(self.SAMPLE_TRANSCRIPT)
        for turn in turns:
            assert turn.char_count == len(turn.content)

    def test_classify_turn_type_question(self):
        assert TranscriptParser.classify_turn_type("What is this?", "user") == "question"

    def test_classify_turn_type_error(self):
        assert TranscriptParser.classify_turn_type("Traceback: ValueError occurred", "assistant") == "error"

    def test_classify_turn_type_error_strict(self):
        """Field names containing 'error' should NOT be classified as errors."""
        assert TranscriptParser.classify_turn_type("cortex_step_type_error_message", "tool") != "error"

    def test_classify_turn_type_error_summary_excluded(self):
        """Summary/progress messages should not be classified as errors even with error-adjacent words."""
        assert TranscriptParser.classify_turn_type("## summary of error handling", "assistant") != "error"
        assert TranscriptParser.classify_turn_type("all tasks complete. here's the summary:", "assistant") != "error"

    def test_classify_turn_type_code_change(self):
        assert TranscriptParser.classify_turn_type("```python\ndef foo(): pass\n```", "assistant") == "code_change"

    def test_classify_turn_type_breakthrough(self):
        assert TranscriptParser.classify_turn_type("That's it! Now it works!", "user") == "breakthrough"

    def test_classify_turn_type_decision(self):
        assert TranscriptParser.classify_turn_type("Let's go with option A", "user") == "decision"

    def test_classify_turn_type_summary(self):
        assert TranscriptParser.classify_turn_type("Summary: we implemented X and Y", "assistant") == "summary"

    def test_classify_turn_type_context(self):
        long_content = "x" * 1500
        assert TranscriptParser.classify_turn_type(long_content, "tool") == "context"

    def test_classify_turn_type_message(self):
        assert TranscriptParser.classify_turn_type("hello world", "user") == "message"

    def test_score_importance_user(self):
        score = TranscriptParser.score_importance("Hello there", "user", "message")
        assert 0.5 < score <= 1.0

    def test_score_importance_tool(self):
        score = TranscriptParser.score_importance("x" * 2000, "tool", "context")
        assert score < 0.5

    def test_score_importance_decision(self):
        score = TranscriptParser.score_importance("We should use approach X", "user", "decision")
        assert score >= 0.9

    def test_score_importance_breakthrough(self):
        score = TranscriptParser.score_importance("Solved it!", "user", "breakthrough")
        assert score >= 0.9

    def test_classify_and_score(self):
        turns = TranscriptParser.parse_transcript(self.SAMPLE_TRANSCRIPT)
        TranscriptParser.classify_and_score(turns)
        assert all(t.turn_type != "message" or t.importance > 0 for t in turns)
        # The last user turn should be classified as breakthrough
        assert turns[3].turn_type == "breakthrough"

    def test_extract_decisions(self):
        turns = [
            Turn(0, "user", "Let's go with A", 15, "decision", 0.9),
            Turn(1, "user", "Hello", 5, "message", 0.6),
            Turn(2, "user", "We should use B", 15, "decision", 0.9),
        ]
        decisions = TranscriptParser.extract_decisions(turns)
        assert len(decisions) == 2

    def test_extract_breakthroughs(self):
        turns = [
            Turn(0, "user", "Eureka!", 7, "breakthrough", 0.95),
            Turn(1, "user", "Hello", 5, "message", 0.6),
        ]
        breakthroughs = TranscriptParser.extract_breakthroughs(turns)
        assert len(breakthroughs) == 1

    def test_categorize_whitemagic(self):
        assert TranscriptParser.categorize("WhiteMagic Galaxy Implementation", "holographic memory dharma") == "whitemagic"

    def test_categorize_ai_research(self):
        assert TranscriptParser.categorize("Ollama Model Benchmark", "open source model llama") == "ai_research"

    def test_categorize_other(self):
        assert TranscriptParser.categorize("Random Topic", "nothing relevant here") == "other"


# ── PatternMiner tests ──────────────────────────────────────────────────────


class TestPatternMiner:
    """Tests for PatternMiner."""

    @pytest.fixture
    def sample_sessions(self):
        return [
            {
                "session_id": "sess-1",
                "title": "Feature Implementation",
                "turns": [
                    {"role": "user", "content": "Let's go with approach A", "turn_type": "decision", "importance": 0.9},
                    {"role": "assistant", "content": "Traceback: ValueError", "turn_type": "error", "importance": 0.5},
                    {"role": "user", "content": "That's it! Solved!", "turn_type": "breakthrough", "importance": 0.95},
                    {"role": "user", "content": "Let's implement the feature", "turn_type": "message", "importance": 0.7},
                ],
            },
            {
                "session_id": "sess-2",
                "title": "Bug Fixing",
                "turns": [
                    {"role": "user", "content": "We should fix the import error", "turn_type": "decision", "importance": 0.85},
                    {"role": "assistant", "content": "ImportError: No module named foo", "turn_type": "error", "importance": 0.4},
                ],
            },
        ]

    def test_mine_decisions(self, sample_sessions):
        decisions = PatternMiner.mine_decisions(sample_sessions)
        assert len(decisions) == 2
        assert decisions[0]["session_id"] == "sess-1"

    def test_mine_breakthroughs(self, sample_sessions):
        breakthroughs = PatternMiner.mine_breakthroughs(sample_sessions)
        assert len(breakthroughs) == 1
        assert breakthroughs[0]["session_id"] == "sess-1"

    def test_mine_errors(self, sample_sessions):
        errors = PatternMiner.mine_errors(sample_sessions)
        assert "other" in errors or "traceback" in errors or "import_error" in errors
        total = sum(len(v) for v in errors.values())
        assert total == 2
        # Check specific error types are detected
        assert "traceback" in errors  # "Traceback: ValueError" -> traceback
        assert "import_error" in errors  # "ImportError: No module named foo" -> import_error

    def test_mine_topics(self, sample_sessions):
        topics = PatternMiner.mine_topics(sample_sessions)
        assert len(topics) >= 1
        # Both sessions should be categorized
        total_sessions = sum(len(ids) for ids in topics.values())
        assert total_sessions == 2

    def test_mine_directives(self, sample_sessions):
        directives = PatternMiner.mine_directives(sample_sessions)
        # "Let's go with approach A" and "Let's implement the feature" and "We should fix..."
        assert len(directives) >= 2

    def test_mine_combined(self, sample_sessions):
        result = PatternMiner.mine(sample_sessions)
        assert result["total_sessions"] == 2
        assert result["decisions"]["count"] == 2
        assert result["breakthroughs"]["count"] == 1
        assert result["errors"]["total_count"] == 2
        assert "directives" in result

    def test_create_codex_memories(self, sample_sessions):
        patterns = PatternMiner.mine(sample_sessions)
        memories = PatternMiner.create_codex_memories(patterns)
        # 2 decisions + 1 breakthrough + any associations/outcomes/recurring
        assert len(memories) >= 3
        assert all(m["galaxy"] == "codex" for m in memories)
        assert memories[0]["importance"] >= 0.8


# ── ExportComparator tests ──────────────────────────────────────────────────


class TestExportComparator:
    """Tests for ExportComparator."""

    @pytest.fixture
    def export_dirs(self, tmp_path):
        old_dir = tmp_path / "api_export_2026-07-01"
        new_dir = tmp_path / "api_export_2026-07-10"
        old_dir.mkdir()
        new_dir.mkdir()

        # Old export index
        old_index = {
            "sessions": [
                {"cascadeId": "sess-old-1", "title": "Old Session 1", "transcriptLength": 5000, "stepCount": 100},
                {"cascadeId": "sess-shared-1", "title": "Shared Session", "transcriptLength": 3000, "stepCount": 50},
            ]
        }
        (old_dir / "INDEX.json").write_text(json.dumps(old_index))

        # New export index
        new_index = {
            "sessions": [
                {"cascadeId": "sess-shared-1", "title": "Shared Session", "transcriptLength": 5000, "stepCount": 80},
                {"cascadeId": "sess-new-1", "title": "New Session", "transcriptLength": 2000, "stepCount": 30},
            ]
        }
        (new_dir / "INDEX.json").write_text(json.dumps(new_index))

        # Create dummy .md files for hash comparison
        (old_dir / "sess-shared-1__sess-sha.md").write_text("old content")
        (new_dir / "sess-shared-1__sess-sha.md").write_text("new content that is different")

        return new_dir, old_dir

    def test_load_export_index(self, export_dirs):
        new_dir, _ = export_dirs
        index = ExportComparator.load_export_index(new_dir)
        assert len(index) == 2
        assert "sess-new-1" in index

    def test_load_export_index_missing(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        index = ExportComparator.load_export_index(empty_dir)
        assert index == {}

    def test_compare_basic(self, export_dirs):
        new_dir, old_dir = export_dirs
        result = ExportComparator.compare(new_dir, [old_dir])

        summary = result["summary"]
        assert summary["total_new_export"] == 2
        assert summary["brand_new"] == 1
        assert summary["changed"] == 1
        assert summary["unchanged"] == 0

    def test_compare_brand_new(self, export_dirs):
        new_dir, old_dir = export_dirs
        result = ExportComparator.compare(new_dir, [old_dir])
        brand_new_ids = [s["cascadeId"] for s in result["brand_new"]]
        assert "sess-new-1" in brand_new_ids

    def test_compare_changed(self, export_dirs):
        new_dir, old_dir = export_dirs
        result = ExportComparator.compare(new_dir, [old_dir])
        changed_ids = [s["cascadeId"] for s in result["changed"]]
        assert "sess-shared-1" in changed_ids


# ── SessionIngestor tests ───────────────────────────────────────────────────


class TestSessionIngestor:
    """Tests for SessionIngestor."""

    def test_ingest_dry_run(self):
        ingestor = SessionIngestor()
        turns = [
            Turn(0, "user", "Hello world", 11, "message", 0.7),
            Turn(1, "ai", "Hi there", 8, "answer", 0.6),
        ]
        result = ingestor.ingest_session("test-sess-1", "Test Session", turns, dry_run=True)
        assert result["dry_run"] is True
        assert result["turns"] == 2
        assert result["title"] == "Test Session"
        assert "user" in result["roles"]
        assert "ai" in result["roles"]

    def test_ingest_dry_run_with_types(self):
        ingestor = SessionIngestor()
        turns = [
            Turn(0, "user", "What is this?", 14, "question", 0.8),
            Turn(1, "ai", "Let's go with A", 15, "decision", 0.9),
        ]
        result = ingestor.ingest_session("test-sess-2", "Test", turns, dry_run=True)
        assert result["turn_types"]["question"] == 1
        assert result["turn_types"]["decision"] == 1


# ── LanguageServerClient tests ──────────────────────────────────────────────


class TestLanguageServerClient:
    """Tests for LanguageServerClient (mocked — no real server needed)."""

    def test_init_defaults(self):
        client = LanguageServerClient()
        assert client._pid is None
        assert client._csrf is None
        assert client._port is None

    def test_is_available_no_server(self):
        client = LanguageServerClient()
        with patch.object(client, "find_server", return_value=None):
            assert client.is_available() is False

    def test_connect_no_pid(self):
        client = LanguageServerClient()
        with patch.object(client, "find_server", return_value=None):
            assert client.connect() is False


# ── ProtobufFallback tests ──────────────────────────────────────────────────


class TestProtobufFallback:
    """Tests for ProtobufFallback."""

    def test_init(self):
        pb = ProtobufFallback()
        assert pb._reader is not None


# ── SessionMiner facade tests ───────────────────────────────────────────────


class TestSessionMiner:
    """Tests for the SessionMiner facade."""

    def test_init(self):
        miner = SessionMiner()
        assert miner._api is not None
        assert miner._pb is not None
        assert miner._parser is not None
        assert miner._ingestor is not None
        assert miner._comparator is not None
        assert miner._miner is not None

    def test_api_available_cached(self):
        miner = SessionMiner()
        miner._api_available = False  # Pre-set to avoid scanning /proc
        assert miner.api_available is False

    def test_safe_filename(self):
        name = SessionMiner._safe_filename("Test/Title: With & Stuff", "abc123def456")
        assert "/" not in name
        assert ":" not in name
        assert "&" not in name
        assert "abc123de" in name

    def test_safe_filename_empty(self):
        name = SessionMiner._safe_filename("", "abc123def456")
        assert "Untitled" in name

    def test_categorize_no_dir(self):
        miner = SessionMiner()
        result = miner.categorize(export_dir=None)
        assert result["status"] == "error"

    def test_categorize_with_files(self, tmp_path):
        export_dir = tmp_path / "export"
        export_dir.mkdir()

        meta = {
            "cascadeId": "test-123",
            "title": "WhiteMagic Galaxy Implementation",
        }
        (export_dir / "test__test-123.json").write_text(json.dumps(meta))
        (export_dir / "test__test-123.md").write_text(
            "=== MESSAGE 0 - User ===\nLet's implement holographic memory with dharma governance.\n"
        )

        miner = SessionMiner()
        result = miner.categorize(export_dir=export_dir)
        assert result["status"] == "success"
        assert result["total"] == 1
        assert result["categorized"][0]["category"] == "whitemagic"
        assert result["categorized"][0]["galaxy"] == "codex"


# ── Turn dataclass tests ────────────────────────────────────────────────────


class TestTurnDataclass:
    """Tests for the Turn dataclass."""

    def test_turn_creation(self):
        turn = Turn(0, "user", "Hello", 5, "message", 0.7)
        assert turn.message_num == 0
        assert turn.role == "user"
        assert turn.content == "Hello"
        assert turn.char_count == 5
        assert turn.turn_type == "message"
        assert turn.importance == 0.7

    def test_turn_to_dict(self):
        turn = Turn(1, "ai", "Response", 8, "answer", 0.6, "assistant")
        d = turn.to_dict()
        assert d["message_num"] == 1
        assert d["role"] == "ai"
        assert d["content"] == "Response"
        assert d["turn_type"] == "answer"
        assert d["step_type"] == "assistant"


# ── SessionInfo dataclass tests ─────────────────────────────────────────────


class TestSessionInfoDataclass:
    """Tests for the SessionInfo dataclass."""

    def test_session_info_creation(self):
        info = SessionInfo(
            cascade_id="test-123",
            title="Test Session",
            step_count=100,
            total_steps=105,
            transcript_length=5000,
        )
        assert info.cascade_id == "test-123"
        assert info.title == "Test Session"
        assert info.step_count == 100

    def test_session_info_to_dict(self):
        info = SessionInfo(cascade_id="test-456", title="Another Session")
        d = info.to_dict()
        assert d["cascadeId"] == "test-456"
        assert d["title"] == "Another Session"
        assert d["stepCount"] == 0


# ── Category keywords coverage test ─────────────────────────────────────────


class TestCategoryKeywords:
    """Ensure all categories have keywords and galaxy mappings exist."""

    def test_all_categories_have_keywords(self):
        for cat, keywords in CATEGORY_KEYWORDS.items():
            assert len(keywords) > 0, f"Category {cat} has no keywords"

    def test_galaxy_mapping_exists_for_main_categories(self):
        from whitemagic.archaeology.session_miner import CATEGORY_TO_GALAXY

        for cat in CATEGORY_KEYWORDS:
            if cat != "other":
                assert cat in CATEGORY_TO_GALAXY, f"Category {cat} missing galaxy mapping"


# ── PatternMiner Advanced tests (8 new methods) ─────────────────────────────


class TestPatternMinerAdvanced:
    """Tests for the 8 new advanced pattern mining methods."""

    @pytest.fixture
    def rich_sessions(self):
        """Sessions with decisions, breakthroughs, errors, and shared keywords."""
        return [
            {
                "session_id": "sess-rust-1",
                "title": "Rust SIMD Expansion for HNSW",
                "turns": [
                    {"role": "user", "content": "Let's go with rust for the SIMD implementation", "turn_type": "decision", "importance": 0.9},
                    {"role": "assistant", "content": "Traceback: ImportError: No module named whitemagic_rust", "turn_type": "error", "importance": 0.5},
                    {"role": "user", "content": "That's it! Rust SIMD acceleration works now!", "turn_type": "breakthrough", "importance": 0.95},
                    {"role": "user", "content": "Let's implement the rust batch euclidean distance", "turn_type": "message", "importance": 0.7},
                ],
            },
            {
                "session_id": "sess-rust-2",
                "title": "Rust PyO3 Bridge Optimization",
                "turns": [
                    {"role": "user", "content": "We should optimize the rust pyo3 bridge", "turn_type": "decision", "importance": 0.85},
                    {"role": "assistant", "content": "ImportError: No module named whitemagic_rust", "turn_type": "error", "importance": 0.4},
                    {"role": "user", "content": "Solved the rust bridge overhead problem", "turn_type": "breakthrough", "importance": 0.9},
                ],
            },
            {
                "session_id": "sess-dharma-1",
                "title": "Dharma Ethical Governance Implementation",
                "turns": [
                    {"role": "user", "content": "Let's implement the dharma governance system", "turn_type": "decision", "importance": 0.9},
                    {"role": "assistant", "content": "TypeError: 'NoneType' object is not callable", "turn_type": "error", "importance": 0.5},
                    {"role": "user", "content": "Eureka! Dharma engine now enforces boundaries", "turn_type": "breakthrough", "importance": 0.95},
                ],
            },
        ]

    # ── #1: Cross-Session Associations ──

    def test_mine_associations_finds_chains(self, rich_sessions):
        chains = PatternMiner.mine_associations(rich_sessions)
        # sess-rust-1 decision about "rust" should link to sess-rust-2 breakthrough about "rust"
        rust_chains = [c for c in chains if "rust" in c["shared_keywords"]]
        assert len(rust_chains) >= 1

    def test_mine_associations_shared_keywords(self, rich_sessions):
        chains = PatternMiner.mine_associations(rich_sessions)
        for chain in chains:
            assert len(chain["shared_keywords"]) >= 2
            assert chain["decision_content"]
            assert chain["breakthrough_content"]

    def test_mine_associations_sorted_by_overlap(self, rich_sessions):
        chains = PatternMiner.mine_associations(rich_sessions)
        for i in range(len(chains) - 1):
            assert len(chains[i]["shared_keywords"]) >= len(chains[i + 1]["shared_keywords"])

    def test_extract_keywords_filters_stopwords(self):
        kw = PatternMiner._extract_keywords("Let's go with the rust implementation for the system")
        assert "rust" in kw
        assert "the" not in kw
        assert "lets" not in kw

    # ── #2: Recurring Errors ──

    def test_mine_recurring_errors_detects_duplicates(self, rich_sessions):
        result = PatternMiner.mine_recurring_errors(rich_sessions)
        # "ImportError: No module named whitemagic_rust" appears in 2 sessions
        assert result["recurring_count"] >= 1
        recurring = result["recurring"]
        assert any(r["count"] >= 2 for r in recurring)

    def test_normalize_error_replaces_paths(self):
        norm = PatternMiner._normalize_error("Error at /home/lucas/file.py line 42")
        assert "/path" in norm or "path" in norm
        assert "42" not in norm

    def test_normalize_error_replaces_strings(self):
        norm = PatternMiner._normalize_error("KeyError: 'some_variable_name'")
        assert "some_variable_name" not in norm

    # ── #3: Topic Co-occurrence ──

    def test_mine_topic_cooccurrence_matrix(self, rich_sessions):
        result = PatternMiner.mine_topic_cooccurrence(rich_sessions)
        assert "topics" in result
        assert "matrix" in result
        assert "top_pairs" in result
        # Matrix should be symmetric
        for t1 in result["topics"]:
            for t2 in result["topics"]:
                assert result["matrix"][t1][t2] == result["matrix"][t2][t1]

    def test_mine_topic_cooccurrence_pairs_sorted(self, rich_sessions):
        result = PatternMiner.mine_topic_cooccurrence(rich_sessions)
        pairs = result["top_pairs"]
        for i in range(len(pairs) - 1):
            assert pairs[i]["count"] >= pairs[i + 1]["count"]

    # ── #4: Session Similarity ──

    def test_mine_session_similarity_finds_rust_pair(self, rich_sessions):
        result = PatternMiner.mine_session_similarity(rich_sessions)
        # sess-rust-1 and sess-rust-2 should be similar (both about rust)
        rust_pair = [
            p for p in result["similar_pairs"]
            if "rust" in p.get("shared_keywords", [])
        ]
        assert len(rust_pair) >= 1
        assert rust_pair[0]["similarity"] >= 0.2

    def test_mine_session_similarity_returns_method(self, rich_sessions):
        result = PatternMiner.mine_session_similarity(rich_sessions)
        assert result["method"] in ("hnsw", "jaccard")

    # ── #5: Tech Timeline ──

    def test_mine_tech_timeline_finds_rust(self, rich_sessions):
        result = PatternMiner.mine_tech_timeline(rich_sessions)
        techs = [t["technology"] for t in result["timeline"]]
        assert "rust" in techs

    def test_mine_tech_timeline_finds_dharma(self, rich_sessions):
        result = PatternMiner.mine_tech_timeline(rich_sessions)
        techs = [t["technology"] for t in result["timeline"]]
        assert "dharma" in techs

    def test_mine_tech_timeline_counts(self, rich_sessions):
        result = PatternMiner.mine_tech_timeline(rich_sessions)
        rust_entry = [t for t in result["timeline"] if t["technology"] == "rust"][0]
        assert rust_entry["mention_count"] >= 2  # appears in both rust sessions

    # ── #6: Emotional Arcs ──

    def test_mine_emotional_arcs_struggle_to_success(self, rich_sessions):
        result = PatternMiner.mine_emotional_arcs(rich_sessions)
        shapes = result["shape_distribution"]
        # At least one session should have struggle_to_success (error before breakthrough)
        assert "struggle_to_success" in shapes or "success_then_issues" in shapes

    def test_mine_emotional_arcs_arc_string(self, rich_sessions):
        result = PatternMiner.mine_emotional_arcs(rich_sessions)
        for arc in result["session_arcs"]:
            assert len(arc["arc"]) > 0
            assert all(c in "+-." for c in arc["arc"])

    def test_mine_emotional_arcs_counts(self, rich_sessions):
        result = PatternMiner.mine_emotional_arcs(rich_sessions)
        for arc in result["session_arcs"]:
            assert arc["positive_turns"] + arc["negative_turns"] + arc["neutral_turns"] == arc["total_turns"]

    # ── #7: Decision Outcomes ──

    def test_mine_decision_outcomes_finds_breakthrough(self, rich_sessions):
        result = PatternMiner.mine_decision_outcomes(rich_sessions)
        outcomes = result["decisions"]
        # At least one decision should be linked to a breakthrough
        bt_outcomes = [o for o in outcomes if o["outcome"] == "led_to_breakthrough"]
        assert len(bt_outcomes) >= 1

    def test_mine_decision_outcomes_distribution(self, rich_sessions):
        result = PatternMiner.mine_decision_outcomes(rich_sessions)
        dist = result["outcome_distribution"]
        assert result["total_decisions"] == sum(dist.values())

    def test_mine_decision_outcomes_has_similarity_scores(self, rich_sessions):
        result = PatternMiner.mine_decision_outcomes(rich_sessions)
        for dec in result["decisions"]:
            assert "breakthrough_similarity" in dec
            assert "error_similarity" in dec
            assert 0.0 <= dec["breakthrough_similarity"] <= 1.0

    # ── #8: Directive Taxonomy ──

    def test_mine_directive_taxonomy_classifies_build(self, rich_sessions):
        result = PatternMiner.mine_directive_taxonomy(rich_sessions)
        # "Let's implement..." should be classified as "build"
        assert "build" in result["distribution"]
        assert result["distribution"]["build"] >= 1

    def test_mine_directive_taxonomy_total(self, rich_sessions):
        result = PatternMiner.mine_directive_taxonomy(rich_sessions)
        dist_sum = sum(result["distribution"].values())
        assert result["total_directives"] == dist_sum

    def test_mine_directive_taxonomy_has_categories(self, rich_sessions):
        result = PatternMiner.mine_directive_taxonomy(rich_sessions)
        for cat in ["build", "fix", "explore", "decide", "verify", "refactor", "other"]:
            assert cat in result["distribution"]

    # ── Combined mine() facade ──

    def test_mine_includes_all_new_sections(self, rich_sessions):
        result = PatternMiner.mine(rich_sessions)
        assert "associations" in result
        assert "recurring_errors" in result
        assert "topic_cooccurrence" in result
        assert "session_similarity" in result
        assert "tech_timeline" in result
        assert "emotional_arcs" in result
        assert "decision_outcomes" in result
        assert "directive_taxonomy" in result

    def test_mine_associations_count(self, rich_sessions):
        result = PatternMiner.mine(rich_sessions)
        assert result["associations"]["count"] >= 1

    def test_mine_create_codex_memories_includes_new_types(self, rich_sessions):
        patterns = PatternMiner.mine(rich_sessions)
        memories = PatternMiner.create_codex_memories(patterns)
        # Should have decision, breakthrough, association, outcome, and recurring error memories
        tags = set()
        for m in memories:
            for tag in m["tags"]:
                tags.add(tag)
        assert "type:association" in tags or "type:decision_outcome" in tags or "type:recurring_error" in tags
