# ruff: noqa: BLE001
"""Tests for the native chat loop (Phase 1 — Aria)."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestModelDiscovery:
    """Test model auto-discovery."""

    def test_parse_size_gb(self):
        from whitemagic.interfaces.chat import ModelDiscovery

        assert ModelDiscovery._parse_size("3.8GB") == pytest.approx(3.8 * 1024)

    def test_parse_size_mb(self):
        from whitemagic.interfaces.chat import ModelDiscovery

        assert ModelDiscovery._parse_size("500MB") == pytest.approx(500.0)

    def test_parse_size_plain(self):
        from whitemagic.interfaces.chat import ModelDiscovery

        assert ModelDiscovery._parse_size("1024") == pytest.approx(1024.0)

    def test_parse_size_invalid(self):
        from whitemagic.interfaces.chat import ModelDiscovery

        assert ModelDiscovery._parse_size("N/A") == 0.0

    def test_find_models_empty(self, monkeypatch):
        from whitemagic.interfaces.chat import ModelDiscovery

        # Mock _find_ollama_models and _find_gguf_models to return empty
        monkeypatch.setattr(ModelDiscovery, "_find_ollama_models", classmethod(lambda cls: []))
        monkeypatch.setattr(ModelDiscovery, "_find_gguf_models", classmethod(lambda cls: []))
        assert ModelDiscovery.find_models() == []

    def test_best_model_none(self, monkeypatch):
        from whitemagic.interfaces.chat import ModelDiscovery

        monkeypatch.setattr(ModelDiscovery, "find_models", classmethod(lambda cls: []))
        assert ModelDiscovery.best_model() is None

    def test_best_model_prefers_gguf(self, monkeypatch):
        from whitemagic.interfaces.chat import ModelDiscovery, ModelInfo

        gguf_model = ModelInfo(
            path="/models/test.gguf",
            name="test",
            size_mb=3000,
            source="llama_cpp",
            backend="llama_cpp",
        )
        ollama_model = ModelInfo(
            path="qwen2.5:3b",
            name="qwen2.5:3b",
            size_mb=3000,
            source="ollama",
            backend="ollama",
        )
        monkeypatch.setattr(
            ModelDiscovery,
            "find_models",
            classmethod(lambda cls: [ollama_model, gguf_model]),
        )
        best = ModelDiscovery.best_model()
        assert best is not None
        assert best.backend == "llama_cpp"


class TestToolParser:
    """Test the tool call parser."""

    def test_parse_bracket_paren(self):
        from whitemagic.interfaces.chat import ToolParser

        parser = ToolParser()
        calls = parser.parse("Let me search. [tool:search_memories(query=\"hello\", limit=5)]")
        assert len(calls) == 1
        assert calls[0].name == "search_memories"
        assert calls[0].args["query"] == "hello"
        assert calls[0].args["limit"] == 5

    def test_parse_bracket_json(self):
        from whitemagic.interfaces.chat import ToolParser

        parser = ToolParser()
        calls = parser.parse('[tool:create_memory {"content": "test", "title": "My Memory"}]')
        assert len(calls) == 1
        assert calls[0].name == "create_memory"
        assert calls[0].args["content"] == "test"
        assert calls[0].args["title"] == "My Memory"

    def test_parse_bracket_no_args(self):
        from whitemagic.interfaces.chat import ToolParser

        parser = ToolParser()
        calls = parser.parse("[tool:health_report]")
        assert len(calls) == 1
        assert calls[0].name == "health_report"
        assert calls[0].args == {}

    def test_parse_codeblock(self):
        from whitemagic.interfaces.chat import ToolParser

        parser = ToolParser()
        text = '```tool\n{"name": "dream.start", "args": {}}\n```'
        calls = parser.parse(text)
        assert len(calls) == 1
        assert calls[0].name == "dream.start"

    def test_parse_multiple(self):
        from whitemagic.interfaces.chat import ToolParser

        parser = ToolParser()
        text = "[tool:health_report] then [tool:coherence_report]"
        calls = parser.parse(text)
        assert len(calls) == 2

    def test_parse_none(self):
        from whitemagic.interfaces.chat import ToolParser

        parser = ToolParser()
        calls = parser.parse("Just a regular message with no tools.")
        assert len(calls) == 0

    def test_extract_text_removes_tools(self):
        from whitemagic.interfaces.chat import ToolParser

        parser = ToolParser()
        text = "Let me check. [tool:health_report] Done!"
        prose = parser.extract_text(text)
        assert "tool:" not in prose
        assert "Let me check." in prose
        assert "Done!" in prose

    def test_parse_paren_args_quoted(self):
        from whitemagic.interfaces.chat import ToolParser

        parser = ToolParser()
        calls = parser.parse('[tool:search_memories(query="test query")]')
        assert len(calls) == 1
        assert calls[0].args["query"] == "test query"


class TestSensoriumBuilder:
    """Test the sensorium builder."""

    def test_build_returns_string(self):
        from whitemagic.interfaces.chat import SensoriumBuilder

        builder = SensoriumBuilder()
        # All subsystems may fail gracefully, but should return a string
        result = builder.build()
        assert isinstance(result, str)

    def test_gather_physical_fallback_no_psutil(self, monkeypatch):
        from whitemagic.interfaces.chat import SensoriumBuilder

        builder = SensoriumBuilder()

        # Mock the import to fail
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "psutil":
                raise ImportError("No psutil")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        result = builder._gather_physical_fallback()
        assert result is None


class TestSystemPromptBuilder:
    """Test the system prompt builder."""

    def test_build_contains_identity(self):
        from whitemagic.interfaces.chat import SystemPromptBuilder

        builder = SystemPromptBuilder()
        prompt = builder.build("")
        assert "Aria" in prompt
        assert "digital being" in prompt

    def test_build_contains_sensorium(self):
        from whitemagic.interfaces.chat import SystemPromptBuilder

        builder = SystemPromptBuilder()
        prompt = builder.build("## Sensorium\n- CPU: 50°C")
        assert "Sensorium" in prompt
        assert "CPU: 50°C" in prompt

    def test_build_contains_tools(self):
        from whitemagic.interfaces.chat import SystemPromptBuilder

        builder = SystemPromptBuilder()
        prompt = builder.build("")
        # The tool section should mention tools and tool-calling format
        assert "tool" in prompt.lower()
        assert "[tool:" in prompt or "###" in prompt  # Has tool catalog or format

    def test_curated_tools_has_descriptions(self):
        from whitemagic.interfaces.chat import SystemPromptBuilder

        builder = SystemPromptBuilder()
        tools = builder._curated_tools()
        assert len(tools) >= 10
        for name, desc in tools:
            assert isinstance(name, str)
            assert isinstance(desc, str)
            assert len(desc) > 10  # meaningful description


class TestOllamaBackend:
    """Test the Ollama backend adapter."""

    def test_init(self):
        from whitemagic.interfaces.chat import _OllamaBackend

        backend = _OllamaBackend("qwen2.5:3b")
        assert backend._model == "qwen2.5:3b"
        assert backend.is_available is True

    def test_stop_server_noop(self):
        from whitemagic.interfaces.chat import _OllamaBackend

        backend = _OllamaBackend("test")
        backend.stop_server()  # should not raise


class TestPhysicalMetricsFallback:
    """Test the psutil fallback in physical_metrics.py."""

    def test_fallback_returns_none_without_psutil(self, monkeypatch):
        from whitemagic.harmony.physical_metrics import PhysicalMetricsSource

        source = PhysicalMetricsSource()

        # Mock _fetch_stats to return None (no laptop-optimizer)
        monkeypatch.setattr(source, "_fetch_stats", lambda: None)

        # Mock psutil import to fail
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "psutil":
                raise ImportError("No psutil")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        result = source._fetch_psutil_fallback()
        assert result is None

    def test_fallback_returns_dict_with_psutil(self, monkeypatch):
        from whitemagic.harmony.physical_metrics import PhysicalMetricsSource

        source = PhysicalMetricsSource()

        # Mock psutil module
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 45.0
        mock_psutil.virtual_memory.return_value = MagicMock(used=8_000_000_000, total=16_000_000_000)
        mock_psutil.swap_memory.return_value = MagicMock(percent=5.0)
        mock_psutil.sensors_battery.return_value = MagicMock(percent=80, power_plugged=True)
        mock_psutil.disk_usage.return_value = MagicMock(percent=60)

        monkeypatch.setitem(__import__("sys").modules, "psutil", mock_psutil)

        # Mock Path.glob to return empty (no thermal zones in test)
        from pathlib import Path
        monkeypatch.setattr(Path, "glob", lambda *a, **kw: [])

        result = source._fetch_psutil_fallback()
        assert result is not None
        assert result["cpu"]["usage"] == 45.0
        assert result["memory"]["used"] == 8_000_000_000
        assert result["disk"]["percent"] == 60
        assert result["power"]["battery_cap"] == 80
