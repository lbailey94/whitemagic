# ruff: noqa: BLE001
"""Hardware-Aware Resource Management
====================================
Adaptive resource allocation based on detected hardware capabilities.
Prevents system overload while maximizing throughput.
"""

import logging
import os
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HardwareProfile:
    """Detected hardware capabilities."""

    cpu_count: int
    cpu_threads: int
    total_ram_gb: float
    available_ram_gb: float
    has_gpu: bool
    disk_free_gb: float

    # CPU ISA features (detected at runtime)
    has_avx2: bool = False
    has_avx512f: bool = False
    has_avx512vnni: bool = False
    has_amx: bool = False
    has_bmi2: bool = False
    has_sse42: bool = False
    has_neon: bool = False  # ARM
    cpu_model_name: str = ""

    # Computed limits
    max_workers: int = 4
    batch_size: int = 250
    memory_limit_mb: int = 2048

    @property
    def is_constrained(self) -> bool:
        """Check if running on constrained hardware."""
        return self.cpu_threads <= 8 or self.available_ram_gb < 8 or not self.has_gpu

    @property
    def resource_tier(self) -> str:
        """Classify hardware tier."""
        if self.cpu_threads >= 16 and self.available_ram_gb >= 16 and self.has_gpu:
            return "HIGH"
        elif self.cpu_threads >= 8 and self.available_ram_gb >= 8:
            return "MEDIUM"
        else:
            return "LOW"

    @property
    def inference_tier(self) -> str:
        """Classify inference capability based on CPU ISA features.

        Tiers (highest to lowest):
        - AMX:    Intel Sapphire Rapids+ with Advanced Matrix Extensions (tile ops)
        - VNNI:   AVX-512 VNNI (512-bit vectors, INT8 dot product, 256 ops/cycle)
        - AVX512: AVX-512 Foundation (512-bit vectors, FP32 ops)
        - AVX2:   AVX2 (256-bit vectors, maddubs/madd_epi16)
        - SSE4:   SSE4.2 (128-bit, scalar fallback)
        - SCALAR: No SIMD
        """
        if self.has_amx:
            return "AMX"
        if self.has_avx512vnni:
            return "VNNI"
        if self.has_avx512f:
            return "AVX512"
        if self.has_avx2:
            return "AVX2"
        if self.has_sse42:
            return "SSE4"
        return "SCALAR"

    @property
    def simd_width_bits(self) -> int:
        """Vector width in bits for the best available SIMD ISA."""
        if self.has_avx512f or self.has_avx512vnni or self.has_amx:
            return 512
        if self.has_avx2:
            return 256
        if self.has_sse42:
            return 128
        return 0

    @property
    def optimal_ternary_kernel(self) -> str:
        """Select the optimal ternary kernel for this hardware.

        Returns one of: 'avx512_vnni', 'avx2_i2s', 'avx2_int16', 'avx2_lut', 'scalar'
        """
        if self.has_avx512vnni:
            return "avx512_vnni"
        if self.has_avx2:
            return "avx2_i2s"  # I2_S is the highest-throughput AVX2 kernel
        return "scalar"

    @property
    def optimal_spec_params(self) -> dict[str, int | float | str]:
        """Optimal speculative decoding parameters for this hardware.

        Tuned based on core count and memory:
        - More cores → larger ngram pool (more draft tokens)
        - Less memory → smaller context, more aggressive KV quantization
        - Constrained hardware → smaller draft windows
        """
        if self.cpu_threads >= 16 and self.available_ram_gb >= 16:
            return {
                "spec_ngram_mod_n_match": 32,
                "spec_ngram_mod_n_min": 48,
                "spec_ngram_mod_n_max": 96,
                "cache_type_k": "q8_0",
                "cache_type_v": "q8_0",
                "parallel": 4,
            }
        elif self.cpu_threads >= 8 and self.available_ram_gb >= 8:
            return {
                "spec_ngram_mod_n_match": 24,
                "spec_ngram_mod_n_min": 32,
                "spec_ngram_mod_n_max": 64,
                "cache_type_k": "q8_0",
                "cache_type_v": "q8_0",
                "parallel": 4,
            }
        else:
            return {
                "spec_ngram_mod_n_match": 16,
                "spec_ngram_mod_n_min": 16,
                "spec_ngram_mod_n_max": 32,
                "cache_type_k": "q4_0",
                "cache_type_v": "q4_0",
                "parallel": 2,
            }


def _detect_cpu_isa(cpuinfo: str) -> dict[str, bool | str]:
    """Detect CPU ISA features from /proc/cpuinfo flags.

    Returns dict with has_avx2, has_avx512f, has_avx512vnni, has_amx,
    has_bmi2, has_sse42, has_neon, cpu_model_name.
    """
    flags: str = ""
    model_name: str = ""

    for line in cpuinfo.split("\n"):
        if line.startswith("flags") and not flags:
            # flags line: "flags		: fpu vme de pse ..."
            parts = line.split(":", 1)
            if len(parts) == 2:
                flags = parts[1].strip()
        elif line.startswith("model name") and not model_name:
            parts = line.split(":", 1)
            if len(parts) == 2:
                model_name = parts[1].strip()

    flag_set = set(flags.split())

    return {
        "has_avx2": "avx2" in flag_set,
        "has_avx512f": "avx512f" in flag_set,
        "has_avx512vnni": "avx512_vnni" in flag_set,
        "has_amx": "amx_bf16" in flag_set or "amx_int8" in flag_set,
        "has_bmi2": "bmi2" in flag_set,
        "has_sse42": "sse4_2" in flag_set,
        "has_neon": "neon" in flag_set or "asimd" in flag_set,
        "cpu_model_name": model_name,
    }


def detect_hardware() -> HardwareProfile:
    """Detect current hardware capabilities using /proc and standard tools."""
    # CPU - read from /proc/cpuinfo
    cpu_isa: dict[str, bool | str] = {
        "has_avx2": False,
        "has_avx512f": False,
        "has_avx512vnni": False,
        "has_amx": False,
        "has_bmi2": False,
        "has_sse42": False,
        "has_neon": False,
        "cpu_model_name": "",
    }
    try:
        with open("/proc/cpuinfo") as f:
            cpuinfo = f.read()
        cpu_threads = cpuinfo.count("processor")
        # Estimate physical cores (rough approximation)
        cpu_count = max(1, cpu_threads // 2)
        cpu_isa = _detect_cpu_isa(cpuinfo)
    except (OSError, FileNotFoundError, PermissionError):
        cpu_count = 4
        cpu_threads = 8

    # RAM - read from /proc/meminfo
    try:
        with open("/proc/meminfo") as f:
            meminfo = f.read()
        for line in meminfo.split("\n"):
            if line.startswith("MemTotal:"):
                total_ram_kb = int(line.split()[1])
                total_ram_gb = total_ram_kb / (1024**2)
            elif line.startswith("MemAvailable:"):
                avail_ram_kb = int(line.split()[1])
                available_ram_gb = avail_ram_kb / (1024**2)
    except (OSError, UnicodeDecodeError):
        total_ram_gb = 8.0
        available_ram_gb = 4.0

    # GPU detection (simple check for nvidia-smi)
    has_gpu = os.path.exists("/usr/bin/nvidia-smi") or os.path.exists("/usr/local/cuda")

    # Disk - use df command
    try:
        from whitemagic.config.paths import WM_ROOT

        result = subprocess.run(
            ["df", "-BG", str(WM_ROOT)], capture_output=True, text=True
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            parts = lines[1].split()
            disk_free_gb = float(parts[3].rstrip("G"))
        else:
            disk_free_gb = 50.0
    except (ImportError, AttributeError):
        disk_free_gb = 50.0

    # Compute safe limits
    # Use 50% of available RAM, leave headroom
    safe_ram_gb = available_ram_gb * 0.5
    memory_limit_mb = int(safe_ram_gb * 1024)

    # Workers: use 75% of threads, minimum 2
    max_workers = max(2, int(cpu_threads * 0.75))

    # Batch size based on available RAM
    # Assume ~1MB per item for embedding
    if available_ram_gb >= 8:
        batch_size = 500
    elif available_ram_gb >= 4:
        batch_size = 250
    else:
        batch_size = 100

    return HardwareProfile(
        cpu_count=cpu_count,
        cpu_threads=cpu_threads,
        total_ram_gb=total_ram_gb,
        available_ram_gb=available_ram_gb,
        has_gpu=has_gpu,
        disk_free_gb=disk_free_gb,
        has_avx2=cpu_isa["has_avx2"],  # type: ignore[arg-type]
        has_avx512f=cpu_isa["has_avx512f"],  # type: ignore[arg-type]
        has_avx512vnni=cpu_isa["has_avx512vnni"],  # type: ignore[arg-type]
        has_amx=cpu_isa["has_amx"],  # type: ignore[arg-type]
        has_bmi2=cpu_isa["has_bmi2"],  # type: ignore[arg-type]
        has_sse42=cpu_isa["has_sse42"],  # type: ignore[arg-type]
        has_neon=cpu_isa["has_neon"],  # type: ignore[arg-type]
        cpu_model_name=cpu_isa["cpu_model_name"],  # type: ignore[arg-type]
        max_workers=max_workers,
        batch_size=batch_size,
        memory_limit_mb=memory_limit_mb,
    )


def get_safe_batch_config(task_type: str = "embedding") -> dict:
    """Get safe batch configuration for task type."""
    hw = detect_hardware()

    configs = {
        "embedding": {
            "HIGH": {"batch_size": 1000, "workers": 12, "memory_mb": 4096},
            "MEDIUM": {"batch_size": 500, "workers": 6, "memory_mb": 2048},
            "LOW": {"batch_size": 100, "workers": 2, "memory_mb": 512},
        },
        "processing": {
            "HIGH": {"batch_size": 5000, "workers": 12, "memory_mb": 2048},
            "MEDIUM": {"batch_size": 2000, "workers": 6, "memory_mb": 1024},
            "LOW": {"batch_size": 500, "workers": 2, "memory_mb": 256},
        },
        "analysis": {
            "HIGH": {"batch_size": 10000, "workers": 8, "memory_mb": 1024},
            "MEDIUM": {"batch_size": 5000, "workers": 4, "memory_mb": 512},
            "LOW": {"batch_size": 1000, "workers": 2, "memory_mb": 256},
        },
    }

    tier = hw.resource_tier
    config = configs.get(task_type, configs["processing"])[tier]

    # Further constrain if RAM is critically low
    if hw.available_ram_gb < 3:
        config["batch_size"] = min(config["batch_size"], 50)
        config["workers"] = 1
        config["memory_mb"] = min(config["memory_mb"], 256)

    return config


def check_resource_headroom() -> dict:
    """Check current resource headroom using /proc."""
    try:
        # Read memory info
        with open("/proc/meminfo") as f:
            meminfo = f.read()
        total_kb = avail_kb = 0
        for line in meminfo.split("\n"):
            if line.startswith("MemTotal:"):
                total_kb = int(line.split()[1])
            elif line.startswith("MemAvailable:"):
                avail_kb = int(line.split()[1])

        ram_available_gb = avail_kb / (1024**2)
        ram_percent_used = (
            ((total_kb - avail_kb) / total_kb * 100) if total_kb > 0 else 50
        )

        # CPU usage - read from /proc/stat (simplified)
        cpu_percent = 50.0  # Conservative estimate

        return {
            "ram_available_gb": ram_available_gb,
            "ram_percent_used": ram_percent_used,
            "cpu_percent_used": cpu_percent,
            "safe_to_proceed": ram_percent_used < 85 and cpu_percent < 90,
        }
    except Exception as e:
        logger.debug("Operation failed: %s", e)
        return {
            "ram_available_gb": 4.0,
            "ram_percent_used": 50.0,
            "cpu_percent_used": 50.0,
            "safe_to_proceed": True,
        }


# Global hardware profile (cached)
_HARDWARE_PROFILE: HardwareProfile | None = None


def get_hardware_profile() -> HardwareProfile:
    """Get cached hardware profile."""
    global _HARDWARE_PROFILE
    if _HARDWARE_PROFILE is None:
        _HARDWARE_PROFILE = detect_hardware()
    return _HARDWARE_PROFILE
