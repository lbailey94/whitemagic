# ruff: noqa: BLE001
"""
Local LLM Bridge
================
Provides an interface to local Large Language Models (LLMs) for inference
without cloud API costs.

Primary backend: Ollama (http://localhost:11434)
Secondary backend: (Planned) Candle/ONNX via Rust bridge

Usage:
    from whitemagic.inference.local_llm import LocalLLM
    llm = LocalLLM(model="phi3:mini")
    response = llm.complete("Why is the sky blue?")
"""

import logging
import time

import requests  # type: ignore

logger = logging.getLogger(__name__)

class LocalLLM:
    """Interface for local LLM inference."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "phi3:mini"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._available = False
        self._check_availability()

    def _check_availability(self):
        """Check if Ollama server is running."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=1.0)
            if resp.status_code == 200:
                self._available = True
                # Check if model exists, if not, try to pull or warn?
                models = [m['name'] for m in resp.json().get('models', [])]
                if self.model not in models and f"{self.model}:latest" not in models:
                    logger.warning(f"Model {self.model} not found in Ollama. Available: {models}")
            else:
                self._available = False
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            self._available = False

    @property
    def is_available(self) -> bool:
        """
        Check whether the available condition holds.
        
        Returns:
            bool
        """
        return self._available

    def complete(self, prompt: str, stop: list[str] | None = None, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate a completion."""
        if not self._available:
            return "Error: Local LLM (Ollama) not available. Run 'ollama serve'."

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "stop": stop or []
            }
        }

        try:
            start = time.time()
            resp = requests.post(url, json=payload, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            latency = (time.time() - start) * 1000
            logger.debug(f"Local inference finished in {latency:.2f}ms")
            res = data.get("response", "")
            return str(res)
        except Exception as e:
            logger.error(f"Local LLM inference failed: {e}")
            return f"Error: {e}"

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
        """Chat completion."""
        if not self._available:
            return "Error: Local LLM (Ollama) not available."

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            res = data.get("message", {}).get("content", "")
            return str(res)
        except (ConnectionError, TimeoutError, OSError) as e:
            logger.error(f"Local LLM chat failed: {e}")
            return f"Error: {e}"

    def classify(self, text: str, categories: list[str]) -> str:
        """
        Classify text into one of the provided categories using constrained generation
        or simple prompting (fallback).
        """
        prompt = (
            f"Classify the following text into exactly one of these categories: {', '.join(categories)}.\n"
            f"Text: \"{text[:500]}\"\n"
            f"Category:"
        )
        response = self.complete(prompt, stop=["\n"], max_tokens=10, temperature=0.0)
        cleaned = response.strip().lower()

        # Simple fuzzy match
        for cat in categories:
            if cat.lower() in cleaned:
                return cat
        return "unknown"
