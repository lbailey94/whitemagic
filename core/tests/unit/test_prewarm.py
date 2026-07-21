"""Tests for MCP serving-stack prewarm (P6.4 follow-up)."""

import threading

from whitemagic.mcp import prewarm


class TestPrewarmEnabled:
    def test_enabled_by_default(self, monkeypatch):
        monkeypatch.delenv("WM_PREWARM", raising=False)
        assert prewarm.prewarm_enabled() is True

    def test_disabled_with_zero(self, monkeypatch):
        monkeypatch.setenv("WM_PREWARM", "0")
        assert prewarm.prewarm_enabled() is False

    def test_disabled_with_false(self, monkeypatch):
        monkeypatch.setenv("WM_PREWARM", "false")
        assert prewarm.prewarm_enabled() is False


class TestPrewarmServingStack:
    def test_calls_all_stages(self, monkeypatch):
        calls = []

        class _FakeEngine:
            def available(self):
                return True

            def encode_batch(self, texts):
                calls.append("encode")

        monkeypatch.setattr(
            "whitemagic.core.memory.embeddings.get_embedding_engine",
            lambda: _FakeEngine(),
        )
        monkeypatch.setattr(
            "whitemagic.security.semantic_defense.combined_semantic_check",
            lambda text: calls.append("semantic_defense") or {},
        )
        monkeypatch.setattr(
            "whitemagic.core.memory.cross_encoder_reranker.rerank_cross_encoder",
            lambda q, docs, top_k=None: calls.append("rerank") or docs,
        )
        monkeypatch.setattr(
            "whitemagic.tools.unified_api._dispatch_tool",
            lambda name, **kw: calls.append("dispatch") or {"status": "success"},
        )

        timings = prewarm.prewarm_serving_stack()

        assert calls == ["encode", "semantic_defense", "rerank", "dispatch"]
        assert set(timings) == {
            "embedding_engine_s",
            "semantic_defense_s",
            "cross_encoder_s",
            "dispatch_chain_s",
        }

    def test_stage_failure_does_not_propagate(self, monkeypatch):
        monkeypatch.setattr(
            "whitemagic.core.memory.embeddings.get_embedding_engine",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        calls = []
        monkeypatch.setattr(
            "whitemagic.security.semantic_defense.combined_semantic_check",
            lambda text: calls.append("semantic_defense") or {},
        )
        monkeypatch.setattr(
            "whitemagic.core.memory.cross_encoder_reranker.rerank_cross_encoder",
            lambda q, docs, top_k=None: calls.append("rerank") or docs,
        )
        monkeypatch.setattr(
            "whitemagic.tools.unified_api._dispatch_tool",
            lambda name, **kw: calls.append("dispatch") or {"status": "success"},
        )

        timings = prewarm.prewarm_serving_stack()

        # Later stages still ran despite the first stage raising
        assert calls == ["semantic_defense", "rerank", "dispatch"]
        assert "embedding_engine_s" in timings


class TestStartPrewarmThread:
    def test_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.setenv("WM_PREWARM", "0")
        assert prewarm.start_prewarm_thread() is None

    def test_spawns_daemon_thread(self, monkeypatch):
        monkeypatch.setenv("WM_PREWARM", "1")
        monkeypatch.setattr(prewarm, "prewarm_serving_stack", lambda: {})
        thread = prewarm.start_prewarm_thread()
        assert thread is not None
        assert isinstance(thread, threading.Thread)
        assert thread.daemon is True
        thread.join(timeout=5)
        assert not thread.is_alive()

    def test_thread_runs_prewarm(self, monkeypatch):
        monkeypatch.setenv("WM_PREWARM", "1")
        ran = []
        monkeypatch.setattr(
            prewarm, "prewarm_serving_stack", lambda: ran.append(True) or {}
        )
        thread = prewarm.start_prewarm_thread()
        thread.join(timeout=5)
        assert ran == [True]
