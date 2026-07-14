"""Tests for P4 Security Enhancements — CrossChainAnalyzer and CanaryToken Layer."""

import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix="wm_test_p4_")
os.environ.setdefault("WM_STATE_ROOT", _tmp)
os.environ.setdefault("WM_SILENT_INIT", "1")


# ─── CrossChainAnalyzer Tests ────────────────────────────────────────────


class TestCrossChainAnalyzer:
    """Test multi-chain vulnerability correlation."""

    def test_analyze_basic(self):
        from whitemagic.tools.security.cross_chain_analyzer import CrossChainAnalyzer

        analyzer = CrossChainAnalyzer()
        chains = [
            {"chain_id": "ethereum", "vulnerabilities": [{"category": "reentrancy", "severity": "critical"}]},
            {"chain_id": "polygon", "vulnerabilities": [{"category": "reentrancy", "severity": "high"}]},
        ]

        result = analyzer.analyze(chains)
        assert result["chains_analyzed"] == 2
        assert result["total_findings"] > 0

    def test_analyze_with_bridge_connections(self):
        from whitemagic.tools.security.cross_chain_analyzer import CrossChainAnalyzer

        analyzer = CrossChainAnalyzer()
        chains = [
            {"chain_id": "ethereum", "vulnerabilities": [{"category": "unverified_lock", "severity": "critical"}]},
            {"chain_id": "polygon", "vulnerabilities": [{"category": "mint_without_burn", "severity": "critical"}]},
        ]
        bridges = [
            {"source_chain": "ethereum", "target_chain": "polygon", "bridge_type": "lock_mint", "tvl": 5_000_000},
        ]

        result = analyzer.analyze(chains, bridge_connections=bridges)
        assert result["bridge_connections"] == 1
        # Should detect lock_mint_drain pattern
        lock_mint_findings = [f for f in result["findings"] if f["category"] == "lock_mint_drain"]
        assert len(lock_mint_findings) > 0
        assert lock_mint_findings[0]["severity"] == "critical"

    def test_cross_chain_correlation(self):
        from whitemagic.tools.security.cross_chain_analyzer import CrossChainAnalyzer

        analyzer = CrossChainAnalyzer()
        chains = [
            {"chain_id": "ethereum", "vulnerabilities": [{"category": "reentrancy", "severity": "high"}]},
            {"chain_id": "bsc", "vulnerabilities": [{"category": "reentrancy", "severity": "high"}]},
            {"chain_id": "polygon", "vulnerabilities": [{"category": "reentrancy", "severity": "high"}]},
        ]

        result = analyzer.analyze(chains)
        cross_chain = [f for f in result["findings"] if f["category"] == "reentrancy" and len(f["chains_affected"]) >= 3]
        assert len(cross_chain) > 0
        assert cross_chain[0]["severity"] == "high"  # 3+ chains = high

    def test_chain_profiles_built(self):
        from whitemagic.tools.security.cross_chain_analyzer import CrossChainAnalyzer

        analyzer = CrossChainAnalyzer()
        chains = [
            {"chain_id": "ethereum", "vulnerabilities": [
                {"category": "reentrancy", "severity": "critical"},
                {"category": "access_control", "severity": "high"},
                {"category": "gas_limit", "severity": "low"},
            ]},
        ]

        result = analyzer.analyze(chains)
        profile = result["chain_profiles"]["ethereum"]
        assert profile["total_vulnerabilities"] == 3
        assert profile["critical_count"] == 1
        assert profile["high_count"] == 1
        assert profile["low_count"] == 1

    def test_composite_risk_scoring(self):
        from whitemagic.tools.security.cross_chain_analyzer import CrossChainAnalyzer

        analyzer = CrossChainAnalyzer()
        chains = [
            {"chain_id": "ethereum", "vulnerabilities": [{"category": "unverified_lock", "severity": "critical"}]},
            {"chain_id": "polygon", "vulnerabilities": [{"category": "mint_without_burn", "severity": "critical"}]},
        ]
        bridges = [
            {"source_chain": "ethereum", "target_chain": "polygon", "bridge_type": "lock_mint", "tvl": 50_000_000},
        ]

        result = analyzer.analyze(chains, bridge_connections=bridges)
        for finding in result["findings"]:
            assert 0.0 <= finding["composite_risk_score"] <= 1.0

    def test_overall_risk_levels(self):
        from whitemagic.tools.security.cross_chain_analyzer import CrossChainAnalyzer

        analyzer = CrossChainAnalyzer()
        # No findings -> low
        result = analyzer.analyze([])
        assert result["overall_risk"] == "low"

        # Critical findings -> critical
        chains = [
            {"chain_id": "ethereum", "vulnerabilities": [{"category": "unverified_lock", "severity": "critical"}]},
            {"chain_id": "polygon", "vulnerabilities": [{"category": "mint_without_burn", "severity": "critical"}]},
        ]
        bridges = [{"source_chain": "ethereum", "target_chain": "polygon", "bridge_type": "lock_mint", "tvl": 5_000_000}]
        result = analyzer.analyze(chains, bridges)
        assert result["overall_risk"] == "critical"

    def test_list_bridge_patterns(self):
        from whitemagic.tools.security.cross_chain_analyzer import CrossChainAnalyzer

        analyzer = CrossChainAnalyzer()
        patterns = analyzer.list_bridge_patterns()
        assert "lock_mint_drain" in patterns
        assert "validator_collusion" in patterns
        assert "description" in patterns["lock_mint_drain"]

    def test_list_chain_signatures(self):
        from whitemagic.tools.security.cross_chain_analyzer import CrossChainAnalyzer

        analyzer = CrossChainAnalyzer()
        sigs = analyzer.list_chain_signatures()
        assert "ethereum" in sigs
        assert "solana" in sigs
        assert "reentrancy" in sigs["ethereum"]

    def test_singleton(self):
        from whitemagic.tools.security.cross_chain_analyzer import (
            get_cross_chain_analyzer,
            get_cross_chain_analyzer as g2,
        )

        assert get_cross_chain_analyzer() is g2()

    def test_empty_chains(self):
        from whitemagic.tools.security.cross_chain_analyzer import CrossChainAnalyzer

        analyzer = CrossChainAnalyzer()
        result = analyzer.analyze([])
        assert result["chains_analyzed"] == 0
        assert result["total_findings"] == 0
        assert result["overall_risk"] == "low"


# ─── CanaryToken Layer Tests ─────────────────────────────────────────────


class TestCanaryTokenLayer:
    """Test canary token deployment and triggering."""

    def test_deploy_api_key_canary(self):
        from whitemagic.security.canary_tokens import CanaryTokenManager, CanaryType, CanaryStatus

        mgr = CanaryTokenManager()
        canary = mgr.deploy_api_key_canary("config.yaml", "Test API key")

        assert canary.canary_type == CanaryType.API_KEY
        assert canary.status == CanaryStatus.DEPLOYED
        assert canary.token_value.startswith("sk-")
        assert canary.location == "config.yaml"

    def test_deploy_credential_canary(self):
        from whitemagic.security.canary_tokens import CanaryTokenManager, CanaryType

        mgr = CanaryTokenManager()
        canary = mgr.deploy_credential_canary(".env", "Test credential")

        assert canary.canary_type == CanaryType.CREDENTIAL
        assert canary.token_value.startswith("wm_cred_")

    def test_deploy_endpoint_canary(self):
        from whitemagic.security.canary_tokens import CanaryTokenManager, CanaryType

        mgr = CanaryTokenManager()
        canary = mgr.deploy_endpoint_canary("routes.ts", "Test endpoint")

        assert canary.canary_type == CanaryType.ENDPOINT
        assert "/api/internal/" in canary.token_value

    def test_trigger_canary(self):
        from whitemagic.security.canary_tokens import CanaryTokenManager, CanaryType, CanaryStatus

        mgr = CanaryTokenManager()
        canary = mgr.deploy(
            CanaryType.API_KEY,
            "Test canary",
            "config.yaml",
        )

        result = mgr.check_trigger(canary.token_value, triggered_by="test_user")
        assert result["triggered"] is True
        assert result["token_id"] == canary.token_id

        # Check status changed
        assert mgr._tokens[canary.token_id].status == CanaryStatus.TRIGGERED

    def test_trigger_no_match(self):
        from whitemagic.security.canary_tokens import CanaryTokenManager

        mgr = CanaryTokenManager()
        result = mgr.check_trigger("nonexistent_value", triggered_by="test")
        assert result["triggered"] is False
        assert result["reason"] == "no_match"

    def test_trigger_already_triggered(self):
        from whitemagic.security.canary_tokens import CanaryTokenManager, CanaryType

        mgr = CanaryTokenManager()
        canary = mgr.deploy(CanaryType.API_KEY, "Test", "config.yaml")

        mgr.check_trigger(canary.token_value, triggered_by="user1")
        result = mgr.check_trigger(canary.token_value, triggered_by="user2")
        assert result["triggered"] is False
        assert result["reason"] == "already_triggered"

    def test_revoke_canary(self):
        from whitemagic.security.canary_tokens import CanaryTokenManager, CanaryType, CanaryStatus

        mgr = CanaryTokenManager()
        canary = mgr.deploy(CanaryType.API_KEY, "Test", "config.yaml")

        result = mgr.revoke(canary.token_id)
        assert result["revoked"] is True
        assert mgr._tokens[canary.token_id].status == CanaryStatus.REVOKED

        # Triggering a revoked canary should not work
        trigger_result = mgr.check_trigger(canary.token_value)
        assert trigger_result["triggered"] is False
        assert trigger_result["reason"] == "revoked"

    def test_expired_canary(self):
        from whitemagic.security.canary_tokens import CanaryTokenManager, CanaryType, CanaryStatus

        mgr = CanaryTokenManager()
        canary = mgr.deploy(CanaryType.API_KEY, "Test", "config.yaml", ttl_seconds=0.01)

        import time
        time.sleep(0.02)

        result = mgr.check_trigger(canary.token_value)
        assert result["triggered"] is False
        assert result["reason"] == "expired"
        assert mgr._tokens[canary.token_id].status == CanaryStatus.EXPIRED

    def test_list_tokens(self):
        from whitemagic.security.canary_tokens import CanaryTokenManager, CanaryType, CanaryStatus

        mgr = CanaryTokenManager()
        mgr.deploy(CanaryType.API_KEY, "Token 1", "config.yaml")
        mgr.deploy(CanaryType.CREDENTIAL, "Token 2", ".env")

        all_tokens = mgr.list_tokens()
        assert len(all_tokens) == 2

        deployed = mgr.list_tokens(status_filter=CanaryStatus.DEPLOYED)
        assert len(deployed) == 2

    def test_trigger_log(self):
        from whitemagic.security.canary_tokens import CanaryTokenManager, CanaryType

        mgr = CanaryTokenManager()
        canary = mgr.deploy(CanaryType.API_KEY, "Test", "config.yaml")
        mgr.check_trigger(canary.token_value, triggered_by="attacker", context={"ip": "10.0.0.1"})

        log = mgr.get_trigger_log()
        assert len(log) == 1
        assert log[0]["triggered_by"] == "attacker"
        assert log[0]["context"]["ip"] == "10.0.0.1"

    def test_status(self):
        from whitemagic.security.canary_tokens import CanaryTokenManager, CanaryType

        mgr = CanaryTokenManager()
        mgr.deploy(CanaryType.API_KEY, "Active 1", "config.yaml")
        mgr.deploy(CanaryType.CREDENTIAL, "Active 2", ".env")
        canary = mgr.deploy(CanaryType.ENDPOINT, "Triggered", "routes.ts")
        mgr.check_trigger(canary.token_value)

        status = mgr.status()
        assert status["total_tokens"] == 3
        assert status["active"] == 2
        assert status["triggered"] == 1
        assert status["trigger_log_count"] == 1

    def test_cleanup_expired(self):
        from whitemagic.security.canary_tokens import CanaryTokenManager, CanaryType

        mgr = CanaryTokenManager()
        mgr.deploy(CanaryType.API_KEY, "Expired", "config.yaml", ttl_seconds=0.01)
        mgr.deploy(CanaryType.CREDENTIAL, "Active", ".env", ttl_seconds=3600)

        import time
        time.sleep(0.02)

        removed = mgr.cleanup_expired()
        assert removed == 1
        assert mgr.status()["total_tokens"] == 1

    def test_token_value_masked_in_dict(self):
        from whitemagic.security.canary_tokens import CanaryTokenManager, CanaryType

        mgr = CanaryTokenManager()
        canary = mgr.deploy(CanaryType.API_KEY, "Test", "config.yaml")
        d = canary.to_dict()
        # Value should be masked (first 8 chars + ...)
        assert "..." in d["token_value"]
        assert len(d["token_value"]) < len(canary.token_value)

    def test_singleton(self):
        from whitemagic.security.canary_tokens import get_canary_manager, get_canary_manager as g2

        assert get_canary_manager() is g2()
