"""Tests for speculative decoding pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from whitemagic.inference.speculative_decoder import (
    SpeculativeDecoder,
    SpeculativeResult,
    SpeculativeStats,
    get_speculative_decoder,
)


class TestSpeculativeStats:
    def test_default(self):
        stats = SpeculativeStats()
        assert stats.total_calls == 0
        assert stats.acceptance_rate == 0.0
        assert stats.avg_speedup == 0.0

    def test_acceptance_rate(self):
        stats = SpeculativeStats()
        stats.total_accepted = 7
        stats.total_draft_generated = 10
        assert stats.acceptance_rate == 0.7

    def test_to_dict(self):
        stats = SpeculativeStats()
        stats.total_calls = 5
        stats.total_accepted = 10
        stats.total_draft_generated = 20
        d = stats.to_dict()
        assert d["total_calls"] == 5
        assert d["acceptance_rate"] == 0.5


class TestSpeculativeResult:
    def test_creation(self):
        result = SpeculativeResult(
            text="hello",
            accepted_tokens=3,
            rejected_tokens=1,
            draft_tokens_generated=4,
            draft_latency_ms=10.0,
            verify_latency_ms=50.0,
            total_latency_ms=60.0,
        )
        assert result.text == "hello"
        assert result.accepted_tokens == 3
        assert result.metadata == {}


class TestSpeculativeDecoder:
    def test_not_available_without_handlers(self):
        decoder = SpeculativeDecoder()
        assert not decoder.is_available

    def test_available_with_handlers(self):
        decoder = SpeculativeDecoder(
            draft_handler=MagicMock(),
            verify_handler=MagicMock(),
        )
        assert decoder.is_available

    def test_register_handlers(self):
        decoder = SpeculativeDecoder()
        assert not decoder.is_available
        decoder.register_draft(MagicMock())
        decoder.register_verify(MagicMock())
        assert decoder.is_available

    def test_generate_without_handlers(self):
        decoder = SpeculativeDecoder()
        result = decoder.generate("test", max_tokens=10)
        assert result.text == ""
        assert result.accepted_tokens == 0
        assert "error" in result.metadata

    def test_generate_all_accepted(self):
        """Draft and verify produce same tokens — all accepted."""
        draft = MagicMock(return_value={
            "tokens": [100, 200, 300, 400],
            "text": "abcd",
            "latency_ms": 10.0,
        })
        verify = MagicMock(return_value={
            "tokens": [100, 200, 300, 400],
            "text": "abcd",
            "latency_ms": 50.0,
        })
        decoder = SpeculativeDecoder(
            draft_handler=draft,
            verify_handler=verify,
            draft_tokens=4,
        )
        result = decoder.generate("prompt", max_tokens=4)
        assert result.accepted_tokens == 4
        assert result.rejected_tokens == 0
        assert result.acceptance_rate == 1.0

    def test_generate_partial_accept(self):
        """Draft and verify diverge at token 2 — first 2 accepted, rest rejected."""
        draft = MagicMock(return_value={
            "tokens": [100, 200, 300, 400],
            "text": "abcd",
        })
        verify = MagicMock(return_value={
            "tokens": [100, 200, 999, 400],
            "text": "abxd",
        })
        decoder = SpeculativeDecoder(
            draft_handler=draft,
            verify_handler=verify,
            draft_tokens=4,
        )
        result = decoder.generate("prompt", max_tokens=4)
        # 2 accepted from draft, 1 correction from verify = 3 total
        assert result.accepted_tokens >= 2
        assert result.rejected_tokens >= 1

    def test_generate_all_rejected(self):
        """Draft and verify produce completely different tokens."""
        draft = MagicMock(return_value={
            "tokens": [100, 200, 300],
            "text": "abc",
        })
        verify = MagicMock(return_value={
            "tokens": [999, 888, 777],
            "text": "xyz",
        })
        decoder = SpeculativeDecoder(
            draft_handler=draft,
            verify_handler=verify,
            draft_tokens=3,
        )
        result = decoder.generate("prompt", max_tokens=3)
        assert result.rejected_tokens > 0
        # Verify model's first token should be used as correction
        assert result.accepted_tokens >= 1

    def test_adaptive_k_decrease(self):
        """K should decrease when acceptance rate is low."""
        draft = MagicMock(return_value={
            "tokens": [100, 200, 300, 400],
            "text": "abcd",
        })
        verify = MagicMock(return_value={
            "tokens": [999, 888, 777, 666],
            "text": "wxyz",
        })
        decoder = SpeculativeDecoder(
            draft_handler=draft,
            verify_handler=verify,
            draft_tokens=4,
            min_accept_rate=0.5,
        )
        decoder.generate("prompt", max_tokens=4)
        # All rejected → K should decrease
        assert decoder._adaptive_k < 4

    def test_adaptive_k_increase(self):
        """K should increase when acceptance rate is high."""
        draft = MagicMock(return_value={
            "tokens": [100, 200, 300, 400],
            "text": "abcd",
        })
        verify = MagicMock(return_value={
            "tokens": [100, 200, 300, 400],
            "text": "abcd",
        })
        decoder = SpeculativeDecoder(
            draft_handler=draft,
            verify_handler=verify,
            draft_tokens=4,
            min_accept_rate=0.2,
        )
        decoder.generate("prompt", max_tokens=4)
        # All accepted → K should increase
        assert decoder._adaptive_k > 4

    def test_stats_tracking(self):
        draft = MagicMock(return_value={
            "tokens": [100, 200],
            "text": "ab",
        })
        verify = MagicMock(return_value={
            "tokens": [100, 200],
            "text": "ab",
        })
        decoder = SpeculativeDecoder(
            draft_handler=draft,
            verify_handler=verify,
            draft_tokens=2,
        )
        decoder.generate("prompt", max_tokens=2)
        stats = decoder.get_stats()
        assert stats["total_calls"] == 1
        assert stats["total_accepted"] == 2
        assert stats["total_draft_generated"] == 2

    def test_reset_stats(self):
        decoder = SpeculativeDecoder(
            draft_handler=MagicMock(),
            verify_handler=MagicMock(),
        )
        decoder._stats.total_calls = 10
        decoder.reset_stats()
        assert decoder._stats.total_calls == 0

    def test_accept_reject_matching(self):
        decoder = SpeculativeDecoder(
            draft_handler=MagicMock(),
            verify_handler=MagicMock(),
        )
        accepted, rejected = decoder._accept_reject(
            [1, 2, 3, 4, 5],
            [1, 2, 9, 4, 5],
        )
        # Tokens 1,2 match; at index 2 draft=3 vs verify=9 mismatch
        # so verify's token 9 is accepted as correction, rest rejected
        assert accepted == [1, 2, 9]
        assert rejected == [4, 5]

    def test_accept_reject_all_match(self):
        decoder = SpeculativeDecoder(
            draft_handler=MagicMock(),
            verify_handler=MagicMock(),
        )
        accepted, rejected = decoder._accept_reject(
            [1, 2, 3],
            [1, 2, 3],
        )
        assert accepted == [1, 2, 3]
        assert rejected == []

    def test_accept_reject_draft_longer(self):
        decoder = SpeculativeDecoder(
            draft_handler=MagicMock(),
            verify_handler=MagicMock(),
        )
        accepted, rejected = decoder._accept_reject(
            [1, 2, 3, 4, 5],
            [1, 2, 3],
        )
        assert accepted == [1, 2, 3]
        assert rejected == [4, 5]

    def test_multiple_rounds(self):
        """Test that multiple rounds accumulate tokens."""
        call_count = [0]

        def draft_fn(prompt, max_tokens, temperature=0.7):
            call_count[0] += 1
            return {
                "tokens": [100, 200],
                "text": "ab",
            }

        def verify_fn(prompt, max_tokens, temperature=0.7, draft_tokens=None):
            return {
                "tokens": [100, 200],
                "text": "ab",
            }

        decoder = SpeculativeDecoder(
            draft_handler=draft_fn,
            verify_handler=verify_fn,
            draft_tokens=2,
        )
        result = decoder.generate("prompt", max_tokens=6)
        # Should run 3 rounds (2 tokens per round, 6 total)
        assert result.accepted_tokens == 6
        assert call_count[0] == 3


class TestSingleton:
    def test_get_decoder(self):
        d1 = get_speculative_decoder()
        d2 = get_speculative_decoder()
        assert d1 is d2


class TestSpeculativeRouterWiring:
    """Test the speculative decoding router wiring (mock-based, no subprocesses)."""

    def test_draft_handler_returns_tokens(self):
        """Draft handler should return tokens and text for speculative decoding."""
        from whitemagic.inference.router import _draft_handler

        with patch("whitemagic.inference.router._get_draft_backend") as mock_get:
            mock_backend = MagicMock()
            mock_backend.is_available = True
            mock_backend.complete_with_tokens.return_value = {
                "text": "hello",
                "tokens": [1, 2, 3, 4],
                "latency_ms": 10.0,
            }
            mock_get.return_value = mock_backend

            result = _draft_handler("test prompt", max_tokens=4, temperature=0.3)
            assert result["tokens"] == [1, 2, 3, 4]
            assert result["text"] == "hello"
            assert "verify_per_token_ms" in result

    def test_draft_handler_no_backend(self):
        """Draft handler returns empty when no backend available."""
        from whitemagic.inference.router import _draft_handler

        with patch("whitemagic.inference.router._get_draft_backend", return_value=None):
            result = _draft_handler("test", max_tokens=4)
            assert result["tokens"] == []
            assert result["text"] == ""

    def test_verify_handler_returns_tokens(self):
        """Verify handler should return tokens for token-level comparison."""
        from whitemagic.inference.router import _verify_handler

        with patch("whitemagic.inference.router._get_large_backend") as mock_large:
            mock_backend = MagicMock()
            mock_backend.is_available = True
            mock_backend.complete_with_tokens.return_value = {
                "text": "hello",
                "tokens": [1, 2, 3, 4],
                "latency_ms": 50.0,
            }
            mock_large.return_value = mock_backend

            result = _verify_handler("test prompt", max_tokens=4, temperature=0.5)
            assert result["tokens"] == [1, 2, 3, 4]
            assert result["text"] == "hello"

    def test_verify_handler_falls_back_to_small(self):
        """Verify handler falls back to small backend when large unavailable."""
        from whitemagic.inference.router import _verify_handler

        with (
            patch("whitemagic.inference.router._get_large_backend", return_value=None),
            patch("whitemagic.inference.router._get_small_backend") as mock_small,
        ):
            mock_backend = MagicMock()
            mock_backend.is_available = True
            mock_backend.complete_with_tokens.return_value = {
                "text": "fallback",
                "tokens": [10, 20],
                "latency_ms": 30.0,
            }
            mock_small.return_value = mock_backend

            result = _verify_handler("test", max_tokens=4)
            assert result["tokens"] == [10, 20]

    def test_get_speculative_router_registers_handlers(self):
        """get_speculative_router should register draft+verify handlers."""
        # Reset singleton
        import whitemagic.inference.speculative_decoder as sd
        from whitemagic.inference.router import get_speculative_router

        sd._decoder = None

        decoder = get_speculative_router()
        assert decoder.is_available
        assert decoder._draft is not None
        assert decoder._verify is not None


class TestLlamaCppChatReasoningFallback:
    """Test that LlamaCppBackend.chat() handles Qwen3 reasoning_content fallback."""

    def test_chat_extracts_content(self):
        """Normal response: content field is populated."""
        from whitemagic.inference.llama_cpp import LlamaCppBackend, LlamaCppConfig

        backend = LlamaCppBackend(
            model_path="/fake/model.gguf",
            port=9999,
            auto_start=False,
            config=LlamaCppConfig(),
        )
        backend._available = True

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "The answer is 4.",
                        "reasoning_content": "",
                    }
                }
            ]
        }
        with patch("requests.post", return_value=mock_response):
            result = backend.chat(
                messages=[{"role": "user", "content": "What is 2+2?"}],
                max_tokens=100,
            )
        assert result == "The answer is 4."

    def test_chat_falls_back_to_reasoning_content(self):
        """Qwen3 reasoning model: content empty, reasoning_content has the output."""
        from whitemagic.inference.llama_cpp import LlamaCppBackend, LlamaCppConfig

        backend = LlamaCppBackend(
            model_path="/fake/model.gguf",
            port=9999,
            auto_start=False,
            config=LlamaCppConfig(),
        )
        backend._available = True

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "reasoning_content": "Okay, 2+2=4. The answer is 4.",
                    }
                }
            ]
        }
        with patch("requests.post", return_value=mock_response):
            result = backend.chat(
                messages=[{"role": "user", "content": "What is 2+2?"}],
                max_tokens=10,
            )
        assert "4" in result
        assert "Okay" in result

    def test_chat_returns_empty_when_both_empty(self):
        """Both content and reasoning_content empty — return empty string."""
        from whitemagic.inference.llama_cpp import LlamaCppBackend, LlamaCppConfig

        backend = LlamaCppBackend(
            model_path="/fake/model.gguf",
            port=9999,
            auto_start=False,
            config=LlamaCppConfig(),
        )
        backend._available = True

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "reasoning_content": "",
                    }
                }
            ]
        }
        with patch("requests.post", return_value=mock_response):
            result = backend.chat(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
        assert result == ""


class TestCompleteWithTokens:
    """Test complete_with_tokens used by speculative decoding."""

    def test_returns_tokens_and_text(self):
        from whitemagic.inference.llama_cpp import LlamaCppBackend, LlamaCppConfig

        backend = LlamaCppBackend(
            model_path="/fake/model.gguf",
            port=9999,
            auto_start=False,
            config=LlamaCppConfig(),
        )
        backend._available = True

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": "hello world",
            "tokens": [100, 200, 300],
        }
        with patch("requests.post", return_value=mock_response):
            result = backend.complete_with_tokens("test", max_tokens=3)
        assert result["tokens"] == [100, 200, 300]
        assert result["text"] == "hello world"
        assert "latency_ms" in result

    def test_tokenizes_text_when_tokens_missing(self):
        """When server doesn't return tokens, use tokenize endpoint."""
        from whitemagic.inference.llama_cpp import LlamaCppBackend, LlamaCppConfig

        backend = LlamaCppBackend(
            model_path="/fake/model.gguf",
            port=9999,
            auto_start=False,
            config=LlamaCppConfig(),
        )
        backend._available = True

        completion_response = MagicMock()
        completion_response.json.return_value = {
            "content": "hello",
            "tokens": [],
        }
        tokenize_response = MagicMock()
        tokenize_response.json.return_value = {"tokens": [42, 99]}

        with patch("requests.post", side_effect=[completion_response, tokenize_response]):
            result = backend.complete_with_tokens("test", max_tokens=1)
        assert result["tokens"] == [42, 99]
        assert result["text"] == "hello"
