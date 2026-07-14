"""Tests for WhiteMagic framework adapters.

All tests use mocks — no framework dependencies required.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


class TestLangChainAdapter:
    """Test LangChain adapter."""

    def test_memory_init(self):
        from whitemagic.adapters.langchain import WhiteMagicMemory
        memory = WhiteMagicMemory(galaxy="test", user_id="alice", search_limit=5)
        assert memory.galaxy == "test"
        assert memory.user_id == "alice"
        assert memory.search_limit == 5
        assert memory.memory_key == "history"

    def test_memory_save_context(self):
        from whitemagic.adapters.langchain import WhiteMagicMemory
        memory = WhiteMagicMemory(galaxy="test")

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success", "data": {"id": "mem1"}}
            memory.save_context(
                inputs={"input": "Hello"},
                outputs={"output": "Hi there!"},
            )
            assert mock_call.call_count == 2

    def test_memory_load_variables(self):
        from whitemagic.adapters.langchain import WhiteMagicMemory
        memory = WhiteMagicMemory(galaxy="test", search_limit=3)

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {
                "status": "success",
                "data": [
                    {"content": "Memory 1"},
                    {"content": "Memory 2"},
                ],
            }
            result = memory.load_memory_variables({"input": "test query"})
            assert "history" in result
            assert "Memory 1" in result["history"]

    def test_memory_load_empty_query(self):
        from whitemagic.adapters.langchain import WhiteMagicMemory
        memory = WhiteMagicMemory(galaxy="test")

        result = memory.load_memory_variables({})
        assert result == {"history": ""}

    def test_toolkit_get_tools(self):
        from whitemagic.adapters.langchain import WhiteMagicToolkit
        toolkit = WhiteMagicToolkit(galaxy="test")
        tools = toolkit.get_tools()
        assert len(tools) == 4
        assert tools[0].name == "search_memories"

    def test_tool_run(self):
        from whitemagic.adapters.langchain import WhiteMagicTool
        tool = WhiteMagicTool("search_memories", "Search memories")

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success", "data": []}
            result = tool.run(query="test")
            assert isinstance(result, str)
            parsed = json.loads(result)
            assert parsed["status"] == "success"


class TestCrewAIAdapter:
    """Test CrewAI adapter."""

    def test_memory_init(self):
        from whitemagic.adapters.crewai import WhiteMagicCrewMemory
        memory = WhiteMagicCrewMemory(galaxy="test", search_limit=5)
        assert memory.galaxy == "test"
        assert memory.search_limit == 5

    def test_memory_store(self):
        from whitemagic.adapters.crewai import WhiteMagicCrewMemory
        memory = WhiteMagicCrewMemory(galaxy="test")

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success", "data": {"id": "mem123"}}
            mem_id = memory.store("Test content")
            assert mem_id == "mem123"
            assert len(memory._storage) == 1

    def test_memory_search(self):
        from whitemagic.adapters.crewai import WhiteMagicCrewMemory
        memory = WhiteMagicCrewMemory(galaxy="test")

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {
                "status": "success",
                "data": [{"id": "mem1", "content": "Found it"}],
            }
            results = memory.search("test query")
            assert len(results) == 1
            assert results[0]["content"] == "Found it"

    def test_memory_clear(self):
        from whitemagic.adapters.crewai import WhiteMagicCrewMemory
        memory = WhiteMagicCrewMemory(galaxy="test")
        memory._storage.append({"id": "1", "content": "test"})
        memory.clear()
        assert len(memory._storage) == 0

    def test_crew_tools(self):
        from whitemagic.adapters.crewai import WhiteMagicCrewTools
        tools = WhiteMagicCrewTools(galaxy="test")
        assert tools.galaxy == "test"
        assert tools.memory.galaxy == "test"


class TestAutoGenAdapter:
    """Test AutoGen adapter."""

    def test_register_tools(self):
        from whitemagic.adapters.autogen import register_whitemagic_tools

        agent = MagicMock()
        register_whitemagic_tools(agent, galaxy="test")

        assert agent.register_function.called
        assert agent.register_function.call_count == 3

    def test_register_custom_tools(self):
        from whitemagic.adapters.autogen import register_whitemagic_tools

        agent = MagicMock()
        register_whitemagic_tools(agent, galaxy="test", tools=["search_memories"])

        assert agent.register_function.call_count == 1

    def test_mixin_remember(self):
        from whitemagic.adapters.autogen import WhiteMagicAgentMixin

        mixin = WhiteMagicAgentMixin()
        mixin._wm_galaxy = "test"

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success", "data": {"id": "mem1"}}
            result = mixin.remember("Test content")
            assert result == "mem1"

    def test_mixin_recall(self):
        from whitemagic.adapters.autogen import WhiteMagicAgentMixin

        mixin = WhiteMagicAgentMixin()
        mixin._wm_galaxy = "test"

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {
                "status": "success",
                "data": [{"id": "mem1", "content": "test"}],
            }
            results = mixin.recall("query")
            assert len(results) == 1


class TestPydanticAIAdapter:
    """Test PydanticAI adapter."""

    def test_toolset_init(self):
        from whitemagic.adapters.pydantic_ai import WhiteMagicToolset
        toolset = WhiteMagicToolset(galaxy="test")
        assert toolset.galaxy == "test"
        assert "search_memories" in toolset._tool_names

    def test_toolset_search(self):
        from whitemagic.adapters.pydantic_ai import WhiteMagicToolset
        toolset = WhiteMagicToolset(galaxy="test")

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {
                "status": "success",
                "data": [{"id": "mem1", "content": "test"}],
            }
            results = toolset.search_memories("query")
            assert len(results) == 1

    def test_toolset_create(self):
        from whitemagic.adapters.pydantic_ai import WhiteMagicToolset
        toolset = WhiteMagicToolset(galaxy="test")

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success", "data": {"id": "mem123"}}
            mem_id = toolset.create_memory("Test content")
            assert mem_id == "mem123"

    def test_toolset_health(self):
        from whitemagic.adapters.pydantic_ai import WhiteMagicToolset
        toolset = WhiteMagicToolset(galaxy="test")

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success", "healthy": True}
            result = toolset.health()
            assert result["status"] == "success"

    def test_toolset_execute(self):
        from whitemagic.adapters.pydantic_ai import WhiteMagicToolset
        toolset = WhiteMagicToolset(galaxy="test")

        with patch("whitemagic.tools.unified_api.call_tool") as mock_call:
            mock_call.return_value = {"status": "success"}
            result = toolset.execute("health")
            assert result["status"] == "success"


class TestAdapterImports:
    """Test that all adapters can be imported without framework deps."""

    def test_import_langchain(self):
        from whitemagic.adapters.langchain import WhiteMagicMemory, WhiteMagicTool, WhiteMagicToolkit
        assert WhiteMagicMemory is not None
        assert WhiteMagicTool is not None
        assert WhiteMagicToolkit is not None

    def test_import_crewai(self):
        from whitemagic.adapters.crewai import WhiteMagicCrewMemory, WhiteMagicCrewTools
        assert WhiteMagicCrewMemory is not None
        assert WhiteMagicCrewTools is not None

    def test_import_autogen(self):
        from whitemagic.adapters.autogen import register_whitemagic_tools, WhiteMagicAgentMixin
        assert register_whitemagic_tools is not None
        assert WhiteMagicAgentMixin is not None

    def test_import_pydantic_ai(self):
        from whitemagic.adapters.pydantic_ai import WhiteMagicToolset
        assert WhiteMagicToolset is not None

    def test_import_init(self):
        from whitemagic.adapters import _check_optional
        assert callable(_check_optional)
