"""Tests for local model wiring and speculative decoding integration.

Tests cover:
- Router env-var model path resolution
- LlamaCppBackend.complete_with_tokens method
- SpeculativeDecoder accept/reject logic
- InferenceRouter.speculative_route fallback behavior
- Draft/verify handler factory wiring
"""

from unittest.mock import MagicMock, patch


class TestRouterEnvVarModelPaths:
    """Test that the router correctly resolves model paths from env vars."""

    def test_small_backend_uses_wm_model_small(self, tmp_path, monkeypatch):
        """_get_small_backend should use WM_MODEL_SMALL env var."""
        fake_model = tmp_path / "fake.gguf"
        fake_model.write_text("fake")

        monkeypatch.setenv("WM_MODEL_SMALL", str(fake_model))
        monkeypatch.setenv("WM_MODEL_QWEN3_1_7B", "")
        monkeypatch.setenv("WM_MODEL_QWEN25_1_5B", "")
        monkeypatch.setenv("WM_MODEL_LLAMA32_1B", "")

        import whitemagic.inference.router as router_mod
        router_mod._small_backend = None

        with patch("whitemagic.inference.llama_cpp.LlamaCppBackend") as MockBackend:
            mock_instance = MagicMock()
            mock_instance.is_available = True
            MockBackend.return_value = mock_instance

            backend = router_mod._get_small_backend()
            assert backend is not None
            call_args = MockBackend.call_args
            assert call_args.kwargs["model_path"] == str(fake_model)
            assert call_args.kwargs["port"] == 8091

        router_mod._small_backend = None

    def test_large_backend_uses_wm_model_large(self, tmp_path, monkeypatch):
        """_get_large_backend should use WM_MODEL_LARGE env var."""
        fake_model = tmp_path / "large.gguf"
        fake_model.write_text("fake")

        monkeypatch.setenv("WM_MODEL_LARGE", str(fake_model))
        monkeypatch.setenv("WM_MODEL_QWEN3_4B", "")
        monkeypatch.setenv("WM_MODEL_PHI4_MINI", "")
        monkeypatch.setenv("WM_LLAMA_MODEL", "")

        import whitemagic.inference.router as router_mod
        router_mod._large_backend = None

        with patch("whitemagic.inference.llama_cpp.LlamaCppBackend") as MockBackend:
            mock_instance = MagicMock()
            mock_instance.is_available = True
            MockBackend.return_value = mock_instance

            backend = router_mod._get_large_backend()
            assert backend is not None
            call_args = MockBackend.call_args
            assert call_args.kwargs["model_path"] == str(fake_model)
            assert call_args.kwargs["port"] == 8090

        router_mod._large_backend = None

    def test_draft_backend_uses_wm_model_draft(self, tmp_path, monkeypatch):
        """_get_draft_backend should use WM_MODEL_DRAFT env var."""
        fake_model = tmp_path / "draft.gguf"
        fake_model.write_text("fake")

        monkeypatch.setenv("WM_MODEL_DRAFT", str(fake_model))
        monkeypatch.setenv("WM_MODEL_SMOLLM2_360M", "")

        import whitemagic.inference.router as router_mod
        router_mod._draft_backend = None

        with patch("whitemagic.inference.llama_cpp.LlamaCppBackend") as MockBackend:
            mock_instance = MagicMock()
            mock_instance.is_available = True
            MockBackend.return_value = mock_instance

            backend = router_mod._get_draft_backend()
            assert backend is not None
            call_args = MockBackend.call_args
            assert call_args.kwargs["model_path"] == str(fake_model)
            assert call_args.kwargs["port"] == 8092

        router_mod._draft_backend = None

    def test_small_backend_returns_none_when_no_model(self, monkeypatch):
        """_get_small_backend should return None when no model is found."""
        monkeypatch.delenv("WM_MODEL_SMALL", raising=False)
        monkeypatch.delenv("WM_MODEL_QWEN3_1_7B", raising=False)
        monkeypatch.delenv("WM_MODEL_QWEN25_1_5B", raising=False)
        monkeypatch.delenv("WM_MODEL_LLAMA32_1B", raising=False)

        import whitemagic.inference.router as router_mod
        router_mod._small_backend = None

        # Mock ModelDiscovery to find no models
        with patch("whitemagic.interfaces.chat.ModelDiscovery.best_model", return_value=None):
            backend = router_mod._get_small_backend()
            assert backend is None

    def test_llama_cpp_handler_uses_small_backend_fallback(self, monkeypatch):
        """_llama_cpp_handler should use _get_small_backend, not old WM_LLAMA_MODEL."""
        import whitemagic.inference.router as router_mod

        with patch("whitemagic.inference.llama_cpp.get_dual_model_manager", return_value=None):
            with patch.object(router_mod, "_get_small_backend", return_value=None) as mock_get:
                result = router_mod._llama_cpp_handler("test prompt")
                assert result["confidence"] == 0.0
                assert "error" in result["metadata"]
                mock_get.assert_called_once()


class TestLlamaCppCompleteWithTokens:
    """Test the complete_with_tokens method on LlamaCppBackend."""

    def test_returns_text_and_tokens(self):
        """complete_with_tokens should return dict with text, tokens, latency_ms."""
        from whitemagic.inference.llama_cpp import LlamaCppBackend

        backend = LlamaCppBackend.__new__(LlamaCppBackend)
        backend._base_url = "http://localhost:8080"
        backend._available = True
        backend._config = MagicMock()
        backend._config.temperature = 0.7
        backend._config.top_p = 0.9
        backend._config.repeat_penalty = 1.1

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": "Hello world",
            "tokens": [1, 2, 3],
        }

        with patch("requests.post", return_value=mock_response):
            result = backend.complete_with_tokens("test", max_tokens=5)
            assert result["text"] == "Hello world"
            assert result["tokens"] == [1, 2, 3]
            assert result["latency_ms"] > 0

    def test_falls_back_to_tokenize_when_no_tokens(self):
        """When response lacks tokens, should use tokenize endpoint."""
        from whitemagic.inference.llama_cpp import LlamaCppBackend

        backend = LlamaCppBackend.__new__(LlamaCppBackend)
        backend._base_url = "http://localhost:8080"
        backend._available = True
        backend._config = MagicMock()
        backend._config.temperature = 0.7
        backend._config.top_p = 0.9
        backend._config.repeat_penalty = 1.1

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": "Hello",
            "tokens": [],
        }

        with patch("requests.post", return_value=mock_response):
            with patch.object(backend, "tokenize", return_value=[10, 20]) as mock_tok:
                result = backend.complete_with_tokens("test", max_tokens=5)
                assert result["text"] == "Hello"
                assert result["tokens"] == [10, 20]
                mock_tok.assert_called_once_with("Hello")

    def test_unavailable_backend_returns_empty(self):
        """Should return empty result when backend is not available."""
        from whitemagic.inference.llama_cpp import LlamaCppBackend

        backend = LlamaCppBackend.__new__(LlamaCppBackend)
        backend._available = False
        backend._base_url = "http://localhost:8080"

        result = backend.complete_with_tokens("test")
        assert result["text"] == ""
        assert result["tokens"] == []
        assert result["latency_ms"] == 0.0


class TestSpeculativeDecoderAcceptReject:
    """Test the token-level accept/reject logic."""

    def test_all_tokens_accepted(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        decoder = SpeculativeDecoder()
        draft = [1, 2, 3, 4]
        verify = [1, 2, 3, 4]
        accepted, rejected = decoder._accept_reject(draft, verify)
        assert accepted == [1, 2, 3, 4]
        assert rejected == []

    def test_first_mismatch_takes_verify_token(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        decoder = SpeculativeDecoder()
        draft = [1, 2, 3, 4]
        verify = [1, 2, 9, 5]
        accepted, rejected = decoder._accept_reject(draft, verify)
        assert accepted == [1, 2, 9]
        assert rejected == [4]

    def test_all_mismatch_first_token(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        decoder = SpeculativeDecoder()
        draft = [1, 2, 3]
        verify = [9, 8, 7]
        accepted, rejected = decoder._accept_reject(draft, verify)
        assert accepted == [9]
        assert rejected == [2, 3]

    def test_verify_shorter_than_draft(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        decoder = SpeculativeDecoder()
        draft = [1, 2, 3, 4, 5]
        verify = [1, 2, 3]
        accepted, rejected = decoder._accept_reject(draft, verify)
        assert accepted == [1, 2, 3]
        assert rejected == [4, 5]

    def test_draft_shorter_than_verify(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        decoder = SpeculativeDecoder()
        draft = [1, 2]
        verify = [1, 2, 3, 4]
        accepted, rejected = decoder._accept_reject(draft, verify)
        assert accepted == [1, 2]
        assert rejected == []

    def test_empty_tokens(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        decoder = SpeculativeDecoder()
        accepted, rejected = decoder._accept_reject([], [])
        assert accepted == []
        assert rejected == []


class TestSpeculativeDecoderGenerate:
    """Test the full generate pipeline with mock handlers."""

    def test_generate_with_mock_handlers(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        def mock_draft(prompt, **kwargs):
            return {
                "text": "ABCD",
                "tokens": [1, 2, 3, 4],
                "latency_ms": 10.0,
                "verify_per_token_ms": 50.0,
            }

        def mock_verify(prompt, **kwargs):
            return {
                "text": "ABCD",
                "tokens": [1, 2, 3, 4],
                "latency_ms": 30.0,
            }

        decoder = SpeculativeDecoder(
            draft_handler=mock_draft,
            verify_handler=mock_verify,
            draft_tokens=4,
        )

        result = decoder.generate("test prompt", max_tokens=8)
        assert result.accepted_tokens == 8
        assert result.rejected_tokens == 0
        assert result.acceptance_rate == 1.0

    def test_generate_with_partial_acceptance(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        call_count = [0]

        def mock_draft(prompt, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"text": "AB", "tokens": [1, 2, 3, 4], "latency_ms": 10.0,
                        "verify_per_token_ms": 50.0}
            return {"text": "CD", "tokens": [5, 6], "latency_ms": 5.0,
                    "verify_per_token_ms": 50.0}

        def mock_verify(prompt, **kwargs):
            if call_count[0] == 1:
                return {"text": "ABX", "tokens": [1, 2, 9], "latency_ms": 30.0}
            return {"text": "CD", "tokens": [5, 6], "latency_ms": 20.0}

        decoder = SpeculativeDecoder(
            draft_handler=mock_draft,
            verify_handler=mock_verify,
            draft_tokens=4,
        )

        result = decoder.generate("test", max_tokens=8)
        assert result.accepted_tokens > 0
        assert result.draft_tokens_generated > 0

    def test_generate_falls_back_when_draft_fails(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        def mock_draft(prompt, **kwargs):
            return {"text": "", "tokens": [], "latency_ms": 0.0}

        def mock_verify(prompt, **kwargs):
            return {"text": "OK", "tokens": [1], "latency_ms": 10.0}

        decoder = SpeculativeDecoder(
            draft_handler=mock_draft,
            verify_handler=mock_verify,
        )

        result = decoder.generate("test", max_tokens=4)
        assert result.text == ""
        assert result.accepted_tokens == 0

    def test_adaptive_k_decreases_on_low_acceptance(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        def mock_draft(prompt, **kwargs):
            return {"text": "AB", "tokens": [1, 2, 3, 4], "latency_ms": 5.0,
                    "verify_per_token_ms": 50.0}

        def mock_verify(prompt, **kwargs):
            # All tokens mismatch — only 1 accepted (verify correction)
            return {"text": "XYZW", "tokens": [9, 9, 9, 9], "latency_ms": 30.0}

        decoder = SpeculativeDecoder(
            draft_handler=mock_draft,
            verify_handler=mock_verify,
            draft_tokens=4,
            min_accept_rate=0.5,  # 1/4 = 0.25 < 0.5, so K should decrease
        )

        decoder.generate("test", max_tokens=4)
        assert decoder._adaptive_k < 4

    def test_adaptive_k_increases_on_high_acceptance(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        def mock_draft(prompt, **kwargs):
            return {"text": "AB", "tokens": [1, 2, 3, 4], "latency_ms": 5.0,
                    "verify_per_token_ms": 50.0}

        def mock_verify(prompt, **kwargs):
            return {"text": "ABCD", "tokens": [1, 2, 3, 4], "latency_ms": 30.0}

        decoder = SpeculativeDecoder(
            draft_handler=mock_draft,
            verify_handler=mock_verify,
            draft_tokens=2,
            min_accept_rate=0.2,
        )

        decoder.generate("test", max_tokens=4)
        assert decoder._adaptive_k > 2


class TestInferenceRouterSpeculativeRoute:
    """Test InferenceRouter.speculative_route method."""

    def test_speculative_route_falls_back_when_disabled(self):
        """When use_speculative=False, should fall back to normal routing."""
        from whitemagic.inference.complexity import InferenceTier
        from whitemagic.inference.router import InferenceRouter

        router = InferenceRouter(use_speculative=False)
        router.register_handler(
            InferenceTier.EDGE_RULES,
            lambda prompt, **kw: {"answer": "edge", "confidence": 0.9, "metadata": {}},
        )

        response = router.speculative_route("test", max_tokens=4, force_tier=InferenceTier.EDGE_RULES)
        assert response.answer == "edge"

    def test_speculative_route_falls_back_when_unavailable(self):
        """When speculative decoding is unavailable, should fall back."""
        from whitemagic.inference.complexity import InferenceTier
        from whitemagic.inference.router import InferenceRouter

        router = InferenceRouter(use_speculative=True)
        router.register_handler(
            InferenceTier.EDGE_RULES,
            lambda prompt, **kw: {"answer": "edge", "confidence": 0.9, "metadata": {}},
        )

        mock_decoder = MagicMock()
        mock_decoder.is_available = False

        with patch("whitemagic.inference.router.get_speculative_router", return_value=mock_decoder):
            response = router.speculative_route("test", max_tokens=4, force_tier=InferenceTier.EDGE_RULES)
            assert response.answer == "edge"

    def test_speculative_route_returns_spec_result(self):
        """When speculative decoding works, should return spec result."""
        from whitemagic.inference.router import InferenceRouter

        router = InferenceRouter(use_speculative=True)

        mock_spec_result = MagicMock()
        mock_spec_result.text = "spec answer"
        mock_spec_result.accepted_tokens = 10
        mock_spec_result.rejected_tokens = 2
        mock_spec_result.acceptance_rate = 0.83
        mock_spec_result.speedup_vs_sequential = 1.5
        mock_spec_result.total_latency_ms = 42.0
        mock_spec_result.metadata = {"adaptive_k": 4, "rounds": 3}

        mock_decoder = MagicMock()
        mock_decoder.is_available = True
        mock_decoder.generate.return_value = mock_spec_result

        with patch("whitemagic.inference.router.get_speculative_router", return_value=mock_decoder):
            response = router.speculative_route("test prompt", max_tokens=16)
            assert response.answer == "spec answer"
            assert response.metadata["speculative"] is True
            assert response.metadata["accepted_tokens"] == 10
            assert response.metadata["acceptance_rate"] == 0.83
            assert response.metadata["speedup"] == 1.5

    def test_speculative_route_falls_back_on_exception(self):
        """When speculative decoding raises, should fall back to normal routing."""
        from whitemagic.inference.complexity import InferenceTier
        from whitemagic.inference.router import InferenceRouter

        router = InferenceRouter(use_speculative=True)
        router.register_handler(
            InferenceTier.EDGE_RULES,
            lambda prompt, **kw: {"answer": "fallback", "confidence": 0.9, "metadata": {}},
        )

        with patch("whitemagic.inference.router.get_speculative_router", side_effect=RuntimeError("boom")):
            response = router.speculative_route("test", max_tokens=4, force_tier=InferenceTier.EDGE_RULES)
            assert response.answer == "fallback"


class TestSpeculativeRouterWiring:
    """Test the get_speculative_router factory function."""

    def test_get_speculative_router_registers_handlers(self):
        """get_speculative_router should register draft/verify handlers."""
        import whitemagic.inference.router as router_mod

        # Reset the singleton
        import whitemagic.inference.speculative_decoder as spec_mod
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder
        spec_mod._decoder = None

        # Mock the handler functions to avoid needing real backends
        with patch.object(router_mod, "_draft_handler", MagicMock()):
            with patch.object(router_mod, "_verify_handler", MagicMock()):
                decoder = router_mod.get_speculative_router()
                assert isinstance(decoder, SpeculativeDecoder)
                assert decoder.is_available

        # Cleanup
        spec_mod._decoder = None

    def test_get_speculative_router_reuses_existing(self):
        """get_speculative_router should not re-register if already available."""
        import whitemagic.inference.router as router_mod
        from whitemagic.inference.speculative_decoder import get_speculative_decoder

        decoder = get_speculative_decoder()
        # Register mock handlers
        decoder.register_draft(lambda prompt, **kw: {"text": "", "tokens": [], "latency_ms": 0})
        decoder.register_verify(lambda prompt, **kw: {"text": "", "tokens": [], "latency_ms": 0})

        # Should return the same decoder without re-registering
        result = router_mod.get_speculative_router()
        assert result is decoder
