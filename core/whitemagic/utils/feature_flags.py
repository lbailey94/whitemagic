"""feature_flags.py — WM_FEATURE_* environment variable convention and registry.

Phase 5.5: Provides a lightweight feature-flag system so experimental features can be
enabled/disabled without code changes. Follows the ``WM_FEATURE_<NAME>=1`` convention.

Usage:
    from whitemagic.utils.feature_flags import is_enabled, require

    if is_enabled("EXPERIMENTAL_KG2"):
        # use new knowledge graph path
        ...

    # Or raise if feature not enabled (useful in tool handlers):
    require("OTEL")  # raises FeatureDisabledError if WM_FEATURE_OTEL != "1"

Adding a new feature flag:
    1. Add an entry to ``FEATURE_REGISTRY`` below with name, description, and default.
    2. Use ``is_enabled("YOUR_FLAG")`` in code.
    3. Document in ``docs/CONFIGURATION.md`` under a "Feature Flags" section.

Environment variable format:
    WM_FEATURE_<NAME>=1   # enable
    WM_FEATURE_<NAME>=0   # explicitly disable (overrides default)
    (unset)               # use default from registry
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


class FeatureDisabledError(RuntimeError):
    """Raised by ``require()`` when a feature flag is not enabled."""

    def __init__(self, flag_name: str) -> None:
        super().__init__(
            f"Feature '{flag_name}' is not enabled. "
            f"Set WM_FEATURE_{flag_name.upper()}=1 to enable it."
        )
        self.flag_name = flag_name


@dataclass(frozen=True)
class FeatureFlag:
    """Registry entry for a single feature flag."""

    name: str
    description: str
    default: bool = False
    stable: bool = False  # True = production-ready; False = experimental


FEATURE_REGISTRY: list[FeatureFlag] = [
    FeatureFlag(
        name="OTEL",
        description="Enable OpenTelemetry tracing (requires opentelemetry-sdk)",
        default=False,
        stable=True,
    ),
    FeatureFlag(
        name="PROMETHEUS",
        description="Expose Prometheus metrics endpoint on WM_PROMETHEUS_PORT",
        default=False,
        stable=True,
    ),
    FeatureFlag(
        name="EXPERIMENTAL_KG2",
        description="Use KG 2.0 (LightNER + typed edges) as default for knowledge extraction",
        default=False,
        stable=False,
    ),
    FeatureFlag(
        name="STRICT_CORS",
        description="Enforce strict CORS (localhost only) even if WM_MCP_CORS_ORIGINS=*",
        default=True,
        stable=True,
    ),
    FeatureFlag(
        name="ELIXIR_OTP",
        description="Route concurrency tasks to Elixir/OTP bridge (experimental — stub only)",
        default=False,
        stable=False,
    ),
    FeatureFlag(
        name="KOKA_EFFECTS",
        description="Enable Koka algebraic effect handlers for memory transactions",
        default=False,
        stable=False,
    ),
    FeatureFlag(
        name="DREAM_AUTO",
        description="Automatically start dream cycle on idle (Wu Xing Water phase)",
        default=False,
        stable=False,
    ),
    FeatureFlag(
        name="RUST_STORE",
        description="Use Rust-native SQLite store path (PSR-001) when available",
        default=True,
        stable=True,
    ),
]

# Build lookup dict for O(1) access
_REGISTRY: dict[str, FeatureFlag] = {f.name.upper(): f for f in FEATURE_REGISTRY}


def is_enabled(flag_name: str) -> bool:
    """Return True if the feature flag is enabled.

    Checks ``WM_FEATURE_<FLAG_NAME>`` env var first, then registry default.

    Args:
        flag_name: Case-insensitive flag name (e.g., ``"OTEL"``, ``"otel"``).

    Returns:
        True if enabled, False otherwise.
    """
    key = flag_name.upper()
    env_var = f"WM_FEATURE_{key}"
    raw = os.environ.get(env_var)

    if raw is not None:
        return raw.strip() not in ("0", "false", "no", "")

    flag = _REGISTRY.get(key)
    return flag.default if flag is not None else False


def require(flag_name: str) -> None:
    """Assert a feature flag is enabled, raising FeatureDisabledError if not.

    Useful for tool entry-points that should fail fast when their feature gate
    is off rather than silently degrading.

    Args:
        flag_name: Case-insensitive flag name.

    Raises:
        FeatureDisabledError: If the flag is not enabled.
    """
    if not is_enabled(flag_name):
        raise FeatureDisabledError(flag_name.upper())


def get_all_flags() -> dict[str, dict[str, Any]]:
    """Return all registered flags with their current values.

    Useful for the ``capabilities`` and ``manifest`` tools.

    Returns:
        Dict mapping flag name → {enabled, default, description, stable}.
    """
    result = {}
    for flag in FEATURE_REGISTRY:
        result[flag.name] = {
            "enabled": is_enabled(flag.name),
            "default": flag.default,
            "description": flag.description,
            "stable": flag.stable,
            "env_var": f"WM_FEATURE_{flag.name.upper()}",
        }
    return result
