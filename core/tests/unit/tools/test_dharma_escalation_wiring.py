"""Tests for Dharma 4-tier escalation MCP tool wiring."""


class TestDharmaEscalationWiring:
    def test_dispatch_entries(self):
        from whitemagic.tools.dispatch_table import DISPATCH_TABLE
        assert "dharma.escalate" in DISPATCH_TABLE
        assert "dharma.review_queue" in DISPATCH_TABLE
        assert "dharma.resolve_review" in DISPATCH_TABLE

    def test_prat_mappings(self):
        from whitemagic.tools.prat_mappings import TOOL_TO_GANA
        assert TOOL_TO_GANA["dharma.escalate"] == "gana_straddling_legs"
        assert TOOL_TO_GANA["dharma.review_queue"] == "gana_straddling_legs"
        assert TOOL_TO_GANA["dharma.resolve_review"] == "gana_straddling_legs"

    def test_registry_definitions(self):
        from whitemagic.tools.registry_defs import collect
        tools = collect()
        names = {t.name for t in tools}
        assert "dharma.escalate" in names
        assert "dharma.review_queue" in names
        assert "dharma.resolve_review" in names


class TestDharmaEscalationHandlers:
    def test_escalate_clear_safe(self):
        from whitemagic.tools.handlers.dharma import handle_dharma_escalate
        result = handle_dharma_escalate(action={"tool": "search", "description": "search memories for context"})
        assert result["status"] == "success"
        assert "action" in result
        assert "tiers" in result

    def test_escalate_clear_block(self):
        from whitemagic.tools.handlers.dharma import handle_dharma_escalate
        result = handle_dharma_escalate(action={"tool": "delete", "description": "delete all memories without consent"})
        assert result["status"] == "success"
        assert result["action"] in ("allow", "warn", "block", "pending")

    def test_escalate_non_dict_action(self):
        from whitemagic.tools.handlers.dharma import handle_dharma_escalate
        result = handle_dharma_escalate(action="some risky action")
        assert result["status"] == "success"

    def test_review_queue_empty(self):
        from whitemagic.tools.handlers.dharma import handle_dharma_review_queue
        result = handle_dharma_review_queue()
        assert result["status"] == "success"
        assert "pending_count" in result
        assert "reviews" in result

    def test_resolve_review_missing_id(self):
        from whitemagic.tools.handlers.dharma import handle_dharma_resolve_review
        result = handle_dharma_resolve_review()
        assert result["status"] == "error"

    def test_resolve_review_not_found(self):
        from whitemagic.tools.handlers.dharma import handle_dharma_resolve_review
        result = handle_dharma_resolve_review(review_id="HR-FAKE-9999", decision="allow", score=0.9)
        assert result["status"] == "error"
