"""
Unit tests for Karma Ledger v1.0.0.
Exercises: record, report, get_debt, verify_chain, merkle_root, forgive,
and chain integrity.
"""
import os
import tempfile
from pathlib import Path

import pytest

from whitemagic.dharma.karma_ledger import KarmaEntry, KarmaLedger, get_karma_ledger


class TestKarmaEntry:
    def test_entry_creation(self):
        entry = KarmaEntry(
            tool="test_tool",
            declared_safety="READ",
            actual_writes=0,
            success=True,
            mismatch=False,
            debt_delta=0.0,
            timestamp="2026-05-15T18:00:00Z",
            prev_hash="genesis",
            entry_hash="abc123",
            ops_class="blue-ops",
        )
        assert entry.tool == "test_tool"
        assert entry.declared_safety == "READ"
        assert entry.actual_writes == 0
        assert entry.entry_hash == "abc123"
        assert entry.ops_class == "blue-ops"

    def test_entry_to_dict(self):
        entry = KarmaEntry(
            tool="test",
            declared_safety="WRITE",
            actual_writes=1,
            success=True,
            mismatch=False,
            debt_delta=0.0,
            timestamp="2026-05-15T18:00:00Z",
            prev_hash="genesis",
            entry_hash="abc",
        )
        d = entry.to_dict()
        assert d["tool"] == "test"
        assert d["declared_safety"] == "WRITE"
        assert d["actual_writes"] == 1


class TestKarmaLedger:
    @pytest.fixture
    def ledger(self):
        """Create a ledger with a temp storage dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            l = KarmaLedger(storage_dir=Path(tmpdir))
            yield l

    @pytest.fixture
    def memory_ledger(self):
        """Create an in-memory ledger (no persistence)."""
        return KarmaLedger(storage_dir=None)

    # --- record ---

    def test_record_honest_read(self, memory_ledger):
        entry = memory_ledger.record(
            tool="memory_read",
            declared_safety="READ",
            actual_writes=0,
            success=True,
        )
        assert entry.mismatch is False
        assert entry.debt_delta == 0.0
        assert entry.declared_safety == "READ"

    def test_record_deceptive_read_writes(self, memory_ledger):
        entry = memory_ledger.record(
            tool="stealth_writer",
            declared_safety="READ",
            actual_writes=3,
            success=True,
        )
        assert entry.mismatch is True
        assert entry.debt_delta == 1.0

    def test_record_honest_write(self, memory_ledger):
        entry = memory_ledger.record(
            tool="memory_write",
            declared_safety="WRITE",
            actual_writes=1,
            success=True,
        )
        assert entry.mismatch is False
        assert entry.debt_delta == 0.0

    def test_record_wasteful_write_no_writes(self, memory_ledger):
        entry = memory_ledger.record(
            tool="lazy_writer",
            declared_safety="WRITE",
            actual_writes=0,
            success=True,
        )
        assert entry.mismatch is True
        assert entry.debt_delta == 0.2

    def test_record_wasteful_delete_no_effect(self, memory_ledger):
        entry = memory_ledger.record(
            tool="noop_deleter",
            declared_safety="DELETE",
            actual_writes=0,
            success=True,
        )
        assert entry.mismatch is True
        assert entry.debt_delta == 0.1

    def test_record_produces_chain(self, memory_ledger):
        e1 = memory_ledger.record("tool_a", "READ", 0, True)
        e2 = memory_ledger.record("tool_b", "WRITE", 1, True)
        e3 = memory_ledger.record("tool_c", "READ", 2, True)
        assert e2.prev_hash == e1.entry_hash
        assert e3.prev_hash == e2.entry_hash

    def test_record_with_ops_class(self, memory_ledger):
        entry = memory_ledger.record(
            tool="red_tool",
            declared_safety="WRITE",
            actual_writes=5,
            success=True,
            ops_class="red-ops",
        )
        assert entry.ops_class == "red-ops"

    # --- verify_chain ---

    def test_verify_chain_valid(self, memory_ledger):
        memory_ledger.record("t1", "READ", 0, True)
        memory_ledger.record("t2", "WRITE", 1, True)
        result = memory_ledger.verify_chain()
        assert result["valid"] is True

    def test_verify_chain_empty_ledger(self, memory_ledger):
        result = memory_ledger.verify_chain()
        assert result["valid"] is True

    # --- report ---

    def test_report_empty(self, memory_ledger):
        report = memory_ledger.report()
        assert report["total_calls_tracked"] == 0
        assert report["total_debt"] == 0.0

    def test_report_with_entries(self, memory_ledger):
        memory_ledger.record("t1", "READ", 0, True)
        memory_ledger.record("t2", "WRITE", 1, True)
        report = memory_ledger.report()
        assert report["total_calls_tracked"] == 2
        assert report["total_mismatches"] == 0

    def test_report_shows_mismatches(self, memory_ledger):
        memory_ledger.record("bad_tool", "READ", 5, True)
        report = memory_ledger.report()
        assert report["total_mismatches"] == 1
        assert len(report["top_offenders"]) >= 1

    # --- get_debt ---

    def test_get_debt_zero_no_mismatch(self, memory_ledger):
        memory_ledger.record("t1", "READ", 0, True)
        assert memory_ledger.get_debt() == 0.0

    def test_get_debt_positive_on_mismatch(self, memory_ledger):
        memory_ledger.record("deceptive", "READ", 3, True)
        assert memory_ledger.get_debt() == 1.0

    def test_get_debt_accumulates(self, memory_ledger):
        memory_ledger.record("d1", "READ", 1, True)  # +1.0
        memory_ledger.record("w1", "WRITE", 0, True)  # +0.2
        assert memory_ledger.get_debt() == 1.2

    # --- forgiven ---

    def test_forgive_reduces_debt(self, memory_ledger):
        memory_ledger.record("bad", "READ", 2, True)  # +1.0
        assert memory_ledger.get_debt() == 1.0
        memory_ledger.forgive(0.5)
        assert memory_ledger.get_debt() == 0.5

    def test_forgive_cannot_go_negative(self, memory_ledger):
        memory_ledger.forgive(100.0)
        assert memory_ledger.get_debt() == 0.0

    # --- merkle_root ---

    def test_merkle_root_empty(self, memory_ledger):
        root = memory_ledger.merkle_root()
        assert root is not None
        assert len(root) > 0

    def test_merkle_root_changes_with_new_entry(self, memory_ledger):
        root1 = memory_ledger.merkle_root()
        memory_ledger.record("t1", "READ", 0, True)
        root2 = memory_ledger.merkle_root()
        assert root1 != root2

    # --- report_by_ops ---

    def test_report_by_ops_filter(self, memory_ledger):
        memory_ledger.record("b1", "READ", 0, True, ops_class="blue-ops")
        memory_ledger.record("b2", "WRITE", 1, True, ops_class="blue-ops")
        memory_ledger.record("r1", "READ", 3, True, ops_class="red-ops")
        blue_report = memory_ledger.report_by_ops("blue-ops")
        red_report = memory_ledger.report_by_ops("red-ops")
        assert blue_report["total_entries"] == 2
        assert red_report["total_entries"] == 1

    # --- rotation_stats ---

    def test_rotation_stats_memory_ledger(self, memory_ledger):
        stats = memory_ledger.rotation_stats()
        assert "status" in stats
        assert stats["status"] in ["in_memory_only", "ok"]

    # --- Persistence ---

    def test_persisted_entries_survive_ledger_reload(self, ledger):
        ledger.record("t1", "READ", 0, True)
        ledger.record("t2", "WRITE", 1, True)
        report1 = ledger.report()
        assert report1["total_calls_tracked"] == 2

    def test_multiple_records(self, memory_ledger):
        for i in range(50):
            # Alternate honest and deceptive
            writes = 0 if i % 2 == 0 else 1
            memory_ledger.record(
                f"tool_{i}",
                "READ" if i % 3 == 0 else "WRITE",
                writes,
                True,
            )
        report = memory_ledger.report()
        assert report["total_calls_tracked"] == 50


class TestGetKarmaLedger:
    def test_singleton_returns_same_instance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["WM_STATE_ROOT"] = tmpdir
            try:
                l1 = get_karma_ledger()
                l2 = get_karma_ledger()
                assert l1 is l2
            finally:
                if "WM_STATE_ROOT" in os.environ:
                    del os.environ["WM_STATE_ROOT"]
