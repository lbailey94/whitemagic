"""
Archived v11.3 tests — obsolete on v22.0.0.

These tests validated APIs that have been completely rewritten:
- TestDharmaYAMLDirectory: Dharma rules loading from YAML directories
- TestMCPToolRoutingV113: v11.3 MCP routing aliases and tool names

Preserved for historical reference. Not expected to pass on v22.
"""
import json
import time

import pytest

# =========================================================================
# 6. Dharma Rules from YAML Directory (v11 API — removed in v22)
# =========================================================================

@pytest.mark.skip("v11.3 Dharma rules loading changed — archived")
class TestDharmaYAMLDirectory:

    def test_rules_dir_loads_extra_rules(self, tmp_path):
        """YAML files dropped into rules.d/ are merged with built-in defaults."""
        from whitemagic.dharma.rules import DharmaRulesEngine

        rules_dir = tmp_path / "rules.d"
        rules_dir.mkdir()
        (rules_dir / "custom.yaml").write_text(
            "rules:\n"
            "  - name: no_foo\n"
            "    description: Block foo tool\n"
            "    action: block\n"
            "    severity: 0.9\n"
            "    explain: foo is forbidden\n"
            "    tool_patterns: ['foo_*']\n"
        )
        engine = DharmaRulesEngine(rules_dir=rules_dir)
        rule_names = [r["name"] for r in engine.get_rules()]
        assert "no_foo" in rule_names
        # Built-in defaults should still be present
        assert "destructive_ops" in rule_names

    def test_last_write_wins_override(self, tmp_path):
        """A user rule with the same name as a built-in replaces it."""
        from whitemagic.dharma.rules import DharmaAction, DharmaRulesEngine

        rules_dir = tmp_path / "rules.d"
        rules_dir.mkdir()
        (rules_dir / "override.yaml").write_text(
            "rules:\n"
            "  - name: destructive_ops\n"
            "    description: Overridden\n"
            "    action: block\n"
            "    severity: 1.0\n"
            "    explain: User override\n"
            "    keyword_patterns: ['delete']\n"
        )
        engine = DharmaRulesEngine(rules_dir=rules_dir)
        # Use Python evaluator directly — this tests YAML override, not Haskell
        d = engine._python_evaluate({"tool": "x", "description": "delete stuff"}, "default")
        assert d.action == DharmaAction.BLOCK
        assert "User override" in d.explain

    def test_single_file_plus_dir_merged(self, tmp_path):
        """Both rules_path and rules_dir can be used together."""
        from whitemagic.dharma.rules import DharmaRulesEngine

        single_file = tmp_path / "main.yaml"
        single_file.write_text(
            "rules:\n"
            "  - name: single_rule\n"
            "    description: From single file\n"
            "    action: tag\n"
            "    severity: 0.2\n"
            "    explain: Single file rule\n"
            "    keyword_patterns: ['single']\n"
        )
        rules_dir = tmp_path / "rules.d"
        rules_dir.mkdir()
        (rules_dir / "dir_rule.yaml").write_text(
            "rules:\n"
            "  - name: dir_rule\n"
            "    description: From directory\n"
            "    action: warn\n"
            "    severity: 0.5\n"
            "    explain: Directory rule\n"
            "    keyword_patterns: ['directory']\n"
        )
        engine = DharmaRulesEngine(rules_path=single_file, rules_dir=rules_dir)
        names = [r["name"] for r in engine.get_rules()]
        assert "single_rule" in names
        assert "dir_rule" in names
        assert "destructive_ops" in names  # built-in still present

    def test_check_reload_detects_change(self, tmp_path):
        """check_reload() returns True when a file changes."""
        from whitemagic.dharma.rules import DharmaRulesEngine

        rules_dir = tmp_path / "rules.d"
        rules_dir.mkdir()
        f = rules_dir / "live.yaml"
        f.write_text("rules:\n  - name: v1\n    action: log\n    severity: 0.1\n    explain: v1\n")

        engine = DharmaRulesEngine(rules_dir=rules_dir)
        assert "v1" in [r["name"] for r in engine.get_rules()]

        # No change yet
        assert engine.check_reload() is False

        # Modify file
        import time
        time.sleep(0.05)
        f.write_text("rules:\n  - name: v2\n    action: warn\n    severity: 0.5\n    explain: v2\n")

        assert engine.check_reload() is True
        assert "v2" in [r["name"] for r in engine.get_rules()]

    def test_yml_extension_supported(self, tmp_path):
        """Both .yaml and .yml extensions are loaded."""
        from whitemagic.dharma.rules import DharmaRulesEngine

        rules_dir = tmp_path / "rules.d"
        rules_dir.mkdir()
        (rules_dir / "a.yml").write_text(
            "rules:\n  - name: yml_rule\n    action: log\n    severity: 0.1\n    explain: yml\n"
        )
        engine = DharmaRulesEngine(rules_dir=rules_dir)
        assert "yml_rule" in [r["name"] for r in engine.get_rules()]


# =========================================================================
# 8. MCP Tool Routing (v11 API — removed in v22)
# =========================================================================

@pytest.mark.skip("v11.3 MCP routing aliases changed — archived")
class TestMCPToolRoutingV113:

    def test_lifecycle_stats_tool(self, tool_caller):
        result = tool_caller.ok("memory.lifecycle_stats")
        assert "lifecycle" in result["details"]

    def test_homeostasis_status_tool(self, tool_caller):
        result = tool_caller.ok("homeostasis.status")
        assert "homeostasis" in result["details"]

    def test_homeostasis_check_tool(self, tool_caller):
        result = tool_caller.ok("homeostasis.check")
        assert "actions_taken" in result["details"]

    def test_maturity_assess_tool(self, tool_caller):
        result = tool_caller.ok("maturity.assess")
        maturity = result["details"].get("maturity", {})
        assert "current_stage" in maturity

    def test_consolidation_stats_tool(self, tool_caller):
        result = tool_caller.ok("memory.consolidation_stats")
        assert "consolidation" in result["details"]

    def test_tool_graph_summary(self, tool_caller):
        result = tool_caller.ok("tool.graph")
        assert "graph" in result["details"]

    def test_tool_graph_for_specific_tool(self, tool_caller):
        result = tool_caller.ok("tool.graph", tool="vote.create")
        assert "next_steps" in result["details"]
        assert "prerequisites" in result["details"]

    def test_tool_graph_full(self, tool_caller):
        result = tool_caller.ok("tool.graph_full")
        assert "edges" in result["details"]

    def test_dharma_reload(self, tool_caller):
        result = tool_caller.ok("dharma.reload")
        assert "rules_loaded" in result["details"]

    def test_underscore_aliases_work(self, tool_caller):
        """Verify underscore-style names resolve to dot-style."""
        result = tool_caller.ok("homeostasis_status")
        assert result["tool"] == "homeostasis.status"
