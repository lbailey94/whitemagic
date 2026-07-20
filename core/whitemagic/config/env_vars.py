"""Centralized environment variable registry for WhiteMagic.

Single source of truth for all ``WM_*`` environment variables.  Each entry
declares the variable name, default value, type, and a short description.

Usage::

    from whitemagic.config.env_vars import get_env, get_env_int, get_env_bool

    host = get_env("WM_LLAMA_HOST", "127.0.0.1")
    port = get_env_int("WM_LLAMA_PORT", 8080)
    debug = get_env_bool("WM_DEBUG", False)

This module is the canonical place to read ``WM_*`` env vars.  The ratchet
script ``scripts/check_env_var_ratchet.sh`` prevents new ``os.getenv("WM_")``
calls outside ``config/``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EnvVarSpec:
    """Specification for a single WM_* environment variable."""

    name: str
    default: Any
    var_type: str  # "str", "int", "float", "bool", "path"
    description: str
    alias: str | None = None  # WHITEMAGIC_* alias if applicable


# ---------------------------------------------------------------------------
# Registry — all known WM_* env vars.
# New vars should be added here rather than read via os.getenv directly.
# ---------------------------------------------------------------------------
REGISTRY: dict[str, EnvVarSpec] = {
    # ── Core runtime ──────────────────────────────────────────────────
    "WM_STATE_ROOT": EnvVarSpec("WM_STATE_ROOT", "~/.whitemagic", "path", "Root directory for WhiteMagic state files"),
    "WM_ENV": EnvVarSpec("WM_ENV", "development", "str", "Environment name", alias="WHITEMAGIC_ENV"),
    "WM_DEBUG": EnvVarSpec("WM_DEBUG", False, "bool", "Enable debug mode", alias="WHITEMAGIC_DEBUG"),
    "WM_SILENT_INIT": EnvVarSpec("WM_SILENT_INIT", False, "bool", "Suppress non-essential init output"),
    "WM_SKIP_POLYGLOT": EnvVarSpec("WM_SKIP_POLYGLOT", False, "bool", "Skip polyglot bridge initialization"),
    "WM_LOCAL_ONLY": EnvVarSpec("WM_LOCAL_ONLY", True, "bool", "Restrict to local-only operation"),
    "WM_PRIVACY_MODE": EnvVarSpec("WM_PRIVACY_MODE", "local_only", "str", "Privacy mode setting"),
    "WM_FALLBACK_TO_CWD": EnvVarSpec("WM_FALLBACK_TO_CWD", False, "bool", "Fall back to CWD for state root"),
    "WM_NO_UPDATE_CHECK": EnvVarSpec("WM_NO_UPDATE_CHECK", False, "bool", "Disable update checking"),
    "WM_MODE": EnvVarSpec("WM_MODE", "local", "str", "WhiteMagic operation mode", alias="WHITEMAGIC_MODE"),
    "WM_CONFIG_FILE": EnvVarSpec("WM_CONFIG_FILE", "", "path", "Config file path"),
    "WM_CONFIG_ROOT": EnvVarSpec("WM_CONFIG_ROOT", "", "path", "Config root directory"),
    "WM_BASE_PATH": EnvVarSpec("WM_BASE_PATH", "", "path", "Base path for WhiteMagic installation"),
    "WM_AUTO_INIT": EnvVarSpec("WM_AUTO_INIT", False, "bool", "Auto-initialize on startup", alias="WHITEMAGIC_AUTO_INIT"),

    # ── Database / storage ────────────────────────────────────────────
    "WM_DB_PATH": EnvVarSpec("WM_DB_PATH", "", "path", "SQLite database path"),
    "WM_DATA_DIR": EnvVarSpec("WM_DATA_DIR", "", "path", "Data directory", alias="WHITEMAGIC_DATA_DIR"),
    "WM_DATABASE_URL": EnvVarSpec("WM_DATABASE_URL", "", "str", "Database URL", alias="WHITEMAGIC_DATABASE_URL"),
    "WM_PG_HOST": EnvVarSpec("WM_PG_HOST", "", "str", "PostgreSQL host"),
    "WM_PG_PORT": EnvVarSpec("WM_PG_PORT", "5432", "int", "PostgreSQL port"),
    "WM_PG_DB": EnvVarSpec("WM_PG_DB", "", "str", "PostgreSQL database name"),
    "WM_PG_USER": EnvVarSpec("WM_PG_USER", "", "str", "PostgreSQL user"),
    "WM_PG_PASSWORD": EnvVarSpec("WM_PG_PASSWORD", "", "str", "PostgreSQL password"),

    # ── Redis / cache ─────────────────────────────────────────────────
    "WM_REDIS_URL": EnvVarSpec("WM_REDIS_URL", "", "str", "Redis connection URL", alias="WHITEMAGIC_REDIS_URL"),
    "WM_REDIS_CONNECT_TIMEOUT": EnvVarSpec("WM_REDIS_CONNECT_TIMEOUT", 1.0, "float", "Redis connect timeout", alias="WHITEMAGIC_REDIS_CONNECT_TIMEOUT"),
    "WM_REDIS_SOCKET_TIMEOUT": EnvVarSpec("WM_REDIS_SOCKET_TIMEOUT", 1.0, "float", "Redis socket timeout", alias="WHITEMAGIC_REDIS_SOCKET_TIMEOUT"),
    "WM_REDIS_PROBE_TIMEOUT": EnvVarSpec("WM_REDIS_PROBE_TIMEOUT", 0.5, "float", "Redis probe timeout", alias="WHITEMAGIC_REDIS_PROBE_TIMEOUT"),

    # ── API / network ─────────────────────────────────────────────────
    "WM_API_HOST": EnvVarSpec("WM_API_HOST", "127.0.0.1", "str", "API host", alias="WHITEMAGIC_API_HOST"),
    "WM_API_PORT": EnvVarSpec("WM_API_PORT", "8000", "int", "API port", alias="WHITEMAGIC_API_PORT"),
    "WM_SECRET_KEY": EnvVarSpec("WM_SECRET_KEY", "", "str", "Secret key for signing", alias="WHITEMAGIC_SECRET_KEY"),
    "WM_MESH_ENABLED": EnvVarSpec("WM_MESH_ENABLED", False, "bool", "Enable mesh networking"),
    "WM_CLOUD_API": EnvVarSpec("WM_CLOUD_API", "", "str", "Cloud API endpoint"),
    "WM_TELEMETRY": EnvVarSpec("WM_TELEMETRY", False, "bool", "Enable telemetry"),
    "WM_SOCKET_PATH": EnvVarSpec("WM_SOCKET_PATH", "/tmp/whitemagic/wm.sock", "path", "Unix socket path"),
    "WM_TCP_ADDR": EnvVarSpec("WM_TCP_ADDR", "", "str", "TCP address for mesh"),
    "WM_HOSTS": EnvVarSpec("WM_HOSTS", "", "str", "Comma-separated host list", alias="WHITEMAGIC_HOSTS"),

    # ── Inference / LLM ───────────────────────────────────────────────
    "WM_INFERENCE_BACKEND": EnvVarSpec("WM_INFERENCE_BACKEND", "auto", "str", "Inference backend"),
    "WM_INFERENCE_MODEL": EnvVarSpec("WM_INFERENCE_MODEL", "", "str", "Default inference model"),
    "WM_LLM_MODEL": EnvVarSpec("WM_LLM_MODEL", "", "str", "Local LLM model name"),
    "WM_LLAMA_HOST": EnvVarSpec("WM_LLAMA_HOST", "127.0.0.1", "str", "Llama server host"),
    "WM_LLAMA_PORT": EnvVarSpec("WM_LLAMA_PORT", "8080", "int", "Llama server port"),
    "WM_LLAMA_SERVER": EnvVarSpec("WM_LLAMA_SERVER", "llama-server", "str", "Llama server binary path"),
    "WM_LLAMA_FG_MODEL": EnvVarSpec("WM_LLAMA_FG_MODEL", "", "str", "Foreground LLM model"),
    "WM_LLAMA_BG_MODEL": EnvVarSpec("WM_LLAMA_BG_MODEL", "", "str", "Background LLM model"),
    "WM_LLAMA_FG_PORT": EnvVarSpec("WM_LLAMA_FG_PORT", "8080", "int", "Foreground LLM port"),
    "WM_LLAMA_BG_PORT": EnvVarSpec("WM_LLAMA_BG_PORT", "8081", "int", "Background LLM port"),
    "WM_LLAMA_SMALL_PORT": EnvVarSpec("WM_LLAMA_SMALL_PORT", "8091", "int", "Small model LLM port"),
    "WM_LLAMA_LARGE_PORT": EnvVarSpec("WM_LLAMA_LARGE_PORT", "8090", "int", "Large model LLM port"),
    "WM_LLAMA_DRAFT_PORT": EnvVarSpec("WM_LLAMA_DRAFT_PORT", "8092", "int", "Draft model LLM port"),
    "WM_LLAMA_MODEL": EnvVarSpec("WM_LLAMA_MODEL", "", "str", "Llama model name"),
    "WM_SPEC_VERIFY_MODEL": EnvVarSpec("WM_SPEC_VERIFY_MODEL", "bitnet-2b4t", "str", "Speculative decoding verify model"),
    "WM_ALLOW_MODEL_DOWNLOAD": EnvVarSpec("WM_ALLOW_MODEL_DOWNLOAD", False, "bool", "Allow model downloads"),
    "WM_ENABLE_LOCAL_MODELS": EnvVarSpec("WM_ENABLE_LOCAL_MODELS", False, "bool", "Enable local models", alias="WHITEMAGIC_ENABLE_LOCAL_MODELS"),
    "WM_ENABLE_BITNET": EnvVarSpec("WM_ENABLE_BITNET", False, "bool", "Enable BitNet bridge", alias="WHITEMAGIC_ENABLE_BITNET"),
    "WM_AUTO_OPTIMIZE": EnvVarSpec("WM_AUTO_OPTIMIZE", False, "bool", "Enable auto-optimization loop"),
    "WM_OPTIMIZE_INTERVAL": EnvVarSpec("WM_OPTIMIZE_INTERVAL", 300, "int", "Auto-optimizer interval in seconds"),
    "WM_AUTONOMIC_ENABLED": EnvVarSpec("WM_AUTONOMIC_ENABLED", False, "bool", "Enable BitMamba autonomic mode"),
    "WM_MODEL_MESH": EnvVarSpec("WM_MODEL_MESH", False, "bool", "Enable model mesh"),
    "WM_MODEL_SMALL": EnvVarSpec("WM_MODEL_SMALL", "", "str", "Small model name"),
    "WM_MODEL_LARGE": EnvVarSpec("WM_MODEL_LARGE", "", "str", "Large model name"),
    "WM_MODEL_QWEN3_1_7B": EnvVarSpec("WM_MODEL_QWEN3_1_7B", "", "str", "Qwen3 1.7B model path"),
    "WM_MODEL_QWEN3_4B": EnvVarSpec("WM_MODEL_QWEN3_4B", "", "str", "Qwen3 4B model path"),
    "WM_MODEL_QWEN25_1_5B": EnvVarSpec("WM_MODEL_QWEN25_1_5B", "", "str", "Qwen2.5 1.5B model path"),
    "WM_MODEL_PHI4_MINI": EnvVarSpec("WM_MODEL_PHI4_MINI", "", "str", "Phi4 Mini model path"),
    "WM_MODEL_SMOLLM2_360M": EnvVarSpec("WM_MODEL_SMOLLM2_360M", "", "str", "SmolLM2 360M model path"),
    "WM_MODEL_LLAMA32_1B": EnvVarSpec("WM_MODEL_LLAMA32_1B", "", "str", "Llama 3.2 1B model path"),
    "WM_HUBEN_MODEL": EnvVarSpec("WM_HUBEN_MODEL", "", "str", "Huben model name"),
    "WM_XIANFENG_MODEL": EnvVarSpec("WM_XIANFENG_MODEL", "", "str", "Xianfeng model name"),
    "WM_WEIWUZU_MODEL": EnvVarSpec("WM_WEIWUZU_MODEL", "", "str", "Weiwuzu model name"),

    # ── Tools / dispatch ──────────────────────────────────────────────
    "WM_TOOL_TIMEOUT": EnvVarSpec("WM_TOOL_TIMEOUT", "30", "str", "Default tool timeout"),
    "WM_TOOL_RUNTIME": EnvVarSpec("WM_TOOL_RUNTIME", False, "bool", "Tool runtime mode"),
    "WM_TOOL_DISPATCH_TIMEOUT_S": EnvVarSpec("WM_TOOL_DISPATCH_TIMEOUT_S", 30.0, "float", "Tool dispatch timeout"),
    "WM_TOOL_TIMEOUT_AGENT_GENERATION_S": EnvVarSpec("WM_TOOL_TIMEOUT_AGENT_GENERATION_S", 45.0, "float", "Agent generation timeout"),
    "WM_TOOL_TIMEOUT_COLD_STATUS_S": EnvVarSpec("WM_TOOL_TIMEOUT_COLD_STATUS_S", 15.0, "float", "Cold status timeout"),
    "WM_TOOL_TIMEOUT_HEALTH_CHECK_S": EnvVarSpec("WM_TOOL_TIMEOUT_HEALTH_CHECK_S", 30.0, "float", "Health check timeout"),
    "WM_TOOL_TIMEOUT_LOCAL_GENERATION_S": EnvVarSpec("WM_TOOL_TIMEOUT_LOCAL_GENERATION_S", 30.0, "float", "Local generation timeout"),
    "WM_BENCHMARK_MODE": EnvVarSpec("WM_BENCHMARK_MODE", False, "bool", "Benchmark mode"),
    "WM_BENCHMARK_QUIET": EnvVarSpec("WM_BENCHMARK_QUIET", False, "bool", "Suppress benchmark output"),
    "WM_PATTERN_GUARD": EnvVarSpec("WM_PATTERN_GUARD", True, "bool", "Enable pattern guard"),
    "WM_CODE_NUDGE": EnvVarSpec("WM_CODE_NUDGE", True, "bool", "Enable code nudge"),
    "WM_CACHE_PRIVATE_MEMORY": EnvVarSpec("WM_CACHE_PRIVATE_MEMORY", False, "bool", "Cache private memory"),
    "WM_ERROR_LEARN": EnvVarSpec("WM_ERROR_LEARN", True, "bool", "Learn from errors"),
    "WM_TRANSACTION_FIREWALL": EnvVarSpec("WM_TRANSACTION_FIREWALL", True, "bool", "Enable transaction firewall"),
    "WM_FIREWALL_FAIL_CLOSED": EnvVarSpec("WM_FIREWALL_FAIL_CLOSED", False, "bool", "Firewall fail-closed mode"),
    "WM_FIREWALL_MAINTENANCE": EnvVarSpec("WM_FIREWALL_MAINTENANCE", False, "bool", "Firewall maintenance mode"),
    "WM_WASM_VERIFY": EnvVarSpec("WM_WASM_VERIFY", False, "bool", "Enable WASM verification"),
    "WM_SANDBOX_ENABLED": EnvVarSpec("WM_SANDBOX_ENABLED", True, "bool", "Enable sandboxing"),
    "WM_SEMANTIC_CACHE_EMBEDDINGS": EnvVarSpec("WM_SEMANTIC_CACHE_EMBEDDINGS", False, "bool", "Enable semantic cache embeddings"),
    "WM_SESSION_RECORD": EnvVarSpec("WM_SESSION_RECORD", False, "bool", "Enable session recording"),
    "WM_SESSION_ID": EnvVarSpec("WM_SESSION_ID", "", "str", "Session ID"),
    "WM_VECTORIZED": EnvVarSpec("WM_VECTORIZED", False, "bool", "Enable vectorized execution"),
    "WM_RD_MODE": EnvVarSpec("WM_RD_MODE", "", "str", "R&D mode"),
    "WM_RESONANCE": EnvVarSpec("WM_RESONANCE", "", "str", "Resonance mode"),
    "WM_SENSORIUM": EnvVarSpec("WM_SENSORIUM", True, "bool", "Enable sensorium"),
    "WM_SENSORIUM_ALL": EnvVarSpec("WM_SENSORIUM_ALL", False, "bool", "Enable all sensorium sensors"),
    "WM_BROKER_STATUS_TIMEOUT": EnvVarSpec("WM_BROKER_STATUS_TIMEOUT", 1.5, "float", "Broker status timeout", alias="WHITEMAGIC_BROKER_STATUS_TIMEOUT"),
    "WM_ABSTENTION_THRESHOLD": EnvVarSpec("WM_ABSTENTION_THRESHOLD", "", "str", "Memory abstention threshold"),
    "WM_SKIP_HOLO_INDEX": EnvVarSpec("WM_SKIP_HOLO_INDEX", False, "bool", "Skip holographic indexing"),
    "WM_SKIP_CONSCIOUSNESS_OBSERVE": EnvVarSpec("WM_SKIP_CONSCIOUSNESS_OBSERVE", False, "bool", "Skip consciousness observation"),
    "WM_SEQUENTIAL_OBSERVE": EnvVarSpec("WM_SEQUENTIAL_OBSERVE", False, "bool", "Sequential observation mode"),
    "WM_SECURITY_SCAN_PATH": EnvVarSpec("WM_SECURITY_SCAN_PATH", "", "path", "Security scan path"),
    "WM_CITTA_MODE": EnvVarSpec("WM_CITTA_MODE", "normal", "str", "Citta cycle mode"),

    # ── Consciousness / lifecycle ─────────────────────────────────────
    "WM_SLEEP_ENABLED": EnvVarSpec("WM_SLEEP_ENABLED", True, "bool", "Enable sleep cycle"),
    "WM_SLEEP_TIME": EnvVarSpec("WM_SLEEP_TIME", "23:00", "str", "Sleep start time"),
    "WM_WAKE_TIME": EnvVarSpec("WM_WAKE_TIME", "07:00", "str", "Wake time"),
    "WM_MAINTENANCE_APT": EnvVarSpec("WM_MAINTENANCE_APT", True, "bool", "Run apt maintenance"),
    "WM_MAINTENANCE_BACKUP": EnvVarSpec("WM_MAINTENANCE_BACKUP", True, "bool", "Run backup maintenance"),
    "WM_MAINTENANCE_DURATION_MIN": EnvVarSpec("WM_MAINTENANCE_DURATION_MIN", "10", "str", "Maintenance duration in minutes"),
    "WM_AMBIENT_INTERVAL": EnvVarSpec("WM_AMBIENT_INTERVAL", "30", "str", "Ambient sensor interval"),

    # ── Dharma / governance ───────────────────────────────────────────
    "WM_ENFORCE_DHARMA": EnvVarSpec("WM_ENFORCE_DHARMA", True, "bool", "Enforce Dharma rules", alias="WHITEMAGIC_ENFORCE_DHARMA"),
    "WM_DHARMA_STRICT": EnvVarSpec("WM_DHARMA_STRICT", False, "bool", "Strict Dharma mode", alias="WHITEMAGIC_DHARMA_STRICT"),

    # ── Concurrency ───────────────────────────────────────────────────
    "WM_MAX_WORKERS": EnvVarSpec("WM_MAX_WORKERS", "", "str", "Max workers", alias="WHITEMAGIC_MAX_WORKERS"),
    "WM_TRIGRAM_CORE_PINNING": EnvVarSpec("WM_TRIGRAM_CORE_PINNING", False, "bool", "Enable trigram core pinning"),
    "WM_TRIGRAM_RB_CAP": EnvVarSpec("WM_TRIGRAM_RB_CAP", 1048576, "int", "Trigram ring buffer capacity"),
    "WM_TRIGRAM_SHM_DIR": EnvVarSpec("WM_TRIGRAM_SHM_DIR", "/dev/shm", "path", "Trigram shared memory dir"),
    "WM_AUTO_IPC": EnvVarSpec("WM_AUTO_IPC", False, "bool", "Auto IPC bridge"),

    # ── Monitoring ────────────────────────────────────────────────────
    "WM_OTEL_ENABLED": EnvVarSpec("WM_OTEL_ENABLED", True, "bool", "Enable OpenTelemetry"),
    "WM_PROMETHEUS_ENABLED": EnvVarSpec("WM_PROMETHEUS_ENABLED", False, "bool", "Enable Prometheus"),
    "WM_PROMETHEUS_PORT": EnvVarSpec("WM_PROMETHEUS_PORT", "9090", "str", "Prometheus port"),

    # ── Shelter / execution ───────────────────────────────────────────
    "WM_SHELTER_RUNTIME": EnvVarSpec("WM_SHELTER_RUNTIME", "podman", "str", "Shelter runtime"),
    "WM_SHELTER_MAX_CONCURRENT": EnvVarSpec("WM_SHELTER_MAX_CONCURRENT", "4", "str", "Shelter max concurrent"),
    "WM_SHELTER_TIMEOUT_S": EnvVarSpec("WM_SHELTER_TIMEOUT_S", "300", "str", "Shelter timeout"),
    "WM_SHELTER_FIRECRACKER": EnvVarSpec("WM_SHELTER_FIRECRACKER", "", "str", "Firecracker binary path"),
    "WM_ENABLE_IN_PROCESS_EXEC": EnvVarSpec("WM_ENABLE_IN_PROCESS_EXEC", False, "bool", "Enable in-process exec", alias="WHITEMAGIC_ENABLE_IN_PROCESS_EXEC"),

    # ── Security ──────────────────────────────────────────────────────
    "WM_POC_APPROVED": EnvVarSpec("WM_POC_APPROVED", "", "str", "Approved PoC list"),
    "WM_POC_AUTO_APPROVE": EnvVarSpec("WM_POC_AUTO_APPROVE", False, "bool", "Auto-approve PoCs"),
    "WM_VAULT_PASSPHRASE": EnvVarSpec("WM_VAULT_PASSPHRASE", "", "str", "Vault passphrase"),
    "WM_ALLOW_CWD_PATH": EnvVarSpec("WM_ALLOW_CWD_PATH", False, "bool", "Allow CWD path", alias="WHITEMAGIC_ALLOW_CWD_PATH"),
    "WM_ALLOW_EXTERNAL_STATE_ROOT": EnvVarSpec("WM_ALLOW_EXTERNAL_STATE_ROOT", False, "bool", "Allow external state root", alias="WHITEMAGIC_ALLOW_EXTERNAL_STATE_ROOT"),
    "WM_ALLOWED_PATHS": EnvVarSpec("WM_ALLOWED_PATHS", "", "str", "Allowed paths", alias="WHITEMAGIC_ALLOWED_PATHS"),

    # ── Payments ──────────────────────────────────────────────────────
    "WM_ILP_POINTER": EnvVarSpec("WM_ILP_POINTER", "", "str", "ILP payment pointer"),
    "WM_ILP_CONNECTOR_URL": EnvVarSpec("WM_ILP_CONNECTOR_URL", "", "str", "ILP connector URL"),
    "WM_ILP_AUTH_TOKEN": EnvVarSpec("WM_ILP_AUTH_TOKEN", "", "str", "ILP auth token"),
    "WM_XRP_ADDRESS": EnvVarSpec("WM_XRP_ADDRESS", "", "str", "XRP address"),
    "WM_XRP_DEST_TAG": EnvVarSpec("WM_XRP_DEST_TAG", "", "str", "XRP destination tag"),

    # ── Acceleration / polyglot ───────────────────────────────────────
    "WM_GHC_LIB_DIR": EnvVarSpec("WM_GHC_LIB_DIR", "", "path", "GHC lib directory"),
    "WM_HS_LIB": EnvVarSpec("WM_HS_LIB", "", "path", "Haskell shared lib path"),
    "WM_GO_PREFETCH_BIN": EnvVarSpec("WM_GO_PREFETCH_BIN", "", "path", "Go prefetch binary"),
    "WM_ZIG_LIB": EnvVarSpec("WM_ZIG_LIB", "", "path", "Zig shared lib path"),
    "WM_AUTO_BUILD_RUST_BRIDGE": EnvVarSpec("WM_AUTO_BUILD_RUST_BRIDGE", True, "bool", "Auto-build Rust bridge"),

    # ── MCP / runtime ─────────────────────────────────────────────────
    "WM_MCP_COMPACT": EnvVarSpec("WM_MCP_COMPACT", "0", "str", "MCP compact level"),
    "WM_MCP_CORS_ORIGINS": EnvVarSpec("WM_MCP_CORS_ORIGINS", "", "str", "MCP CORS origins"),
    "WM_MCP_SHORT_INSTRUCTIONS": EnvVarSpec("WM_MCP_SHORT_INSTRUCTIONS", False, "bool", "Short MCP instructions"),
    "WM_MCP_PRAT": EnvVarSpec("WM_MCP_PRAT", "2", "str", "MCP PRAT level"),
    "WM_MCP_CLIENT": EnvVarSpec("WM_MCP_CLIENT", "", "str", "MCP client path"),
    "WM_MCP_LITE": EnvVarSpec("WM_MCP_LITE", False, "bool", "MCP lite mode"),
    "WM_SCHEDULER_INTERVAL": EnvVarSpec("WM_SCHEDULER_INTERVAL", "300", "str", "Scheduler interval"),
    "WM_SCHEDULER_MAX_ACTIONS": EnvVarSpec("WM_SCHEDULER_MAX_ACTIONS", "3", "str", "Scheduler max actions"),
    "WM_AUTO_SCHEDULER": EnvVarSpec("WM_AUTO_SCHEDULER", False, "bool", "Enable auto scheduler"),

    # ── Misc ──────────────────────────────────────────────────────────
    "WM_ROOT": EnvVarSpec("WM_ROOT", ".", "path", "Root path for code graph"),
    "WM_REPLAY_DIR": EnvVarSpec("WM_REPLAY_DIR", "", "path", "Replay directory"),
    "WM_REACHING_AI_KEY": EnvVarSpec("WM_REACHING_AI_KEY", "", "str", "ReachingAI API key"),
    "WM_FEATURE_RUST_STORE": EnvVarSpec("WM_FEATURE_RUST_STORE", False, "bool", "Enable Rust store"),
    "WM_MEMORY_FREQUENCY": EnvVarSpec("WM_MEMORY_FREQUENCY", "5", "str", "Auto-capture frequency", alias="WHITEMAGIC_MEMORY_FREQUENCY"),
    "WM_WORKSPACE_ID": EnvVarSpec("WM_WORKSPACE_ID", "", "str", "Workspace ID", alias="WHITEMAGIC_WORKSPACE_ID"),
    "WM_CODEGENOME_STRICT_SIGNING": EnvVarSpec("WM_CODEGENOME_STRICT_SIGNING", False, "bool", "Strict CodeGenome signing"),
    "WM_LOAD_EXAMPLE_PLUGINS": EnvVarSpec("WM_LOAD_EXAMPLE_PLUGINS", False, "bool", "Load example plugins", alias="WHITEMAGIC_LOAD_EXAMPLE_PLUGINS"),
    "WM_PYTHON": EnvVarSpec("WM_PYTHON", "", "str", "Python executable path", alias="WHITEMAGIC_PYTHON"),
    "WM_ELIXIR_MASTER": EnvVarSpec("WM_ELIXIR_MASTER", "", "str", "Elixir master node", alias="WHITEMAGIC_ELIXIR_MASTER"),
}


# ---------------------------------------------------------------------------
# Accessor functions — use these instead of os.getenv directly.
# ---------------------------------------------------------------------------

def _resolve_alias(name: str) -> str:
    """Return the WHITEMAGIC_* alias for a WM_* var, or vice versa."""
    spec = REGISTRY.get(name)
    if spec and spec.alias:
        return spec.alias
    return name


def get_env(name: str, default: str | None = None) -> str | None:
    """Read a string env var, checking both WM_* and WHITEMAGIC_* aliases."""
    val = os.getenv(name)
    if val is not None:
        return val
    alias = _resolve_alias(name)
    if alias != name:
        val = os.getenv(alias)
        if val is not None:
            return val
    if default is not None:
        return default
    spec = REGISTRY.get(name)
    if spec and spec.default is not None:
        return str(spec.default)
    return None


def get_env_int(name: str, default: int = 0) -> int:
    """Read an int env var with fallback to registry default."""
    val = get_env(name)
    if val is None or val == "":
        spec = REGISTRY.get(name)
        if spec and isinstance(spec.default, int):
            return spec.default
        return default
    try:
        return int(val)
    except ValueError:
        return default


def get_env_float(name: str, default: float = 0.0) -> float:
    """Read a float env var with fallback to registry default."""
    val = get_env(name)
    if val is None or val == "":
        spec = REGISTRY.get(name)
        if spec and isinstance(spec.default, (int, float)):
            return float(spec.default)
        return default
    try:
        return float(val)
    except ValueError:
        return default


def get_env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean env var.  Truthy: 1, true, yes.  Falsy: 0, false, no."""
    val = get_env(name)
    if val is None or val == "":
        spec = REGISTRY.get(name)
        if spec and isinstance(spec.default, bool):
            return spec.default
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def get_env_path(name: str, default: str | None = None) -> Path | None:
    """Read a path env var, expanding ~ and returning a Path object."""
    val = get_env(name, default)
    if val is None or val == "":
        return None
    return Path(val).expanduser()


def get_all_env_vars() -> dict[str, str | None]:
    """Return all registered WM_* env vars with their current values."""
    result = {}
    for name, spec in REGISTRY.items():
        val = os.getenv(name)
        if val is None and spec.alias:
            val = os.getenv(spec.alias)
        result[name] = val
    return result


def get_registry_names() -> list[str]:
    """Return sorted list of all registered env var names."""
    return sorted(REGISTRY.keys())


def is_registered(name: str) -> bool:
    """Check if an env var is in the registry."""
    return name in REGISTRY
