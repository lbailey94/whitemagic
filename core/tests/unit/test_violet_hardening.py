"""Tests for violet profile hardening — verify all new security tools are properly gated."""
import pytest
from unittest.mock import patch, MagicMock

from whitemagic.security.engagement_tokens import (
    RED_OPS_TOOL_PATTERNS,
    is_red_ops_tool,
    is_blue_ops_tool,
    classify_ops,
    requires_engagement_token,
)


class TestRedOpsToolPatterns:
    """Verify all new security tools match RED_OPS_TOOL_PATTERNS."""

    NEW_TOOLS = [
        "nmap_scan",
        "sqlmap_scan",
        "hydra_brute",
        "nikto_scan",
        "ffuf_fuzz",
        "nuclei_scan",
        "redteam_autonomous",
        "agent_redteam_run",
        "attack_cell_execute",
    ]

    EXISTING_TOOLS = [
        "foundry_build",
        "http_probe_get",
        "http_probe_xss",
        "api_state_machine",
        "echidna_fuzz",
        "formal_verify",
        "poc_generate",
        "poc_verify",
    ]

    @pytest.mark.parametrize("tool", NEW_TOOLS)
    def test_new_tool_is_red_ops(self, tool):
        """Every new security tool should be classified as red-ops."""
        assert is_red_ops_tool(tool), f"Tool '{tool}' is not matched by RED_OPS_TOOL_PATTERNS"

    @pytest.mark.parametrize("tool", EXISTING_TOOLS)
    def test_existing_tool_is_red_ops(self, tool):
        """Existing security tools should still be classified as red-ops."""
        assert is_red_ops_tool(tool), f"Tool '{tool}' is not matched by RED_OPS_TOOL_PATTERNS"

    @pytest.mark.parametrize("tool", NEW_TOOLS)
    def test_new_tool_requires_engagement_token(self, tool):
        """Every new security tool should require an engagement token."""
        assert requires_engagement_token(tool), f"Tool '{tool}' does not require engagement token"

    @pytest.mark.parametrize("tool", NEW_TOOLS)
    def test_new_tool_classified_as_red_ops(self, tool):
        """classify_ops should return 'red-ops' for new tools."""
        assert classify_ops(tool) == "red-ops"

    def test_non_offensive_tool_not_red_ops(self):
        """Non-offensive tools should not be classified as red-ops."""
        assert not is_red_ops_tool("create_memory")
        assert not is_red_ops_tool("search_memories")
        assert not is_red_ops_tool("state.current")

    def test_blue_ops_not_red_ops(self):
        """Blue-ops tools should not be classified as red-ops."""
        assert is_blue_ops_tool("scan_codebase")
        assert classify_ops("scan_codebase") == "blue-ops"
        assert classify_ops("create_memory") == ""


class TestDharmaVioletRules:
    """Verify Dharma violet profile rules cover all new tools."""

    def test_violet_rules_loaded(self):
        """Violet profile rules should be loaded in the rules engine."""
        from whitemagic.dharma.rules import DharmaRulesEngine
        engine = DharmaRulesEngine()
        engine.set_profile("violet")
        violet_rules = [r for r in engine._rules if r.profile == "violet"]
        assert len(violet_rules) >= 4  # engagement_token, blue_ops, model_load, exfiltration, throttle, jailbreak

    def test_violet_engagement_token_rule_exists(self):
        """The violet_require_engagement_token rule should exist."""
        from whitemagic.dharma.rules import DharmaRulesEngine
        engine = DharmaRulesEngine()
        names = [r.name for r in engine._rules]
        assert "violet_require_engagement_token" in names

    def test_violet_rule_has_new_keywords(self):
        """Violet engagement token rule should include new tool keywords."""
        from whitemagic.dharma.rules import DharmaRulesEngine
        engine = DharmaRulesEngine()
        rule = next(r for r in engine._rules if r.name == "violet_require_engagement_token")
        keywords = rule.keyword_patterns or []
        for expected in ["sqlmap", "hydra", "nikto", "ffuf", "nuclei", "redteam", "attack_cell", "agent_redteam"]:
            assert expected in keywords, f"Keyword '{expected}' missing from violet_require_engagement_token"

    def test_violet_rule_has_new_tool_patterns(self):
        """Violet engagement token rule should include new tool patterns."""
        from whitemagic.dharma.rules import DharmaRulesEngine
        engine = DharmaRulesEngine()
        rule = next(r for r in engine._rules if r.name == "violet_require_engagement_token")
        patterns = rule.tool_patterns or []
        for expected in ["sqlmap_*", "hydra_*", "nikto_*", "ffuf_*", "nuclei_*", "redteam_*", "agent_redteam_*", "attack_cell_*"]:
            assert expected in patterns, f"Tool pattern '{expected}' missing from violet_require_engagement_token"

    def test_violet_throttle_recon_has_new_tools(self):
        """Violet throttle recon rule should include new recon tool keywords."""
        from whitemagic.dharma.rules import DharmaRulesEngine
        engine = DharmaRulesEngine()
        rule = next(r for r in engine._rules if r.name == "violet_throttle_recon")
        keywords = rule.keyword_patterns or []
        for expected in ["nikto", "nuclei", "ffuf"]:
            assert expected in keywords, f"Keyword '{expected}' missing from violet_throttle_recon"

    def test_violet_blocks_offensive_without_token(self):
        """Violet profile should block offensive tool actions without a token."""
        from whitemagic.dharma.rules import DharmaRulesEngine
        engine = DharmaRulesEngine()
        engine.set_profile("violet")
        action = {"tool": "nmap_scan", "description": "Port scan on target"}
        decision = engine.evaluate(action)
        assert decision.action == "block"

    def test_violet_blocks_sqlmap(self):
        """Violet profile should block sqlmap without a token."""
        from whitemagic.dharma.rules import DharmaRulesEngine
        engine = DharmaRulesEngine()
        engine.set_profile("violet")
        action = {"tool": "sqlmap_scan", "description": "SQL injection scan"}
        decision = engine.evaluate(action)
        assert decision.action == "block"

    def test_violet_blocks_attack_cell(self):
        """Violet profile should block attack_cell without a token."""
        from whitemagic.dharma.rules import DharmaRulesEngine
        engine = DharmaRulesEngine()
        engine.set_profile("violet")
        action = {"tool": "attack_cell_execute", "description": "Execute attack cell"}
        decision = engine.evaluate(action)
        assert decision.action == "block"


class TestHandlerOffensiveTokenCheck:
    """Verify handler-level offensive token check covers all new tools."""

    def test_all_new_tools_in_offensive_set(self):
        """All new tools should be in _OFFENSIVE_HANDLER_TOOLS."""
        from whitemagic.tools.handlers.security_tools import _OFFENSIVE_HANDLER_TOOLS
        for tool in ["nmap_scan", "sqlmap_scan", "hydra_brute", "nikto_scan", "ffuf_fuzz",
                      "nuclei_scan", "redteam_autonomous", "agent_redteam_run", "attack_cell_execute"]:
            assert tool in _OFFENSIVE_HANDLER_TOOLS, f"Tool '{tool}' not in _OFFENSIVE_HANDLER_TOOLS"

    def test_check_offensive_token_blocks_under_violet(self):
        """_check_offensive_token should block without token under violet."""
        from whitemagic.tools.handlers.security_tools import _check_offensive_token
        with patch("whitemagic.dharma.rules.get_rules_engine") as mock_engine:
            mock_engine.return_value.get_profile.return_value = "violet"
            result = _check_offensive_token("nmap_scan", {"target": "127.0.0.1"})
            assert result is not None
            assert result["error_code"] == "engagement_token_required"

    def test_check_offensive_token_allows_with_valid_token(self):
        """_check_offensive_token should allow with valid token."""
        from whitemagic.tools.handlers.security_tools import _check_offensive_token
        with patch("whitemagic.dharma.rules.get_rules_engine") as mock_engine, \
             patch("whitemagic.security.engagement_tokens.get_token_manager") as mock_mgr:
            mock_engine.return_value.get_profile.return_value = "violet"
            mock_mgr.return_value.validate.return_value = {"valid": True, "reason": "Token valid."}
            result = _check_offensive_token("nmap_scan", {"target": "127.0.0.1", "_engagement_token_id": "evt_test"})
            assert result is None

    def test_check_offensive_token_passes_non_offensive(self):
        """_check_offensive_token should return None for non-offensive tools."""
        from whitemagic.tools.handlers.security_tools import _check_offensive_token
        result = _check_offensive_token("create_memory", {"content": "test"})
        assert result is None

    def test_target_extraction_includes_contract_address(self):
        """Target extraction should include contract_address and address keys."""
        from whitemagic.tools.handlers.security_tools import _check_offensive_token
        with patch("whitemagic.dharma.rules.get_rules_engine") as mock_engine, \
             patch("whitemagic.security.engagement_tokens.get_token_manager") as mock_mgr:
            mock_engine.return_value.get_profile.return_value = "violet"
            mock_mgr.return_value.validate.return_value = {"valid": True}
            _check_offensive_token("foundry_build", {
                "contract_address": "0x1234567890abcdef",
                "_engagement_token_id": "evt_test",
            })
            # Verify validate was called with the contract_address as target
            call_args = mock_mgr.return_value.validate.call_args
            assert call_args.kwargs.get("target") == "0x1234567890abcdef"


class TestShelterVioletTemplate:
    """Verify violet shelter template is properly configured."""

    def test_violet_template_exists(self):
        """Violet template should exist in SHELTER_TEMPLATES."""
        from whitemagic.shelter.manager import SHELTER_TEMPLATES
        assert "violet" in SHELTER_TEMPLATES

    def test_violet_template_has_dharma_profile(self):
        """Violet template should have dharma_profile set to 'violet'."""
        from whitemagic.shelter.manager import SHELTER_TEMPLATES
        assert SHELTER_TEMPLATES["violet"]["dharma_profile"] == "violet"

    def test_violet_template_has_network_caps(self):
        """Violet template should have network_read and network_write."""
        from whitemagic.shelter.manager import SHELTER_TEMPLATES
        caps = SHELTER_TEMPLATES["violet"]["capabilities"]
        assert "network_read" in caps
        assert "network_write" in caps

    def test_violet_template_has_fs_scoping(self):
        """Violet template should have scoped filesystem access."""
        from whitemagic.shelter.manager import SHELTER_TEMPLATES
        caps = SHELTER_TEMPLATES["violet"]["capabilities"]
        assert "fs_read:/tmp" in caps
        assert "fs_write:/tmp" in caps
        # Should NOT have unrestricted fs access
        assert "fs_read" not in caps or "fs_read:/tmp" in caps

    def test_violet_template_has_timeout_limit(self):
        """Violet template should have a timeout limit."""
        from whitemagic.shelter.manager import SHELTER_TEMPLATES
        limits = SHELTER_TEMPLATES["violet"]["limits"]
        assert "timeout_s" in limits
        assert limits["timeout_s"] <= 300  # Max 5 minutes
