# ruff: noqa: BLE001
"""Tests for the agent-friendly tool descriptions module (Phase 7)."""

import pytest


class TestAgentDescriptions:
    """Test the agent_descriptions module."""

    def test_get_known_tool(self):
        from whitemagic.tools.agent_descriptions import get_agent_description

        desc = get_agent_description("search_memories")
        assert desc is not None
        assert "memory" in desc.lower() or "recall" in desc.lower()

    def test_get_unknown_tool(self):
        from whitemagic.tools.agent_descriptions import get_agent_description

        desc = get_agent_description("nonexistent_tool_xyz")
        assert desc is None

    def test_get_all(self):
        from whitemagic.tools.agent_descriptions import get_all_agent_descriptions

        all_descs = get_all_agent_descriptions()
        assert isinstance(all_descs, dict)
        assert len(all_descs) >= 50  # We have many tools

    def test_wm_meta_tool(self):
        from whitemagic.tools.agent_descriptions import get_agent_description

        desc = get_agent_description("wm")
        assert desc is not None
        assert "490" in desc or "route" in desc.lower()

    def test_gana_descriptions(self):
        from whitemagic.tools.agent_descriptions import get_agent_description

        for gana in ["gana_horn", "gana_neck", "gana_root", "gana_heart", "gana_void"]:
            desc = get_agent_description(gana)
            assert desc is not None, f"Missing description for {gana}"
            assert len(desc) > 20

    def test_session_tools(self):
        from whitemagic.tools.agent_descriptions import get_agent_description

        for tool in ["session.record", "session.recall", "session.search"]:
            desc = get_agent_description(tool)
            assert desc is not None, f"Missing description for {tool}"

    def test_cognitive_tools(self):
        from whitemagic.tools.agent_descriptions import get_agent_description

        for tool in ["rerank", "working_memory.attend", "consolidation.run", "neuro.compute"]:
            desc = get_agent_description(tool)
            assert desc is not None, f"Missing description for {tool}"

    def test_descriptions_are_natural_language(self):
        """Descriptions should be natural language, not technical jargon."""
        from whitemagic.tools.agent_descriptions import get_all_agent_descriptions

        for name, desc in get_all_agent_descriptions().items():
            # Should not start with technical terms like "holographic" or "5D"
            assert not desc.lower().startswith("holographic")
            assert not desc.lower().startswith("5d")
            # Should be a sentence
            assert desc.endswith(".") or desc.endswith("?")

    def test_get_tools_by_intent(self):
        from whitemagic.tools.agent_descriptions import get_tools_by_intent

        results = get_tools_by_intent("remember something important")
        assert isinstance(results, list)
        assert len(results) > 0
        # Should include memory-related tools
        names = [r[0] for r in results]
        assert any("memory" in n or "create" in n for n in names)

    def test_get_tools_by_intent_search(self):
        from whitemagic.tools.agent_descriptions import get_tools_by_intent

        results = get_tools_by_intent("find search memories")
        assert len(results) > 0
        names = [r[0] for r in results]
        assert any("search" in n for n in names)

    def test_build_agent_tool_catalog(self):
        from whitemagic.tools.agent_descriptions import build_agent_tool_catalog

        catalog = build_agent_tool_catalog(max_tools=50)
        assert isinstance(catalog, str)
        assert "## Your Tools" in catalog
        assert "###" in catalog  # Has categories
        assert "**" in catalog  # Has bold tool names

    def test_build_agent_tool_catalog_categories(self):
        from whitemagic.tools.agent_descriptions import build_agent_tool_catalog

        catalog = build_agent_tool_catalog(max_tools=100)
        # Should have multiple categories
        category_count = catalog.count("### ")
        assert category_count >= 5  # At least 5 categories

    def test_all_descriptions_have_use_context(self):
        """Each description should explain when to use the tool."""
        from whitemagic.tools.agent_descriptions import get_all_agent_descriptions

        action_words = [
            "use", "when", "for", "find", "get", "check", "save", "search",
            "list", "create", "start", "stop", "run", "record", "cast",
            "submit", "export", "import", "delete", "update", "transfer",
            "merge", "backup", "restore", "navigate", "read", "write",
            "activate", "boost", "propose", "compute", "apply", "replay",
            "tag", "spread", "set", "detect", "propagate", "mark", "attend",
            "rerank", "broadcast", "publish", "discover", "negotiate",
            "complete", "issue", "validate", "vote", "analyze", "plan",
            "assess", "convene", "query", "suggest", "reload", "flush",
            "decay", "reset", "synthesize", "excavate", "scan", "fix",
            "invoke", "decompose", "route", "resolve", "register",
            "deregister", "send", "emit", "advance", "summarize",
            "replay", "backfill", "consolidate", "continuity", "remove",
            "synchronize", "disconnect", "track", "maintain", "organize",
            "distribute", "mine", "handle", "manage", "monitor",
            "calibrate", "anchor", "verify", "render", "maintain",
        ]
        for name, desc in get_all_agent_descriptions().items():
            desc_lower = desc.lower()
            assert any(word in desc_lower for word in action_words), \
                f"Tool {name} description lacks usage context: {desc}"
