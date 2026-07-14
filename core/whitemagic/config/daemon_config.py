# ruff: noqa: BLE001
"""Daemon configuration — single source of truth for WhiteMagic settings.

All defaults are local-only. No telemetry, no cloud, no mesh unless
explicitly enabled by the user.

Configuration is loaded from (in priority order):
1. Environment variables (WM_*)
2. ~/.whitemagic/config.yaml (user config)
3. Built-in defaults
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from whitemagic.config.paths import WM_ROOT

import logging
logger = logging.getLogger(__name__)

CONFIG_FILE = WM_ROOT / "config.yaml"


@dataclass
class DaemonConfig:
    """WhiteMagic daemon configuration."""

    # Master switch
    local_only: bool = True

    # Network
    mesh_enabled: bool = False
    cloud_api: str | None = None
    telemetry: bool = False
    p2p_discovery: bool = False

    # Inference
    inference_backend: str = "auto"  # (renamed to llama.cpp)
    inference_model: str | None = None
    cloud_fallback: bool = False
    idle_timeout_s: int = 300

    # Storage
    storage_root: str = "~/.whitemagic"
    encrypt_at_rest: bool = False

    # Loops
    beta_interval_s: float = 5.0
    alpha_interval_s: float = 30.0
    theta_interval_s: float = 300.0
    delta_interval_s: float = 3600.0

    # Citta
    citta_heartbeat_s: float = 30.0
    citta_idle_threshold_s: float = 300.0
    citta_buffer_size: int = 100

    # Gateway
    socket_path: str = "/tmp/whitemagic/wm.sock"
    tcp_port: int = 4730
    enable_tcp: bool = False

    # Privacy
    privacy_mode: str = "local_only"

    def to_dict(self) -> dict[str, Any]:
        return {
            "local_only": self.local_only,
            "network": {
                "mesh_enabled": self.mesh_enabled,
                "cloud_api": self.cloud_api,
                "telemetry": self.telemetry,
                "p2p_discovery": self.p2p_discovery,
            },
            "inference": {
                "backend": self.inference_backend,
                "model": self.inference_model,
                "cloud_fallback": self.cloud_fallback,
                "idle_timeout_s": self.idle_timeout_s,
            },
            "storage": {
                "root": self.storage_root,
                "encrypt": self.encrypt_at_rest,
            },
            "loops": {
                "beta_interval_s": self.beta_interval_s,
                "alpha_interval_s": self.alpha_interval_s,
                "theta_interval_s": self.theta_interval_s,
                "delta_interval_s": self.delta_interval_s,
            },
            "citta": {
                "heartbeat_s": self.citta_heartbeat_s,
                "idle_threshold_s": self.citta_idle_threshold_s,
                "buffer_size": self.citta_buffer_size,
            },
            "gateway": {
                "socket_path": self.socket_path,
                "tcp_port": self.tcp_port,
                "enable_tcp": self.enable_tcp,
            },
            "privacy_mode": self.privacy_mode,
        }

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        d = self.to_dict()
        lines = ["# WhiteMagic Daemon Configuration"]
        lines.append("# All defaults are local-only. Zero network egress.")
        lines.append("")
        lines.append(f"local_only: {d['local_only']}")
        lines.append("")
        lines.append("network:")
        for k, v in d["network"].items():
            lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append("inference:")
        for k, v in d["inference"].items():
            lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append("storage:")
        for k, v in d["storage"].items():
            lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append("loops:")
        for k, v in d["loops"].items():
            lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append("citta:")
        for k, v in d["citta"].items():
            lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append("gateway:")
        for k, v in d["gateway"].items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines) + "\n"


def load_config() -> DaemonConfig:
    """Load configuration from env vars, config file, and defaults."""
    config = DaemonConfig()

    # Override from environment variables
    if os.environ.get("WM_LOCAL_ONLY", "").lower() in ("0", "false", "no"):
        config.local_only = False
    if os.environ.get("WM_MESH_ENABLED", "").lower() in ("1", "true", "yes"):
        config.mesh_enabled = True
    if os.environ.get("WM_CLOUD_API"):
        config.cloud_api = os.environ["WM_CLOUD_API"]
    if os.environ.get("WM_TELEMETRY", "").lower() in ("1", "true", "yes"):
        config.telemetry = True
    if os.environ.get("WM_INFERENCE_BACKEND"):
        config.inference_backend = os.environ["WM_INFERENCE_BACKEND"]
    if os.environ.get("WM_INFERENCE_MODEL"):
        config.inference_model = os.environ["WM_INFERENCE_MODEL"]
    if os.environ.get("WM_PRIVACY_MODE"):
        config.privacy_mode = os.environ["WM_PRIVACY_MODE"]

    # Try loading YAML config file
    config_path = Path(os.environ.get("WM_CONFIG_FILE", str(CONFIG_FILE)))
    if config_path.exists():
        try:
            import yaml
            with open(config_path) as f:
                data = yaml.safe_load(f)
            if data:
                if "local_only" in data:
                    config.local_only = bool(data["local_only"])
                net = data.get("network", {})
                if "mesh_enabled" in net:
                    config.mesh_enabled = bool(net["mesh_enabled"])
                if "cloud_api" in net:
                    config.cloud_api = net["cloud_api"]
                if "telemetry" in net:
                    config.telemetry = bool(net["telemetry"])
                inf = data.get("inference", {})
                if "backend" in inf:
                    config.inference_backend = inf["backend"]
                if "model" in inf:
                    config.inference_model = inf["model"]
        except Exception:
            logger.debug("Ignored Exception in daemon_config.py:184")

    return config


def save_default_config() -> None:
    """Write the default config file if it doesn't exist."""
    config_path = Path(os.environ.get("WM_CONFIG_FILE", str(CONFIG_FILE)))
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config = DaemonConfig()
        config_path.write_text(config.to_yaml())
