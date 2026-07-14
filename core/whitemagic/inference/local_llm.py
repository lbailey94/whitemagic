# ruff: noqa: BLE001
"""
Local LLM Bridge
================
Provides an interface to local Large Language Models (LLMs) for inference
without cloud API costs.

Primary backend: llama.cpp (via llama-server HTTP API)
Delegates to LlamaCppBackend which manages the llama-server subprocess
and exposes OpenAI-compatible endpoints.

Usage:
    from whitemagic.inference.local_llm import LocalLLM
    llm = LocalLLM(model="/models/qwen3-4b.gguf")
    response = llm.complete("Why is the sky blue?")
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class LocalLLM:
    """Interface for local LLM inference via llama.cpp."""

    def __init__(
        self, base_url: str = "http://localhost:8080", model: str | None = None
    ):
        self.base_url = base_url.rstrip("/")
        self._requested_model = model
        self.model = model or os.environ.get("WM_LLM_MODEL", "")
        self._available = False
        self._backend: Any = None
        self._check_availability()

    def _check_availability(self):
        """Check if llama-server is running and auto-select model if needed."""
        try:
            from whitemagic.inference.llama_cpp import BinaryManager, LlamaCppBackend

            # Try to get or create a backend
            binary = BinaryManager.find_binary()
            if not binary and not os.environ.get("WM_LLAMA_SERVER"):
                logger.debug("llama-server binary not found")
                self._available = False
                return

            # Parse host/port from base_url
            from urllib.parse import urlparse
            parsed = urlparse(self.base_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 8080

            self._backend = LlamaCppBackend(
                model_path=self.model or None,
                host=host,
                port=port,
                binary_path=binary,
            )
            self._available = self._backend.is_available
            if self._available:
                self.model = self._backend._model_path or self.model
                logger.info("LocalLLM connected to llama-server at %s:%s", host, port)
        except Exception as e:
            logger.debug("LocalLLM availability check failed: %s", e)
            self._available = False

    @property
    def is_available(self) -> bool:
        """Check whether the backend is available."""
        if self._backend:
            return self._backend.is_available
        return self._available

    def complete(
        self,
        prompt: str,
        stop: list[str] | None = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        grammar: str | None = None,
    ) -> str:
        """Generate a completion. Optionally grammar-constrained (GBNF)."""
        if not self.is_available:
            return "Error: Local LLM (llama.cpp) not available. Start llama-server."
        return self._backend.complete(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
            grammar=grammar,
        )

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
        """Chat completion."""
        if not self.is_available:
            return "Error: Local LLM (llama.cpp) not available."
        return self._backend.chat(messages, temperature=temperature)

    def classify(self, text: str, categories: list[str]) -> str:
        """Classify text into one of the provided categories."""
        prompt = (
            f"Classify the following text into exactly one of these categories: {', '.join(categories)}.\n"
            f'Text: "{text[:500]}"\n'
            f"Category:"
        )
        response = self.complete(prompt, stop=["\n"], max_tokens=10, temperature=0.0)
        cleaned = response.strip().lower()

        # Simple fuzzy match
        for cat in categories:
            if cat.lower() in cleaned:
                return cat
        return "unknown"

    def complete_background(
        self,
        prompt: str,
        max_tokens: int = 64,
        temperature: float = 0.3,
    ) -> str:
        """Generate a completion using the background (small) model.

        When DualModelManager is configured (WM_LLAMA_BG_MODEL set),
        routes to the continuous background model. Falls back to the
        single backend otherwise.
        """
        try:
            from whitemagic.inference.llama_cpp import get_dual_model_manager

            dmm = get_dual_model_manager()
            if dmm is not None:
                if not dmm.background.is_available:
                    dmm.start_background()
                return dmm.route_inference(prompt, is_background=True)
        except Exception as e:
            logger.debug("Background model routing failed: %s", e)
        return self.complete(prompt, max_tokens=max_tokens, temperature=temperature)
