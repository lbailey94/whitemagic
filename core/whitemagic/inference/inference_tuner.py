# ruff: noqa: BLE001
"""Inference Auto-Tuner — Hardware-aware kernel and parameter selection.
================================================================
Senses hardware capabilities at startup and configures the inference
pipeline for optimal performance on whatever hardware WhiteMagic
finds itself on.

Usage::

    from whitemagic.inference.inference_tuner import get_inference_tuner

    tuner = get_inference_tuner()
    tuner.apply_to_llama_config(config)  # Mutates LlamaCppConfig in-place
    report = tuner.get_report()
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from whitemagic.config.paths import WM_ROOT
from whitemagic.core.system.hardware_monitor import HardwareProfile, detect_hardware

logger = logging.getLogger(__name__)

_TUNER_CACHE_PATH = WM_ROOT / "inference_tuner_cache.json"


@dataclass
class KernelBenchmark:
    """Benchmark result for a single kernel/configuration."""

    kernel_name: str
    tokens_per_second: float = 0.0
    latency_ms: float = 0.0
    elements_per_second: float = 0.0
    passed: bool = False


@dataclass
class TunerReport:
    """Full report of hardware detection and tuning decisions."""

    timestamp: float = field(default_factory=time.time)
    cpu_model: str = ""
    inference_tier: str = ""
    simd_width_bits: int = 0
    cpu_threads: int = 0
    available_ram_gb: float = 0.0
    selected_kernel: str = ""
    spec_params: dict[str, Any] = field(default_factory=dict)
    llama_config_overrides: dict[str, Any] = field(default_factory=dict)
    benchmarks: list[dict[str, Any]] = field(default_factory=list)
    is_constrained: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class InferenceTuner:
    """Auto-tunes inference pipeline based on detected hardware.

    Responsibilities:
    1. Detect CPU ISA features (AVX2, AVX-512, VNNI, AMX)
    2. Select optimal ternary kernel for the hardware
    3. Configure speculative decoding parameters
    4. Tune llama.cpp parameters (threads, cache, parallelism)
    5. Optionally benchmark kernels to validate selection
    6. Persist tuning decisions across sessions
    """

    def __init__(self) -> None:
        self._profile: HardwareProfile | None = None
        self._report: TunerReport | None = None
        self._applied = False

    @property
    def profile(self) -> HardwareProfile:
        """Lazy-load hardware profile."""
        if self._profile is None:
            self._profile = detect_hardware()
            logger.info(
                "Hardware detected: %s (%d threads, %.1f GB RAM, tier=%s, simd=%d-bit)",
                self._profile.cpu_model_name,
                self._profile.cpu_threads,
                self._profile.available_ram_gb,
                self._profile.inference_tier,
                self._profile.simd_width_bits,
            )
        return self._profile

    @property
    def report(self) -> TunerReport:
        """Lazy-compute tuning report."""
        if self._report is None:
            self._report = self._compute_report()
        return self._report

    def _compute_report(self) -> TunerReport:
        """Compute tuning decisions based on hardware profile."""
        hw = self.profile

        # Select speculative decoding params
        spec_params = hw.optimal_spec_params

        # Compute llama.cpp config overrides
        overrides: dict[str, Any] = {}

        # Thread allocation: leave 2 threads for OS / MCP server
        if hw.cpu_threads <= 4:
            overrides["n_threads"] = max(1, hw.cpu_threads - 1)
            overrides["n_threads_batch"] = hw.cpu_threads
            overrides["parallel"] = 1
        elif hw.cpu_threads <= 8:
            overrides["n_threads"] = hw.cpu_threads - 2
            overrides["n_threads_batch"] = hw.cpu_threads
            overrides["parallel"] = spec_params.get("parallel", 2)
        else:
            overrides["n_threads"] = hw.cpu_threads - 2
            overrides["n_threads_batch"] = hw.cpu_threads
            overrides["parallel"] = spec_params.get("parallel", 4)

        # KV cache quantization based on memory
        if hw.available_ram_gb < 4:
            overrides["cache_type_k"] = "q4_0"
            overrides["cache_type_v"] = "q4_0"
            overrides["n_ctx"] = 2048
        elif hw.available_ram_gb < 8:
            overrides["cache_type_k"] = "q4_0"
            overrides["cache_type_v"] = "q4_0"
            overrides["n_ctx"] = 4096
        elif hw.available_ram_gb < 16:
            overrides["cache_type_k"] = "q8_0"
            overrides["cache_type_v"] = "q8_0"
            overrides["n_ctx"] = 8192
        else:
            overrides["cache_type_k"] = "q8_0"
            overrides["cache_type_v"] = "q8_0"
            overrides["n_ctx"] = 16384

        # Speculative decoding params
        overrides["spec_type"] = "ngram-mod"
        overrides["spec_ngram_mod_n_match"] = spec_params["spec_ngram_mod_n_match"]
        overrides["spec_ngram_mod_n_min"] = spec_params["spec_ngram_mod_n_min"]
        overrides["spec_ngram_mod_n_max"] = spec_params["spec_ngram_mod_n_max"]

        # Polling mode for continuous workloads (reduces latency)
        if hw.cpu_threads >= 8 and not hw.is_constrained:
            overrides["poll"] = True

        # Flash attention always on
        overrides["flash_attn"] = True

        return TunerReport(
            cpu_model=hw.cpu_model_name,
            inference_tier=hw.inference_tier,
            simd_width_bits=hw.simd_width_bits,
            cpu_threads=hw.cpu_threads,
            available_ram_gb=hw.available_ram_gb,
            selected_kernel=hw.optimal_ternary_kernel,
            spec_params=spec_params,
            llama_config_overrides=overrides,
            is_constrained=hw.is_constrained,
        )

    def apply_to_llama_config(self, config: Any) -> None:
        """Apply tuning overrides to a LlamaCppConfig in-place.

        Only overrides fields that are at their defaults — explicit
        user configuration is preserved.
        """
        report = self.report
        overrides = report.llama_config_overrides

        for key, value in overrides.items():
            if hasattr(config, key):
                current = getattr(config, key)
                # Only override if user hasn't explicitly changed from default
                # We check against the dataclass default
                fields_map = type(config).__dataclass_fields__
                if key in fields_map:
                    default_val = fields_map[key].default
                    if current == default_val:
                        setattr(config, key, value)
                        logger.debug("Tuner: %s = %s (auto)", key, value)
                    else:
                        logger.debug("Tuner: %s = %s (user-set, preserved)", key, current)

        self._applied = True
        logger.info(
            "Inference tuning applied: kernel=%s, threads=%s, ctx=%s, spec=%s",
            report.selected_kernel,
            overrides.get("n_threads"),
            overrides.get("n_ctx"),
            overrides.get("spec_type"),
        )

    def get_recommended_config(self) -> dict[str, Any]:
        """Get recommended config as a dict (for new config creation)."""
        return dict(self.report.llama_config_overrides)

    def benchmark_ternary_kernels(self, m: int = 64, k: int = 256) -> list[KernelBenchmark]:
        """Benchmark available ternary kernels to validate selection.

        Runs a small GEMV with each available kernel and measures throughput.
        Useful for validating that the auto-selected kernel is actually fastest
        on the current hardware.
        """
        results: list[KernelBenchmark] = []
        hw = self.profile

        # Generate test data
        import random

        random.seed(42)
        weights = [random.choice([0b00, 0b01, 0b10]) for _ in range(m * k)]
        weights_packed = []
        for i in range(m):
            words_per_row = (k + 15) // 16
            for w in range(words_per_row):
                word = 0
                for j in range(16):
                    idx = w * 16 + j
                    if idx >= k:
                        break
                    word |= weights[i * k + idx] << (j * 2)
                weights_packed.append(word)
        activations = [random.uniform(-1.0, 1.0) for _ in range(k)]

        # Try Rust kernels via PyO3
        try:
            from whitemagic.core.acceleration.rust_bridge import get_rust_bridge

            bridge = get_rust_bridge()
            if bridge.is_available:
                # Benchmark ternary_gemv
                iterations = 100
                start = time.time()
                for _ in range(iterations):
                    bridge.call("py_ternary_gemv", weights_packed, activations, m, k)
                elapsed = time.time() - start
                tps = iterations / elapsed if elapsed > 0 else 0
                eps = (iterations * m * k) / elapsed if elapsed > 0 else 0

                kernel_name = hw.optimal_ternary_kernel
                results.append(KernelBenchmark(
                    kernel_name=kernel_name,
                    tokens_per_second=tps,
                    latency_ms=(elapsed / iterations) * 1000,
                    elements_per_second=eps,
                    passed=True,
                ))
                logger.info(
                    "Benchmark %s: %.1f ops/s, %.2f ms/op, %.1f M elem/s",
                    kernel_name, tps, (elapsed / iterations) * 1000, eps / 1e6,
                )
        except Exception as e:
            logger.debug("Rust kernel benchmark skipped: %s", e)

        # Fallback: Python scalar benchmark
        if not results:
            start = time.time()
            for _ in range(10):
                _scalar_ternary_gemv(weights_packed, activations, m, k)
            elapsed = time.time() - start
            tps = 10 / elapsed if elapsed > 0 else 0
            results.append(KernelBenchmark(
                kernel_name="python_scalar",
                tokens_per_second=tps,
                latency_ms=(elapsed / 10) * 1000,
                elements_per_second=(10 * m * k) / elapsed if elapsed > 0 else 0,
                passed=True,
            ))

        return results

    def save_cache(self) -> bool:
        """Persist tuning report for next session."""
        try:
            data = self.report.to_dict()
            _TUNER_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_TUNER_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except (OSError, ValueError) as e:
            logger.warning("Failed to save tuner cache: %s", e)
            return False

    def load_cache(self) -> TunerReport | None:
        """Load previously saved tuning report."""
        if not _TUNER_CACHE_PATH.exists():
            return None
        try:
            with open(_TUNER_CACHE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            return TunerReport(**{
                k: v for k, v in data.items()
                if k in TunerReport.__dataclass_fields__
            })
        except Exception as e:
            logger.warning("Failed to load tuner cache: %s", e)
            return None

    def get_report(self) -> dict[str, Any]:
        """Get full tuning report for MCP tool / status display."""
        report = self.report
        result = report.to_dict()
        result["applied"] = self._applied
        result["cache_path"] = str(_TUNER_CACHE_PATH)
        result["has_cache"] = _TUNER_CACHE_PATH.exists()
        return result

    def refresh(self) -> None:
        """Force re-detection of hardware and recompute tuning."""
        self._profile = None
        self._report = None
        self._applied = False


def _scalar_ternary_gemv(
    weights_packed: list[int], activations: list[float], m: int, k: int
) -> list[float]:
    """Pure Python scalar ternary GEMV fallback for benchmarking."""
    output = [0.0] * m
    words_per_row = (k + 15) // 16
    for i in range(m):
        s = 0.0
        for w in range(words_per_row):
            word = weights_packed[i * words_per_row + w]
            base = w * 16
            for j in range(16):
                idx = base + j
                if idx >= k:
                    break
                bits = (word >> (j * 2)) & 0b11
                if bits == 0b01:
                    s += activations[idx]
                elif bits == 0b10:
                    s -= activations[idx]
        output[i] = s
    return output


# ── Singleton ────────────────────────────────────────────────────────

_tuner: InferenceTuner | None = None


def get_inference_tuner() -> InferenceTuner:
    """Get the global InferenceTuner singleton."""
    global _tuner
    if _tuner is None:
        _tuner = InferenceTuner()
    return _tuner
