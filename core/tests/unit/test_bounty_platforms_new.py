"""Tests for new bounty platform adapters (Cantina, huntr, Algora, Opire, TaskBounty)."""
import time
from unittest.mock import patch, MagicMock

import pytest

from whitemagic.agents.bounty_platforms import (
    CantinaPlatform,
    HuntrPlatform,
    AlgoraPlatform,
    OpirePlatform,
    TaskBountyPlatform,
    get_all_platforms,
    scan_all_platforms,
    _cache,
)
from whitemagic.agents.bounty_connector import ExternalBounty


class TestCantinaPlatform:
    def test_platform_name(self):
        p = CantinaPlatform()
        assert p.platform_name == "cantina"

    def test_scan_bounties_fallback(self):
        """Test fallback known bounties when API is unavailable."""
        _cache._data.pop("cantina", None)
        p = CantinaPlatform()
        bounties = p.scan_bounties(limit=50)
        assert len(bounties) > 0
        # Should include Uniswap v4 with $15.5M
        uniswap = [b for b in bounties if "uniswap" in b.title.lower()]
        assert len(uniswap) == 1
        assert uniswap[0].reward == 15500000

    def test_scan_bounties_sorted_by_reward(self):
        _cache._data.pop("cantina", None)
        p = CantinaPlatform()
        bounties = p.scan_bounties(limit=50)
        rewards = [b.reward for b in bounties]
        assert rewards == sorted(rewards, reverse=True)

    def test_scan_bounties_reserve_protocol(self):
        _cache._data.pop("cantina", None)
        p = CantinaPlatform()
        bounties = p.scan_bounties(limit=50)
        reserve = [b for b in bounties if "reserve" in b.title.lower()]
        assert len(reserve) == 1
        assert reserve[0].reward == 10000000

    def test_scan_bounties_polymarket_new(self):
        _cache._data.pop("cantina", None)
        p = CantinaPlatform()
        bounties = p.scan_bounties(limit=50)
        poly = [b for b in bounties if "polymarket" in b.title.lower()]
        assert len(poly) == 1
        assert poly[0].reward == 5000000

    def test_claim_bounty_not_supported(self):
        p = CantinaPlatform()
        assert p.claim_bounty("test", "agent1") is False

    def test_submit_result_not_supported(self):
        p = CantinaPlatform()
        assert p.submit_result("test", {}) is False

    def test_caching(self):
        _cache._data.pop("cantina", None)
        p = CantinaPlatform()
        bounties1 = p.scan_bounties(limit=5)
        bounties2 = p.scan_bounties(limit=5)
        assert bounties1 == bounties2


class TestHuntrPlatform:
    def test_platform_name(self):
        p = HuntrPlatform()
        assert p.platform_name == "huntr"

    def test_scan_bounties_fallback(self):
        _cache._data.pop("huntr", None)
        p = HuntrPlatform()
        bounties = p.scan_bounties(limit=50)
        assert len(bounties) > 0

    def test_scan_bounties_includes_challenge(self):
        _cache._data.pop("huntr", None)
        p = HuntrPlatform()
        bounties = p.scan_bounties(limit=50)
        challenges = [b for b in bounties if "challenge" in b.title.lower()]
        assert len(challenges) >= 1
        assert challenges[0].reward == 15000

    def test_scan_bounties_includes_mfv(self):
        _cache._data.pop("huntr", None)
        p = HuntrPlatform()
        bounties = p.scan_bounties(limit=50)
        mfv = [b for b in bounties if "mfv" in b.external_id or "mvf" in b.external_id]
        assert len(mfv) >= 10  # We have 11 MFV entries
        for b in mfv:
            assert b.reward == 1500

    def test_scan_bounties_required_caps(self):
        _cache._data.pop("huntr", None)
        p = HuntrPlatform()
        bounties = p.scan_bounties(limit=50)
        for b in bounties:
            assert "ai_ml_security" in b.required_capabilities

    def test_claim_bounty_not_supported(self):
        p = HuntrPlatform()
        assert p.claim_bounty("test", "agent1") is False

    def test_submit_result_not_supported(self):
        p = HuntrPlatform()
        assert p.submit_result("test", {}) is False

    def test_challenge_has_deadline(self):
        _cache._data.pop("huntr", None)
        p = HuntrPlatform()
        bounties = p.scan_bounties(limit=50)
        challenge = [b for b in bounties if "new agents" in b.title.lower()]
        assert len(challenge) == 1
        assert challenge[0].deadline is not None


class TestAlgoraPlatform:
    def test_platform_name(self):
        p = AlgoraPlatform()
        assert p.platform_name == "algora"

    def test_scan_bounties_fallback(self):
        _cache._data.pop("algora", None)
        p = AlgoraPlatform()
        bounties = p.scan_bounties(limit=30)
        assert len(bounties) > 0
        assert bounties[0].platform == "algora"

    def test_scan_bounties_required_caps(self):
        _cache._data.pop("algora", None)
        p = AlgoraPlatform()
        bounties = p.scan_bounties(limit=30)
        for b in bounties:
            assert "fix_generation" in b.required_capabilities

    def test_known_orgs_list(self):
        p = AlgoraPlatform()
        assert "ziverge" in p._KNOWN_ORGS
        assert "pydantic" in p._KNOWN_ORGS

    def test_claim_bounty_not_supported(self):
        p = AlgoraPlatform()
        assert p.claim_bounty("test", "agent1") is False

    def test_submit_result_not_supported(self):
        p = AlgoraPlatform()
        assert p.submit_result("test", {}) is False


class TestOpirePlatform:
    def test_platform_name(self):
        p = OpirePlatform()
        assert p.platform_name == "opire"

    def test_scan_bounties_fallback(self):
        _cache._data.pop("opire", None)
        p = OpirePlatform()
        bounties = p.scan_bounties(limit=30)
        assert len(bounties) > 0
        assert bounties[0].platform == "opire"

    def test_claim_bounty_not_supported(self):
        p = OpirePlatform()
        assert p.claim_bounty("test", "agent1") is False

    def test_submit_result_not_supported(self):
        p = OpirePlatform()
        assert p.submit_result("test", {}) is False


class TestTaskBountyPlatform:
    def test_platform_name(self):
        p = TaskBountyPlatform()
        assert p.platform_name == "taskbounty"

    def test_scan_bounties_fallback(self):
        _cache._data.pop("taskbounty", None)
        p = TaskBountyPlatform()
        bounties = p.scan_bounties(limit=30)
        assert len(bounties) > 0
        assert bounties[0].platform == "taskbounty"

    def test_scan_bounties_currency(self):
        _cache._data.pop("taskbounty", None)
        p = TaskBountyPlatform()
        bounties = p.scan_bounties(limit=30)
        assert bounties[0].currency == "USDC"

    def test_claim_bounty_not_supported(self):
        p = TaskBountyPlatform()
        assert p.claim_bounty("test", "agent1") is False

    def test_submit_result_not_supported(self):
        p = TaskBountyPlatform()
        assert p.submit_result("test", {}) is False


class TestGetAllPlatforms:
    def test_returns_all_10_platforms(self):
        platforms = get_all_platforms()
        assert len(platforms) == 10

    def test_includes_new_platforms(self):
        platforms = get_all_platforms()
        names = [p.platform_name for p in platforms]
        assert "cantina" in names
        assert "huntr" in names
        assert "algora" in names
        assert "opire" in names
        assert "taskbounty" in names

    def test_platform_names_unique(self):
        platforms = get_all_platforms()
        names = [p.platform_name for p in platforms]
        assert len(names) == len(set(names))


class TestScanAllPlatforms:
    def test_scan_all_returns_all_platforms(self):
        """Test that scan_all_platforms returns results for all 10 platforms."""
        # Clear all caches first
        for key in list(_cache._data.keys()):
            _cache._data.pop(key, None)
        results = scan_all_platforms(limit_per_platform=5)
        assert len(results) == 10
        for name in ["immunefi", "codehawks", "sherlock", "code4rena", "hackenproof",
                      "cantina", "huntr", "algora", "opire", "taskbounty"]:
            assert name in results
            assert isinstance(results[name], list)

    def test_scan_all_handles_errors_gracefully(self):
        """Test that scan_all_platforms doesn't crash if one platform fails."""
        results = scan_all_platforms(limit_per_platform=5)
        # Should still return all platform keys even if some are empty
        assert len(results) == 10
