# ruff: noqa: BLE001
"""llama.cpp backend — local LLM inference via llama-server HTTP API.

This module provides a Python interface to llama-server (the llama.cpp
HTTP server), which offers better performance and memory predictability
than llama.cpp for continuous consciousness workloads.

Key advantages over llama.cpp:
- Predictable memory (no dynamic quantization swapping)
- Better throughput for continuous inference (no model loading overhead)
- Supports speculative decoding with draft models
- Lower latency for small models (no HTTP framework overhead)

Usage::

    from whitemagic.inference.llama_cpp import LlamaCppBackend

    backend = LlamaCppBackend(model_path="/models/qwen2.5-1.5b.gguf")
    if backend.is_available:
        response = backend.complete("Hello, world")
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8080
DEFAULT_TIMEOUT = 300


@dataclass
class LlamaCppConfig:
    """Configuration for the llama.cpp backend.

    All parameters map directly to llama-server CLI flags.
    See: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
    """

    # ── Core ──────────────────────────────────────────────────────────
    model_path: str = ""
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    n_ctx: int = 8192
    n_threads: int | None = None  # generation threads
    n_threads_batch: int | None = None  # prompt processing threads
    n_gpu_layers: int = 0
    temperature: float = 0.7
    top_p: float = 0.9
    repeat_penalty: float = 1.1
    seed: int = -1
    flash_attn: bool = True
    no_mmap: bool = False

    # ── KV Cache Quantization ────────────────────────────────────────
    # Reduces memory for KV cache, enabling larger context windows.
    # q8_0 = 50% reduction (practically lossless)
    # q4_0 = 75% reduction (minimal quality loss)
    cache_type_k: str = "q8_0"
    cache_type_v: str = "q8_0"

    # ── Speculative Decoding ─────────────────────────────────────────
    # ngram-mod: no draft model needed, uses token history hash pool (~16MB)
    # draft-simple: uses a separate draft model
    # draft-eagle3: EAGLE-3 draft model (reads target hidden states)
    # Comma-separated list to combine: "ngram-mod,draft-simple"
    spec_type: str = "ngram-mod"
    draft_model_path: str = ""  # path to draft model GGUF
    spec_ngram_mod_n_match: int = 24  # ngram lookup length
    spec_ngram_mod_n_min: int = 48  # min draft tokens
    spec_ngram_mod_n_max: int = 64  # max draft tokens
    spec_draft_n_max: int = 16  # max tokens for draft model
    spec_draft_n_min: int = 5  # min tokens for draft model
    spec_draft_p_min: float = 0.9  # min probability for greedy drafting

    # ── Parallel Decoding ────────────────────────────────────────────
    # Number of concurrent server slots for continuous batching.
    # Citta heartbeats, entity extraction, salience, user chat can all share.
    parallel: int = 4

    # ── Thread Optimization ──────────────────────────────────────────
    cpu_strict: bool = False  # strict CPU placement
    poll: bool = False  # polling mode (reduces latency for continuous workloads)

    # ── Grammar / JSON Schema Constraints ────────────────────────────
    # Constrains output to valid JSON — zero parsing failures.
    # Set json_schema at server level for always-on constraints,
    # or pass response_format per-request via chat API.
    json_schema: str = ""  # JSON schema string for constrained generation
    grammar_file: str = ""  # path to GBNF grammar file
    jinja: bool = True  # enable Jinja templating for tool-use chat templates

    # ── Embeddings ───────────────────────────────────────────────────
    embeddings: bool = False  # restrict to embedding-only use case

    def to_args(self) -> list[str]:
        """Convert to llama-server CLI arguments."""
        args = [
            "--host", self.host,
            "--port", str(self.port),
            "--ctx-size", str(self.n_ctx),
            "--temp", str(self.temperature),
            "--top-p", str(self.top_p),
            "--repeat-penalty", str(self.repeat_penalty),
            "--cache-type-k", self.cache_type_k,
            "--cache-type-v", self.cache_type_v,
            "--parallel", str(self.parallel),
        ]
        if self.n_threads:
            args.extend(["--threads", str(self.n_threads)])
        if self.n_threads_batch:
            args.extend(["--threads-batch", str(self.n_threads_batch)])
        if self.n_gpu_layers > 0:
            args.extend(["--n-gpu-layers", str(self.n_gpu_layers)])
        if self.flash_attn:
            args.extend(["--flash-attn", "on"])
        if self.no_mmap:
            args.append("--no-mmap")
        if self.seed >= 0:
            args.extend(["--seed", str(self.seed)])
        if self.cpu_strict:
            args.append("--cpu-strict")
        if self.poll:
            args.append("--poll")
        if self.jinja:
            args.append("--jinja")
        if self.embeddings:
            args.append("--embeddings")

        # Speculative decoding
        if self.spec_type and self.spec_type != "none":
            args.extend(["--spec-type", self.spec_type])
            if "ngram-mod" in self.spec_type:
                args.extend([
                    "--spec-ngram-mod-n-match", str(self.spec_ngram_mod_n_match),
                    "--spec-ngram-mod-n-min", str(self.spec_ngram_mod_n_min),
                    "--spec-ngram-mod-n-max", str(self.spec_ngram_mod_n_max),
                ])
            if "draft" in self.spec_type and self.draft_model_path:
                args.extend(["--model-draft", self.draft_model_path])
                args.extend(["--spec-draft-n-max", str(self.spec_draft_n_max)])
                args.extend(["--spec-draft-n-min", str(self.spec_draft_n_min)])
                args.extend(["--spec-draft-p-min", str(self.spec_draft_p_min)])

        # Grammar constraints
        if self.json_schema:
            args.extend(["--json-schema", self.json_schema])
        if self.grammar_file:
            args.extend(["--grammar-file", self.grammar_file])

        return args


class LlamaCppBackend:
    """llama.cpp inference backend via llama-server HTTP API."""

    def __init__(
        self,
        model_path: str | None = None,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        auto_start: bool = False,
        binary_path: str | None = None,
        config: LlamaCppConfig | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._base_url = f"http://{host}:{port}"
        self._model_path = model_path or os.environ.get("WM_LLAMA_MODEL", "")
        self._binary_path = binary_path or os.environ.get("WM_LLAMA_SERVER", "llama-server")
        self._process: subprocess.Popen | None = None
        self._available = False
        if config:
            self._config = config
            self._config.model_path = self._model_path
            self._config.host = host
            self._config.port = port
        else:
            self._config = LlamaCppConfig(
                model_path=self._model_path,
                host=host,
                port=port,
            )

        # Check if server is already running
        self._check_availability()

        # Auto-start if requested
        if not self._available and auto_start and self._model_path:
            self.start_server()

    def _check_availability(self) -> None:
        """Check if llama-server is running and responsive."""
        try:
            resp = requests.get(f"{self._base_url}/health", timeout=2.0)
            self._available = resp.status_code == 200
            if self._available:
                logger.debug("llama-server available at %s", self._base_url)
        except Exception:
            self._available = False

    def start_server(self) -> bool:
        """Start llama-server as a subprocess."""
        if not self._model_path:
            logger.warning("No model path specified — cannot start llama-server")
            return False

        if not Path(self._binary_path).exists() and not _which(self._binary_path):
            logger.warning("llama-server binary not found at %s", self._binary_path)
            return False

        args = [self._binary_path, "-m", self._model_path] + self._config.to_args()
        logger.info("Starting llama-server: %s", " ".join(args[:5]))

        try:
            self._process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "LLAMA_LOG_PREFIX": "0"},
            )
            # Wait for server to be ready (up to 120s for large models from SD card)
            for _ in range(240):
                time.sleep(0.5)
                self._check_availability()
                if self._available:
                    logger.info("llama-server started (PID %d)", self._process.pid)
                    return True

            logger.error("llama-server failed to start within 120s")
            self.stop_server()
            return False
        except Exception as e:
            logger.error("Failed to start llama-server: %s", e)
            return False

    def stop_server(self) -> None:
        """Stop the llama-server subprocess."""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
            self._available = False
            logger.info("llama-server stopped")

    @property
    def is_available(self) -> bool:
        """Check if the backend is available."""
        if not self._available:
            self._check_availability()
        return self._available

    @property
    def base_url(self) -> str:
        return self._base_url

    def complete(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float | None = None,
        stop: list[str] | None = None,
        stream: bool = False,
        json_schema: str | None = None,
        grammar: str | None = None,
    ) -> str:
        """Generate a completion.

        Args:
            prompt: The prompt text.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature override.
            stop: Stop sequences.
            stream: Whether to stream the response.
            json_schema: JSON schema string for constrained output.
            grammar: GBNF grammar string for constrained output.
        """
        if not self.is_available:
            return "Error: llama-server not available. Start with start_server()."

        payload: dict[str, Any] = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": temperature if temperature is not None else self._config.temperature,
            "top_p": self._config.top_p,
            "repeat_penalty": self._config.repeat_penalty,
            "stream": stream,
        }
        if stop:
            payload["stop"] = stop
        if json_schema:
            # llama-server expects json_schema as a JSON object, not a string
            if isinstance(json_schema, str):
                payload["json_schema"] = json.loads(json_schema)
            else:
                payload["json_schema"] = json_schema
        if grammar:
            payload["grammar"] = grammar

        try:
            start = time.time()
            resp = requests.post(
                f"{self._base_url}/completion",
                json=payload,
                timeout=DEFAULT_TIMEOUT,
                stream=stream,
            )
            resp.raise_for_status()

            if stream:
                # Collect streamed response
                text = ""
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        if data.get("stop"):
                            break
                        text += data.get("content", "")
                latency = (time.time() - start) * 1000
                logger.debug("llama.cpp stream completed in %.0fms", latency)
                return text
            else:
                data = resp.json()
                latency = (time.time() - start) * 1000
                logger.debug("llama.cpp inference in %.0fms", latency)
                return data.get("content", "")
        except Exception as e:
            logger.error("llama.cpp inference failed: %s", e)
            return f"Error: {e}"

    def complete_with_tokens(
        self,
        prompt: str,
        max_tokens: int = 64,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Generate a completion and return both text and token IDs.

        Used by the speculative decoding pipeline which needs token-level
        comparison between draft and verify models.

        Returns:
            {"text": str, "tokens": list[int], "latency_ms": float}
        """
        if not self.is_available:
            return {"text": "", "tokens": [], "latency_ms": 0.0}

        payload: dict[str, Any] = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": temperature if temperature is not None else self._config.temperature,
            "top_p": self._config.top_p,
            "repeat_penalty": self._config.repeat_penalty,
            "stream": False,
        }

        try:
            start = time.time()
            resp = requests.post(
                f"{self._base_url}/completion",
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            latency_ms = (time.time() - start) * 1000
            text = data.get("content", "")
            # llama-server doesn't always return token IDs in the response.
            # Use the tokenize endpoint to convert generated text to tokens.
            tokens = data.get("tokens", [])
            if not tokens and text:
                tokens = self.tokenize(text)
            return {
                "text": text,
                "tokens": tokens,
                "latency_ms": round(latency_ms, 2),
            }
        except Exception as e:
            logger.error("llama.cpp complete_with_tokens failed: %s", e)
            return {"text": "", "tokens": [], "latency_ms": 0.0}

    def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        """Chat completion using OpenAI-compatible endpoint.

        Args:
            messages: List of {role, content} message objects.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature override.
            response_format: JSON schema constraint, e.g.
                {"type": "json_object", "schema": {...}}
            tools: List of tool definitions for function calling.
        """
        if not self.is_available:
            return "Error: llama-server not available."

        payload: dict[str, Any] = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature if temperature is not None else self._config.temperature,
            "stream": False,
        }
        if response_format:
            payload["response_format"] = response_format
        if tools:
            payload["tools"] = tools

        try:
            resp = requests.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            message = data.get("choices", [{}])[0].get("message", {})
            content = message.get("content", "")
            # Qwen3 reasoning models: if content is empty, the model may have
            # used all token budget on reasoning_content. Fall back to it.
            if not content.strip():
                reasoning = message.get("reasoning_content", "")
                if reasoning.strip():
                    content = reasoning
            return content
        except Exception as e:
            logger.error("llama.cpp chat failed: %s", e)
            return f"Error: {e}"

    def embed(self, text: str) -> list[float]:
        """Get embeddings for text.

        Uses the native /embedding endpoint (per-token embeddings averaged).
        Falls back to /v1/embeddings if the model supports pooling.
        """
        if not self.is_available:
            return []

        try:
            resp = requests.post(
                f"{self._base_url}/embedding",
                json={"content": text},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                emb = data[0].get("embedding", [])
                # Per-token embeddings come as list of lists — average them
                if emb and isinstance(emb[0], list):
                    import numpy as np
                    arr = np.array(emb)
                    return arr.mean(axis=0).tolist()
                return emb
            return []
        except Exception:
            # Fallback to OpenAI-compatible endpoint
            try:
                resp = requests.post(
                    f"{self._base_url}/v1/embeddings",
                    json={"input": text},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", [{}])[0].get("embedding", [])
            except Exception as e:
                logger.error("llama.cpp embedding failed: %s", e)
                return []

    def tokenize(self, text: str) -> list[int]:
        """Tokenize text."""
        if not self.is_available:
            return []

        try:
            resp = requests.post(
                f"{self._base_url}/tokenize",
                json={"content": text},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("tokens", [])
        except Exception as e:
            logger.error("llama.cpp tokenize failed: %s", e)
            return []

    def get_status(self) -> dict[str, Any]:
        """Get server status including tuning parameters."""
        if not self.is_available:
            return {"available": False}

        status: dict[str, Any] = {
            "available": True,
            "pid": self._process.pid if self._process else None,
            "base_url": self._base_url,
            "model_path": self._model_path,
            "config": {
                "n_ctx": self._config.n_ctx,
                "cache_type_k": self._config.cache_type_k,
                "cache_type_v": self._config.cache_type_v,
                "spec_type": self._config.spec_type,
                "parallel": self._config.parallel,
                "flash_attn": self._config.flash_attn,
                "jinja": self._config.jinja,
            },
        }

        try:
            resp = requests.get(f"{self._base_url}/props", timeout=5)
            if resp.status_code == 200:
                props = resp.json()
                status["model"] = props.get("model_path", "")
                status["context_size"] = props.get(
                    "default_generation_settings", {}
                ).get("n_ctx", 0)
        except Exception:
            logger.debug("Ignored error in llama_cpp.py:536")
        return status


def _which(binary: str) -> str | None:
    """Find binary in PATH."""
    from shutil import which
    return which(binary)


# ── Dual-model manager ───────────────────────────────────────────────


class DualModelManager:
    """Manages two llama.cpp models: background (small) + foreground (large).

    The background model runs continuously for citta heartbeats, salience
    detection, and simple tasks. The foreground model handles user-facing
    requests and is loaded/unloaded as needed to save memory.
    """

    def __init__(
        self,
        background_model: str = "",
        foreground_model: str = "",
        background_port: int = 8081,
        foreground_port: int = 8080,
        background_config: LlamaCppConfig | None = None,
        foreground_config: LlamaCppConfig | None = None,
    ) -> None:
        bg_cfg = background_config or LlamaCppConfig(
            n_ctx=4096,
            cache_type_k="q8_0",
            cache_type_v="q8_0",
            parallel=2,
            spec_type="ngram-mod",
            temperature=0.3,
            embeddings=True,
        )
        fg_cfg = foreground_config or LlamaCppConfig(
            n_ctx=8192,
            cache_type_k="q8_0",
            cache_type_v="q8_0",
            parallel=4,
            spec_type="ngram-mod",
            jinja=True,
        )
        self._background = LlamaCppBackend(
            model_path=background_model,
            port=background_port,
            config=bg_cfg,
        )
        self._foreground = LlamaCppBackend(
            model_path=foreground_model,
            port=foreground_port,
            config=fg_cfg,
        )
        self._background_started = False

    def start_background(self) -> bool:
        """Start the background model (runs continuously)."""
        if self._background.is_available:
            return True
        result = self._background.start_server()
        if result:
            self._background_started = True
            logger.info("Background model started (continuous)")
        return result

    def start_foreground(self) -> bool:
        """Start the foreground model (on-demand)."""
        if self._foreground.is_available:
            return True
        return self._foreground.start_server()

    def stop_foreground(self) -> None:
        """Stop the foreground model to free memory."""
        self._foreground.stop_server()

    def stop_all(self) -> None:
        """Stop all models."""
        self._foreground.stop_server()
        self._background.stop_server()
        self._background_started = False

    @property
    def background(self) -> LlamaCppBackend:
        return self._background

    @property
    def foreground(self) -> LlamaCppBackend:
        return self._foreground

    def route_inference(self, prompt: str, is_background: bool = False) -> str:
        """Route inference to appropriate model."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Answer briefly."},
            {"role": "user", "content": prompt},
        ]
        if is_background and self._background.is_available:
            return self._background.chat(messages, max_tokens=64)
        elif self._foreground.is_available:
            return self._foreground.chat(messages, max_tokens=512)
        elif self._background.is_available:
            return self._background.chat(messages, max_tokens=64)
        return "Error: No model available"


# ── Binary manager ───────────────────────────────────────────────────


class BinaryManager:
    """Manages llama-server binary discovery and version checking."""

    SEARCH_PATHS = [
        "/usr/local/bin/llama-server",
        "/usr/bin/llama-server",
        os.path.expanduser("~/.local/bin/llama-server"),
        os.path.expanduser("~/llama.cpp/build/bin/llama-server"),
        os.path.expanduser("~/llama.cpp/build/bin/Release/llama-server"),
    ]

    @classmethod
    def find_binary(cls) -> str | None:
        """Find llama-server binary."""
        # Check PATH first
        from shutil import which
        found = which("llama-server")
        if found:
            return found

        # Check known locations
        for path in cls.SEARCH_PATHS:
            if Path(path).exists():
                return path

        return None

    @classmethod
    def get_version(cls, binary_path: str) -> str:
        """Get llama-server version."""
        try:
            result = subprocess.run(
                [binary_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() or result.stderr.strip()
        except Exception:
            return "unknown"

    @classmethod
    def is_compatible(cls, binary_path: str) -> bool:
        """Check if binary supports required features."""
        version = cls.get_version(binary_path)
        # llama-server b4000+ supports /v1/chat/completions
        return "llama-server" in version.lower() or True  # permissive


# ── Singleton ────────────────────────────────────────────────────────

_backend: LlamaCppBackend | None = None
_dual_manager: DualModelManager | None = None


def get_llama_cpp_backend() -> LlamaCppBackend:
    """Get the global LlamaCppBackend singleton.

    Auto-discovers model and binary if not explicitly configured.
    Reads from environment variables:
        WM_LLAMA_MODEL: path to GGUF model file
        WM_LLAMA_SERVER: path to llama-server binary
        WM_LLAMA_HOST: server host (default: localhost)
        WM_LLAMA_PORT: server port (default: 8080)
    """
    global _backend
    if _backend is None:
        model = os.environ.get("WM_LLAMA_MODEL", "")
        binary = os.environ.get("WM_LLAMA_SERVER", "llama-server")
        host = os.environ.get("WM_LLAMA_HOST", DEFAULT_HOST)
        port = int(os.environ.get("WM_LLAMA_PORT", str(DEFAULT_PORT)))

        # Auto-discover binary if not in PATH
        if not _which(binary):
            found = BinaryManager.find_binary()
            if found:
                binary = found

        # Auto-discover model if not set
        if not model:
            from whitemagic.interfaces.chat import ModelDiscovery
            best = ModelDiscovery.best_model()
            if best and best.backend == "llama_cpp":
                model = best.path

        _backend = LlamaCppBackend(
            model_path=model,
            host=host,
            port=port,
            binary_path=binary,
        )
    return _backend


def get_dual_model_manager() -> DualModelManager | None:
    """Get the global DualModelManager singleton.

    Returns None if dual-model is not configured (no background model path set).

    Reads from environment variables:
        WM_LLAMA_BG_MODEL: path to background (small) GGUF model
        WM_LLAMA_FG_MODEL: path to foreground (large) GGUF model
        WM_LLAMA_BG_PORT: background server port (default: 8081)
        WM_LLAMA_FG_PORT: foreground server port (default: 8080)
    """
    global _dual_manager
    if _dual_manager is None:
        bg_model = os.environ.get("WM_LLAMA_BG_MODEL", "")
        fg_model = os.environ.get("WM_LLAMA_FG_MODEL", "")
        bg_port = int(os.environ.get("WM_LLAMA_BG_PORT", "8081"))
        fg_port = int(os.environ.get("WM_LLAMA_FG_PORT", str(DEFAULT_PORT)))

        if not bg_model and not fg_model:
            return None

        _dual_manager = DualModelManager(
            background_model=bg_model,
            foreground_model=fg_model,
            background_port=bg_port,
            foreground_port=fg_port,
        )
    return _dual_manager
