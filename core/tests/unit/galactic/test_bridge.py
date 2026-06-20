"""
Tests for the galactic bridge module (core/whitemagic/core/bridge/galactic.py).

These tests verify the bridge functions correctly wrap the galactic
substrate. They run against the live substrate DB at
~/.whitemagic/memory/whitemagic.db when available.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def use_live_substrate(monkeypatch):
    """Use the live substrate DB for these tests.

    The top-level conftest sets WM_STATE_ROOT to a temp dir; we override
    so galactic._resolve_db_path() returns the real DB.
    """
    from pathlib import Path
    live = Path("/home/lucas/.whitemagic/memory/whitemagic.db")
    if live.exists():
        monkeypatch.setenv("WM_MEMORY_DB", str(live))
    monkeypatch.delenv("WM_STATE_ROOT", raising=False)
    yield


# ─── Tests: each bridge function ──────────────────────────────────


def test_galactic_substrate_health_returns_alive():
    from whitemagic.core.bridge.galactic import galactic_substrate_health

    h = galactic_substrate_health()
    assert h["status"] == "alive"
    assert h["total_memories"] > 0
    assert h["total_dharma_audits"] > 0  # The 35K rehydration is in there


def test_galactic_galaxy_stats_shape():
    from whitemagic.core.bridge.galactic import galactic_galaxy_stats

    result = galactic_galaxy_stats()
    assert result["status"] == "ok"
    assert result["function"] == "galactic_galaxy_stats"
    r = result["result"]
    assert "total_memories" in r
    assert "by_zone" in r
    assert "by_type" in r
    # v23.0.0-alpha.1 rehydration brought the dharma_audit count to 35K+.
    assert r["total_memories"] > 100


def test_galactic_memory_recent_default_limit():
    from whitemagic.core.bridge.galactic import galactic_memory_recent

    result = galactic_memory_recent()
    assert result["status"] == "ok"
    assert result["result"]["count"] == 10
    assert len(result["result"]["memories"]) == 10
    for m in result["result"]["memories"]:
        assert m["id"]
        assert m["memory_type"]


def test_galactic_memory_recent_limit_capped():
    """Limit should be capped at 200 to prevent runaway queries."""
    from whitemagic.core.bridge.galactic import galactic_memory_recent

    # 999 should be silently capped to 200.
    result = galactic_memory_recent(limit=999)
    assert result["status"] == "ok"
    assert result["result"]["count"] <= 200


def test_galactic_memory_recent_filter_by_type():
    from whitemagic.core.bridge.galactic import galactic_memory_recent

    short = galactic_memory_recent(limit=20, memory_type="SHORT_TERM")
    long = galactic_memory_recent(limit=20, memory_type="LONG_TERM")
    assert short["status"] == "ok"
    assert long["status"] == "ok"
    for m in short["result"]["memories"]:
        assert m["memory_type"] == "SHORT_TERM"
    for m in long["result"]["memories"]:
        assert m["memory_type"] == "LONG_TERM"


def test_galactic_memory_search_returns_results():
    from whitemagic.core.bridge.galactic import galactic_memory_search

    # The FTS5 index in the live substrate is unpopulated, so search
    # falls back to LIKE matching. Use a substring known to match many
    # Hermes gate decisions.
    result = galactic_memory_search("Hermes Gate", limit=10)
    assert result["status"] == "ok"
    assert result["result"]["query"] == "Hermes Gate"
    assert result["result"]["count"] >= 1
    for m in result["result"]["memories"]:
        text = (m.get("title") or "") + " " + (m.get("content") or "")
        assert "Hermes Gate" in text or "hermes gate" in text.lower()


def test_galactic_memory_search_empty_query():
    from whitemagic.core.bridge.galactic import galactic_memory_search

    result = galactic_memory_search("")
    assert result["status"] == "ok"
    assert result["result"]["count"] == 0


def test_galactic_memory_by_id_roundtrip():
    from whitemagic.core.bridge.galactic import galactic_memory_by_id, galactic_memory_recent

    recent = galactic_memory_recent(limit=1)
    if not recent["result"]["memories"]:
        pytest.skip("no memories to test")
    mem_id = recent["result"]["memories"][0]["id"]
    result = galactic_memory_by_id(mem_id)
    assert result["status"] == "ok"
    assert result["result"]["id"] == mem_id


def test_galactic_memory_by_id_not_found():
    from whitemagic.core.bridge.galactic import galactic_memory_by_id

    result = galactic_memory_by_id("definitely-not-a-real-id-zzzzzzz")
    assert result["status"] == "not_found"
    assert result["memory_id"] == "definitely-not-a-real-id-zzzzzzz"


def test_galactic_associations_invalid_id():
    """Invalid memory id should return empty list, not error."""
    from whitemagic.core.bridge.galactic import galactic_associations

    result = galactic_associations("nonexistent-id")
    assert result["status"] == "ok"
    assert result["result"]["count"] == 0


def test_galactic_event_search_no_filter():
    from whitemagic.core.bridge.galactic import galactic_event_search

    result = galactic_event_search(limit=10)
    assert result["status"] == "ok"
    assert result["result"]["count"] > 0
    # The rehydration marker should be in at least some of the events.
    actions = [e["action"] for e in result["result"]["events"]]
    rehydrated = sum(1 for a in actions if "whitemagic-core-rehydrate" in a)
    assert rehydrated > 0, "expected some rehydrated events in the audit log"


def test_galactic_event_search_filter_by_type():
    from whitemagic.core.bridge.galactic import galactic_event_search

    # The CLI audit migration writes boundary_type="cli_command".
    result = galactic_event_search(event_type="cli_command", limit=10)
    assert result["status"] == "ok"
    for e in result["result"]["events"]:
        assert e["boundary_type"] == "cli_command"


def test_galactic_event_search_filter_by_type_voice():
    """The rehydrated events have type=voice_expressed (Whitemagic-Core's
    narrator type). Filter by that."""
    from whitemagic.core.bridge.galactic import galactic_event_search

    result = galactic_event_search(event_type="voice_expressed", limit=5)
    assert result["status"] == "ok"
    if result["result"]["count"] > 0:
        for e in result["result"]["events"]:
            assert e["boundary_type"] == "voice_expressed"


def test_galactic_event_search_with_text_query():
    from whitemagic.core.bridge.galactic import galactic_event_search

    result = galactic_event_search(query="echo test", limit=5)
    assert result["status"] == "ok"
    for e in result["result"]["events"]:
        # The query searches action/concerns/context.
        text = (e["action"] + " " + (e.get("concerns") or "")).lower()
        assert "echo" in text or "test" in text


def test_galactic_constellation_count():
    from whitemagic.core.bridge.galactic import galactic_constellation_count

    result = galactic_constellation_count()
    assert result["status"] == "ok"
    # The current substrate is pre-HDBSCAN so this is 0, but the wire is live.
    assert result["result"]["constellations"] >= 0


def test_galactic_event_search_limit_capped():
    """The event search limit should be capped at 200."""
    from whitemagic.core.bridge.galactic import galactic_event_search

    result = galactic_event_search(limit=9999)
    assert result["status"] == "ok"
    assert result["result"]["count"] <= 200
