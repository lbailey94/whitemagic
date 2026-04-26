"""Tests for Dream Artifacts and Consolidator."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from whitemagic.core.dreaming.dream_artifacts import (
    DreamArtifact,
    DreamArtifactWriter,
    _extract_keywords,
    archive_dream,
    expire_dream,
    list_dreams,
    promote_dream,
    read_dream,
    revisit_dream,
)
from whitemagic.core.dreaming.dream_consolidator import DreamConsolidator


@pytest.fixture
def tmp_dreams_dir(tmp_path: Path):
    """Provide a temporary dreams directory."""
    d = tmp_path / "dreams"
    d.mkdir()
    with patch("whitemagic.config.paths.DREAMS_DIR", d):
        yield d


class TestDreamArtifactDataclass:
    def test_roundtrip_dict(self):
        a = DreamArtifact(
            dream_id="d1",
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            source="test",
            confidence=0.42,
            tension_score=0.78,
            left_hemisphere="left",
            right_hemisphere="right",
            creative_bridge="bridge",
            keywords=["k1", "k2"],
        )
        d = a.to_dict()
        b = DreamArtifact.from_dict(d)
        assert b.dream_id == "d1"
        assert b.confidence == pytest.approx(0.42)
        assert b.keywords == ["k1", "k2"]


class TestDreamArtifactWriter:
    def test_write_artifact_creates_file(self, tmp_dreams_dir: Path):
        writer = DreamArtifactWriter()
        art = writer.write_artifact(
            query="How to cache memories",
            left="Use LRU",
            right="Use emotion tags",
            synthesis="Emotional LRU cache",
            confidence=0.3,
            tension=0.6,
            dominant="balanced",
        )
        assert art.dream_id.startswith("dream_")
        files = list(tmp_dreams_dir.glob("*.yaml"))
        assert len(files) == 1
        assert art.dream_id in files[0].name

    def test_extract_keywords(self):
        kw = _extract_keywords(
            "Module caching should be deterministic",
            "What if caching had emotional valence",
            "Cache warmth boosts recall priority",
        )
        assert "caching" in kw
        assert len(kw) <= 5

    def test_list_dreams(self, tmp_dreams_dir: Path):
        writer = DreamArtifactWriter()
        writer.write_artifact(query="q1", left="l", right="r", synthesis="s", confidence=0.3, tension=0.5, dominant="r")
        writer.write_artifact(query="q2", left="l", right="r", synthesis="s", confidence=0.3, tension=0.5, dominant="r")
        dreams = list_dreams()
        assert len(dreams) == 2

    def test_read_dream(self, tmp_dreams_dir: Path):
        writer = DreamArtifactWriter()
        art = writer.write_artifact(query="read_test", left="l", right="r", synthesis="s", confidence=0.3, tension=0.5, dominant="r")
        data = read_dream(art.dream_id)
        assert data is not None
        assert data["dream_id"] == art.dream_id

    def test_read_missing(self, tmp_dreams_dir: Path):
        assert read_dream("nonexistent") is None

    def test_promote_dream(self, tmp_dreams_dir: Path):
        writer = DreamArtifactWriter()
        art = writer.write_artifact(query="promote_test", left="l", right="r", synthesis="s", confidence=0.3, tension=0.5, dominant="r")
        result = promote_dream(art.dream_id, memory_id="mem_123")
        assert result is not None
        assert result["status"] == "promoted"
        assert result["promoted_to_memory_id"] == "mem_123"

    def test_expire_dream(self, tmp_dreams_dir: Path):
        writer = DreamArtifactWriter()
        art = writer.write_artifact(query="expire_test", left="l", right="r", synthesis="s", confidence=0.3, tension=0.5, dominant="r")
        result = expire_dream(art.dream_id)
        assert result is not None
        assert result["status"] == "expired"

    def test_archive_dream(self, tmp_dreams_dir: Path):
        writer = DreamArtifactWriter()
        art = writer.write_artifact(query="archive_test", left="l", right="r", synthesis="s", confidence=0.3, tension=0.5, dominant="r")
        result = archive_dream(art.dream_id)
        assert result is not None
        assert result["status"] == "archived"

    def test_revisit_dream(self, tmp_dreams_dir: Path):
        writer = DreamArtifactWriter()
        art = writer.write_artifact(query="revisit_test", left="l", right="r", synthesis="s", confidence=0.3, tension=0.5, dominant="r")
        result = revisit_dream(art.dream_id)
        assert result is not None
        assert result["revisit_count"] == 1
        result2 = revisit_dream(art.dream_id)
        assert result2["revisit_count"] == 2

    def test_list_filter_by_status(self, tmp_dreams_dir: Path):
        writer = DreamArtifactWriter()
        art = writer.write_artifact(query="filter_test", left="l", right="r", synthesis="s", confidence=0.3, tension=0.5, dominant="r")
        expire_dream(art.dream_id)
        all_dreams = list_dreams()
        assert len(all_dreams) == 1
        expired = list_dreams(status_filter="expired")
        assert len(expired) == 1
        incubating = list_dreams(status_filter="incubating")
        assert len(incubating) == 0

    def test_event_listener_writes(self, tmp_dreams_dir: Path):
        from whitemagic.core.resonance import EventType, ResonanceEvent, get_bus
        writer = DreamArtifactWriter()
        writer.start_listening()
        event = ResonanceEvent(
            source="bicameral_reasoner",
            event_type=EventType.CREATIVE_BRIDGE_LOW_CONFIDENCE,
            data={
                "query": "event test",
                "left": "left content",
                "right": "right content",
                "synthesis": "synthesis content",
                "confidence": 0.2,
                "tension": 0.7,
                "dominant": "right",
            },
        )
        get_bus().emit(event)
        dreams = list_dreams()
        assert len(dreams) == 1
        assert dreams[0]["creative_bridge"] == "synthesis content"

    def test_yaml_is_safe(self, tmp_dreams_dir: Path):
        writer = DreamArtifactWriter()
        art = writer.write_artifact(query="yaml_safe", left="l", right="r", synthesis="s", confidence=0.3, tension=0.5, dominant="r")
        path = tmp_dreams_dir / f"{art.dream_id}_yaml_safe.yaml"
        assert path.exists()
        text = path.read_text()
        assert "!!python" not in text  # no unsafe tags


class TestDreamConsolidator:
    def test_promote_high_revisit(self, tmp_dreams_dir: Path):
        writer = DreamArtifactWriter()
        art = writer.write_artifact(query="consolidate_promote", left="l", right="r", synthesis="s", confidence=0.3, tension=0.5, dominant="r")
        for _ in range(5):
            revisit_dream(art.dream_id)
        cons = DreamConsolidator()
        report = cons.consolidate()
        assert art.dream_id in report.promoted

    def test_expire_old_archived(self, tmp_dreams_dir: Path):
        import yaml
        writer = DreamArtifactWriter()
        art = writer.write_artifact(query="consolidate_expire", left="l", right="r", synthesis="s", confidence=0.3, tension=0.5, dominant="r")
        archive_dream(art.dream_id)
        # Patch created_at to be 60 days ago
        for path in tmp_dreams_dir.glob("*.yaml"):
            if art.dream_id in path.name:
                with open(path, "r", encoding="utf-8") as fp:
                    data = yaml.safe_load(fp)
                from datetime import datetime, timedelta, timezone
                data["created_at"] = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
                with open(path, "w", encoding="utf-8") as fp:
                    yaml.dump(data, fp, default_flow_style=False, sort_keys=False, allow_unicode=True)
        cons = DreamConsolidator()
        report = cons.consolidate()
        assert art.dream_id in report.expired

    def test_skip_recent_incubating(self, tmp_dreams_dir: Path):
        writer = DreamArtifactWriter()
        writer.write_artifact(query="skip", left="l", right="r", synthesis="s", confidence=0.3, tension=0.5, dominant="r")
        cons = DreamConsolidator()
        report = cons.consolidate()
        assert report.skipped == 1
        assert report.promoted == []
        assert report.expired == []
