"""Unit tests for ripple tagging system."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp(prefix="wm_test_ripple_"))
os.environ.setdefault("WM_SILENT_INIT", "1")

from whitemagic.core.memory.ripple_tagging import (  # noqa: E402
    batch_tag,
    decay_tags,
    get_tags,
    stats,
    tag_ripple,
)


class TestTagRipple:
    def test_basic_tag(self):
        result = tag_ripple(["mem-1", "mem-2", "mem-3"])
        assert result["tagged"] is True
        assert "ripple_id" in result
        assert result["tagged_count"] == 3
        assert result["strength"] > 0

    def test_insufficient_co_activation(self):
        result = tag_ripple(["mem-1"])
        assert result["tagged"] is False

    def test_emotional_weight_amplifies_strength(self):
        r1 = tag_ripple(["m-a", "m-b"], emotional_weight=1.0)
        r2 = tag_ripple(["m-c", "m-d"], emotional_weight=2.0)
        assert r2["strength"] > r1["strength"]

    def test_more_memories_stronger_ripple(self):
        r1 = tag_ripple(["m1", "m2"])
        r2 = tag_ripple(["m3", "m4", "m5", "m6", "m7"])
        assert r2["strength"] > r1["strength"]


class TestGetTags:
    def test_get_tags_for_tagged_memories(self):
        tag_ripple(["tagged-1", "tagged-2"])
        result = get_tags(["tagged-1", "tagged-2", "untagged-1"])
        assert len(result) == 3
        assert result[0]["ripple_count"] >= 1
        assert result[2]["ripple_count"] == 0

    def test_get_tags_empty_list(self):
        result = get_tags([])
        assert result == []


class TestBatchTag:
    def test_batch_processing(self):
        events = [
            {"memory_ids": ["b1", "b2"], "galaxy": "universal"},
            {"memory_ids": ["b3", "b4", "b5"], "galaxy": "codex"},
        ]
        result = batch_tag(events)
        assert result["total"] == 2
        assert all(r["tagged"] for r in result["results"])


class TestDecayTags:
    def test_decay_reduces_strength(self):
        tag_ripple(["d1", "d2"], emotional_weight=2.0)
        before = get_tags(["d1"])[0]["tags"][0]["strength"]
        decay_tags(hours=10.0)  # 50% decay
        after_tags = get_tags(["d1"])[0]["tags"]
        if after_tags:
            assert after_tags[0]["strength"] < before
        # Very weak tags should be pruned


class TestStats:
    def test_stats_returns_dict(self):
        s = stats()
        assert "total_tags" in s
        assert "total_events" in s
        assert "ripples_detected" in s
        assert "backend" in s
        assert s["backend"] in ("elixir", "python")
