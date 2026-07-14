"""Tests for speculative decoding wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from whitemagic.inference.speculative_wiring import (
    _bitmamba_draft_handler,
    _bitnetcpp_verify_handler,
    _llamacpp_verify_handler,
    is_speculative_ready,
    wire_speculative_decoder,
)


class TestBitmambaDraftHandler:
    def test_draft_with_unavailable_model(self):
        """Draft handler returns empty when BitMamba is not available."""
        with patch("whitemagic.inference.bitmamba_autonomic.get_autonomic") as mock:
            autonomic = MagicMock()
            autonomic.is_available = False
            mock.return_value = autonomic
            result = _bitmamba_draft_handler("test", max_tokens=5)
        assert result["text"] == ""
        assert result["tokens"] == []

    def test_draft_with_available_model(self):
        """Draft handler returns tokens when BitMamba is available."""
        with patch("whitemagic.inference.bitmamba_autonomic.get_autonomic") as mock:
            autonomic = MagicMock()
            autonomic.is_available = True
            autonomic._run_inference.return_value = {
                "token_ids": [100, 200, 300],
                "latency_ms": 50.0,
            }
            mock.return_value = autonomic
            result = _bitmamba_draft_handler("test prompt", max_tokens=3)
        assert result["tokens"] == [100, 200, 300]
        assert result["latency_ms"] == 50.0


class TestLlamaCppVerifyHandler:
    def test_verify_with_unavailable_backend(self):
        """Verify handler returns empty when llama.cpp is not available."""
        with patch("whitemagic.inference.llama_cpp.get_llama_cpp_backend") as mock:
            backend = MagicMock()
            backend.is_available = False
            mock.return_value = backend
            result = _llamacpp_verify_handler("test", max_tokens=5)
        assert result["text"] == ""
        assert result["tokens"] == []

    def test_verify_with_available_backend(self):
        """Verify handler returns text when llama.cpp is available."""
        with patch("whitemagic.inference.llama_cpp.get_llama_cpp_backend") as mock:
            backend = MagicMock()
            backend.is_available = True
            backend.complete.return_value = "Hello world"
            mock.return_value = backend
            result = _llamacpp_verify_handler("test", max_tokens=5)
        assert result["text"] == "Hello world"
        assert result["latency_ms"] > 0


class TestWireSpeculativeDecoder:
    def test_wire_with_both_available(self):
        """Wire decoder when both backends are available."""
        # Reset singleton
        import whitemagic.inference.speculative_decoder as sd_mod
        sd_mod._decoder = None

        with patch("whitemagic.inference.bitmamba_autonomic.get_autonomic") as mock_auto, \
             patch("whitemagic.inference.llama_cpp.get_llama_cpp_backend") as mock_llama:

            autonomic = MagicMock()
            autonomic.is_available = True
            mock_auto.return_value = autonomic

            backend = MagicMock()
            backend.is_available = True
            mock_llama.return_value = backend

            decoder = wire_speculative_decoder()

        assert decoder.is_available
        assert decoder._draft is not None
        assert decoder._verify is not None

    def test_wire_with_only_draft(self):
        """Wire decoder when only draft is available."""
        import whitemagic.inference.speculative_decoder as sd_mod
        sd_mod._decoder = None

        with patch("whitemagic.inference.bitmamba_autonomic.get_autonomic") as mock_auto, \
             patch("whitemagic.inference.llama_cpp.get_llama_cpp_backend") as mock_llama:

            autonomic = MagicMock()
            autonomic.is_available = True
            mock_auto.return_value = autonomic

            backend = MagicMock()
            backend.is_available = False
            mock_llama.return_value = backend

            decoder = wire_speculative_decoder()

        assert not decoder.is_available
        assert decoder._draft is not None
        assert decoder._verify is None

    def test_wire_with_neither(self):
        """Wire decoder when neither backend is available."""
        import whitemagic.inference.speculative_decoder as sd_mod
        sd_mod._decoder = None

        with patch("whitemagic.inference.bitmamba_autonomic.get_autonomic") as mock_auto, \
             patch("whitemagic.inference.llama_cpp.get_llama_cpp_backend") as mock_llama:

            autonomic = MagicMock()
            autonomic.is_available = False
            mock_auto.return_value = autonomic

            backend = MagicMock()
            backend.is_available = False
            mock_llama.return_value = backend

            decoder = wire_speculative_decoder()

        assert not decoder.is_available
        assert decoder._draft is None
        assert decoder._verify is None

    def test_is_speculative_ready(self):
        """Test the readiness check."""
        import whitemagic.inference.speculative_decoder as sd_mod
        sd_mod._decoder = None

        with patch("whitemagic.inference.bitmamba_autonomic.get_autonomic") as mock_auto, \
             patch("whitemagic.inference.llama_cpp.get_llama_cpp_backend") as mock_llama:

            autonomic = MagicMock()
            autonomic.is_available = True
            mock_auto.return_value = autonomic

            backend = MagicMock()
            backend.is_available = True
            mock_llama.return_value = backend

            wire_speculative_decoder()
            assert is_speculative_ready()


class TestBitnetCppVerifyHandler:
    def test_verify_with_missing_model(self):
        """bitnet.cpp verify handler returns empty when model file is missing."""
        import os
        with patch.dict(os.environ, {"WM_SPEC_VERIFY_MODEL": "bitnet-2b4t"}):
            with patch("os.path.isfile", return_value=False):
                result = _bitnetcpp_verify_handler("test", max_tokens=5)
        assert result["text"] == ""
        assert result["tokens"] == []

    def test_verify_with_missing_cli(self):
        """bitnet.cpp verify handler returns empty when CLI binary is missing."""
        import os
        with patch.dict(os.environ, {"WM_SPEC_VERIFY_MODEL": "bitnet-2b4t"}):
            with patch("os.path.isfile", side_effect=lambda p: not p.endswith("llama-cli")):
                result = _bitnetcpp_verify_handler("test", max_tokens=5)
        assert result["text"] == ""


class TestMultiModelWiring:
    def test_wire_bitnet_verify(self):
        """Wire decoder with bitnet.cpp as verify model."""
        import whitemagic.inference.speculative_decoder as sd_mod
        sd_mod._decoder = None

        with patch("whitemagic.inference.bitmamba_autonomic.get_autonomic") as mock_auto, \
             patch("os.path.isfile", return_value=True):

            autonomic = MagicMock()
            autonomic.is_available = True
            mock_auto.return_value = autonomic

            decoder = wire_speculative_decoder(verify_model="bitnet")

        assert decoder._draft is not None
        assert decoder._verify is not None

    def test_wire_falcon3_verify(self):
        """Wire decoder with Falcon3-1B as verify model."""
        import whitemagic.inference.speculative_decoder as sd_mod
        sd_mod._decoder = None

        with patch("whitemagic.inference.bitmamba_autonomic.get_autonomic") as mock_auto, \
             patch("os.path.isfile", return_value=True):

            autonomic = MagicMock()
            autonomic.is_available = True
            mock_auto.return_value = autonomic

            decoder = wire_speculative_decoder(verify_model="falcon3")

        assert decoder._draft is not None
        assert decoder._verify is not None
