"""Tests for P3/P4 Security Enhancements.

Covers:
  - HermitCrab → EngagementToken integration (revoke on WITHDRAWN)
  - EngagementTokenManager.revoke_all()
  - AdaptiveDefense → VulnKB feedback loop
"""

import os
import tempfile
from pathlib import Path

import pytest

_tmp = tempfile.mkdtemp(prefix="wm_test_sec_enh_")
os.environ.setdefault("WM_STATE_ROOT", _tmp)
os.environ.setdefault("WM_SILENT_INIT", "1")


# ─── HermitCrab → EngagementToken Integration ────────────────────────────


class TestHermitCrabTokenRevocation:
    """Test that HermitCrab revokes engagement tokens when withdrawing."""

    def test_revoke_all_method_exists(self):
        from whitemagic.security.engagement_tokens import get_token_manager

        mgr = get_token_manager()
        assert hasattr(mgr, "revoke_all")

    def test_revoke_all_with_no_tokens(self):
        from whitemagic.security.engagement_tokens import EngagementTokenManager

        mgr = EngagementTokenManager()
        count = mgr.revoke_all(reason="test")
        assert count == 0

    def test_revoke_all_with_active_tokens(self):
        from whitemagic.security.engagement_tokens import EngagementTokenManager

        mgr = EngagementTokenManager()
        mgr.issue(scope=["10.0.0.*"], tools=["red_*"], issuer="test", duration_minutes=5)
        mgr.issue(scope=["192.168.*"], tools=["nmap_*"], issuer="test", duration_minutes=5)

        count = mgr.revoke_all(reason="emergency")
        assert count == 2

        # All tokens should now be revoked
        result = mgr.list_tokens()
        for token in result.get("tokens", []):
            assert token["revoked"] is True

    def test_revoke_all_skips_already_revoked(self):
        from whitemagic.security.engagement_tokens import EngagementTokenManager

        mgr = EngagementTokenManager()
        issued = mgr.issue(scope=["10.0.0.*"], tools=["red_*"], issuer="test", duration_minutes=5)
        token_id = issued["token"]["token_id"]

        # Revoke one first
        mgr.revoke(token_id)
        # Then revoke_all should not count it
        count = mgr.revoke_all(reason="test")
        assert count == 0

    def test_hermit_crab_revokes_tokens_on_withdrawal(self):
        from whitemagic.security.engagement_tokens import EngagementTokenManager, get_token_manager
        from whitemagic.security.hermit_crab import HermitCrab, HermitState

        # Issue a token first
        mgr = get_token_manager()
        mgr.issue(scope=["10.0.0.*"], tools=["red_*"], issuer="test", duration_minutes=5)

        # Create HermitCrab with fresh state dir
        state_dir = Path(tempfile.mkdtemp(prefix="wm_hc_test_"))
        hc = HermitCrab(state_dir=state_dir)

        # Force withdrawal
        hc.withdraw(reason="test threat")

        assert hc._state == HermitState.WITHDRAWN

        # Check that tokens were revoked
        tokens = mgr.list_tokens()
        for token in tokens.get("tokens", []):
            if token.get("issuer") == "test":
                assert token["revoked"] is True

    def test_hermit_crab_guarded_does_not_revoke(self):
        from whitemagic.security.engagement_tokens import EngagementTokenManager
        from whitemagic.security.hermit_crab import HermitCrab, HermitState

        mgr = EngagementTokenManager()
        issued = mgr.issue(scope=["10.0.0.*"], tools=["red_*"], issuer="test2", duration_minutes=5)
        token_id = issued["token"]["token_id"]

        state_dir = Path(tempfile.mkdtemp(prefix="wm_hc_guarded_"))
        hc = HermitCrab(state_dir=state_dir)

        # Trigger guarded state (threat above 0.3 but below 0.7)
        hc.assess_threat(
            signals={
                "rapid_tool_calls": True,
                "unusual_access_pattern": True,
            }
        )

        # Should be in guarded state, not withdrawn
        if hc._state == HermitState.GUARDED:
            # Token should still be valid
            token = mgr._tokens.get(token_id)
            assert token is not None
            assert not token.revoked


# ─── AdaptiveDefense → VulnKB Feedback ───────────────────────────────────


class TestAdaptiveDefenseVulnKBFeedback:
    """Test that AdaptiveDefenseLoop patterns can feed into VulnKnowledgeBase."""

    def test_vuln_kb_add_pattern_from_adaptive(self):
        """Simulate feeding a discovered attack pattern into the VulnKB."""
        from whitemagic.tools.security.vuln_knowledge import VulnKnowledgeBase, VulnerabilityPattern

        kb = VulnKnowledgeBase()
        initial_count = len(kb._patterns)

        # Simulate a pattern discovered by AdaptiveDefenseLoop
        pattern = VulnerabilityPattern(
            pattern_id="ADAPT-001",
            name="Prompt injection via unicode homoglyph",
            category="injection",
            severity="high",
            description="Attack uses unicode homoglyphs to bypass input sanitization",
            detection_regex=r"[\u0455\u0430\u0435\u0440\u043e\u0441\u0445]",
            detection_keywords=["homoglyph", "unicode_bypass"],
            false_positive_indicators=["legitimate_internationalization"],
            mitigation="Normalize unicode before pattern matching",
            cwe_id="CWE-20",
            swc_id="",
            source="adaptive_defense",
            confidence=0.85,
        )
        kb.add_pattern(pattern)

        assert len(kb._patterns) == initial_count + 1
        found = kb.get_pattern("ADAPT-001")
        assert found is not None
        assert found.source == "adaptive_defense"

    def test_persistent_vuln_kb_stores_adaptive_patterns(self):
        """Test that PersistentVulnKnowledgeBase stores adaptive defense patterns."""
        from whitemagic.tools.security.vuln_kb_persistent import PersistentVulnKnowledgeBase
        from whitemagic.tools.security.vuln_knowledge import VulnerabilityPattern

        db_path = Path(tempfile.mkdtemp(prefix="wm_vulnkb_adapt_")) / "test_vuln.db"
        kb = PersistentVulnKnowledgeBase(db_path)

        pattern = VulnerabilityPattern(
            pattern_id="ADAPT-PERSIST-001",
            name="XSS via SVG onload",
            category="xss",
            severity="medium",
            description="SVG onload event handler bypasses standard XSS filters",
            detection_regex=r"<svg[^>]+onload\s*=",
            detection_keywords=["svg", "onload", "xss"],
            false_positive_indicators=["svg_documentation"],
            mitigation="Strip event handlers from SVG elements",
            cwe_id="CWE-79",
            swc_id="",
            source="adaptive_defense",
            confidence=0.78,
        )
        kb.add_pattern(pattern)

        # Verify persisted
        kb2 = PersistentVulnKnowledgeBase(db_path)
        loaded = kb2.get_pattern("ADAPT-PERSIST-001")
        assert loaded is not None
        assert loaded.source == "adaptive_defense"
        assert loaded.confidence == 0.78
