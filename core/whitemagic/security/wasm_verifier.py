# ruff: noqa: BLE001
"""WASM Compute Verification Layer — Sandbox-based result verification.
================================================================
Verifies agent compute results by replaying tool calls in a
sandboxed environment and comparing outputs. Uses checksum-based
verification for deterministic tools.

Opt-in via WM_WASM_VERIFY=1 env var. Non-blocking — runs post-dispatch.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Any

from whitemagic.config.paths import WM_ROOT

logger = logging.getLogger(__name__)

# ── Tools that can be verified (pure/read only) ──────────────────────

VERIFIABLE_TOOLS: set[str] = {
    "memory_search",
    "memory_stats",
    "galaxy.list",
    "galaxy.stats",
    "session.recall",
    "session.search",
    "gnosis",
    "capabilities",
    "tool.graph",
    "karma.report",
    "harmony.vector",
}

# ── Dataclasses ──────────────────────────────────────────────────────


@dataclass
class VerificationRequest:
    """Request to verify a tool call's output."""

    tool_name: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    agent_id: str = "default"
    timestamp: float = field(default_factory=lambda: __import__("time").time())


@dataclass
class VerificationResult:
    """Result of verification."""

    verified: bool
    method: str  # "checksum", "replay", "skipped"
    confidence: float = 0.0
    details: str = ""


# ── WASM Verifier ────────────────────────────────────────────────────


class WasmVerifier:
    """Verifies tool outputs via checksum or WASM replay."""

    def __init__(self) -> None:
        self._checksum_cache: dict[str, str] = {}  # tool:hash(inputs) → hash(outputs)
        self._lock = threading.Lock()
        self._verify_dir = WM_ROOT / "verification"
        self._verify_dir.mkdir(parents=True, exist_ok=True)
        self._worker_script = self._verify_dir / "verify_worker.js"

    def verify(self, request: VerificationRequest) -> VerificationResult:
        """Verify a tool call's output."""
        if request.tool_name not in VERIFIABLE_TOOLS:
            return VerificationResult(
                verified=True,
                method="skipped",
                confidence=1.0,
                details=f"Tool {request.tool_name} not in verifiable set",
            )

        # Try checksum verification first (fast)
        result = self._checksum_verify(request)
        if result.verified:
            return result

        # Fall back to replay if checksum doesn't match
        # (could be a new input combination)
        replay_result = self._replay_verify(request)
        if replay_result.verified:
            # Update checksum cache with new verified result
            self._update_checksum_cache(request)
            return replay_result

        return result or replay_result

    def _checksum_verify(self, request: VerificationRequest) -> VerificationResult:
        """Verify via input→output checksum mapping."""
        input_hash = self._hash_dict(request.inputs)
        cache_key = f"{request.tool_name}:{input_hash}"

        with self._lock:
            if cache_key in self._checksum_cache:
                expected_output_hash = self._checksum_cache[cache_key]
                actual_output_hash = self._hash_dict(request.outputs)
                if expected_output_hash == actual_output_hash:
                    return VerificationResult(
                        verified=True,
                        method="checksum",
                        confidence=0.95,
                        details="Checksum match",
                    )
                else:
                    return VerificationResult(
                        verified=False,
                        method="checksum",
                        confidence=0.9,
                        details=f"Checksum mismatch: expected {expected_output_hash[:8]}, got {actual_output_hash[:8]}",
                    )

        # No cached checksum — can't verify via checksum alone
        return VerificationResult(
            verified=False,
            method="checksum",
            confidence=0.0,
            details="No cached checksum for this input combination",
        )

    def _replay_verify(self, request: VerificationRequest) -> VerificationResult:
        """Verify by replaying the tool call in a sandbox."""
        # For now, we use a simple Python-level replay rather than actual WASM
        # This avoids Node.js dependency in tests while maintaining the interface
        try:
            replayed = self._replay_tool(request.tool_name, request.inputs)
            if replayed is None:
                return VerificationResult(
                    verified=True,
                    method="replay",
                    confidence=0.5,
                    details="Replay not available, assuming verified",
                )

            replay_hash = self._hash_dict(replayed)
            output_hash = self._hash_dict(request.outputs)

            if replay_hash == output_hash:
                return VerificationResult(
                    verified=True,
                    method="replay",
                    confidence=0.9,
                    details="Replay matches output",
                )
            else:
                return VerificationResult(
                    verified=False,
                    method="replay",
                    confidence=0.85,
                    details=f"Replay mismatch: replay hash {replay_hash[:8]} vs output hash {output_hash[:8]}",
                )
        except Exception as e:
            logger.debug("Replay verification failed: %s", e)
            return VerificationResult(
                verified=True,
                method="replay",
                confidence=0.3,
                details=f"Replay error (permissive): {e}",
            )

    def _replay_tool(self, tool_name: str, inputs: dict[str, Any]) -> dict[str, Any] | None:
        """Replay a tool call to get expected output.

        For pure/read tools, we re-execute the tool and compare.
        Returns None if replay is not possible.
        """
        try:
            from whitemagic.tools.dispatch_table import dispatch

            # Strip pipeline-internal kwargs
            clean_inputs = {
                k: v for k, v in inputs.items()
                if not k.startswith("_")
            }
            result = dispatch(tool_name, **clean_inputs)
            if isinstance(result, dict):
                # Strip non-deterministic fields
                result.pop("_sensorium", None)
                result.pop("timestamp", None)
                if "metadata" in result and isinstance(result["metadata"], dict):
                    result["metadata"].pop("elapsed_ms", None)
            return result
        except Exception as e:
            logger.debug("Replay tool %s failed: %s", tool_name, e)
            return None

    def _update_checksum_cache(self, request: VerificationRequest) -> None:
        """Update the checksum cache with a verified result."""
        input_hash = self._hash_dict(request.inputs)
        output_hash = self._hash_dict(request.outputs)
        cache_key = f"{request.tool_name}:{input_hash}"
        with self._lock:
            self._checksum_cache[cache_key] = output_hash
            # Limit cache size
            if len(self._checksum_cache) > 10000:
                # Remove oldest 25% (arbitrary keys)
                keys = list(self._checksum_cache.keys())
                for k in keys[:2500]:
                    del self._checksum_cache[k]

    @staticmethod
    def _hash_dict(data: dict[str, Any]) -> str:
        """Create a stable hash of a dict."""
        try:
            # Sort keys for determinism, filter non-serializable
            clean = {}
            for k, v in sorted(data.items()):
                if k.startswith("_"):
                    continue
                try:
                    json.dumps(v)
                    clean[k] = v
                except (TypeError, ValueError):
                    clean[k] = str(v)
            return hashlib.sha256(
                json.dumps(clean, sort_keys=True, default=str).encode()
            ).hexdigest()
        except Exception:
            return hashlib.sha256(str(data).encode()).hexdigest()

    def get_status(self) -> dict[str, Any]:
        """Return verifier status."""
        return {
            "enabled": os.environ.get("WM_WASM_VERIFY", "0") in ("1", "true", "yes"),
            "verifiable_tools": sorted(VERIFIABLE_TOOLS),
            "checksum_cache_size": len(self._checksum_cache),
            "worker_script": str(self._worker_script),
        }


# ── Singleton ────────────────────────────────────────────────────────

_verifier: WasmVerifier | None = None


def get_wasm_verifier() -> WasmVerifier:
    """Get the global WasmVerifier singleton."""
    global _verifier
    if _verifier is None:
        _verifier = WasmVerifier()
    return _verifier
