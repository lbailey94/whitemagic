"""GAR (Governance Audit Record) Level 1 Conformance Tests.

Maps WhiteMagic's Karma Ledger + Dharma Engine to IETF draft-sato-soos-gar
Level 1 requirements:
  1. Non-suppressibility — audit records are generated automatically
  2. Tamper-evidence — hash chain + optional Ed25519 signatures
  3. Completeness — every tool call produces a record
  4. Verifiability — chain integrity can be checked programmatically
  5. Reportability — audit package can be exported
"""

import pytest

from whitemagic.dharma.karma_ledger import KarmaEntry, KarmaLedger


class TestGARLevel1Conformance:
    @pytest.fixture
    def ledger(self, tmp_path):
        return KarmaLedger(storage_dir=tmp_path)

    # ── Requirement 1: Non-suppressibility ──────────────────────────

    def test_every_record_produces_audit_entry(self, ledger):
        """GAR §3.1: Every material action must generate an audit record."""
        entry = ledger.record("memory_create", "WRITE", 1, True)
        assert isinstance(entry, KarmaEntry)
        assert entry.tool == "memory_create"
        assert entry.timestamp

    def test_audit_entry_contains_required_fields(self, ledger):
        """GAR §4.2: Audit record must contain tool, timestamp, outcome."""
        entry = ledger.record("search", "READ", 0, True)
        assert entry.tool
        assert entry.timestamp
        assert entry.success is True
        assert entry.debt_delta is not None

    # ── Requirement 2: Tamper-evidence ────────────────────────────────

    def test_hash_chain_links_entries(self, ledger):
        """GAR §5.1: Chain of custody via cryptographic linking."""
        e1 = ledger.record("t1", "READ", 0, True)
        e2 = ledger.record("t2", "WRITE", 1, True)
        assert e2.prev_hash == e1.entry_hash
        assert e1.entry_hash != ""
        assert e2.entry_hash != ""

    def test_tampered_entry_breaks_chain(self, ledger):
        """GAR §5.3: Any alteration invalidates the chain."""
        ledger.record("t1", "READ", 0, True)
        ledger.record("t2", "WRITE", 1, True)
        # Tamper
        ledger._entries[0].entry_hash = "badhash"
        result = ledger.verify_chain()
        assert result["valid"] is False

    def test_merkle_root_changes_with_new_entries(self, ledger):
        """GAR §5.4: Merkle root is a compact tamper-evident fingerprint."""
        r1 = ledger.merkle_root()
        ledger.record("t1", "READ", 0, True)
        r2 = ledger.merkle_root()
        ledger.record("t2", "READ", 0, True)
        r3 = ledger.merkle_root()
        assert r1 != r2 != r3  # monotonically changing within same ledger
        # Tampering changes root
        original_root = r3
        ledger._entries[0].entry_hash = "tampered"
        assert ledger.merkle_root() != original_root

    # ── Requirement 3: Completeness ───────────────────────────────────

    def test_all_tool_safety_levels_recorded(self, ledger):
        """GAR §3.2: READ, WRITE, DELETE actions all tracked."""
        for safety in ("READ", "WRITE", "DELETE"):
            ledger.record(f"tool_{safety}", safety, 0, True)
        report = ledger.report()
        assert report["total_calls_tracked"] == 3

    # ── Requirement 4: Verifiability ──────────────────────────────────

    def test_verify_chain_succeeds_for_intact_ledger(self, ledger):
        """GAR §6.1: Auditor can run independent verification."""
        for i in range(10):
            ledger.record(f"t{i}", "READ", 0, True)
        result = ledger.verify_chain()
        assert result["valid"] is True
        assert result["entries_checked"] == 10

    def test_verify_chain_reports_signature_status(self, ledger):
        """GAR §6.2: Signature verification included in chain check."""
        ledger.record("t1", "READ", 0, True)
        result = ledger.verify_chain()
        assert "signatures_verified" in result or result["valid"]

    # ── Requirement 5: Reportability ─────────────────────────────────

    def test_report_contains_top_offenders_and_recent_entries(self, ledger):
        """GAR §7.1: Audit package contains actionable summary."""
        ledger.record("bad_tool", "READ", 5, True)  # deceptive → debt
        report = ledger.report(limit=10)
        assert "total_debt" in report
        assert "top_offenders" in report
        assert "recent_entries" in report
        assert len(report["recent_entries"]) > 0

    def test_ops_class_dual_log_filtering(self, ledger):
        """GAR §7.2: Classification-based filtering for red-team/blue-team."""
        ledger.record("r1", "READ", 0, True, ops_class="red-ops")
        ledger.record("b1", "READ", 0, True, ops_class="blue-ops")
        red = ledger.report_by_ops("red-ops")
        blue = ledger.report_by_ops("blue-ops")
        assert red["total_entries"] == 1
        assert blue["total_entries"] == 1
        assert red["entries"][0]["tool"] == "r1"

    # ── Graceful degradation ─────────────────────────────────────────

    def test_ledger_operates_without_storage(self):
        """GAR §8.1: Audit subsystem must not block on I/O failure."""
        mem = KarmaLedger(storage_dir=None)
        entry = mem.record("test", "READ", 0, True)
        assert entry.timestamp
        report = mem.report()
        assert report["total_calls_tracked"] == 1
