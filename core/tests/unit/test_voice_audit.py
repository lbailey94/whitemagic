"""Tests for Jaynes Voice Audit and Quarantine."""

from unittest.mock import patch

import pytest

from whitemagic.core.governance.quarantine import QuarantineManager
from whitemagic.core.governance.voice_audit import (
    ClaimLog,
    VoiceAuditScanner,
)


class TestClaimLog:
    def test_register_and_verify(self):
        log = ClaimLog()
        cid = log.register("module_a", "delete_memory", {"memory_id": "123"})
        assert cid.startswith("claim_")
        assert len(log.get_unverified()) == 1
        entry = log.verify("delete_memory", {"memory_id": "123"})
        assert entry is not None
        assert entry.verified is True
        assert len(log.get_unverified()) == 0

    def test_verify_no_match(self):
        log = ClaimLog()
        log.register("module_a", "delete_memory", {"memory_id": "123"})
        entry = log.verify("create_memory")
        assert entry is None
        assert len(log.get_unverified()) == 1

    def test_prune_old(self):
        log = ClaimLog(max_age_minutes=0)
        log.register("module_a", "tool_x")
        # Immediate prune on next access
        assert len(log.get_unverified()) == 0


class TestVoiceAuditScanner:
    def test_scan_finds_hallucination(self):
        scanner = VoiceAuditScanner()
        scanner.register_claim("module_a", "delete_memory")
        # No karma ledger entry for delete_memory
        report = scanner.scan()
        assert report.scanned_claims == 1
        assert report.verified_claims == 0
        assert len(report.hallucinated_claims) == 1
        assert report.hallucinated_claims[0]["tool"] == "delete_memory"
        assert report.quarantine_triggered is True

    def test_scan_verifies_real_tool(self):
        scanner = VoiceAuditScanner()
        scanner.register_claim("module_a", "health_report")
        # Simulate a karma ledger entry for health_report
        try:
            from whitemagic.dharma.karma_ledger import get_karma_ledger
            ledger = get_karma_ledger()
            ledger.record(tool="health_report", declared_safety="READ", actual_writes=0, success=True)
        except Exception:
            pytest.skip("Karma ledger unavailable")
        report = scanner.scan()
        assert report.verified_claims >= 1

    def test_stats(self):
        scanner = VoiceAuditScanner()
        scanner.register_claim("mod", "tool")
        scanner.scan()
        stats = scanner.get_stats()
        assert stats["scan_count"] == 1
        assert stats["last_report"] is not None


class TestQuarantineManager:
    def test_quarantine_and_release(self):
        qm = QuarantineManager()
        qm.quarantine_session("sess_1", "Hallucinated claim")
        assert qm.is_quarantined("sess_1") is True
        qm.release_session("sess_1", "Reviewed: false positive")
        assert qm.is_quarantined("sess_1") is False

    def test_list_quarantined(self):
        qm = QuarantineManager()
        qm.quarantine_session("sess_1", "reason1")
        qm.quarantine_session("sess_2", "reason2")
        active = qm.list_quarantined()
        assert len(active) == 2
        qm.release_session("sess_1")
        active = qm.list_quarantined()
        assert len(active) == 1
        all_entries = qm.list_quarantined(include_reviewed=True)
        assert len(all_entries) == 2

    def test_remove_session(self):
        qm = QuarantineManager()
        qm.quarantine_session("sess_1", "reason")
        assert qm.remove_session("sess_1") is True
        assert qm.is_quarantined("sess_1") is False
        assert qm.remove_session("sess_1") is False

    def test_status(self):
        qm = QuarantineManager()
        qm.quarantine_session("sess_1", "reason")
        qm.release_session("sess_1")
        status = qm.status()
        assert status["active_quarantines"] == 0
        assert status["reviewed_quarantines"] == 1
