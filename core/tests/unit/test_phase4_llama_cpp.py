# ruff: noqa: BLE001
"""Tests for Phase 4 — llama.cpp backend, dual-model, binary manager, router update."""

from __future__ import annotations

import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix="wm_test_")
os.environ["WM_STATE_ROOT"] = _tmp
os.environ["WM_SILENT_INIT"] = "1"


class TestLlamaCppBackend:
    """Test the llama.cpp backend."""

    def test_backend_init_defaults(self):
        from whitemagic.inference.llama_cpp import LlamaCppBackend
        backend = LlamaCppBackend()
        assert backend._host == "localhost"
        assert backend._port == 8080
        assert backend.is_available is False  # no server running

    def test_backend_init_custom(self):
        from whitemagic.inference.llama_cpp import LlamaCppBackend
        backend = LlamaCppBackend(host="127.0.0.1", port=9999)
        assert backend._host == "127.0.0.1"
        assert backend._port == 9999

    def test_backend_complete_not_available(self):
        from whitemagic.inference.llama_cpp import LlamaCppBackend
        backend = LlamaCppBackend()
        result = backend.complete("test")
        assert "Error" in result

    def test_backend_chat_not_available(self):
        from whitemagic.inference.llama_cpp import LlamaCppBackend
        backend = LlamaCppBackend()
        result = backend.chat([{"role": "user", "content": "hi"}])
        assert "Error" in result

    def test_backend_embed_not_available(self):
        from whitemagic.inference.llama_cpp import LlamaCppBackend
        backend = LlamaCppBackend()
        result = backend.embed("test")
        assert result == []

    def test_backend_get_status(self):
        from whitemagic.inference.llama_cpp import LlamaCppBackend
        backend = LlamaCppBackend()
        status = backend.get_status()
        assert status["available"] is False

    def test_backend_singleton(self):
        from whitemagic.inference.llama_cpp import get_llama_cpp_backend
        b1 = get_llama_cpp_backend()
        b2 = get_llama_cpp_backend()
        assert b1 is b2


class TestLlamaCppConfig:
    """Test config serialization."""

    def test_config_defaults(self):
        from whitemagic.inference.llama_cpp import LlamaCppConfig
        config = LlamaCppConfig()
        assert config.host == "localhost"
        assert config.port == 8080
        assert config.n_ctx == 4096

    def test_config_to_args(self):
        from whitemagic.inference.llama_cpp import LlamaCppConfig
        config = LlamaCppConfig(n_threads=4, n_gpu_layers=2)
        args = config.to_args()
        assert "--host" in args
        assert "--threads" in args
        assert "--n-gpu-layers" in args
        assert "--flash-attn" in args


class TestBinaryManager:
    """Test the binary manager."""

    def test_find_binary_returns_none_if_not_installed(self):
        from whitemagic.inference.llama_cpp import BinaryManager
        # Should either find it or return None — just test it doesn't crash
        result = BinaryManager.find_binary()
        assert result is None or isinstance(result, str)

    def test_get_version_handles_missing_binary(self):
        from whitemagic.inference.llama_cpp import BinaryManager
        version = BinaryManager.get_version("/nonexistent/llama-server")
        assert version == "unknown"


class TestDualModelManager:
    """Test the dual-model manager."""

    def test_init(self):
        from whitemagic.inference.llama_cpp import DualModelManager
        dmm = DualModelManager(
            background_model="/models/bg.gguf",
            foreground_model="/models/fg.gguf",
        )
        assert dmm.background._model_path == "/models/bg.gguf"
        assert dmm.foreground._model_path == "/models/fg.gguf"

    def test_route_inference_no_models(self):
        from whitemagic.inference.llama_cpp import DualModelManager
        dmm = DualModelManager()
        result = dmm.route_inference("test")
        assert "Error" in result

    def test_stop_all(self):
        from whitemagic.inference.llama_cpp import DualModelManager
        dmm = DualModelManager()
        dmm.stop_all()  # should not crash


class TestRouterUpdate:
    """Test that the inference router includes the new LOCAL_LLAMA_CPP tier."""

    def test_tier_exists(self):
        from whitemagic.inference.complexity import InferenceTier
        assert hasattr(InferenceTier, "LOCAL_LLAMA_CPP")
        assert InferenceTier.LOCAL_LLAMA_CPP == 1
        assert InferenceTier.LOCAL_SMALL == 2
        assert InferenceTier.LOCAL_LARGE == 3
        assert InferenceTier.CLOUD == 4

    def test_router_has_llama_cpp_handler_slot(self):
        from whitemagic.inference.router import InferenceRouter
        router = InferenceRouter()
        assert router._llama_cpp_handler is None  # not registered yet

    def test_router_register_llama_cpp_handler(self):
        from whitemagic.inference.router import InferenceRouter
        from whitemagic.inference.complexity import InferenceTier
        router = InferenceRouter()
        def custom_handler(prompt, **kwargs):
            return {"answer": "test", "confidence": 1.0, "metadata": {}}
        router.register_handler(InferenceTier.LOCAL_LLAMA_CPP, custom_handler)
        assert router._llama_cpp_handler is not None

    def test_router_get_llama_cpp_handler(self):
        from whitemagic.inference.router import InferenceRouter
        from whitemagic.inference.complexity import InferenceTier
        router = InferenceRouter()
        def custom_handler(prompt, **kwargs):
            return {"answer": "test", "confidence": 1.0, "metadata": {}}
        router.register_handler(InferenceTier.LOCAL_LLAMA_CPP, custom_handler)
        handler = router._get_handler(InferenceTier.LOCAL_LLAMA_CPP)
        assert handler is not None
        result = handler("test")
        assert result["answer"] == "test"
