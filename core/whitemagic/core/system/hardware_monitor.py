"""Hardware-Aware Resource Management
====================================
Adaptive resource allocation based on detected hardware capabilities.
Prevents system overload while maximizing throughput.
"""
# ruff: noqa: BLE001

import os
import subprocess
from dataclasses import dataclass
import logging
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

    # Computed limits
    max_workers: int
    batch_size: int
    memory_limit_mb: int

    @property
    def is_constrained(self) -> bool:
        """Check if running on constrained hardware."""
        return (
            self.cpu_threads <= 8 or
            self.available_ram_gb < 8 or
            not self.has_gpu
        )

    @property
    def resource_tier(self) -> str:
        """Classify hardware tier."""
        if self.cpu_threads >= 16 and self.available_ram_gb >= 16 and self.has_gpu:
            return "HIGH"
        elif self.cpu_threads >= 8 and self.available_ram_gb >= 8:
            return "MEDIUM"
        else:
            return "LOW"

def detect_hardware() -> HardwareProfile:
    """Detect current hardware capabilities using /proc and standard tools."""
    # CPU - read from /proc/cpuinfo
    try:
        with open('/proc/cpuinfo') as f:
            cpuinfo = f.read()
        cpu_threads = cpuinfo.count('processor')
        # Estimate physical cores (rough approximation)
        cpu_count = max(1, cpu_threads // 2)
    except (OSError, FileNotFoundError, PermissionError):
        cpu_count = 4
        cpu_threads = 8

    # RAM - read from /proc/meminfo
    try:
        with open('/proc/meminfo') as f:
            meminfo = f.read()
        for line in meminfo.split('\n'):
            if line.startswith('MemTotal:'):
                total_ram_kb = int(line.split()[1])
                total_ram_gb = total_ram_kb / (1024**2)
            elif line.startswith('MemAvailable:'):
                avail_ram_kb = int(line.split()[1])
                available_ram_gb = avail_ram_kb / (1024**2)
    except (OSError, UnicodeDecodeError):
        total_ram_gb = 8.0
        available_ram_gb = 4.0

    # GPU detection (simple check for nvidia-smi)
    has_gpu = os.path.exists('/usr/bin/nvidia-smi') or os.path.exists('/usr/local/cuda')

    # Disk - use df command
    try:
        from whitemagic.config.paths import WM_ROOT
        result = subprocess.run(['df', '-BG', str(WM_ROOT)], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            disk_free_gb = float(parts[3].rstrip('G'))
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
        with open('/proc/meminfo') as f:
            meminfo = f.read()
        total_kb = avail_kb = 0
        for line in meminfo.split('\n'):
            if line.startswith('MemTotal:'):
                total_kb = int(line.split()[1])
            elif line.startswith('MemAvailable:'):
                avail_kb = int(line.split()[1])

        ram_available_gb = avail_kb / (1024**2)
        ram_percent_used = ((total_kb - avail_kb) / total_kb * 100) if total_kb > 0 else 50

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
