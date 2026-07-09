"""Tests for Slither integration — MCP handlers, dispatch, PRAT, registry."""
import pytest


class TestSlitherHandlers:
    def test_slither_status(self):
        from whitemagic.tools.handlers.security_tools import handle_slither_status
        result = handle_slither_status({})
        assert "available" in result
        assert "path" in result

    def test_slither_scan_no_slither(self, monkeypatch):
        from whitemagic.tools.handlers.security_tools import handle_slither_scan
        monkeypatch.setattr("shutil.which", lambda x: None)
        result = handle_slither_scan({"project_dir": "."})
        assert result["status"] == "error"
        assert "not installed" in result["error"]


class TestSlitherWiring:
    def test_slither_in_dispatch(self):
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE
        assert "slither.scan" in DISPATCH_TABLE
        assert "slither.status" in DISPATCH_TABLE

    def test_slither_in_prat(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA
        assert TOOL_TO_GANA["slither.scan"] == "gana_three_stars"
        assert TOOL_TO_GANA["slither.status"] == "gana_three_stars"

    def test_slither_in_registry(self):
        from whitemagic.tools.registry_defs import collect
        tools = collect()
        sec_names = {t.name for t in tools if t.category.value == "security"}
        assert "slither.scan" in sec_names
        assert "slither.status" in sec_names


class TestSlitherCheckerRegistration:
    def test_slither_checker_registered(self):
        from whitemagic.tools.strata.checkers import get_checkers
        checkers = get_checkers()
        names = [c.__name__ for c in checkers]
        assert "check_slither" in names
