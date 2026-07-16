"""Tests for the 10 new bounty MCP tool handlers."""
import tempfile
from pathlib import Path

import pytest

from whitemagic.tools.handlers.v24_3_handlers import (
    handle_bounty_platforms,
    handle_bounty_scan_platform,
    handle_bounty_match,
    handle_bounty_deadlines,
    handle_bounty_stats,
    handle_bounty_earnings,
    handle_strata_model_security,
    handle_bounty_huntr_mfv,
    handle_bounty_opportunities,
    handle_bounty_register_agent,
)
from whitemagic.agents.bounty_platforms import _cache


class TestBountyPlatforms:
    def test_returns_all_platforms(self):
        result = handle_bounty_platforms()
        assert result["status"] == "success"
        assert result["count"] == 10
        names = [p["name"] for p in result["platforms"]]
        assert "immunefi" in names
        assert "cantina" in names
        assert "huntr" in names
        assert "algora" in names

    def test_platform_has_url(self):
        result = handle_bounty_platforms()
        for p in result["platforms"]:
            assert "name" in p
            assert "url" in p
            assert "supports_claim" in p
            assert "supports_submit" in p


class TestBountyScanPlatform:
    def test_scan_cantina(self):
        _cache._data.pop("cantina", None)
        result = handle_bounty_scan_platform(platform="cantina", limit=5)
        assert result["status"] == "success"
        assert result["platform"] == "cantina"
        assert result["count"] > 0

    def test_scan_huntr(self):
        _cache._data.pop("huntr", None)
        result = handle_bounty_scan_platform(platform="huntr", limit=10)
        assert result["status"] == "success"
        assert result["platform"] == "huntr"
        assert result["count"] > 0

    def test_scan_unknown_platform(self):
        result = handle_bounty_scan_platform(platform="nonexistent")
        assert result["status"] == "error"

    def test_scan_missing_platform_param(self):
        result = handle_bounty_scan_platform()
        assert result["status"] == "error"

    def test_scan_with_min_reward(self):
        _cache._data.pop("cantina", None)
        result = handle_bounty_scan_platform(platform="cantina", min_reward=5000000)
        assert result["status"] == "success"
        for b in result["bounties"]:
            assert b["reward"] >= 5000000


class TestBountyMatch:
    def test_match_returns_results(self):
        result = handle_bounty_match()
        assert result["status"] == "success"
        assert "matched" in result
        assert "matched_count" in result

    def test_match_with_min_score(self):
        result = handle_bounty_match(min_score=1.0)
        assert result["status"] == "success"
        for m in result["matched"]:
            assert m["match_score"] >= 1.0


class TestBountyDeadlines:
    def test_deadlines_returns_list(self):
        result = handle_bounty_deadlines()
        assert result["status"] == "success"
        assert "deadlines" in result
        assert "days_ahead" in result

    def test_deadlines_sorted_by_urgency(self):
        result = handle_bounty_deadlines(days_ahead=365, limit=50)
        if result["count"] > 1:
            deadlines = result["deadlines"]
            for i in range(len(deadlines) - 1):
                assert deadlines[i]["deadline"] <= deadlines[i + 1]["deadline"]

    def test_deadlines_days_ahead_filter(self):
        result = handle_bounty_deadlines(days_ahead=1)
        for d in result["deadlines"]:
            assert d["days_left"] <= 1


class TestBountyStats:
    def test_stats_aggregates(self):
        result = handle_bounty_stats()
        assert result["status"] == "success"
        assert result["total_platforms"] == 10
        assert result["total_bounties"] > 0
        assert "by_platform" in result
        assert "by_currency" in result

    def test_stats_per_platform(self):
        result = handle_bounty_stats()
        for name, stats in result["by_platform"].items():
            assert "count" in stats
            assert "total_reward" in stats
            assert "max_reward" in stats


class TestBountyEarnings:
    def test_earnings_returns_success(self):
        result = handle_bounty_earnings()
        assert result["status"] == "success"
        assert "earnings" in result
        assert "count" in result

    def test_earnings_with_status_filter(self):
        result = handle_bounty_earnings(status="pending")
        assert result["status"] == "success"


class TestStrataModelSecurity:
    def test_scan_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = handle_strata_model_security(project_path=tmpdir)
            assert result["status"] == "success"
            assert result["total_findings"] == 0
            assert len(result["checkers_run"]) == 10

    def test_scan_detects_unsafe_pickle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "model_utils.py"
            p.write_text("import pickle\npickle.load(open('model.pkl', 'rb'))\n")
            result = handle_strata_model_security(project_path=tmpdir)
            assert result["status"] == "success"
            assert result["total_findings"] > 0
            categories = [f["category"] for f in result["findings"]]
            assert "unsafe_deserialization" in categories

    def test_scan_detects_torch_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "train.py"
            p.write_text("import torch\nmodel = torch.load('model.pt')\n")
            result = handle_strata_model_security(project_path=tmpdir)
            assert result["status"] == "success"
            categories = [f["category"] for f in result["findings"]]
            assert "unsafe_torch_load" in categories

    def test_scan_missing_path(self):
        result = handle_strata_model_security(project_path="/nonexistent/path")
        assert result["status"] == "error"

    def test_scan_no_project_path(self):
        result = handle_strata_model_security()
        assert result["status"] == "error"


class TestBountyHuntrMfv:
    def test_returns_mfv_bounties(self):
        _cache._data.pop("huntr", None)
        result = handle_bounty_huntr_mfv()
        assert result["status"] == "success"
        assert result["mfv_count"] > 0
        assert result["total_value"] > 0

    def test_mfv_bounties_have_strata_mapping(self):
        _cache._data.pop("huntr", None)
        result = handle_bounty_huntr_mfv()
        for b in result["mfv_bounties"]:
            assert "strata_checker" in b
            assert b["strata_checker"].startswith("check_")

    def test_mfv_bounty_reward_is_1500(self):
        _cache._data.pop("huntr", None)
        result = handle_bounty_huntr_mfv()
        for b in result["mfv_bounties"]:
            assert b["reward"] == 1500

    def test_challenges_included(self):
        _cache._data.pop("huntr", None)
        result = handle_bounty_huntr_mfv()
        assert len(result["challenges"]) >= 1


class TestBountyOpportunities:
    def test_returns_opportunities(self):
        result = handle_bounty_opportunities()
        assert result["status"] == "success"
        assert "opportunities" in result

    def test_opportunities_sorted_by_score(self):
        result = handle_bounty_opportunities(limit=20)
        if result["count"] > 1:
            scores = [o["opportunity_score"] for o in result["opportunities"]]
            assert scores == sorted(scores, reverse=True)

    def test_min_reward_filter(self):
        result = handle_bounty_opportunities(min_reward=999999)
        for o in result["opportunities"]:
            assert o["reward"] >= 999999


class TestBountyRegisterAgent:
    def test_register_success(self):
        result = handle_bounty_register_agent(
            agent_id="test_agent_001",
            capabilities=["solidity_analysis", "code_analysis", "ai_ml_security"],
        )
        assert result["status"] == "success"
        assert result["agent_id"] == "test_agent_001"
        assert "solidity_analysis" in result["capabilities"]

    def test_register_missing_agent_id(self):
        result = handle_bounty_register_agent(capabilities=["code_analysis"])
        assert result["status"] == "error"

    def test_register_missing_capabilities(self):
        result = handle_bounty_register_agent(agent_id="test_agent_002")
        assert result["status"] == "error"
